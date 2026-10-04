"""
omni_engine.verification.store
==============================
SQLite persistence for evidence-based completion receipts (Checkpoint L15).
"""

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omni_engine.contracts.verification import ObjectiveVerificationResult


class VerificationStore:
    """Thread-safe SQLite storage for durable Quest verification receipts."""

    def __init__(self, db_path: Union[str, Path] = ":memory:"):
        self.db_path = str(db_path)
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quest_verifications (
                    verification_id TEXT PRIMARY KEY,
                    quest_id TEXT NOT NULL,
                    plan_id TEXT,
                    objective_text TEXT,
                    verified_complete INTEGER NOT NULL,
                    verified_partial INTEGER NOT NULL,
                    verified_failure INTEGER NOT NULL,
                    unresolved_requirements TEXT,
                    violated_constraints TEXT,
                    evidence_hash TEXT NOT NULL,
                    verifier_version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_verifications_quest ON quest_verifications(quest_id);"
            )

    def record_verification(self, result: ObjectiveVerificationResult) -> None:
        """Durably stores an objective verification result."""
        conn = self._get_connection()
        with conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO quest_verifications (
                    verification_id, quest_id, plan_id, objective_text,
                    verified_complete, verified_partial, verified_failure,
                    unresolved_requirements, violated_constraints,
                    evidence_hash, verifier_version, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.verification_id,
                    result.quest_id,
                    result.plan_id,
                    result.objective_text,
                    1 if result.verified_complete else 0,
                    1 if result.verified_partial else 0,
                    1 if result.verified_failure else 0,
                    json.dumps(result.unresolved_requirements),
                    json.dumps(result.violated_constraints),
                    result.evidence_hash,
                    result.verifier_version,
                    json.dumps(result.model_dump()),
                    result.timestamp,
                ),
            )

    def get_verification(self, verification_id: str) -> Optional[ObjectiveVerificationResult]:
        """Retrieves a verification result by its verification_id."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT payload_json FROM quest_verifications WHERE verification_id = ?",
            (verification_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ObjectiveVerificationResult.model_validate(json.loads(row["payload_json"]))

    def get_latest_for_quest(self, quest_id: str) -> Optional[ObjectiveVerificationResult]:
        """Retrieves the latest verification result for a given quest_id."""
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT payload_json FROM quest_verifications WHERE quest_id = ? ORDER BY created_at DESC LIMIT 1",
            (quest_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ObjectiveVerificationResult.model_validate(json.loads(row["payload_json"]))

    def close(self) -> None:
        """Closes the current thread's SQLite connection."""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None
