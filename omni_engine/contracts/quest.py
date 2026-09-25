"""Quest Contracts for LAYA Autonomous V2 Runtime.

Defines the core data contracts, state machines, and lifecycle transitions
for persistent multi-step Quests, Steps, and Event Streams (Checkpoint L10).
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field

from .base import BaseContractModel
from .enums import ActionClass, AutonomyProfile


class QuestStatus(str, Enum):
    """Lifecycle states for a persisted Quest."""
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED_FOR_CONFIRMATION = "paused_for_confirmation"
    PAUSED_FOR_INPUT = "paused_for_input"
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Execution states for an individual Quest step."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    AWAITING_VERIFICATION = "awaiting_verification"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class QuestEventEnum(str, Enum):
    """Event types recorded in the append-only Quest event ledger."""
    QUEST_CREATED = "quest_created"
    PLAN_ATTACHED = "plan_attached"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_PAUSED = "step_paused"
    STEP_RESUMED = "step_resumed"
    QUEST_PAUSED = "quest_paused"
    QUEST_RESUMED = "quest_resumed"
    QUEST_AWAITING_VERIFICATION = "quest_awaiting_verification"
    QUEST_COMPLETED = "quest_completed"
    QUEST_FAILED = "quest_failed"
    QUEST_CANCELLED = "quest_cancelled"


# Terminal states from which no further transitions are allowed
TERMINAL_QUEST_STATES: Set[QuestStatus] = {
    QuestStatus.COMPLETED,
    QuestStatus.FAILED,
    QuestStatus.CANCELLED,
}

TERMINAL_STEP_STATES: Set[StepStatus] = {
    StepStatus.COMPLETED,
    StepStatus.FAILED,
    StepStatus.CANCELLED,
    StepStatus.SKIPPED,
}

# Strict state transition matrix
VALID_QUEST_TRANSITIONS: Dict[QuestStatus, Set[QuestStatus]] = {
    QuestStatus.CREATED: {
        QuestStatus.PLANNED,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.PLANNED: {
        QuestStatus.RUNNING,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.RUNNING: {
        QuestStatus.PAUSED_FOR_CONFIRMATION,
        QuestStatus.PAUSED_FOR_INPUT,
        QuestStatus.AWAITING_VERIFICATION,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.PAUSED_FOR_CONFIRMATION: {
        QuestStatus.RUNNING,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.PAUSED_FOR_INPUT: {
        QuestStatus.RUNNING,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.AWAITING_VERIFICATION: {
        QuestStatus.COMPLETED,
        QuestStatus.FAILED,
        QuestStatus.CANCELLED,
    },
    QuestStatus.COMPLETED: set(),
    QuestStatus.FAILED: set(),
    QuestStatus.CANCELLED: set(),
}

VALID_STEP_TRANSITIONS: Dict[StepStatus, Set[StepStatus]] = {
    StepStatus.PENDING: {
        StepStatus.READY,
        StepStatus.RUNNING,
        StepStatus.SKIPPED,
        StepStatus.CANCELLED,
    },
    StepStatus.READY: {
        StepStatus.RUNNING,
        StepStatus.SKIPPED,
        StepStatus.CANCELLED,
    },
    StepStatus.RUNNING: {
        StepStatus.PAUSED,
        StepStatus.AWAITING_VERIFICATION,
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.CANCELLED,
    },
    StepStatus.PAUSED: {
        StepStatus.RUNNING,
        StepStatus.FAILED,
        StepStatus.CANCELLED,
    },
    StepStatus.AWAITING_VERIFICATION: {
        StepStatus.COMPLETED,
        StepStatus.FAILED,
        StepStatus.CANCELLED,
    },
    StepStatus.COMPLETED: set(),
    StepStatus.FAILED: set(),
    StepStatus.CANCELLED: set(),
    StepStatus.SKIPPED: set(),
}


# Domain-specific exceptions
class QuestError(Exception):
    """Base exception for Quest runtime operations."""
    pass


class QuestNotFoundError(QuestError):
    """Raised when a requested Quest ID does not exist."""
    pass


class StepNotFoundError(QuestError):
    """Raised when a requested Step ID does not exist in a Quest."""
    pass


class InvalidStateTransitionError(QuestError):
    """Raised when attempting an unauthorized state transition."""
    pass


class OptimisticLockError(QuestError):
    """Raised when an OCC version check fails due to concurrent modification."""
    pass


class QuestStep(BaseContractModel):
    """Strongly typed contract for an individual plan step in a Quest."""
    step_id: str
    quest_id: str
    capability_id: str
    action_class: ActionClass
    intent: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    version: int = 1
    execution_receipt: Optional[Dict[str, Any]] = None
    verification_receipt: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class QuestEvent(BaseContractModel):
    """Immutable audit event logged during Quest progression."""
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    quest_id: str
    step_id: Optional[str] = None
    event_type: QuestEventEnum
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class Quest(BaseContractModel):
    """Strongly typed top-level contract for a durable multi-step Quest."""
    quest_id: str
    title: str
    goal: str
    status: QuestStatus = QuestStatus.CREATED
    version: int = 1
    autonomy_profile: AutonomyProfile = AutonomyProfile.LOCAL_OPERATOR
    current_step_id: Optional[str] = None
    steps: List[QuestStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
