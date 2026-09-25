"""SQLite Persistence Store for Operation Ledger.

Provides relational storage, ACID transactions, and indexed lookup
for operations, attempts, and external idempotency keys (Checkpoint L11).
"""

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ..contracts.operation import (
    AttemptState,
    DuplicateOperationError,
    LedgerError,
    MutationState,
    OperationAttempt,
    OperationNotFoundError,
    OperationRecord,
)


class OperationStore:
    """Thread-safe persistent SQLite store for operations and attempts."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        """Initialize the operation store.
        
        Args:
            db_path: Path to database file or ':memory:'.
        """
        self.raw_path = str(db_path)
        self.is_memory = (self.raw_path == ":memory:")

        if self.is_memory:
            self.uri = "file:op_memdb?mode=memory&cache=shared"
            self.is_uri = True
        elif self.raw_path.startswith("file:"):
            self.uri = self.raw_path
            self.is_uri = True
        else:
            self.db_path = Path(self.raw_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.uri = str(self.db_path)
            self.is_uri = False

        self._local = threading.local()
        self._write_lock = threading.RLock()
        self._connections: List[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()

        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns or creates a thread-local SQLite connection initialized per Python 3.12 rules."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        connect_kwargs: Dict[str, Any] = {
            "timeout": 5.0,
            "autocommit": True,
        }
        if self.is_uri:
            connect_kwargs["uri"] = True

        conn = sqlite3.connect(self.uri, **connect_kwargs)
        conn.row_factory = sqlite3.Row

        if not self.is_memory:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")

        conn.autocommit = False

        self._local.conn = conn
        with self._conn_lock:
            self._connections.append(conn)

        return conn

    def _init_schema(self) -> None:
        """Initializes tables and indices."""
        conn = self._get_connection()
        with self._write_lock:
            try:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    operation_id TEXT PRIMARY KEY,
                    quest_id TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    argument_hash TEXT NOT NULL,
                    state TEXT NOT NULL,
                    current_attempt INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    execution_receipt TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ops_quest_step ON operations(quest_id, step_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ops_idempotency ON operations(idempotency_key);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ops_state ON operations(state);")

                conn.execute("""
                CREATE TABLE IF NOT EXISTS operation_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL,
                    attempt_number INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    started_at REAL NOT NULL,
                    finished_at REAL,
                    execution_receipt TEXT,
                    error TEXT,
                    FOREIGN KEY (operation_id) REFERENCES operations(operation_id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_attempts_op ON operation_attempts(operation_id, attempt_number);")

                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # =========================================================================
    # Operation Record Operations
    # =========================================================================

    def create_operation(self, op: OperationRecord) -> OperationRecord:
        """Persists a new operation record."""
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                conn.execute(
                    """
                    INSERT INTO operations (
                        operation_id, quest_id, step_id, capability_id, idempotency_key,
                        argument_hash, state, current_attempt, max_attempts, execution_receipt,
                        error, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        op.operation_id,
                        op.quest_id,
                        op.step_id,
                        op.capability_id,
                        op.idempotency_key,
                        op.argument_hash,
                        op.state.value,
                        op.current_attempt,
                        op.max_attempts,
                        json.dumps(op.execution_receipt, default=str) if op.execution_receipt is not None else None,
                        op.error,
                        op.created_at or now,
                        op.updated_at or now,
                    )
                )
                conn.commit()
                return op
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise DuplicateOperationError(
                    f"Operation with ID '{op.operation_id}' or key '{op.idempotency_key}' already exists: {exc}"
                ) from exc
            except Exception:
                conn.rollback()
                raise

    def get_operation(self, operation_id: str) -> Optional[OperationRecord]:
        """Retrieves an operation record by ID along with its attempts."""
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM operations WHERE operation_id = ?", (operation_id,))
            row = cur.fetchone()
            if not row:
                return None

            attempts = self.get_attempts(operation_id)

            return OperationRecord(
                operation_id=row["operation_id"],
                quest_id=row["quest_id"],
                step_id=row["step_id"],
                capability_id=row["capability_id"],
                idempotency_key=row["idempotency_key"],
                argument_hash=row["argument_hash"],
                state=MutationState(row["state"]),
                current_attempt=row["current_attempt"],
                max_attempts=row["max_attempts"],
                execution_receipt=json.loads(row["execution_receipt"]) if row["execution_receipt"] else None,
                error=row["error"],
                attempts=attempts,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[OperationRecord]:
        """Retrieves an operation record by its unique idempotency key."""
        conn = self._get_connection()
        op_id = None
        try:
            cur = conn.execute("SELECT operation_id FROM operations WHERE idempotency_key = ?", (idempotency_key,))
            row = cur.fetchone()
            if row:
                op_id = row["operation_id"]
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

        if not op_id:
            return None
        return self.get_operation(op_id)

    def get_by_quest_step(self, quest_id: str, step_id: str) -> Optional[OperationRecord]:
        """Retrieves the operation associated with a given quest_id and step_id."""
        conn = self._get_connection()
        op_id = None
        try:
            cur = conn.execute(
                "SELECT operation_id FROM operations WHERE quest_id = ? AND step_id = ?",
                (quest_id, step_id)
            )
            row = cur.fetchone()
            if row:
                op_id = row["operation_id"]
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

        if not op_id:
            return None
        return self.get_operation(op_id)

    def update_operation(self, op: OperationRecord) -> OperationRecord:
        """Updates an existing operation record."""
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                cur = conn.execute(
                    """
                    UPDATE operations
                    SET state = ?, current_attempt = ?, execution_receipt = ?,
                        error = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (
                        op.state.value,
                        op.current_attempt,
                        json.dumps(op.execution_receipt, default=str) if op.execution_receipt is not None else None,
                        op.error,
                        now,
                        op.operation_id,
                    )
                )
                if cur.rowcount == 0:
                    raise OperationNotFoundError(f"Operation {op.operation_id} not found")
                conn.commit()
                return op.model_copy(update={"updated_at": now})
            except Exception:
                conn.rollback()
                raise

    # =========================================================================
    # Attempt Operations
    # =========================================================================

    def record_attempt(self, attempt: OperationAttempt) -> OperationAttempt:
        """Persists a new execution attempt."""
        conn = self._get_connection()
        with self._write_lock:
            try:
                conn.execute(
                    """
                    INSERT INTO operation_attempts (
                        attempt_id, operation_id, attempt_number, state,
                        started_at, finished_at, execution_receipt, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt.attempt_id,
                        attempt.operation_id,
                        attempt.attempt_number,
                        attempt.state.value,
                        attempt.started_at,
                        attempt.finished_at,
                        json.dumps(attempt.execution_receipt, default=str) if attempt.execution_receipt is not None else None,
                        attempt.error,
                    )
                )
                conn.commit()
                return attempt
            except Exception:
                conn.rollback()
                raise

    def update_attempt(self, attempt: OperationAttempt) -> OperationAttempt:
        """Updates an attempt (e.g. marking finished, receipt, or error)."""
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                conn.execute(
                    """
                    UPDATE operation_attempts
                    SET state = ?, finished_at = ?, execution_receipt = ?, error = ?
                    WHERE attempt_id = ?
                    """,
                    (
                        attempt.state.value,
                        attempt.finished_at or now,
                        json.dumps(attempt.execution_receipt, default=str) if attempt.execution_receipt is not None else None,
                        attempt.error,
                        attempt.attempt_id,
                    )
                )
                conn.commit()
                return attempt.model_copy(update={"finished_at": attempt.finished_at or now})
            except Exception:
                conn.rollback()
                raise

    def get_attempts(self, operation_id: str) -> List[OperationAttempt]:
        """Retrieves all attempts for a given operation ordered by attempt number."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM operation_attempts WHERE operation_id = ? ORDER BY attempt_number ASC",
                (operation_id,)
            )
            attempts: List[OperationAttempt] = []
            for row in cur.fetchall():
                attempts.append(
                    OperationAttempt(
                        attempt_id=row["attempt_id"],
                        operation_id=row["operation_id"],
                        attempt_number=row["attempt_number"],
                        state=AttemptState(row["state"]),
                        started_at=row["started_at"],
                        finished_at=row["finished_at"],
                        execution_receipt=json.loads(row["execution_receipt"]) if row["execution_receipt"] else None,
                        error=row["error"],
                    )
                )
            return attempts
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

    def list_uncertain_operations(self) -> List[OperationRecord]:
        """Retrieves all operations currently in UNKNOWN_COMMIT state requiring reconciliation."""
        conn = self._get_connection()
        op_ids = []
        try:
            cur = conn.execute(
                "SELECT operation_id FROM operations WHERE state = ? ORDER BY created_at ASC",
                (MutationState.UNKNOWN_COMMIT.value,)
            )
            op_ids = [row["operation_id"] for row in cur.fetchall()]
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

        results: List[OperationRecord] = []
        for op_id in op_ids:
            op = self.get_operation(op_id)
            if op:
                results.append(op)
        return results

    # =========================================================================
    # Atomic Attempt and Operation Transitions (Checkpoint L14.1 / AUDIT-04)
    # =========================================================================

    def begin_attempt_atomic(
        self,
        attempt: OperationAttempt,
        updated_op: OperationRecord,
    ) -> Tuple[OperationAttempt, OperationRecord]:
        """Atomically inserts a new attempt and transitions operation to IN_PROGRESS in a single transaction.
        
        Args:
            attempt: The newly created OperationAttempt in STARTED state.
            updated_op: The OperationRecord with state=IN_PROGRESS and incremented attempt count.
            
        Returns:
            Tuple of (persisted OperationAttempt, persisted OperationRecord).
        """
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                # 1. Insert attempt
                conn.execute(
                    """
                    INSERT INTO operation_attempts (
                        attempt_id, operation_id, attempt_number, state,
                        started_at, finished_at, execution_receipt, error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        attempt.attempt_id,
                        attempt.operation_id,
                        attempt.attempt_number,
                        attempt.state.value,
                        attempt.started_at,
                        attempt.finished_at,
                        json.dumps(attempt.execution_receipt, default=str) if attempt.execution_receipt is not None else None,
                        attempt.error,
                    )
                )

                # 2. Update operation
                cur = conn.execute(
                    """
                    UPDATE operations
                    SET state = ?, current_attempt = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (
                        updated_op.state.value,
                        updated_op.current_attempt,
                        now,
                        updated_op.operation_id,
                    )
                )
                if cur.rowcount == 0:
                    raise OperationNotFoundError(f"Operation {updated_op.operation_id} not found")

                conn.commit()
                return attempt, updated_op.model_copy(update={"updated_at": now})
            except Exception:
                conn.rollback()
                raise

    def commit_attempt_atomic(
        self,
        attempt: OperationAttempt,
        updated_op: OperationRecord,
    ) -> Tuple[OperationAttempt, OperationRecord]:
        """Atomically marks attempt and operation as COMMITTED in a single transaction.
        
        Args:
            attempt: The completed attempt with state=COMPLETED and execution_receipt.
            updated_op: The operation with state=COMMITTED and execution_receipt.
            
        Returns:
            Tuple of (persisted OperationAttempt, persisted OperationRecord).
        """
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                # 1. Update attempt
                conn.execute(
                    """
                    UPDATE operation_attempts
                    SET state = ?, finished_at = ?, execution_receipt = ?, error = ?
                    WHERE attempt_id = ?
                    """,
                    (
                        attempt.state.value,
                        attempt.finished_at or now,
                        json.dumps(attempt.execution_receipt, default=str) if attempt.execution_receipt is not None else None,
                        attempt.error,
                        attempt.attempt_id,
                    )
                )

                # 2. Update operation
                cur = conn.execute(
                    """
                    UPDATE operations
                    SET state = ?, execution_receipt = ?, error = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (
                        updated_op.state.value,
                        json.dumps(updated_op.execution_receipt, default=str) if updated_op.execution_receipt is not None else None,
                        updated_op.error,
                        now,
                        updated_op.operation_id,
                    )
                )
                if cur.rowcount == 0:
                    raise OperationNotFoundError(f"Operation {updated_op.operation_id} not found")

                conn.commit()
                return (
                    attempt.model_copy(update={"finished_at": attempt.finished_at or now}),
                    updated_op.model_copy(update={"updated_at": now}),
                )
            except Exception:
                conn.rollback()
                raise

    def fail_attempt_atomic(
        self,
        attempt: OperationAttempt,
        updated_op: OperationRecord,
    ) -> Tuple[OperationAttempt, OperationRecord]:
        """Atomically marks attempt and operation as FAILED or UNKNOWN_COMMIT in a single transaction.
        
        Args:
            attempt: The failed attempt with state=FAILED and error.
            updated_op: The operation with state=FAILED/UNKNOWN_COMMIT and error.
            
        Returns:
            Tuple of (persisted OperationAttempt, persisted OperationRecord).
        """
        conn = self._get_connection()
        now = time.time()
        with self._write_lock:
            try:
                # 1. Update attempt
                conn.execute(
                    """
                    UPDATE operation_attempts
                    SET state = ?, finished_at = ?, error = ?
                    WHERE attempt_id = ?
                    """,
                    (
                        attempt.state.value,
                        attempt.finished_at or now,
                        attempt.error,
                        attempt.attempt_id,
                    )
                )

                # 2. Update operation
                cur = conn.execute(
                    """
                    UPDATE operations
                    SET state = ?, error = ?, updated_at = ?
                    WHERE operation_id = ?
                    """,
                    (
                        updated_op.state.value,
                        updated_op.error,
                        now,
                        updated_op.operation_id,
                    )
                )
                if cur.rowcount == 0:
                    raise OperationNotFoundError(f"Operation {updated_op.operation_id} not found")

                conn.commit()
                return (
                    attempt.model_copy(update={"finished_at": attempt.finished_at or now}),
                    updated_op.model_copy(update={"updated_at": now}),
                )
            except Exception:
                conn.rollback()
                raise

    def close(self) -> None:
        """Closes all active connections."""
        with self._conn_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        if hasattr(self._local, "conn"):
            self._local.conn = None
