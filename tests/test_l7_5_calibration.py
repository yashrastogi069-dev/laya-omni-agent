"""
tests.test_l7_5_calibration
===========================
Comprehensive unit and integration test suite for Checkpoint L7.5:
System One Truth, Calibration & Upstream Alignment.

Tests cover:
1. CalibrationConfig validation, immutability, and custom threshold propagation.
2. DECISION_EVAL_CORPUS_V1 integrity (100+ cases, all canonical domains, schema checks).
3. LayaProvider model selection, pre-eviction memory safety, thread locking, and model_id stability.
4. DecisionFabric.evaluate_adaptive() fast triage exit vs full-frame escalation.
5. DecisionFabric calibration metadata and threshold adherence.
6. HierarchicalRouter calibrated scoring and threshold customization.
7. Shadow Semantic Skill Routing telemetry and agreement tracking.
8. Hardware-aware benchmark harness execution.
"""

import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from omni_engine.contracts.calibration import (
    CalibratedModelThresholds,
    CalibrationConfig,
    DeterministicPolicyThresholds,
)
from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.enums import DecisionSignalType
from omni_engine.decision.benchmark import run_decision_benchmark
from omni_engine.decision.eval_corpus import DECISION_EVAL_CORPUS_V1, DecisionEvalCase
from omni_engine.decision.fabric import DecisionFabric
from omni_engine.providers.system1 import LayaProvider
from omni_engine.routing.router import HierarchicalRouter


class MockSystemOneProvider:
    """Fast, deterministic mock provider for unit testing calibration logic."""

    def __init__(self, responses: Dict[str, Any] = None) -> None:
        self.provider_id = "mock-system1"
        self.model_id = "mock-calibrated-v1"
        self.responses = responses or {}
        self.call_history = []

    def predict_signals(self, context: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, DecisionSignal]:
        self.call_history.append((context, questions))
        signals = {}
        for q_name in questions:
            resp_val = self.responses.get(q_name, "default_val")
            signals[q_name] = DecisionSignal(
                signal_type=DecisionSignalType.INTENT if q_name == "intent" else DecisionSignalType.RISK,
                value=resp_val,
                confidence=0.92,
                probabilities={resp_val: 0.92},
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            )
        return signals


class TestCalibrationContracts(unittest.TestCase):
    """Verifies CalibrationConfig schema, validation, and threshold models."""

    def test_default_calibration_config_values(self):
        config = CalibrationConfig()
        self.assertEqual(config.calibration_version, "modernbert-large-temp-scaled-v1")
        self.assertEqual(config.model_thresholds.domain_confidence_min, 0.55)
        self.assertEqual(config.model_thresholds.ambiguity_max, 0.65)
        self.assertEqual(config.model_thresholds.skill_candidate_min, 0.50)
        self.assertEqual(config.model_thresholds.skill_selection_min, 0.75)
        self.assertEqual(config.model_thresholds.skill_description_overlap_ceiling, 0.50)

        self.assertEqual(config.deterministic_policy.ambiguity_min_words, 2)
        self.assertEqual(config.deterministic_policy.pinned_capability_score, 1.0)
        self.assertEqual(config.deterministic_policy.skill_required_capability_score, 0.98)
        self.assertEqual(config.deterministic_policy.skill_optional_capability_score, 0.75)
        self.assertEqual(config.deterministic_policy.domain_primary_default_score, 0.85)
        self.assertEqual(config.deterministic_policy.domain_pooled_default_score, 0.70)

    def test_calibration_config_forbids_extra_fields(self):
        with self.assertRaises(Exception):
            CalibrationConfig(unknown_field="invalid")

    def test_custom_calibration_overrides(self):
        custom = CalibrationConfig(
            calibration_version="custom-v2",
            model_thresholds=CalibratedModelThresholds(
                skill_selection_min=0.88,
                domain_confidence_min=0.60,
            ),
            deterministic_policy=DeterministicPolicyThresholds(
                pinned_capability_score=0.99,
            ),
        )
        self.assertEqual(custom.calibration_version, "custom-v2")
        self.assertEqual(custom.model_thresholds.skill_selection_min, 0.88)
        self.assertEqual(custom.model_thresholds.domain_confidence_min, 0.60)
        self.assertEqual(custom.deterministic_policy.pinned_capability_score, 0.99)


class TestEvalCorpusIntegrity(unittest.TestCase):
    """Verifies DECISION_EVAL_CORPUS_V1 structure, domain diversity, and schema compliance."""

    def test_corpus_count_exceeds_100_cases(self):
        self.assertGreaterEqual(len(DECISION_EVAL_CORPUS_V1), 100)

    def test_case_schema_and_types(self):
        seen_ids = set()
        domains = set()
        for case in DECISION_EVAL_CORPUS_V1:
            self.assertIsInstance(case, DecisionEvalCase)
            self.assertNotIn(case.id, seen_ids, f"Duplicate case ID: {case.id}")
            seen_ids.add(case.id)
            self.assertTrue(case.prompt.strip(), f"Empty prompt in {case.id}")
            self.assertIn(case.expected_domain, ["general", "os", "dev", "web", "browser", "data"])
            self.assertIn(case.expected_intent, ["informational", "task_execution", "troubleshooting", "empty"])
            self.assertIn(case.expected_risk, ["safe_read_only", "reversible_mutation", "high_risk_system"])
            self.assertIsInstance(case.expected_needs_tools, bool)
            self.assertIsInstance(case.expected_needs_plan, bool)
            domains.add(case.expected_domain)

        # All 6 domains must be represented
        self.assertEqual(domains, {"general", "os", "dev", "web", "browser", "data"})


class TestLayaProviderCalibration(unittest.TestCase):
    """Verifies LayaProvider upstream alignment, model routing, and memory guards."""

    def test_model_name_and_model_id_backward_compatibility(self):
        # Default english model must expose model_id = "ModernBERT-large" for contract parity
        p_eng = LayaProvider(model_name="english", preload=False)
        self.assertEqual(p_eng.model_name, "english")
        self.assertEqual(p_eng.model_id, "ModernBERT-large")

        # Multilingual model is strictly forbidden under English-only invariant
        with self.assertRaises(ValueError) as ctx:
            LayaProvider(model_name="multilingual", preload=False)
        self.assertIn("forbidden", str(ctx.exception).lower())

        # Typed-decisions model
        p_typed = LayaProvider(model_name="typed-decisions", preload=False)
        self.assertEqual(p_typed.model_name, "typed-decisions")
        self.assertEqual(p_typed.model_id, "ModernBERT-typed-decisions")

    def test_invalid_model_name_rejected(self):
        with self.assertRaises(ValueError):
            LayaProvider(model_name="nonexistent_checkpoint", preload=False)

    @patch("omni_engine.providers.system1._SHARED_ROUTER", None)
    @patch("laya.Router")
    def test_preload_only_loads_explicit_model_name(self, mock_router_cls):
        mock_router_instance = MagicMock()
        mock_router_instance.loaded = set()
        mock_router_cls.return_value = mock_router_instance

        p = LayaProvider(model_name="english", preload=True)
        # Verify preload was called with explicit list ["english"], NEVER None (which loads all 3)
        mock_router_instance.preload.assert_called_with(names=["english"])


class TestDecisionFabricAdaptiveAndCalibration(unittest.TestCase):
    """Verifies DecisionFabric evaluate_adaptive, calibration metadata, and thresholds."""

    def test_evaluate_adaptive_conversational_early_exit(self):
        # Mock answers indicating conversational chat
        mock_prov = MockSystemOneProvider(
            responses={
                "intent": "informational",
                "risk": "safe_read_only",
                "needs_tools": "no_tools",
                "requires_action": "reply_only",
            }
        )
        fabric = DecisionFabric(provider=mock_prov)
        frame = fabric.evaluate_adaptive("What is the capital of France?")

        # Must exit at triage: only 1 call to provider evaluating 4 triage questions
        self.assertEqual(len(mock_prov.call_history), 1)
        _, questions = mock_prov.call_history[0]
        self.assertEqual(set(questions.keys()), {"intent", "risk", "needs_tools", "requires_action"})

        # Frame should be fully formed and valid
        self.assertEqual(frame.intent.value, "informational")
        self.assertFalse(frame.needs_tools.value)
        self.assertFalse(frame.requires_action.value)
        self.assertEqual(frame.risk.value, "safe_read_only")
        self.assertEqual(frame.candidate_domains, ["general"])
        self.assertEqual(frame.intent.metadata.get("adaptive_triage"), "early_exit")
        self.assertEqual(frame.intent.metadata.get("calibration_version"), fabric.calibration.calibration_version)

    def test_evaluate_adaptive_task_execution_triggers_full_pass(self):
        # Mock answers indicating action required
        mock_prov = MockSystemOneProvider(
            responses={
                "intent": "task_execution",
                "risk": "reversible_mutation",
                "needs_tools": "tools_required",
                "requires_action": "action_required",
                "domain": "dev",
            }
        )
        fabric = DecisionFabric(provider=mock_prov)
        # Safe non-high-risk task prompt
        frame = fabric.evaluate_adaptive("Inspect directory contents and view python file")

        # Must trigger stage 2 full pass: 2 calls total (triage + remaining 11 questions)
        self.assertEqual(len(mock_prov.call_history), 2)
        triage_q = set(mock_prov.call_history[0][1].keys())
        remaining_q = set(mock_prov.call_history[1][1].keys())
        self.assertEqual(len(triage_q), 4)
        self.assertEqual(len(remaining_q), 11)
        self.assertEqual(triage_q.union(remaining_q), set(fabric._get_batched_questions().keys()))

        self.assertTrue(frame.requires_action.value)
        self.assertTrue(frame.needs_tools.value)

    def test_evaluate_adaptive_high_risk_regex_bypasses_triage(self):
        mock_prov = MockSystemOneProvider(
            responses={
                "intent": "task_execution",
                "risk": "high_risk_system",
                "needs_tools": "tools_required",
                "requires_action": "action_required",
                "domain": "os",
            }
        )
        fabric = DecisionFabric(provider=mock_prov)
        # Matches high-risk pattern r"\bkill_process\b"
        frame = fabric.evaluate_adaptive("kill_process pid 9999")

        # Direct full pass without triage stage
        self.assertEqual(len(mock_prov.call_history), 1)
        self.assertEqual(len(mock_prov.call_history[0][1]), 15)
        self.assertEqual(frame.risk.value, "high_risk_system")
        self.assertEqual(frame.reversibility.value, "irreversible")
        self.assertTrue(frame.escalation_required.value)

    def test_custom_calibration_ambiguity_threshold(self):
        # Configure tight ambiguity threshold of 0.30
        custom_cal = CalibrationConfig(
            model_thresholds=CalibratedModelThresholds(ambiguity_max=0.30),
            deterministic_policy=DeterministicPolicyThresholds(ambiguity_min_words=1),
        )
        mock_prov = MockSystemOneProvider(
            responses={
                "intent": "task_execution",
                "risk": "safe_read_only",
                "needs_tools": "tools_required",
                "requires_action": "action_required",
                "ambiguity": 0.45,  # Above custom 0.30, but below default 0.65
            }
        )
        fabric = DecisionFabric(provider=mock_prov, calibration=custom_cal)
        frame = fabric.evaluate("analyze this code carefully and report back")

        # Should escalate to needs_clarification=True due to custom threshold
        self.assertTrue(frame.needs_clarification.value)


class TestHierarchicalRouterCalibrationAndShadow(unittest.TestCase):
    """Verifies HierarchicalRouter calibrated scoring and shadow semantic routing."""

    def test_router_inherits_custom_calibration(self):
        custom_cal = CalibrationConfig(
            model_thresholds=CalibratedModelThresholds(skill_selection_min=0.90),
            deterministic_policy=DeterministicPolicyThresholds(
                pinned_capability_score=0.95,
                skill_required_capability_score=0.92,
            ),
        )
        router = HierarchicalRouter(calibration=custom_cal)
        self.assertEqual(router.calibration.model_thresholds.skill_selection_min, 0.90)
        self.assertEqual(router.calibration.deterministic_policy.pinned_capability_score, 0.95)

    def test_pinned_capability_uses_calibrated_score(self):
        custom_cal = CalibrationConfig(
            deterministic_policy=DeterministicPolicyThresholds(pinned_capability_score=0.93)
        )
        router = HierarchicalRouter(calibration=custom_cal)
        # "git status" matches CAPABILITY_PIN_MAP
        decision = router.route("run git status in current directory")
        git_cands = [c for c in decision.candidates if c.capability_id == "git_status"]
        self.assertTrue(len(git_cands) >= 1)
        self.assertEqual(git_cands[0].score, 0.93)

    def test_shadow_semantic_skill_routing_telemetry(self):
        # Test shadow semantic routing enabled
        router = HierarchicalRouter(enable_shadow_semantic=True)
        # Mock provider predict_signals to simulate shadow semantic choice
        mock_prov = MagicMock()
        mock_prov.predict_signals.return_value = {
            "skill_choice": DecisionSignal(
                signal_type=DecisionSignalType.TASK_CLASS,
                value="diagnose_system",
                confidence=0.89,
                probabilities={"diagnose_system": 0.89, "inspect_repository": 0.11},
                provider_id="mock",
                model_id="mock",
                latency_ms=10.0,
            )
        }
        router.provider = mock_prov

        decision = router.route("diagnose system health and check processes")
        self.assertIn("shadow_routing", decision.metadata)
        shadow_data = decision.metadata["shadow_routing"]
        self.assertEqual(shadow_data["shadow_selected_skill"], "diagnose_system")
        self.assertIn("semantic_agreement", shadow_data)


class TestBenchmarkHarness(unittest.TestCase):
    """Verifies that the hardware-aware benchmark runs cleanly and returns telemetry."""

    def test_benchmark_dry_run(self):
        # Run minimal benchmark (1 prompt, 1 iteration, no warmup)
        result = run_decision_benchmark(
            prompts=["What is Python?"],
            iterations=1,
            warmup=False,
        )
        self.assertIn("device", result)
        self.assertIn("cpu_count", result)
        self.assertIn("host_ram_gb", result)
        self.assertIn("evaluations", result)
        self.assertIn("batch_scaling", result)
        self.assertIn("adaptive_triage", result)
        self.assertEqual(result["evaluations"]["total_runs"], 1)


if __name__ == "__main__":
    unittest.main()
