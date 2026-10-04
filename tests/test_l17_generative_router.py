"""
tests.test_l17_generative_router
================================
Targeted unit and adversarial tests for Checkpoint L17:
Role-Aware Generative Provider Router, Model Tiers, and User Sovereignty.
"""

from concurrent.futures import ThreadPoolExecutor
import time
import unittest
from typing import List, Optional
from pydantic import BaseModel, Field

from omni_engine.contracts.enums import ErrorCode
from omni_engine.contracts.router import (
    AgentRole,
    ModelTier,
    ModelSovereigntyLevel,
    RoleRouteConfig,
    RouterTelemetry,
    DEFAULT_ROLE_CONFIGS,
)
from omni_engine.providers.base import (
    GenerativeProvider,
    GenerationResult,
    ProviderError,
    ProviderHealth,
)
from omni_engine.providers.router import GenerativeRouter, MockGenerativeProvider


class SamplePlanOutput(BaseModel):
    plan_name: str
    steps: List[str]
    timeout_s: float = 60.0


class SampleArgOutput(BaseModel):
    query: str
    limit: int = 10


class TestMockGenerativeProvider(unittest.TestCase):
    """Unit tests for MockGenerativeProvider capabilities."""

    def setUp(self) -> None:
        self.mock = MockGenerativeProvider(provider_id="mock_test", model_id="test-model")

    def test_default_text_and_history(self) -> None:
        res = self.mock.generate_text(prompt="Hello", system_prompt="Sys")
        self.assertEqual(res.text, "Mock response")
        self.assertEqual(res.model_id, "test-model")
        self.assertEqual(len(self.mock.invocation_history), 1)
        self.assertEqual(self.mock.invocation_history[0]["prompt"], "Hello")

    def test_fifo_queue_text_and_exceptions(self) -> None:
        self.mock.enqueue_response("First queued response")
        self.mock.enqueue_response(ProviderError(code=ErrorCode.RATE_LIMITED, message="Rate limited"))
        self.mock.enqueue_response("Third queued response")

        # 1: Success
        res1 = self.mock.generate_text(prompt="Prompt 1")
        self.assertEqual(res1.text, "First queued response")

        # 2: Rate limited exception
        with self.assertRaises(ProviderError) as ctx:
            self.mock.generate_text(prompt="Prompt 2")
        self.assertEqual(ctx.exception.code, ErrorCode.RATE_LIMITED)

        # 3: Next queued success
        res3 = self.mock.generate_text(prompt="Prompt 3")
        self.assertEqual(res3.text, "Third queued response")

    def test_per_model_responses_and_errors(self) -> None:
        self.mock.set_model_response("fast-model", "Fast answer")
        self.mock.set_model_error("flaky-model", ErrorCode.TIMEOUT)

        # Fast model
        res_fast = self.mock.generate_text(prompt="Q", model="fast-model")
        self.assertEqual(res_fast.text, "Fast answer")
        self.assertEqual(res_fast.model_id, "fast-model")

        # Flaky model
        with self.assertRaises(ProviderError) as ctx:
            self.mock.generate_text(prompt="Q", model="flaky-model")
        self.assertEqual(ctx.exception.code, ErrorCode.TIMEOUT)

    def test_structured_validation(self) -> None:
        # Scripted JSON string
        valid_json = '{"plan_name": "Test Plan", "steps": ["step1", "step2"], "timeout_s": 30.0}'
        self.mock.enqueue_response(valid_json)

        res = self.mock.generate_structured(prompt="Plan please", response_model=SamplePlanOutput)
        self.assertEqual(res.plan_name, "Test Plan")
        self.assertEqual(len(res.steps), 2)
        self.assertEqual(res.timeout_s, 30.0)

    def test_structured_validation_failure(self) -> None:
        # Malformed JSON
        self.mock.enqueue_response('{"plan_name": "Incomplete"}')  # missing required 'steps'

        with self.assertRaises(ProviderError) as ctx:
            self.mock.generate_structured(prompt="Plan please", response_model=SamplePlanOutput)
        self.assertEqual(ctx.exception.code, ErrorCode.SCHEMA_VIOLATION)

    def test_generate_alias_and_health_check(self) -> None:
        text = self.mock.generate(prompt="Quick test")
        self.assertEqual(text, "Mock response")

        health = self.mock.health_check()
        self.assertTrue(health.healthy)
        self.assertEqual(health.provider_id, "mock_test")


class TestGenerativeRouterRoleDispatch(unittest.TestCase):
    """Unit tests for role-based routing and tier defaults."""

    def setUp(self) -> None:
        self.mock_fast = MockGenerativeProvider(provider_id="mock_fast", model_id="fast-model")
        self.mock_capable = MockGenerativeProvider(provider_id="mock_capable", model_id="capable-model")
        self.providers = {
            "mock_fast": self.mock_fast,
            "mock_capable": self.mock_capable,
        }
        self.router = GenerativeRouter(providers=self.providers, default_provider_id="mock_capable")

    def test_dispatch_all_five_roles(self) -> None:
        roles = [
            AgentRole.ARGUMENT_WRITER,
            AgentRole.PLANNER,
            AgentRole.REPLANNER,
            AgentRole.FINALIZER,
            AgentRole.CODING,
        ]

        for role in roles:
            res = self.router.generate_text_for_role(role=role, prompt=f"Task for {role.value}")
            self.assertIn("router_telemetry", res.metadata)
            telemetry = res.metadata["router_telemetry"]
            self.assertEqual(telemetry["role"], role.value)
            self.assertEqual(telemetry["attempts"], 1)
            self.assertFalse(telemetry["was_fallback"])

        history = self.router.get_telemetry_history()
        self.assertEqual(len(history), 5)

    def test_typed_telemetry_methods(self) -> None:
        self.router.pin_model(
            role=AgentRole.ARGUMENT_WRITER,
            model_id="openai/gpt-4o-mini",
            provider_id="mock_fast",
            locked=False,
        )
        self.mock_fast.set_model_response("openai/gpt-4o-mini", '{"query": "machine learning", "limit": 5}')
        
        # Text with telemetry
        gen_res, text_telemetry = self.router.generate_text_with_telemetry(
            role=AgentRole.ARGUMENT_WRITER,
            prompt="Extract arg",
        )
        self.assertIsInstance(gen_res, GenerationResult)
        self.assertIsInstance(text_telemetry, RouterTelemetry)
        self.assertEqual(text_telemetry.role, AgentRole.ARGUMENT_WRITER)

        # Structured with telemetry
        structured_res, struct_telemetry = self.router.generate_structured_with_telemetry(
            role=AgentRole.ARGUMENT_WRITER,
            prompt="Extract arg structured",
            response_model=SampleArgOutput,
        )
        self.assertIsInstance(structured_res, SampleArgOutput)
        self.assertIsInstance(struct_telemetry, RouterTelemetry)
        self.assertEqual(structured_res.query, "machine learning")
        self.assertEqual(structured_res.limit, 5)


class TestGenerativeRouterUserSovereignty(unittest.TestCase):
    """Adversarial tests for USER_LOCKED, USER_PREFERRED, and AUTO sovereignty levels."""

    def setUp(self) -> None:
        self.mock_provider = MockGenerativeProvider(provider_id="mock", model_id="default-model")
        self.router = GenerativeRouter(
            providers={"mock": self.mock_provider},
            default_provider_id="mock",
        )

    def test_user_locked_strictly_forbids_fallback(self) -> None:
        """Invariant: USER_LOCKED must abort immediately on failure without trying fallbacks."""
        # Pin model as USER_LOCKED
        self.router.pin_model(
            role=AgentRole.PLANNER,
            model_id="locked-primary",
            provider_id="mock",
            locked=True,
        )
        # Configure the locked model to fail with a recoverable error
        self.mock_provider.set_model_error("locked-primary", ErrorCode.RATE_LIMITED)
        # Configure a fallback model that would succeed if cascade were allowed
        self.mock_provider.set_model_response("fallback-model", "Fallback plan")

        # Must raise ProviderError immediately; MUST NOT cascade!
        with self.assertRaises(ProviderError) as ctx:
            self.router.generate_text_for_role(role=AgentRole.PLANNER, prompt="Create plan")

        self.assertEqual(ctx.exception.code, ErrorCode.RATE_LIMITED)
        # Verify only 1 attempt was made
        history = self.router.get_telemetry_history(role=AgentRole.PLANNER)
        self.assertEqual(len(history), 0)  # No successful telemetry recorded

    def test_user_preferred_cascades_with_telemetry(self) -> None:
        """Invariant: USER_PREFERRED attempts preferred model first, cascades on recoverable error."""
        # Pin model as USER_PREFERRED (locked=False)
        self.router.pin_model(
            role=AgentRole.PLANNER,
            model_id="preferred-model",
            provider_id="mock",
            locked=False,
        )
        # Preferred model fails with timeout
        self.mock_provider.set_model_error("preferred-model", ErrorCode.TIMEOUT)
        # Fallback succeeds
        fallback_model = DEFAULT_ROLE_CONFIGS[AgentRole.PLANNER].fallback_models[0]
        self.mock_provider.set_model_response(fallback_model, "Successful fallback plan")

        res, telemetry = self.router.generate_text_with_telemetry(
            role=AgentRole.PLANNER,
            prompt="Plan task",
        )

        self.assertEqual(res.text, "Successful fallback plan")
        self.assertEqual(telemetry.requested_model, "preferred-model")
        self.assertEqual(telemetry.selected_model_id, fallback_model)
        self.assertEqual(telemetry.attempts, 2)
        self.assertTrue(telemetry.was_fallback)
        self.assertIsNotNone(telemetry.fallback_reason)
        self.assertIn("preferred-model", telemetry.fallback_reason)

    def test_auto_tier_cascades_transparently(self) -> None:
        """AUTO dynamically cascades through fallback models on recoverable errors."""
        primary = DEFAULT_ROLE_CONFIGS[AgentRole.CODING].primary_model
        fb1 = DEFAULT_ROLE_CONFIGS[AgentRole.CODING].fallback_models[0]

        # Primary model is rate-limited
        self.mock_provider.set_model_error(primary, ErrorCode.RATE_LIMITED)
        self.mock_provider.set_model_response(fb1, "def solution(): pass")

        res, telemetry = self.router.generate_text_with_telemetry(
            role=AgentRole.CODING,
            prompt="Write code",
        )

        self.assertEqual(res.text, "def solution(): pass")
        self.assertEqual(telemetry.attempts, 2)
        self.assertTrue(telemetry.was_fallback)
        self.assertEqual(telemetry.selected_model_id, fb1)

    def test_pin_model_validation(self) -> None:
        """Configuring unknown provider raises ValueError immediately."""
        with self.assertRaises(ValueError) as ctx:
            self.router.pin_model(
                role=AgentRole.FINALIZER,
                model_id="some-model",
                provider_id="non_existent_provider",
            )
        self.assertIn("is not registered", str(ctx.exception))

    def test_unpin_restores_auto(self) -> None:
        self.router.pin_model(role=AgentRole.PLANNER, model_id="custom", locked=True)
        self.assertEqual(self.router.get_role_config(AgentRole.PLANNER).sovereignty, ModelSovereigntyLevel.USER_LOCKED)

        self.router.unpin_model(AgentRole.PLANNER)
        cfg = self.router.get_role_config(AgentRole.PLANNER)
        self.assertEqual(cfg.sovereignty, ModelSovereigntyLevel.AUTO)
        self.assertIsNone(cfg.pinned_model_id)


class TestGenerativeRouterCascadesAndFailures(unittest.TestCase):
    """Tests for cascade error classification, schema violations, and provider exhaustion."""

    def setUp(self) -> None:
        self.mock_provider = MockGenerativeProvider(provider_id="mock", model_id="default-model")
        self.router = GenerativeRouter(
            providers={"mock": self.mock_provider},
            default_provider_id="mock",
        )

    def test_structured_schema_violation_cascade(self) -> None:
        """Structured generation schema violation is recoverable, cascading to capable model."""
        primary = DEFAULT_ROLE_CONFIGS[AgentRole.PLANNER].primary_model
        fb1 = DEFAULT_ROLE_CONFIGS[AgentRole.PLANNER].fallback_models[0]

        # Primary produces invalid JSON schema
        self.mock_provider.set_model_response(primary, '{"plan_name": "Broken plan"}')  # missing 'steps'
        # Fallback produces valid schema
        self.mock_provider.set_model_response(
            fb1,
            '{"plan_name": "Valid fallback plan", "steps": ["step1", "step2"], "timeout_s": 45.0}',
        )

        res, telemetry = self.router.generate_structured_with_telemetry(
            role=AgentRole.PLANNER,
            prompt="Make plan",
            response_model=SamplePlanOutput,
        )

        self.assertEqual(res.plan_name, "Valid fallback plan")
        self.assertEqual(telemetry.attempts, 2)
        self.assertTrue(telemetry.was_fallback)
        self.assertIn(primary, telemetry.fallback_reason)

    def test_fatal_error_aborts_cascade_immediately(self) -> None:
        """Non-recoverable fatal error (e.g. CANCELLED or UNAUTHORIZED) aborts without fallback."""
        primary = DEFAULT_ROLE_CONFIGS[AgentRole.PLANNER].primary_model
        fb1 = DEFAULT_ROLE_CONFIGS[AgentRole.PLANNER].fallback_models[0]

        # Primary fails with CANCELLED
        self.mock_provider.set_model_error(primary, ErrorCode.CANCELLED)
        self.mock_provider.set_model_response(fb1, "Should not be reached")

        with self.assertRaises(ProviderError) as ctx:
            self.router.generate_text_for_role(role=AgentRole.PLANNER, prompt="Prompt")

        self.assertEqual(ctx.exception.code, ErrorCode.CANCELLED)
        # Assert fallback was never called
        self.assertEqual(len(self.mock_provider.invocation_history), 1)

    def test_all_candidates_exhausted_raises_process_failed(self) -> None:
        """When all candidate models fail with recoverable errors, raises PROCESS_FAILED."""
        cfg = DEFAULT_ROLE_CONFIGS[AgentRole.ARGUMENT_WRITER]
        candidates = [cfg.primary_model] + cfg.fallback_models

        for m in candidates:
            self.mock_provider.set_model_error(m, ErrorCode.SERVICE_UNAVAILABLE)

        with self.assertRaises(ProviderError) as ctx:
            self.router.generate_text_for_role(role=AgentRole.ARGUMENT_WRITER, prompt="Extract")

        self.assertEqual(ctx.exception.code, ErrorCode.PROCESS_FAILED)
        self.assertIn("exhausted", str(ctx.exception))
        self.assertEqual(len(self.mock_provider.invocation_history), len(candidates))


class TestGenerativeRouterDropInCompatibility(unittest.TestCase):
    """Tests proving GenerativeRouter functions as a drop-in replacement for GenerativeProvider."""

    def setUp(self) -> None:
        self.mock_provider = MockGenerativeProvider(provider_id="mock", model_id="default-model")
        self.router = GenerativeRouter(
            providers={"mock": self.mock_provider},
            default_provider_id="mock",
        )

    def test_isinstance_generative_provider(self) -> None:
        self.assertIsInstance(self.router, GenerativeProvider)

    def test_standard_generate_text(self) -> None:
        res = self.router.generate_text(prompt="Standard prompt")
        self.assertIsInstance(res, GenerationResult)
        self.assertEqual(res.text, "Mock response")
        self.assertIn("router_telemetry", res.metadata)
        self.assertEqual(res.metadata["router_telemetry"]["role"], AgentRole.PLANNER.value)

    def test_standard_generate_structured(self) -> None:
        self.mock_provider.enqueue_response('{"plan_name": "DropIn", "steps": ["s1"]}')
        plan = self.router.generate_structured(prompt="Plan", response_model=SamplePlanOutput)
        self.assertIsInstance(plan, SamplePlanOutput)
        self.assertEqual(plan.plan_name, "DropIn")

    def test_generate_alias_for_generative_planner(self) -> None:
        text = self.router.generate(prompt="Planner query")
        self.assertIsInstance(text, str)
        self.assertEqual(text, "Mock response")

    def test_generative_planner_integration(self) -> None:
        """Proves GenerativePlanner seamlessly works with GenerativeRouter."""
        from omni_engine.planning.generative_planner import GenerativePlanner
        from omni_engine.capabilities.definitions import build_canonical_registry

        valid_plan_json = """{
            "plan_type": "generative_synthesized",
            "goal": "Test plan via router",
            "timeout_budget_s": 60.0,
            "steps": [
                {
                    "step_id": "step_1",
                    "capability_id": "web_search",
                    "action_class": "read_only",
                    "intent": "Search for info",
                    "arguments": {"query": "python"},
                    "dependencies": []
                }
            ]
        }"""
        self.mock_provider.enqueue_response(valid_plan_json)
        planner = GenerativePlanner(
            provider=self.router,
            capability_registry=build_canonical_registry(),
        )
        plan = planner.synthesize_plan(quest_id="quest_test", goal="Test plan via router")
        self.assertEqual(plan.goal, "Test plan via router")
        self.assertEqual(len(plan.steps), 1)
        self.assertEqual(plan.steps[0].capability_id, "web_search")
        telemetry = self.router.get_telemetry_history()
        self.assertTrue(any(t.role == AgentRole.PLANNER for t in telemetry))


class TestGenerativeRouterCandidateResolutionAndConcurrency(unittest.TestCase):
    """Tests candidate provider:model resolution and multi-threaded invocation safety."""

    def test_provider_uri_scheme_resolution(self) -> None:
        mock1 = MockGenerativeProvider(provider_id="prov1", model_id="m1", default_text="Resp 1")
        mock2 = MockGenerativeProvider(provider_id="prov2", model_id="m2", default_text="Resp 2")
        router = GenerativeRouter(
            providers={"prov1": mock1, "prov2": mock2},
            default_provider_id="prov1",
        )

        # Custom route using provider:model URI syntax
        custom_cfg = RoleRouteConfig(
            role=AgentRole.CODING,
            primary_model="prov2:special-coder-model",
            fallback_models=["prov1:backup-coder-model"],
        )
        router.configure_role(AgentRole.CODING, custom_cfg)

        res, telemetry = router.generate_text_with_telemetry(role=AgentRole.CODING, prompt="Code")
        self.assertEqual(telemetry.selected_provider_id, "prov2")
        self.assertEqual(telemetry.selected_model_id, "special-coder-model")
        self.assertEqual(res.text, "Resp 2")

    def test_multi_threaded_concurrency_safety(self) -> None:
        mock = MockGenerativeProvider(provider_id="mock", model_id="default-model")
        router = GenerativeRouter(
            providers={"mock": mock},
            default_provider_id="mock",
            max_telemetry_history=50,
        )

        def worker(idx: int) -> None:
            router.generate_text_for_role(
                role=AgentRole.PLANNER,
                prompt=f"Worker {idx} query",
            )

        # Run 40 concurrent invocations across 4 threads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(40)]
            for f in futures:
                f.result()

        history = router.get_telemetry_history()
        self.assertEqual(len(history), 40)
        self.assertEqual(len(mock.invocation_history), 40)


if __name__ == "__main__":
    unittest.main()
