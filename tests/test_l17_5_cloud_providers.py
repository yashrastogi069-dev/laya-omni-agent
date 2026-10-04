"""
tests.test_l17_5_cloud_providers
================================
Unit and adversarial tests for Checkpoint L17.5:
Real Cloud Provider Integration (OpenAI, Anthropic, DeepSeek).

Verifies:
1. DirectOpenAIProvider: mock client execution, unconfigured state, secret redaction, structured output.
2. AnthropicProvider: Messages API format, max_tokens enforcement, temperature clamping,
   content block traversal, schema violation handling, error code normalization, secret redaction.
3. DeepSeekProvider: OpenAI-compatible configuration, default endpoint, and routing.
4. GenerativeRouter Integration: multi-provider URI routing (openai:, anthropic:, deepseek:),
   unconfigured provider cascading, and User Sovereignty enforcement.
"""

from typing import Any, Dict, List, Optional
import unittest
from unittest.mock import MagicMock
from pydantic import BaseModel, Field

from omni_engine.contracts.enums import ErrorCode
from omni_engine.contracts.router import (
    AgentRole,
    ModelTier,
    ModelSovereigntyLevel,
    RoleRouteConfig,
    RouterTelemetry,
)
from omni_engine.providers.base import (
    GenerativeProvider,
    GenerationResult,
    ProviderError,
    ProviderHealth,
)
from omni_engine.providers.cloud import (
    AnthropicProvider,
    DeepSeekProvider,
    DirectOpenAIProvider,
    build_standard_generative_router,
    sanitize_provider_error,
)
from omni_engine.providers.router import GenerativeRouter, MockGenerativeProvider


class SamplePlan(BaseModel):
    title: str
    steps: List[str]


class TestDirectOpenAIProvider(unittest.TestCase):
    """Unit tests for DirectOpenAIProvider with mock client."""

    def test_unconfigured_initialization_does_not_throw(self) -> None:
        """Invariant: provider with missing API key must not crash __init__."""
        provider = DirectOpenAIProvider(api_key="")
        self.assertFalse(provider.is_configured)
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="Hello")
        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)

    def test_empty_prompt_rejection(self) -> None:
        mock_client = MagicMock()
        provider = DirectOpenAIProvider(api_key="test-key", client=mock_client)
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="   ")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_ARGUMENT)

    def test_generate_text_with_mock_client(self) -> None:
        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI response"
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 15
        mock_usage.completion_tokens = 25

        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        provider = DirectOpenAIProvider(api_key="test-key", client=mock_client)
        res = provider.generate_text(
            prompt="Hello world",
            system_prompt="Be concise",
            temperature=0.4,
            max_tokens=500,
            model="gpt-4o-mini",
            timeout=30.0,
        )

        self.assertEqual(res.text, "OpenAI response")
        self.assertEqual(res.provider_id, "openai")
        self.assertEqual(res.model_id, "gpt-4o-mini")
        self.assertEqual(res.prompt_tokens, 15)
        self.assertEqual(res.completion_tokens, 25)

        # Verify call arguments passed to OpenAI SDK
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "gpt-4o-mini")
        self.assertEqual(call_kwargs["temperature"], 0.4)
        self.assertEqual(call_kwargs["max_tokens"], 500)
        self.assertEqual(call_kwargs["timeout"], 30.0)
        self.assertEqual(call_kwargs["messages"], [
            {"role": "system", "content": "Be concise"},
            {"role": "user", "content": "Hello world"},
        ])

    def test_generate_structured_with_mock_client(self) -> None:
        mock_choice = MagicMock()
        mock_choice.message.content = '{"title": "Test Plan", "steps": ["s1", "s2"]}'
        mock_choice.finish_reason = "stop"

        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = None

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_resp

        provider = DirectOpenAIProvider(api_key="test-key", client=mock_client)
        plan = provider.generate_structured(prompt="Plan", response_model=SamplePlan)
        self.assertIsInstance(plan, SamplePlan)
        self.assertEqual(plan.title, "Test Plan")
        self.assertEqual(len(plan.steps), 2)

    def test_secret_redaction_in_exception(self) -> None:
        secret_key = "sk-proj-super-secret-key-12345678901234"
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError(f"Failed with key {secret_key}")

        provider = DirectOpenAIProvider(api_key=secret_key, client=mock_client)
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="Test")

        err_str = str(ctx.exception)
        self.assertNotIn(secret_key, err_str)
        self.assertIn("[REDACTED_API_KEY]", err_str)

    def test_repr_does_not_leak_key(self) -> None:
        secret_key = "sk-live-confidential-secret-key-9999"
        provider = DirectOpenAIProvider(api_key=secret_key)
        self.assertNotIn(secret_key, repr(provider))


class TestAnthropicProvider(unittest.TestCase):
    """Unit tests for AnthropicProvider with mock transport."""

    def test_unconfigured_initialization_does_not_throw(self) -> None:
        provider = AnthropicProvider(api_key="")
        self.assertFalse(provider.is_configured)
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="Hello")
        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)

    def test_empty_prompt_rejection(self) -> None:
        provider = AnthropicProvider(api_key="ant-key")
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="")
        self.assertEqual(ctx.exception.code, ErrorCode.INVALID_ARGUMENT)

    def test_messages_api_payload_and_traversal(self) -> None:
        """REV-17.5-01, 02, 06: verifies Messages API schema, max_tokens, temp clamp, and text joining."""
        captured_payload = {}
        captured_timeout = 0.0

        def mock_transport(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            nonlocal captured_payload, captured_timeout
            captured_payload = payload
            captured_timeout = timeout
            return {
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Hello, "},
                    {"type": "thinking", "thinking": "internal thought block"},
                    {"type": "text", "text": "I am Claude."},
                ],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 8},
            }

        provider = AnthropicProvider(api_key="sk-ant-test-key", transport_fn=mock_transport)
        res = provider.generate_text(
            prompt="Hello",
            system_prompt="You are helpful.",
            temperature=1.8,  # Must be clamped to 1.0!
            max_tokens=1500,
            model="claude-3-5-haiku",
            timeout=25.0,
        )

        # Multi-block text traversal verification (REV-17.5-06)
        self.assertEqual(res.text, "Hello, I am Claude.")
        self.assertEqual(res.prompt_tokens, 12)
        self.assertEqual(res.completion_tokens, 8)
        self.assertEqual(res.finish_reason, "end_turn")

        # Payload structure verification (REV-17.5-01, 02)
        self.assertEqual(captured_payload["model"], "claude-3-5-haiku")
        self.assertEqual(captured_payload["max_tokens"], 1500)
        self.assertEqual(captured_payload["temperature"], 1.0)  # Clamped!
        self.assertEqual(captured_payload["system"], "You are helpful.")
        self.assertEqual(captured_payload["messages"], [{"role": "user", "content": "Hello"}])
        self.assertEqual(captured_timeout, 25.0)

    def test_temperature_lower_bound_clamping(self) -> None:
        captured_payload = {}

        def mock_transport(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            nonlocal captured_payload
            captured_payload = payload
            return {"content": [{"type": "text", "text": "ok"}]}

        provider = AnthropicProvider(api_key="test", transport_fn=mock_transport)
        provider.generate_text(prompt="Hi", temperature=-0.5)
        self.assertEqual(captured_payload["temperature"], 0.0)

    def test_structured_generation_with_strict_preamble_framing(self) -> None:
        """REV-17.5-05: strict system framing prevents conversational preambles."""
        captured_system = ""

        def mock_transport(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            nonlocal captured_system
            captured_system = payload.get("system", "")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": '```json\n{"title": "Anthropic Plan", "steps": ["stepA", "stepB"]}\n```',
                    }
                ]
            }

        provider = AnthropicProvider(api_key="test", transport_fn=mock_transport)
        plan = provider.generate_structured(prompt="Make plan", response_model=SamplePlan)
        self.assertEqual(plan.title, "Anthropic Plan")
        self.assertEqual(plan.steps, ["stepA", "stepB"])
        self.assertIn("CRITICAL INSTRUCTION", captured_system)
        self.assertIn("JSON Schema", captured_system)

    def test_error_code_normalization_and_secret_redaction(self) -> None:
        """REV-17.5-03: verifies error mapping and key scrubbing."""
        secret_key = "sk-ant-api03-super-secret-key-abcdef123456"

        def mock_failing_transport(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            raise RuntimeError(f"HTTP 401: Unauthorized request with key {secret_key}")

        provider = AnthropicProvider(api_key=secret_key, transport_fn=mock_failing_transport)
        with self.assertRaises(ProviderError) as ctx:
            provider.generate_text(prompt="Test")

        self.assertEqual(ctx.exception.code, ErrorCode.AUTH_REQUIRED)
        err_msg = str(ctx.exception)
        self.assertNotIn(secret_key, err_msg)
        self.assertIn("[REDACTED_API_KEY]", err_msg)

    def test_repr_does_not_leak_key(self) -> None:
        secret_key = "sk-ant-api03-confidential-token-999"
        provider = AnthropicProvider(api_key=secret_key)
        self.assertNotIn(secret_key, repr(provider))


class TestDeepSeekProvider(unittest.TestCase):
    """Unit tests for DeepSeekProvider."""

    def test_default_attributes_and_configuration(self) -> None:
        provider = DeepSeekProvider(api_key="ds-key")
        self.assertEqual(provider.provider_id, "deepseek")
        self.assertEqual(provider.model_id, "deepseek-chat")
        self.assertEqual(provider.base_url, "https://api.deepseek.com")
        self.assertTrue(provider.is_configured)
        self.assertNotIn("ds-key", repr(provider))


class TestGenerativeRouterCloudIntegration(unittest.TestCase):
    """Integration tests verifying cloud provider URI dispatch and fallbacks in GenerativeRouter."""

    def setUp(self) -> None:
        # Mock OpenAI client
        mock_choice = MagicMock()
        mock_choice.message.content = "OpenAI response"
        mock_choice.finish_reason = "stop"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_resp.usage = None
        self.mock_openai_client = MagicMock()
        self.mock_openai_client.chat.completions.create.return_value = mock_resp
        self.openai_prov = DirectOpenAIProvider(api_key="oa-key", client=self.mock_openai_client)

        # Mock Anthropic transport
        def anthropic_mock_transport(payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
            return {"content": [{"type": "text", "text": "Anthropic response"}]}
        self.anthropic_prov = AnthropicProvider(api_key="ant-key", transport_fn=anthropic_mock_transport)

        # Unconfigured DeepSeek provider
        self.deepseek_unconfigured = DeepSeekProvider(api_key="")

        # Router with direct cloud providers
        self.router = GenerativeRouter(
            providers={
                "openai": self.openai_prov,
                "anthropic": self.anthropic_prov,
                "deepseek": self.deepseek_unconfigured,
            },
            default_provider_id="openai",
        )

    def test_uri_scheme_dispatch_to_direct_providers(self) -> None:
        """Candidate strings with 'provider:model' route directly to target provider."""
        # 1. Route to Anthropic
        cfg_plan = RoleRouteConfig(
            role=AgentRole.PLANNER,
            primary_model="anthropic:claude-3-5-sonnet",
        )
        self.router.configure_role(AgentRole.PLANNER, cfg_plan)
        res_ant, telem_ant = self.router.generate_text_with_telemetry(
            role=AgentRole.PLANNER,
            prompt="Plan goal",
        )
        self.assertEqual(res_ant.text, "Anthropic response")
        self.assertEqual(telem_ant.selected_provider_id, "anthropic")
        self.assertEqual(telem_ant.selected_model_id, "claude-3-5-sonnet")

        # 2. Route to OpenAI
        cfg_code = RoleRouteConfig(
            role=AgentRole.CODING,
            primary_model="openai:gpt-4o",
        )
        self.router.configure_role(AgentRole.CODING, cfg_code)
        res_oa, telem_oa = self.router.generate_text_with_telemetry(
            role=AgentRole.CODING,
            prompt="Write code",
        )
        self.assertEqual(res_oa.text, "OpenAI response")
        self.assertEqual(telem_oa.selected_provider_id, "openai")
        self.assertEqual(telem_oa.selected_model_id, "gpt-4o")

    def test_unconfigured_cloud_provider_cascades_transparently(self) -> None:
        """DeepSeek is unconfigured; router cascades to configured Anthropic fallback."""
        cfg_cascade = RoleRouteConfig(
            role=AgentRole.CODING,
            primary_model="deepseek:deepseek-chat",
            fallback_models=["anthropic:claude-3-5-sonnet"],
            sovereignty=ModelSovereigntyLevel.AUTO,
        )
        self.router.configure_role(AgentRole.CODING, cfg_cascade)

        res, telemetry = self.router.generate_text_with_telemetry(
            role=AgentRole.CODING,
            prompt="Code task",
        )

        self.assertEqual(res.text, "Anthropic response")
        self.assertEqual(telemetry.selected_provider_id, "anthropic")
        self.assertEqual(telemetry.attempts, 2)
        self.assertTrue(telemetry.was_fallback)
        self.assertIn("deepseek", telemetry.fallback_reason.lower())

    def test_user_locked_unconfigured_cloud_provider_fails_fast(self) -> None:
        """Invariant: USER_LOCKED to unconfigured provider strictly aborts without fallback."""
        cfg_locked = RoleRouteConfig(
            role=AgentRole.CODING,
            primary_model="deepseek:deepseek-chat",
            fallback_models=["anthropic:claude-3-5-sonnet"],
            sovereignty=ModelSovereigntyLevel.USER_LOCKED,
        )
        self.router.configure_role(AgentRole.CODING, cfg_locked)

        with self.assertRaises(ProviderError) as ctx:
            self.router.generate_text_for_role(role=AgentRole.CODING, prompt="Code task")

        self.assertEqual(ctx.exception.code, ErrorCode.UNCONFIGURED)
        self.assertIn("deepseek", str(ctx.exception).lower())

    def test_build_standard_generative_router_factory(self) -> None:
        """build_standard_generative_router wires direct cloud providers and mock."""
        mock = MockGenerativeProvider(provider_id="mock", default_text="Mock factory text")
        router = build_standard_generative_router(
            openrouter_api_key="test-or",
            openai_api_key="test-oa",
            anthropic_api_key="test-ant",
            deepseek_api_key="test-ds",
            mock_provider=mock,
            default_provider_id="mock",
        )

        self.assertIn("openrouter", router.providers)
        self.assertIn("openai", router.providers)
        self.assertIn("anthropic", router.providers)
        self.assertIn("deepseek", router.providers)
        self.assertIn("mock", router.providers)

        res = router.generate_text(prompt="Test prompt")
        self.assertEqual(res.text, "Mock factory text")


if __name__ == "__main__":
    unittest.main()
