"""
Canonical System Enums
======================
Standardized enumerations defining:
- Action classifications and policy sensitivity tiers
- Autonomy profiles governing execution boundaries
- Deterministic error codes (including UNKNOWN_COMMIT)
- Verification outcome statuses
- System 1 decision signal types
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


class ErrorCode(str, Enum):
    """Deterministic, strongly typed error codes for routine tool failures."""
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFIRMATION_REJECTED = "CONFIRMATION_REJECTED"
    TIMEOUT = "TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    PROCESS_FAILED = "PROCESS_FAILED"
    RATE_LIMITED = "RATE_LIMITED"
    SCHEMA_VIOLATION = "SCHEMA_VIOLATION"
    UNAUTHORIZED_ACTION = "UNAUTHORIZED_ACTION"
    UNKNOWN_COMMIT = "UNKNOWN_COMMIT"          # Mutation status uncertain; manual audit required


class VerificationStatus(str, Enum):
    """Three-state outcome verification status."""
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    VERIFIED_FAILURE = "VERIFIED_FAILURE"
    UNVERIFIED = "UNVERIFIED"


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
