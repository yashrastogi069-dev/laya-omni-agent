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

__all__ = [
    # Base
    "BaseContractModel",
    # Enums
    "ActionClass",
    "AutonomyProfile",
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
]
