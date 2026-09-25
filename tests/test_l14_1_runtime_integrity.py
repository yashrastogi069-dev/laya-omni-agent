"""Runtime Integrity, Durability & Failure Accountability Test Suite (Checkpoint L14.1).

Tests for independent audit findings AUDIT-01 through AUDIT-16, crash-window fault injection,
transactional atomicity, state machine resilience, and idempotency guarantees.
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from typing import Any, Dict

from omni_engine.capabilities import build_real_capability_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.capability import CapabilitySpec, ErrorCode, IdempotencyClass, ToolError, ToolResult
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, RetryPolicy
from omni_engine.contracts.operation import AttemptState, MutationState
from omni_engine.contracts.plan import Plan, PlanStep, PlanType, PlanValidationError
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.planning.generative_planner import GenerativePlanner
from omni_engine.contracts.quest import (
    InvalidStateTransitionError,
    Quest,
    QuestEventEnum,
    QuestStatus,
    QuestStep,
    StepStatus,
    VALID_STEP_TRANSITIONS,
)
from omni_engine.execution.executor import DeterministicDAGExecutor
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore


class TestL14_1_Batch1_StateMachineAndAtomicity(unittest.TestCase):
    """Tests reproducing AUDIT-04, AUDIT-05, AUDIT-06, and AUDIT-07."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_1_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)

        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.capability_registry = build_real_capability_registry()
        self.policy_engine = PolicyEngine(mode="active")
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
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audit_06_interrupted_read_only_running_step_recovery(self):
        """AUDIT-06: Crash recovery of a READ_ONLY step left in RUNNING status.
        
        Invariant: If a process crashes while a READ_ONLY step is RUNNING, a fresh executor
        instance must be able to recover the step and complete execution cleanly without
        raising InvalidStateTransitionError.
        """
        quest = self.quest_engine.create_quest(
            title="Interrupted Read-Only Quest",
            goal="Survive crash during read-only step",
        )
        s1 = QuestStep(
            step_id="s1",
            quest_id=quest.quest_id,
            capability_id="safe_math",
            action_class=ActionClass.READ_ONLY,
            intent="Interrupted math step",
            arguments={"expression": "40 + 2"},
            status=StepStatus.RUNNING,  # Simulates crash during execution
        )
        self.quest_store.save_steps(quest.quest_id, [s1])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        # Fresh executor simulates reboot
        fresh_executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

        summary = fresh_executor.execute(quest.quest_id)
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(summary.completed_steps, 1)
        recovered_step = self.quest_engine.get_step(quest.quest_id, "s1")
        self.assertEqual(recovered_step.status, StepStatus.COMPLETED)
        self.assertEqual(recovered_step.execution_receipt["data"]["result"], 42)

    def test_audit_07_unknown_commit_pauses_for_reconciliation_not_terminal_failed(self):
        """AUDIT-07: UNKNOWN_COMMIT mutation uncertainty must pause for reconciliation, not permanently fail.
        
        Invariant: When an in-progress mutation is interrupted, it has UNKNOWN_COMMIT uncertainty.
        The Quest must transition to PAUSED_FOR_RECONCILIATION (and step to AWAITING_RECONCILIATION)
        rather than terminal FAILED, so that physical evidence reconciliation can resume execution.
        """
        target_file = Path(self.temp_dir) / "output.txt"
        quest = self.quest_engine.create_quest(
            title="Uncertain Mutation Quest",
            goal="Survive uncertain mutation and reconcile",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        s1 = QuestStep(
            step_id="s1",
            quest_id=quest.quest_id,
            capability_id="file_write",
            action_class=ActionClass.LOCAL_UPDATE,
            intent="Write output file",
            arguments={"filepath": str(target_file), "content": "vital data"},
            status=StepStatus.RUNNING,  # Left running when crashed
        )
        self.quest_store.save_steps(quest.quest_id, [s1])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        # Register operation in ledger as IN_PROGRESS
        op_id = f"op_{quest.quest_id}_s1_file_write"
        self.operation_ledger.register_mutation(
            operation_id=op_id,
            quest_id=quest.quest_id,
            step_id="s1",
            capability_id="file_write",
            arguments={"filepath": str(target_file), "content": "vital data"},
        )
        self.operation_ledger.begin_attempt(op_id)

        # Reboot executor
        fresh_executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

        summary = fresh_executor.execute(quest.quest_id)
        # Must NOT be terminal FAILED! Must be PAUSED_FOR_RECONCILIATION
        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_RECONCILIATION)

        step_rec = self.quest_engine.get_step(quest.quest_id, "s1")
        self.assertEqual(step_rec.status, StepStatus.AWAITING_RECONCILIATION)

        # Simulate reconciliation: an operator or verifier proves the file was written
        target_file.write_text("vital data", encoding="utf-8")
        self.operation_ledger.reconcile_operation(
            operation_id=op_id,
            reconciled_state=MutationState.COMMITTED,
            evidence={"file_verified": True},
        )

        # Resume the quest: must successfully advance to AWAITING_VERIFICATION!
        resumed_summary = fresh_executor.resume(quest.quest_id)
        self.assertEqual(resumed_summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(resumed_summary.completed_steps, 1)

    def test_audit_05_quest_transition_and_event_atomicity(self):
        """AUDIT-05: Quest state update and QuestEvent append must be atomic in a single transaction."""
        quest = self.quest_engine.create_quest(title="Atomicity Quest", goal="Test atomic event")
        
        # Test whether transition_quest_atomic exists on store
        self.assertTrue(
            hasattr(self.quest_store, "transition_quest_atomic"),
            "QuestStore must provide transition_quest_atomic to guarantee transactional atomicity",
        )

    def test_audit_04_operation_and_attempt_atomicity(self):
        """AUDIT-04: Operation state update and attempt creation must be atomic in a single transaction."""
        # Test whether atomic attempt methods exist on store
        self.assertTrue(
            hasattr(self.operation_store, "begin_attempt_atomic"),
            "OperationStore must provide begin_attempt_atomic to guarantee transactional atomicity",
        )
        self.assertTrue(
            hasattr(self.operation_store, "commit_attempt_atomic"),
            "OperationStore must provide commit_attempt_atomic to guarantee transactional atomicity",
        )
        self.assertTrue(
            hasattr(self.operation_store, "fail_attempt_atomic"),
            "OperationStore must provide fail_attempt_atomic to guarantee transactional atomicity",
        )


class TestL14_1_Batch2_IdempotencyAndTimeouts(unittest.TestCase):
    """Tests reproducing AUDIT-01, AUDIT-02, and AUDIT-03."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_b2_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)

        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.capability_registry = build_real_capability_registry()
        self.policy_engine = PolicyEngine()
        self.plan_validator = DeterministicPlanValidator(self.capability_registry)

        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audit_01_mutation_timeout_enters_unknown_commit_and_pauses_for_reconciliation(self):
        """AUDIT-01: Mutation timeout must mark UNKNOWN_COMMIT, pause quest for reconciliation, and block blind retry."""
        def timeout_mutation(target: str) -> Dict[str, Any]:
            raise TimeoutError(f"Connection timed out executing mutation on {target}")

        spec = CapabilitySpec(
            id="test_timeout_mutation",
            name="Timeout Mutation Tool",
            description="Simulates a mutation that times out",
            domain="system",
            action_class=ActionClass.EXTERNAL_UPDATE,
            idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
            input_schema={"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]},
        )
        self.capability_registry.register(spec, timeout_mutation)

        quest = self.quest_engine.create_quest(
            title="Timeout Quest",
            goal="Survive timeout during mutating action",
            autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
        )
        step = QuestStep(
            step_id="s1",
            quest_id=quest.quest_id,
            capability_id="test_timeout_mutation",
            action_class=ActionClass.EXTERNAL_UPDATE,
            intent="Mutate external resource with timeout",
            arguments={"target": "api.example.com"},
            status=StepStatus.PENDING,
        )
        self.quest_store.save_steps(quest.quest_id, [step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="test_timeout_mutation",
                    intent="Mutate external resource with timeout",
                    arguments={"target": "api.example.com"},
                    max_attempts=1,
                )
            ],
        )

        summary = self.executor.execute(quest.quest_id, plan=plan)
        # Must pause for reconciliation, NOT silently mark FAILED or fail quest terminally
        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_RECONCILIATION)

        # Verify step is awaiting reconciliation
        step_rec = self.quest_engine.get_step(quest.quest_id, "s1")
        self.assertEqual(step_rec.status, StepStatus.AWAITING_RECONCILIATION)

        # Verify ledger operation is in UNKNOWN_COMMIT state, NOT FAILED
        op_id = f"op_{quest.quest_id}_s1_test_timeout_mutation"
        op = self.operation_ledger.get_operation(op_id)
        self.assertIsNotNone(op)
        self.assertEqual(op.state, MutationState.UNKNOWN_COMMIT)

        # Blind retries must be rejected by the ledger
        with self.assertRaises(Exception):
            self.operation_ledger.begin_attempt(op_id)

    def test_audit_02_ledger_idempotency_keys_scoped_by_quest_id(self):
        """AUDIT-02: Automatic idempotency keys must be scoped by quest_id to prevent cross-quest deduplication collisions."""
        args = {"filepath": "shared_output.txt", "content": "hello world"}
        
        # Quest 1 executes and commits mutation
        op1, is_dedup1 = self.operation_ledger.register_mutation(
            quest_id="quest_alpha",
            step_id="step_write",
            capability_id="file_write",
            arguments=args,
        )
        self.assertFalse(is_dedup1)
        self.operation_ledger.begin_attempt(op1.operation_id)
        self.operation_ledger.commit_attempt(op1.operation_id, "att_1", {"written": True})

        # Quest 2 arrives later with identical capability and arguments
        op2, is_dedup2 = self.operation_ledger.register_mutation(
            quest_id="quest_beta",
            step_id="step_write",
            capability_id="file_write",
            arguments=args,
        )
        # Must NOT be deduplicated across different quests!
        self.assertFalse(is_dedup2, "Automatic idempotency key collision between independent quests!")
        self.assertNotEqual(op1.idempotency_key, op2.idempotency_key)

        # However, an explicit custom_idempotency_key MUST bridge across quests
        shared_key = "external_payment_tx_9999"
        op3, is_dedup3 = self.operation_ledger.register_mutation(
            quest_id="quest_gamma",
            step_id="step_tx",
            capability_id="file_write",
            arguments=args,
            custom_idempotency_key=shared_key,
        )
        self.assertFalse(is_dedup3)
        self.operation_ledger.begin_attempt(op3.operation_id)
        self.operation_ledger.commit_attempt(op3.operation_id, "att_3", {"tx": "done"})

        op4, is_dedup4 = self.operation_ledger.register_mutation(
            quest_id="quest_delta",
            step_id="step_tx",
            capability_id="file_write",
            arguments=args,
            custom_idempotency_key=shared_key,
        )
        self.assertTrue(is_dedup4, "Explicit custom idempotency key must deduplicate globally across quests")

    def test_audit_03_custom_idempotency_key_propagated_to_invocation(self):
        """AUDIT-03: Custom idempotency key and operation context must propagate into capability invocation context."""
        captured_context = {}

        def spy_capability(data: str, **kwargs: Any) -> Dict[str, Any]:
            captured_context.update(kwargs)
            return {"status": "ok", "echo": data}

        spec = CapabilitySpec(
            id="test_spy_mutation",
            name="Spy Mutation Tool",
            description="Records invocation context",
            domain="system",
            action_class=ActionClass.LOCAL_UPDATE,
            idempotency_class=IdempotencyClass.REMOTE_IDEMPOTENCY_KEY,
            input_schema={"type": "object", "properties": {"data": {"type": "string"}}, "required": ["data"]},
        )
        self.capability_registry.register(spec, spy_capability)

        quest = self.quest_engine.create_quest(
            title="Spy Quest",
            goal="Propagate idempotency key",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        step = QuestStep(
            step_id="s1",
            quest_id=quest.quest_id,
            capability_id="test_spy_mutation",
            action_class=ActionClass.LOCAL_UPDATE,
            intent="Execute with propagated context",
            arguments={"data": "test_payload"},
            status=StepStatus.PENDING,
        )
        self.quest_store.save_steps(quest.quest_id, [step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        summary = self.executor.execute(quest.quest_id)
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        
        # Verify propagation of operation context
        self.assertIn("idempotency_key", captured_context, "idempotency_key was not propagated into capability invocation!")
        self.assertTrue(captured_context["idempotency_key"].startswith("idem_"))
        self.assertEqual(captured_context.get("quest_id"), quest.quest_id)
        self.assertEqual(captured_context.get("step_id"), "s1")


class TestL14_1_Batch3_PlanDurabilityAndPlanners(unittest.TestCase):
    """Tests reproducing AUDIT-08, AUDIT-09, AUDIT-10, and AUDIT-11."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_b3_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)

        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.capability_registry = build_real_capability_registry()
        self.policy_engine = PolicyEngine()
        self.plan_validator = DeterministicPlanValidator(self.capability_registry)

        self.planner = StructuredDAGPlanner(self.capability_registry)

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_audit_09_plan_step_semantics_preserved_in_quest_step(self):
        """AUDIT-09: PlanStep semantics (timeout_s, max_attempts, can_fail_silently, metadata) must be preserved in QuestStep."""
        quest = self.quest_engine.create_quest(title="Semantics Quest", goal="Preserve semantics")
        plan_step = PlanStep(
            step_id="step_calc",
            capability_id="safe_math",
            intent="Execute math with custom semantics",
            arguments={"expression": "100 * 2"},
            timeout_s=45.0,
            max_attempts=1,
            can_fail_silently=True,
            metadata={"priority": "high", "cluster": "fast"},
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[plan_step],
        )

        self.planner.attach_to_quest(self.quest_engine, plan)

        # Reload step from persistent QuestStore
        saved_step = self.quest_engine.get_step(quest.quest_id, "step_calc")
        self.assertIsNotNone(saved_step)
        self.assertEqual(saved_step.timeout_s, 45.0)
        self.assertEqual(saved_step.max_attempts, 1)
        self.assertTrue(saved_step.can_fail_silently)
        self.assertEqual(saved_step.metadata.get("priority"), "high")
        self.assertEqual(saved_step.metadata.get("cluster"), "fast")

    def test_audit_08_plan_provenance_persisted_in_quest_metadata(self):
        """AUDIT-08: Plan identity (plan_id, plan_hash, plan_type) must be durably recorded in Quest metadata."""
        quest = self.quest_engine.create_quest(title="Provenance Quest", goal="Track provenance")
        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="s1",
                    capability_id="safe_math",
                    intent="Do math",
                    arguments={"expression": "2 + 2"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        reloaded_quest = self.quest_engine.get_quest(quest.quest_id)
        self.assertIn("plan_provenance", reloaded_quest.metadata)
        prov = reloaded_quest.metadata["plan_provenance"]
        self.assertEqual(prov.get("plan_id"), plan.plan_id)
        self.assertIn("plan_hash", prov)
        self.assertEqual(prov.get("plan_type"), PlanType.TEMPLATE_DERIVED.value)

    def test_audit_10_planners_derive_max_attempts_from_capability_spec(self):
        """AUDIT-10: Planners must derive max_attempts respecting CapabilitySpec.retry_policy and idempotency_class."""
        # Non-idempotent capability with RetryPolicy.NEVER
        spec = CapabilitySpec(
            id="test_charge_card",
            name="Charge Card",
            description="Charges credit card",
            domain="system",
            action_class=ActionClass.EXTERNAL_UPDATE,
            idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
            retry_policy=RetryPolicy.NEVER,
            input_schema={"type": "object", "properties": {"amount": {"type": "number"}}, "required": ["amount"]},
        )
        self.capability_registry.register(spec, lambda amount: {"charged": amount})

        gen_planner = GenerativePlanner(
            provider=None,
            capability_registry=self.capability_registry,
        )

        mock_plan_json = json.dumps({
            "steps": [
                {
                    "step_id": "charge_step",
                    "capability_id": "test_charge_card",
                    "intent": "Charge card once",
                    "arguments": {"amount": 50},
                    "dependencies": [],
                }
            ]
        })

        plan = gen_planner.synthesize_plan(
            quest_id="q_charge",
            goal="Charge card",
            mock_response=mock_plan_json,
        )
        # Must derive max_attempts=1, NOT hardcoded 3!
        self.assertEqual(plan.steps[0].max_attempts, 1)

    def test_audit_11_generative_planner_enforces_allowed_capabilities_boundary(self):
        """AUDIT-11: GenerativePlanner must reject steps referencing capabilities outside allowed_capabilities."""
        gen_planner = GenerativePlanner(
            provider=None,
            capability_registry=self.capability_registry,
        )
        mock_plan_json = json.dumps({
            "steps": [
                {
                    "step_id": "write_step",
                    "capability_id": "file_write",
                    "intent": "Write file",
                    "arguments": {"filepath": "out.txt", "content": "hi"},
                    "dependencies": [],
                }
            ]
        })

        # Caller explicitly restricts allowed capabilities to safe_math only
        with self.assertRaises(PlanValidationError):
            gen_planner.synthesize_plan(
                quest_id="q_restricted",
                goal="Write file",
                allowed_capabilities=["safe_math"],
                mock_response=mock_plan_json,
            )


class TestL14_1_Batch4_ResolversResourcesAndLifecycle(unittest.TestCase):
    """Batch 4: Missing Input Pauses, Resource Conflict Detection, Timeout Enforcement, and Cancellation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_quest_b4.db"
        self.op_db_path = Path(self.temp_dir) / "test_ops_b4.db"

        self.quest_store = QuestStore(self.db_path)
        self.quest_engine = QuestEngine(self.quest_store)

        self.operation_store = OperationStore(self.op_db_path)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.capability_registry = CapabilityRegistry()
        self._register_test_capabilities()

        self.policy_engine = PolicyEngine()
        self.plan_validator = DeterministicPlanValidator(self.capability_registry)
        self.planner = StructuredDAGPlanner(self.capability_registry)

        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.capability_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.operation_ledger,
            plan_validator=self.plan_validator,
        )

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _register_test_capabilities(self):
        # Register file_write
        spec_write = CapabilitySpec(
            id="file_write",
            name="File Write",
            description="Writes text to file",
            domain="os",
            action_class=ActionClass.LOCAL_UPDATE,
            idempotency_class=IdempotencyClass.NATURAL,
            input_schema={"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]},
        )
        self.capability_registry.register(spec_write, lambda filepath, content: {"written": True, "filepath": filepath})

        # Register safe_math
        spec_math = CapabilitySpec(
            id="safe_math",
            name="Safe Math",
            description="Evaluates math",
            domain="system",
            action_class=ActionClass.READ_ONLY,
            idempotency_class=IdempotencyClass.READ_ONLY,
            input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
        )
        self.capability_registry.register(spec_math, lambda expression: {"result": 42})

        # Register slow capability
        spec_slow = CapabilitySpec(
            id="slow_cap",
            name="Slow Capability",
            description="Sleeps for a short while",
            domain="system",
            action_class=ActionClass.READ_ONLY,
            idempotency_class=IdempotencyClass.READ_ONLY,
            input_schema={"type": "object", "properties": {"delay": {"type": "number"}}, "required": ["delay"]},
        )
        def _slow_impl(delay):
            time.sleep(delay)
            return {"waited": delay}
        self.capability_registry.register(spec_slow, _slow_impl)

    def test_audit_12_missing_input_pauses_quest_for_input_and_resumes(self):
        """AUDIT-12: Missing $inputs.<key> must pause step as PAUSED and quest as PAUSED_FOR_INPUT, not fail terminally."""
        quest = self.quest_engine.create_quest(title="Input Quest", goal="Test input pause")
        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="step_write",
                    capability_id="file_write",
                    intent="Write file using input",
                    arguments={"filepath": "$inputs.target_file", "content": "hello world"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Execute with empty inputs (target_file missing)
        summary = self.executor.execute(quest.quest_id, inputs={})

        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_INPUT)
        self.assertEqual(summary.paused_step_id, "step_write")
        self.assertIn("target_file", summary.confirmation_prompt or "")

        # Verify step in SQLite is PAUSED, NOT FAILED
        reloaded_step = self.quest_engine.get_step(quest.quest_id, "step_write")
        self.assertEqual(reloaded_step.status, StepStatus.PAUSED)

        # Resume with provided user input
        resumed_summary = self.executor.resume(
            quest.quest_id,
            user_inputs={"target_file": "actual_output.txt"},
        )
        self.assertEqual(resumed_summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(resumed_summary.completed_steps, 1)

    def test_audit_13_validator_detects_concurrent_resource_conflicts(self):
        """AUDIT-13: Plan validator must detect concurrent conflicting mutations on identical resources."""
        # Two concurrent writes to the same file 'conflict.txt' with no dependency between them
        plan = Plan(
            quest_id="q_conflict",
            goal="Two writes to same file",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="write_1",
                    capability_id="file_write",
                    intent="First write",
                    arguments={"filepath": "conflict.txt", "content": "one"},
                ),
                PlanStep(
                    step_id="write_2",
                    capability_id="file_write",
                    intent="Second write",
                    arguments={"filepath": "conflict.txt", "content": "two"},
                ),
            ],
        )
        report = self.plan_validator.validate(plan)
        self.assertFalse(report.is_valid)
        self.assertTrue(any("conflict" in err.lower() or "resource" in err.lower() for err in report.errors))

        # Adding a causal dependency resolves the concurrency conflict
        plan_ordered = Plan(
            quest_id="q_ordered",
            goal="Two ordered writes to same file",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="write_1",
                    capability_id="file_write",
                    intent="First write",
                    arguments={"filepath": "conflict.txt", "content": "one"},
                ),
                PlanStep(
                    step_id="write_2",
                    capability_id="file_write",
                    intent="Second write",
                    arguments={"filepath": "conflict.txt", "content": "two"},
                    dependencies=["write_1"],
                ),
            ],
        )
        report_ordered = self.plan_validator.validate(plan_ordered)
        self.assertTrue(report_ordered.is_valid)

    def test_audit_14_canonical_resource_identity_extraction(self):
        """AUDIT-14: Canonical resource identity extraction normalizes file paths, PIDs, and repo paths."""
        res_file = DeterministicPlanValidator.extract_resource_identity(
            PlanStep(
                step_id="s1",
                capability_id="file_write",
                intent="write",
                arguments={"filepath": "test_dir/../test_dir/file.txt"},
            )
        )
        self.assertIsNotNone(res_file)
        self.assertTrue(res_file.startswith("file:"))
        self.assertNotIn("..", res_file)

    def test_audit_15_executor_enforces_plan_timeout_budget(self):
        """AUDIT-15: Executor coordinator loop must enforce plan timeout budget."""
        quest = self.quest_engine.create_quest(title="Timeout Quest", goal="Timeout plan")
        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            timeout_budget_s=10.0,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="safe_math",
                    intent="math",
                    arguments={"expression": "1 + 1"},
                    timeout_s=5.0,
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="safe_math",
                    intent="math",
                    arguments={"expression": "2 + 2"},
                    dependencies=["step_1"],
                    timeout_s=5.0,
                ),
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Simulate elapsed time advancing past timeout budget in coordinator loop
        real_perf_counter = time.perf_counter
        call_count = 0
        def fake_perf_counter():
            nonlocal call_count
            call_count += 1
            if call_count > 3:
                return real_perf_counter() + 20.0
            return real_perf_counter()

        with unittest.mock.patch("time.perf_counter", side_effect=fake_perf_counter):
            summary = self.executor.execute(quest.quest_id)
            self.assertEqual(summary.final_status, QuestStatus.FAILED)
            self.assertIn("timeout", (summary.error or "").lower())

        reloaded = self.quest_engine.get_quest(quest.quest_id)
        self.assertEqual(reloaded.status, QuestStatus.FAILED)

    def test_audit_16_deterministic_cancellation_lifecycle(self):
        """AUDIT-16: Deterministic cancellation cancels unstarted steps, sets quest CANCELLED, and emits event."""
        quest = self.quest_engine.create_quest(title="Cancel Quest", goal="Cancel task")
        plan = Plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="step_a",
                    capability_id="safe_math",
                    intent="math",
                    arguments={"expression": "1 + 1"},
                ),
                PlanStep(
                    step_id="step_b",
                    capability_id="safe_math",
                    intent="math",
                    arguments={"expression": "2 + 2"},
                    dependencies=["step_a"],
                ),
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        summary = self.executor.cancel(quest.quest_id, reason="Operator abort")
        self.assertEqual(summary.final_status, QuestStatus.CANCELLED)

        reloaded_quest = self.quest_engine.get_quest(quest.quest_id)
        self.assertEqual(reloaded_quest.status, QuestStatus.CANCELLED)

        step_a = self.quest_engine.get_step(quest.quest_id, "step_a")
        step_b = self.quest_engine.get_step(quest.quest_id, "step_b")
        self.assertEqual(step_a.status, StepStatus.CANCELLED)
        self.assertEqual(step_b.status, StepStatus.CANCELLED)

        events = self.quest_engine.get_events(quest.quest_id)
        self.assertTrue(any(e.event_type == QuestEventEnum.QUEST_CANCELLED for e in events))


if __name__ == "__main__":
    unittest.main()

