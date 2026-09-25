"""Operation Ledger & Exactly-Once Mutation Semantics Engine.

Enforces deterministic mutation lifecycles, external idempotency hashing,
attempt bounding, and strict blocking of blind retries on UNKNOWN_COMMIT (Checkpoint L11).
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..contracts.enums import ErrorCode
from ..contracts.operation import (
    AttemptState,
    DuplicateOperationError,
    InvalidMutationStateTransitionError,
    LedgerError,
    MaxAttemptsExceededError,
    MutationState,
    OperationAttempt,
    OperationCommitUncertainError,
    OperationNotFoundError,
    OperationRecord,
    TERMINAL_MUTATION_STATES,
    VALID_MUTATION_TRANSITIONS,
)
from .store import OperationStore


class OperationLedger:
    """Manages the lifecycle, idempotency keying, and execution attempts of mutations.
    
    Invariants:
    1. Deterministic Control: Mutations are persisted with explicit state transitions.
    2. Exactly-Once Semantics: An operation whose idempotency key matches an already COMMITTED
       record immediately returns the cached physical receipt without re-execution.
    3. UNKNOWN_COMMIT Defense: Blind retries are strictly prohibited when an operation is in
       UNKNOWN_COMMIT state. Manual or programmatic evidence-based reconciliation is required.
    4. Bounded Attempts: No operation can exceed its max_attempts limit.
    """

    def __init__(
        self,
        store: Optional[OperationStore] = None,
        db_path: Union[str, Path] = ":memory:",
    ):
        """Initialize the Operation Ledger.
        
        Args:
            store: Pre-configured OperationStore instance, or None to instantiate.
            db_path: Database path if store is None.
        """
        self.store = store if store is not None else OperationStore(db_path)

    # =========================================================================
    # Idempotency & Hashing Utilities
    # =========================================================================

    @staticmethod
    def compute_argument_hash(arguments: Dict[str, Any]) -> str:
        """Computes a deterministic SHA-256 fingerprint from canonical JSON arguments."""
        canonical_str = json.dumps(arguments, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    def compute_idempotency_key(
        self,
        capability_id: str,
        arguments: Dict[str, Any],
        custom_key: Optional[str] = None,
        quest_id: Optional[str] = None,
    ) -> str:
        """Derives a deterministic external idempotency key for capability invocation.
        
        If custom_key is provided, it is used verbatim (allowing explicit cross-quest deduplication).
        Otherwise, the key is strictly scoped by quest_id to prevent unintended cross-quest collisions.
        """
        if custom_key:
            return custom_key
        arg_hash = self.compute_argument_hash(arguments)
        if quest_id:
            return f"idem_{quest_id}_{capability_id}_{arg_hash[:16]}"
        return f"idem_{capability_id}_{arg_hash[:16]}"

    # =========================================================================
    # Operation Lifecycle
    # =========================================================================

    def register_mutation(
        self,
        quest_id: str,
        step_id: str,
        capability_id: str,
        arguments: Dict[str, Any],
        max_attempts: int = 3,
        custom_idempotency_key: Optional[str] = None,
        operation_id: Optional[str] = None,
        idempotency_class: Optional[Any] = None,
        **kwargs: Any,
    ) -> Tuple[OperationRecord, bool]:
        """Registers a mutation operation in the ledger before execution.
        
        Args:
            quest_id: Parent Quest ID.
            step_id: Parent Step ID.
            capability_id: Target capability.
            arguments: Resolved arguments dictionary.
            max_attempts: Maximum allowed execution attempts (default 3).
            custom_idempotency_key: Optional custom idempotency key.
            
        Returns:
            Tuple of (OperationRecord, is_deduplicated: bool).
            If is_deduplicated is True, the operation was already COMMITTED and
            execution must NOT be repeated; the caller should return the cached receipt.
            
        Raises:
            OperationCommitUncertainError: If an existing operation is in UNKNOWN_COMMIT state.
            LedgerError: If the operation is currently IN_PROGRESS in another attempt.
            MaxAttemptsExceededError: If the operation failed and exhausted all attempts.
        """
        idempotency_key = self.compute_idempotency_key(
            capability_id,
            arguments,
            custom_key=custom_idempotency_key,
            quest_id=quest_id,
        )
        arg_hash = self.compute_argument_hash(arguments)

        existing = self.store.get_by_idempotency_key(idempotency_key)
        if existing:
            # 1. Exactly-Once check: Already COMMITTED -> Return cached receipt immediately
            if existing.state == MutationState.COMMITTED:
                return existing, True

            # 2. UNKNOWN_COMMIT check: Blind retries strictly forbidden!
            if existing.state == MutationState.UNKNOWN_COMMIT:
                raise OperationCommitUncertainError(
                    f"Operation '{existing.operation_id}' with idempotency key '{idempotency_key}' "
                    f"is in UNKNOWN_COMMIT state. Blind retries are strictly forbidden. "
                    f"Physical evidence reconciliation is required."
                )

            # 3. Concurrent execution check
            if existing.state == MutationState.IN_PROGRESS:
                raise LedgerError(
                    f"Operation '{existing.operation_id}' is currently IN_PROGRESS. "
                    f"Concurrent execution of the same idempotency key is prohibited."
                )

            # 4. FAILED check: Can retry only if attempts remain
            if existing.state == MutationState.FAILED:
                if existing.current_attempt >= existing.max_attempts:
                    raise MaxAttemptsExceededError(
                        f"Operation '{existing.operation_id}' has exhausted all {existing.max_attempts} attempts."
                    )
                return existing, False

        # Create new operation record in PENDING state
        now = time.time()
        op_id = operation_id or f"op_{quest_id}_{step_id}_{capability_id}"
        new_op = OperationRecord(
            operation_id=op_id,
            quest_id=quest_id,
            step_id=step_id,
            capability_id=capability_id,
            idempotency_key=idempotency_key,
            argument_hash=arg_hash,
            state=MutationState.PENDING,
            current_attempt=0,
            max_attempts=max_attempts,
            created_at=now,
            updated_at=now,
        )

        persisted = self.store.create_operation(new_op)
        return persisted, False

    def begin_attempt(self, operation_id: str) -> OperationAttempt:
        """Transitions an operation to IN_PROGRESS and records a new execution attempt.
        
        Args:
            operation_id: The target operation ID.
            
        Returns:
            The newly created OperationAttempt in STARTED state.
            
        Raises:
            OperationNotFoundError: If operation does not exist.
            OperationCommitUncertainError: If operation is in UNKNOWN_COMMIT state.
            MaxAttemptsExceededError: If max_attempts reached.
            LedgerError: If already COMMITTED or IN_PROGRESS.
        """
        op = self.store.get_operation(operation_id)
        if not op:
            raise OperationNotFoundError(f"Operation '{operation_id}' not found")

        if op.state == MutationState.COMMITTED:
            raise LedgerError(f"Cannot begin attempt on already COMMITTED operation '{operation_id}'")

        if op.state == MutationState.UNKNOWN_COMMIT:
            raise OperationCommitUncertainError(
                f"Cannot begin attempt on operation '{operation_id}' in UNKNOWN_COMMIT state. Reconciliation required."
            )

        if op.state == MutationState.IN_PROGRESS:
            raise LedgerError(f"Operation '{operation_id}' is already IN_PROGRESS")

        if op.current_attempt >= op.max_attempts:
            raise MaxAttemptsExceededError(
                f"Operation '{operation_id}' has reached maximum attempt count ({op.max_attempts})"
            )

        new_attempt_number = op.current_attempt + 1
        now = time.time()

        # Create attempt
        attempt = OperationAttempt(
            operation_id=operation_id,
            attempt_number=new_attempt_number,
            state=AttemptState.STARTED,
            started_at=now,
        )

        # Update operation
        updated_op = op.model_copy(
            update={
                "state": MutationState.IN_PROGRESS,
                "current_attempt": new_attempt_number,
                "updated_at": now,
            }
        )
        saved_attempt, _ = self.store.begin_attempt_atomic(attempt, updated_op)
        return saved_attempt

    def commit_attempt(
        self,
        operation_id: str,
        attempt_id: str,
        execution_receipt: Dict[str, Any],
    ) -> OperationRecord:
        """Marks an attempt and its parent operation as COMMITTED.
        
        Args:
            operation_id: Target operation ID.
            attempt_id: The attempt that successfully completed.
            execution_receipt: Structured execution receipt from capability execution.
            
        Returns:
            The updated OperationRecord in COMMITTED status.
        """
        op = self.store.get_operation(operation_id)
        if not op:
            raise OperationNotFoundError(f"Operation '{operation_id}' not found")

        now = time.time()

        # Update attempt
        attempt = OperationAttempt(
            attempt_id=attempt_id,
            operation_id=operation_id,
            attempt_number=op.current_attempt,
            state=AttemptState.COMPLETED,
            finished_at=now,
            execution_receipt=execution_receipt,
        )

        # Update operation to COMMITTED
        updated_op = op.model_copy(
            update={
                "state": MutationState.COMMITTED,
                "execution_receipt": execution_receipt,
                "error": None,
                "updated_at": now,
            }
        )
        _, committed_op = self.store.commit_attempt_atomic(attempt, updated_op)
        return committed_op

    def fail_attempt(
        self,
        operation_id: str,
        attempt_id: str,
        error: str,
        is_uncertain: bool = False,
    ) -> OperationRecord:
        """Marks an attempt as failed, recording UNKNOWN_COMMIT if outcome is uncertain.
        
        Args:
            operation_id: Target operation ID.
            attempt_id: The attempt that encountered an error.
            error: Error message or reason.
            is_uncertain: If True, indicates network partition, timeout during mutation,
                         or unhandled process crash. Sets operation state to UNKNOWN_COMMIT,
                         which strictly blocks blind retries until reconciled.
                         
        Returns:
            The updated OperationRecord.
        """
        op = self.store.get_operation(operation_id)
        if not op:
            raise OperationNotFoundError(f"Operation '{operation_id}' not found")

        now = time.time()
        attempt_state = AttemptState.UNCERTAIN if is_uncertain else AttemptState.FAILED
        op_state = MutationState.UNKNOWN_COMMIT if is_uncertain else MutationState.FAILED

        # Update attempt
        attempt = OperationAttempt(
            attempt_id=attempt_id,
            operation_id=operation_id,
            attempt_number=op.current_attempt,
            state=attempt_state,
            finished_at=now,
            error=error,
        )

        # Update operation
        updated_op = op.model_copy(
            update={
                "state": op_state,
                "error": error,
                "updated_at": now,
            }
        )
        _, failed_op = self.store.fail_attempt_atomic(attempt, updated_op)
        return failed_op

    def commit_operation(
        self,
        operation_id: str,
        execution_receipt: Dict[str, Any],
        attempt_id: Optional[str] = None,
    ) -> OperationRecord:
        """Marks the active attempt and operation as COMMITTED."""
        if not attempt_id:
            attempts = self.store.get_attempts(operation_id)
            if not attempts:
                raise LedgerError(f"No attempts found for operation '{operation_id}' to commit")
            attempt_id = attempts[-1].attempt_id
        return self.commit_attempt(operation_id, attempt_id, execution_receipt)

    def fail_operation(
        self,
        operation_id: str,
        error: str,
        is_uncertain: bool = False,
        attempt_id: Optional[str] = None,
    ) -> OperationRecord:
        """Marks the active attempt and operation as failed or UNKNOWN_COMMIT."""
        if not attempt_id:
            attempts = self.store.get_attempts(operation_id)
            if not attempts:
                attempt = self.begin_attempt(operation_id)
                attempt_id = attempt.attempt_id
            else:
                attempt_id = attempts[-1].attempt_id
        return self.fail_attempt(operation_id, attempt_id, error, is_uncertain=is_uncertain)

    def reconcile_operation(
        self,
        operation_id: str,
        is_verified_committed: Optional[bool] = None,
        execution_receipt: Optional[Dict[str, Any]] = None,
        reconciliation_note: Optional[str] = None,
        reconciled_state: Optional[Union[MutationState, str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> OperationRecord:
        """Reconciles an operation in UNKNOWN_COMMIT state based on independent physical verification.
        
        Args:
            operation_id: Target operation ID.
            is_verified_committed: True if physical verification confirmed the mutation took effect.
            execution_receipt: Verified outcome data if committed.
            reconciliation_note: Explanation or audit note for the reconciliation decision.
            reconciled_state: Optional MutationState (COMMITTED/FAILED) or string.
            evidence: Optional dictionary of evidence (alias for execution_receipt).
            
        Returns:
            The updated OperationRecord (COMMITTED if verified, FAILED if uncommitted).
            
        Raises:
            OperationNotFoundError: If operation does not exist.
            LedgerError: If operation is not in UNKNOWN_COMMIT state.
        """
        op = self.store.get_operation(operation_id)
        if not op:
            raise OperationNotFoundError(f"Operation '{operation_id}' not found")

        if op.state != MutationState.UNKNOWN_COMMIT:
            raise LedgerError(
                f"Operation '{operation_id}' is in state '{op.state.value}', not UNKNOWN_COMMIT. "
                f"Reconciliation can only be performed on UNKNOWN_COMMIT operations."
            )

        if is_verified_committed is None:
            if reconciled_state is not None:
                if isinstance(reconciled_state, str):
                    is_verified_committed = reconciled_state.lower() in ("committed", "mutationstate.committed")
                else:
                    is_verified_committed = (reconciled_state == MutationState.COMMITTED)
            else:
                is_verified_committed = False

        receipt_data = execution_receipt or evidence
        now = time.time()
        if is_verified_committed:
            new_state = MutationState.COMMITTED
            new_receipt = receipt_data or {"reconciliation": "verified_externally", "note": reconciliation_note}
            new_error = None
        else:
            new_state = MutationState.FAILED
            new_receipt = None
            new_error = f"Reconciled as uncommitted: {reconciliation_note or 'Verified mutation did not execute'}"

        updated_op = op.model_copy(
            update={
                "state": new_state,
                "execution_receipt": new_receipt,
                "error": new_error,
                "updated_at": now,
            }
        )
        return self.store.update_operation(updated_op)

    # =========================================================================
    # Queries & Helpers
    # =========================================================================

    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """Retrieves an operation record by ID."""
        return self.store.get_operation(operation_id)

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[OperationRecord]:
        """Retrieves an operation record by its external idempotency key."""
        return self.store.get_by_idempotency_key(idempotency_key)

    def list_uncertain_operations(self) -> List[OperationRecord]:
        """Returns all operations currently in UNKNOWN_COMMIT state."""
        return self.store.list_uncertain_operations()

    def close(self) -> None:
        """Closes store connections."""
        self.store.close()
