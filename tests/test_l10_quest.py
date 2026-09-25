"""Comprehensive Unit & Integration Test Suite for Checkpoint L10: Persisted SQLite Quest Runtime.

Tests:
1. Strongly Typed Contracts & Extra Field Rejection (Invariant 4)
2. Deterministic State Machine Transitions & Terminal State Invariants (Invariant 1 & 6)
3. Optimistic Concurrency Control (OCC) Version Conflict Detection
4. Crash & Restart Recovery Simulation with File Persistence
5. Foreign Key Integrity & Cascade Enforcement
6. Multi-Threaded Concurrent Operations & WAL Mode Stability
7. Non-Switching Legacy Boundary (omni_agent.py and omni_engine/planner.py untouched)
"""

import os
import shutil
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import List

from pydantic import ValidationError

from omni_engine.contracts.enums import ActionClass, AutonomyProfile
from omni_engine.contracts.quest import (
    InvalidStateTransitionError,
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
    TERMINAL_STEP_STATES,
)
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore


class TestL10QuestContracts(unittest.TestCase):
    """Verifies Pydantic v2 contract integrity for Quests, Steps, and Events."""

    def test_quest_step_contract_valid_and_forbids_extra(self):
        step = QuestStep(
            step_id="step_1",
            quest_id="qst_123",
            capability_id="file_read",
            action_class=ActionClass.READ_ONLY,
            intent="Read user configuration",
            arguments={"path": "config.json"},
        )
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertEqual(step.version, 1)

        # Invariant 4: Forbids extra fields
        with self.assertRaises(ValidationError):
            QuestStep(
                step_id="step_2",
                quest_id="qst_123",
                capability_id="file_read",
                action_class=ActionClass.READ_ONLY,
                intent="Invalid step",
                unauthorized_extra_field="malicious",
            )

    def test_quest_contract_valid_and_forbids_extra(self):
        quest = Quest(
            quest_id="qst_001",
            title="Deploy Service",
            goal="Deploy production web server",
            status=QuestStatus.CREATED,
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertEqual(quest.version, 1)
        self.assertEqual(len(quest.steps), 0)

        # Forbids extra fields
        with self.assertRaises(ValidationError):
            Quest(
                quest_id="qst_002",
                title="Bad Quest",
                goal="Should fail",
                phantom_payload="illegal",
            )

    def test_quest_event_contract(self):
        event = QuestEvent(
            quest_id="qst_001",
            step_id="step_1",
            event_type=QuestEventEnum.STEP_COMPLETED,
            payload={"exit_code": 0},
        )
        self.assertTrue(event.event_id.startswith("evt_"))
        self.assertEqual(event.event_type, QuestEventEnum.STEP_COMPLETED)


class TestL10QuestStateMachine(unittest.TestCase):
    """Verifies state machine transitions, terminal states, and Invariant 6."""

    def setUp(self):
        self.engine = QuestEngine()

    def tearDown(self):
        self.engine.close()

    def test_full_happy_path_lifecycle(self):
        """CREATED -> PLANNED -> RUNNING -> AWAITING_VERIFICATION -> COMPLETED"""
        # 1. Create
        quest = self.engine.create_quest(
            title="Inspect System",
            goal="Analyze disk usage and generate report",
        )
        self.assertEqual(quest.status, QuestStatus.CREATED)
        self.assertEqual(quest.version, 1)

        # 2. Attach Plan -> PLANNED
        steps = [
            QuestStep(
                step_id="s1",
                quest_id=quest.quest_id,
                capability_id="system_diagnostics",
                action_class=ActionClass.READ_ONLY,
                intent="Gather diagnostics",
            ),
            QuestStep(
                step_id="s2",
                quest_id=quest.quest_id,
                capability_id="file_write",
                action_class=ActionClass.LOCAL_CREATE,
                intent="Save report",
                dependencies=["s1"],
            ),
        ]
        planned_quest = self.engine.attach_plan(quest.quest_id, steps)
        self.assertEqual(planned_quest.status, QuestStatus.PLANNED)
        self.assertEqual(len(planned_quest.steps), 2)
        self.assertEqual(planned_quest.version, 2)

        # 3. Transition to RUNNING
        running_quest = self.engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)
        self.assertEqual(running_quest.status, QuestStatus.RUNNING)
        self.assertEqual(running_quest.version, 3)

        # 4. Execute Step 1 (PENDING -> READY -> RUNNING)
        s1_ready = self.engine.transition_step(
            quest.quest_id, "s1", StepStatus.READY
        )
        self.assertEqual(s1_ready.status, StepStatus.READY)

        s1 = self.engine.transition_step(
            quest.quest_id, "s1", StepStatus.RUNNING
        )
        self.assertEqual(s1.status, StepStatus.RUNNING)
        self.assertEqual(self.engine.get_quest(quest.quest_id).current_step_id, "s1")

        s1_done = self.engine.transition_step(
            quest.quest_id,
            "s1",
            StepStatus.COMPLETED,
            execution_receipt={"disk_free_gb": 45.2},
        )
        self.assertEqual(s1_done.status, StepStatus.COMPLETED)
        self.assertEqual(s1_done.execution_receipt["disk_free_gb"], 45.2)

        # 5. Execute Step 2
        s2 = self.engine.transition_step(quest.quest_id, "s2", StepStatus.RUNNING)
        self.assertEqual(s2.status, StepStatus.RUNNING)
        self.assertEqual(self.engine.get_quest(quest.quest_id).current_step_id, "s2")

        s2_done = self.engine.transition_step(
            quest.quest_id,
            "s2",
            StepStatus.COMPLETED,
            execution_receipt={"path": "report.txt", "bytes": 1024},
        )
        self.assertEqual(s2_done.status, StepStatus.COMPLETED)

        # 6. Invariant 6: Direct RUNNING -> COMPLETED must be BLOCKED!
        with self.assertRaises(InvalidStateTransitionError):
            self.engine.transition_quest(quest.quest_id, QuestStatus.COMPLETED)

        # 7. RUNNING -> AWAITING_VERIFICATION must succeed
        verif_quest = self.engine.transition_quest(
            quest.quest_id, QuestStatus.AWAITING_VERIFICATION
        )
        self.assertEqual(verif_quest.status, QuestStatus.AWAITING_VERIFICATION)

        # 8. AWAITING_VERIFICATION -> COMPLETED
        completed_quest = self.engine.transition_quest(
            quest.quest_id, QuestStatus.COMPLETED
        )
        self.assertEqual(completed_quest.status, QuestStatus.COMPLETED)

        # 9. Verify event audit trail
        events = self.engine.get_events(quest.quest_id)
        event_types = [e.event_type for e in events]
        self.assertIn(QuestEventEnum.QUEST_CREATED, event_types)
        self.assertIn(QuestEventEnum.PLAN_ATTACHED, event_types)
        self.assertIn(QuestEventEnum.STEP_STARTED, event_types)
        self.assertIn(QuestEventEnum.STEP_COMPLETED, event_types)
        self.assertIn(QuestEventEnum.QUEST_AWAITING_VERIFICATION, event_types)
        self.assertIn(QuestEventEnum.QUEST_COMPLETED, event_types)

    def test_terminal_states_are_absorbing(self):
        """Terminal states cannot transition to any other state."""
        quest = self.engine.create_quest(title="Fail Test", goal="Intentional fail")
        self.engine.transition_quest(quest.quest_id, QuestStatus.FAILED, reason="Pre-flight check failed")

        failed_quest = self.engine.get_quest(quest.quest_id)
        self.assertEqual(failed_quest.status, QuestStatus.FAILED)

        # Any transition out of FAILED must be rejected
        for target in QuestStatus:
            with self.assertRaises(InvalidStateTransitionError):
                self.engine.transition_quest(quest.quest_id, target)

    def test_pause_and_resume_transitions(self):
        """RUNNING -> PAUSED_FOR_CONFIRMATION -> RUNNING -> PAUSED_FOR_INPUT -> RUNNING"""
        quest = self.engine.create_quest(
            title="Pause Test",
            goal="Test pause states",
            initial_steps=[
                QuestStep(
                    step_id="step_a",
                    quest_id="qst_temp",
                    capability_id="file_read",
                    action_class=ActionClass.READ_ONLY,
                    intent="Read",
                )
            ]
        )
        # Move to RUNNING
        self.engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)

        # Pause for confirmation
        paused_conf = self.engine.transition_quest(
            quest.quest_id, QuestStatus.PAUSED_FOR_CONFIRMATION, reason="High-risk action approval"
        )
        self.assertEqual(paused_conf.status, QuestStatus.PAUSED_FOR_CONFIRMATION)

        # Resume to RUNNING
        resumed_1 = self.engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)
        self.assertEqual(resumed_1.status, QuestStatus.RUNNING)

        # Pause for input
        paused_input = self.engine.transition_quest(
            quest.quest_id, QuestStatus.PAUSED_FOR_INPUT, reason="Missing parameter: port"
        )
        self.assertEqual(paused_input.status, QuestStatus.PAUSED_FOR_INPUT)

        # Resume to RUNNING
        resumed_2 = self.engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)
        self.assertEqual(resumed_2.status, QuestStatus.RUNNING)


class TestL10OptimisticConcurrencyControl(unittest.TestCase):
    """Verifies that concurrent updates on stale versions are rejected via OptimisticLockError."""

    def setUp(self):
        self.engine = QuestEngine()

    def tearDown(self):
        self.engine.close()

    def test_quest_occ_conflict_detection(self):
        quest = self.engine.create_quest(title="OCC Quest", goal="Test OCC")
        self.assertEqual(quest.version, 1)

        # Worker A fetches quest (version 1)
        worker_a_quest = self.engine.get_quest(quest.quest_id)
        # Worker B fetches quest (version 1)
        worker_b_quest = self.engine.get_quest(quest.quest_id)

        # Worker A updates quest status to FAILED -> updates db to version 2
        updated_a = self.engine.store.update_quest(
            worker_a_quest.model_copy(update={"status": QuestStatus.FAILED})
        )
        self.assertEqual(updated_a.version, 2)

        # Worker B tries to update using stale version 1 -> MUST raise OptimisticLockError
        with self.assertRaises(OptimisticLockError) as ctx:
            self.engine.store.update_quest(
                worker_b_quest.model_copy(update={"title": "Concurrent Update Title"})
            )
        self.assertIn("OCC conflict", str(ctx.exception))

    def test_step_occ_conflict_detection(self):
        quest = self.engine.create_quest(
            title="Step OCC Quest",
            goal="Test Step OCC",
            initial_steps=[
                QuestStep(
                    step_id="step_x",
                    quest_id="qst_step_occ",
                    capability_id="file_read",
                    action_class=ActionClass.READ_ONLY,
                    intent="Read",
                )
            ]
        )

        step_a = self.engine.get_step(quest.quest_id, "step_x")
        step_b = self.engine.get_step(quest.quest_id, "step_x")
        self.assertEqual(step_a.version, 1)

        # Worker A updates step status to RUNNING (advancing to version 2)
        updated_step_a = self.engine.store.update_step(
            step_a.model_copy(update={"status": StepStatus.RUNNING})
        )
        self.assertEqual(updated_step_a.version, 2)

        # Worker B attempts to update with stale version 1 -> MUST raise OptimisticLockError
        with self.assertRaises(OptimisticLockError):
            self.engine.store.update_step(
                step_b.model_copy(update={"intent": "Conflicting intent"})
            )


class TestL10CrashAndRestartRecovery(unittest.TestCase):
    """Simulates abrupt process crash mid-quest and verifies restart recovery from disk."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_quest_test_")
        self.db_path = Path(self.temp_dir) / "test_quests.db"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_crash_recovery_preserves_full_state(self):
        # 1. Start session, create quest with steps and execution receipts
        engine1 = QuestEngine(db_path=self.db_path)
        quest = engine1.create_quest(
            title="Durable Processing Quest",
            goal="Process large dataset across multiple stages",
            initial_steps=[
                QuestStep(
                    step_id="fetch_data",
                    quest_id="dummy",
                    capability_id="http_api",
                    action_class=ActionClass.EXTERNAL_CREATE,
                    intent="Fetch API dataset",
                ),
                QuestStep(
                    step_id="transform_data",
                    quest_id="dummy",
                    capability_id="file_transform",
                    action_class=ActionClass.LOCAL_UPDATE,
                    intent="Transform JSON to Parquet",
                    dependencies=["fetch_data"],
                ),
            ]
        )
        engine1.transition_quest(quest.quest_id, QuestStatus.RUNNING)
        engine1.transition_step(quest.quest_id, "fetch_data", StepStatus.RUNNING)
        engine1.transition_step(
            quest.quest_id,
            "fetch_data",
            StepStatus.COMPLETED,
            execution_receipt={"records_fetched": 1500, "url": "https://api.example.com/data"},
        )
        engine1.transition_step(quest.quest_id, "transform_data", StepStatus.RUNNING)

        # 2. Simulate CRASH: abruptly close database connections
        engine1.close()
        del engine1

        # 3. Simulate REBOOT: fresh engine instance loads existing SQLite database
        engine2 = QuestEngine(db_path=self.db_path)
        recovered_quest = engine2.get_quest(quest.quest_id)
        self.assertIsNotNone(recovered_quest)
        self.assertEqual(recovered_quest.title, "Durable Processing Quest")
        self.assertEqual(recovered_quest.status, QuestStatus.RUNNING)
        self.assertEqual(recovered_quest.current_step_id, "transform_data")
        self.assertEqual(len(recovered_quest.steps), 2)

        # Verify step 1 recovered with full receipts
        s1_recovered = engine2.get_step(quest.quest_id, "fetch_data")
        self.assertEqual(s1_recovered.status, StepStatus.COMPLETED)
        self.assertEqual(s1_recovered.execution_receipt["records_fetched"], 1500)

        # Verify step 2 recovered in RUNNING status
        s2_recovered = engine2.get_step(quest.quest_id, "transform_data")
        self.assertEqual(s2_recovered.status, StepStatus.RUNNING)

        # Verify active quest discovery
        active_quests = engine2.recover_active_quests()
        self.assertEqual(len(active_quests), 1)
        self.assertEqual(active_quests[0].quest_id, quest.quest_id)

        # Continue execution in new session
        engine2.transition_step(
            quest.quest_id,
            "transform_data",
            StepStatus.COMPLETED,
            execution_receipt={"output_file": "data.parquet"},
        )
        engine2.transition_quest(quest.quest_id, QuestStatus.AWAITING_VERIFICATION)
        completed = engine2.transition_quest(quest.quest_id, QuestStatus.COMPLETED)
        self.assertEqual(completed.status, QuestStatus.COMPLETED)

        engine2.close()


class TestL10ForeignKeysAndCascades(unittest.TestCase):
    """Verifies SQLite foreign key constraints and cascade deletions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_fk_test_")
        self.db_path = Path(self.temp_dir) / "fk_quests.db"
        self.engine = QuestEngine(db_path=self.db_path)

    def tearDown(self):
        self.engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_foreign_key_blocks_orphan_step(self):
        """Attempting to insert a step pointing to a non-existent quest must fail."""
        orphan_step = QuestStep(
            step_id="step_orphan",
            quest_id="qst_non_existent",
            capability_id="file_read",
            action_class=ActionClass.READ_ONLY,
            intent="Orphan step",
        )
        with self.assertRaises(Exception):
            self.engine.store.save_steps("qst_non_existent", [orphan_step])

    def test_cascade_delete_removes_steps_and_events(self):
        """Deleting a quest cascades to clean up its steps and audit events."""
        quest = self.engine.create_quest(
            title="Cascade Quest",
            goal="Test cascade",
            initial_steps=[
                QuestStep(
                    step_id="s_c1",
                    quest_id="dummy",
                    capability_id="file_read",
                    action_class=ActionClass.READ_ONLY,
                    intent="Read",
                )
            ]
        )
        # Verify step and event exist
        self.assertIsNotNone(self.engine.get_step(quest.quest_id, "s_c1"))
        self.assertGreaterEqual(len(self.engine.get_events(quest.quest_id)), 1)

        # Delete the quest row directly
        conn = self.engine.store._get_connection()
        with self.engine.store._write_lock:
            conn.execute("DELETE FROM quests WHERE quest_id = ?", (quest.quest_id,))
            conn.commit()

        # Step and events must be removed by SQLite CASCADE
        self.assertIsNone(self.engine.get_step(quest.quest_id, "s_c1"))
        self.assertEqual(len(self.engine.get_events(quest.quest_id)), 0)


class TestL10ConcurrencyAndWAL(unittest.TestCase):
    """Verifies that multiple concurrent threads can write and read without database locks."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_wal_test_")
        self.db_path = Path(self.temp_dir) / "wal_quests.db"
        self.engine = QuestEngine(db_path=self.db_path)

    def tearDown(self):
        self.engine.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_event_logging_under_threads(self):
        quest = self.engine.create_quest(title="Threaded Quest", goal="Stress test WAL")
        errors: List[Exception] = []

        def worker(thread_idx: int):
            try:
                for i in range(20):
                    self.engine.store.record_event(
                        QuestEvent(
                            quest_id=quest.quest_id,
                            event_type=QuestEventEnum.STEP_COMPLETED,
                            payload={"thread_idx": thread_idx, "iter": i},
                        )
                    )
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        events = self.engine.get_events(quest.quest_id)
        # Initial event + 5 * 20 = 101 events
        self.assertEqual(len(events), 101)


class TestL10LegacyNonSwitchingBoundary(unittest.TestCase):
    """Verifies that legacy prototype dispatch remains completely isolated."""

    def test_legacy_files_are_untouched(self):
        import subprocess
        res = subprocess.run(
            ["git", "diff", "HEAD", "omni_agent.py", "omni_engine/planner.py"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "", "Legacy files must have 0 diffs!")


if __name__ == "__main__":
    unittest.main()
