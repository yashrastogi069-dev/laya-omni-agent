"""
omni_engine.contracts.router
============================
Contracts for Role-Aware Generative Provider Router, Model Tiers, and User Sovereignty.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): User model sovereignty and fallback cascades
  are strictly enforced by deterministic policy, not prompt hints.
- System 1 vs Generative Boundary (Invariant 2 & 3): Generative calls are scoped
  to explicit roles: ARGUMENT_WRITER, PLANNER, REPLANNER, FINALIZER, CODING.
- Strongly Typed Contracts (Invariant 4): All models strictly enforce extra="forbid"
  and validation upon assignment.
"""

from enum import Enum
import time
from typing import Any, Dict, List, Optional
from pydantic import Field

from omni_engine.contracts.base import BaseContractModel


class AgentRole(str, Enum):
    """Specific functional roles for generative model invocation."""
    ARGUMENT_WRITER = "argument_writer"
    PLANNER = "planner"
    REPLANNER = "replanner"
    FINALIZER = "finalizer"
    CODING = "coding"


class ModelTier(str, Enum):
    """Calibrated capability and latency tiers for generative models."""
    FAST = "fast"          # <1s latency, schema conformance, parameter extraction
    BALANCED = "balanced"  # Workhorse reasoning, replanning, research synthesis
    CAPABLE = "capable"    # Frontier intelligence, complex DAG planning, coding


class ModelSovereigntyLevel(str, Enum):
    """Operator sovereignty over generative model selection."""
    USER_LOCKED = "user_locked"        # Strictly no fallback; fails if pinned model is unavailable
    USER_PREFERRED = "user_preferred"  # User prefers model; fallback allowed with explicit telemetry
    AUTO = "auto"                      # Router dynamically selects and cascades based on role tier


class RoleRouteConfig(BaseContractModel):
    """Configuration governing model routing, token bounds, and fallbacks for a role."""
    schema_version: str = Field(default="1.0.0", description="Contract schema version")
    role: AgentRole = Field(..., description="Target agent role")
    primary_model: str = Field(..., description="Canonical primary model identifier (e.g. 'anthropic/claude-3.5-sonnet')")
    tier: ModelTier = Field(default=ModelTier.BALANCED, description="Performance/latency tier")
    fallback_models: List[str] = Field(default_factory=list, description="Ordered list of fallback models")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=2000, gt=0, description="Maximum token generation budget")
    timeout_seconds: float = Field(default=60.0, gt=0.0, description="Per-invocation timeout deadline in seconds")
    sovereignty: ModelSovereigntyLevel = Field(default=ModelSovereigntyLevel.AUTO, description="Sovereignty level")
    pinned_provider_id: Optional[str] = Field(default=None, description="Explicitly pinned provider identifier")
    pinned_model_id: Optional[str] = Field(default=None, description="Explicitly pinned model identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary role routing metadata")


class RouterTelemetry(BaseContractModel):
    """Comprehensive telemetry record emitted by GenerativeRouter upon execution."""
    schema_version: str = Field(default="1.0.0", description="Contract schema version")
    role: AgentRole = Field(..., description="Agent role for which generation was requested")
    requested_model: str = Field(..., description="Initially requested / primary model identifier")
    selected_provider_id: str = Field(..., description="Provider that successfully serviced the request")
    selected_model_id: str = Field(..., description="Model that successfully serviced the request")
    attempts: int = Field(default=1, ge=1, description="Number of candidate attempts made")
    was_fallback: bool = Field(default=False, description="Whether fallback was required")
    fallback_reason: Optional[str] = Field(default=None, description="Diagnostic explanation for fallback if occurred")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Total execution latency in milliseconds")
    prompt_tokens: Optional[int] = Field(default=None, description="Input token count if reported")
    completion_tokens: Optional[int] = Field(default=None, description="Generated token count if reported")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp of generation")


# Default calibrated configurations across the 5 agent roles
DEFAULT_ROLE_CONFIGS: Dict[AgentRole, RoleRouteConfig] = {
    AgentRole.ARGUMENT_WRITER: RoleRouteConfig(
        role=AgentRole.ARGUMENT_WRITER,
        primary_model="openai/gpt-4o-mini",
        tier=ModelTier.FAST,
        fallback_models=["anthropic/claude-3.5-haiku", "meta-llama/llama-3.3-70b-instruct"],
        temperature=0.1,
        max_tokens=1000,
        timeout_seconds=30.0,
        sovereignty=ModelSovereigntyLevel.AUTO,
    ),
    AgentRole.PLANNER: RoleRouteConfig(
        role=AgentRole.PLANNER,
        primary_model="anthropic/claude-3.5-sonnet",
        tier=ModelTier.CAPABLE,
        fallback_models=["openai/gpt-4o", "meta-llama/llama-3.3-70b-instruct"],
        temperature=0.2,
        max_tokens=3000,
        timeout_seconds=60.0,
        sovereignty=ModelSovereigntyLevel.AUTO,
    ),
    AgentRole.REPLANNER: RoleRouteConfig(
        role=AgentRole.REPLANNER,
        primary_model="anthropic/claude-3.5-sonnet",
        tier=ModelTier.BALANCED,
        fallback_models=["openai/gpt-4o", "meta-llama/llama-3.3-70b-instruct"],
        temperature=0.2,
        max_tokens=2000,
        timeout_seconds=45.0,
        sovereignty=ModelSovereigntyLevel.AUTO,
    ),
    AgentRole.FINALIZER: RoleRouteConfig(
        role=AgentRole.FINALIZER,
        primary_model="anthropic/claude-3.5-sonnet",
        tier=ModelTier.BALANCED,
        fallback_models=["openai/gpt-4o", "meta-llama/llama-3.3-70b-instruct"],
        temperature=0.4,
        max_tokens=4000,
        timeout_seconds=60.0,
        sovereignty=ModelSovereigntyLevel.AUTO,
    ),
    AgentRole.CODING: RoleRouteConfig(
        role=AgentRole.CODING,
        primary_model="anthropic/claude-3.5-sonnet",
        tier=ModelTier.CAPABLE,
        fallback_models=["deepseek/deepseek-chat", "openai/gpt-4o"],
        temperature=0.1,
        max_tokens=3000,
        timeout_seconds=60.0,
        sovereignty=ModelSovereigntyLevel.AUTO,
    ),
}
