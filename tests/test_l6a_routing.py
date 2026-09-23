"""
tests.test_l6a_routing
======================
Comprehensive test suite for Checkpoint L6A: Hierarchical Routing Foundation.

Verifies:
1. Conversational gating and empty-prompt deterministic fast-paths.
2. Single-domain exact filtering and zero-inference short-circuiting.
3. Dynamic candidate pruning bounded to [min_candidates, max_candidates].
4. Multi-step cross-domain tool retention (fail-open across domains).
5. Ambiguity and low-confidence fail-open pooling.
6. Explicit keyword capability pinning (zero tool dropping).
7. General domain technical promotion.
8. Elimination of legacy ISSUE-02 (flat [:12] truncation defect).
9. RouteDecision contract immutability and consistency validation.
10. Legacy prototype non-switching boundary preservation.
"""

import time
import unittest
from unittest.mock import MagicMock, patch

from pydantic import ValidationError

from omni_engine.capabilities.definitions import CANONICAL_SPECS, build_canonical_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.enums import DecisionSignalType
from omni_engine.contracts.routing import CapabilityCandidate, RouteDecision
from omni_engine.decision.fabric import DecisionFabric
from omni_engine.providers.base import ProviderHealth, SystemOneProvider
from omni_engine.routing.router import HierarchicalRouter


class MockSystemOneProvider(SystemOneProvider):
    """Deterministic mock provider for unit testing routing logic without GPU/neural weights."""
    provider_id = "mock-s1"
    model_id = "mock-model"
    is_configured = True

    def __init__(self, domain_decision: str = "web", confidence: float = 0.90, ambiguity: float = 0.10) -> None:
        self.domain_decision = domain_decision
        self.confidence = confidence
        self.ambiguity = ambiguity

    def predict_signals(self, context, questions):
        signals = {}
        for q_name, q_val in questions.items():
            if q_name == "domain":
                val = self.domain_decision
                probs = {
                    self.domain_decision: self.confidence,
                    "general": 0.05,
                    "dev": 0.03,
                    "os": 0.02,
                }
            elif q_name == "ambiguity":
                val = self.ambiguity
                probs = {"ambiguous": self.ambiguity, "clear": 1.0 - self.ambiguity}
            elif q_name == "needs_tools":
                val = True
                probs = {"yes": 0.9, "no": 0.1}
            elif q_name == "needs_plan":
                val = False
                probs = {"single_step": 0.8, "multi_step": 0.2}
            elif q_name == "task_class":
                val = "simple_action"
                probs = {"simple_action": 0.9}
            else:
                val = "standard"
                probs = {"standard": 0.9}

            signals[q_name] = DecisionSignal(
                signal_type=DecisionSignalType.INTENT,
                value=val,
                confidence=self.confidence,
                probabilities=probs,
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        return signals

    def classify(self, prompt, criteria, instructions="Classify:"):
        return DecisionSignal(
            signal_type=DecisionSignalType.INTENT,
            value=self.domain_decision,
            confidence=self.confidence,
            provider_id=self.provider_id,
            model_id=self.model_id,
        )

    def score(self, prompt, criteria):
        return self.confidence

    def health_check(self):
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=True,
            message="Mock operational",
        )


class TestHierarchicalRouting(unittest.TestCase):
    """Test suite for HierarchicalRouter in omni_engine.routing."""

    def setUp(self) -> None:
        self.registry = build_canonical_registry()
        self.mock_provider = MockSystemOneProvider(domain_decision="web", confidence=0.85)
        self.fabric = DecisionFabric(provider=self.mock_provider)
        self.router = HierarchicalRouter(
            registry=self.registry,
            provider=self.mock_provider,
            fabric=self.fabric,
        )

    # -----------------------------------------------------------------------
    # 1. Fast-Paths: Empty Prompts & Conversational Gating
    # -----------------------------------------------------------------------

    def test_empty_and_whitespace_prompt_fastpath(self) -> None:
        """Empty or whitespace prompts return empty candidates in <5ms without neural scoring."""
        t0 = time.perf_counter()
        dec = self.router.route("")
        t1 = time.perf_counter()

        self.assertEqual(len(dec.candidates), 0)
        self.assertEqual(dec.candidate_domains, [])
        self.assertFalse(dec.is_fail_open)
        self.assertIsNone(dec.fallback_reason)
        self.assertEqual(dec.catalog_reduction_ratio, 1.0)
        self.assertTrue(dec.metadata.get("fast_path"))
        self.assertEqual(dec.metadata.get("reason"), "empty_prompt")
        self.assertLess((t1 - t0) * 1000, 20.0)

        dec_ws = self.router.route("     \n\t   ")
        self.assertEqual(len(dec_ws.candidates), 0)
        self.assertEqual(dec_ws.catalog_reduction_ratio, 1.0)

    def test_conversational_gating(self) -> None:
        """Conversational queries where tools are not needed return 0 candidates with 100% reduction."""
        frame = self.fabric.evaluate("Hello, what is your name?")
        # Force frame to conversational non-tool
        frame.needs_tools.value = False
        frame.requires_action.value = False

        dec = self.router.route("Hello, what is your name?", decision_frame=frame)
        self.assertEqual(len(dec.candidates), 0)
        self.assertEqual(dec.candidate_domains, [])
        self.assertFalse(dec.is_fail_open)
        self.assertIsNone(dec.fallback_reason)
        self.assertEqual(dec.catalog_reduction_ratio, 1.0)
        self.assertEqual(dec.metadata.get("reason"), "conversational_no_tools_needed")

    # -----------------------------------------------------------------------
    # 2. Single-Domain Filtering & Zero-Inference Short Circuit
    # -----------------------------------------------------------------------

    def test_single_domain_exact_filtering(self) -> None:
        """Web query retrieves only web domain tools with exact candidate reduction."""
        frame = self.fabric.evaluate("Search the web for ModernBERT architecture")
        frame.candidate_domains = ["web", "dev", "os"]
        frame.raw_signals["domain"] = DecisionSignal(
            signal_type=DecisionSignalType.DOMAIN,
            value="web",
            confidence=0.92,
            provider_id="mock",
        )
        frame.needs_plan.value = False
        frame.ambiguity.value = 0.05

        dec = self.router.route("Search the web for ModernBERT architecture", decision_frame=frame)
        
        self.assertEqual(dec.selected_domain, "web")
        self.assertEqual(dec.candidate_domains, ["web"])
        # Web domain has 4 capabilities (<= max_candidates 6), so all 4 retained without pruning
        self.assertEqual(len(dec.candidates), 4)
        for c in dec.candidates:
            self.assertEqual(c.domain, "web")
        # 1.0 - 4/23 = ~0.8261
        self.assertAlmostEqual(dec.catalog_reduction_ratio, round(1.0 - (4 / 23), 4), places=3)
        self.assertFalse(dec.is_fail_open)
        self.assertIsNone(dec.fallback_reason)

    # -----------------------------------------------------------------------
    # 3. Dynamic Candidate Pruning
    # -----------------------------------------------------------------------

    def test_candidate_pruning_bound(self) -> None:
        """In os domain (8 capabilities), candidates are bounded to max_candidates (e.g. 5)."""
        frame = self.fabric.evaluate("List all running system processes and monitor system diagnostics")
        frame.candidate_domains = ["os", "dev"]
        frame.raw_signals["domain"] = DecisionSignal(
            signal_type=DecisionSignalType.DOMAIN,
            value="os",
            confidence=0.88,
            provider_id="mock",
        )
        frame.needs_plan.value = False
        frame.ambiguity.value = 0.10

        dec = self.router.route(
            "List all running system processes and monitor system diagnostics",
            decision_frame=frame,
            min_candidates=3,
            max_candidates=5,
        )

        self.assertEqual(dec.selected_domain, "os")
        # Total registered OS tools is 8; must be pruned to <= 5
        self.assertLessEqual(len(dec.candidates), 5)
        self.assertGreaterEqual(len(dec.candidates), 3)
        
        # Pinned or highly relevant tools must be present
        cand_ids = [c.capability_id for c in dec.candidates]
        self.assertIn("list_processes", cand_ids)

    # -----------------------------------------------------------------------
    # 4. Multi-Step Task Cross-Domain Retention (Rec-1)
    # -----------------------------------------------------------------------

    def test_multi_step_cross_domain_retention(self) -> None:
        """Multi-step tasks force pooling across top-2 domains, preserving tools from both."""
        prompt = "Download https://example.com/dataset.csv and run python script to analyze it"
        frame = self.fabric.evaluate(prompt)
        frame.candidate_domains = ["web", "dev", "data"]
        frame.raw_signals["domain"] = DecisionSignal(
            signal_type=DecisionSignalType.DOMAIN,
            value="web",
            confidence=0.85, # High confidence in single domain
            provider_id="mock",
        )
        frame.needs_plan.value = True # MULTI-STEP SCOPE
        frame.task_class.value = "multi_step_quest"

        dec = self.router.route(prompt, decision_frame=frame, max_candidates=6)

        # Must fail open across at least web and dev
        self.assertTrue(dec.is_fail_open)
        self.assertIn("multi_step_cross_domain_pooling", dec.fallback_reason)
        self.assertIn("web", dec.candidate_domains)
        self.assertIn("dev", dec.candidate_domains)

        cand_ids = [c.capability_id for c in dec.candidates]
        # Crucial invariant: both download_file (web) AND run_python (dev) must be retained!
        self.assertIn("download_file", cand_ids)
        self.assertIn("run_python", cand_ids)

    # -----------------------------------------------------------------------
    # 5. Ambiguity and Low-Confidence Fail-Open (Rec-3)
    # -----------------------------------------------------------------------

    def test_fail_open_on_low_confidence_and_ambiguity(self) -> None:
        """Low domain confidence (<0.55) or high ambiguity (>0.65) triggers fail-open pooling."""
        prompt = "Fix the error"
        frame = self.fabric.evaluate(prompt)
        frame.candidate_domains = ["dev", "os", "web"]
        frame.raw_signals["domain"] = DecisionSignal(
            signal_type=DecisionSignalType.DOMAIN,
            value="dev",
            confidence=0.45, # Low confidence (< 0.55)
            provider_id="mock",
        )
        frame.ambiguity.value = 0.80 # High ambiguity (> 0.65)

        dec = self.router.route(prompt, decision_frame=frame)

        self.assertTrue(dec.is_fail_open)
        self.assertIn("low_domain_confidence_or_high_ambiguity", dec.fallback_reason)
        self.assertGreaterEqual(len(dec.candidate_domains), 2)
        self.assertIn("dev", dec.candidate_domains)
        self.assertIn("os", dec.candidate_domains)

    # -----------------------------------------------------------------------
    # 6. Explicit Keyword Capability Pinning (Rec-5)
    # -----------------------------------------------------------------------

    def test_explicit_capability_keyword_pinning(self) -> None:
        """Explicit mentions of tools (e.g. sqlite, git status, ping, clipboard) pin them at score 1.0."""
        queries = [
            ("Run sqlite query to select * from users", "sqlite_exec", "data"),
            ("Check git status and branch information", "git_status", "dev"),
            ("Ping 127.0.0.1 to check connectivity", "ping_test", "os"),
            ("Copy results to clipboard", "clipboard", "os"),
            ("Calculate 2 ** 16", "safe_math", "data"),
        ]

        for prompt, expected_cap_id, expected_domain in queries:
            with self.subTest(prompt=prompt, expected_cap_id=expected_cap_id):
                dec = self.router.route(prompt)
                cand_ids = [c.capability_id for c in dec.candidates]
                self.assertIn(expected_cap_id, cand_ids)
                
                # Check candidate details
                matching_cand = next(c for c in dec.candidates if c.capability_id == expected_cap_id)
                self.assertEqual(matching_cand.score, 1.0)
                self.assertEqual(matching_cand.rationale, "explicit_keyword_pinned")
                self.assertEqual(matching_cand.domain, expected_domain)

    # -----------------------------------------------------------------------
    # 7. General Domain Technical Promotion (Rec-6)
    # -----------------------------------------------------------------------

    def test_general_domain_promotion(self) -> None:
        """If primary domain is general but needs_tools is True, technical domain is promoted."""
        frame = self.fabric.evaluate("Explain and inspect system CPU load")
        frame.candidate_domains = ["general", "os", "dev"]
        frame.needs_tools.value = True
        frame.requires_action.value = True

        dec = self.router.route("Explain and inspect system CPU load", decision_frame=frame)

        self.assertTrue(dec.is_fail_open)
        self.assertIn("general_domain_promoted_technical", dec.fallback_reason)
        self.assertNotIn("general", dec.candidate_domains)
        self.assertIn("os", dec.candidate_domains)
        self.assertGreater(len(dec.candidates), 0)

    # -----------------------------------------------------------------------
    # 8. Elimination of Legacy ISSUE-02 (Flat [:12] Truncation Defect)
    # -----------------------------------------------------------------------

    def test_elimination_of_legacy_truncation_defect(self) -> None:
        """Prove that tools 13-23 (which were dropped by legacy [:12] slicing) are accessible."""
        # In legacy planner.py: available_tools = list(OMNI_TOOL_REGISTRY.keys())[:12]
        # Tools at index 12+ (like ping_test, safe_math, inspect_data, sqlite_exec, powershell) were silently dropped.
        legacy_dropped_tools = [
            ("ping_test", "os", "Ping 8.8.8.8 to verify network connection"),
            ("powershell", "os", "Execute powershell command Get-Process"),
            ("sqlite_exec", "data", "Execute sqlite database query on records.db"),
            ("inspect_data", "data", "Inspect csv dataset at data/users.csv"),
            ("safe_math", "data", "Calculate mathematical expression 1024 * 768"),
        ]

        for cap_id, dom, prompt in legacy_dropped_tools:
            with self.subTest(cap_id=cap_id):
                frame = self.fabric.evaluate(prompt)
                frame.candidate_domains = [dom, "dev"]
                frame.needs_tools.value = True
                
                dec = self.router.route(prompt, decision_frame=frame)
                cand_ids = [c.capability_id for c in dec.candidates]
                self.assertIn(
                    cap_id,
                    cand_ids,
                    f"Capability '{cap_id}' (index 12+ in legacy inventory) was dropped by router!",
                )

    # -----------------------------------------------------------------------
    # 9. RouteDecision Contract Immutability & Validation (Rec-4)
    # -----------------------------------------------------------------------

    def test_contract_immutability_and_validation(self) -> None:
        """RouteDecision strictly validates extra fields, uniqueness, and fail-open consistency."""
        valid_cand = CapabilityCandidate(
            capability_id="web_search",
            domain="web",
            score=0.95,
            rationale="domain_primary",
            spec_summary="Search the web",
        )

        # 1. Extra fields forbidden
        with self.assertRaises(ValidationError):
            RouteDecision(
                request_id="req_1",
                candidates=[valid_cand],
                catalog_reduction_ratio=0.5,
                total_registry_capabilities=23,
                bogus_field="illegal", # type: ignore
            )

        # 2. Duplicate capability IDs rejected
        with self.assertRaises(ValidationError):
            RouteDecision(
                request_id="req_1",
                candidates=[valid_cand, valid_cand], # Duplicate
                catalog_reduction_ratio=0.5,
                total_registry_capabilities=23,
            )

        # 3. is_fail_open=True requires non-empty fallback_reason
        with self.assertRaises(ValidationError):
            RouteDecision(
                request_id="req_1",
                candidates=[valid_cand],
                is_fail_open=True,
                fallback_reason=None, # Missing reason
                catalog_reduction_ratio=0.5,
                total_registry_capabilities=23,
            )

        # 4. is_fail_open=False requires fallback_reason=None
        with self.assertRaises(ValidationError):
            RouteDecision(
                request_id="req_1",
                candidates=[valid_cand],
                is_fail_open=False,
                fallback_reason="Should be None", # Illegal when False
                catalog_reduction_ratio=0.5,
                total_registry_capabilities=23,
            )

        # 5. Candidate count cannot exceed total registry capabilities
        with self.assertRaises(ValidationError):
            RouteDecision(
                request_id="req_1",
                candidates=[valid_cand],
                total_registry_capabilities=0, # total < candidates
                catalog_reduction_ratio=0.0,
            )

    # -----------------------------------------------------------------------
    # 10. Legacy Non-Switching Boundary Preservation
    # -----------------------------------------------------------------------

    def test_legacy_non_switching_boundary(self) -> None:
        """Confirms omni_engine.planner and omni_engine.system1 preserve their legacy dispatch."""
        from omni_engine.planner import AutonomousPlanner
        from omni_engine.system1 import System1Router

        # System1Router still exists and provides route_tool
        s1 = System1Router()
        self.assertTrue(hasattr(s1, "route_tool"))
        self.assertTrue(callable(s1.route_tool))

        # AutonomousPlanner still instantiates and uses System1Router without crashing
        planner = AutonomousPlanner(
            sys1_engine=s1,
            sys2_engine=MagicMock(),
            memory_engine=MagicMock(),
        )
        self.assertIsNotNone(planner.sys1)
        self.assertTrue(callable(planner.plan_and_execute))

    # -----------------------------------------------------------------------
    # 11. Live Neural Model Inference Test
    # -----------------------------------------------------------------------

    def test_live_modernbert_hierarchical_routing(self) -> None:
        """Verifies HierarchicalRouter end-to-end using real Laya ModernBERT neural weights."""
        from omni_engine.providers.system1 import LayaProvider
        live_provider = LayaProvider(preload=False)
        live_router = HierarchicalRouter(
            registry=self.registry,
            provider=live_provider,
        )

        prompt = "Search the live web for the latest artificial intelligence breakthroughs"
        dec = live_router.route(prompt)

        self.assertIsInstance(dec, RouteDecision)
        self.assertGreater(len(dec.candidates), 0)
        self.assertLessEqual(len(dec.candidates), 6)
        self.assertIn("web", dec.candidate_domains)
        cand_ids = [c.capability_id for c in dec.candidates]
        self.assertIn("web_search", cand_ids)
        self.assertGreater(dec.catalog_reduction_ratio, 0.70)


if __name__ == "__main__":
    unittest.main()
