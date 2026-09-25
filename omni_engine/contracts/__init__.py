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
from .n8n import (
    N8nTriggerType,
    N8nCredentialReference,
    N8nNode,
    N8nWorkflowSummary,
    N8nWorkflowDetail,
    N8nWorkflowValidationResult,
    N8nExecutionReceipt,
    N8nActionResult,
)
from .developer import (
    ConvergenceStatus,
    DevTaskSpec,
    CodeVerificationReceipt,
    DevExecutionReceipt,
    DevActionResult,
)
from .quest import (
    QuestStatus,
    StepStatus,
    QuestEventEnum,
    TERMINAL_QUEST_STATES,
    TERMINAL_STEP_STATES,
    VALID_QUEST_TRANSITIONS,
    VALID_STEP_TRANSITIONS,
    QuestError,
    QuestNotFoundError,
    StepNotFoundError,
    InvalidStateTransitionError,
    OptimisticLockError,
    QuestStep,
    QuestEvent,
    Quest,
)
from .operation import (
    MutationState,
    AttemptState,
    TERMINAL_MUTATION_STATES,
    VALID_MUTATION_TRANSITIONS,
    LedgerError,
    OperationNotFoundError,
    DuplicateOperationError,
    OperationCommitUncertainError,
    MaxAttemptsExceededError,
    InvalidMutationStateTransitionError,
    OperationAttempt,
    OperationRecord,
)
from .plan import (
    PlanType,
    PlanError,
    PlanValidationError,
    PlanGenerationError,
    PlanStep,
    Plan,
)
from .validation import (
    ValidationPassName,
    ValidationPassResult,
    PlanValidationReport,
)
from .execution import (
    ExecutionError,
    UnresolvedArgumentError,
    MissingInputError,
    QuestAlreadyRunningError,
    ExecutionFirewallError,
    PolicyBlockedExecutionError,
    StepExecutionReceipt,
    QuestExecutionSummary,
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
    # n8n
    "N8nTriggerType",
    "N8nCredentialReference",
    "N8nNode",
    "N8nWorkflowSummary",
    "N8nWorkflowDetail",
    "N8nWorkflowValidationResult",
    "N8nExecutionReceipt",
    "N8nActionResult",
    # Developer
    "ConvergenceStatus",
    "DevTaskSpec",
    "CodeVerificationReceipt",
    "DevExecutionReceipt",
    "DevActionResult",
    # Quest (L10)
    "QuestStatus",
    "StepStatus",
    "QuestEventEnum",
    "TERMINAL_QUEST_STATES",
    "TERMINAL_STEP_STATES",
    "VALID_QUEST_TRANSITIONS",
    "VALID_STEP_TRANSITIONS",
    "QuestError",
    "QuestNotFoundError",
    "StepNotFoundError",
    "InvalidStateTransitionError",
    "OptimisticLockError",
    "QuestStep",
    "QuestEvent",
    "Quest",
    # Operation Ledger (L11)
    "MutationState",
    "AttemptState",
    "TERMINAL_MUTATION_STATES",
    "VALID_MUTATION_TRANSITIONS",
    "LedgerError",
    "OperationNotFoundError",
    "DuplicateOperationError",
    "OperationCommitUncertainError",
    "MaxAttemptsExceededError",
    "InvalidMutationStateTransitionError",
    "OperationAttempt",
    "OperationRecord",
    # Structured DAG Planner (L12)
    "PlanType",
    "PlanError",
    "PlanValidationError",
    "PlanGenerationError",
    "PlanStep",
    "Plan",
    # Deterministic Plan Validator (L13)
    "ValidationPassName",
    "ValidationPassResult",
    "PlanValidationReport",
    # Deterministic DAG Executor (L14)
    "ExecutionError",
    "UnresolvedArgumentError",
    "MissingInputError",
    "QuestAlreadyRunningError",
    "ExecutionFirewallError",
    "PolicyBlockedExecutionError",
    "StepExecutionReceipt",
    "QuestExecutionSummary",
]



