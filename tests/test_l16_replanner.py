"""Unit and Integration Tests for Checkpoint L16: Controlled Replanner & Recovery Loop.

Verifies:
1. Blast-radius containment and transitive dependent tree isolation.
2. Anti-oscillation budgeting and replan attempt limits.
3. Deterministic fallback capability replacement.
4. Preservation of completed step receipts and OperationLedger idempotency.
5. Support for can_fail_silently in validator and executor.
6. End-to-end executor automatic replanning and recovery loop.
"""

import os
import shutil
import tempfile
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.capability import CapabilitySpec, ToolError, ToolResult
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, ErrorCode, ToolOutcome
from omni_engine.contracts.plan import Plan, PlanStep, PlanType
from omni_engine.contracts.quest import (
    Quest,
    QuestEventEnum,
    QuestStatus,
    QuestStep,
    StepStatus,
)
from omni_engine.contracts.replanning import (
    ReplanRequest,
    ReplanResult,
    ReplanScope,
    ReplanTrigger,
)
from omni_engine.execution.executor import DeterministicDAGExecutor
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore
from omni_engine.planning.replanner import ControlledReplanner, DEFAULT_CAPABILITY_FALLBACKS
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine
from omni_engine.policy.store import PolicyStore
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore


class TestL16ControlledReplanner(unittest.TestCase):
    """Test suite for ControlledReplanner algorithmic logic and contract invariants."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.quest_db = os.path.join(self.temp_dir, "test_quests.db")
        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.registry = build_real_capability_registry()
        self.validator = DeterministicPlanValidator(self.registry, allow_silent_failure=True)
        self.replanner = ControlledReplanner(
            capability_registry=self.registry,
            plan_validator=self.validator,
            max_replans=3,
        )

    def tearDown(self):
        self.quest_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compute_blast_radius_single_leaf_step(self):
        """A leaf step with no dependents has blast radius containing only itself."""
        steps = [
            PlanStep(step_id="step_1", capability_id="system_diagnostics", intent="check system"),
            PlanStep(step_id="step_2", capability_id="safe_math", intent="calc", dependencies=["step_1"]),
            PlanStep(step_id="step_3", capability_id="ping_test", intent="ping", arguments={"host": "127.0.0.1"}, dependencies=["step_1"]),
        ]
        # Failure in step_2 (leaf)
        blast = self.replanner.compute_blast_radius(steps, "step_2")
        self.assertEqual(blast, {"step_2"})

    def test_compute_blast_radius_transitive_descendants(self):
        """Failure in a root step includes all transitive children in the blast radius."""
        # Graph: step_1 -> step_2 -> step_3; step_4 independent
        steps = [
            PlanStep(step_id="step_1", capability_id="system_diagnostics", intent="root"),
            PlanStep(step_id="step_2", capability_id="safe_math", intent="mid", dependencies=["step_1"]),
            PlanStep(step_id="step_3", capability_id="safe_math", intent="leaf", dependencies=["step_2"]),
            PlanStep(step_id="step_4", capability_id="ping_test", intent="independent", arguments={"host": "127.0.0.1"}),
        ]
        blast = self.replanner.compute_blast_radius(steps, "step_1")
        self.assertEqual(blast, {"step_1", "step_2", "step_3"})
        self.assertNotIn("step_4", blast)

    def test_replan_request_budget_exceeded(self):
        """Replanning halts with success=False when replan_attempt > max_replans."""
        quest = self.quest_engine.create_quest(title="test budget", goal="test budget", quest_id="q_budget")
        plan = Plan(
            quest_id="q_budget",
            goal="test budget",
            steps=[PlanStep(step_id="s1", capability_id="safe_math", intent="calc")],
        )
        req = ReplanRequest(
            quest_id="q_budget",
            failed_step_id="s1",
            trigger=ReplanTrigger.STEP_FAILURE,
            error_message="tool crashed",
            replan_attempt=4,
            max_replans=3,
        )
        res = self.replanner.replan(req, plan, quest)
        self.assertFalse(res.success)
        self.assertIn("exceeds maximum allowed replans", res.error)

    def test_anti_oscillation_gate_blocks_duplicate_failed_step(self):
        """Anti-oscillation blocks replanning if identical step already failed previously."""
        quest = self.quest_engine.create_quest(title="test anti-oscillation", goal="test anti-oscillation", quest_id="q_osc")
        plan = Plan(
            quest_id="q_osc",
            goal="test anti-oscillation",
            steps=[PlanStep(step_id="s1", capability_id="web_search", intent="search", arguments={"query": "test query"})],
        )
        import hashlib, json
        args_hash = hashlib.sha256(json.dumps({"query": "test query"}, sort_keys=True).encode()).hexdigest()[:12]
        
        req = ReplanRequest(
            quest_id="q_osc",
            failed_step_id="s1",
            trigger=ReplanTrigger.STEP_FAILURE,
            error_message="network timed out",
            replan_attempt=2,
            max_replans=3,
            previous_failures=[
                {"step_id": "s1", "capability_id": "web_search", "args_hash": args_hash, "error": "network timed out"}
            ],
        )
        res = self.replanner.replan(req, plan, quest)
        self.assertFalse(res.success)
        self.assertIn("Anti-oscillation gate triggered", res.error)

    def test_replan_deterministic_fallback_replaces_capability_and_preserves_dependents(self):
        """Failed web_search is replaced by deep_research and downstream steps are rewired."""
        quest = self.quest_engine.create_quest(title="test fallback", goal="test fallback", quest_id="q_fallback")
        plan = Plan(
            quest_id="q_fallback",
            goal="search and report",
            steps=[
                PlanStep(step_id="step_1", capability_id="web_search", intent="search the web", arguments={"query": "python 3.12"}),
                PlanStep(step_id="step_2", capability_id="system_diagnostics", intent="check host", dependencies=["step_1"]),
            ],
        )
        req = ReplanRequest(
            quest_id="q_fallback",
            failed_step_id="step_1",
            trigger=ReplanTrigger.STEP_FAILURE,
            error_message="Search API rate limit exceeded",
            replan_attempt=1,
            max_replans=3,
        )
        res = self.replanner.replan(req, plan, quest)
        self.assertTrue(res.success, f"Replan failed: {res.error}")
        self.assertIsNotNone(res.revised_plan)
        revised = res.revised_plan
        self.assertEqual(revised.plan_version, 2)

        # Check replacement step was added
        step_ids = [s.step_id for s in revised.steps]
        self.assertIn("step_1_alt1", step_ids)
        self.assertNotIn("step_1", step_ids)

        # Verify fallback capability was selected
        alt_step = next(s for s in revised.steps if s.step_id == "step_1_alt1")
        self.assertEqual(alt_step.capability_id, "deep_research")

        # Verify downstream dependency was rewired to the replacement step
        downstream = next(s for s in revised.steps if s.step_id == "step_2")
        self.assertIn("step_1_alt1", downstream.dependencies)
        self.assertNotIn("step_1", downstream.dependencies)

    def test_replan_preserves_completed_steps(self):
        """Preserved step IDs retain their place in the revised plan without alteration."""
        quest = self.quest_engine.create_quest(title="test preservation", goal="test preservation", quest_id="q_pres")
        plan = Plan(
            quest_id="q_pres",
            goal="multi-step",
            steps=[
                PlanStep(step_id="step_1", capability_id="system_diagnostics", intent="step 1"),
                PlanStep(step_id="step_2", capability_id="web_search", intent="step 2", arguments={"query": "laya"}, dependencies=["step_1"]),
            ],
        )
        req = ReplanRequest(
            quest_id="q_pres",
            failed_step_id="step_2",
            trigger=ReplanTrigger.STEP_FAILURE,
            error_message="failed search",
            replan_attempt=1,
            max_replans=3,
            preserved_step_ids=["step_1"],
        )
        res = self.replanner.replan(req, plan, quest)
        self.assertTrue(res.success)
        self.assertIn("step_1", res.preserved_step_ids)
        revised_ids = [s.step_id for s in res.revised_plan.steps]
        self.assertIn("step_1", revised_ids)

    def test_replan_validation_firewall_blocks_invalid_graft(self):
        """If a replacement plan violates validator rules, replanning returns failure."""
        quest = self.quest_engine.create_quest(title="test validator", goal="test validator", quest_id="q_val")
        plan = Plan(
            quest_id="q_val",
            goal="test",
            steps=[PlanStep(step_id="step_1", capability_id="safe_math", intent="calc", arguments={"expression": "1+1"})],
        )
        req = ReplanRequest(
            quest_id="q_val",
            failed_step_id="step_1",
            trigger=ReplanTrigger.STEP_FAILURE,
            error_message="fail",
            replan_attempt=1,
            max_replans=3,
        )
        # Mock synthesis to return an invalid plan step with unknown capability
        with patch.object(self.replanner, "_synthesize_replacement_steps") as mock_synth:
            mock_synth.return_value = [
                PlanStep(step_id="step_1_alt1", capability_id="non_existent_capability_12345", intent="invalid")
            ]
            res = self.replanner.replan(req, plan, quest)
            self.assertFalse(res.success)
            self.assertIn("validation", res.error.lower())


class TestL16ExecutorIntegration(unittest.TestCase):
    """Integration test suite for DeterministicDAGExecutor with ControlledReplanner."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.quest_db = os.path.join(self.temp_dir, "test_quests.db")
        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)

        self.ledger_db = os.path.join(self.temp_dir, "test_ledger.db")
        self.ledger_store = OperationStore(self.ledger_db)
        self.ledger = OperationLedger(self.ledger_store)

        self.policy_store = PolicyStore(os.path.join(self.temp_dir, "policy.json"))
        self.policy_engine = PolicyEngine(self.policy_store)

        self.registry = build_real_capability_registry()
        self.validator = DeterministicPlanValidator(self.registry, allow_silent_failure=True)
        self.replanner = ControlledReplanner(
            capability_registry=self.registry,
            plan_validator=self.validator,
            max_replans=2,
        )

        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.ledger,
            plan_validator=self.validator,
            replanner=self.replanner,
            enable_replanning=True,
            max_replans=2,
        )

    def tearDown(self):
        self.quest_store.close()
        self.ledger_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_can_fail_silently_tolerates_step_failure(self):
        """A step marked can_fail_silently=True fails but is tolerated, allowing execution to reach AWAITING_VERIFICATION."""
        quest = self.quest_engine.create_quest(
            title="Test silent failure tolerance",
            goal="Test silent failure tolerance",
            quest_id="q_silent",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )

        # Step 1: fails but can_fail_silently=True
        # Step 2: succeeds independently
        plan = Plan(
            quest_id="q_silent",
            goal="Test silent failure",
            steps=[
                PlanStep(
                    step_id="step_fail_silent",
                    capability_id="safe_math",
                    intent="Failing silent step",
                    arguments={"expression": "1 / 0"},  # Triggers division by zero error
                    can_fail_silently=True,
                ),
                PlanStep(
                    step_id="step_success",
                    capability_id="system_diagnostics",
                    intent="Successful diagnostics",
                ),
            ],
        )

        summary = self.executor.execute(quest_id="q_silent", plan=plan)
        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(summary.completed_steps, 1)

    def test_executor_automatic_recovery_via_replanner(self):
        """When a step fails, the executor automatically invokes the replanner, splices the recovery step, and finishes successfully."""
        quest = self.quest_engine.create_quest(
            title="Test automatic recovery loop",
            goal="Test automatic recovery loop",
            quest_id="q_recovery",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )

        # Plan: Step 1 (web_search) fails -> Replanner replaces with deep_research -> finishes
        plan = Plan(
            quest_id="q_recovery",
            goal="Search and complete",
            steps=[
                PlanStep(
                    step_id="step_search",
                    capability_id="web_search",
                    intent="Search for information",
                    arguments={"query": "python"},
                ),
            ],
        )

        # Simulate web_search failing and deep_research succeeding via mock invoke
        original_invoke = self.registry.invoke

        def fake_invoke(cap_id, *args, **kwargs):
            if cap_id == "web_search":
                return ToolResult(
                    capability_id="web_search",
                    outcome=ToolOutcome.FAILURE,
                    error=ToolError(code=ErrorCode.TIMEOUT, message="Simulated connection timeout"),
                )
            elif cap_id == "deep_research":
                return ToolResult(
                    capability_id="deep_research",
                    outcome=ToolOutcome.SUCCESS,
                    data={"dossier": "Simulated deep research success"},
                )
            return original_invoke(cap_id, *args, **kwargs)

        with patch.object(self.registry, "invoke", side_effect=fake_invoke):
            summary = self.executor.execute(quest_id="q_recovery", plan=plan)

        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        updated_quest = self.quest_engine.get_quest("q_recovery")
        self.assertEqual(updated_quest.metadata.get("replan_count"), 1)

        # Verify new replacement step was recorded and completed
        step_ids = [s.step_id for s in updated_quest.steps]
        self.assertIn("step_search_alt1", step_ids)
        alt_step = next(s for s in updated_quest.steps if s.step_id == "step_search_alt1")
        self.assertEqual(alt_step.status, StepStatus.COMPLETED)

    def test_executor_exhausted_replans_halts_as_failed(self):
        """When replanning fails or exhausts max_replans, the Quest transitions to FAILED."""
        quest = self.quest_engine.create_quest(
            title="Test exhausted replans",
            goal="Test exhausted replans",
            quest_id="q_exhausted",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )

        # Step has no fallback capability and will fail
        plan = Plan(
            quest_id="q_exhausted",
            goal="Test exhausted replans",
            steps=[
                PlanStep(
                    step_id="step_fail",
                    capability_id="safe_math",
                    intent="Invalid division",
                    arguments={"expression": "1 / 0"},
                    can_fail_silently=False,
                ),
            ],
        )

        summary = self.executor.execute(quest_id="q_exhausted", plan=plan)
        self.assertEqual(summary.final_status, QuestStatus.FAILED)
        self.assertIn("failed", summary.error.lower())

    def test_replan_preserves_completed_mutations_without_reexecution(self):
        """Completed mutation steps are never re-executed upon replanning a subsequent failing step."""
        quest = self.quest_engine.create_quest(
            title="Test mutation preservation",
            goal="Test mutation preservation",
            quest_id="q_mut_pres",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )

        test_file = os.path.join(self.temp_dir, "preserved_mutation.txt")

        # Step 1: file_write (mutation)
        # Step 2: web_search (fails, triggers replan)
        plan = Plan(
            quest_id="q_mut_pres",
            goal="Write and search",
            steps=[
                PlanStep(
                    step_id="step_write",
                    capability_id="file_write",
                    intent="Write file",
                    arguments={"filepath": test_file, "content": "initial data"},
                ),
                PlanStep(
                    step_id="step_search",
                    capability_id="web_search",
                    intent="Search for data",
                    arguments={"query": "laya"},
                    dependencies=["step_write"],
                ),
            ],
        )

        # Simulate web_search failing and deep_research succeeding via mock invoke
        original_invoke = self.registry.invoke

        def fake_invoke(cap_id, *args, **kwargs):
            if cap_id == "web_search":
                return ToolResult(
                    capability_id="web_search",
                    outcome=ToolOutcome.FAILURE,
                    error=ToolError(code=ErrorCode.NETWORK_ERROR, message="Search failed"),
                )
            elif cap_id == "deep_research":
                return ToolResult(
                    capability_id="deep_research",
                    outcome=ToolOutcome.SUCCESS,
                    data={"data": "recovered"},
                )
            return original_invoke(cap_id, *args, **kwargs)

        with patch.object(self.registry, "invoke", side_effect=fake_invoke):
            summary = self.executor.execute(quest_id="q_mut_pres", plan=plan)

        self.assertEqual(summary.final_status, QuestStatus.AWAITING_VERIFICATION)
        
        # Verify file exists on disk from Step 1
        self.assertTrue(os.path.exists(test_file))
        with open(test_file, "r") as f:
            self.assertEqual(f.read(), "initial data")

        # Verify OperationRecord for step_write in ledger is COMMITTED with exactly 1 attempt
        op_id = f"op_q_mut_pres_step_write_file_write"
        op_rec = self.ledger.get_operation(op_id)
        self.assertIsNotNone(op_rec)
        self.assertEqual(op_rec.current_attempt, 1)


if __name__ == "__main__":
    unittest.main()
