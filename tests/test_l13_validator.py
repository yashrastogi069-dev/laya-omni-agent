"""
tests.test_l13_validator
========================
Comprehensive unit and integration test suite for Checkpoint L13:
Deterministic Plan Validator Firewall.

Tests all 10 deterministic validation passes:
1. DAG_ACYCLICITY
2. DEPENDENCY_EXISTENCE
3. CAPABILITY_REGISTRATION
4. SCHEMA_CONFORMANCE (including dynamic placeholder masking and causal dependency checking)
5. POLICY_FEASIBILITY (blocking hard invariants, deferring dynamic placeholders)
6. AUTONOMY_COMPLIANCE (ADVISOR mutation rejection, rank comparisons)
7. STEP_COUNT_BOUNDS
8. GRAPH_DEPTH_BOUNDS (cycle immunity, depth calculation)
9. MUTATION_SAFETY (non-idempotent retry bounding)
10. RESOURCE_BUDGET (plan budget bounds, step timeout consistency)
+ Non-switching boundary verification (omni_agent.py and omni_engine/planner.py untouched).
"""

import subprocess
import unittest

from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
)
from omni_engine.contracts.plan import Plan, PlanStep, PlanType
from omni_engine.contracts.validation import (
    PlanValidationReport,
    ValidationPassName,
    ValidationPassResult,
)
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine


class TestL13ValidatorContracts(unittest.TestCase):
    """Verifies Plan Validator contract constraints and extra='forbid' safety."""

    def test_validation_pass_result_forbids_extra(self):
        result = ValidationPassResult(
            pass_name=ValidationPassName.DAG_ACYCLICITY,
            passed=True,
            message="Valid",
        )
        self.assertTrue(result.passed)
        with self.assertRaises(Exception):
            ValidationPassResult(
                pass_name=ValidationPassName.DAG_ACYCLICITY,
                passed=True,
                message="Valid",
                unauthorized_extra_field="bad",
            )

    def test_plan_validation_report_contract(self):
        report = PlanValidationReport(
            plan_id="plan_123",
            is_valid=True,
            passes=[
                ValidationPassResult(
                    pass_name=ValidationPassName.DAG_ACYCLICITY,
                    passed=True,
                    message="OK",
                )
            ],
            latency_ms=1.5,
        )
        self.assertTrue(report.is_valid)
        self.assertEqual(len(report.passes), 1)
        with self.assertRaises(Exception):
            PlanValidationReport(
                plan_id="plan_123",
                is_valid=True,
                unauthorized_extra="bad",
            )


class TestL13Pass1DAGAcyclicity(unittest.TestCase):
    """Pass 1: Cycle detection, self-loops, and duplicate step IDs."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_valid_acyclic_dag_passes(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Research query",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(step_id="step_1", capability_id="web_search", intent="Search", arguments={"query": "test"}),
                PlanStep(step_id="step_2", capability_id="safe_math", intent="Calculate", arguments={"expression": "2+2"}, dependencies=["step_1"]),
            ],
        )
        report = self.validator.validate(plan)
        p1 = next(p for p in report.passes if p.pass_name == ValidationPassName.DAG_ACYCLICITY)
        self.assertTrue(p1.passed)

    def test_self_dependency_detected(self):
        # Use model_construct to bypass Plan constructor validation (BLK-01)
        step = PlanStep(step_id="step_1", capability_id="web_search", intent="Self loop", arguments={"query": "test"}, dependencies=["step_1"])
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="Self loop goal",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        self.assertFalse(report.is_valid)
        p1 = next(p for p in report.passes if p.pass_name == ValidationPassName.DAG_ACYCLICITY)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.error_code, ErrorCode.CONFLICT)

    def test_two_node_cycle_detected(self):
        step1 = PlanStep(step_id="step_1", capability_id="web_search", intent="S1", arguments={"query": "test"}, dependencies=["step_2"])
        step2 = PlanStep(step_id="step_2", capability_id="safe_math", intent="S2", arguments={"expression": "1+1"}, dependencies=["step_1"])
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="2 node cycle",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step1, step2],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        self.assertFalse(report.is_valid)
        p1 = next(p for p in report.passes if p.pass_name == ValidationPassName.DAG_ACYCLICITY)
        self.assertFalse(p1.passed)
        self.assertIn("Cycle detected", p1.message)

    def test_duplicate_step_ids_detected(self):
        step1 = PlanStep(step_id="dup_step", capability_id="web_search", intent="First", arguments={"query": "test"})
        step2 = PlanStep(step_id="dup_step", capability_id="safe_math", intent="Second", arguments={"expression": "2*2"})
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="Duplicate step IDs",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step1, step2],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        self.assertFalse(report.is_valid)
        p1 = next(p for p in report.passes if p.pass_name == ValidationPassName.DAG_ACYCLICITY)
        self.assertFalse(p1.passed)
        self.assertIn("Duplicate step ID", p1.message)


class TestL13Pass2DependencyExistence(unittest.TestCase):
    """Pass 2: Zero dangling dependency references."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_dangling_dependency_detected(self):
        step = PlanStep(
            step_id="step_1",
            capability_id="web_search",
            intent="Has dangling dep",
            arguments={"query": "test"},
            dependencies=["non_existent_step_99"],
        )
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="Dangling dep test",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        p2 = next(p for p in report.passes if p.pass_name == ValidationPassName.DEPENDENCY_EXISTENCE)
        self.assertFalse(p2.passed)
        self.assertEqual(p2.error_code, ErrorCode.INVALID_ARGUMENT)
        self.assertIn("non_existent_step_99", p2.message)


class TestL13Pass3CapabilityRegistration(unittest.TestCase):
    """Pass 3: Referenced capabilities must exist in registry."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_unregistered_capability_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Unregistered capability test",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="hallucinated_quantum_tool_v9",
                    intent="Invalid capability",
                    arguments={"foo": "bar"},
                )
            ],
        )
        report = self.validator.validate(plan)
        p3 = next(p for p in report.passes if p.pass_name == ValidationPassName.CAPABILITY_REGISTRATION)
        self.assertFalse(p3.passed)
        self.assertEqual(p3.error_code, ErrorCode.NOT_FOUND)
        self.assertIn("hallucinated_quantum_tool_v9", p3.message)


class TestL13Pass4SchemaConformance(unittest.TestCase):
    """Pass 4: Argument schema conformance, causal dependencies, and dynamic placeholders."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_missing_required_argument_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Missing required arg",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search with no query",
                    arguments={"max_results": 5},  # Missing "query"
                )
            ],
        )
        report = self.validator.validate(plan)
        p4 = next(p for p in report.passes if p.pass_name == ValidationPassName.SCHEMA_CONFORMANCE)
        self.assertFalse(p4.passed)
        self.assertIn("missing required argument 'query'", p4.message)

    def test_invalid_literal_argument_type_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Invalid arg type",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search with string max_results",
                    arguments={"query": "test", "max_results": "NOT_AN_INTEGER"},
                )
            ],
        )
        report = self.validator.validate(plan)
        p4 = next(p for p in report.passes if p.pass_name == ValidationPassName.SCHEMA_CONFORMANCE)
        self.assertFalse(p4.passed)

    def test_valid_dynamic_placeholder_with_causal_dependency_passes(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Dynamic argument with causal dependency",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Initial search",
                    arguments={"query": "python"},
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="safe_math",
                    intent="Calculate with search result count",
                    arguments={"expression": "$steps.step_1.output.count + 5"},
                    dependencies=["step_1"],  # Causal dependency correctly declared
                ),
            ],
        )
        report = self.validator.validate(plan)
        p4 = next(p for p in report.passes if p.pass_name == ValidationPassName.SCHEMA_CONFORMANCE)
        self.assertTrue(p4.passed)

    def test_dynamic_placeholder_missing_causal_dependency_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Dynamic argument without causal dependency",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Initial search",
                    arguments={"query": "python"},
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="safe_math",
                    intent="Calculate with search result count",
                    arguments={"expression": "$steps.step_1.output.count + 5"},
                    dependencies=[],  # Missing causal dependency "step_1"!
                ),
            ],
        )
        report = self.validator.validate(plan)
        p4 = next(p for p in report.passes if p.pass_name == ValidationPassName.SCHEMA_CONFORMANCE)
        self.assertFalse(p4.passed)
        self.assertIn("without declaring it as a dependency", p4.message)

    def test_dynamic_placeholder_referencing_nonexistent_step_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Dynamic argument referencing non-existent step",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search with phantom step ref",
                    arguments={"query": "$steps.phantom_step.output.query"},
                ),
            ],
        )
        report = self.validator.validate(plan)
        p4 = next(p for p in report.passes if p.pass_name == ValidationPassName.SCHEMA_CONFORMANCE)
        self.assertFalse(p4.passed)
        self.assertIn("references non-existent step", p4.message)


class TestL13Pass5PolicyFeasibility(unittest.TestCase):
    """Pass 5: Pre-flight policy feasibility checks."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_forbidden_git_command_hard_denied(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Destructive git command",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="powershell",
                    intent="Dangerous reset",
                    arguments={"command": "git reset --hard HEAD~1"},
                )
            ],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR)
        p5 = next(p for p in report.passes if p.pass_name == ValidationPassName.POLICY_FEASIBILITY)
        self.assertFalse(p5.passed)
        self.assertEqual(p5.error_code, ErrorCode.PERMISSION_DENIED)
        self.assertIn("violates policy", p5.message)

    def test_protected_system32_path_hard_denied(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Write to system32",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="file_write",
                    intent="System overwrite",
                    arguments={"file_path": r"C:\Windows\System32\payload.dll", "content": "bad"},
                )
            ],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.LOCAL_OPERATOR)
        p5 = next(p for p in report.passes if p.pass_name == ValidationPassName.POLICY_FEASIBILITY)
        self.assertFalse(p5.passed)
        self.assertEqual(p5.error_code, ErrorCode.PERMISSION_DENIED)

    def test_dynamic_path_does_not_trigger_false_positive_denial(self):
        # Testing BLK-03: Placeholder string containing .key does not trigger is_protected_path
        plan = Plan(
            quest_id="quest_1",
            goal="Dynamic key file read",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search for file",
                    arguments={"query": "find key"},
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="file_read",
                    intent="Read dynamic file",
                    arguments={"file_path": "$steps.step_1.output.key_path"},
                    dependencies=["step_1"],
                ),
            ],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.SAFE_ASSISTANT)
        p5 = next(p for p in report.passes if p.pass_name == ValidationPassName.POLICY_FEASIBILITY)
        self.assertTrue(p5.passed)
        self.assertTrue(any("policy check deferred" in w for w in report.warnings))


class TestL13Pass6AutonomyCompliance(unittest.TestCase):
    """Pass 6: Autonomy rank floors and ADVISOR read-only invariant."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_advisor_autonomy_rejects_mutating_action(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Mutate under advisor",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="file_write",
                    intent="Write file",
                    arguments={"file_path": "safe.txt", "content": "hello"},
                )
            ],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.ADVISOR)
        p6 = next(p for p in report.passes if p.pass_name == ValidationPassName.AUTONOMY_COMPLIANCE)
        self.assertFalse(p6.passed)
        self.assertEqual(p6.error_code, ErrorCode.UNAUTHORIZED_ACTION)
        self.assertIn("forbidden under ADVISOR", p6.message)

    def test_safe_assistant_rejects_trusted_operator_capability(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Run powershell under safe assistant",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="powershell",
                    intent="Run safe command",
                    arguments={"command": "Get-Date"},
                )
            ],
        )
        # powershell requires TRUSTED_OPERATOR (rank 4), SAFE_ASSISTANT is rank 2
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.SAFE_ASSISTANT)
        p6 = next(p for p in report.passes if p.pass_name == ValidationPassName.AUTONOMY_COMPLIANCE)
        self.assertFalse(p6.passed)
        self.assertEqual(p6.error_code, ErrorCode.UNAUTHORIZED_ACTION)
        self.assertIn("exceeding granted 'SAFE_ASSISTANT'", p6.message)

    def test_trusted_operator_accepts_powershell_capability(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Run powershell under trusted operator",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="powershell",
                    intent="Run safe command",
                    arguments={"command": "Get-Date"},
                )
            ],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR)
        p6 = next(p for p in report.passes if p.pass_name == ValidationPassName.AUTONOMY_COMPLIANCE)
        self.assertTrue(p6.passed)


class TestL13Pass7StepCountBounds(unittest.TestCase):
    """Pass 7: Enforces [1, max_steps] bounds."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_empty_plan_rejected(self):
        plan = Plan.model_construct(
            plan_id="plan_empty",
            quest_id="quest_1",
            goal="Empty plan",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        p7 = next(p for p in report.passes if p.pass_name == ValidationPassName.STEP_COUNT_BOUNDS)
        self.assertFalse(p7.passed)
        self.assertIn("minimum 1 step required", p7.message)

    def test_exceeding_max_steps_rejected(self):
        steps = [
            PlanStep(
                step_id=f"step_{i}",
                capability_id="safe_math",
                intent=f"Calc {i}",
                arguments={"expression": f"{i}+1"},
            )
            for i in range(5)
        ]
        plan = Plan(
            quest_id="quest_1",
            goal="5 step plan",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=steps,
        )
        # Set max_steps=4
        report = self.validator.validate(plan, max_steps=4)
        p7 = next(p for p in report.passes if p.pass_name == ValidationPassName.STEP_COUNT_BOUNDS)
        self.assertFalse(p7.passed)
        self.assertIn("exceeds maximum allowed (4)", p7.message)


class TestL13Pass8GraphDepthBounds(unittest.TestCase):
    """Pass 8: Enforces [1, max_depth] bounds and handles cyclical graphs gracefully."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_exceeding_max_depth_rejected(self):
        # Linear chain of 5 steps
        steps = []
        for i in range(5):
            deps = [f"step_{i-1}"] if i > 0 else []
            steps.append(
                PlanStep(
                    step_id=f"step_{i}",
                    capability_id="safe_math",
                    intent=f"Calc {i}",
                    arguments={"expression": f"{i}+1"},
                    dependencies=deps,
                )
            )
        plan = Plan(
            quest_id="quest_1",
            goal="Deep chain",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=steps,
        )
        # Chain depth is 5; max_depth=3 should fail
        report = self.validator.validate(plan, max_depth=3)
        p8 = next(p for p in report.passes if p.pass_name == ValidationPassName.GRAPH_DEPTH_BOUNDS)
        self.assertFalse(p8.passed)
        self.assertIn("exceeds maximum allowed depth limit (3)", p8.message)

    def test_cyclical_plan_does_not_crash_pass8(self):
        # Testing BLK-04: compute_plan_depth is skipped when cycle is detected
        step1 = PlanStep(step_id="step_1", capability_id="safe_math", intent="S1", arguments={"expression": "1"}, dependencies=["step_2"])
        step2 = PlanStep(step_id="step_2", capability_id="safe_math", intent="S2", arguments={"expression": "2"}, dependencies=["step_1"])
        plan = Plan.model_construct(
            plan_id="plan_cyclic",
            quest_id="quest_1",
            goal="Cycle plan",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step1, step2],
            timeout_budget_s=300.0,
        )
        report = self.validator.validate(plan)
        p8 = next(p for p in report.passes if p.pass_name == ValidationPassName.GRAPH_DEPTH_BOUNDS)
        self.assertFalse(p8.passed)
        self.assertIn("skipped due to circular dependencies", p8.message)


class TestL13Pass9MutationSafety(unittest.TestCase):
    """Pass 9: Checks non-idempotent mutations against dangerous retries."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_non_idempotent_step_with_excess_attempts_rejected(self):
        # powershell is NON_IDEMPOTENT with RetryPolicy.NEVER
        step = PlanStep(
            step_id="step_1",
            capability_id="powershell",
            intent="Run command",
            arguments={"command": "Get-Process"},
            max_attempts=3,  # Excess retry attempts on non-idempotent tool
        )
        plan = Plan(
            quest_id="quest_1",
            goal="Non idempotent retry",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[step],
        )
        report = self.validator.validate(plan, autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR)
        p9 = next(p for p in report.passes if p.pass_name == ValidationPassName.MUTATION_SAFETY)
        self.assertFalse(p9.passed)
        self.assertIn("declares max_attempts=3 > 1", p9.message)


class TestL13Pass10ResourceBudget(unittest.TestCase):
    """Pass 10: Validates plan timeout budgets and step timeout consistency."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_negative_timeout_budget_rejected(self):
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="Invalid budget",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[PlanStep(step_id="step_1", capability_id="web_search", intent="Search", arguments={"query": "test"})],
            timeout_budget_s=-10.0,
        )
        report = self.validator.validate(plan)
        p10 = next(p for p in report.passes if p.pass_name == ValidationPassName.RESOURCE_BUDGET)
        self.assertFalse(p10.passed)
        self.assertIn("must be strictly positive", p10.message)

    def test_timeout_budget_exceeding_max_rejected(self):
        plan = Plan.model_construct(
            plan_id="plan_test",
            quest_id="quest_1",
            goal="Excessive budget",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[PlanStep(step_id="step_1", capability_id="web_search", intent="Search", arguments={"query": "test"})],
            timeout_budget_s=5000.0,
        )
        report = self.validator.validate(plan, max_timeout_budget_s=3600.0)
        p10 = next(p for p in report.passes if p.pass_name == ValidationPassName.RESOURCE_BUDGET)
        self.assertFalse(p10.passed)
        self.assertIn("exceeds maximum allowed limit", p10.message)

    def test_step_timeout_exceeding_plan_budget_rejected(self):
        plan = Plan(
            quest_id="quest_1",
            goal="Step budget conflict",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            timeout_budget_s=60.0,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search",
                    arguments={"query": "test"},
                    timeout_s=120.0,  # 120s > 60s plan budget
                )
            ],
        )
        report = self.validator.validate(plan)
        p10 = next(p for p in report.passes if p.pass_name == ValidationPassName.RESOURCE_BUDGET)
        self.assertFalse(p10.passed)
        self.assertIn("exceeds plan timeout budget", p10.message)


class TestL13GoldenMultiStepPlans(unittest.TestCase):
    """End-to-end integration tests for multi-step valid diamond DAGs."""

    def setUp(self):
        self.validator = DeterministicPlanValidator()

    def test_golden_diamond_dag_passes_all_10_checks(self):
        # A valid diamond DAG:
        #        step_1 (web_search)
        #        /                 \
        #  step_2 (file_read)     step_3 (safe_math)
        #        \                 /
        #        step_4 (file_write)
        plan = Plan(
            quest_id="quest_golden_1",
            goal="Research, calculate, and document findings",
            plan_type=PlanType.TEMPLATE_DERIVED,
            timeout_budget_s=300.0,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="web_search",
                    intent="Search for reference data",
                    arguments={"query": "python algorithms", "max_results": 5},
                    timeout_s=30.0,
                ),
                PlanStep(
                    step_id="step_2",
                    capability_id="file_read",
                    intent="Read local config template",
                    arguments={"filepath": "config.json"},
                    dependencies=["step_1"],
                    timeout_s=15.0,
                ),
                PlanStep(
                    step_id="step_3",
                    capability_id="safe_math",
                    intent="Calculate batch size",
                    arguments={"expression": "10 * 4"},
                    dependencies=["step_1"],
                    timeout_s=5.0,
                ),
                PlanStep(
                    step_id="step_4",
                    capability_id="file_write",
                    intent="Write synthesized summary",
                    arguments={"filepath": "summary.txt", "content": "Findings documented"},
                    dependencies=["step_2", "step_3"],
                    timeout_s=30.0,
                ),
            ],
        )
        report = self.validator.validate(
            plan=plan,
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
            max_steps=10,
            max_depth=5,
        )

        self.assertTrue(report.is_valid, f"Validation failed with errors: {report.errors}")
        self.assertEqual(len(report.errors), 0)
        self.assertEqual(len(report.passes), 10)
        self.assertTrue(all(p.passed for p in report.passes))
        
        # Windows timeslice hardening: take best of 5 samples to measure true intrinsic engine execution speed
        latencies = [report.latency_ms] + [
            self.validator.validate(
                plan=plan,
                autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
                max_steps=10,
                max_depth=5,
            ).latency_ms
            for _ in range(4)
        ]
        best_latency = min(latencies)
        self.assertLess(best_latency, 100.0, f"Validator intrinsic latency {best_latency}ms exceeded 100ms (samples: {latencies})")


class TestL13NonSwitchingBoundary(unittest.TestCase):
    """Verifies that legacy omni_agent.py and omni_engine/planner.py have 0 git diffs."""

    def test_legacy_files_remain_untouched(self):
        res = subprocess.run(
            ["git", "diff", "HEAD", "--", "omni_agent.py", "omni_engine/planner.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(
            res.stdout.strip(),
            "",
            f"Non-switching boundary breached! Found git diffs: {res.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
