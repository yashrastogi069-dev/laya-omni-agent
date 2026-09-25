"""Execution Contracts for LAYA Autonomous V2 Runtime.

Defines the core data contracts, execution receipts, and summary envelopes
for the Deterministic DAG Executor (Checkpoint L14).
"""

import time
from typing import Any, Dict, List, Optional

from pydantic import Field

from .base import BaseContractModel
from .capability import ToolResult
from .enums import ActionClass
from .quest import QuestStatus, StepStatus


class ExecutionError(Exception):
    """Base exception for all runtime execution errors."""
    pass


class UnresolvedArgumentError(ExecutionError):
    """Raised when a dynamic parameter expression ($inputs or $steps) cannot be resolved."""
    pass


class QuestAlreadyRunningError(ExecutionError):
    """Raised when an active lease already exists for a running quest."""
    pass


class ExecutionFirewallError(ExecutionError):
    """Raised when pre-execution plan validation fails."""
    pass


class PolicyBlockedExecutionError(ExecutionError):
    """Raised when pre-invocation policy evaluation denies execution."""
    pass


class StepExecutionReceipt(BaseContractModel):
    """Strongly typed physical receipt for an individual step execution."""
    step_id: str
    capability_id: str
    action_class: ActionClass
    status: StepStatus
    tool_result: Optional[ToolResult] = None
    is_deduplicated: bool = False
    latency_ms: float = 0.0
    started_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None


class QuestExecutionSummary(BaseContractModel):
    """Top-level summary envelope returned after a DAG execution round."""
    quest_id: str
    initial_status: QuestStatus
    final_status: QuestStatus
    total_steps: int
    completed_steps: int
    failed_steps: int
    paused_step_id: Optional[str] = None
    confirmation_prompt: Optional[str] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
