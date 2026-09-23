"""
Agent Communication & Tracing Contracts
=======================================
Structures defining:
- Distributed TraceContext with multi-tier causal correlation fields
  (trace_id, parent_id, session_id, turn_id, quest_id, plan_id, step_id, operation_id)
- Inbound AgentRequest envelope with explicit contract schema versioning
- Outbound structured AgentResponse envelope with physical audit receipts
- Asynchronous AgentEvent envelope
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import BaseContractModel
from .capability import ExecutionReceipt, VerificationResult
from .decision import DecisionFrame
from .trace import TraceContext


class AgentRequest(BaseContractModel):
    """Inbound agent request envelope wrapping user prompts or trigger events."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for AgentRequest"
    )
    request_id: str = Field(..., description="Unique request identifier")
    user_prompt: str = Field(..., description="Raw or preprocessed user prompt or trigger instruction")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental runtime context (workspace paths, active variables, environment)"
    )
    trace_context: Optional[TraceContext] = Field(
        default=None,
        description="Optional distributed tracing context"
    )
    created_at: float = Field(..., description="Epoch timestamp request was submitted")


class AgentResponse(BaseContractModel):
    """Outbound structured agent response envelope containing execution receipts and verification."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for AgentResponse"
    )
    request_id: str = Field(..., description="Correlation request identifier matching AgentRequest")
    content: str = Field(..., description="Synthesized response or completion summary for the user")
    decision_frame: Optional[DecisionFrame] = Field(
        default=None,
        description="System 1 decision frame that guided this response"
    )
    executed_tools: List[str] = Field(
        default_factory=list,
        description="List of capability IDs invoked during resolution"
    )
    receipts: List[ExecutionReceipt] = Field(
        default_factory=list,
        description="Physical execution receipts for all executed operations"
    )
    verifications: List[VerificationResult] = Field(
        default_factory=list,
        description="Physical outcome verification results"
    )
    total_duration_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total duration from request arrival to response completion"
    )
    completed_at: float = Field(..., description="Epoch timestamp response was completed")


class AgentEvent(BaseContractModel):
    """Event envelope for internal agent event bus, telemetry, and background notifications."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for AgentEvent"
    )
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Domain event type, e.g. 'step.started', 'verification.failed'")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured event payload"
    )
    timestamp: float = Field(..., description="Epoch timestamp event occurred")
