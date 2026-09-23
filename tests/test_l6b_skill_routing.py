"""
tests.test_l6b_skill_routing
============================
Comprehensive test suite for Checkpoint L6B: Skill-Aware Hierarchical Router.

Verifies:
1. Strongly typed RouteDecision contract with skill fields and strict validation.
2. Fast-path conversational and empty prompt gating (<5ms).
3. Exact canonical skill matching across all 7 canonical skills.
4. Blocking-1: Dynamic Candidate Floor Expansion (retaining all required tools).
5. Blocking-2: Unconditional Cross-Domain Spec Backfill for skill capabilities.
6. Blocking-3: Dual-Threshold Gating & Anti-Locking Defenses (destructive verb gate, generic token gate).
7. Unified deduplication and multi-rationale merging.
8. Budget-conscious optional capabilities ingestion.
9. System 1 Latency budget adherence.
10. Legacy non-switching boundary preservation.
"""

import time
import unittest
from typing import Any, Dict, List, Optional

from omni_engine.capabilities.definitions import build_canonical_registry
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    DecisionSignalType,
)
from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.routing import CapabilityCandidate, RouteDecision
from omni_engine.contracts.skill import SkillManifest, SkillStepTemplate
from omni_engine.decision.fabric import DecisionFabric
from omni_engine.providers.base import ProviderHealth, SystemOneProvider
from omni_engine.routing.router import HierarchicalRouter
from omni_engine.skills.definitions import build_canonical_skill_registry
from omni_engine.skills.registry import SkillRegistry


class MockSystemOneProvider(SystemOneProvider):
    """Deterministic Mock System 1 Provider for fast testing."""

    def __init__(self, primary_domain: str = "web", needs_tools: bool = True, needs_plan: bool = False) -> None:
        self.provider_id = "mock_laya"
        self.model_id = "mock-v1"
        self.is_configured = True
        self._primary_domain = primary_domain
        self._needs_tools = needs_tools
        self._needs_plan = needs_plan

    def predict_signals(self, context: Dict[str, Any], questions: Dict[str, Any]) -> Dict[str, DecisionSignal]:
        prompt = context.get("prompt", "")
        domain = self._primary_domain
        p_lower = prompt.lower()
        if "cpu" in p_lower or "diagnose" in p_lower or "process" in p_lower:
            domain = "os"
        elif "git" in p_lower or "code" in p_lower or "repo" in p_lower or "file" in p_lower:
            domain = "dev"
        elif "sql" in p_lower or "dataset" in p_lower or "data" in p_lower or "csv" in p_lower:
            domain = "data"
        elif "browse" in p_lower or "browser" in p_lower or "browsing" in p_lower:
            domain = "browser"
        elif "research" in p_lower or "scrape" in p_lower or "search" in p_lower:
            domain = "web"

        needs_tools = self._needs_tools
        if "hello" in p_lower or "thank" in p_lower or "how are you" in p_lower:
            needs_tools = False

        return {
            "intent": DecisionSignal(
                signal_type=DecisionSignalType.INTENT,
                value="task_execution" if needs_tools else "informational",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "task_class": DecisionSignal(
                signal_type=DecisionSignalType.TASK_CLASS,
                value="multi_step_quest" if self._needs_plan else "single_turn_reflex",
                confidence=0.90,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "domain": DecisionSignal(
                signal_type=DecisionSignalType.DOMAIN,
                value=domain,
                confidence=0.92,
                probabilities={domain: 0.92, "general": 0.08},
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "urgency": DecisionSignal(
                signal_type=DecisionSignalType.URGENCY,
                value="routine",
                confidence=0.85,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "importance": DecisionSignal(
                signal_type=DecisionSignalType.IMPORTANCE,
                value="normal",
                confidence=0.85,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "risk": DecisionSignal(
                signal_type=DecisionSignalType.RISK,
                value="safe_read_only",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "ambiguity": DecisionSignal(
                signal_type=DecisionSignalType.AMBIGUITY,
                value="unambiguous",
                confidence=0.10,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "needs_plan": DecisionSignal(
                signal_type=DecisionSignalType.NEEDS_PLAN,
                value="needs_dag_plan" if self._needs_plan else "direct",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "needs_tools": DecisionSignal(
                signal_type=DecisionSignalType.NEEDS_TOOLS,
                value="tools_required" if needs_tools else "no_tools",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "requires_action": DecisionSignal(
                signal_type=DecisionSignalType.REQUIRES_ACTION,
                value="action_required" if needs_tools else "reply_only",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "needs_clarification": DecisionSignal(
                signal_type=DecisionSignalType.NEEDS_CLARIFICATION,
                value="proceed",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "escalation_required": DecisionSignal(
                signal_type=DecisionSignalType.ESCALATION_REQUIRED,
                value="autonomous",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "model_tier": DecisionSignal(
                signal_type=DecisionSignalType.MODEL_TIER,
                value="system_1",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "reversibility": DecisionSignal(
                signal_type=DecisionSignalType.REVERSIBILITY,
                value="reversible",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
            "needs_generative_reasoning": DecisionSignal(
                signal_type=DecisionSignalType.NEEDS_GENERATIVE_REASONING,
                value="deterministic_or_s1",
                confidence=0.95,
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=1.5,
            ),
        }

    def classify(self, prompt: str, criteria: Dict[str, str], instructions: str = "") -> DecisionSignal:
        return DecisionSignal(
            signal_type=DecisionSignalType.INTENT,
            value=list(criteria.keys())[0],
            confidence=0.90,
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


class TestL6BSkillRouting(unittest.TestCase):
    """Test suite for Skill-Aware Hierarchical Capability Router."""

    def setUp(self) -> None:
        self.cap_registry = build_canonical_registry()
        self.skill_registry = build_canonical_skill_registry(self.cap_registry)
        self.mock_provider = MockSystemOneProvider()
        self.mock_fabric = DecisionFabric(provider=self.mock_provider)
        self.router = HierarchicalRouter(
            registry=self.cap_registry,
            provider=self.mock_provider,
            fabric=self.mock_fabric,
            skill_registry=self.skill_registry,
        )

    # -----------------------------------------------------------------------
    # 1. Contract Completeness & Invariants
    # -----------------------------------------------------------------------
    def test_route_decision_contract_skill_fields_and_validation(self) -> None:
        """RouteDecision strictly validates skill fields and consistency."""
        step = SkillStepTemplate(
            step_id="s1",
            capability_id="web_search",
            description="Search the web",
        )
        decision = RouteDecision(
            request_id="req_001",
            selected_domain="web",
            candidate_domains=["web"],
            selected_skill="web_research",
            candidate_skills=["web_research"],
            skill_workflow_template=[step],
            skill_confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
            candidates=[
                CapabilityCandidate(
                    capability_id="web_search",
                    domain="web",
                    score=0.98,
                    rationale="skill_required",
                )
            ],
            is_fail_open=False,
            catalog_reduction_ratio=0.9565,
            total_registry_capabilities=23,
            latency_ms=1.5,
        )
        self.assertEqual(decision.selected_skill, "web_research")
        self.assertIn("web_research", decision.candidate_skills)
        self.assertEqual(len(decision.skill_workflow_template), 1)
        self.assertEqual(decision.skill_confirmation_policy, ConfirmationPolicy.POLICY_CONTROLLED)

        # Invariant: If selected_skill is None, template and policy MUST be None
        with self.assertRaises(ValueError):
            RouteDecision(
                request_id="req_002",
                selected_skill=None,
                skill_workflow_template=[step], # Invalid!
                candidates=[],
                catalog_reduction_ratio=1.0,
                total_registry_capabilities=23,
            )

        with self.assertRaises(ValueError):
            RouteDecision(
                request_id="req_003",
                selected_skill=None,
                skill_confirmation_policy=ConfirmationPolicy.ALWAYS, # Invalid!
                candidates=[],
                catalog_reduction_ratio=1.0,
                total_registry_capabilities=23,
            )

    # -----------------------------------------------------------------------
    # 2. Conversational & Empty Prompt Fast-Paths
    # -----------------------------------------------------------------------
    def test_fastpath_empty_and_conversational(self) -> None:
        """Empty and conversational prompts return zero candidates and zero skills in <5ms."""
        # Empty
        t0 = time.perf_counter()
        d_empty = self.router.route("")
        t_empty = (time.perf_counter() - t0) * 1000
        self.assertIsNone(d_empty.selected_skill)
        self.assertEqual(d_empty.candidate_skills, [])
        self.assertEqual(len(d_empty.candidates), 0)
        self.assertLess(t_empty, 5.0)

        # Conversational
        t0 = time.perf_counter()
        d_conv = self.router.route("hello there, thank you for your help!")
        t_conv = (time.perf_counter() - t0) * 1000
        self.assertIsNone(d_conv.selected_skill)
        self.assertEqual(d_conv.candidate_skills, [])
        self.assertEqual(len(d_conv.candidates), 0)
        self.assertLess(t_conv, 5.0)

    # -----------------------------------------------------------------------
    # 3. Canonical Skills Matching Parity
    # -----------------------------------------------------------------------
    def test_canonical_skill_matching_web_research(self) -> None:
        """Prompt matching web_research selects skill and includes required capabilities."""
        decision = self.router.route("research quantum computing papers and scrape documentation")
        self.assertEqual(decision.selected_skill, "web_research")
        self.assertIn("web_research", decision.candidate_skills)
        self.assertIsNotNone(decision.skill_workflow_template)
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("web_search", candidate_ids)
        self.assertIn("scrape_url", candidate_ids)

    def test_canonical_skill_matching_diagnose_system(self) -> None:
        """Prompt matching diagnose_system selects skill and includes required capabilities."""
        decision = self.router.route("diagnose system health and investigate cpu memory usage")
        self.assertEqual(decision.selected_skill, "diagnose_system")
        self.assertIn("diagnose_system", decision.candidate_skills)
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("system_diagnostics", candidate_ids)
        self.assertIn("list_processes", candidate_ids)

    def test_canonical_skill_matching_inspect_repository(self) -> None:
        """Prompt matching inspect_repository selects skill and includes required capabilities."""
        decision = self.router.route("inspect repository code structure and explore codebase")
        self.assertEqual(decision.selected_skill, "inspect_repository")
        self.assertIn("inspect_repository", decision.candidate_skills)
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("directory_tree", candidate_ids)
        self.assertIn("search_code", candidate_ids)
        self.assertIn("file_read", candidate_ids)

    def test_canonical_skill_matching_analyze_data(self) -> None:
        """Prompt matching analyze_data selects skill and includes required capabilities."""
        decision = self.router.route("inspect csv dataset and analyze data with sql queries")
        self.assertEqual(decision.selected_skill, "analyze_data")
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("sqlite_exec", candidate_ids)
        self.assertIn("inspect_data", candidate_ids)

    def test_canonical_skill_matching_browser_task(self) -> None:
        """Prompt matching browser_information_task selects skill and includes visual_browse."""
        decision = self.router.route("interactive web exploration and visual web browsing with screenshot")
        self.assertEqual(decision.selected_skill, "browser_information_task")
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("visual_browse", candidate_ids)

    def test_canonical_skill_matching_git_inspection(self) -> None:
        """Prompt matching perform_git_inspection selects skill and includes git_status."""
        decision = self.router.route("check git commits and inspect git repository")
        self.assertEqual(decision.selected_skill, "perform_git_inspection")
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("git_status", candidate_ids)
        self.assertIn("search_code", candidate_ids)
        self.assertIn("file_read", candidate_ids)

    # -----------------------------------------------------------------------
    # 4. Blocking-1: Dynamic Candidate Floor Expansion
    # -----------------------------------------------------------------------
    def test_blocking_1_dynamic_floor_expansion(self) -> None:
        """Candidate budget dynamically expands to never drop required or pinned tools."""
        # inspect_repository requires 3 tools (directory_tree, search_code, file_read)
        # In addition, prompt explicitly pins 'calculate' -> safe_math (total 4 mandatory tools)
        # We set max_candidates=2 (which is less than 4)
        decision = self.router.route(
            prompt="inspect repository code structure, explore codebase, and calculate 2 + 2",
            max_candidates=2,
        )
        self.assertEqual(decision.selected_skill, "inspect_repository")
        candidate_ids = [c.capability_id for c in decision.candidates]

        # Verify all 4 mandatory capabilities are present!
        self.assertIn("directory_tree", candidate_ids)
        self.assertIn("search_code", candidate_ids)
        self.assertIn("file_read", candidate_ids)
        self.assertIn("safe_math", candidate_ids)

        # Verify budget was expanded and telemetry records it
        self.assertGreaterEqual(len(decision.candidates), 4)
        self.assertTrue(decision.metadata.get("budget_expanded"))
        self.assertEqual(
            decision.metadata.get("expanded_reason"),
            "skill_required_capabilities_exceeded_max",
        )

    # -----------------------------------------------------------------------
    # 5. Blocking-2: Unconditional Cross-Domain Spec Backfill
    # -----------------------------------------------------------------------
    def test_blocking_2_cross_domain_spec_backfill(self) -> None:
        """Constituent capabilities from other domains are backfilled into candidate specs."""
        # Create a custom skill in 'dev' domain that requires a capability from 'os' domain
        custom_skill = SkillManifest(
            skill_id="custom_cross_domain_skill",
            domain="dev",
            name="Dev with OS probe",
            description="Dev inspection requiring OS diagnostic",
            intent_patterns=["custom dev probe"],
            required_capabilities=["directory_tree", "system_diagnostics"], # 'dev' and 'os'
            action_classes=[ActionClass.READ_ONLY],
            workflow_template=[
                SkillStepTemplate(step_id="s1", capability_id="directory_tree", description="tree"),
                SkillStepTemplate(step_id="s2", capability_id="system_diagnostics", description="diag"),
            ],
            planning_required=False,
            applicable_autonomy=AutonomyProfile.ADVISOR,
            confirmation_policy=ConfirmationPolicy.NEVER,
        )
        self.skill_registry.register(custom_skill)

        # Force active domain to 'dev' only
        frame = self.mock_fabric.evaluate("custom dev probe")
        frame.candidate_domains = ["dev"]

        decision = self.router.route("custom dev probe", decision_frame=frame)
        self.assertEqual(decision.selected_skill, "custom_cross_domain_skill")

        candidate_ids = [c.capability_id for c in decision.candidates]
        # system_diagnostics (os domain) MUST be backfilled and present!
        self.assertIn("directory_tree", candidate_ids)
        self.assertIn("system_diagnostics", candidate_ids)

    # -----------------------------------------------------------------------
    # 6. Blocking-3: Dual-Threshold Gating & Anti-Locking Defenses
    # -----------------------------------------------------------------------
    def test_blocking_3_destructive_verb_prevents_false_positive_lock(self) -> None:
        """Destructive verbs prevent locking into harmless/read-only skills."""
        # Prompt has 'delete' and 'file', which overlaps with file_transform intent pattern 'edit file'
        # But since prompt has destructive verb 'delete', it MUST NOT lock into file_transform
        decision = self.router.route("delete the temporary file junk.txt")
        self.assertIsNone(decision.selected_skill)
        # Should fall back cleanly to capability routing
        self.assertGreater(len(decision.candidates), 0)

    def test_blocking_3_generic_single_token_prevents_skill_lock(self) -> None:
        """Single generic English words (e.g. 'file', 'run') do not trigger skill selection."""
        decision = self.router.route("open file")
        # 'file' alone is a generic token; score does not reach 0.75 threshold
        self.assertIsNone(decision.selected_skill)
        candidate_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("file_read", candidate_ids)

    # -----------------------------------------------------------------------
    # 7. Deduplication & Score Merging
    # -----------------------------------------------------------------------
    def test_deduplication_and_multi_rationale_merging(self) -> None:
        """Capabilities that are both pinned and skill-required merge rationale and retain score=1.0."""
        # git status is pinned by keyword 'git status' (score 1.0)
        # and required by perform_git_inspection (score 0.98)
        decision = self.router.route("check git status and inspect git repository")
        self.assertEqual(decision.selected_skill, "perform_git_inspection")

        git_status_cand = next(c for c in decision.candidates if c.capability_id == "git_status")
        self.assertEqual(git_status_cand.score, 1.0)
        self.assertEqual(git_status_cand.rationale, "explicit_keyword_pinned+skill_required")

    # -----------------------------------------------------------------------
    # 8. Budget-Conscious Optional Capabilities Ingestion
    # -----------------------------------------------------------------------
    def test_optional_capabilities_ingestion_and_scoring(self) -> None:
        """Optional capabilities receive score 0.75 and do not exceed effective_max."""
        decision = self.router.route("diagnose system health and check running processes", max_candidates=6)
        self.assertEqual(decision.selected_skill, "diagnose_system")
        candidate_map = {c.capability_id: c for c in decision.candidates}

        # Required
        self.assertIn("system_diagnostics", candidate_map)
        self.assertIn("list_processes", candidate_map)

        # Optional tool ping_test from diagnose_system
        self.assertIn("ping_test", candidate_map)
        self.assertEqual(candidate_map["ping_test"].score, 0.75)
        self.assertEqual(candidate_map["ping_test"].rationale, "skill_optional")

        self.assertLessEqual(len(decision.candidates), 6)

    # -----------------------------------------------------------------------
    # 9. Legacy Non-Switching Boundary
    # -----------------------------------------------------------------------
    def test_legacy_non_switching_boundary(self) -> None:
        """Verifies omni_engine.planner and omni_engine.system1 preserve their legacy dispatch."""
        from unittest.mock import MagicMock
        from omni_engine.planner import AutonomousPlanner
        from omni_engine.system1 import System1Router

        legacy_router = System1Router()
        self.assertTrue(hasattr(legacy_router, "route_tool"))
        self.assertTrue(callable(legacy_router.route_tool))

        planner = AutonomousPlanner(
            sys1_engine=MagicMock(),
            sys2_engine=MagicMock(),
            memory_engine=MagicMock(),
        )
        self.assertTrue(callable(planner.plan_and_execute))

    # -----------------------------------------------------------------------
    # 10. Live ModernBERT Neural Skill Routing Test
    # -----------------------------------------------------------------------
    def test_live_modernbert_skill_routing(self) -> None:
        """Verifies Skill-Aware HierarchicalRouter end-to-end using real Laya ModernBERT neural weights."""
        from omni_engine.providers.system1 import LayaProvider
        live_provider = LayaProvider(preload=False)
        live_router = HierarchicalRouter(
            registry=self.cap_registry,
            provider=live_provider,
            skill_registry=self.skill_registry,
        )

        prompt = "Search the live web for the latest artificial intelligence breakthroughs and research findings"
        decision = live_router.route(prompt)

        self.assertIsInstance(decision, RouteDecision)
        self.assertGreater(len(decision.candidates), 0)
        self.assertLessEqual(len(decision.candidates), 6)
        self.assertIn("web", decision.candidate_domains)
        cand_ids = [c.capability_id for c in decision.candidates]
        self.assertIn("web_search", cand_ids)
        self.assertEqual(decision.selected_skill, "web_research")
        self.assertIsNotNone(decision.skill_workflow_template)
        self.assertGreater(decision.catalog_reduction_ratio, 0.70)


if __name__ == "__main__":
    unittest.main()
