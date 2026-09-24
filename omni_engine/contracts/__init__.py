"""
LAYA Canonical Contracts Package
================================
Strongly typed, validated data structures and boundary contracts for the
standalone LAYA autonomous agent.
"""

from .base import BaseContractModel
from .enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
    ToolOutcome,
    VerificationStatus,
    DecisionSignalType,
    AUTONOMY_RANK,
)
from .decision import (
    DecisionSignal,
    DecisionFrame,
)
from .capability import (
    CapabilitySpec,
    CapabilityInvocation,
    ExecutableCapability,
    ToolError,
    ExecutionReceipt,
    VerificationResult,
    ToolResult,
)
from .agent import (
    TraceContext,
    AgentRequest,
    AgentResponse,
    AgentEvent,
)
from .routing import (
    CapabilityCandidate,
    RouteDecision,
)
from .skill import (
    SkillStepTemplate,
    SkillManifest,
)
from .calibration import (
    CalibratedModelThresholds,
    DeterministicPolicyThresholds,
    CalibrationConfig,
)
from .arguments import (
    ArgumentExtractionSource,
    ArgumentSlot,
    ArgumentResolutionEnvelope,
)
from .policy import (
    PolicyEffect,
    ActionAssessment,
    PolicyRule,
    PolicyDecision,
)
from .broker import (
    ProviderSelectionMode,
    BrokerRoutingOutcome,
    FallbackReason,
    TaskProviderOverride,
    ProviderPolicyConfig,
    BrokerDecision,
    CalibrationMetrics,
)
from .research import (
    EvidenceStance,
    ClaimVerificationStatus,
    FetchMethod,
    EvidenceItem,
    ResearchClaim,
    ResearchBudget,
    ResearchTelemetry,
    ResearchDossier,
)
from .browser import (
    BrowserActionType,
    BrowserElement,
    BrowserSnapshot,
    BrowserActionRequest,
    BrowserActionResult,
)
from .desktop import (
    WindowBounds,
    WindowState,
    AppWindowInfo,
    AppLaunchResult,
    ServiceHealthStatus,
    DesktopActionResult,
)

__all__ = [
    # Base
    "BaseContractModel",
    # Enums
    "ActionClass",
    "AutonomyProfile",
    "AUTONOMY_RANK",
    "ConfirmationPolicy",
    "ErrorCode",
    "IdempotencyClass",
    "RetryPolicy",
    "ToolOutcome",
    "VerificationStatus",
    "DecisionSignalType",
    # Decision
    "DecisionSignal",
    "DecisionFrame",
    # Capability
    "CapabilitySpec",
    "CapabilityInvocation",
    "ExecutableCapability",
    "ToolError",
    "ExecutionReceipt",
    "VerificationResult",
    "ToolResult",
    # Agent
    "TraceContext",
    "AgentRequest",
    "AgentResponse",
    "AgentEvent",
    # Routing
    "CapabilityCandidate",
    "RouteDecision",
    # Skill
    "SkillStepTemplate",
    "SkillManifest",
    # Calibration
    "CalibratedModelThresholds",
    "DeterministicPolicyThresholds",
    "CalibrationConfig",
    # Arguments
    "ArgumentExtractionSource",
    "ArgumentSlot",
    "ArgumentResolutionEnvelope",
    # Policy
    "PolicyEffect",
    "ActionAssessment",
    "PolicyRule",
    "PolicyDecision",
    # Broker
    "ProviderSelectionMode",
    "BrokerRoutingOutcome",
    "FallbackReason",
    "TaskProviderOverride",
    "ProviderPolicyConfig",
    "BrokerDecision",
    "CalibrationMetrics",
    # Research
    "EvidenceStance",
    "ClaimVerificationStatus",
    "FetchMethod",
    "EvidenceItem",
    "ResearchClaim",
    "ResearchBudget",
    "ResearchTelemetry",
    "ResearchDossier",
    # Browser
    "BrowserActionType",
    "BrowserElement",
    "BrowserSnapshot",
    "BrowserActionRequest",
    "BrowserActionResult",
    # Desktop
    "WindowBounds",
    "WindowState",
    "AppWindowInfo",
    "AppLaunchResult",
    "ServiceHealthStatus",
    "DesktopActionResult",
]

