"""
Distributed Tracing & Correlation Contract
==========================================
Defines TraceContext with multi-tier causal correlation fields:
- trace_id, parent_id, session_id, turn_id, quest_id, plan_id, step_id, operation_id
"""

from typing import Optional
from pydantic import Field
from .base import BaseContractModel


class TraceContext(BaseContractModel):
    """Context for distributed tracing and causal correlation across agent operations."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for TraceContext"
    )
    trace_id: str = Field(..., description="Root trace identifier")
    parent_id: Optional[str] = Field(default=None, description="Parent span or caller operation identifier")
    session_id: Optional[str] = Field(default=None, description="Persistent user conversation/session identifier")
    turn_id: Optional[str] = Field(default=None, description="Current conversational turn identifier")
    quest_id: Optional[str] = Field(default=None, description="Persistent Quest identifier")
    plan_id: Optional[str] = Field(default=None, description="Validated DAG plan identifier")
    step_id: Optional[str] = Field(default=None, description="Plan step identifier")
    operation_id: Optional[str] = Field(default=None, description="Logical mutation / step operation identifier")
