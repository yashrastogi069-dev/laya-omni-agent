"""
omni_engine.policy.engine
=========================
Master Deterministic Policy Engine for capability invocation gating and safety.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Models propose; deterministic policy decides.
- Invariant 3 in AGENTS.md: Hard Invariant Inviolability — Forbidden operations cannot be bypassed by user_confirmed=True.
- Invariant 4: Strongly Typed Contracts — Emits validated PolicyDecision envelopes.
- Invariant 7: Signals are First-Class — Explicitly assesses blast-radius, reversibility, and risk.
"""

import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    AUTONOMY_RANK,
    ConfirmationPolicy,
)
from omni_engine.contracts.policy import (
    ActionAssessment,
    PolicyDecision,
    PolicyEffect,
    PolicyRule,
)
from .rules import (
    canonicalize_path,
    is_protected_path,
    is_protected_process,
    scan_embedded_commands,
)
from .store import PolicyStore


BASE_ACTION_CLASS_RISK: Dict[ActionClass, float] = {
    ActionClass.READ_ONLY: 0.0,
    ActionClass.LOCAL_CREATE: 0.20,
    ActionClass.LOCAL_UPDATE: 0.35,
    ActionClass.LOCAL_DELETE: 0.70,
    ActionClass.EXTERNAL_CREATE: 0.30,
    ActionClass.EXTERNAL_UPDATE: 0.55,
    ActionClass.EXTERNAL_SEND: 0.75,
    ActionClass.EXTERNAL_DELETE: 0.90,
    ActionClass.SYSTEM_ACTION: 0.80,
    ActionClass.SECURITY_SENSITIVE: 0.85,
    ActionClass.FINANCIAL: 1.00,
}

SQL_DESTRUCTIVE_PATTERN = re.compile(
    r"""\b(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE|ALTER\s+TABLE\s+.*\s+DROP)\b""",
    re.IGNORECASE,
)

DESTRUCTIVE_COMMAND_TOKENS = [
    "remove-item",
    "del",
    "rmdir",
    "format",
    "stop-process",
    "kill",
    "rm -rf",
    "rm -f",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
]


class PolicyEngine:
    """Evaluates proposed capability invocations against deterministic safety policies."""

    def __init__(
        self,
        store: Optional[PolicyStore] = None,
        default_autonomy: AutonomyProfile = AutonomyProfile.SAFE_ASSISTANT,
        mode: Optional[str] = None,
    ) -> None:
        self.store = store or PolicyStore()
        self.default_autonomy = default_autonomy
        self.mode = mode or os.environ.get("LAYA_V2_MODE", "active").lower()

    def assess_action(
        self,
        spec: CapabilitySpec,
        arguments: Dict[str, Any],
        session_context: Optional[Dict[str, Any]] = None,
    ) -> ActionAssessment:
        """Deterministically calculates risk, reversibility, and blast-radius."""
        # 1. Determine destructiveness
        is_destructive = spec.action_class in (ActionClass.LOCAL_DELETE, ActionClass.EXTERNAL_DELETE)

        if spec.id == "kill_process":
            is_destructive = True

        elif spec.id == "file_write":
            path = arguments.get("filepath") or arguments.get("file_path")
            if path and os.path.exists(path):
                is_destructive = True

        elif spec.id == "sqlite_exec":
            query = arguments.get("query", "")
            if SQL_DESTRUCTIVE_PATTERN.search(query):
                is_destructive = True

        elif spec.id in ("powershell", "run_python"):
            cmd = (arguments.get("command") or arguments.get("code") or "").lower()
            if any(tok in cmd for tok in DESTRUCTIVE_COMMAND_TOKENS):
                is_destructive = True

        # 2. Determine reversibility
        is_reversible = False
        if spec.action_class == ActionClass.READ_ONLY:
            is_reversible = True
        elif spec.action_class == ActionClass.LOCAL_CREATE:
            is_reversible = True
        elif spec.action_class == ActionClass.LOCAL_UPDATE and not is_destructive:
            is_reversible = True

        # 3. Identify sensitive targets
        sensitive_targets: List[str] = []

        # Check path arguments
        for k in ("filepath", "file_path", "path", "filename", "db_path", "save_path"):
            val = arguments.get(k)
            if val and isinstance(val, str):
                prot, reason = is_protected_path(val)
                if prot:
                    sensitive_targets.append(f"path:{val}")

        # Check process arguments
        for k in ("target", "pid"):
            val = arguments.get(k)
            if val is not None:
                prot, reason = is_protected_process(val)
                if prot:
                    sensitive_targets.append(f"process:{val}")

        # Check domain/url arguments
        for k in ("url", "host"):
            val = arguments.get(k)
            if val and isinstance(val, str):
                val_lower = val.lower()
                for rule in self.store.get_active_rules():
                    for dom in rule.target_domains:
                        if dom in val_lower:
                            sensitive_targets.append(f"domain:{val}")

        # Check financial browser interactions (REQ-B4)
        if spec.id in ("browser_interact", "browser.interact"):
            action = str(arguments.get("action") or "").lower()
            target = str(arguments.get("target") or "").lower()
            url = str(arguments.get("url") or "").lower()
            financial_terms = ["pay", "checkout", "buy", "order", "purchase", "card", "cvv", "billing", "subscribe"]
            if action == "confirm_purchase" or any(t in target or t in url for t in financial_terms):
                sensitive_targets.append("financial:browser_checkout")

        # 4. Determine blast radius
        blast_radius = "NONE"
        if spec.action_class == ActionClass.READ_ONLY and not sensitive_targets:
            blast_radius = "NONE"
        elif sensitive_targets or spec.action_class in (ActionClass.SECURITY_SENSITIVE, ActionClass.FINANCIAL):
            blast_radius = "SECURITY_CRITICAL"
        elif spec.id in ("file_read", "file_write", "download_file"):
            blast_radius = "LOCAL_FILE"
        elif spec.id in ("directory_tree", "search_code", "git_status"):
            blast_radius = "LOCAL_WORKSPACE"
        elif spec.id in ("kill_process", "launch_app", "powershell", "run_python", "clipboard", "desktop_screenshot"):
            blast_radius = "LOCAL_SYSTEM"
        elif spec.id in ("web_search", "scrape_url", "http_api", "visual_browse", "browser_screenshot", "ping_test", "deep_research", "research.deep", "browser_interact", "browser.interact"):
            blast_radius = "EXTERNAL_NETWORK"

        # 5. Calculate composite risk score in [0.0, 1.0]
        base_risk = BASE_ACTION_CLASS_RISK.get(spec.action_class, 0.50)
        modifier = 0.0

        if sensitive_targets:
            modifier += 0.25
        if is_destructive:
            modifier += 0.15
        if not is_reversible:
            modifier += 0.10
        if spec.confirmation_policy == ConfirmationPolicy.ALWAYS:
            modifier += 0.10

        risk_score = round(min(1.0, max(0.0, base_risk + modifier)), 3)

        return ActionAssessment(
            capability_id=spec.id,
            action_class=spec.action_class,
            autonomy_required=spec.minimum_autonomy_profile,
            is_destructive=is_destructive,
            is_reversible=is_reversible,
            sensitive_targets=sensitive_targets,
            blast_radius=blast_radius,
            risk_score=risk_score,
        )

    def _make_decision(
        self,
        request_id: str,
        capability_id: str,
        effect: PolicyEffect,
        matched_rules: List[str],
        assessment: ActionAssessment,
        start_time: float,
        denial_reason: Optional[str] = None,
        confirmation_prompt: Optional[str] = None,
        is_hard_invariant: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> PolicyDecision:
        t1 = time.perf_counter()
        latency_ms = round((t1 - start_time) * 1000, 3)
        meta = extra_metadata or {}
        meta["mode"] = self.mode

        # If in shadow mode and NOT a hard invariant, simulate ALLOW while recording shadow telemetry
        if self.mode == "shadow" and not is_hard_invariant and effect != PolicyEffect.ALLOW:
            meta["shadow_mode"] = True
            meta["shadow_original_effect"] = effect.value
            meta["shadow_matched_rules"] = matched_rules
            if denial_reason:
                meta["shadow_denial_reason"] = denial_reason
            if confirmation_prompt:
                meta["shadow_confirmation_prompt"] = confirmation_prompt
            return PolicyDecision(
                request_id=request_id,
                capability_id=capability_id,
                allowed=True,
                effect=PolicyEffect.ALLOW,
                matched_rules=matched_rules,
                assessment=assessment,
                latency_ms=latency_ms,
                metadata=meta,
            )

        allowed = (effect == PolicyEffect.ALLOW)
        return PolicyDecision(
            request_id=request_id,
            capability_id=capability_id,
            allowed=allowed,
            effect=effect,
            matched_rules=matched_rules,
            denial_reason=denial_reason,
            confirmation_prompt=confirmation_prompt,
            assessment=assessment,
            latency_ms=latency_ms,
            metadata=meta,
        )

    def evaluate(
        self,
        capability: Any,
        arguments: Dict[str, Any],
        autonomy_profile: Optional[AutonomyProfile] = None,
        user_confirmed: bool = False,
        session_context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> PolicyDecision:
        """Evaluates a proposed invocation and returns an authoritative PolicyDecision.
        
        Evaluates in order:
        Stage 0: System Hard Invariants (Rule-0: Inviolable, user_confirmed strictly ignored).
        Stage 1: User Persistent Blacklist Rules (PolicyStore).
        Stage 2: Autonomy Profile Gating (ADVISOR read-only floor, profile ceilings).
        Stage 3: Capability Confirmation Policy (ALWAYS, POLICY_CONTROLLED high-risk floors).
        Stage 4: Baseline Default.
        """
        t0 = time.perf_counter()
        spec: CapabilitySpec = getattr(capability, "spec", capability)
        req_id = request_id or f"pol_{uuid.uuid4().hex[:8]}"
        current_autonomy = autonomy_profile or self.default_autonomy
        assessment = self.assess_action(spec, arguments, session_context)

        # -------------------------------------------------------------------
        # STAGE 0: SYSTEM HARD INVARIANTS (INVIOLABLE, user_confirmed IGNORED)
        # -------------------------------------------------------------------
        # 1. Embedded Command Scanner (git reset --hard, disk format, etc.)
        for arg_key in ("command", "code", "app_name", "query"):
            arg_val = arguments.get(arg_key)
            if arg_val and isinstance(arg_val, str):
                violation, reason = scan_embedded_commands(arg_val)
                if violation:
                    return self._make_decision(
                        request_id=req_id,
                        capability_id=spec.id,
                        effect=PolicyEffect.DENY,
                        matched_rules=["RULE_0_FORBIDDEN_OPERATIONS"],
                        assessment=assessment,
                        start_time=t0,
                        denial_reason=reason,
                        is_hard_invariant=True,
                        extra_metadata={"inviolable_tier": 0},
                    )

        # 2. Protected System Paths (Windows, Program Files, .ssh, .env, root drives)
        if spec.action_class != ActionClass.READ_ONLY or spec.id == "file_write":
            for arg_key in ("filepath", "file_path", "path", "filename", "db_path", "save_path"):
                arg_val = arguments.get(arg_key)
                if arg_val and isinstance(arg_val, str):
                    is_prot, reason = is_protected_path(arg_val)
                    if is_prot:
                        return self._make_decision(
                            request_id=req_id,
                            capability_id=spec.id,
                            effect=PolicyEffect.DENY,
                            matched_rules=["RULE_0_PROTECTED_SYSTEM_PATHS"],
                            assessment=assessment,
                            start_time=t0,
                            denial_reason=reason,
                            is_hard_invariant=True,
                            extra_metadata={"inviolable_tier": 0},
                        )

        # 3. Protected Critical System Processes (csrss, lsass, smss, services, PID 0/4)
        if spec.id == "kill_process":
            target = arguments.get("target") or arguments.get("pid")
            is_prot_proc, reason = is_protected_process(target)
            if is_prot_proc:
                return self._make_decision(
                    request_id=req_id,
                    capability_id=spec.id,
                    effect=PolicyEffect.DENY,
                    matched_rules=["RULE_0_PROTECTED_SYSTEM_PROCESSES"],
                    assessment=assessment,
                    start_time=t0,
                    denial_reason=reason,
                    is_hard_invariant=True,
                    extra_metadata={"inviolable_tier": 0},
                )

        # -------------------------------------------------------------------
        # STAGE 1: USER PERSISTENT BLACKLIST RULES
        # -------------------------------------------------------------------
        for rule in self.store.get_active_rules():
            if rule.effect == PolicyEffect.DENY:
                # Check path match
                if rule.target_paths:
                    for arg_key in ("filepath", "file_path", "path", "filename", "db_path", "save_path"):
                        val = arguments.get(arg_key)
                        if val and isinstance(val, str):
                            val_canon = canonicalize_path(val)
                            for blocked in rule.target_paths:
                                b_norm = blocked.lower().replace("/", "\\").rstrip("\\")
                                val_norm = val_canon.replace("/", "\\").rstrip("\\")
                                if ":" in b_norm or b_norm.startswith("\\\\"):
                                    is_match = (val_norm == b_norm or val_norm.startswith(b_norm + "\\"))
                                else:
                                    is_match = (
                                        val_norm == b_norm
                                        or val_norm.startswith(b_norm + "\\")
                                        or f"\\{b_norm}\\" in f"\\{val_norm}\\"
                                        or val_norm.endswith(f"\\{b_norm}")
                                    )
                                if is_match:
                                    return self._make_decision(
                                        request_id=req_id,
                                        capability_id=spec.id,
                                        effect=PolicyEffect.DENY,
                                        matched_rules=[rule.rule_id],
                                        assessment=assessment,
                                        start_time=t0,
                                        denial_reason=f"Access to path '{val}' is denied by user rule '{rule.name}'.",
                                        extra_metadata={"rule_priority": rule.priority},
                                    )

                # Check domain match
                if rule.target_domains:
                    for arg_key in ("url", "host"):
                        val = arguments.get(arg_key)
                        if val and isinstance(val, str):
                            val_lower = val.lower()
                            for dom in rule.target_domains:
                                if dom in val_lower:
                                    return self._make_decision(
                                        request_id=req_id,
                                        capability_id=spec.id,
                                        effect=PolicyEffect.DENY,
                                        matched_rules=[rule.rule_id],
                                        assessment=assessment,
                                        start_time=t0,
                                        denial_reason=f"Network destination '{val}' is denied by user domain rule '{rule.name}'.",
                                        extra_metadata={"rule_priority": rule.priority},
                                    )

        # -------------------------------------------------------------------
        # STAGE 2: AUTONOMY PROFILE GATING
        # -------------------------------------------------------------------
        current_rank = AUTONOMY_RANK.get(current_autonomy, 1)
        required_rank = AUTONOMY_RANK.get(spec.minimum_autonomy_profile, 1)

        # Strict floor: ADVISOR autonomy can NEVER execute mutating actions
        if current_autonomy == AutonomyProfile.ADVISOR and spec.action_class != ActionClass.READ_ONLY:
            return self._make_decision(
                request_id=req_id,
                capability_id=spec.id,
                effect=PolicyEffect.DENY,
                matched_rules=["AUTONOMY_ADVISOR_READ_ONLY_FLOOR"],
                assessment=assessment,
                start_time=t0,
                denial_reason=f"Action '{spec.name}' has action class '{spec.action_class.value}', which is prohibited under ADVISOR autonomy.",
                extra_metadata={"current_autonomy": current_autonomy.value},
            )

        # Autonomy deficit
        if current_rank < required_rank:
            if not user_confirmed:
                prompt = (
                    f"Action '{spec.name}' requires '{spec.minimum_autonomy_profile.value}' autonomy, "
                    f"exceeding current profile '{current_autonomy.value}'. Confirm execution to elevate?"
                )
                return self._make_decision(
                    request_id=req_id,
                    capability_id=spec.id,
                    effect=PolicyEffect.REQUIRE_CONFIRMATION,
                    matched_rules=["AUTONOMY_ELEVATION_REQUIRED"],
                    assessment=assessment,
                    start_time=t0,
                    confirmation_prompt=prompt,
                    extra_metadata={"current_autonomy": current_autonomy.value, "required_autonomy": spec.minimum_autonomy_profile.value},
                )

        # -------------------------------------------------------------------
        # STAGE 3: CAPABILITY CONFIRMATION POLICY GATING
        # -------------------------------------------------------------------
        if spec.confirmation_policy == ConfirmationPolicy.ALWAYS:
            if not user_confirmed:
                prompt = f"Action '{spec.name}' has mandatory confirmation policy (ALWAYS). Confirm execution?"
                return self._make_decision(
                    request_id=req_id,
                    capability_id=spec.id,
                    effect=PolicyEffect.REQUIRE_CONFIRMATION,
                    matched_rules=["CONFIRMATION_POLICY_ALWAYS"],
                    assessment=assessment,
                    start_time=t0,
                    confirmation_prompt=prompt,
                )

        elif spec.confirmation_policy == ConfirmationPolicy.POLICY_CONTROLLED:
            # Policy-controlled triggers confirmation if high-risk or destructive under lower autonomy
            # Financial and security-sensitive actions MUST require confirmation under all tiers below WORKFLOW_AUTHORIZED
            is_critical_sensitive = (
                spec.action_class in (
                    ActionClass.SECURITY_SENSITIVE,
                    ActionClass.FINANCIAL,
                )
                or any(t.startswith("financial:") for t in assessment.sensitive_targets)
            )
            is_high_risk = (
                assessment.is_destructive
                or assessment.risk_score >= 0.70
                or spec.action_class in (
                    ActionClass.LOCAL_DELETE,
                    ActionClass.EXTERNAL_DELETE,
                    ActionClass.EXTERNAL_SEND,
                )
            )
            requires_gate = False
            if is_critical_sensitive and not user_confirmed and current_rank < AUTONOMY_RANK[AutonomyProfile.WORKFLOW_AUTHORIZED]:
                requires_gate = True
            elif is_high_risk and not user_confirmed and current_rank < AUTONOMY_RANK[AutonomyProfile.TRUSTED_OPERATOR]:
                requires_gate = True

            if requires_gate:
                prompt = (
                    f"Action '{spec.name}' has potential high-risk side effects ({assessment.blast_radius}, risk={assessment.risk_score}). "
                    f"Confirm execution?"
                )
                return self._make_decision(
                    request_id=req_id,
                    capability_id=spec.id,
                    effect=PolicyEffect.REQUIRE_CONFIRMATION,
                    matched_rules=["POLICY_CONTROLLED_HIGH_RISK_GATE"],
                    assessment=assessment,
                    start_time=t0,
                    confirmation_prompt=prompt,
                )

        # -------------------------------------------------------------------
        # STAGE 4: BASELINE PERMITTED
        # -------------------------------------------------------------------
        return self._make_decision(
            request_id=req_id,
            capability_id=spec.id,
            effect=PolicyEffect.ALLOW,
            matched_rules=["BASELINE_PERMITTED"],
            assessment=assessment,
            start_time=t0,
            extra_metadata={"autonomy_profile": current_autonomy.value},
        )
