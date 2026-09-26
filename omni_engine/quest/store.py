"""SQLite-backed Quest Persistence Store.

Provides ACID persistence, foreign-key enforcement, WAL mode configuration,
and Optimistic Concurrency Control (OCC) for Quests, Steps, and Events (Checkpoint L10).
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..contracts.enums import ActionClass, AutonomyProfile
from ..contracts.quest import (
    OptimisticLockError,
    Quest,
    QuestError,
    QuestEvent,
    QuestEventEnum,
    QuestNotFoundError,
    QuestStatus,
    QuestStep,
    StepNotFoundError,
    StepStatus,
    TERMINAL_QUEST_STATES,
)


class QuestStore:
    """Thread-safe persistent SQLite store for Quests, Steps, and Event Streams.
    
    Adheres strictly to ADR-013:
    - WAL mode & synchronous = NORMAL
    - Foreign keys ON
    - Explicit transaction demarcation with autocommit = False
    - Serialized write transactions via threading.RLock
    - Thread-local connections
    - Optimistic Concurrency Control (OCC) version tracking
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        """Initialize the store.
        
        Args:
            db_path: Filesystem path to SQLite file, or ':memory:'.
        """
        self.raw_path = str(db_path)
        self.is_memory = (self.raw_path == ":memory:")
        
        if self.is_memory:
            # Use shared in-memory URI so multiple thread connections share the database
            self.uri = "file:quest_memdb?mode=memory&cache=shared"
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

        # Initialize schema using an initial connection
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Returns or creates a thread-local SQLite connection initialized per Python 3.12 PRAGMA rules."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        # Connect with autocommit=True to execute WAL and safety PRAGMAs outside transactions
        connect_kwargs: Dict[str, Any] = {
            "timeout": 5.0,
            "autocommit": True,
        }
        if self.is_uri:
            connect_kwargs["uri"] = True

        conn = sqlite3.connect(self.uri, **connect_kwargs)
        conn.row_factory = sqlite3.Row

        # Execute PRAGMAs per ADR-013
        if not self.is_memory:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        conn.execute("PRAGMA foreign_keys = ON;")

        # Enable explicit PEP 249 transactions
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
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS quests (
                    quest_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    autonomy_profile TEXT NOT NULL,
                    current_step_id TEXT,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_quests_status ON quests(status);")

                conn.execute("""
                CREATE TABLE IF NOT EXISTS quest_steps (
                    step_id TEXT NOT NULL,
                    quest_id TEXT NOT NULL,
                    capability_id TEXT NOT NULL,
                    action_class TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    dependencies TEXT NOT NULL,
                    status TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    timeout_s REAL,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    can_fail_silently INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    execution_receipt TEXT,
                    verification_receipt TEXT,
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (quest_id, step_id),
                    FOREIGN KEY (quest_id) REFERENCES quests(quest_id) ON DELETE CASCADE
                );
                """)
                # Migrations for existing tables (AUDIT-09)
                for col_name, col_type in (
                    ("timeout_s", "REAL"),
                    ("max_attempts", "INTEGER DEFAULT 3"),
                    ("can_fail_silently", "INTEGER DEFAULT 0"),
                    ("metadata", "TEXT DEFAULT '{}'"),
                ):
                    try:
                        conn.execute(f"ALTER TABLE quest_steps ADD COLUMN {col_name} {col_type};")
                    except sqlite3.OperationalError:
                        pass

                conn.execute("CREATE INDEX IF NOT EXISTS idx_steps_status ON quest_steps(quest_id, status);")

                conn.execute("""
                CREATE TABLE IF NOT EXISTS quest_events (
                    event_id TEXT PRIMARY KEY,
                    quest_id TEXT NOT NULL,
                    step_id TEXT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    FOREIGN KEY (quest_id) REFERENCES quests(quest_id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_quest ON quest_events(quest_id, timestamp);")

                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?);",
                    (self.SCHEMA_VERSION, time.time())
                )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    # =========================================================================
    # Quest Operations
    # =========================================================================

    def create_quest(self, quest: Quest) -> Quest:
        """Persists a new Quest and any initial steps atomically.
        
        Args:
            quest: The Quest instance to insert.
            
        Returns:
            The persisted Quest.
            
        Raises:
            QuestError: If a quest with the same ID already exists.
        """
        conn = self._get_connection()
        now = time.time()
        created_at = quest.created_at or now
        updated_at = quest.updated_at or now

        with self._write_lock:
            try:
                conn.execute(
                    """
                    INSERT INTO quests (
                        quest_id, title, goal, status, version, autonomy_profile,
                        current_step_id, metadata, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        quest.quest_id,
                        quest.title,
                        quest.goal,
                        quest.status.value,
                        quest.version,
                        quest.autonomy_profile.value,
                        quest.current_step_id,
                        json.dumps(quest.metadata, default=str),
                        created_at,
                        updated_at,
                    )
                )

                # Insert steps if provided
                for step in quest.steps:
                    conn.execute(
                        """
                        INSERT INTO quest_steps (
                            step_id, quest_id, capability_id, action_class, intent,
                            arguments, dependencies, status, version, execution_receipt,
                            verification_receipt, error, timeout_s, max_attempts,
                            can_fail_silently, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self._step_to_insert_row(quest.quest_id, step, created_at)
                    )

                conn.commit()
                return quest
            except sqlite3.IntegrityError as exc:
                conn.rollback()
                raise QuestError(f"Quest {quest.quest_id} already exists or violated integrity: {exc}") from exc
            except Exception:
                conn.rollback()
                raise

    @staticmethod
    def _step_to_insert_row(quest_id: str, step: QuestStep, default_time: float) -> tuple:
        """Serializes a QuestStep into a parameter tuple for INSERT INTO quest_steps."""
        return (
            step.step_id,
            quest_id,
            step.capability_id,
            step.action_class.value,
            step.intent,
            json.dumps(step.arguments, default=str),
            json.dumps(step.dependencies, default=str),
            step.status.value,
            step.version,
            json.dumps(step.execution_receipt, default=str) if step.execution_receipt is not None else None,
            json.dumps(step.verification_receipt, default=str) if step.verification_receipt is not None else None,
            step.error,
            step.timeout_s,
            step.max_attempts,
            1 if step.can_fail_silently else 0,
            json.dumps(step.metadata, default=str),
            step.created_at or default_time,
            step.updated_at or default_time,
        )

    @staticmethod
    def _row_to_step(row: sqlite3.Row) -> QuestStep:
        """Deserializes a sqlite3.Row into a QuestStep, safely handling extended columns."""
        keys = row.keys()
        timeout_s = row["timeout_s"] if "timeout_s" in keys else None
        max_attempts = row["max_attempts"] if "max_attempts" in keys and row["max_attempts"] is not None else 3
        can_fail_silently = bool(row["can_fail_silently"]) if "can_fail_silently" in keys and row["can_fail_silently"] is not None else False
        meta = {}
        if "metadata" in keys and row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                meta = {}

        return QuestStep(
            step_id=row["step_id"],
            quest_id=row["quest_id"],
            capability_id=row["capability_id"],
            action_class=ActionClass(row["action_class"]),
            intent=row["intent"],
            arguments=json.loads(row["arguments"]),
            dependencies=json.loads(row["dependencies"]),
            status=StepStatus(row["status"]),
            version=row["version"],
            execution_receipt=json.loads(row["execution_receipt"]) if row["execution_receipt"] else None,
            verification_receipt=json.loads(row["verification_receipt"]) if row["verification_receipt"] else None,
            error=row["error"],
            timeout_s=timeout_s,
            max_attempts=max_attempts,
            can_fail_silently=can_fail_silently,
            metadata=meta,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Retrieves a Quest and its steps by ID.
        
        Args:
            quest_id: The unique quest ID.
            
        Returns:
            The populated Quest model, or None if not found.
        """
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM quests WHERE quest_id = ?", (quest_id,))
            row = cur.fetchone()
            if not row:
                return None

            # Fetch steps
            step_cur = conn.execute(
                "SELECT * FROM quest_steps WHERE quest_id = ? ORDER BY created_at ASC, step_id ASC",
                (quest_id,)
            )
            steps: List[QuestStep] = [self._row_to_step(s_row) for s_row in step_cur.fetchall()]

            return Quest(
                quest_id=row["quest_id"],
                title=row["title"],
                goal=row["goal"],
                status=QuestStatus(row["status"]),
                version=row["version"],
                autonomy_profile=AutonomyProfile(row["autonomy_profile"]),
                current_step_id=row["current_step_id"],
                steps=steps,
                metadata=json.loads(row["metadata"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

    def update_quest(self, quest: Quest) -> Quest:
        """Updates Quest attributes using Optimistic Concurrency Control (OCC).
        
        Increments the `version` counter by 1.
        
        Args:
            quest: The Quest to update (quest.version must match current database version).
            
        Returns:
            Updated Quest with incremented version and updated timestamp.
            
        Raises:
            QuestNotFoundError: If the quest does not exist.
            OptimisticLockError: If the version does not match (concurrent update occurred).
        """
        conn = self._get_connection()
        now = time.time()
        new_version = quest.version + 1

        with self._write_lock:
            try:
                cur = conn.execute(
                    """
                    UPDATE quests
                    SET title = ?, goal = ?, status = ?, autonomy_profile = ?,
                        current_step_id = ?, metadata = ?, version = ?, updated_at = ?
                    WHERE quest_id = ? AND version = ?
                    """,
                    (
                        quest.title,
                        quest.goal,
                        quest.status.value,
                        quest.autonomy_profile.value,
                        quest.current_step_id,
                        json.dumps(quest.metadata, default=str),
                        new_version,
                        now,
                        quest.quest_id,
                        quest.version,
                    )
                )

                if cur.rowcount == 0:
                    # Check whether the quest exists at all
                    check_cur = conn.execute("SELECT version FROM quests WHERE quest_id = ?", (quest.quest_id,))
                    existing = check_cur.fetchone()
                    if not existing:
                        raise QuestNotFoundError(f"Quest {quest.quest_id} not found")
                    actual_version = existing["version"]
                    raise OptimisticLockError(
                        f"Quest {quest.quest_id} OCC conflict: expected version {quest.version}, but database has {actual_version}"
                    )

                conn.commit()
                return quest.model_copy(update={"version": new_version, "updated_at": now})
            except Exception:
                conn.rollback()
                raise

    def list_active_quests(self) -> List[Quest]:
        """Lists all quests currently in a non-terminal state."""
        conn = self._get_connection()
        quest_ids = []
        try:
            terminal_values = tuple(s.value for s in TERMINAL_QUEST_STATES)
            placeholders = ",".join("?" for _ in terminal_values)
            cur = conn.execute(
                f"SELECT quest_id FROM quests WHERE status NOT IN ({placeholders}) ORDER BY created_at ASC",
                terminal_values
            )
            quest_ids = [row["quest_id"] for row in cur.fetchall()]
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

        results: List[Quest] = []
        for q_id in quest_ids:
            q = self.get_quest(q_id)
            if q is not None:
                results.append(q)
        return results

    # =========================================================================
    # Step Operations
    # =========================================================================

    def save_steps(self, quest_id: str, steps: List[QuestStep]) -> None:
        """Appends or attaches a collection of steps to a Quest.
        
        Args:
            quest_id: The ID of the parent Quest.
            steps: The list of QuestStep objects to persist.
        """
        conn = self._get_connection()
        now = time.time()

        with self._write_lock:
            try:
                for step in steps:
                    conn.execute(
                        """
                        INSERT INTO quest_steps (
                            step_id, quest_id, capability_id, action_class, intent,
                            arguments, dependencies, status, version, execution_receipt,
                            verification_receipt, error, timeout_s, max_attempts,
                            can_fail_silently, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self._step_to_insert_row(quest_id, step, now)
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def get_step(self, quest_id: str, step_id: str) -> Optional[QuestStep]:
        """Retrieves an individual step by quest_id and step_id."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM quest_steps WHERE quest_id = ? AND step_id = ?",
                (quest_id, step_id)
            )
            row = cur.fetchone()
            if not row:
                return None

            return self._row_to_step(row)
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

    def update_step(self, step: QuestStep) -> QuestStep:
        """Updates a QuestStep using Optimistic Concurrency Control (OCC).
        
        Increments the step's `version` counter by 1.
        
        Args:
            step: The QuestStep to update.
            
        Returns:
            The updated QuestStep with incremented version and new timestamp.
            
        Raises:
            StepNotFoundError: If the step does not exist.
            OptimisticLockError: If the version in the database does not match step.version.
        """
        conn = self._get_connection()
        now = time.time()
        new_version = step.version + 1

        with self._write_lock:
            try:
                cur = conn.execute(
                    """
                    UPDATE quest_steps
                    SET capability_id = ?, action_class = ?, intent = ?, arguments = ?,
                        dependencies = ?, status = ?, version = ?, execution_receipt = ?,
                        verification_receipt = ?, error = ?, timeout_s = ?, max_attempts = ?,
                        can_fail_silently = ?, metadata = ?, updated_at = ?
                    WHERE quest_id = ? AND step_id = ? AND version = ?
                    """,
                    (
                        step.capability_id,
                        step.action_class.value,
                        step.intent,
                        json.dumps(step.arguments, default=str),
                        json.dumps(step.dependencies, default=str),
                        step.status.value,
                        new_version,
                        json.dumps(step.execution_receipt, default=str) if step.execution_receipt is not None else None,
                        json.dumps(step.verification_receipt, default=str) if step.verification_receipt is not None else None,
                        step.error,
                        step.timeout_s,
                        step.max_attempts,
                        1 if step.can_fail_silently else 0,
                        json.dumps(step.metadata, default=str),
                        now,
                        step.quest_id,
                        step.step_id,
                        step.version,
                    )
                )

                if cur.rowcount == 0:
                    check_cur = conn.execute(
                        "SELECT version FROM quest_steps WHERE quest_id = ? AND step_id = ?",
                        (step.quest_id, step.step_id)
                    )
                    existing = check_cur.fetchone()
                    if not existing:
                        raise StepNotFoundError(f"Step {step.step_id} in Quest {step.quest_id} not found")
                    actual_version = existing["version"]
                    raise OptimisticLockError(
                        f"Step {step.step_id} OCC conflict: expected version {step.version}, database has {actual_version}"
                    )

                conn.commit()
                return step.model_copy(update={"version": new_version, "updated_at": now})
            except Exception:
                conn.rollback()
                raise

    # =========================================================================
    # Event Operations
    # =========================================================================

    def record_event(self, event: QuestEvent) -> QuestEvent:
        """Appends an immutable event to the Quest event stream.
        
        Args:
            event: The QuestEvent to record.
            
        Returns:
            The recorded QuestEvent.
        """
        conn = self._get_connection()
        with self._write_lock:
            try:
                conn.execute(
                    """
                    INSERT INTO quest_events (
                        event_id, quest_id, step_id, event_type, payload, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.quest_id,
                        event.step_id,
                        event.event_type.value,
                        json.dumps(event.payload, default=str),
                        event.timestamp,
                    )
                )
                conn.commit()
                return event
            except Exception:
                conn.rollback()
                raise

    def get_events(self, quest_id: str) -> List[QuestEvent]:
        """Retrieves all chronological events for a given Quest."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM quest_events WHERE quest_id = ? ORDER BY timestamp ASC, rowid ASC",
                (quest_id,)
            )
            events: List[QuestEvent] = []
            for row in cur.fetchall():
                events.append(
                    QuestEvent(
                        event_id=row["event_id"],
                        quest_id=row["quest_id"],
                        step_id=row["step_id"],
                        event_type=QuestEventEnum(row["event_type"]),
                        payload=json.loads(row["payload"]),
                        timestamp=row["timestamp"],
                    )
                )
            return events
        finally:
            try:
                conn.rollback()
            except Exception:
                pass

    # =========================================================================
    # Atomic Multi-Entity Operations (Checkpoint L14.1 / AUDIT-05)
    # =========================================================================

    def transition_quest_atomic(
        self,
        quest: Optional[Quest] = None,
        event: Optional[QuestEvent] = None,
        *,
        quest_id: Optional[str] = None,
        target_status: Optional[QuestStatus] = None,
        event_type: Optional[QuestEventEnum] = None,
        reason: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        current_step_id: Optional[str] = None,
        _fault_injection: Optional[str] = None,
    ) -> Quest:
        """Atomically updates a Quest's status and appends its audit event in a single transaction.
        
        Args:
            quest: The Quest with target status to update (OCC version check applied).
            event: The corresponding QuestEvent to persist.
            
        Returns:
            Updated Quest with incremented version and updated timestamp.
            
        Raises:
            QuestNotFoundError: If the quest does not exist.
            OptimisticLockError: If an OCC version conflict occurs.
        """
        if quest is None:
            if not quest_id:
                raise ValueError("Must provide either 'quest' or 'quest_id'")
            fetched = self.get_quest(quest_id)
            if not fetched:
                raise QuestNotFoundError(f"Quest {quest_id} not found")
            quest = fetched.model_copy(
                update={
                    "status": target_status or fetched.status,
                    "current_step_id": current_step_id or fetched.current_step_id,
                }
            )

        if event is None:
            evt_type = event_type or QuestEventEnum.QUEST_RESUMED
            evt_payload = payload or ({"reason": reason} if reason else {})
            event = QuestEvent(
                quest_id=quest.quest_id,
                step_id=current_step_id,
                event_type=evt_type,
                payload=evt_payload,
            )

        conn = self._get_connection()
        now = time.time()
        new_version = quest.version + 1

        with self._write_lock:
            try:
                cur = conn.execute(
                    """
                    UPDATE quests
                    SET title = ?, goal = ?, status = ?, autonomy_profile = ?,
                        current_step_id = ?, metadata = ?, version = ?, updated_at = ?
                    WHERE quest_id = ? AND version = ?
                    """,
                    (
                        quest.title,
                        quest.goal,
                        quest.status.value,
                        quest.autonomy_profile.value,
                        quest.current_step_id,
                        json.dumps(quest.metadata, default=str),
                        new_version,
                        now,
                        quest.quest_id,
                        quest.version,
                    )
                )

                if cur.rowcount == 0:
                    check_cur = conn.execute("SELECT version FROM quests WHERE quest_id = ?", (quest.quest_id,))
                    existing = check_cur.fetchone()
                    if not existing:
                        raise QuestNotFoundError(f"Quest {quest.quest_id} not found")
                    actual_version = existing["version"]
                    raise OptimisticLockError(
                        f"Quest {quest.quest_id} OCC conflict: expected version {quest.version}, but database has {actual_version}"
                    )

                if _fault_injection == "after_quest_update":
                    raise sqlite3.OperationalError("Simulated fault after quest update")

                # Atomically append the event
                conn.execute(
                    """
                    INSERT INTO quest_events (
                        event_id, quest_id, step_id, event_type, payload, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.quest_id,
                        event.step_id,
                        event.event_type.value,
                        json.dumps(event.payload, default=str),
                        event.timestamp,
                    )
                )

                conn.commit()
                return quest.model_copy(update={"version": new_version, "updated_at": now})
            except Exception:
                conn.rollback()
                raise

    def transition_step_atomic(
        self,
        step: QuestStep,
        event: QuestEvent,
        _fault_injection: Optional[str] = None,
    ) -> QuestStep:
        """Atomically updates a step's execution state and records its audit event in a single transaction.
        
        Args:
            step: The QuestStep with target status (OCC version check applied).
            event: The corresponding QuestEvent to persist.
            _fault_injection: Optional fault injection key for atomicity testing.
            
        Returns:
            Updated QuestStep with incremented version and updated timestamp.
            
        Raises:
            StepNotFoundError: If step does not exist.
            OptimisticLockError: If an OCC version conflict occurs.
        """
        conn = self._get_connection()
        now = time.time()
        new_version = step.version + 1

        with self._write_lock:
            try:
                cur = conn.execute(
                    """
                    UPDATE quest_steps
                    SET capability_id = ?, action_class = ?, intent = ?, arguments = ?,
                        dependencies = ?, status = ?, version = ?, execution_receipt = ?,
                        verification_receipt = ?, error = ?, timeout_s = ?, max_attempts = ?,
                        can_fail_silently = ?, metadata = ?, updated_at = ?
                    WHERE quest_id = ? AND step_id = ? AND version = ?
                    """,
                    (
                        step.capability_id,
                        step.action_class.value,
                        step.intent,
                        json.dumps(step.arguments, default=str),
                        json.dumps(step.dependencies, default=str),
                        step.status.value,
                        new_version,
                        json.dumps(step.execution_receipt, default=str) if step.execution_receipt is not None else None,
                        json.dumps(step.verification_receipt, default=str) if step.verification_receipt is not None else None,
                        step.error,
                        step.timeout_s,
                        step.max_attempts,
                        1 if step.can_fail_silently else 0,
                        json.dumps(step.metadata, default=str),
                        now,
                        step.quest_id,
                        step.step_id,
                        step.version,
                    )
                )

                if cur.rowcount == 0:
                    check_cur = conn.execute(
                        "SELECT version FROM quest_steps WHERE quest_id = ? AND step_id = ?",
                        (step.quest_id, step.step_id)
                    )
                    existing = check_cur.fetchone()
                    if not existing:
                        raise StepNotFoundError(f"Step {step.step_id} in Quest {step.quest_id} not found")
                    actual_version = existing["version"]
                    raise OptimisticLockError(
                        f"Step {step.step_id} OCC conflict: expected version {step.version}, database has {actual_version}"
                    )

                if _fault_injection == "after_step_update":
                    raise sqlite3.OperationalError("Simulated fault after step update")

                # Atomically append the event
                conn.execute(
                    """
                    INSERT INTO quest_events (
                        event_id, quest_id, step_id, event_type, payload, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.quest_id,
                        event.step_id,
                        event.event_type.value,
                        json.dumps(event.payload, default=str),
                        event.timestamp,
                    )
                )

                conn.commit()
                return step.model_copy(update={"version": new_version, "updated_at": now})
            except Exception:
                conn.rollback()
                raise

    def attach_plan_atomic(
        self,
        quest: Quest,
        steps: List[QuestStep],
        event: QuestEvent,
        _fault_injection: Optional[str] = None,
    ) -> Quest:
        """Atomically updates Quest to PLANNED, inserts all steps, and appends the PLAN_ATTACHED event.
        
        Args:
            quest: The Quest model with status PLANNED and attached steps.
            steps: Collection of QuestStep objects to persist.
            event: The PLAN_ATTACHED event to append.
            _fault_injection: Optional fault injection key for atomicity testing.
            
        Returns:
            Updated Quest with incremented version and updated timestamp.
        """
        conn = self._get_connection()
        now = time.time()
        new_version = quest.version + 1

        with self._write_lock:
            try:
                # 1. Update Quest
                cur = conn.execute(
                    """
                    UPDATE quests
                    SET title = ?, goal = ?, status = ?, autonomy_profile = ?,
                        current_step_id = ?, metadata = ?, version = ?, updated_at = ?
                    WHERE quest_id = ? AND version = ?
                    """,
                    (
                        quest.title,
                        quest.goal,
                        quest.status.value,
                        quest.autonomy_profile.value,
                        quest.current_step_id,
                        json.dumps(quest.metadata, default=str),
                        new_version,
                        now,
                        quest.quest_id,
                        quest.version,
                    )
                )

                if cur.rowcount == 0:
                    check_cur = conn.execute("SELECT version FROM quests WHERE quest_id = ?", (quest.quest_id,))
                    existing = check_cur.fetchone()
                    if not existing:
                        raise QuestNotFoundError(f"Quest {quest.quest_id} not found")
                    actual_version = existing["version"]
                    raise OptimisticLockError(
                        f"Quest {quest.quest_id} OCC conflict: expected version {quest.version}, but database has {actual_version}"
                    )

                if _fault_injection == "after_quest_update":
                    raise sqlite3.OperationalError("Simulated fault after quest update")

                # 2. Insert all steps
                for step in steps:
                    conn.execute(
                        """
                        INSERT INTO quest_steps (
                            step_id, quest_id, capability_id, action_class, intent,
                            arguments, dependencies, status, version, execution_receipt,
                            verification_receipt, error, timeout_s, max_attempts,
                            can_fail_silently, metadata, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        self._step_to_insert_row(quest.quest_id, step, now)
                    )

                if _fault_injection == "after_steps_insert":
                    raise sqlite3.OperationalError("Simulated fault after steps insert")

                # 3. Insert the PLAN_ATTACHED event
                conn.execute(
                    """
                    INSERT INTO quest_events (
                        event_id, quest_id, step_id, event_type, payload, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.quest_id,
                        event.step_id,
                        event.event_type.value,
                        json.dumps(event.payload, default=str),
                        event.timestamp,
                    )
                )

                conn.commit()
                return quest.model_copy(update={"version": new_version, "updated_at": now, "steps": steps})
            except Exception:
                conn.rollback()
                raise

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def close(self) -> None:
        """Closes all active thread connections."""
        with self._conn_lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        if hasattr(self._local, "conn"):
            self._local.conn = None
