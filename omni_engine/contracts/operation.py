"""Operation Ledger Contracts for LAYA Autonomous V2 Runtime.

Defines the core data contracts, mutation states, attempt lifecycles,
and idempotency structures for Exactly-Once Mutation Semantics (Checkpoint L11).
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field

from .base import BaseContractModel


class MutationState(str, Enum):
    """Lifecycle states for a mutation operation in the Operation Ledger."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMMITTED = "committed"
    FAILED = "failed"
    UNKNOWN_COMMIT = "unknown_commit"


class AttemptState(str, Enum):
    """Execution states for an individual attempt of an operation."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    UNCERTAIN = "uncertain"


# Terminal mutation states from which normal execution cannot proceed
TERMINAL_MUTATION_STATES: Set[MutationState] = {
    MutationState.COMMITTED,
}

# Strict mutation transition matrix
VALID_MUTATION_TRANSITIONS: Dict[MutationState, Set[MutationState]] = {
    MutationState.PENDING: {
        MutationState.IN_PROGRESS,
        MutationState.FAILED,
    },
    MutationState.IN_PROGRESS: {
        MutationState.COMMITTED,
        MutationState.FAILED,
        MutationState.UNKNOWN_COMMIT,
    },
    MutationState.FAILED: {
        MutationState.IN_PROGRESS,  # Retry allowed if attempts remain
        MutationState.FAILED,
    },
    MutationState.UNKNOWN_COMMIT: {
        MutationState.COMMITTED,    # Reconciled as committed via physical evidence
        MutationState.FAILED,       # Reconciled as uncommitted, allowing clean retry
    },
    MutationState.COMMITTED: set(), # Absorbing terminal state: strictly exactly-once!
}


# Domain-specific exceptions
class LedgerError(Exception):
    """Base exception for Operation Ledger operations."""
    pass


class OperationNotFoundError(LedgerError):
    """Raised when an operation ID is not found in the ledger."""
    pass


class DuplicateOperationError(LedgerError):
    """Raised when registering an operation whose idempotency key conflicts in an active state."""
    pass


class OperationCommitUncertainError(LedgerError):
    """Raised when attempting a blind retry on an operation in UNKNOWN_COMMIT state.
    
    Prime Directive & Invariant 1: Blind retries on UNKNOWN_COMMIT are strictly forbidden.
    Reconciliation against physical evidence is mandatory.
    """
    pass


class MaxAttemptsExceededError(LedgerError):
    """Raised when maximum attempt count has been reached for an operation."""
    pass


class InvalidMutationStateTransitionError(LedgerError):
    """Raised when an illegal mutation state transition is attempted."""
    pass


class OperationAttempt(BaseContractModel):
    """Strongly typed contract for an individual execution attempt of a mutation."""
    attempt_id: str = Field(default_factory=lambda: f"att_{uuid.uuid4().hex[:12]}")
    operation_id: str
    attempt_number: int
    state: AttemptState = AttemptState.STARTED
    started_at: float = Field(default_factory=time.time)
    finished_at: Optional[float] = None
    execution_receipt: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class OperationRecord(BaseContractModel):
    """Strongly typed top-level contract for a persisted mutation in the Operation Ledger."""
    operation_id: str
    quest_id: str
    step_id: str
    capability_id: str
    idempotency_key: str
    argument_hash: str
    state: MutationState = MutationState.PENDING
    current_attempt: int = 0
    max_attempts: int = 3
    execution_receipt: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempts: List[OperationAttempt] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
