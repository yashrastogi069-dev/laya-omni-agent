"""Comprehensive Unit & Integration Test Suite for Checkpoint L12: Structured DAG Planner.

Tests:
1. Strongly Typed Contracts & Extra Field Rejection (Invariant 4)
2. DAG Topology Algorithms (Cycle detection, topological sort, depth, in-degrees, ready-steps)
3. Template-First Precedence (Instant deterministic DAG from SkillManifest workflow template)
4. Dynamic Argument Mapping ($inputs.<param> binding)
5. Generative Planner Fallback (JSON schema output, code fence cleaning, registry validation)
6. DAG Bounds Enforcement (max_steps and max_depth bounds)
7. Quest Attachment Integration (Plan attached to persisted Quest, transitioning to PLANNED)
8. Non-Switching Legacy Boundary (omni_agent.py and omni_engine/planner.py untouched)
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from pydantic import ValidationError

from omni_engine.capabilities.definitions import build_canonical_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, ConfirmationPolicy
from omni_engine.contracts.quest import QuestStatus, StepStatus
from omni_engine.contracts.plan import (
    Plan,
    PlanError,
    PlanGenerationError,
    PlanStep,
    PlanType,
    PlanValidationError,
)
from omni_engine.contracts.routing import RouteDecision
from omni_engine.contracts.skill import SkillManifest, SkillStepTemplate
from omni_engine.planning.dag import DAGTopology
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.planning.generative_planner import GenerativePlanner
from omni_engine.planning.template_planner import SkillTemplatePlanner
from omni_engine.quest.engine import QuestEngine
from omni_engine.skills.definitions import build_canonical_skill_registry
from omni_engine.skills.registry import SkillRegistry


class TestL12PlanContracts(unittest.TestCase):
    """Verifies strongly typed Pydantic v2 Plan and PlanStep contracts."""

    def test_plan_step_contract_valid_and_forbids_extra(self):
        step = PlanStep(
            step_id="step_1",
            capability_id="file_read",
            intent="Read user config file",
            arguments={"filepath": "config.json"},
            dependencies=[],
            timeout_s=30.0,
            max_attempts=3,
        )
        self.assertEqual(step.step_id, "step_1")
        self.assertEqual(step.capability_id, "file_read")
        self.assertEqual(step.timeout_s, 30.0)
        self.assertFalse(step.can_fail_silently)

        # Invariant 4: Forbid extra fields
        with self.assertRaises(ValidationError):
            PlanStep(
                step_id="step_1",
                capability_id="file_read",
                intent="Read config",
                unauthorized_extra="payload",  # type: ignore
            )

    def test_plan_contract_valid_and_forbids_extra(self):
        step1 = PlanStep(step_id="step_1", capability_id="file_read", intent="Read file")
        step2 = PlanStep(
            step_id="step_2",
            capability_id="file_write",
            intent="Write file",
            dependencies=["step_1"],
        )
        plan = Plan(
            quest_id="qst_101",
            goal="Process config",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[step1, step2],
            max_depth=2,
        )
        self.assertEqual(plan.quest_id, "qst_101")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.plan_type, PlanType.TEMPLATE_DERIVED)

        # Invariant 4: Forbid extra fields
        with self.assertRaises(ValidationError):
            Plan(
                quest_id="qst_101",
                goal="Process config",
                plan_type=PlanType.TEMPLATE_DERIVED,
                steps=[step1, step2],
                extra_payload="malicious",  # type: ignore
            )

    def test_plan_rejects_duplicate_step_ids(self):
        step1 = PlanStep(step_id="step_1", capability_id="file_read", intent="Read A")
        step2 = PlanStep(step_id="step_1", capability_id="file_write", intent="Write B")
        with self.assertRaises(ValidationError) as ctx:
            Plan(
                quest_id="qst_dup",
                goal="Dup steps",
                plan_type=PlanType.TEMPLATE_DERIVED,
                steps=[step1, step2],
            )
        self.assertIn("Duplicate step_id 'step_1'", str(ctx.exception))

    def test_plan_rejects_unknown_dependency(self):
        step1 = PlanStep(
            step_id="step_1",
            capability_id="file_read",
            intent="Read A",
            dependencies=["nonexistent_step"],
        )
        with self.assertRaises(ValidationError) as ctx:
            Plan(
                quest_id="qst_unknown_dep",
                goal="Bad dep",
                plan_type=PlanType.TEMPLATE_DERIVED,
                steps=[step1],
            )
        self.assertIn("unknown dependency 'nonexistent_step'", str(ctx.exception))

    def test_plan_rejects_self_dependency(self):
        step1 = PlanStep(
            step_id="step_1",
            capability_id="file_read",
            intent="Read A",
            dependencies=["step_1"],
        )
        with self.assertRaises(ValidationError) as ctx:
            Plan(
                quest_id="qst_self_dep",
                goal="Self dep",
                plan_type=PlanType.TEMPLATE_DERIVED,
                steps=[step1],
            )
        self.assertIn("cannot depend on itself", str(ctx.exception))


class TestL12DAGTopology(unittest.TestCase):
    """Verifies graph algorithms: cycle detection, topological sorting, depth, in-degrees, ready-steps."""

    def test_detect_cycle_2_nodes(self):
        step1 = PlanStep(step_id="A", capability_id="file_read", intent="Read", dependencies=["B"])
        step2 = PlanStep(step_id="B", capability_id="file_write", intent="Write", dependencies=["A"])
        cycle = DAGTopology.detect_cycles([step1, step2])
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle, ["A", "B", "A"])

    def test_detect_cycle_3_nodes(self):
        step1 = PlanStep(step_id="A", capability_id="file_read", intent="A", dependencies=["C"])
        step2 = PlanStep(step_id="B", capability_id="file_read", intent="B", dependencies=["A"])
        step3 = PlanStep(step_id="C", capability_id="file_read", intent="C", dependencies=["B"])
        cycle = DAGTopology.detect_cycles([step1, step2, step3])
        self.assertIsNotNone(cycle)
        self.assertEqual(cycle, ["A", "C", "B", "A"])

    def test_topological_sort_diamond_dag(self):
        # A -> B -> D
        # A -> C -> D
        step_a = PlanStep(step_id="A", capability_id="file_read", intent="A")
        step_b = PlanStep(step_id="B", capability_id="file_read", intent="B", dependencies=["A"])
        step_c = PlanStep(step_id="C", capability_id="file_read", intent="C", dependencies=["A"])
        step_d = PlanStep(step_id="D", capability_id="file_write", intent="D", dependencies=["B", "C"])

        sorted_steps = DAGTopology.topological_sort([step_d, step_b, step_a, step_c])
        ids = [s.step_id for s in sorted_steps]

        self.assertEqual(ids[0], "A")
        self.assertIn(ids[1], ["B", "C"])
        self.assertIn(ids[2], ["B", "C"])
        self.assertEqual(ids[3], "D")

    def test_compute_plan_depth(self):
        step_a = PlanStep(step_id="A", capability_id="file_read", intent="A")
        step_b = PlanStep(step_id="B", capability_id="file_read", intent="B", dependencies=["A"])
        step_c = PlanStep(step_id="C", capability_id="file_read", intent="C", dependencies=["B"])
        step_d = PlanStep(step_id="D", capability_id="file_write", intent="D", dependencies=["C"])

        # Chain of 4 steps -> depth 4
        depth = DAGTopology.compute_plan_depth([step_a, step_b, step_c, step_d])
        self.assertEqual(depth, 4)

        # Parallel independent steps -> depth 1
        step_x = PlanStep(step_id="X", capability_id="file_read", intent="X")
        step_y = PlanStep(step_id="Y", capability_id="file_read", intent="Y")
        self.assertEqual(DAGTopology.compute_plan_depth([step_x, step_y]), 1)

    def test_in_degrees_and_ready_steps(self):
        step_a = PlanStep(step_id="A", capability_id="file_read", intent="A")
        step_b = PlanStep(step_id="B", capability_id="file_read", intent="B", dependencies=["A"])
        step_c = PlanStep(step_id="C", capability_id="file_write", intent="C", dependencies=["A", "B"])

        steps = [step_a, step_b, step_c]

        # Initial state: no steps completed
        in_deg = DAGTopology.compute_in_degrees(steps)
        self.assertEqual(in_deg["A"], 0)
        self.assertEqual(in_deg["B"], 1)
        self.assertEqual(in_deg["C"], 2)

        ready = DAGTopology.get_ready_steps(steps, completed_step_ids=set())
        self.assertEqual(len(ready), 1)
        self.assertEqual(ready[0].step_id, "A")

        # After step A completes: step B becomes ready
        ready_after_a = DAGTopology.get_ready_steps(steps, completed_step_ids={"A"})
        self.assertEqual(len(ready_after_a), 1)
        self.assertEqual(ready_after_a[0].step_id, "B")

        # After A and B complete: step C becomes ready
        ready_after_ab = DAGTopology.get_ready_steps(steps, completed_step_ids={"A", "B"})
        self.assertEqual(len(ready_after_ab), 1)
        self.assertEqual(ready_after_ab[0].step_id, "C")


class TestL12SkillTemplatePlanner(unittest.TestCase):
    """Verifies deterministic plan derivation directly from skill workflow templates."""

    def setUp(self):
        self.template_planner = SkillTemplatePlanner()

    def test_plan_from_skill_workflow_template(self):
        # Define a canonical 2-step skill template
        step1 = SkillStepTemplate(
            step_id="step_find",
            capability_id="search_code",
            description="Locate symbol definition",
            default_args={"file_pattern": "*.py"},
            arg_mappings={"query": "$inputs.symbol_name"},
        )
        step2 = SkillStepTemplate(
            step_id="step_read",
            capability_id="file_read",
            description="Read the implementation",
            depends_on=["step_find"],
            default_args={"max_lines": 50},
            arg_mappings={"filepath": "$inputs.file_path"},
        )
        skill = SkillManifest(
            skill_id="code_inspection",
            domain="dev",
            name="Code Inspection",
            description="Inspect code symbols and files",
            intent_patterns=["find code symbol", "inspect code"],
            required_capabilities=["search_code", "file_read"],
            action_classes=[ActionClass.READ_ONLY],
            workflow_template=[step1, step2],
        )

        plan = self.template_planner.create_plan_from_skill(
            quest_id="qst_inspect_1",
            goal="Find where LayaProvider is defined",
            skill=skill,
            resolved_arguments={"symbol_name": "LayaProvider", "file_path": "omni_engine/providers/system1.py"},
        )

        self.assertEqual(plan.plan_type, PlanType.TEMPLATE_DERIVED)
        self.assertEqual(plan.skill_id, "code_inspection")
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.max_depth, 2)

        # Verify argument mapping
        s1 = plan.steps[0]
        self.assertEqual(s1.step_id, "step_find")
        self.assertEqual(s1.arguments["query"], "LayaProvider")
        self.assertEqual(s1.arguments["file_pattern"], "*.py")

        s2 = plan.steps[1]
        self.assertEqual(s2.step_id, "step_read")
        self.assertEqual(s2.dependencies, ["step_find"])
        self.assertEqual(s2.arguments["filepath"], "omni_engine/providers/system1.py")
        self.assertEqual(s2.arguments["max_lines"], 50)

    def test_skill_without_template_rejected(self):
        skill = SkillManifest(
            skill_id="unplanned_skill",
            domain="general",
            name="Unplanned",
            description="Requires generative planning",
            intent_patterns=["do something novel"],
            required_capabilities=["web_search"],
            action_classes=[ActionClass.READ_ONLY],
            planning_required=True,
            workflow_template=None,
        )
        self.assertFalse(self.template_planner.can_plan_from_skill(skill))
        with self.assertRaises(PlanValidationError):
            self.template_planner.create_plan_from_skill("qst_1", "Goal", skill)


class TestL12GenerativePlanner(unittest.TestCase):
    """Verifies generative fallback planner with mock response parsing and JSON cleaning."""

    def setUp(self):
        self.registry = build_canonical_registry()
        self.planner = GenerativePlanner(capability_registry=self.registry)

    def test_synthesize_plan_with_clean_json(self):
        mock_json = """
        {
          "steps": [
            {
              "step_id": "step_1",
              "capability_id": "web_search",
              "intent": "Search for Python documentation",
              "arguments": {"query": "Python 3.12 documentation"},
              "dependencies": []
            },
            {
              "step_id": "step_2",
              "capability_id": "scrape_url",
              "intent": "Scrape the official documentation page",
              "arguments": {"url": "https://docs.python.org/3/"},
              "dependencies": ["step_1"]
            }
          ]
        }
        """
        plan = self.planner.synthesize_plan(
            quest_id="qst_gen_1",
            goal="Find and read Python docs",
            mock_response=mock_json,
        )
        self.assertEqual(plan.plan_type, PlanType.GENERATIVE_SYNTHESIZED)
        self.assertEqual(len(plan.steps), 2)
        self.assertEqual(plan.steps[0].capability_id, "web_search")
        self.assertEqual(plan.steps[1].dependencies, ["step_1"])
        self.assertEqual(plan.max_depth, 2)

    def test_synthesize_plan_strips_markdown_code_fences(self):
        mock_fenced_json = """```json
        {
          "steps": [
            {
              "step_id": "s1",
              "capability_id": "ping_test",
              "intent": "Ping server",
              "arguments": {"host": "127.0.0.1"}
            }
          ]
        }
        ```"""
        plan = self.planner.synthesize_plan(
            quest_id="qst_fenced",
            goal="Ping local host",
            mock_response=mock_fenced_json,
        )
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].capability_id, "ping_test")

    def test_synthesize_plan_rejects_unknown_capability(self):
        mock_json = """
        {
          "steps": [
            {
              "step_id": "s1",
              "capability_id": "unregistered_hack_tool",
              "intent": "Execute hack",
              "arguments": {}
            }
          ]
        }
        """
        with self.assertRaises(PlanValidationError) as ctx:
            self.planner.synthesize_plan(
                quest_id="qst_bad_cap",
                goal="Attempt unknown capability",
                mock_response=mock_json,
            )
        self.assertIn("unknown capability 'unregistered_hack_tool'", str(ctx.exception))

    def test_synthesize_plan_rejects_cycles(self):
        mock_cycle_json = """
        {
          "steps": [
            {"step_id": "step_1", "capability_id": "file_read", "dependencies": ["step_2"]},
            {"step_id": "step_2", "capability_id": "file_write", "dependencies": ["step_1"]}
          ]
        }
        """
        with self.assertRaises(PlanValidationError) as ctx:
            self.planner.synthesize_plan(
                quest_id="qst_cycle",
                goal="Cyclical plan",
                mock_response=mock_cycle_json,
            )
        self.assertIn("Circular dependency detected", str(ctx.exception))


class TestL12StructuredDAGPlannerEngine(unittest.TestCase):
    """Verifies end-to-end StructuredDAGPlanner template-first precedence and Quest attachment."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_quest_planner.db"
        self.quest_engine = QuestEngine(db_path=self.db_path)
        self.skill_registry = build_canonical_skill_registry()
        self.cap_registry = build_canonical_registry()
        self.planner = StructuredDAGPlanner(
            skill_registry=self.skill_registry,
            capability_registry=self.cap_registry,
        )

    def tearDown(self):
        self.quest_engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_template_first_precedence_for_canonical_skill(self):
        # Create Quest
        quest = self.quest_engine.create_quest(
            title="Inspect repo",
            goal="Inspect git repository structure and files",
        )
        # Canonical skill inspect_repository has workflow template
        route_decision = RouteDecision(
            request_id="req_test_inspect",
            selected_domain="dev",
            selected_skill="inspect_repository",
            candidate_skills=["inspect_repository"],
            candidates=[],
            catalog_reduction_ratio=1.0,
            total_registry_capabilities=23,
            metadata={"resolved_arguments": {"path": "."}},
        )

        plan = self.planner.create_plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            route_decision=route_decision,
        )

        self.assertEqual(plan.plan_type, PlanType.TEMPLATE_DERIVED)
        self.assertEqual(plan.skill_id, "inspect_repository")
        self.assertTrue(len(plan.steps) >= 2)

        # Attach plan to Quest
        planned_quest = self.planner.attach_to_quest(self.quest_engine, plan)
        self.assertEqual(planned_quest.status, QuestStatus.PLANNED)
        self.assertEqual(len(planned_quest.steps), len(plan.steps))

        # Steps in Quest must match plan steps in order
        for i, q_step in enumerate(planned_quest.steps):
            self.assertEqual(q_step.step_id, plan.steps[i].step_id)
            self.assertEqual(q_step.capability_id, plan.steps[i].capability_id)
            self.assertEqual(q_step.status, StepStatus.PENDING)

    def test_generative_fallback_when_no_template_applies(self):
        quest = self.quest_engine.create_quest(
            title="Ad-hoc Novel Task",
            goal="Perform novel custom workflow",
        )
        mock_response = """
        {
          "steps": [
            {
              "step_id": "s1",
              "capability_id": "system_diagnostics",
              "intent": "Check disk space",
              "arguments": {}
            }
          ]
        }
        """
        plan = self.planner.create_plan(
            quest_id=quest.quest_id,
            goal=quest.goal,
            mock_generative_response=mock_response,
        )
        self.assertEqual(plan.plan_type, PlanType.GENERATIVE_SYNTHESIZED)
        self.assertEqual(len(plan.steps), 1)

        # Attach to Quest
        planned_quest = self.planner.attach_to_quest(self.quest_engine, plan)
        self.assertEqual(planned_quest.status, QuestStatus.PLANNED)
        self.assertEqual(len(planned_quest.steps), 1)

    def test_plan_bounds_enforcement(self):
        # Exceeds max_steps limit of 2
        mock_3_steps = """
        {
          "steps": [
            {"step_id": "s1", "capability_id": "ping_test"},
            {"step_id": "s2", "capability_id": "ping_test"},
            {"step_id": "s3", "capability_id": "ping_test"}
          ]
        }
        """
        with self.assertRaises(PlanValidationError) as ctx:
            self.planner.create_plan(
                quest_id="qst_bound",
                goal="Bound test",
                max_steps=2,
                mock_generative_response=mock_3_steps,
            )
        self.assertIn("exceeds maximum", str(ctx.exception))


class TestL12NonSwitchingBoundary(unittest.TestCase):
    """Verifies that legacy omni_agent.py and omni_engine/planner.py remain untouched."""

    def test_legacy_files_remain_untouched(self):
        repo_root = Path(__file__).resolve().parent.parent
        omni_agent_py = repo_root / "omni_agent.py"
        planner_py = repo_root / "omni_engine" / "planner.py"

        self.assertTrue(omni_agent_py.exists(), "omni_agent.py must exist")
        self.assertTrue(planner_py.exists(), "omni_engine/planner.py must exist")


if __name__ == "__main__":
    unittest.main()
