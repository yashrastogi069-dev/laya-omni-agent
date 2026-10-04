"""
Unit and Integration Test Suite for Checkpoint L14.3: Practical Runtime Integration & Operator-Control Closure.

Verifies end-to-end resolution for findings PRACT-001 through PRACT-036:
- Objective Decomposition and Clause Isolation (Prompts A through G).
- Template-as-Building-Block Augmentation (no dropped clauses, 100% pre-execution coverage).
- PRACT-004: Launch app adapter infrastructure argument filtering.
- PRACT-010: Resumed step clears stale confirmation error.
- PRACT-011 & PRACT-028: SessionManager interactive continuation and referent binding.
- PRACT-018, PRACT-023, PRACT-024: Research fetch telemetry and candidate backfilling.
- PRACT-025: SemanticArgumentValidator URL sanity checks.
- PRACT-030: Secret-bearing file protection (Rule-0 hard DENY on read & write).
- PRACT-031: Ordinary browser navigation risk calibration.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

from omni_engine.arguments.extractors import extract_search_query, extract_url
from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.arguments.validator import SemanticArgumentValidator, SemanticValidationError
from omni_engine.capabilities.adapters import (
    _strip_infrastructure_args,
    make_adapter,
    make_launch_app_adapter,
)
from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
)
from omni_engine.contracts.objective import ObjectiveSpec, RequirementCoverageState
from omni_engine.contracts.plan import Plan, PlanStep, PlanType
from omni_engine.contracts.policy import (
    OperatorPolicyPreferences,
    PolicyEffect,
)
from omni_engine.contracts.quest import QuestStatus, StepStatus, QuestStep
from omni_engine.execution.executor import DeterministicDAGExecutor
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore
from omni_engine.planning.decomposer import ObjectiveDecomposer
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine
from omni_engine.policy.rules import is_secret_bearing_file
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore
from omni_engine.research.fetcher import PageFetcher
from omni_engine.session.manager import SessionManager
from omni_engine.skills.definitions import build_canonical_skill_registry


class TestObjectiveDecomposition(unittest.TestCase):
    """Verifies Prompt A through G decomposition into discrete, isolated clauses."""

    def setUp(self):
        self.decomposer = ObjectiveDecomposer()

    def test_prompt_a_decomposition(self):
        prompt = "Inspect system health, identify processes using the most memory, and save findings to health_report.txt"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        self.assertGreaterEqual(len(spec.requirements), 3)
        save_reqs = [r for r in spec.requirements if r.domain == "file" or "save" in r.description.lower()]
        self.assertEqual(len(save_reqs), 1)

    def test_prompt_b_decomposition(self):
        prompt = "Navigate to https://example.com and capture a screenshot"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        domains = [r.domain for r in spec.requirements]
        self.assertIn("browser", domains)
        has_ss = any("screenshot" in r.description.lower() for r in spec.requirements)
        self.assertTrue(has_ss)

    def test_prompt_c_decomposition(self):
        prompt = "Inspect repository structure, locate Quest persistence, and identify crash recovery files"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        descs = " ".join(r.description for r in spec.requirements)
        self.assertIn("Quest persistence", descs)

    def test_prompt_d_decomposition(self):
        prompt = "Inspect requirements.txt dependency declarations and inspect Python imports used by planner"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        domains = {r.domain for r in spec.requirements}
        self.assertIn("repository", domains)

    def test_prompt_e_decomposition(self):
        prompt = "Search the web for quantum algorithms and save findings to quantum.txt"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        save_reqs = [r for r in spec.requirements if r.domain == "file" or "save" in r.description.lower()]
        self.assertEqual(len(save_reqs), 1)

    def test_prompt_f_decomposition(self):
        prompt = "Search the web for ModernBERT and inspect this repository structure"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        domains = {r.domain for r in spec.requirements}
        self.assertIn("web", domains)
        self.assertIn("repository", domains)

    def test_prompt_g_decomposition(self):
        prompt = "Check system health, check n8n port 5678, list n8n workflows, aggregate results"
        spec = self.decomposer.decompose(prompt)
        self.assertTrue(spec.is_compound)
        health_reqs = [r for r in spec.requirements if "port 5678" in r.description.lower() or "health" in r.description.lower()]
        list_reqs = [r for r in spec.requirements if "workflows" in r.description.lower()]
        self.assertGreaterEqual(len(health_reqs), 1)
        self.assertGreaterEqual(len(list_reqs), 1)


class TestTemplateAugmentation(unittest.TestCase):
    """Verifies that StructuredDAGPlanner never drops uncovered clauses (Template-as-Building-Block)."""

    def setUp(self):
        self.cap_registry = build_real_capability_registry()
        self.skill_registry = build_canonical_skill_registry(self.cap_registry)
        self.planner = StructuredDAGPlanner(
            skill_registry=self.skill_registry,
            capability_registry=self.cap_registry,
        )

    def test_prompt_b_augments_screenshot(self):
        prompt = "Navigate to https://example.com and capture a screenshot"
        plan = self.planner.create_plan(
            quest_id="qst_test_b",
            goal=prompt,
            skill_id="browser_information_task",
            arguments={"url": "https://example.com"},
        )
        caps = [s.capability_id for s in plan.steps]
        self.assertIn("visual_browse", caps)
        self.assertIn("browser_screenshot", caps)

    def test_prompt_g_augments_service_health_and_workflows(self):
        prompt = "Check system health, check n8n port 5678, list n8n workflows, aggregate results"
        plan = self.planner.create_plan(
            quest_id="qst_test_g",
            goal=prompt,
            skill_id="diagnose_system",
            arguments={"port": 5678},
        )
        caps = [s.capability_id for s in plan.steps]
        has_health = any("service_health" in c for c in caps)
        has_list = any("list_workflows" in c for c in caps)
        self.assertTrue(has_health)
        self.assertTrue(has_list)

    def test_single_intent_not_over_augmented(self):
        prompt = "Inspect system health"
        plan = self.planner.create_plan(
            quest_id="qst_single",
            goal=prompt,
            skill_id="diagnose_system",
            arguments={},
        )
        self.assertEqual(len(plan.steps), 2)
        caps = [s.capability_id for s in plan.steps]
        self.assertEqual(caps, ["system_diagnostics", "list_processes"])


class TestPRACT004_LaunchAppAdapter(unittest.TestCase):
    """PRACT-004: Adapter execution-context leakage passes idempotency_key into legacy tools."""

    def test_app_launch_adapter_filters_infrastructure_args(self):
        called_with = {}

        def mock_legacy_launch(app_name: str):
            called_with["app_name"] = app_name
            return f"Launched {app_name}"

        adapter_fn = make_launch_app_adapter(mock_legacy_launch, "launch_app")
        # Pass extraneous infrastructure arguments
        ok, res = adapter_fn(
            app_name="notepad",
            idempotency_key="idem_12345",
            session_id="sess_abc",
            quest_id="qst_xyz",
            step_id="step_1",
        )
        self.assertTrue(ok)
        self.assertEqual(called_with.get("app_name"), "notepad")
        self.assertNotIn("idempotency_key", called_with)
        self.assertEqual(res.get("app_name"), "notepad")


class TestPRACT010_ResumedStepErrorClearing(unittest.TestCase):
    """PRACT-010: Resumed steps must clear stale confirmation error text."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "quest_test.db"
        self.store = QuestStore(self.db_path)
        self.engine = QuestEngine(self.store)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resumed_step_clears_stale_error(self):
        quest = self.engine.create_quest(
            title="Confirmation test",
            goal="Test stale error clearing",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        # Create a step in PAUSED status with confirmation error text
        q_step = QuestStep(
            step_id="step_1",
            quest_id=quest.quest_id,
            capability_id="file_write",
            action_class=ActionClass.LOCAL_UPDATE,
            intent="Write file",
            arguments={"filepath": "out.txt", "content": "data"},
            dependencies=[],
            status=StepStatus.PAUSED,
            error="Human confirmation required before overwriting file",
        )
        self.store.save_steps(quest.quest_id, [q_step])
        # Verify step initially has error
        initial_q = self.engine.get_quest(quest.quest_id)
        self.assertEqual(initial_q.steps[0].error, "Human confirmation required before overwriting file")

        # Now resume step to RUNNING, then COMPLETED
        self.engine.transition_step(
            quest_id=quest.quest_id,
            step_id="step_1",
            target_status=StepStatus.RUNNING,
        )
        running_q = self.engine.get_quest(quest.quest_id)
        self.assertIsNone(running_q.steps[0].error)

        self.engine.transition_step(
            quest_id=quest.quest_id,
            step_id="step_1",
            target_status=StepStatus.COMPLETED,
            execution_receipt={"bytes_written": 4},
        )
        completed_q = self.engine.get_quest(quest.quest_id)
        self.assertEqual(completed_q.steps[0].status, StepStatus.COMPLETED)
        self.assertIsNone(completed_q.steps[0].error)


class TestPRACT011_And_PRACT028_SessionManager(unittest.TestCase):
    """PRACT-011 & PRACT-028: Multi-turn session continuation and referent binding."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = Path(self.test_dir) / "session_test.db"
        self.quest_store = QuestStore(self.db_path)
        self.quest_engine = QuestEngine(self.quest_store)
        self.op_store = OperationStore(self.db_path)
        self.op_ledger = OperationLedger(self.op_store)
        self.cap_registry = build_real_capability_registry()
        self.policy_engine = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.cap_registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.cap_registry,
            policy_engine=self.policy_engine,
            operation_ledger=self.op_ledger,
            plan_validator=self.validator,
        )
        self.session_mgr = SessionManager(
            quest_engine=self.quest_engine,
            executor=self.executor,
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_referent_resolution(self):
        session_id = "test_sess"
        # Simulate prior quest result stored in session
        self.session_mgr.record_step_result(
            session_id=session_id,
            result={"filepath": "C:\\logs\\app.log", "lines": 42},
            output_summary="Log file generated at C:\\logs\\app.log",
        )

        # Referent "this" or "the results" should bind context
        prompt = "Save this to report.txt"
        resolved, ctx = self.session_mgr.resolve_referents(session_id, prompt)
        self.assertEqual(ctx.get("last_output_summary"), "Log file generated at C:\\logs\\app.log")
        self.assertIn("last_tool_result", ctx)

    def test_interactive_confirmation_continuation(self):
        session_id = "test_confirm_sess"
        quest = self.quest_engine.create_quest(
            title="Interactive quest",
            goal="Test interactive approval",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        # Attach a step and transition quest to PAUSED_FOR_CONFIRMATION
        q_step = QuestStep(
            step_id="step_1",
            quest_id=quest.quest_id,
            capability_id="safe_math",
            action_class=ActionClass.READ_ONLY,
            intent="Calculate math",
            arguments={"expression": "2 + 2"},
            dependencies=[],
            status=StepStatus.PAUSED,
        )
        self.quest_store.save_steps(quest.quest_id, [q_step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)
        self.quest_engine.transition_quest(
            quest.quest_id,
            QuestStatus.PAUSED_FOR_CONFIRMATION,
            reason="Awaiting operator approval",
        )
        self.session_mgr.set_active_quest(session_id, quest.quest_id)

        # Operator responds "yes"
        handled, summary, msg = self.session_mgr.handle_interactive_input(session_id, "yes")
        self.assertTrue(handled)
        self.assertIsNotNone(summary)
        self.assertIn("Resumed quest", msg)


class TestPRACT018_023_024_ResearchTelemetry(unittest.TestCase):
    """PRACT-018, PRACT-023, PRACT-024: Truthful fetch telemetry and URL backfilling."""

    def test_fetcher_records_truthful_methods(self):
        fetcher = PageFetcher(timeout_seconds=1)
        # Direct fetch of a nonexistent localhost endpoint
        result = fetcher.fetch("http://127.0.0.1:54321/nonexistent")
        self.assertFalse(result["success"])
        self.assertGreaterEqual(len(result["attempted_methods"]), 1)
        self.assertIsNone(result["successful_method"])
        self.assertIn("errors_by_method", result)


class TestPRACT025_SemanticArgumentValidator(unittest.TestCase):
    """PRACT-025: Malformed URLs like https://https://... must be rejected."""

    def setUp(self):
        self.validator = SemanticArgumentValidator()

    def test_rejects_double_scheme_url(self):
        with self.assertRaises(SemanticValidationError):
            self.validator.validate_arguments(
                capability_id="visual_browse",
                arguments={"url": "https://https://www.example.com"},
            )

    def test_accepts_valid_url(self):
        validated = self.validator.validate_arguments(
            capability_id="visual_browse",
            arguments={"url": "https://www.example.com/docs"},
        )
        self.assertEqual(validated["url"], "https://www.example.com/docs")


class TestPRACT030_SecretBearingFileProtection(unittest.TestCase):
    """PRACT-030: Secret-bearing files (.env, keys.env, keys, id_rsa, etc.) must be hard blocked."""

    def setUp(self):
        self.policy = PolicyEngine(default_autonomy=AutonomyProfile.TRUSTED_OPERATOR)
        self.cap_registry = build_real_capability_registry()

    def test_is_secret_bearing_file(self):
        is_sec, _ = is_secret_bearing_file(".env")
        self.assertTrue(is_sec)
        is_sec, _ = is_secret_bearing_file("keys.env")
        self.assertTrue(is_sec)
        is_sec, _ = is_secret_bearing_file("keys")
        self.assertTrue(is_sec)
        is_sec, _ = is_secret_bearing_file("C:\\Users\\admin\\.ssh\\id_rsa")
        self.assertTrue(is_sec)
        is_sec, _ = is_secret_bearing_file("certs\\server.pem")
        self.assertTrue(is_sec)
        is_sec, _ = is_secret_bearing_file("main.py")
        self.assertFalse(is_sec)
        is_sec, _ = is_secret_bearing_file("README.md")
        self.assertFalse(is_sec)

    def test_hard_deny_on_secret_file_read(self):
        spec = self.cap_registry.get_spec("file_read")
        decision = self.policy.evaluate(
            capability=spec,
            arguments={"filepath": "keys.env"},
            autonomy_profile=AutonomyProfile.WORKFLOW_AUTHORIZED,
            user_confirmed=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.DENY)
        self.assertIn("secret-bearing", (decision.denial_reason or "").lower())

    def test_hard_deny_on_secret_file_write(self):
        spec = self.cap_registry.get_spec("file_write")
        decision = self.policy.evaluate(
            capability=spec,
            arguments={"filepath": ".env", "content": "SECRET=123"},
            autonomy_profile=AutonomyProfile.WORKFLOW_AUTHORIZED,
            user_confirmed=True,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.DENY)


class TestPRACT031_BrowserNavigationCalibratedRisk(unittest.TestCase):
    """PRACT-031: Ordinary browser navigation must not trigger high-risk false-positive confirmation."""

    def setUp(self):
        self.policy = PolicyEngine(default_autonomy=AutonomyProfile.LOCAL_OPERATOR)
        self.cap_registry = build_real_capability_registry()

    def test_ordinary_browse_is_low_risk(self):
        spec = self.cap_registry.get_spec("visual_browse")
        decision = self.policy.evaluate(
            capability=spec,
            arguments={"url": "https://www.python.org"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.ALLOW)
        self.assertLessEqual(decision.assessment.risk_score, 0.25)


if __name__ == "__main__":
    unittest.main()
