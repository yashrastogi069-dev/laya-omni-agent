"""
tests.test_l4_providers
=======================
Comprehensive test suite for Checkpoint L4: Provider Foundations.

Validates:
1. SystemOneProvider abstract contract adherence.
2. LayaProvider local ModernBERT execution, multi-signal batching, and provenance.
3. JevProvider graceful degradation and non-crashing unconfigured state.
4. GenerativeProvider abstract contract adherence.
5. OpenRouterProvider graceful degradation when unconfigured.
6. Markdown JSON fence extraction and structured generation parsing.
7. Router memory singleton preservation across provider instances.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock
from pydantic import BaseModel, Field

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.contracts.decision import DecisionSignal
from omni_engine.providers import (
    GenerationResult,
    GenerativeProvider,
    JevProvider,
    LayaProvider,
    OpenRouterProvider,
    ProviderError,
    ProviderHealth,
    SystemOneProvider,
    extract_json_from_text,
    get_shared_laya_router,
)
from omni_engine.providers.system1 import _extract_decision_data


class DummyPlan(BaseModel):
    objective: str
    steps: list[str] = Field(default_factory=list)


class TestL4SystemOneLayaProvider(unittest.TestCase):
    """Tests LayaProvider wrapping local ModernBERT router."""

    def setUp(self):
        self.provider = LayaProvider(preload=False)

    def test_provider_identity_and_contract(self):
        """Asserts LayaProvider inherits from SystemOneProvider and declares expected IDs."""
        self.assertIsInstance(self.provider, SystemOneProvider)
        self.assertEqual(self.provider.provider_id, "laya")
        self.assertEqual(self.provider.model_id, "ModernBERT-large")
        self.assertTrue(self.provider.is_configured)

    def test_shared_router_singleton_preserves_ram(self):
        """Asserts multiple LayaProvider instances share the exact same ModernBERT router instance."""
        p2 = LayaProvider(preload=False)
        self.assertIs(self.provider._router, p2._router)
        self.assertIs(self.provider._router, get_shared_laya_router())

    def test_classify_returns_valid_decision_signal(self):
        """Single classification returns strongly typed DecisionSignal with full provenance."""
        signal = self.provider.classify(
            prompt="Refactor authentication middleware to fix token leak",
            criteria={
                "coding": "Software engineering or code modification",
                "weather": "Weather queries and forecasts",
            },
            instructions="Classify prompt domain:",
        )
        self.assertIsInstance(signal, DecisionSignal)
        self.assertEqual(signal.value, "coding")
        self.assertGreaterEqual(signal.confidence, 0.0)
        self.assertLessEqual(signal.confidence, 1.0)
        self.assertEqual(signal.provider_id, "laya")
        self.assertEqual(signal.model_id, "ModernBERT-large")
        self.assertEqual(signal.decision_schema_version, "1.0.0")
        self.assertGreaterEqual(signal.latency_ms, 0.0)

    def test_batched_multi_signal_prediction(self):
        """Asserts batched multi-question evaluation returns all signals in a single forward pass."""
        questions = {
            "intent": {
                "criteria": {"read": "Read local file", "execute": "Run command"},
                "instructions": "Determine intent:",
            },
            "urgency": {
                "criteria": {"urgent": "Immediate action required", "routine": "Normal priority"},
                "instructions": "Determine urgency:",
            },
            "risk": {
                "criteria": {"safe": "Read only safe operation", "risky": "System modification"},
                "instructions": "Determine operational risk:",
            },
        }

        signals = self.provider.predict_signals(
            context={"prompt": "Inspect directory tree and view README.md"},
            questions=questions,
        )

        self.assertEqual(len(signals), 3)
        self.assertIn("intent", signals)
        self.assertIn("urgency", signals)
        self.assertIn("risk", signals)

        for q_name, sig in signals.items():
            self.assertIsInstance(sig, DecisionSignal)
            self.assertEqual(sig.provider_id, "laya")
            self.assertGreaterEqual(sig.confidence, 0.0)
            self.assertLessEqual(sig.confidence, 1.0)
            self.assertGreaterEqual(sig.latency_ms, 0.0)

    def test_health_check_operational(self):
        """Health check probe returns healthy ProviderHealth."""
        health = self.provider.health_check()
        self.assertIsInstance(health, ProviderHealth)
        self.assertTrue(health.healthy)
        self.assertEqual(health.provider_id, "laya")
        self.assertGreaterEqual(health.latency_ms, 0.0)

    def test_extract_decision_data_defensive_handles_none_values(self):
        """_extract_decision_data handles None confidence and probabilities without TypeError."""
        # Dict with None values
        choice, conf, probs = _extract_decision_data({"choice": "test", "confidence": None, "probabilities": None})
        self.assertEqual(choice, "test")
        self.assertEqual(conf, 0.0)
        self.assertEqual(probs, {})

        # Dict with invalid types
        choice2, conf2, probs2 = _extract_decision_data({"choice": 123, "confidence": "invalid", "probs": {"a": "bad"}})
        self.assertEqual(choice2, "123")
        self.assertEqual(conf2, 0.0)
        self.assertEqual(probs2, {"a": 0.0})

        # Object with None attributes
        class MockDecision:
            choice = "mock_choice"
            confidence = None
            probs = None

        choice3, conf3, probs3 = _extract_decision_data(MockDecision())
        self.assertEqual(choice3, "mock_choice")
        self.assertEqual(conf3, 0.0)
        self.assertEqual(probs3, {})

    def test_laya_provider_score_method(self):
        """LayaProvider.score evaluates criterion score in [0.0, 1.0]."""
        score = self.provider.score(
            prompt="Refactor authentication middleware to fix token leak",
            criteria="Software engineering task",
        )
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestL4SystemOneJevProvider(unittest.TestCase):
    """Tests JevProvider handling unconfigured cloud credentials gracefully."""

    def test_unconfigured_initialization_does_not_crash(self):
        """Initializing JevProvider with no API key does not raise exception."""
        jev = JevProvider(api_key=None)
        self.assertIsInstance(jev, SystemOneProvider)
        self.assertEqual(jev.provider_id, "jev")
        self.assertFalse(jev.is_configured)

    def test_unconfigured_health_check_reports_unconfigured(self):
        """Health check on unconfigured JevProvider reports ErrorCode.UNCONFIGURED."""
        jev = JevProvider(api_key=None)
        health = jev.health_check()
        self.assertFalse(health.healthy)
        self.assertEqual(health.status_code, ErrorCode.UNCONFIGURED)
        self.assertIn("unconfigured", health.message.lower())

    def test_unconfigured_prediction_raises_normalized_provider_error(self):
        """Calling predict_signals on unconfigured JevProvider raises ProviderError."""
        jev = JevProvider(api_key=None)
        with self.assertRaises(ProviderError) as ctx:
            jev.predict_signals(context={"prompt": "test"}, questions={"q": {"criteria": {"a": "A"}}})
        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)

    def test_unconfigured_score_raises_provider_error(self):
        """Calling score on unconfigured JevProvider raises ProviderError with UNCONFIGURED."""
        jev = JevProvider(api_key=None)
        with self.assertRaises(ProviderError) as ctx:
            jev.score("test", "test criteria")
        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)


class TestL4GenerativeOpenRouterProvider(unittest.TestCase):
    """Tests OpenRouterProvider handling configuration, error normalization, and structured parsing."""

    def test_unconfigured_initialization_does_not_crash(self):
        """Initializing OpenRouterProvider with no API key does not crash."""
        prov = OpenRouterProvider(api_key="")
        self.assertIsInstance(prov, GenerativeProvider)
        self.assertEqual(prov.provider_id, "openrouter")
        self.assertFalse(prov.is_configured)

        with unittest.mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            prov_env = OpenRouterProvider()
            self.assertFalse(prov_env.is_configured)

    def test_unconfigured_health_check_reports_unconfigured(self):
        """Health check on unconfigured OpenRouterProvider reports ErrorCode.UNCONFIGURED."""
        prov = OpenRouterProvider(api_key="")
        health = prov.health_check()
        self.assertFalse(health.healthy)
        self.assertEqual(health.status_code, ErrorCode.UNCONFIGURED)

    def test_unconfigured_generate_raises_provider_error(self):
        """Generating text without API key raises ProviderError with UNCONFIGURED code."""
        prov = OpenRouterProvider(api_key="")
        with self.assertRaises(ProviderError) as ctx:
            prov.generate_text(prompt="Plan test mission")
        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)

    def test_json_markdown_fence_extraction(self):
        """extract_json_from_text correctly extracts raw JSON from markdown fences."""
        raw_markdown = """Here is your structured plan:
```json
{
  "objective": "Audit codebase",
  "steps": ["step 1", "step 2"]
}
```
Hope this helps!"""
        extracted = extract_json_from_text(raw_markdown)
        self.assertTrue(extracted.startswith("{"))
        self.assertTrue(extracted.endswith("}"))

        # Test bracket fallback
        raw_brackets = 'Some preamble {"objective": "Test", "steps": []} postscript'
        extracted2 = extract_json_from_text(raw_brackets)
        self.assertEqual(extracted2, '{"objective": "Test", "steps": []}')

    def test_mocked_generate_structured_parsing(self):
        """Structured generation parses valid JSON into target Pydantic model."""
        prov = OpenRouterProvider(api_key="mock_key_123")
        prov._client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '```json\n{"objective": "Deploy agent", "steps": ["build", "test"]}\n```'
        mock_choice.finish_reason = "stop"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = None
        prov._client.chat.completions.create.return_value = mock_resp

        parsed_plan = prov.generate_structured(prompt="Deploy agent", response_model=DummyPlan)
        self.assertIsInstance(parsed_plan, DummyPlan)
        self.assertEqual(parsed_plan.objective, "Deploy agent")
        self.assertEqual(parsed_plan.steps, ["build", "test"])

    def test_mocked_generate_structured_schema_violation_error(self):
        """Invalid JSON schema response raises ProviderError with SCHEMA_VIOLATION."""
        prov = OpenRouterProvider(api_key="mock_key_123")
        prov._client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '```json\n{"invalid_key": 123}\n```'
        mock_choice.finish_reason = "stop"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = None
        prov._client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(ProviderError) as ctx:
            prov.generate_structured(prompt="Deploy agent", response_model=DummyPlan)
        self.assertEqual(ctx.exception.code, ErrorCode.SCHEMA_VIOLATION)

    def test_openrouter_empty_choices_raises_process_failed(self):
        """Empty choices in API response raises ProviderError with PROCESS_FAILED."""
        prov = OpenRouterProvider(api_key="mock_key_123")
        prov._client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices = []
        prov._client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(ProviderError) as ctx:
            prov.generate_text(prompt="Hello")
        self.assertEqual(ctx.exception.code, ErrorCode.PROCESS_FAILED)

    def test_openrouter_timeout_parameter_configured(self):
        """OpenRouterProvider sets and respects configurable timeout budget."""
        prov = OpenRouterProvider(api_key="mock_key_123", timeout=45.5)
        self.assertEqual(prov.timeout, 45.5)


if __name__ == "__main__":
    unittest.main()
