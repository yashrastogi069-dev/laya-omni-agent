"""
omni_engine.routing.router
==========================
Skill-Aware Hierarchical Capability Router for the standalone LAYA Omni Agent.

Implements the multi-tier routing pipeline:
Request -> DecisionFrame -> Domain Routing -> Skill Routing -> Candidate Pruning -> RouteDecision

Invariants:
- Deterministic Control & Fail-Open: Ambiguous, low-confidence, or multi-step requests widen candidate pools.
- Zero Tool Dropping: Explicit capability keywords pin required tools.
- Skill Prioritization & Floor Expansion: A selected skill's required capabilities are unconditionally
  preserved, dynamically expanding candidate budgets when necessary.
- Dual-Threshold Anti-Locking Defenses: Weak token overlap or destructive verb conflicts prevent false-positive
  skill locking.
- Strict Latency SLA: Fast regex and token scoring keep warm inference <35ms (<5ms for deterministic paths).
- Non-Switching Principle: Main agent dispatch remains unaffected until L8/L9.
"""

import re
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple

from omni_engine.capabilities.definitions import CANONICAL_SPECS, build_canonical_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.enums import ActionClass, ConfirmationPolicy
from omni_engine.contracts.routing import CapabilityCandidate, RouteDecision
from omni_engine.contracts.skill import SkillManifest, SkillStepTemplate
from omni_engine.decision.fabric import DecisionFabric
from omni_engine.providers.base import ProviderError, SystemOneProvider
from omni_engine.providers.system1 import LayaProvider, get_shared_laya_router
from omni_engine.skills.definitions import build_canonical_skill_registry
from omni_engine.skills.registry import SkillRegistry


# ---------------------------------------------------------------------------
# Declarative Keyword Maps
# ---------------------------------------------------------------------------

DOMAIN_KEYWORD_MAP: Dict[str, Set[str]] = {
    "web": {
        "web", "search", "google", "bing", "tavily", "internet", "online",
        "scrape", "url", "download", "http", "api", "rest", "endpoint", "curl", "fetch"
    },
    "browser": {
        "browser", "browse", "website", "dom", "click", "webpage", "navigate",
        "page", "edge", "playwright", "button", "input_element"
    },
    "os": {
        "process", "processes", "kill", "ps", "taskkill", "taskmgr", "tasklist",
        "app", "launch", "application", "desktop", "screenshot", "clipboard",
        "powershell", "cmd", "terminal", "ping", "diagnostics", "cpu", "ram",
        "memory_usage", "system_health", "battery", "disk"
    },
    "dev": {
        "file", "read", "write", "code", "directory", "tree", "folder", "python",
        "script", "git", "commit", "status", "branch", "diff", "repo", "repository",
        "directory_tree", "search_code"
    },
    "data": {
        "sql", "sqlite", "database", "table", "query", "math", "calculate",
        "expression", "arithmetic", "inspect", "csv", "json", "dataset",
        "dataframe", "inspect_data", "safe_math"
    },
}

# Explicit capability pin mapping: regex patterns to capability ID
CAPABILITY_PIN_MAP: List[Tuple[re.Pattern, str]] = [
    # Data domain
    (re.compile(r"\b(sqlite|sql\s+query|database|select\s+\*)\b", re.IGNORECASE), "sqlite_exec"),
    (re.compile(r"\b(inspect\s+data|inspect\s+csv|dataset|view\s+csv)\b", re.IGNORECASE), "inspect_data"),
    (re.compile(r"\b(calculate|math|arithmetic|\d+\s*[\+\-\*\/\^]\s*\d+|2\s*\*\*)\b", re.IGNORECASE), "safe_math"),
    # Dev domain
    (re.compile(r"\b(read\s+file|view\s+file|cat\s+file|open\s+file|file_read)\b", re.IGNORECASE), "file_read"),
    (re.compile(r"\b(write\s+file|save\s+file|write\s+to\s+file|overwrite|file_write)\b", re.IGNORECASE), "file_write"),
    (re.compile(r"\b(search\s+code|find\s+pattern|grep\b|code_search)\b", re.IGNORECASE), "search_code"),
    (re.compile(r"\b(directory\s+tree|list\s+files|dir\s+tree|folder\s+structure)\b", re.IGNORECASE), "directory_tree"),
    (re.compile(r"\b(run\s+python|python\s+script|execute\s+python|run_python)\b", re.IGNORECASE), "run_python"),
    (re.compile(r"\b(git\s+status|git\s+diff|git\s+log|git\s+branch|git\s+repo|git\b)\b", re.IGNORECASE), "git_status"),
    # OS domain
    (re.compile(r"\b(system\s+diagnostics|system\s+health|cpu\s+load|ram\s+usage|battery|disk\s+space)\b", re.IGNORECASE), "system_diagnostics"),
    (re.compile(r"\b(list\s+processes|running\s+processes|tasklist|ps\b)\b", re.IGNORECASE), "list_processes"),
    (re.compile(r"\b(kill\s+process|terminate\s+process|kill\s+pid|stop\s+process|taskkill)\b", re.IGNORECASE), "kill_process"),
    (re.compile(r"\b(launch\s+app|open\s+app|start\s+program|launch_app)\b", re.IGNORECASE), "launch_app"),
    (re.compile(r"\b(desktop\s+screenshot|screen\s+capture|take\s+screenshot)\b", re.IGNORECASE), "desktop_screenshot"),
    (re.compile(r"\b(clipboard|copy\s+to\s+clipboard|paste\s+from\s+clipboard)\b", re.IGNORECASE), "clipboard"),
    (re.compile(r"\b(powershell|pwsh\b|run\s+powershell|shell\s+command)\b", re.IGNORECASE), "powershell"),
    (re.compile(r"\b(ping\b|ping\s+test|ping\s+host|connectivity\s+check)\b", re.IGNORECASE), "ping_test"),
    # Web domain
    (re.compile(r"\b(web\s+search|search\s+the\s+web|google\s+for|search\s+tavily)\b", re.IGNORECASE), "web_search"),
    (re.compile(r"\b(scrape\b|scrape\s+url|extract\s+text\s+from\s+url|read\s+webpage)\b", re.IGNORECASE), "scrape_url"),
    (re.compile(r"\b(http\s+api|rest\s+api|http\s+get|http\s+post|http\s+request|curl\b)\b", re.IGNORECASE), "http_api"),
    (re.compile(r"\b(download\s+file|download\s+from|download\s+https?:\/\/)\b", re.IGNORECASE), "download_file"),
    # Browser domain
    (re.compile(r"\b(visual\s+browse|navigate\s+to|open\s+browser|browse\s+page)\b", re.IGNORECASE), "visual_browse"),
    (re.compile(r"\b(browser\s+screenshot|capture\s+browser)\b", re.IGNORECASE), "browser_screenshot"),
]

# Tokens excluded from matching skills on their own to prevent false-positive skill locking
GENERIC_SINGLE_TOKENS: Set[str] = {
    "file", "run", "status", "data", "system", "check", "test", "web", "code", "repo", "python"
}

# Verbs signaling destructive or mutation intent
DESTRUCTIVE_VERBS: Set[str] = {
    "delete", "remove", "kill", "drop", "purge", "terminate", "rmdir", "unlink", "wipe"
}


def _stem_token(token: str) -> str:
    """Lightweight morphological stemmer for English verbal and noun suffixes."""
    for suffix in ("ing", "tions", "tion", "es", "s", "ed"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            token = token[:-len(suffix)]
            break
    if token.endswith("e") and len(token) > 4:
        token = token[:-1]
    return token


class HierarchicalRouter:
    """Skill-Aware Hierarchical Capability Router driving multi-tier catalog reduction.
    
    Architecture:
    1. Input: User prompt + optional pre-computed DecisionFrame.
    2. Gating: Fast deterministic bypass for conversational or empty prompts (<5ms).
    3. Domain Routing: Resolves primary and fail-open candidate domains.
    4. Explicit Pinning: Scans prompt for explicit capability tokens (score=1.0).
    5. Skill Routing: Matches prompt against SkillRegistry intent patterns and descriptions:
       - If high-confidence skill (>=0.75) is selected:
         - All required capabilities are unconditionally preserved (score=0.98).
         - Candidate budget dynamically expands if required tools exceed max_candidates.
         - Declarative workflow DAG template and confirmation policy are attached.
       - If no skill matches: falls back cleanly to domain capability routing.
    6. Dynamic Pruning: Fills remaining capacity with optional skill tools and top domain tools.
    7. Envelope Construction: Returns strongly typed RouteDecision.
    """

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        provider: Optional[SystemOneProvider] = None,
        fabric: Optional[DecisionFabric] = None,
        skill_registry: Optional[SkillRegistry] = None,
    ) -> None:
        self.registry = registry or build_canonical_registry()
        self.provider = provider or LayaProvider()
        self.fabric = fabric or DecisionFabric(provider=self.provider)
        self.skill_registry = skill_registry or build_canonical_skill_registry(self.registry)

    def _score_skill_match(
        self,
        prompt_lower: str,
        prompt_tokens: Set[str],
        manifest: SkillManifest,
        primary_domain: Optional[str],
    ) -> float:
        """Evaluates prompt match against a skill manifest with anti-locking defenses."""
        # 1. Destructive verb conflict gate
        has_destructive_verb = any(v in prompt_tokens for v in DESTRUCTIVE_VERBS)
        skill_has_destructive_ac = any(
            ac in [ActionClass.LOCAL_DELETE, ActionClass.EXTERNAL_DELETE, ActionClass.SYSTEM_ACTION]
            for ac in manifest.action_classes
        )
        if has_destructive_verb and not skill_has_destructive_ac:
            # Prompt requests destructive action, but skill only performs read-only or harmless operations
            return 0.0

        best_score = 0.0

        # Build morphological stem sets
        prompt_stems = {_stem_token(t) for t in prompt_tokens} | prompt_tokens

        # 2. Intent patterns matching
        for pattern in manifest.intent_patterns:
            p_lower = pattern.lower().strip()
            p_tokens = set(re.findall(r"\w+", p_lower))
            p_stems = {_stem_token(t) for t in p_tokens} | p_tokens

            # Exact multi-token phrase match
            if len(p_tokens) > 1 and re.search(r"\b" + re.escape(p_lower) + r"\b", prompt_lower):
                score = 0.95
                if manifest.domain == primary_domain:
                    score = 1.0
                best_score = max(best_score, score)
                continue

            # Stemmed token overlap with intent pattern
            overlap = prompt_stems.intersection(p_stems)
            non_generic_overlap = [
                t for t in overlap
                if t not in GENERIC_SINGLE_TOKENS and _stem_token(t) not in GENERIC_SINGLE_TOKENS
            ]

            if len(p_tokens) > 0:
                overlap_ratio = len(overlap) / len(p_tokens)
                # Require at least 2 non-generic tokens or 1 non-generic with >=50% pattern overlap
                if len(non_generic_overlap) >= 2 or (len(non_generic_overlap) >= 1 and overlap_ratio >= 0.50):
                    token_score = 0.65 + 0.30 * min(1.0, overlap_ratio)
                    if manifest.domain == primary_domain:
                        token_score = min(0.98, token_score + 0.10)
                    best_score = max(best_score, token_score)

        # 3. Description & name token overlap (capped at 0.50 so it never triggers selection alone)
        desc_text = f"{manifest.name} {manifest.description}".lower()
        desc_tokens = set(re.findall(r"\w+", desc_text))
        desc_stems = {_stem_token(t) for t in desc_tokens} | desc_tokens
        non_generic_desc_overlap = [
            t for t in prompt_stems.intersection(desc_stems)
            if t not in GENERIC_SINGLE_TOKENS and _stem_token(t) not in GENERIC_SINGLE_TOKENS
        ]
        if len(non_generic_desc_overlap) >= 2:
            desc_score = min(0.50, 0.20 + 0.10 * len(non_generic_desc_overlap))
            best_score = max(best_score, desc_score)

        return round(best_score, 3)

    def route(
        self,
        prompt: str,
        decision_frame: Optional[DecisionFrame] = None,
        context: Optional[Dict[str, Any]] = None,
        min_candidates: int = 3,
        max_candidates: int = 6,
    ) -> RouteDecision:
        """Computes hierarchical routing decision for the given prompt.
        
        Args:
            prompt: User natural language request.
            decision_frame: Optional pre-computed DecisionFrame from DecisionFabric.
            context: Supplemental context dictionary.
            min_candidates: Minimum candidate count (default: 3).
            max_candidates: Maximum candidate count (default: 6).
            
        Returns:
            RouteDecision envelope containing ranked candidates, skill resolution, and telemetry.
        """
        t0 = time.perf_counter()
        total_caps = self.registry.count()
        req_id = decision_frame.request_id if decision_frame else f"req_{uuid.uuid4().hex[:8]}"

        # -------------------------------------------------------------------
        # 1. Deterministic Fast-Path for Empty / Whitespace Prompts
        # -------------------------------------------------------------------
        stripped_prompt = prompt.strip() if prompt else ""
        if not stripped_prompt:
            t1 = time.perf_counter()
            return RouteDecision(
                request_id=req_id,
                selected_domain=None,
                candidate_domains=[],
                selected_skill=None,
                candidate_skills=[],
                skill_workflow_template=None,
                skill_confirmation_policy=None,
                candidates=[],
                is_fail_open=False,
                fallback_reason=None,
                catalog_reduction_ratio=1.0 if total_caps > 0 else 0.0,
                total_registry_capabilities=total_caps,
                latency_ms=round((t1 - t0) * 1000, 3),
                metadata={"fast_path": True, "reason": "empty_prompt"},
            )

        # -------------------------------------------------------------------
        # 2. DecisionFrame Resolution & Conversational Gating
        # -------------------------------------------------------------------
        frame = decision_frame
        if frame is None:
            frame = self.fabric.evaluate(prompt=prompt, session_context=context)

        # Conversational Fast-Path (Needs no tools and requires no real-world action)
        needs_tools_val = getattr(frame.needs_tools, "value", True)
        needs_tools = needs_tools_val in [True, "tools_required", "true", "yes"]

        requires_action_val = getattr(frame.requires_action, "value", True) if frame.requires_action is not None else True
        requires_action = requires_action_val in [True, "action_required", "true", "yes"]

        if not needs_tools and not requires_action:
            t1 = time.perf_counter()
            return RouteDecision(
                request_id=req_id,
                selected_domain=None,
                candidate_domains=[],
                selected_skill=None,
                candidate_skills=[],
                skill_workflow_template=None,
                skill_confirmation_policy=None,
                candidates=[],
                is_fail_open=False,
                fallback_reason=None,
                catalog_reduction_ratio=1.0 if total_caps > 0 else 0.0,
                total_registry_capabilities=total_caps,
                latency_ms=round((t1 - t0) * 1000, 3),
                metadata={"fast_path": True, "reason": "conversational_no_tools_needed"},
            )

        # -------------------------------------------------------------------
        # 3. Domain Resolution & Fail-Open Analysis
        # -------------------------------------------------------------------
        candidate_domains = list(frame.candidate_domains)
        is_fail_open = False
        fallback_reasons: List[str] = []

        # General Domain Promotion
        if candidate_domains and candidate_domains[0] == "general":
            candidate_domains = [d for d in candidate_domains if d != "general"]
            if not candidate_domains:
                candidate_domains = ["web", "dev", "os", "data", "browser"]
            is_fail_open = True
            fallback_reasons.append("general_domain_promoted_technical")

        # Extract domain confidence safely from raw_signals["domain"]
        domain_confidence = 1.0
        if "domain" in frame.raw_signals:
            domain_confidence = frame.raw_signals["domain"].confidence

        # Multi-Step Task Cross-Domain Retention
        needs_plan_val = getattr(frame.needs_plan, "value", False)
        needs_plan = needs_plan_val in [True, "needs_dag_plan", "true", "yes"]
        task_class = getattr(frame.task_class, "value", "simple_action")
        is_multi_step = needs_plan or task_class in ["multi_step_quest", "code_refactor"]

        if is_multi_step:
            is_fail_open = True
            fallback_reasons.append("multi_step_cross_domain_pooling")

        # Ambiguity & Low Confidence Fail-Open
        ambiguity_val = getattr(frame.ambiguity, "value", 0.0)
        try:
            ambiguity_num = float(ambiguity_val)
        except (ValueError, TypeError):
            ambiguity_num = 1.0 if ambiguity_val in ["ambiguous", True] else 0.0

        needs_clarif_val = getattr(frame.needs_clarification, "value", False) if frame.needs_clarification is not None else False
        needs_clarif = needs_clarif_val in [True, "ask_user", "true", "yes"]

        if domain_confidence < 0.55 or ambiguity_num > 0.65 or needs_clarif:
            is_fail_open = True
            fallback_reasons.append("low_domain_confidence_or_high_ambiguity")

        # Domain Keyword Discovery
        prompt_lower = stripped_prompt.lower()
        keyword_detected_domains: Set[str] = set()
        for dom, kw_set in DOMAIN_KEYWORD_MAP.items():
            for kw in kw_set:
                if re.search(r"\b" + re.escape(kw) + r"\b", prompt_lower):
                    keyword_detected_domains.add(dom)
                    break

        # Pool domains based on fail-open rules
        active_domains: List[str] = []
        if is_fail_open or is_multi_step:
            for d in candidate_domains[:2]:
                if d not in active_domains:
                    active_domains.append(d)
            for d in keyword_detected_domains:
                if d not in active_domains:
                    active_domains.append(d)
        else:
            if candidate_domains:
                active_domains = [candidate_domains[0]]
            elif keyword_detected_domains:
                active_domains = [list(keyword_detected_domains)[0]]

        if not active_domains:
            active_domains = ["web", "dev", "os", "data", "browser"]
            is_fail_open = True
            fallback_reasons.append("empty_candidate_domains_fallback")

        primary_domain = active_domains[0] if active_domains else None

        # -------------------------------------------------------------------
        # 4. Explicit Capability Pinning (Score = 1.0)
        # -------------------------------------------------------------------
        pinned_caps: Dict[str, CapabilityCandidate] = {}
        for pattern, cap_id in CAPABILITY_PIN_MAP:
            if pattern.search(prompt_lower):
                spec = self.registry.get_spec(cap_id)
                if spec is not None:
                    pinned_caps[cap_id] = CapabilityCandidate(
                        capability_id=cap_id,
                        domain=spec.domain,
                        score=1.0,
                        rationale="explicit_keyword_pinned",
                        spec_summary=f"{spec.name}: {spec.description[:80]}",
                    )

        # -------------------------------------------------------------------
        # 5. Skill Routing & Selection (Dual-Threshold Gating)
        # -------------------------------------------------------------------
        prompt_tokens = set(re.findall(r"\w+", prompt_lower))
        skills_to_consider: List[SkillManifest] = []
        if is_fail_open:
            skills_to_consider = self.skill_registry.list_manifests()
        else:
            for dom in active_domains:
                skills_to_consider.extend(self.skill_registry.list_by_domain(dom))

        # Deduplicate manifests
        unique_skills_map = {s.skill_id: s for s in skills_to_consider}
        scored_skills: List[Tuple[float, SkillManifest]] = []

        for manifest in unique_skills_map.values():
            score = self._score_skill_match(
                prompt_lower=prompt_lower,
                prompt_tokens=prompt_tokens,
                manifest=manifest,
                primary_domain=primary_domain,
            )
            if score >= 0.50:
                scored_skills.append((score, manifest))

        # Deterministic sorting: highest score, domain match preference, lexicographical ID
        scored_skills.sort(
            key=lambda x: (
                -x[0],
                0 if x[1].domain == primary_domain else 1,
                x[1].skill_id,
            )
        )

        candidate_skills = [m.skill_id for _, m in scored_skills]
        selected_skill_manifest: Optional[SkillManifest] = None
        selected_skill: Optional[str] = None

        if scored_skills and scored_skills[0][0] >= 0.75:
            selected_skill_manifest = scored_skills[0][1]
            selected_skill = selected_skill_manifest.skill_id

        # -------------------------------------------------------------------
        # 6. Candidate Retrieval & Cross-Domain Spec Backfill
        # -------------------------------------------------------------------
        domain_specs: Dict[str, CapabilitySpec] = {}
        for dom in active_domains:
            for spec in self.registry.list_specs(domain=dom):
                domain_specs[spec.id] = spec

        # Ensure pinned capabilities are included even if domain wasn't active
        for cap_id, pin_cand in pinned_caps.items():
            if cap_id not in domain_specs:
                spec = self.registry.get_spec(cap_id)
                if spec is not None:
                    domain_specs[cap_id] = spec

        # Unconditional Spec Backfill for constituent skill capabilities
        if selected_skill_manifest is not None:
            all_skill_caps = (
                selected_skill_manifest.required_capabilities
                + selected_skill_manifest.optional_capabilities
            )
            for cap_id in all_skill_caps:
                if cap_id not in domain_specs:
                    spec = self.registry.get_spec(cap_id)
                    if spec is not None:
                        domain_specs[cap_id] = spec

        # -------------------------------------------------------------------
        # 7. Skill-Guided Prioritization & Floor Expansion
        # -------------------------------------------------------------------
        skill_required_caps: Dict[str, CapabilityCandidate] = {}
        skill_optional_caps: Dict[str, CapabilityCandidate] = {}
        skill_workflow_template: Optional[List[SkillStepTemplate]] = None
        skill_confirmation_policy: Optional[ConfirmationPolicy] = None

        if selected_skill_manifest is not None:
            skill_workflow_template = (
                [step.model_copy(deep=True) for step in selected_skill_manifest.workflow_template]
                if selected_skill_manifest.workflow_template
                else None
            )
            skill_confirmation_policy = selected_skill_manifest.confirmation_policy

            for cap_id in selected_skill_manifest.required_capabilities:
                spec = domain_specs.get(cap_id) or self.registry.get_spec(cap_id)
                if spec is not None:
                    if cap_id in pinned_caps:
                        pinned_caps[cap_id].rationale = "explicit_keyword_pinned+skill_required"
                    else:
                        skill_required_caps[cap_id] = CapabilityCandidate(
                            capability_id=cap_id,
                            domain=spec.domain,
                            score=0.98,
                            rationale="skill_required",
                            spec_summary=f"{spec.name}: {spec.description[:80]}",
                        )

            for cap_id in selected_skill_manifest.optional_capabilities:
                if cap_id not in pinned_caps and cap_id not in skill_required_caps:
                    spec = domain_specs.get(cap_id) or self.registry.get_spec(cap_id)
                    if spec is not None:
                        skill_optional_caps[cap_id] = CapabilityCandidate(
                            capability_id=cap_id,
                            domain=spec.domain,
                            score=0.75,
                            rationale="skill_optional",
                            spec_summary=f"{spec.name}: {spec.description[:80]}",
                        )

        # Dynamic Floor Expansion: all pinned + skill-required tools MUST be retained
        mandatory_caps: Dict[str, CapabilityCandidate] = {**pinned_caps, **skill_required_caps}
        effective_max = max(max_candidates, len(mandatory_caps))
        budget_expanded = effective_max > max_candidates

        final_candidates: List[CapabilityCandidate] = list(mandatory_caps.values())
        remaining_capacity = effective_max - len(final_candidates)

        # Budget-conscious optional capabilities ingestion
        if remaining_capacity > 0:
            for cap_id, opt_cand in skill_optional_caps.items():
                if remaining_capacity <= 0:
                    break
                final_candidates.append(opt_cand)
                remaining_capacity -= 1

        # Fill remaining capacity with domain capabilities
        if remaining_capacity > 0:
            domain_pool = {
                cap_id: spec
                for cap_id, spec in domain_specs.items()
                if cap_id not in mandatory_caps and cap_id not in skill_optional_caps
            }

            if len(domain_pool) <= remaining_capacity:
                for cap_id, spec in domain_pool.items():
                    final_candidates.append(
                        CapabilityCandidate(
                            capability_id=cap_id,
                            domain=spec.domain,
                            score=0.85 if spec.domain == primary_domain else 0.70,
                            rationale="domain_primary" if spec.domain == primary_domain else "pooled_domain",
                            spec_summary=f"{spec.name}: {spec.description[:80]}",
                        )
                    )
            else:
                # Dynamic lexical scoring for domain tools
                domain_scores: List[Tuple[float, CapabilityCandidate]] = []
                for cap_id, spec in domain_pool.items():
                    spec_text = f"{spec.id} {spec.name} {spec.domain} {spec.description}".lower()
                    spec_tokens = set(re.findall(r"\w+", spec_text))
                    overlap = len(prompt_tokens.intersection(spec_tokens))
                    base_score = 0.50 if spec.domain == primary_domain else 0.35
                    relevance_boost = min(0.40, overlap * 0.15)
                    score = round(min(0.90, base_score + relevance_boost), 3)

                    domain_scores.append(
                        (
                            score,
                            CapabilityCandidate(
                                capability_id=cap_id,
                                domain=spec.domain,
                                score=score,
                                rationale="lexical_relevance_pruned",
                                spec_summary=f"{spec.name}: {spec.description[:80]}",
                            ),
                        )
                    )

                domain_scores.sort(key=lambda x: x[0], reverse=True)
                for _, cand in domain_scores[:remaining_capacity]:
                    final_candidates.append(cand)

        # Deduplication
        deduped: List[CapabilityCandidate] = []
        seen_ids: Set[str] = set()
        for c in final_candidates:
            if c.capability_id not in seen_ids:
                seen_ids.add(c.capability_id)
                deduped.append(c)

        # -------------------------------------------------------------------
        # 8. Telemetry & RouteDecision Construction
        # -------------------------------------------------------------------
        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000, 3)

        reduction_ratio = 0.0
        if total_caps > 0:
            reduction_ratio = max(0.0, min(1.0, round(1.0 - (len(deduped) / total_caps), 4)))

        fallback_reason_str = "; ".join(fallback_reasons) if is_fail_open else None

        metadata: Dict[str, Any] = {
            "pinned_count": len(pinned_caps),
            "active_domain_count": len(active_domains),
            "is_multi_step": is_multi_step,
            "domain_confidence": domain_confidence,
            "selected_skill": selected_skill,
            "candidate_skills_count": len(candidate_skills),
            "budget_expanded": budget_expanded,
        }
        if budget_expanded:
            metadata["expanded_reason"] = "skill_required_capabilities_exceeded_max"

        return RouteDecision(
            request_id=req_id,
            selected_domain=primary_domain,
            candidate_domains=active_domains,
            selected_skill=selected_skill,
            candidate_skills=candidate_skills,
            skill_workflow_template=skill_workflow_template,
            skill_confirmation_policy=skill_confirmation_policy,
            candidates=deduped,
            is_fail_open=is_fail_open,
            fallback_reason=fallback_reason_str,
            catalog_reduction_ratio=reduction_ratio,
            total_registry_capabilities=total_caps,
            latency_ms=latency_ms,
            metadata=metadata,
        )
