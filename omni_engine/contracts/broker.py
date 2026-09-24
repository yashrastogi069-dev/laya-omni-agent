"""
omni_engine.contracts.broker
============================
Contracts for SystemOneBroker, User Model Sovereignty, Provider Policies,
and Empirical Calibration telemetry.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): User policy and provider allowlists are
  strictly binding deterministic rules, never bypassed by model heuristics.
- Signals are First-Class (Invariant 7): Fallback reasons, queue latencies, and
  confidence metrics are explicit, strongly typed signals.
- User Model Sovereignty: USER_LOCKED prohibits silent fallback; USER_PREFERRED
  records mandatory explanatory telemetry; AUTO optimizes within allowlist.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator
from omni_engine.contracts.base import BaseContractModel


class ProviderSelectionMode(str, Enum):
    """User authority mode over System 1 model and provider selection."""
    USER_LOCKED = "user_locked"
    USER_PREFERRED = "user_preferred"
    AUTO = "auto"


class BrokerRoutingOutcome(str, Enum):
    """Execution pathway selected by SystemOneBroker."""
    DETERMINISTIC_NO_MODEL = "deterministic_no_model"
    LAYA_ENGLISH = "laya_english"
    LAYA_TYPED_DECISIONS = "laya_typed_decisions"
    JEV = "jev"
    DUAL_CHECK = "dual_check"
    GENERATIVE_ESCALATION = "generative_escalation"


class FallbackReason(str, Enum):
    """Explicit typed reason for an automatic provider substitution."""
    NONE = "none"
    PROVIDER_UNHEALTHY = "provider_unhealthy"
    PROVIDER_UNCONFIGURED = "provider_unconfigured"
    RAM_PRESSURE = "ram_pressure"
    QUEUE_TIMEOUT = "queue_timeout"
    PRIVACY_RESTRICTION = "privacy_restriction"
    QUALITY_FLOOR_BREACH = "quality_floor_breach"
    CONTEXT_LIMIT_EXCEEDED = "context_limit_exceeded"
    TASK_OVERRIDE = "task_override"


class TaskProviderOverride(BaseContractModel):
    """Task-level provider preference and scoping overrides."""
    target_provider: Optional[str] = Field(default=None, description="Requested provider for this task")
    scope: Optional[str] = Field(default=None, description="Scope of override: e.g. 'routing', 'browser', 'all'")
    privacy_local_only: bool = Field(default=False, description="Strict local-only constraint prohibiting remote providers")
    latency_priority: bool = Field(default=False, description="Whether low latency takes precedence over highest quality")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual metadata")


class ProviderPolicyConfig(BaseContractModel):
    """Persistent user provider policy and operational constraints."""
    mode: ProviderSelectionMode = Field(
        default=ProviderSelectionMode.USER_PREFERRED,
        description="Active provider selection mode (USER_LOCKED, USER_PREFERRED, AUTO)",
    )
    allowed_providers: List[str] = Field(
        default_factory=lambda: ["laya_english", "laya_typed_decisions"],
        description="Explicit user allowlist of approved System 1 providers",
    )
    preferred_provider: str = Field(
        default="laya_english",
        description="Default provider when mode is USER_PREFERRED or USER_LOCKED",
    )
    max_local_concurrency: int = Field(
        default=1,
        ge=1,
        le=8,
        description="Maximum concurrent forward passes for local LAYA engine (default 1 for 4-core CPU)",
    )
    ram_headroom_mb: float = Field(
        default=500.0,
        ge=100.0,
        description="Minimum system free RAM required before considering model eviction",
    )
    quality_floor: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum acceptable macro-accuracy / calibration floor for AUTO mode",
    )
    queue_timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        description="Maximum seconds a request will wait in the inference queue before timeout",
    )

    @field_validator("allowed_providers")
    @classmethod
    def validate_allowed_providers_non_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("allowed_providers list cannot be empty")
        return [p.strip().lower() for p in v]


class BrokerDecision(BaseContractModel):
    """Output envelope produced by SystemOneBroker describing provider resolution."""
    selected_provider: str = Field(..., description="The provider chosen for execution")
    target_provider: str = Field(..., description="The provider initially requested or preferred")
    outcome: BrokerRoutingOutcome = Field(..., description="Categorical routing outcome")
    selection_mode: ProviderSelectionMode = Field(..., description="Active user selection mode")
    fallback_occurred: bool = Field(default=False, description="True if selected_provider != target_provider")
    fallback_reason: FallbackReason = Field(default=FallbackReason.NONE, description="Explicit reason if fallback occurred")
    fallback_details: Optional[str] = Field(default=None, description="Contextual explanation for fallback")
    broker_latency_ms: float = Field(default=0.0, ge=0.0, description="Routing decision overhead in milliseconds")
    queue_wait_ms: float = Field(default=0.0, ge=0.0, description="Milliseconds spent waiting for inference semaphore")
    cold_start: bool = False
    is_local: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CalibrationMetrics(BaseContractModel):
    """Empirical calibration and task evaluation metrics on held-out test splits."""
    signal_name: str = Field(..., description="Name of the evaluated decision signal (e.g. 'domain', 'intent')")
    provider_id: str = Field(..., description="Evaluated provider identifier")
    sample_count: int = Field(..., ge=0, description="Number of evaluated samples")
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Raw categorical accuracy")
    precision: float = Field(..., ge=0.0, le=1.0, description="Macro precision")
    recall: float = Field(..., ge=0.0, le=1.0, description="Macro recall")
    f1: float = Field(..., ge=0.0, le=1.0, description="Macro F1 score")
    ece: float = Field(..., ge=0.0, le=1.0, description="Expected Calibration Error across 10 bins")
    is_calibrated: bool = Field(..., description="True if sample_count >= 30, ECE <= 0.15, and F1 >= 0.70")
    details: Dict[str, Any] = Field(default_factory=dict)
