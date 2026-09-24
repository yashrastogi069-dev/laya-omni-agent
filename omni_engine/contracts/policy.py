"""
omni_engine.contracts.policy
============================
Strongly typed contracts for deterministic policy decisions, rule specifications,
action risk assessments, and execution boundaries.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Models must NEVER independently decide permissions or policy.
- Invariant 4: Strongly Typed Contracts — All policy structures inherit BaseContractModel (extra='forbid').
- Invariant 7: Signals are First-Class — Risk, reversibility, and blast-radius are explicitly tracked.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, model_validator

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import ActionClass, AutonomyProfile


class PolicyEffect(str, Enum):
    """Effect outcome of a policy rule or decision."""
    ALLOW = "ALLOW"
    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    DENY = "DENY"
    QUARANTINE = "QUARANTINE"


class ActionAssessment(BaseContractModel):
    """Detailed deterministic risk assessment of a proposed capability invocation."""
    capability_id: str = Field(..., description="Target capability identifier")
    action_class: ActionClass = Field(..., description="Action safety classification")
    autonomy_required: AutonomyProfile = Field(..., description="Minimum autonomy tier required")
    is_destructive: bool = Field(default=False, description="Whether action overwrites, deletes, or terminates state")
    is_reversible: bool = Field(default=False, description="Whether action can be programmatically undone")
    sensitive_targets: List[str] = Field(default_factory=list, description="Target paths, domains, or processes detected as sensitive")
    blast_radius: str = Field(default="NONE", description="Categorical blast radius (NONE, LOCAL_FILE, LOCAL_WORKSPACE, LOCAL_SYSTEM, EXTERNAL_NETWORK, SECURITY_CRITICAL)")
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Normalized deterministic risk score")


class PolicyRule(BaseContractModel):
    """Declarative persistent policy rule contract."""
    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(default="", description="Rule purpose and behavior")
    effect: PolicyEffect = Field(..., description="Target effect if rule conditions match")
    action_classes: List[ActionClass] = Field(default_factory=list, description="Target action classes filtered by this rule")
    forbidden_patterns: List[str] = Field(default_factory=list, description="Regex patterns matched against command/script/query arguments")
    target_paths: List[str] = Field(default_factory=list, description="Target filesystem path prefixes or glob patterns")
    target_domains: List[str] = Field(default_factory=list, description="Target network domain names or hosts")
    priority: int = Field(default=100, description="Evaluation priority (lower numbers evaluate earlier)")
    is_active: bool = Field(default=True, description="Whether this rule is actively enforced")


class PolicyDecision(BaseContractModel):
    """Final deterministic policy envelope authorizing or gating capability execution."""
    schema_version: str = Field(default="1.0.0", description="Policy decision contract version")
    request_id: str = Field(..., description="Correlation request ID")
    capability_id: str = Field(..., description="Target capability ID")
    allowed: bool = Field(..., description="Whether capability execution is unconditionally permitted")
    effect: PolicyEffect = Field(..., description="Terminal policy effect")
    matched_rules: List[str] = Field(default_factory=list, description="Rule IDs that matched the proposed action")
    confirmation_prompt: Optional[str] = Field(default=None, description="Interactive confirmation prompt if confirmation is required")
    denial_reason: Optional[str] = Field(default=None, description="Clear explanatory rationale if invocation was denied or quarantined")
    assessment: ActionAssessment = Field(..., description="Deterministic risk assessment of the invocation")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Policy evaluation duration in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry and policy mode")

    @model_validator(mode="after")
    def validate_policy_consistency(self) -> "PolicyDecision":
        """Ensures logical consistency between allowed, effect, and explanatory fields."""
        if self.allowed and self.effect != PolicyEffect.ALLOW:
            raise ValueError(f"Inconsistent PolicyDecision: allowed=True but effect={self.effect.value}")

        if not self.allowed and self.effect == PolicyEffect.ALLOW:
            raise ValueError("Inconsistent PolicyDecision: allowed=False but effect=ALLOW")

        if self.effect in (PolicyEffect.DENY, PolicyEffect.QUARANTINE):
            if not self.denial_reason or not self.denial_reason.strip():
                raise ValueError(f"PolicyDecision with effect={self.effect.value} requires a non-empty denial_reason")

        if self.effect == PolicyEffect.REQUIRE_CONFIRMATION:
            if not self.confirmation_prompt or not self.confirmation_prompt.strip():
                raise ValueError("PolicyDecision with effect=REQUIRE_CONFIRMATION requires a non-empty confirmation_prompt")

        return self
