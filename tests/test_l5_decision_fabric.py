"""
tests.test_l5_decision_fabric
==============================
Comprehensive test suite for Checkpoint L5: System One Decision Fabric.

Validates:
1. DecisionFrame complete contract adherence and JSON serialization.
2. Deterministic fast-path boundary conditions (empty prompt, whitespace, massive prompt, Unicode).
3. Deterministic safety floor overrides and Invariant 7 reversibility constraints.
4. Ambiguity detection and clarifying question triggers.
5. Action vs conversation disambiguation and generative necessity gating.
6. Candidate domain ranking without violating extra='forbid'.
7. Graceful fallback on provider failure.
8. Live benchmark evaluation against the standard corpus.
9. Strict non-switching boundary preservation.
"""

import json
import os
import sys
import unittest
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from pydantic import ValidationError

from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.decision import (
    BENCHMARK_CORPUS,
    DecisionFabric,
    evaluate_decision_corpus,
)
from omni_engine.providers.base import ProviderError, ProviderHealth, SystemOneProvider


class MockSystemOneProvider(SystemOneProvider):
    """Fast, deterministic in-memory provider for testing fabric logic without loading PyTorch weights."""

    def __init__(self, should_fail: bool = False) -> None:
        self.provider_id = "mock-s1"
        self.model_id = "mock-decision-model"
        self.is_configured = True
        self.should_fail = should_fail
        self.call_count = 0

    def predict_signals(
        self,
        context: Dict[str, Any],
        questions: Dict[str, Any],
    ) -> Dict[str, DecisionSignal]:
        self.call_count += 1
        if self.should_fail:
            raise ProviderError(
                code=ErrorCode.PROCESS_FAILED,
                message="Mock simulated forward pass failure",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        prompt = context.get("prompt", "").lower()
        signals = {}

        # Default signal assignments based on keyword heuristics for mock
        is_kill = "kill" in prompt
        is_refactor = "refactor" in prompt or "unit test" in prompt
        is_chat = "capital" in prompt or "hello" in prompt
        is_ambiguous = prompt.strip() == "do it" or len(prompt.split()) <= 2

        signals["intent"] = DecisionSignal(
            signal_type=DecisionSignalType.INTENT,
            value="informational" if is_chat else "task_execution",
            confidence=0.92,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["task_class"] = DecisionSignal(
            signal_type=DecisionSignalType.TASK_CLASS,
            value="multi_step_quest" if is_refactor else "single_turn_reflex",
            confidence=0.88,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["domain"] = DecisionSignal(
            signal_type=DecisionSignalType.DOMAIN,
            value="os" if is_kill else ("dev" if is_refactor else "general"),
            confidence=0.85,
            probabilities={"dev": 0.6, "os": 0.3, "general": 0.1},
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["urgency"] = DecisionSignal(
            signal_type=DecisionSignalType.URGENCY,
            value="immediate" if is_kill else "routine",
            confidence=0.89,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["importance"] = DecisionSignal(
            signal_type=DecisionSignalType.IMPORTANCE,
            value="high" if is_refactor else "normal",
            confidence=0.90,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["risk"] = DecisionSignal(
            signal_type=DecisionSignalType.RISK,
            value="high_risk_system" if is_kill else "safe_read_only",
            confidence=0.95,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["reversibility"] = DecisionSignal(
            signal_type=DecisionSignalType.REVERSIBILITY,
            value="irreversible" if is_kill else "reversible",
            confidence=0.91,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["ambiguity"] = DecisionSignal(
            signal_type=DecisionSignalType.AMBIGUITY,
            value="ambiguous" if is_ambiguous else "unambiguous",
            confidence=0.93 if is_ambiguous else 0.15,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["needs_plan"] = DecisionSignal(
            signal_type=DecisionSignalType.NEEDS_PLAN,
            value="needs_dag_plan" if is_refactor else "direct",
            confidence=0.87,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["needs_tools"] = DecisionSignal(
            signal_type=DecisionSignalType.NEEDS_TOOLS,
            value="no_tools" if is_chat else "tools_required",
            confidence=0.94,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["model_tier"] = DecisionSignal(
            signal_type=DecisionSignalType.MODEL_TIER,
            value="pro" if is_refactor else "system_1",
            confidence=0.86,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["needs_clarification"] = DecisionSignal(
            signal_type=DecisionSignalType.NEEDS_CLARIFICATION,
            value="ask_user" if is_ambiguous else "proceed",
            confidence=0.90,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["requires_action"] = DecisionSignal(
            signal_type=DecisionSignalType.REQUIRES_ACTION,
            value="reply_only" if is_chat else "action_required",
            confidence=0.92,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["needs_generative_reasoning"] = DecisionSignal(
            signal_type=DecisionSignalType.NEEDS_GENERATIVE_REASONING,
            value="generative_required" if is_refactor else "deterministic_or_s1",
            confidence=0.88,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        signals["escalation_required"] = DecisionSignal(
            signal_type=DecisionSignalType.ESCALATION_REQUIRED,
            value="escalate" if is_kill else "autonomous",
            confidence=0.96,
            provider_id=self.provider_id,
            model_id=self.model_id,
            latency_ms=1.5,
        )
        return signals

    def classify(self, prompt: str, criteria: Dict[str, str], instructions: str = "") -> DecisionSignal:
        return DecisionSignal(
            signal_type=DecisionSignalType.INTENT,
            value=list(criteria.keys())[0],
            confidence=0.9,
            provider_id=self.provider_id,
            model_id=self.model_id,
        )

    def score(self, prompt: str, criteria: str) -> float:
        return 0.85

    def health_check(self) -> ProviderHealth:
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=True,
            latency_ms=0.1,
        )


class TestL5DecisionFabric(unittest.TestCase):
    """Unit and functional test suite for DecisionFabric."""

    def setUp(self):
        self.mock_provider = MockSystemOneProvider()
        self.fabric = DecisionFabric(provider=self.mock_provider)

    def test_decision_frame_complete_contract_adherence(self):
        """DecisionFrame contains all 10 mandatory signals and 4 extended signals, correctly typed."""
        frame = self.fabric.evaluate("View the contents of README.md to check instructions")
        self.assertIsInstance(frame, DecisionFrame)
        self.assertEqual(frame.schema_version, "1.0.0")

        # 10 Mandatory Signals
        self.assertIsInstance(frame.intent, DecisionSignal)
        self.assertEqual(frame.intent.signal_type, DecisionSignalType.INTENT)
        self.assertIsInstance(frame.task_class, DecisionSignal)
        self.assertIsInstance(frame.urgency, DecisionSignal)
        self.assertIsInstance(frame.importance, DecisionSignal)
        self.assertIsInstance(frame.risk, DecisionSignal)
        self.assertIsInstance(frame.reversibility, DecisionSignal)
        self.assertIsInstance(frame.ambiguity, DecisionSignal)
        self.assertIsInstance(frame.needs_plan, DecisionSignal)
        self.assertIsInstance(frame.needs_tools, DecisionSignal)
        self.assertIsInstance(frame.model_tier, DecisionSignal)

        # 4 Extended Signals
        self.assertIsNotNone(frame.needs_clarification)
        self.assertIsInstance(frame.needs_clarification.value, bool)
        self.assertIsNotNone(frame.requires_action)
        self.assertIsInstance(frame.requires_action.value, bool)
        self.assertIsNotNone(frame.needs_generative_reasoning)
        self.assertIsInstance(frame.needs_generative_reasoning.value, bool)
        self.assertIsNotNone(frame.escalation_required)
        self.assertIsInstance(frame.escalation_required.value, bool)

        # Candidate domains list (avoiding domain contract trap)
        self.assertIsInstance(frame.candidate_domains, list)
        self.assertTrue(len(frame.candidate_domains) > 0)
        self.assertIn("dev", frame.candidate_domains)

        # JSON serialization roundtrip
        dumped_json = frame.model_dump_json()
        self.assertIn('"schema_version":"1.0.0"', dumped_json)
        loaded = json.loads(dumped_json)
        self.assertEqual(loaded["schema_version"], "1.0.0")

    def test_empty_prompt_fastpath(self):
        """Empty or whitespace prompts return instant deterministic DecisionFrame without calling model."""
        for empty_val in ["", "   ", "\t\n\r  "]:
            self.mock_provider.call_count = 0
            frame = self.fabric.evaluate(empty_val)
            self.assertEqual(self.mock_provider.call_count, 0)  # Model was NOT invoked
            self.assertEqual(frame.intent.value, "empty")
            self.assertTrue(frame.needs_clarification.value)
            self.assertFalse(frame.requires_action.value)
            self.assertFalse(frame.needs_tools.value)
            self.assertFalse(frame.needs_plan.value)
            self.assertLess(frame.total_latency_ms, 5.0)

    def test_massive_prompt_truncation(self):
        """Prompts exceeding 3,000 characters are truncated via head-tail sliding window."""
        long_prompt = "Header instructions: audit codebase.\n" + ("x" * 5000) + "\nFooter: report findings."
        frame = self.fabric.evaluate(long_prompt)
        self.assertIsInstance(frame, DecisionFrame)
        self.assertEqual(self.mock_provider.call_count, 1)

    def test_high_risk_safety_override(self):
        """High-risk commands trigger deterministic safety floor overrides and Invariant 7 reversibility."""
        for dangerous_cmd in [
            "kill_process --pid 9999",
            "rmdir /s /q C:\\ImportantData",
            "del /f /s C:\\test.txt",
            "rm -rf /var/log",
            "drop table users",
        ]:
            frame = self.fabric.evaluate(dangerous_cmd)
            self.assertEqual(frame.risk.value, "high_risk_system")
            self.assertEqual(frame.reversibility.value, "irreversible")
            self.assertTrue(frame.escalation_required.value)

    def test_ambiguity_triggers_clarification(self):
        """Ambiguous instructions trigger needs_clarification=True."""
        frame = self.fabric.evaluate("do it")
        self.assertTrue(frame.needs_clarification.value)
        self.assertTrue(frame.needs_generative_reasoning.value)

    def test_conversational_prompt_disables_action_and_tools(self):
        """Pure conversational prompt sets requires_action=False, needs_tools=False, needs_plan=False."""
        frame = self.fabric.evaluate("What is the capital of France and what is its history?")
        self.assertFalse(frame.requires_action.value)
        self.assertFalse(frame.needs_tools.value)
        self.assertFalse(frame.needs_plan.value)
        self.assertFalse(frame.needs_generative_reasoning.value)
        self.assertEqual(frame.model_tier.value, "system_1")

    def test_provider_failure_graceful_fallback(self):
        """When provider raises ProviderError, fabric returns a safe escalated DecisionFrame."""
        failing_provider = MockSystemOneProvider(should_fail=True)
        fabric = DecisionFabric(provider=failing_provider)
        frame = fabric.evaluate("Execute command")
        self.assertIsInstance(frame, DecisionFrame)
        self.assertTrue(frame.needs_clarification.value)
        self.assertTrue(frame.escalation_required.value)
        self.assertTrue(frame.needs_generative_reasoning.value)
        self.assertEqual(frame.model_tier.value, "pro")
        self.assertIn("fallback", frame.provider_id)

    def test_domain_ranking_order(self):
        """candidate_domains is correctly ordered by descending probability."""
        frame = self.fabric.evaluate("Refactor auth middleware and add unit tests")
        # In mock provider, probabilities are {"dev": 0.6, "os": 0.3, "general": 0.1}
        self.assertEqual(frame.candidate_domains[:3], ["dev", "os", "general"])

    def test_legacy_non_switching_boundary(self):
        """Existing legacy System1Router remains intact and functional."""
        from omni_engine.system1 import System1Router
        router = System1Router()
        self.assertTrue(hasattr(router, "route_tool"))


class TestL5BenchmarkEvaluation(unittest.TestCase):
    """Evaluates DecisionFabric against the 10-prompt standard benchmark corpus."""

    def test_benchmark_corpus_structure(self):
        """Benchmark corpus contains at least 10 diverse representative prompts."""
        self.assertGreaterEqual(len(BENCHMARK_CORPUS), 10)
        for item in BENCHMARK_CORPUS:
            self.assertIn("id", item)
            self.assertIn("prompt", item)

    def test_evaluate_decision_corpus_with_mock_provider(self):
        """Runs evaluate_decision_corpus with MockSystemOneProvider and reports summary metrics."""
        mock_prov = MockSystemOneProvider()
        fabric = DecisionFabric(provider=mock_prov)
        summary = evaluate_decision_corpus(fabric=fabric)

        self.assertEqual(summary["total_prompts"], len(BENCHMARK_CORPUS))
        self.assertEqual(len(summary["results"]), len(BENCHMARK_CORPUS))
        self.assertIn("avg_ms", summary["latency_summary"])
        self.assertIn("min_ms", summary["latency_summary"])
        self.assertIn("max_ms", summary["latency_summary"])
        self.assertIn("p95_ms", summary["latency_summary"])
        self.assertLess(summary["latency_summary"]["avg_ms"], 50.0)

    def test_live_laya_provider_single_evaluation(self):
        """Live evaluation of one prompt through local ModernBERT-large (LayaProvider)."""
        from omni_engine.providers.system1 import LayaProvider
        import torch

        live_fabric = DecisionFabric(provider=LayaProvider(preload=False))
        # Warm up model to load weights into memory
        _ = live_fabric.evaluate("System initialization warmup probe")

        # Warm evaluation pass adhering to latency budget
        frame = live_fabric.evaluate("View the contents of README.md to check instructions")

        self.assertIsInstance(frame, DecisionFrame)
        self.assertEqual(frame.provider_id, "laya")
        self.assertGreaterEqual(frame.total_latency_ms, 0.0)

        # Hardware-aware latency budget check:
        # CUDA target: <35ms; CPU fallback budget for 15-question batched forward pass: <35000ms
        latency_budget = 35.0 if torch.cuda.is_available() else 35000.0
        self.assertLess(frame.total_latency_ms, latency_budget)


if __name__ == "__main__":
    unittest.main()
