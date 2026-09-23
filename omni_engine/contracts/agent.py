"""
Agent Communication & Tracing Contracts
=======================================
Structures defining:
- Distributed TraceContext
- Inbound AgentRequest envelope
- Outbound structured AgentResponse envelope with physical audit receipts
- Asynchronous AgentEvent envelope
"""

from typing import Any, Dict, List, Optional
from pydantic import Field

from .base import BaseContractModel
from .capability import ExecutionReceipt, VerificationResult
from .decision import DecisionFrame


class TraceContext(BaseContractModel):
    """Context for distributed tracing and causal correlation across agent operations."""
    trace_id: str = Field(..., description="Root trace identifier")
    parent_id: Optional[str] = Field(default=None, description="Parent span or caller operation identifier")
    session_id: Optional[str] = Field(default=None, description="Persistent user conversation/session identifier")


class AgentRequest(BaseContractModel):
    """Inbound agent request envelope wrapping user prompts or trigger events."""
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
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Domain event type, e.g. 'step.started', 'verification.failed'")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured event payload"
    )
    timestamp: float = Field(..., description="Epoch timestamp event occurred")
