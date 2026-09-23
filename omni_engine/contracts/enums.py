"""
Canonical System Enums
======================
Standardized enumerations defining:
- Action classifications and policy sensitivity tiers
- Autonomy profiles governing execution boundaries
- Deterministic error codes (including explicit UNKNOWN_COMMIT and differentiation
  between PERMISSION_DENIED and UNAUTHORIZED_ACTION)
- Capability policy semantics (ConfirmationPolicy, RetryPolicy, IdempotencyClass)
- Tool execution outcome classifications (ToolOutcome: SUCCESS, PARTIAL, FAILURE)
- Three-state physical verification outcome statuses
- First-class System 1 decision signal types
"""

from enum import Enum


class ActionClass(str, Enum):
    """Classification of tool action safety and blast radius."""
    READ_ONLY = "READ_ONLY"
    LOCAL_CREATE = "LOCAL_CREATE"
    LOCAL_UPDATE = "LOCAL_UPDATE"
    LOCAL_DELETE = "LOCAL_DELETE"
    EXTERNAL_CREATE = "EXTERNAL_CREATE"
    EXTERNAL_UPDATE = "EXTERNAL_UPDATE"
    EXTERNAL_SEND = "EXTERNAL_SEND"
    EXTERNAL_DELETE = "EXTERNAL_DELETE"
    SYSTEM_ACTION = "SYSTEM_ACTION"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    FINANCIAL = "FINANCIAL"


class AutonomyProfile(str, Enum):
    """Autonomy tier governing required approvals and execution bounds."""
    ADVISOR = "ADVISOR"                        # Read-only observation, plans only
    SAFE_ASSISTANT = "SAFE_ASSISTANT"          # Local reads + harmless updates, confirms deletes/sends
    LOCAL_OPERATOR = "LOCAL_OPERATOR"          # Full local automation, confirms external deletes/sends
    TRUSTED_OPERATOR = "TRUSTED_OPERATOR"      # Unattended local and external execution
    WORKFLOW_AUTHORIZED = "WORKFLOW_AUTHORIZED"# Pre-authorized deterministic DAG execution


class ConfirmationPolicy(str, Enum):
    """Policy governing whether tool execution requires interactive human confirmation."""
    NEVER = "NEVER"
    POLICY_CONTROLLED = "POLICY_CONTROLLED"
    ALWAYS = "ALWAYS"


class RetryPolicy(str, Enum):
    """Policy governing automatic retry behavior upon transient execution failure."""
    NEVER = "NEVER"
    SAFE_READ_RETRY = "SAFE_READ_RETRY"
    SAFE_WITH_IDEMPOTENCY = "SAFE_WITH_IDEMPOTENCY"
    VERIFY_BEFORE_RETRY = "VERIFY_BEFORE_RETRY"


class IdempotencyClass(str, Enum):
    """Idempotency classification determining safe re-execution semantics."""
    READ_ONLY = "READ_ONLY"                    # Re-execution has zero external side effects
    NATURAL = "NATURAL"                        # Naturally idempotent (e.g. file overwrite with exact content)
    LEDGER_REQUIRED = "LEDGER_REQUIRED"        # Requires operation ledger dedup to prevent duplicate side effects
    REMOTE_IDEMPOTENCY_KEY = "REMOTE_IDEMPOTENCY_KEY" # Supports upstream API idempotency tokens
    NON_IDEMPOTENT = "NON_IDEMPOTENT"          # Strictly non-idempotent (e.g. append, financial transfer)


class ToolOutcome(str, Enum):
    """Outcome classification of a capability execution."""
    SUCCESS = "SUCCESS"                        # Execution completed fully and successfully
    PARTIAL = "PARTIAL"                        # Execution completed partially (e.g. 7/10 sources, partial batch)
    FAILURE = "FAILURE"                        # Execution failed completely


class VerificationStatus(str, Enum):
    """Three-state physical outcome verification status."""
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILURE = "VERIFIED_FAILURE"
    UNVERIFIED = "UNVERIFIED"


class ErrorCode(str, Enum):
    """Deterministic, strongly typed error codes for routine tool and execution failures.
    
    Semantic Invariants:
    - PERMISSION_DENIED: Underlying OS, filesystem, external service, or API rejected an otherwise valid action.
    - UNAUTHORIZED_ACTION: LAYA internal policy or autonomy profile rules refused the action.
    - UNKNOWN_COMMIT: Mutation status uncertain (e.g. timeout during HTTP POST). Manual audit required; NEVER blind retry.
    """
    # Validation & Schema
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"

    # Configuration & Auth
    UNCONFIGURED = "UNCONFIGURED"
    AUTH_REQUIRED = "AUTH_REQUIRED"

    # Policy & Permissions
    PERMISSION_DENIED = "PERMISSION_DENIED"        # OS/service/API rejected valid action
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"    # LAYA policy/autonomy refused action
    CONFIRMATION_REJECTED = "CONFIRMATION_REJECTED"# User declined confirmation

    # Resource State
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"

    # Transient & Network
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Process & Execution
    PROCESS_FAILED = "PROCESS_FAILED"
    CANCELLED = "CANCELLED"

    # Critical & Internal
    UNKNOWN_COMMIT = "UNKNOWN_COMMIT"              # Side-effect uncertain; manual audit required
    INTERNAL_ERROR = "INTERNAL_ERROR"              # Engine invariant breach or unhandled bug


class DecisionSignalType(str, Enum):
    """First-class signals produced by the System 1 nervous system."""
    INTENT = "INTENT"
    TASK_CLASS = "TASK_CLASS"
    DOMAIN = "DOMAIN"
    SKILL = "SKILL"
    URGENCY = "URGENCY"
    IMPORTANCE = "IMPORTANCE"
    RISK = "RISK"
    REVERSIBILITY = "REVERSIBILITY"
    AMBIGUITY = "AMBIGUITY"
    NEEDS_PLAN = "NEEDS_PLAN"
    NEEDS_TOOLS = "NEEDS_TOOLS"
    MODEL_TIER = "MODEL_TIER"
    # L2.1 Extended Decision Signals
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"    # Explicit: ask user question before acting (distinct from ambiguity)
    REQUIRES_ACTION = "REQUIRES_ACTION"            # Whether execution is required vs conversational reply
    NEEDS_GENERATIVE_REASONING = "NEEDS_GENERATIVE_REASONING" # Whether S2 generative LLM is genuinely required
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"    # Whether problem must escalate to human or advanced tier
