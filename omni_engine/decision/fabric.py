"""
omni_engine.decision.fabric
===========================
System 1 Decision Fabric: High-frequency, strongly-typed DecisionFrame generation.

Adheres to Prime Directive & Repository Invariants:
- Fast Decision Nervous System: Evaluates multi-dimensional signals in a single batched pass.
- Deterministic Control (Invariant 1): Deterministic safety rules strictly override/pre-empt neural outputs.
- First-Class Signals (Invariant 7): Reversibility, risk, urgency, importance, and ambiguity are explicit.
- Hardware SLA: Target <35ms on CUDA GPU; hardware-aware CPU fallback budget (<5000ms).
- Graceful Fallback: Model failures return a safe, escalated DecisionFrame rather than throwing unhandled exceptions.
"""

import re
import time
import uuid
from typing import Any, Dict, List, Optional

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.calibration import CalibrationConfig
from omni_engine.contracts.decision import DecisionFrame, DecisionSignal
from omni_engine.contracts.enums import DecisionSignalType, ErrorCode
from omni_engine.providers.base import ProviderError, SystemOneProvider
from omni_engine.providers.system1 import LayaProvider, sanitize_float, sanitize_probabilities

# Default high-risk command patterns that mandate immediate safety floor escalation
DEFAULT_HIGH_RISK_PATTERNS = [
    r"\brmdir\b",
    r"\bdel\s+/[a-z]",
    r"\bformat\b",
    r"\bkill\b",
    r"\bkill_process\b",
    r"\bdrop\s+table\b",
    r"\bdrop\s+database\b",
    r"\brm\s+-rf\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"powershell\s+.*-enc",
    r"Invoke-Expression",
]


class DecisionFabric:
    """Coordinates high-frequency System 1 decisions, generating validated DecisionFrames."""

    def __init__(
        self,
        provider: Optional[SystemOneProvider] = None,
        high_risk_patterns: Optional[List[str]] = None,
        calibration: Optional[CalibrationConfig] = None,
    ) -> None:
        self.provider = provider if provider is not None else LayaProvider(preload=False)
        self.high_risk_patterns = high_risk_patterns or DEFAULT_HIGH_RISK_PATTERNS
        self._compiled_risk_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.high_risk_patterns
        ]
        self.calibration = calibration or CalibrationConfig()

    def _truncate_prompt(self, prompt: str, max_chars: int = 3000) -> str:
        """Sliding-window head-tail truncation to fit model context window."""
        if len(prompt) <= max_chars:
            return prompt
        half = (max_chars - 60) // 2
        return f"{prompt[:half]}\n[...TRUNCATED BY SYSTEM 1...]\n{prompt[-half:]}"

    def _build_empty_prompt_frame(self, request_id: str, t0: float) -> DecisionFrame:
        """Fast-path deterministic DecisionFrame for empty or whitespace prompts (<1ms)."""
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)
        prov_id = getattr(self.provider, "provider_id", "deterministic-fastpath")
        model_id = getattr(self.provider, "model_id", "rules-v1")

        def _sig(st: DecisionSignalType, val: Any, conf: float = 1.0) -> DecisionSignal:
            return DecisionSignal(
                signal_type=st,
                value=val,
                confidence=sanitize_float(conf),
                provider_id=prov_id,
                model_id=model_id,
                latency_ms=latency_ms,
            )

        return DecisionFrame(
            schema_version="1.0.0",
            request_id=request_id,
            timestamp=time.time(),
            intent=_sig(DecisionSignalType.INTENT, "empty"),
            task_class=_sig(DecisionSignalType.TASK_CLASS, "single_turn_reflex"),
            urgency=_sig(DecisionSignalType.URGENCY, "routine"),
            importance=_sig(DecisionSignalType.IMPORTANCE, "normal"),
            risk=_sig(DecisionSignalType.RISK, "safe_read_only"),
            reversibility=_sig(DecisionSignalType.REVERSIBILITY, "reversible"),
            ambiguity=_sig(DecisionSignalType.AMBIGUITY, "ambiguous"),
            needs_plan=_sig(DecisionSignalType.NEEDS_PLAN, False),
            needs_tools=_sig(DecisionSignalType.NEEDS_TOOLS, False),
            model_tier=_sig(DecisionSignalType.MODEL_TIER, "system_1"),
            needs_clarification=_sig(DecisionSignalType.NEEDS_CLARIFICATION, True),
            requires_action=_sig(DecisionSignalType.REQUIRES_ACTION, False),
            needs_generative_reasoning=_sig(DecisionSignalType.NEEDS_GENERATIVE_REASONING, False),
            escalation_required=_sig(DecisionSignalType.ESCALATION_REQUIRED, False),
            candidate_domains=["general"],
            total_latency_ms=latency_ms,
            provider_id=prov_id,
        )

    def _build_fallback_frame(
        self,
        request_id: str,
        t0: float,
        error_message: str,
    ) -> DecisionFrame:
        """Safe fallback DecisionFrame when provider raises an unhandled error."""
        latency_ms = round((time.perf_counter() - t0) * 1000, 3)
        base_prov = getattr(self.provider, "provider_id", "system1")
        prov_id = f"{base_prov}-fallback"
        model_id = getattr(self.provider, "model_id", "fallback-rules")

        def _sig(st: DecisionSignalType, val: Any, conf: float = 0.5) -> DecisionSignal:
            return DecisionSignal(
                signal_type=st,
                value=val,
                confidence=sanitize_float(conf),
                provider_id=prov_id,
                model_id=model_id,
                latency_ms=latency_ms,
                metadata={"fallback": True, "error": error_message},
            )

        return DecisionFrame(
            schema_version="1.0.0",
            request_id=request_id,
            timestamp=time.time(),
            intent=_sig(DecisionSignalType.INTENT, "troubleshooting"),
            task_class=_sig(DecisionSignalType.TASK_CLASS, "single_turn_reflex"),
            urgency=_sig(DecisionSignalType.URGENCY, "routine"),
            importance=_sig(DecisionSignalType.IMPORTANCE, "high"),
            risk=_sig(DecisionSignalType.RISK, "safe_read_only"),
            reversibility=_sig(DecisionSignalType.REVERSIBILITY, "reversible"),
            ambiguity=_sig(DecisionSignalType.AMBIGUITY, "ambiguous"),
            needs_plan=_sig(DecisionSignalType.NEEDS_PLAN, False),
            needs_tools=_sig(DecisionSignalType.NEEDS_TOOLS, False),
            model_tier=_sig(DecisionSignalType.MODEL_TIER, "pro"),
            needs_clarification=_sig(DecisionSignalType.NEEDS_CLARIFICATION, True),
            requires_action=_sig(DecisionSignalType.REQUIRES_ACTION, False),
            needs_generative_reasoning=_sig(DecisionSignalType.NEEDS_GENERATIVE_REASONING, True),
            escalation_required=_sig(DecisionSignalType.ESCALATION_REQUIRED, True),
            candidate_domains=["general"],
            total_latency_ms=latency_ms,
            provider_id=prov_id,
            raw_signals={},
        )

    def _get_batched_questions(self) -> Dict[str, Any]:
        """Returns the canonical set of questions mapped strictly to DecisionFrame fields."""
        return {
            "intent": {
                "type": "choice",
                "instructions": "Classify overall user intention:",
                "criteria": {
                    "informational": "General question, knowledge lookup, conversational chat, or explanation",
                    "task_execution": "Execute an action, run tools, modify files, manage processes, or automate tasks",
                    "troubleshooting": "Diagnose an error, debug code, inspect system state, or fix a failure",
                },
            },
            "task_class": {
                "type": "choice",
                "instructions": "Classify operational task structure:",
                "criteria": {
                    "single_turn_reflex": "Simple atomic task completed in one tool call or direct answer",
                    "multi_step_quest": "Complex goal requiring sequential steps, dependent tasks, or workflow",
                    "code_refactor": "Software engineering, code modification, debugging, or test execution",
                    "system_admin": "OS management, process termination, system diagnostics, or network tests",
                    "web_research": "Deep web search, documentation fetching, scraping, or data gathering",
                },
            },
            "domain": {
                "type": "choice",
                "instructions": "Determine primary capability domain:",
                "criteria": {
                    "os": "Operating system, processes, desktop apps, clipboard, diagnostics",
                    "dev": "Local files, code search, Python execution, git operations",
                    "web": "Web search, web scraping, HTTP API requests, file downloads",
                    "browser": "Visual browser automation, website interaction, browser screenshots",
                    "data": "SQLite database, data inspection, mathematical calculations",
                    "general": "General conversation, explanations, or conceptual questions",
                },
            },
            "urgency": {
                "type": "choice",
                "instructions": "Determine execution urgency:",
                "criteria": {
                    "immediate": "Emergency, high priority, critical blockage, or immediate action requested",
                    "routine": "Standard, non-urgent request or normal priority task",
                },
            },
            "importance": {
                "type": "choice",
                "instructions": "Determine consequence severity:",
                "criteria": {
                    "high": "High-consequence action, production files, critical system state, or sensitive data",
                    "normal": "Standard everyday task or low-consequence operation",
                },
            },
            "risk": {
                "type": "choice",
                "instructions": "Determine blast radius and safety risk:",
                "criteria": {
                    "safe_read_only": "Read-only inspection, search, diagnostics, or information retrieval",
                    "reversible_mutation": "Writing local files, clipboard copy, safe modifications with easy undo",
                    "high_risk_system": "Killing processes, executing arbitrary shell code, system-wide changes, or deletions",
                },
            },
            "reversibility": {
                "type": "choice",
                "instructions": "Determine action reversibility (Invariant 7):",
                "criteria": {
                    "reversible": "Changes can be easily rolled back or undone (e.g. creating a new temp file, clipboard)",
                    "irreversible": "Action cannot be undone automatically (e.g. killing a process, running external POST API, destructive overwrite)",
                },
            },
            "ambiguity": {
                "type": "choice",
                "instructions": "Determine clarity and completeness of instructions:",
                "criteria": {
                    "unambiguous": "Clear, specific, and actionable request with all needed parameters",
                    "ambiguous": "Vague, underspecified, or missing critical parameters (e.g. which file, which process)",
                },
            },
            "needs_plan": {
                "type": "choice",
                "instructions": "Determine if multi-step DAG planning is required:",
                "criteria": {
                    "needs_dag_plan": "Requires multi-step decomposition, planning, and validated DAG execution",
                    "direct": "Can be executed directly in a single step without DAG decomposition",
                },
            },
            "needs_tools": {
                "type": "choice",
                "instructions": "Determine if external capability tools are needed:",
                "criteria": {
                    "tools_required": "Requires invoking system tools, reading files, searching web, or running commands",
                    "no_tools": "Can be answered directly from knowledge without running external tools",
                },
            },
            "model_tier": {
                "type": "choice",
                "instructions": "Select appropriate model tier for execution:",
                "criteria": {
                    "system_1": "Reflexive System 1 decision or direct deterministic tool invocation",
                    "flash": "Fast light generative model for simple extraction, summary, or template filling",
                    "pro": "High-capability generative reasoning model for complex novel planning or difficult code",
                },
            },
            "needs_clarification": {
                "type": "choice",
                "instructions": "Determine if clarification question is required:",
                "criteria": {
                    "ask_user": "High ambiguity or missing critical information requires clarifying question first",
                    "proceed": "Instructions are sufficiently clear to proceed without asking the user",
                },
            },
            "requires_action": {
                "type": "choice",
                "instructions": "Determine if real-world execution is needed vs conversational response:",
                "criteria": {
                    "action_required": "User wants an action performed in the environment",
                    "reply_only": "User only wants an informative text reply",
                },
            },
            "needs_generative_reasoning": {
                "type": "choice",
                "instructions": "Determine if generative LLM is strictly required:",
                "criteria": {
                    "generative_required": "Novel planning, creative generation, or complex synthesis required",
                    "deterministic_or_s1": "Can be solved with deterministic logic, known skill, or System 1 decision",
                },
            },
            "escalation_required": {
                "type": "choice",
                "instructions": "Determine if policy escalation is required:",
                "criteria": {
                    "escalate": "Exceeds safe autonomy, touches forbidden operations, or requires human intervention",
                    "autonomous": "Can be handled autonomously within agent capabilities and safety policies",
                },
            },
        }

    def _get_triage_questions(self) -> Dict[str, Any]:
        """Returns the minimal triage question set (4 questions) for rapid conversational routing."""
        all_q = self._get_batched_questions()
        return {
            "intent": all_q["intent"],
            "risk": all_q["risk"],
            "needs_tools": all_q["needs_tools"],
            "requires_action": all_q["requires_action"],
        }

    def _assemble_decision_frame(
        self,
        cleaned_prompt: str,
        signals: Dict[str, DecisionSignal],
        t0: float,
        req_id: str,
    ) -> DecisionFrame:
        """Assembles a validated DecisionFrame from neural signals and deterministic safety floors."""
        t1 = time.perf_counter()
        total_latency_ms = round((t1 - t0) * 1000, 3)
        cal_ver = self.calibration.calibration_version

        # Helper to safely retrieve signal with guaranteed type and bounds
        def _get_sig(name: str, def_type: DecisionSignalType, def_val: Any) -> DecisionSignal:
            if name in signals:
                s = signals[name]
                meta = dict(s.metadata) if s.metadata else {}
                meta.setdefault("calibration_version", cal_ver)
                if s.signal_type != def_type:
                    return DecisionSignal(
                        signal_type=def_type,
                        value=s.value,
                        confidence=s.confidence,
                        probabilities=s.probabilities,
                        provider_id=s.provider_id,
                        model_id=s.model_id,
                        latency_ms=s.latency_ms,
                        metadata=meta,
                    )
                if "calibration_version" not in (s.metadata or {}):
                    return DecisionSignal(
                        signal_type=s.signal_type,
                        value=s.value,
                        confidence=s.confidence,
                        probabilities=s.probabilities,
                        provider_id=s.provider_id,
                        model_id=s.model_id,
                        latency_ms=s.latency_ms,
                        metadata=meta,
                    )
                return s
            return DecisionSignal(
                signal_type=def_type,
                value=def_val,
                confidence=0.5,
                provider_id=getattr(self.provider, "provider_id", "laya"),
                model_id=getattr(self.provider, "model_id", "default"),
                latency_ms=total_latency_ms,
                metadata={"calibration_version": cal_ver},
            )

        intent_sig = _get_sig("intent", DecisionSignalType.INTENT, "informational")
        task_class_sig = _get_sig("task_class", DecisionSignalType.TASK_CLASS, "single_turn_reflex")
        urgency_sig = _get_sig("urgency", DecisionSignalType.URGENCY, "routine")
        importance_sig = _get_sig("importance", DecisionSignalType.IMPORTANCE, "normal")
        risk_sig = _get_sig("risk", DecisionSignalType.RISK, "safe_read_only")
        reversibility_sig = _get_sig("reversibility", DecisionSignalType.REVERSIBILITY, "reversible")
        ambiguity_sig = _get_sig("ambiguity", DecisionSignalType.AMBIGUITY, "unambiguous")
        needs_plan_sig = _get_sig("needs_plan", DecisionSignalType.NEEDS_PLAN, False)
        needs_tools_sig = _get_sig("needs_tools", DecisionSignalType.NEEDS_TOOLS, False)
        model_tier_sig = _get_sig("model_tier", DecisionSignalType.MODEL_TIER, "system_1")
        needs_clarification_sig = _get_sig("needs_clarification", DecisionSignalType.NEEDS_CLARIFICATION, False)
        requires_action_sig = _get_sig("requires_action", DecisionSignalType.REQUIRES_ACTION, False)
        needs_gen_sig = _get_sig("needs_generative_reasoning", DecisionSignalType.NEEDS_GENERATIVE_REASONING, False)
        escalation_sig = _get_sig("escalation_required", DecisionSignalType.ESCALATION_REQUIRED, False)

        # 3. Normalize Boolean Values
        needs_plan_bool = needs_plan_sig.value in [True, "needs_dag_plan", "true", "yes"]
        needs_tools_bool = needs_tools_sig.value in [True, "tools_required", "true", "yes"]
        needs_clarification_bool = needs_clarification_sig.value in [True, "ask_user", "true", "yes"]
        requires_action_bool = requires_action_sig.value in [True, "action_required", "true", "yes"]
        needs_gen_bool = needs_gen_sig.value in [True, "generative_required", "true", "yes"]
        escalation_bool = escalation_sig.value in [True, "escalate", "true", "yes"]

        # 4. Deterministic Pre-emption & Safety Escalation Rules (Invariants 1 & 7)

        # 4a. High-Risk Safety Floor Override
        is_pattern_high_risk = any(p.search(cleaned_prompt) for p in self._compiled_risk_patterns)
        if is_pattern_high_risk:
            risk_sig = DecisionSignal(
                signal_type=DecisionSignalType.RISK,
                value="high_risk_system",
                confidence=1.0,
                provider_id="deterministic-safety-rule",
                model_id="rule-pattern-matcher",
                latency_ms=total_latency_ms,
                metadata={"override": "high_risk_pattern_detected", "calibration_version": cal_ver},
            )
            reversibility_sig = DecisionSignal(
                signal_type=DecisionSignalType.REVERSIBILITY,
                value="irreversible",
                confidence=1.0,
                provider_id="deterministic-safety-rule",
                model_id="rule-pattern-matcher",
                latency_ms=total_latency_ms,
                metadata={"calibration_version": cal_ver},
            )
            escalation_bool = True
            requires_action_bool = True

        # 4b. Reversibility Invariant (Destructive actions must be marked irreversible)
        if risk_sig.value == "high_risk_system" or not reversibility_sig.value:
            if risk_sig.value == "high_risk_system":
                reversibility_sig = DecisionSignal(
                    signal_type=DecisionSignalType.REVERSIBILITY,
                    value="irreversible",
                    confidence=max(reversibility_sig.confidence, risk_sig.confidence),
                    provider_id=risk_sig.provider_id,
                    model_id=risk_sig.model_id,
                    latency_ms=total_latency_ms,
                    metadata={"calibration_version": cal_ver},
                )

        # 4c. Ambiguity Escalation (Calibrated Thresholds)
        ambiguity_max_thresh = self.calibration.model_thresholds.ambiguity_max
        ambiguity_min_words = self.calibration.deterministic_policy.ambiguity_min_words

        is_ambiguous = (
            ambiguity_sig.value in ["ambiguous", True]
            or (isinstance(ambiguity_sig.value, (int, float)) and ambiguity_sig.value > ambiguity_max_thresh)
            or (ambiguity_sig.probabilities and ambiguity_sig.probabilities.get("ambiguous", 0.0) > ambiguity_max_thresh)
            or len(cleaned_prompt.split()) <= ambiguity_min_words
        )
        if is_ambiguous:
            needs_clarification_bool = True
            needs_gen_bool = True

        # 4d. Action vs Conversation Disambiguation
        if intent_sig.value == "informational" and not needs_tools_bool:
            requires_action_bool = False
            needs_plan_bool = False
            needs_gen_bool = False

        if intent_sig.value in ["task_execution", "troubleshooting"]:
            requires_action_bool = True
            if task_class_sig.value in ["multi_step_quest", "code_refactor"]:
                needs_plan_bool = True
                needs_tools_bool = True

        # 4e. Generative Model Necessity Gate (Invariant 3)
        if not needs_plan_bool and not needs_clarification_bool and risk_sig.value == "safe_read_only":
            needs_gen_bool = False
            model_tier_val = "system_1"
        elif needs_plan_bool or importance_sig.value == "high":
            needs_gen_bool = True
            model_tier_val = "pro" if importance_sig.value == "high" else "flash"
        else:
            model_tier_val = "flash" if needs_gen_bool else "system_1"

        # 5. Extract Candidate Domains
        candidate_domains = []
        domain_sig = signals.get("domain")
        if domain_sig and domain_sig.probabilities:
            sorted_domains = sorted(
                domain_sig.probabilities.items(), key=lambda kv: kv[1], reverse=True
            )
            candidate_domains = [k for k, _ in sorted_domains]
        elif domain_sig and isinstance(domain_sig.value, str):
            candidate_domains = [domain_sig.value]
        else:
            candidate_domains = ["general"]

        if not candidate_domains:
            candidate_domains = ["general"]

        # 6. Re-package Normalized Boolean Signals
        prov_id = getattr(self.provider, "provider_id", "laya")
        mod_id = getattr(self.provider, "model_id", "ModernBERT-large")

        def _update_bool_sig(orig_sig: DecisionSignal, val: bool) -> DecisionSignal:
            meta = dict(orig_sig.metadata) if orig_sig.metadata else {}
            meta.setdefault("calibration_version", cal_ver)
            return DecisionSignal(
                signal_type=orig_sig.signal_type,
                value=val,
                confidence=sanitize_float(orig_sig.confidence),
                probabilities=orig_sig.probabilities,
                provider_id=orig_sig.provider_id or prov_id,
                model_id=orig_sig.model_id or mod_id,
                latency_ms=orig_sig.latency_ms,
                metadata=meta,
            )

        needs_plan_sig = _update_bool_sig(needs_plan_sig, needs_plan_bool)
        needs_tools_sig = _update_bool_sig(needs_tools_sig, needs_tools_bool)
        needs_clarification_sig = _update_bool_sig(needs_clarification_sig, needs_clarification_bool)
        requires_action_sig = _update_bool_sig(requires_action_sig, requires_action_bool)
        needs_gen_sig = _update_bool_sig(needs_gen_sig, needs_gen_bool)
        escalation_sig = _update_bool_sig(escalation_sig, escalation_bool)

        model_tier_sig = DecisionSignal(
            signal_type=DecisionSignalType.MODEL_TIER,
            value=model_tier_val,
            confidence=sanitize_float(model_tier_sig.confidence),
            provider_id=prov_id,
            model_id=mod_id,
            latency_ms=total_latency_ms,
            metadata={"calibration_version": cal_ver},
        )

        raw_signals_store = dict(signals)

        return DecisionFrame(
            schema_version="1.0.0",
            request_id=req_id,
            timestamp=time.time(),
            intent=intent_sig,
            task_class=task_class_sig,
            urgency=urgency_sig,
            importance=importance_sig,
            risk=risk_sig,
            reversibility=reversibility_sig,
            ambiguity=ambiguity_sig,
            needs_plan=needs_plan_sig,
            needs_tools=needs_tools_sig,
            model_tier=model_tier_sig,
            needs_clarification=needs_clarification_sig,
            requires_action=requires_action_sig,
            needs_generative_reasoning=needs_gen_sig,
            escalation_required=escalation_sig,
            candidate_domains=candidate_domains,
            total_latency_ms=total_latency_ms,
            provider_id=prov_id,
            raw_signals=raw_signals_store,
        )

    def evaluate(
        self,
        prompt: str,
        session_context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> DecisionFrame:
        """Evaluates input prompt through System 1 nervous system, returning validated DecisionFrame."""
        t0 = time.perf_counter()
        req_id = request_id or str(uuid.uuid4())
        raw_prompt = prompt or ""

        # 1. Deterministic Fast-Path: Empty or Whitespace Only
        if not raw_prompt.strip():
            return self._build_empty_prompt_frame(req_id, t0)

        cleaned_prompt = self._truncate_prompt(raw_prompt.strip())
        ctx = {"prompt": cleaned_prompt}
        if session_context:
            ctx.update(session_context)

        # 2. Neural Evaluation Pass (Batched Single Forward Pass)
        questions = self._get_batched_questions()
        try:
            signals = self.provider.predict_signals(context=ctx, questions=questions)
        except Exception as e:
            return self._build_fallback_frame(req_id, t0, str(e))

        return self._assemble_decision_frame(cleaned_prompt, signals, t0, req_id)

    def evaluate_adaptive(
        self,
        prompt: str,
        session_context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> DecisionFrame:
        """Adaptive two-stage evaluation: fast triage for conversational queries, full pass for tasks.
        
        Saves significant latency on CPU by evaluating only 4 triage criteria for safe informational queries.
        """
        t0 = time.perf_counter()
        req_id = request_id or str(uuid.uuid4())
        raw_prompt = prompt or ""

        # 1. Deterministic Fast-Path: Empty or Whitespace Only
        if not raw_prompt.strip():
            return self._build_empty_prompt_frame(req_id, t0)

        cleaned_prompt = self._truncate_prompt(raw_prompt.strip())
        ctx = {"prompt": cleaned_prompt}
        if session_context:
            ctx.update(session_context)

        # 2. Deterministic High-Risk Pattern Check: If regex matches, execute full evaluation
        is_pattern_high_risk = any(p.search(cleaned_prompt) for p in self._compiled_risk_patterns)
        if is_pattern_high_risk:
            questions = self._get_batched_questions()
            try:
                signals = self.provider.predict_signals(context=ctx, questions=questions)
            except Exception as e:
                return self._build_fallback_frame(req_id, t0, str(e))
            return self._assemble_decision_frame(cleaned_prompt, signals, t0, req_id)

        # 3. Stage 1: Fast Triage Pass (4 questions)
        triage_q = self._get_triage_questions()
        try:
            triage_signals = self.provider.predict_signals(context=ctx, questions=triage_q)
        except Exception as e:
            return self._build_fallback_frame(req_id, t0, str(e))

        intent_sig = triage_signals.get("intent")
        intent_val = intent_sig.value if intent_sig else "informational"
        risk_sig = triage_signals.get("risk")
        risk_val = risk_sig.value if risk_sig else "safe_read_only"
        needs_tools_sig = triage_signals.get("needs_tools")
        needs_tools = (needs_tools_sig.value in [True, "tools_required", "true", "yes"]) if needs_tools_sig else False
        req_action_sig = triage_signals.get("requires_action")
        requires_action = (req_action_sig.value in [True, "action_required", "true", "yes"]) if req_action_sig else False

        # 4. Fast Conversational Exit
        if intent_val == "informational" and risk_val == "safe_read_only" and not needs_tools and not requires_action:
            cal_ver = self.calibration.calibration_version
            triage_lat = round((time.perf_counter() - t0) * 1000, 3)
            prov_id = getattr(self.provider, "provider_id", "laya")
            mod_id = getattr(self.provider, "model_id", "ModernBERT-large")

            words = cleaned_prompt.split()
            ambig_min_w = self.calibration.deterministic_policy.ambiguity_min_words
            is_ambig = len(words) <= ambig_min_w
            ambig_val = "ambiguous" if is_ambig else "unambiguous"

            def _synthesize(st: DecisionSignalType, val: Any) -> DecisionSignal:
                return DecisionSignal(
                    signal_type=st,
                    value=val,
                    confidence=0.95,
                    provider_id=prov_id,
                    model_id=mod_id,
                    latency_ms=triage_lat,
                    metadata={"calibration_version": cal_ver, "adaptive_triage": "early_exit"},
                )

            signals = dict(triage_signals)
            intent_meta = dict(intent_sig.metadata) if intent_sig and intent_sig.metadata else {}
            intent_meta["adaptive_triage"] = "early_exit"
            signals["intent"] = DecisionSignal(
                signal_type=DecisionSignalType.INTENT,
                value=intent_val,
                confidence=intent_sig.confidence if intent_sig else 0.95,
                probabilities=intent_sig.probabilities if intent_sig else None,
                provider_id=intent_sig.provider_id if intent_sig else prov_id,
                model_id=intent_sig.model_id if intent_sig else mod_id,
                latency_ms=triage_lat,
                metadata=intent_meta,
            )
            signals["task_class"] = _synthesize(DecisionSignalType.TASK_CLASS, "single_turn_reflex")
            signals["urgency"] = _synthesize(DecisionSignalType.URGENCY, "routine")
            signals["importance"] = _synthesize(DecisionSignalType.IMPORTANCE, "normal")
            signals["reversibility"] = _synthesize(DecisionSignalType.REVERSIBILITY, "reversible")
            signals["ambiguity"] = _synthesize(DecisionSignalType.AMBIGUITY, ambig_val)
            signals["needs_plan"] = _synthesize(DecisionSignalType.NEEDS_PLAN, False)
            signals["model_tier"] = _synthesize(DecisionSignalType.MODEL_TIER, "system_1")
            signals["needs_clarification"] = _synthesize(DecisionSignalType.NEEDS_CLARIFICATION, is_ambig)
            signals["needs_generative_reasoning"] = _synthesize(DecisionSignalType.NEEDS_GENERATIVE_REASONING, False)
            signals["escalation_required"] = _synthesize(DecisionSignalType.ESCALATION_REQUIRED, False)
            signals["domain"] = DecisionSignal(
                signal_type=DecisionSignalType.DOMAIN,
                value="general",
                confidence=1.0,
                probabilities={"general": 1.0},
                provider_id=prov_id,
                model_id=mod_id,
                latency_ms=triage_lat,
                metadata={"calibration_version": cal_ver, "adaptive_triage": "early_exit"},
            )

            return self._assemble_decision_frame(cleaned_prompt, signals, t0, req_id)

        # 5. Stage 2: Full pass for tasks / tools / risk
        all_q = self._get_batched_questions()
        remaining_q = {k: v for k, v in all_q.items() if k not in triage_q}
        try:
            remaining_signals = self.provider.predict_signals(context=ctx, questions=remaining_q)
        except Exception as e:
            return self._build_fallback_frame(req_id, t0, str(e))

        combined_signals = dict(triage_signals)
        combined_signals.update(remaining_signals)
        return self._assemble_decision_frame(cleaned_prompt, combined_signals, t0, req_id)

