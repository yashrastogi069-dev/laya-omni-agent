"""
tests.test_foundation_broker
============================
Comprehensive Unit Test Suite for Foundation Gate:
- SystemOneBroker with User Model Sovereignty (USER_LOCKED, USER_PREFERRED, AUTO)
- Strict Provider Allowlist & Task-Level Overrides
- Concurrency Separation & Queue Timeout Governance
- Strict English-Only Invariant Enforcement
- Windows RAM Telemetry & Eviction Debouncing
- Deterministic 70/30 Stratified Calibration & ECE Metrics
- Concurrency Benchmark Harness
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.contracts.decision import DecisionSignal
from omni_engine.contracts.broker import (
    BrokerDecision,
    BrokerRoutingOutcome,
    FallbackReason,
    ProviderPolicyConfig,
    ProviderSelectionMode,
    TaskProviderOverride,
)
from omni_engine.providers.base import ProviderError, ProviderHealth, SystemOneProvider
from omni_engine.providers.broker import SystemOneBroker
from omni_engine.providers.system1 import (
    LayaProvider,
    _drain_inference_permits,
    _restore_inference_permits,
    evict_laya_model_if_idle,
    get_available_ram_mb,
    get_laya_concurrency,
    get_shared_laya_router,
    is_ram_pressure_critical,
    set_laya_concurrency,
)
from omni_engine.decision.calibration_eval import (
    compute_calibration_metrics,
    get_stratified_corpus_split,
)
from omni_engine.decision.concurrency_benchmark import run_concurrency_benchmark


class MockSystemOneProvider(SystemOneProvider):
    """Controllable mock provider for testing broker routing and failure handling."""

    def __init__(
        self,
        provider_id: str,
        healthy: bool = True,
        latency_ms: float = 10.0,
        configured: bool = True,
    ) -> None:
        self.provider_id = provider_id
        self.model_id = f"mock-{provider_id}"
        self.is_configured = configured
        self._healthy = healthy
        self._latency_ms = latency_ms

    def predict_signals(self, context, questions):
        if not self._healthy:
            raise ProviderError(
                code=ErrorCode.PROCESS_FAILED,
                message=f"{self.provider_id} simulated failure",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        return {
            q: DecisionSignal(
                signal_type=DecisionSignalType.INTENT,
                value="mock_choice",
                confidence=0.92,
                probabilities={"mock_choice": 0.92, "other": 0.08},
                provider_id=self.provider_id,
                model_id=self.model_id,
                decision_schema_version="1.0.0",
                calibration_version="mock-v1",
                latency_ms=self._latency_ms,
            )
            for q in questions
        }

    def classify(self, prompt, criteria, instructions="Classify:"):
        return self.predict_signals(context={"prompt": prompt}, questions={"classification": {}})["classification"]

    def score(self, prompt, criteria):
        return 0.88

    def health_check(self):
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=self._healthy,
            status_code=ErrorCode.UNKNOWN if self._healthy else ErrorCode.SERVICE_UNAVAILABLE,
            latency_ms=self._latency_ms,
            message="Mock operational" if self._healthy else "Mock unhealthy",
        )


class TestSystemOneBrokerUserLocked(unittest.TestCase):
    """Tests for USER_LOCKED mode sovereignty invariants."""

    def setUp(self):
        self.mock_laya = MockSystemOneProvider("laya_english", healthy=True, latency_ms=15.0)
        self.mock_jev = MockSystemOneProvider("jev", healthy=True, latency_ms=5.0)
        self.mock_typed = MockSystemOneProvider("laya_typed_decisions", healthy=True, latency_ms=12.0)
        self.providers = {
            "laya_english": self.mock_laya,
            "jev": self.mock_jev,
            "laya_typed_decisions": self.mock_typed,
        }

    def test_user_locked_selects_target_provider(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        prov, decision = broker.resolve_provider()

        self.assertEqual(prov.provider_id, "laya_english")
        self.assertEqual(decision.selected_provider, "laya_english")
        self.assertEqual(decision.outcome, BrokerRoutingOutcome.LAYA_ENGLISH)
        self.assertFalse(decision.fallback_occurred)

    def test_user_locked_rejects_disallowed_provider(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["laya_english"],
            preferred_provider="jev",  # not in allowlist
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider()
        self.assertEqual(ctx.exception.code, ErrorCode.UNAUTHORIZED_ACTION)
        self.assertIn("not in allowed_providers", str(ctx.exception))

    def test_user_locked_rejects_task_override(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(target_provider="jev")

        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider(task_override=override)
        self.assertEqual(ctx.exception.code, ErrorCode.UNAUTHORIZED_ACTION)
        self.assertIn("Task override 'jev' rejected", str(ctx.exception))

    def test_user_locked_refuses_silent_fallback_on_unhealthy(self):
        self.mock_laya._healthy = False
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)

        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider()
        self.assertIn("Silent fallback prohibited under USER_LOCKED", str(ctx.exception))

    def test_user_locked_rejects_conflicting_privacy_constraint(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["jev", "laya_english"],
            preferred_provider="jev",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(privacy_local_only=True)

        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider(task_override=override)
        self.assertEqual(ctx.exception.code, ErrorCode.UNAUTHORIZED_ACTION)
        self.assertIn("conflicts with USER_LOCKED remote provider", str(ctx.exception))


class TestSystemOneBrokerUserPreferred(unittest.TestCase):
    """Tests for USER_PREFERRED mode and explanatory fallback telemetry."""

    def setUp(self):
        self.mock_laya = MockSystemOneProvider("laya_english", healthy=True, latency_ms=15.0)
        self.mock_jev = MockSystemOneProvider("jev", healthy=True, latency_ms=5.0)
        self.mock_typed = MockSystemOneProvider("laya_typed_decisions", healthy=True, latency_ms=12.0)
        self.providers = {
            "laya_english": self.mock_laya,
            "jev": self.mock_jev,
            "laya_typed_decisions": self.mock_typed,
        }

    def test_user_preferred_default(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        prov, decision = broker.resolve_provider()

        self.assertEqual(prov.provider_id, "laya_english")
        self.assertFalse(decision.fallback_occurred)
        self.assertEqual(decision.fallback_reason, FallbackReason.NONE)

    def test_user_preferred_task_override_valid(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(target_provider="jev")
        prov, decision = broker.resolve_provider(task_override=override)

        self.assertEqual(prov.provider_id, "jev")
        self.assertEqual(decision.selected_provider, "jev")

    def test_user_preferred_task_override_disallowed(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english"],  # jev not allowed
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(target_provider="jev")

        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider(task_override=override)
        self.assertEqual(ctx.exception.code, ErrorCode.UNAUTHORIZED_ACTION)

    def test_user_preferred_fallback_on_unhealthy_with_telemetry(self):
        self.mock_laya._healthy = False  # Preferred fails
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        prov, decision = broker.resolve_provider()

        self.assertEqual(prov.provider_id, "jev")
        self.assertTrue(decision.fallback_occurred)
        self.assertEqual(decision.fallback_reason, FallbackReason.PROVIDER_UNHEALTHY)
        self.assertEqual(decision.target_provider, "laya_english")
        self.assertEqual(decision.selected_provider, "jev")

    def test_user_preferred_fallback_on_privacy_constraint(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["jev", "laya_english"],
            preferred_provider="jev",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(privacy_local_only=True)
        prov, decision = broker.resolve_provider(task_override=override)

        self.assertEqual(prov.provider_id, "laya_english")
        self.assertTrue(decision.fallback_occurred)
        self.assertEqual(decision.fallback_reason, FallbackReason.PRIVACY_RESTRICTION)

    def test_user_preferred_all_alternatives_exhausted(self):
        self.mock_laya._healthy = False
        self.mock_jev._healthy = False
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)

        with self.assertRaises(ProviderError) as ctx:
            broker.resolve_provider()
        self.assertEqual(ctx.exception.code, ErrorCode.SERVICE_UNAVAILABLE)


class TestSystemOneBrokerAuto(unittest.TestCase):
    """Tests for AUTO mode provider optimization."""

    def setUp(self):
        self.mock_laya = MockSystemOneProvider("laya_english", healthy=True, latency_ms=25.0)
        self.mock_jev = MockSystemOneProvider("jev", healthy=True, latency_ms=4.0)
        self.providers = {
            "laya_english": self.mock_laya,
            "jev": self.mock_jev,
        }

    def test_auto_mode_selects_healthy_provider(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.AUTO,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        prov, decision = broker.resolve_provider()

        self.assertIn(prov.provider_id, ["laya_english", "jev"])
        self.assertEqual(decision.selection_mode, ProviderSelectionMode.AUTO)

    def test_auto_mode_respects_privacy_local_only(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.AUTO,
            allowed_providers=["jev", "laya_english"],
            preferred_provider="jev",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(privacy_local_only=True)
        prov, decision = broker.resolve_provider(task_override=override)

        self.assertEqual(prov.provider_id, "laya_english")
        self.assertTrue(decision.is_local)

    def test_auto_mode_latency_priority(self):
        config = ProviderPolicyConfig(
            mode=ProviderSelectionMode.AUTO,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker = SystemOneBroker(policy_config=config, custom_providers=self.providers)
        override = TaskProviderOverride(latency_priority=True)
        prov, decision = broker.resolve_provider(task_override=override)

        # jev has 4.0ms latency vs laya 25.0ms
        self.assertEqual(prov.provider_id, "jev")


class TestConcurrencyAndLocking(unittest.TestCase):
    """Tests for concurrency controls, semaphore permits, and English-only invariant."""

    def test_concurrency_get_and_set(self):
        orig = get_laya_concurrency()
        try:
            set_laya_concurrency(2)
            self.assertEqual(get_laya_concurrency(), 2)
            set_laya_concurrency(1)
            self.assertEqual(get_laya_concurrency(), 1)
        finally:
            set_laya_concurrency(orig)

    def test_concurrency_negative_rejected(self):
        with self.assertRaises(ValueError):
            set_laya_concurrency(0)

    def test_drain_and_restore_permits(self):
        permits = _drain_inference_permits(timeout=2.0)
        self.assertEqual(permits, get_laya_concurrency())
        _restore_inference_permits(permits)

    def test_multilingual_model_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            LayaProvider(model_name="multilingual")
        self.assertIn("forbidden", str(ctx.exception).lower())

    def test_get_shared_router_rejects_multilingual(self):
        with self.assertRaises(ValueError) as ctx:
            get_shared_laya_router("multilingual")
        self.assertIn("forbidden", str(ctx.exception).lower())


class TestRAMTelemetryAndEviction(unittest.TestCase):
    """Tests for Windows RAM telemetry and debounced eviction."""

    def test_get_available_ram_mb(self):
        ram = get_available_ram_mb()
        self.assertGreater(ram, 0.0)

    def test_is_ram_pressure_critical_debouncing(self):
        # When RAM is plenty, critical check is False
        self.assertFalse(is_ram_pressure_critical(threshold_mb=1.0))

    def test_evict_laya_model_if_idle(self):
        # Should return boolean without raising
        result = evict_laya_model_if_idle()
        self.assertIsInstance(result, bool)


class TestStratifiedPartitionAndCalibration(unittest.TestCase):
    """Tests for 70/30 stratified dataset partitioning and ECE metric evaluation."""

    def test_stratified_split_sizes(self):
        dev, test = get_stratified_corpus_split()
        self.assertEqual(len(dev), 72)
        self.assertEqual(len(test), 31)
        self.assertEqual(len(dev) + len(test), 103)

        # Check domain distribution in test split
        test_domains = [c.expected_domain for c in test]
        self.assertEqual(test_domains.count("os"), 10)
        self.assertEqual(test_domains.count("dev"), 7)
        self.assertEqual(test_domains.count("data"), 4)
        self.assertEqual(test_domains.count("web"), 4)
        self.assertEqual(test_domains.count("general"), 4)
        self.assertEqual(test_domains.count("browser"), 2)

    def test_compute_calibration_metrics(self):
        # Well-calibrated distribution: high accuracy aligns with high confidence
        gt = ["os", "dev", "os", "web", "data"] * 10  # 50 items
        pred = ["os", "dev", "os", "web", "data"] * 9 + ["os", "dev", "os", "web", "os"]  # 49/50 correct (98%)
        conf = [0.96, 0.95, 0.97, 0.95, 0.94] * 10  # avg conf ~0.954, acc 0.98

        metrics = compute_calibration_metrics(
            ground_truth=gt,
            predictions=pred,
            confidences=conf,
            signal_name="domain",
            provider_id="mock_laya",
        )
        self.assertEqual(metrics.sample_count, 50)
        self.assertEqual(metrics.accuracy, 0.98)
        self.assertGreaterEqual(metrics.f1, 0.70)
        self.assertLess(metrics.ece, 0.15)
        self.assertTrue(metrics.is_calibrated)

    def test_calibration_gate_fails_under_insufficient_samples(self):
        gt = ["os", "dev"]
        pred = ["os", "dev"]
        conf = [0.9, 0.9]

        metrics = compute_calibration_metrics(
            ground_truth=gt,
            predictions=pred,
            confidences=conf,
            signal_name="domain",
            provider_id="mock_laya",
        )
        # N=2 < 30 -> must be marked uncalibrated
        self.assertFalse(metrics.is_calibrated)

    def test_calibration_gate_fails_when_overconfident(self):
        # Model is 100% confident on wrong predictions -> high ECE
        gt = ["os"] * 50
        pred = ["dev"] * 50  # 0% accuracy
        conf = [0.99] * 50   # 99% confidence

        metrics = compute_calibration_metrics(
            ground_truth=gt,
            predictions=pred,
            confidences=conf,
            signal_name="domain",
            provider_id="mock_laya",
        )
        self.assertEqual(metrics.accuracy, 0.0)
        self.assertGreater(metrics.ece, 0.50)
        self.assertFalse(metrics.is_calibrated)


class TestConcurrencyBenchmarkHarness(unittest.TestCase):
    """Tests for the concurrency benchmark harness."""

    def test_concurrency_benchmark_dry_run(self):
        res = run_concurrency_benchmark(concurrencies=[1, 2], num_requests=2, dry_run=True)
        self.assertIn("1", res["concurrencies"])
        self.assertIn("2", res["concurrencies"])

        stats_1 = res["concurrencies"]["1"]
        self.assertEqual(stats_1["requests_completed"], 2)
        self.assertEqual(stats_1["requests_failed"], 0)
        self.assertIn("throughput_req_per_sec", stats_1)
        self.assertIn("latency_p50_ms", stats_1)
        self.assertIn("latency_p95_ms", stats_1)


if __name__ == "__main__":
    unittest.main()
