"""
omni_engine.routing.router
==========================
Hierarchical Capability Router for the standalone LAYA Omni Agent.

Replaces legacy flat catalog slicing (ISSUE-02 [:12] truncation defect) with a
disciplined multi-tier routing pipeline:
Request -> DecisionFrame -> Domain Routing -> Candidate Pruning -> RouteDecision

Invariants:
- Fail-Open: Ambiguous, low-confidence, or multi-step requests widen candidate pools.
- Zero Tool Dropping: Explicit capability keywords pin required tools.
- Strict Latency SLA: Fast zero-inference short-circuits for single-domain candidate sets <= max_candidates.
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
from omni_engine.contracts.routing import CapabilityCandidate, RouteDecision
from omni_engine.decision.fabric import DecisionFabric
from omni_engine.providers.base import ProviderError, SystemOneProvider
from omni_engine.providers.system1 import LayaProvider, get_shared_laya_router


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


class HierarchicalRouter:
    """Hierarchical capability router driving multi-tier catalog reduction.
    
    Architecture:
    1. Input: User prompt + optional pre-computed DecisionFrame.
    2. Gating: Fast deterministic bypass for conversational or empty prompts.
    3. Domain Routing: Resolves primary and fail-open candidate domains.
    4. Explicit Pinning: Scans prompt for explicit capability tokens.
    5. Dynamic Pruning: Scans domain tools, prunes to top 3-6 candidates with zero-latency short circuits.
    6. Envelope Construction: Returns strongly typed RouteDecision.
    """

    def __init__(
        self,
        registry: Optional[CapabilityRegistry] = None,
        provider: Optional[SystemOneProvider] = None,
        fabric: Optional[DecisionFabric] = None,
    ) -> None:
        self.registry = registry or build_canonical_registry()
        self.provider = provider or LayaProvider()
        self.fabric = fabric or DecisionFabric(provider=self.provider)

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
            RouteDecision envelope containing ranked candidates and telemetry.
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

        # Rec-6: General Domain Promotion
        # If top domain is "general" and tools are needed, bypass "general"
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

        # Rec-1: Multi-Step Task Cross-Domain Retention
        needs_plan_val = getattr(frame.needs_plan, "value", False)
        needs_plan = needs_plan_val in [True, "needs_dag_plan", "true", "yes"]
        task_class = getattr(frame.task_class, "value", "simple_action")
        is_multi_step = needs_plan or task_class in ["multi_step_quest", "code_refactor"]

        if is_multi_step:
            is_fail_open = True
            fallback_reasons.append("multi_step_cross_domain_pooling")

        # Rec-3: Ambiguity & Low Confidence Fail-Open
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
            # Pool at least top-2 candidate domains + keyword detected domains
            for d in candidate_domains[:2]:
                if d not in active_domains:
                    active_domains.append(d)
            for d in keyword_detected_domains:
                if d not in active_domains:
                    active_domains.append(d)
        else:
            # Single primary domain
            if candidate_domains:
                active_domains = [candidate_domains[0]]
            elif keyword_detected_domains:
                active_domains = [list(keyword_detected_domains)[0]]

        # Absolute Fallback if active domains empty
        if not active_domains:
            active_domains = ["web", "dev", "os", "data", "browser"]
            is_fail_open = True
            fallback_reasons.append("empty_candidate_domains_fallback")

        primary_domain = active_domains[0] if active_domains else None

        # -------------------------------------------------------------------
        # 4. Explicit Capability Pinning (Rec-5)
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
        # 5. Candidate Retrieval from Active Domains
        # -------------------------------------------------------------------
        domain_specs: Dict[str, CapabilitySpec] = {}
        for dom in active_domains:
            for spec in self.registry.list_specs(domain=dom):
                domain_specs[spec.id] = spec

        # Ensure any pinned capabilities are included even if their domain wasn't active
        for cap_id, pin_cand in pinned_caps.items():
            if cap_id not in domain_specs:
                spec = self.registry.get_spec(cap_id)
                if spec:
                    domain_specs[cap_id] = spec

        # -------------------------------------------------------------------
        # 6. Candidate Scoring & Dynamic Pruning (Rec-2)
        # -------------------------------------------------------------------
        final_candidates: List[CapabilityCandidate] = []

        if len(domain_specs) <= max_candidates:
            # Zero-Inference Short-Circuit: retain all candidates without pruning!
            for cap_id, spec in domain_specs.items():
                if cap_id in pinned_caps:
                    final_candidates.append(pinned_caps[cap_id])
                else:
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
            # More candidates than max_candidates: Score and prune down to bounded set
            candidate_scores: List[Tuple[float, CapabilityCandidate]] = []
            
            # Fast lexical / semantic relevance scoring
            tokens = set(re.findall(r"\w+", prompt_lower))
            
            for cap_id, spec in domain_specs.items():
                if cap_id in pinned_caps:
                    candidate_scores.append((1.0, pinned_caps[cap_id]))
                    continue
                
                # Compute lexical relevance score against name, description, schema
                spec_text = f"{spec.id} {spec.name} {spec.domain} {spec.description}".lower()
                spec_tokens = set(re.findall(r"\w+", spec_text))
                
                overlap = len(tokens.intersection(spec_tokens))
                base_score = 0.50 if spec.domain == primary_domain else 0.35
                relevance_boost = min(0.45, overlap * 0.15)
                score = round(min(0.95, base_score + relevance_boost), 3)

                candidate_scores.append(
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

            # Sort descending by score
            candidate_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Select top max_candidates (at least min_candidates)
            selected_count = max(min_candidates, min(max_candidates, len(candidate_scores)))
            final_candidates = [cand for _, cand in candidate_scores[:selected_count]]

        # Ensure deduplication
        deduped: List[CapabilityCandidate] = []
        seen_ids: Set[str] = set()
        for c in final_candidates:
            if c.capability_id not in seen_ids:
                seen_ids.add(c.capability_id)
                deduped.append(c)

        # -------------------------------------------------------------------
        # 7. Telemetry & RouteDecision Construction
        # -------------------------------------------------------------------
        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000, 3)

        reduction_ratio = 0.0
        if total_caps > 0:
            reduction_ratio = max(0.0, min(1.0, round(1.0 - (len(deduped) / total_caps), 4)))

        fallback_reason_str = "; ".join(fallback_reasons) if is_fail_open else None

        return RouteDecision(
            request_id=req_id,
            selected_domain=primary_domain,
            candidate_domains=active_domains,
            candidates=deduped,
            is_fail_open=is_fail_open,
            fallback_reason=fallback_reason_str,
            catalog_reduction_ratio=reduction_ratio,
            total_registry_capabilities=total_caps,
            latency_ms=latency_ms,
            metadata={
                "pinned_count": len(pinned_caps),
                "active_domain_count": len(active_domains),
                "is_multi_step": is_multi_step,
                "domain_confidence": domain_confidence,
            },
        )
