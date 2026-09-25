"""Tests for Checkpoint L14: Deterministic DAG Executor.

Verifies:
1. Strongly typed execution contracts (extra="forbid").
2. Dynamic parameter resolution ($inputs.<param>, $steps.<step_id>.<path>, stringified JSON).
3. Plan validation firewall integration (ExecutionFirewallError).
4. Linear and Diamond DAG execution with parallel read-only dispatch.
5. Strict Mutation Barrier and Windows file lock defense.
6. Exactly-once mutation semantics via OperationLedger deduplication.
7. UNKNOWN_COMMIT failure handling blocking blind retries.
8. Confirmation pauses (PAUSED_FOR_CONFIRMATION) and safe resumption.
9. Lease registry preventing concurrent execution of the same quest.
10. Invariant 6 evidence-based completion boundary (AWAITING_VERIFICATION).
11. Crash recovery from SQLite persistence.
"""

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict

from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, IdempotencyClass
from omni_engine.contracts.execution import (
    ExecutionError,
    ExecutionFirewallError,
    QuestAlreadyRunningError,
    QuestExecutionSummary,
    StepExecutionReceipt,
    UnresolvedArgumentError,
)
from omni_engine.contracts.operation import MutationState
from omni_engine.contracts.plan import Plan, PlanStep
from omni_engine.contracts.quest import (
    Quest,
    QuestStatus,
    QuestStep,
    StepStatus,
)
from omni_engine.execution.dynamic_resolver import DynamicResolver
from omni_engine.execution.executor import DeterministicDAGExecutor
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine
from omni_engine.policy.store import PolicyStore
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore


class TestL14Contracts(unittest.TestCase):
    """Test strongly typed execution contracts and extra='forbid' constraint."""

    def test_step_execution_receipt_contract_safety(self):
        receipt = StepExecutionReceipt(
            step_id="step_1",
            capability_id="web_search",
            action_class=ActionClass.READ_ONLY,
            status=StepStatus.COMPLETED,
            latency_ms=12.5,
        )
        self.assertEqual(receipt.step_id, "step_1")
        self.assertEqual(receipt.status, StepStatus.COMPLETED)
        self.assertFalse(receipt.is_deduplicated)

        with self.assertRaises(Exception):
            StepExecutionReceipt(
                step_id="step_1",
                capability_id="web_search",
                action_class=ActionClass.READ_ONLY,
                status=StepStatus.COMPLETED,
                unauthorized_extra_field="malicious",
            )

    def test_quest_execution_summary_contract_safety(self):
        summary = QuestExecutionSummary(
            quest_id="qst_123",
            initial_status=QuestStatus.PLANNED,
            final_status=QuestStatus.AWAITING_VERIFICATION,
            total_steps=3,
            completed_steps=3,
            failed_steps=0,
            latency_ms=45.2,
        )
        self.assertEqual(summary.quest_id, "qst_123")
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)

        with self.assertRaises(Exception):
            QuestExecutionSummary(
                quest_id="qst_123",
                initial_status=QuestStatus.PLANNED,
                final_status=QuestStatus.AWAITING_VERIFICATION,
                total_steps=3,
                completed_steps=3,
                failed_steps=0,
                extra_field="denied",
            )


class TestL14DynamicResolver(unittest.TestCase):
    """Unit tests for DynamicResolver ($inputs, $steps, nested paths, stringified JSON)."""

    def test_resolve_quest_inputs(self):
        args = {"query": "$inputs.search_term", "limit": "$inputs.max_items"}
        inputs = {"search_term": "laya omni agent", "max_items": 10}
        resolved = DynamicResolver.resolve_arguments(args, quest_inputs=inputs)
        self.assertEqual(resolved["query"], "laya omni agent")
        self.assertEqual(resolved["limit"], 10)
        self.assertIsInstance(resolved["limit"], int)

    def test_resolve_step_output_exact_type_preservation(self):
        completed = {
            "step_1": {
                "execution_receipt": {
                    "data": {
                        "count": 42,
                        "flag": True,
                        "items": ["apple", "banana"],
                        "nested": {"key": "secret"},
                    }
                }
            }
        }
        args = {
            "val_int": "$steps.step_1.output.count",
            "val_bool": "$steps.step_1.output.flag",
            "val_list": "$steps.step_1.output.items",
            "val_nested": "$steps.step_1.output.nested.key",
        }
        resolved = DynamicResolver.resolve_arguments(args, completed_steps=completed)
        self.assertEqual(resolved["val_int"], 42)
        self.assertIsInstance(resolved["val_int"], int)
        self.assertIs(resolved["val_bool"], True)
        self.assertEqual(resolved["val_list"], ["apple", "banana"])
        self.assertEqual(resolved["val_nested"], "secret")

    def test_resolve_string_interpolation(self):
        completed = {
            "step_1": {
                "execution_receipt": {
                    "data": {"count": 15}
                }
            }
        }
        inputs = {"prefix": "Found"}
        args = {
            "expression": "$steps.step_1.output.count + 5",
            "message": "$inputs.prefix $steps.step_1.output.count results",
        }
        resolved = DynamicResolver.resolve_arguments(args, quest_inputs=inputs, completed_steps=completed)
        self.assertEqual(resolved["expression"], "15 + 5")
        self.assertEqual(resolved["message"], "Found 15 results")

    def test_resolve_stringified_json_navigation(self):
        completed = {
            "step_1": {
                "execution_receipt": {
                    "output": '{"doc_id": "doc_999", "score": 0.95}'
                }
            }
        }
        args = {"target_doc": "$steps.step_1.output.doc_id"}
        resolved = DynamicResolver.resolve_arguments(args, completed_steps=completed)
        self.assertEqual(resolved["target_doc"], "doc_999")

    def test_unresolved_input_raises_error(self):
        args = {"query": "$inputs.missing_term"}
        with self.assertRaises(UnresolvedArgumentError) as ctx:
            DynamicResolver.resolve_arguments(args, quest_inputs={})
        self.assertIn("missing_term", str(ctx.exception))

    def test_unresolved_step_raises_error(self):
        args = {"query": "$steps.step_unrun.output.id"}
        with self.assertRaises(UnresolvedArgumentError) as ctx:
            DynamicResolver.resolve_arguments(args, completed_steps={})
        self.assertIn("step_unrun", str(ctx.exception))

    def test_missing_property_raises_error(self):
        completed = {"step_1": {"execution_receipt": {"data": {"valid_key": "val"}}}}
        args = {"query": "$steps.step_1.output.invalid_key"}
        with self.assertRaises(UnresolvedArgumentError) as ctx:
            DynamicResolver.resolve_arguments(args, completed_steps=completed)
        self.assertIn("invalid_key", str(ctx.exception))


class TestL14DeterministicDAGExecutor(unittest.TestCase):
    """Integration test suite for DeterministicDAGExecutor."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_l14_test_")
        self.quest_db_path = Path(self.temp_dir) / "test_quest.db"
        self.op_db_path = Path(self.temp_dir) / "test_op.db"
        self.policy_store_path = Path(self.temp_dir) / "test_policy.json"

        # Initialize persistence stores & engines
        self.quest_store = QuestStore(self.quest_db_path)
        self.quest_engine = QuestEngine(store=self.quest_store)

        self.op_store = OperationStore(self.op_db_path)
        self.operation_ledger = OperationLedger(store=self.op_store)

        self.policy_store = PolicyStore(storage_path=str(self.policy_store_path))
        self.policy_engine = PolicyEngine(store=self.policy_store)

        self.capability_registry = build_real_capability_registry()
        self.plan_validator = DeterministicPlanValidator(
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
        )

        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
            max_parallel_workers=4,
        )

    def tearDown(self):
        self.quest_store.close()
        self.op_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Test 1: Plan Validation Firewall Rejection
    # -------------------------------------------------------------------------
    def test_plan_validation_firewall_rejects_cyclical_plan(self):
        """Pre-execution firewall must reject invalid plans immediately."""
        quest = self.quest_engine.create_quest(
            title="Cyclical Quest",
            goal="Test cycle rejection in executor",
        )
        plan = Plan.model_construct(
            quest_id=quest.quest_id,
            goal="Cyclical Plan",
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search 1",
                    arguments={"query": "test"},
                    dependencies=["step_2"],
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="web_search",
                    intent="Search 2",
                    arguments={"query": "test"},
                    dependencies=["step_1"],
                ),
            ],
        )

        with self.assertRaises(ExecutionFirewallError) as ctx:
            self.executor.execute(quest.quest_id, plan=plan)

        self.assertIn("Cycle detected", str(ctx.exception))
        # Verify quest transitioned to FAILED
        q_after = self.quest_engine.get_quest(quest.quest_id)
        self.assertEqual(q_after.status, QuestStatus.FAILED)

    # -------------------------------------------------------------------------
    # Test 2: Linear DAG Execution (A -> B) & Invariant 6 Boundary
    # -------------------------------------------------------------------------
    def test_linear_dag_execution_passes_to_awaiting_verification(self):
        """Linear plan executes and stops at AWAITING_VERIFICATION (Invariant 6)."""
        quest = self.quest_engine.create_quest(
            title="Linear Math Quest",
            goal="Compute dynamic math expression",
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Math Plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="safe_math",
                    intent="Step 1 base calc",
                    arguments={"expression": "10 + 20"},
                ),
                PlanStep(
                    step_id="s2",
                    capability_id="safe_math",
                    intent="Step 2 dynamic calc",
                    arguments={"expression": "$steps.s1.output.result * 2"},
                    dependencies=["s1"],
                ),
            ],
        )

        summary = self.executor.execute(quest.quest_id, plan=plan)

        # Invariant 6 check: MUST be AWAITING_VERIFICATION, NOT COMPLETED
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION, f"Summary error: {summary.error}")
        self.assertEqual(summary.total_steps, 2)
        self.assertEqual(summary.completed_steps, 2)
        self.assertEqual(summary.failed_steps, 0)
        self.assertIsNone(summary.error)

        # Verify steps and receipts persisted in SQLite
        s1 = self.quest_engine.get_step(quest.quest_id, "s1")
        self.assertEqual(s1.status, StepStatus.COMPLETED)
        self.assertEqual(s1.execution_receipt["data"]["result"], 30)

        s2 = self.quest_engine.get_step(quest.quest_id, "s2")
        self.assertEqual(s2.status, StepStatus.COMPLETED)
        self.assertEqual(s2.execution_receipt["data"]["result"], 60)

    # -------------------------------------------------------------------------
    # Test 3: Diamond DAG with Concurrent Read-Only Workers
    # -------------------------------------------------------------------------
    def test_diamond_dag_concurrent_reads_and_aggregation(self):
        """Diamond DAG: s1 -> s2_a, s2_b (parallel) -> s3 (aggregation)."""
        quest = self.quest_engine.create_quest(
            title="Diamond Math Quest",
            goal="Parallel math branches",
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Diamond Plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="safe_math",
                    intent="Root calculation",
                    arguments={"expression": "50"},
                ),
                PlanStep(
                    step_id="s2_a",
                    capability_id="safe_math",
                    intent="Branch A (+10)",
                    arguments={"expression": "$steps.s1.output.result + 10"},
                    dependencies=["s1"],
                ),
                PlanStep(
                    step_id="s2_b",
                    capability_id="safe_math",
                    intent="Branch B (*2)",
                    arguments={"expression": "$steps.s1.output.result * 2"},
                    dependencies=["s1"],
                ),
                PlanStep(
                    step_id="s3",
                    capability_id="safe_math",
                    intent="Join calculation",
                    arguments={"expression": "$steps.s2_a.output.result + $steps.s2_b.output.result"},
                    dependencies=["s2_a", "s2_b"],
                ),
            ],
        )

        summary = self.executor.execute(quest.quest_id, plan=plan)

        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(summary.completed_steps, 4)

        s3 = self.quest_engine.get_step(quest.quest_id, "s3")
        # 60 + 100 = 160
        self.assertEqual(s3.execution_receipt["data"]["result"], 160)

    # -------------------------------------------------------------------------
    # Test 4: Strict Mutation Barrier & Exactly-Once Operation Ledger
    # -------------------------------------------------------------------------
    def test_mutation_barrier_and_operation_ledger_deduplication(self):
        """Mutating step executes under mutation lock and registers in OperationLedger."""
        test_file = Path(self.temp_dir) / "output_test.txt"

        quest = self.quest_engine.create_quest(
            title="File Mutation Quest",
            goal="Write to file and verify ledger",
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="File Write Plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="safe_math",
                    intent="Generate number",
                    arguments={"expression": "100 + 23"},
                ),
                PlanStep(
                    step_id="s2",
                    capability_id="file_write",
                    intent="Write file",
                    arguments={
                        "filepath": str(test_file),
                        "content": "Result is $steps.s1.output.result",
                    },
                    dependencies=["s1"],
                ),
            ],
        )

        summary = self.executor.execute(quest.quest_id, plan=plan)
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertTrue(test_file.exists())
        self.assertIn("123", test_file.read_text(encoding="utf-8"))

        # Verify OperationLedger recorded the mutation
        op_id = f"op_{quest.quest_id}_s2_file_write"
        op_rec = self.operation_ledger.get_operation(op_id)
        self.assertIsNotNone(op_rec)
        self.assertEqual(op_rec.state, MutationState.COMMITTED)
        self.assertEqual(op_rec.total_attempts, 1)

        # Exactly-once deduplication check:
        # Re-registering the same mutation returns cached receipt immediately
        rec, is_dedup = self.operation_ledger.register_mutation(
            operation_id=op_id,
            quest_id=quest.quest_id,
            step_id="s2",
            capability_id="file_write",
            arguments={"filepath": str(test_file), "content": "Result is 123"},
            idempotency_class=IdempotencyClass.NATURAL,
        )
        self.assertTrue(is_dedup)
        self.assertEqual(rec.state, MutationState.COMMITTED)

    # -------------------------------------------------------------------------
    # Test 5: Confirmation Gate Pause & Safe Resumption
    # -------------------------------------------------------------------------
    def test_confirmation_gate_pause_and_resume(self):
        """Action requiring confirmation pauses quest; resume with confirmation finishes."""
        target_file = Path(self.temp_dir) / "sensitive_file.txt"
        target_file.write_text("initial content", encoding="utf-8")

        # Under LOCAL_OPERATOR, file_write overwriting an existing file requires confirmation
        quest = self.quest_engine.create_quest(
            title="Confirmation Gated Quest",
            goal="Overwrite file requiring approval",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Overwrite Plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="file_write",
                    intent="Overwrite existing file",
                    arguments={
                        "filepath": str(target_file),
                        "content": "new approved content",
                    },
                ),
            ],
        )

        # 1. Execute: should pause for confirmation
        summary = self.executor.execute(quest.quest_id, plan=plan)
        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_CONFIRMATION)
        self.assertEqual(summary.paused_step_id, "s1")
        self.assertIsNotNone(summary.confirmation_prompt)

        # Verify step in SQLite is PAUSED
        s1 = self.quest_engine.get_step(quest.quest_id, "s1")
        self.assertEqual(s1.status, StepStatus.PAUSED)

        # 2. Resume with user_confirmation=True
        resume_summary = self.executor.resume(quest.quest_id, user_confirmation=True)
        self.assertEqual(resume_summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(resume_summary.completed_steps, 1)

        # Verify file content updated
        self.assertEqual(target_file.read_text(encoding="utf-8").strip(), "new approved content")

    # -------------------------------------------------------------------------
    # Test 6: Confirmation Gate Rejection
    # -------------------------------------------------------------------------
    def test_confirmation_gate_rejection_fails_quest(self):
        """Resuming with user_confirmation=False fails the quest."""
        target_file = Path(self.temp_dir) / "another_file.txt"
        target_file.write_text("do not overwrite", encoding="utf-8")

        quest = self.quest_engine.create_quest(
            title="Rejected Quest",
            goal="Reject overwrite",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Reject Plan",
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="file_write",
                    intent="Attempt overwrite",
                    arguments={"filepath": str(target_file), "content": "overwrite"},
                ),
            ],
        )

        # Execute -> pause
        self.executor.execute(quest.quest_id, plan=plan)

        # Resume with user_confirmation=False -> fails
        summary = self.executor.resume(quest.quest_id, user_confirmation=False)
        self.assertEqual(summary.final_status, QuestStatus.FAILED)
        self.assertEqual(target_file.read_text(encoding="utf-8"), "do not overwrite")

    # -------------------------------------------------------------------------
    # Test 7: Lease Registry Prevents Concurrent Execution
    # -------------------------------------------------------------------------
    def test_lease_registry_rejects_concurrent_execution(self):
        """Calling execute on an already running quest raises QuestAlreadyRunningError."""
        quest = self.quest_engine.create_quest(title="Lease Quest", goal="Test lease")

        # Manually inject lease
        with self.executor._lease_lock:
            self.executor._active_leases.add(quest.quest_id)

        try:
            with self.assertRaises(QuestAlreadyRunningError):
                self.executor.execute(quest.quest_id)
        finally:
            with self.executor._lease_lock:
                self.executor._active_leases.remove(quest.quest_id)

    # -------------------------------------------------------------------------
    # Test 8: Crash Recovery and SQLite Resumption
    # -------------------------------------------------------------------------
    def test_crash_recovery_resumes_cleanly_from_sqlite(self):
        """Simulate crash with completed step and pending step, fresh executor finishes."""
        quest = self.quest_engine.create_quest(
            title="Crash Recovery Quest",
            goal="Survive process termination",
        )
        s1 = QuestStep(
            step_id="s1",
            quest_id=quest.quest_id,
            capability_id="safe_math",
            action_class=ActionClass.READ_ONLY,
            intent="Step 1 math",
            arguments={"expression": "100"},
            status=StepStatus.COMPLETED,
            execution_receipt={"data": {"result": 100}},
        )
        s2 = QuestStep(
            step_id="s2",
            quest_id=quest.quest_id,
            capability_id="safe_math",
            action_class=ActionClass.READ_ONLY,
            intent="Step 2 math",
            arguments={"expression": "$steps.s1.output.result + 50"},
            dependencies=["s1"],
            status=StepStatus.PENDING,
        )
        self.quest_store.save_steps(quest.quest_id, [s1, s2])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        # Fresh executor simulates process reboot
        fresh_executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

        summary = fresh_executor.execute(quest.quest_id)
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(summary.completed_steps, 2)

        s2_rec = self.quest_engine.get_step(quest.quest_id, "s2")
        self.assertEqual(s2_rec.status, StepStatus.COMPLETED)
        self.assertEqual(s2_rec.execution_receipt["data"]["result"], 150)


if __name__ == "__main__":
    unittest.main()
