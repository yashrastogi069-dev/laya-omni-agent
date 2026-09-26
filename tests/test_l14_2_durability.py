"""Adversarial Durability, Transactional Fault Injection & Evidence Integrity Test Suite.

Checkpoint L14.2 — Proves runtime closure across operation identity, database CAS,
transactional rollback, plan tamper firewall, active cancellation, and durable reconciliation.
"""

import concurrent.futures
import os
import shutil
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

from omni_engine.contracts.enums import ActionClass, ErrorCode, IdempotencyClass, RetryPolicy
from omni_engine.contracts.execution import ExecutionFirewallError, StepExecutionReceipt
from omni_engine.contracts.operation import (
    AttemptState,
    ConcurrentAttemptConflictError,
    LedgerError,
    MaxAttemptsExceededError,
    MutationState,
    OperationAttempt,
    OperationCommitUncertainError,
    OperationNotFoundError,
    OperationRecord,
)
from omni_engine.contracts.plan import Plan, PlanStep, PlanType
from omni_engine.contracts.policy import AutonomyProfile
from omni_engine.contracts.quest import QuestEventEnum, QuestStatus, QuestStep, StepStatus
from omni_engine.execution.executor import DeterministicDAGExecutor, QuestAlreadyRunningError
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore
from omni_engine.planning.engine import StructuredDAGPlanner
from omni_engine.planning.validator import DeterministicPlanValidator
from omni_engine.policy.engine import PolicyEngine
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.capabilities.definitions import build_real_capability_registry


class TestL14_2_OperationIdentityAndIdempotency(unittest.TestCase):
    """L14.2-A: Logical Operation Identity & Idempotency Correctness."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_identity_")
        self.ledger_db = Path(self.temp_dir) / "ledger.db"
        self.store = OperationStore(self.ledger_db)
        self.ledger = OperationLedger(self.store)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_a1_same_quest_different_step_not_deduplicated(self):
        """A1: Steps in the same Quest with identical capability and arguments must NOT deduplicate."""
        quest_id = "quest_test_a1"
        args = {"target": "cache_file.txt", "action": "sync"}

        # Register Step A
        op_a, is_dedup_a = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_a",
            capability_id="file_write",
            arguments=args,
        )
        self.assertFalse(is_dedup_a)
        # Commit Step A
        attempt_a = self.ledger.begin_attempt(op_a.operation_id)
        self.ledger.commit_attempt(op_a.operation_id, attempt_a.attempt_id, {"status": "ok_a"})

        # Register Step B with identical capability and arguments in same Quest
        op_b, is_dedup_b = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_b",
            capability_id="file_write",
            arguments=args,
        )
        # In L14.2, step_b MUST NOT be deduplicated against step_a!
        self.assertFalse(is_dedup_b, "Step B must not deduplicate against Step A in the same quest")
        self.assertNotEqual(op_a.operation_id, op_b.operation_id)
        self.assertNotEqual(op_a.idempotency_key, op_b.idempotency_key)

    def test_a2_same_quest_same_step_replay_deduplicates(self):
        """A2: Replaying the exact same step with identical arguments deduplicates once COMMITTED."""
        quest_id = "quest_test_a2"
        args = {"filepath": "output.txt", "content": "data"}

        op1, is_dedup1 = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_1",
            capability_id="file_write",
            arguments=args,
        )
        self.assertFalse(is_dedup1)
        attempt = self.ledger.begin_attempt(op1.operation_id)
        self.ledger.commit_attempt(op1.operation_id, attempt.attempt_id, {"written": True})

        # Replay same step
        op2, is_dedup2 = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_1",
            capability_id="file_write",
            arguments=args,
        )
        self.assertTrue(is_dedup2)
        self.assertEqual(op1.operation_id, op2.operation_id)
        self.assertEqual(op2.state, MutationState.COMMITTED)

    def test_a3_cross_quest_different_keys_not_deduplicated(self):
        """A3: Unrelated quests with identical operations do not collide or deduplicate."""
        args = {"cmd": "build"}
        op_q1, is_dedup_q1 = self.ledger.register_mutation(
            quest_id="quest_alpha",
            step_id="step_build",
            capability_id="powershell",
            arguments=args,
        )
        att = self.ledger.begin_attempt(op_q1.operation_id)
        self.ledger.commit_attempt(op_q1.operation_id, att.attempt_id, {"exit": 0})

        op_q2, is_dedup_q2 = self.ledger.register_mutation(
            quest_id="quest_beta",
            step_id="step_build",
            capability_id="powershell",
            arguments=args,
        )
        self.assertFalse(is_dedup_q2)
        self.assertNotEqual(op_q1.operation_id, op_q2.operation_id)
        self.assertNotEqual(op_q1.idempotency_key, op_q2.idempotency_key)

    def test_a4_custom_idempotency_key_deduplicates_across_quests(self):
        """A4: Caller-provided custom idempotency key explicitly deduplicates across quests."""
        shared_key = "external_payment_ref_9981"
        op1, is_dedup1 = self.ledger.register_mutation(
            quest_id="quest_1",
            step_id="step_pay",
            capability_id="http_api",
            arguments={"amount": 100},
            custom_idempotency_key=shared_key,
        )
        att = self.ledger.begin_attempt(op1.operation_id)
        self.ledger.commit_attempt(op1.operation_id, att.attempt_id, {"tx": "ok"})

        op2, is_dedup2 = self.ledger.register_mutation(
            quest_id="quest_2",
            step_id="step_pay",
            capability_id="http_api",
            arguments={"amount": 100},
            custom_idempotency_key=shared_key,
        )
        self.assertTrue(is_dedup2)
        self.assertEqual(op2.state, MutationState.COMMITTED)

    def test_a5_argument_change_within_same_step_rejects_conflict(self):
        """A5: Reregistering same step with different argument hash raises LedgerError."""
        quest_id = "quest_test_a5"
        op1, _ = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_1",
            capability_id="file_write",
            arguments={"content": "original"},
        )
        # Attempting to register the same logical step with altered arguments
        with self.assertRaises(LedgerError):
            self.ledger.register_mutation(
                quest_id=quest_id,
                step_id="step_1",
                capability_id="file_write",
                arguments={"content": "MODIFIED_CONFLICTING_ARG"},
            )


class TestL14_2_MaxAttemptsPropagation(unittest.TestCase):
    """L14.2-B: max_attempts Must Reach the Actual Ledger."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_attempts_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.registry = build_real_capability_registry()
        self.policy = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy,
            operation_ledger=self.operation_ledger,
            plan_validator=self.validator,
        )

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_b1_non_idempotent_max_attempts_propagates_to_record(self):
        """B1: NON_IDEMPOTENT step with max_attempts=1 propagates into OperationRecord.max_attempts."""
        quest = self.quest_engine.create_quest(title="B1 Quest", goal="Test attempt propagation")
        step = QuestStep(
            step_id="step_1",
            quest_id=quest.quest_id,
            capability_id="file_write",
            action_class=ActionClass.LOCAL_UPDATE,
            intent="Write file with 1 max attempt",
            arguments={"filepath": str(Path(self.temp_dir) / "f.txt"), "content": "hello"},
            max_attempts=1,  # Explicitly derived by planner for non-idempotent
        )
        self.quest_store.save_steps(quest.quest_id, [step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)

        # Run executor
        self.executor.execute(quest.quest_id)

        # Check ledger record
        op_id = f"op_{quest.quest_id}_step_1_file_write"
        op_rec = self.operation_ledger.get_operation(op_id)
        self.assertIsNotNone(op_rec)
        self.assertEqual(op_rec.max_attempts, 1, "OperationRecord must have max_attempts=1, not default 3")

    def test_b2_exhausted_attempts_blocks_second_begin(self):
        """B2: Operation with max_attempts=1 fails and rejects second begin attempt."""
        op_rec, _ = self.operation_ledger.register_mutation(
            quest_id="quest_b2",
            step_id="step_1",
            capability_id="file_write",
            arguments={"filepath": "out.txt"},
            max_attempts=1,
        )
        self.assertEqual(op_rec.max_attempts, 1)

        # Attempt 1 begins and fails (normal safe failure)
        att = self.operation_ledger.begin_attempt(op_rec.operation_id)
        self.operation_ledger.fail_attempt(op_rec.operation_id, att.attempt_id, "disk error", is_uncertain=False)

        # Second attempt must be strictly blocked
        with self.assertRaises(MaxAttemptsExceededError):
            self.operation_ledger.begin_attempt(op_rec.operation_id)

    def test_b3_max_attempts_survives_restart(self):
        """B3: Max attempts remains 1 after store reload/restart."""
        op_id = "op_b3_step_1_file_write"
        self.operation_ledger.register_mutation(
            quest_id="quest_b3",
            step_id="step_1",
            capability_id="file_write",
            arguments={"filepath": "out.txt"},
            max_attempts=1,
            operation_id=op_id,
        )
        self.operation_store.close()

        # Reopen store in fresh instance
        reopened_store = OperationStore(self.ledger_db)
        reopened_ledger = OperationLedger(reopened_store)
        op_rec = reopened_ledger.get_operation(op_id)
        self.assertIsNotNone(op_rec)
        self.assertEqual(op_rec.max_attempts, 1)
        reopened_store.close()


class TestL14_2_DatabaseLevelConcurrencyCAS(unittest.TestCase):
    """L14.2-C: Database-Level Concurrency, Not Only Python Locks."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_cas_")
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_c1_concurrent_begin_attempt_race_50_iterations(self):
        """C1: Real file-backed SQLite database with 50 iterations of competing connections racing on begin_attempt."""
        for iteration in range(50):
            db_file = Path(self.temp_dir) / f"race_{iteration}.db"
            store1 = OperationStore(db_file)
            store2 = OperationStore(db_file)
            ledger1 = OperationLedger(store1)
            ledger2 = OperationLedger(store2)

            op_id = f"op_race_{iteration}"
            ledger1.register_mutation(
                quest_id=f"quest_{iteration}",
                step_id="step_1",
                capability_id="file_write",
                arguments={"iteration": iteration},
                max_attempts=1,
                operation_id=op_id,
            )

            barrier = threading.Barrier(2)
            results = []
            errors = []

            def worker(ledger_instance):
                try:
                    barrier.wait(timeout=3.0)
                    att = ledger_instance.begin_attempt(op_id)
                    results.append(att)
                except Exception as e:
                    errors.append(e)

            t1 = threading.Thread(target=worker, args=(ledger1,))
            t2 = threading.Thread(target=worker, args=(ledger2,))
            t1.start()
            t2.start()
            t1.join(timeout=5.0)
            t2.join(timeout=5.0)

            # Exactly one worker must win!
            self.assertEqual(
                len(results), 1,
                f"Iteration {iteration}: Exactly one worker must win the attempt CAS race! Won: {len(results)}"
            )
            self.assertEqual(
                len(errors), 1,
                f"Iteration {iteration}: Exactly one worker must lose with a typed conflict error! Errors: {errors}"
            )
            # Losing worker must get a typed domain conflict (not raw sqlite OperationalError)
            self.assertTrue(
                isinstance(errors[0], (ConcurrentAttemptConflictError, LedgerError)),
                f"Iteration {iteration}: Losing worker must receive ConcurrentAttemptConflictError, got: {type(errors[0])}"
            )

            # Reopen fresh DB connection and verify exactly 1 attempt row exists with attempt_number=1
            store1.close()
            store2.close()
            verify_store = OperationStore(db_file)
            attempts = verify_store.get_attempts(op_id)
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0].attempt_number, 1)
            op = verify_store.get_operation(op_id)
            self.assertEqual(op.state, MutationState.IN_PROGRESS)
            self.assertEqual(op.current_attempt, 1)
            verify_store.close()


class TestL14_2_TransactionalFaultInjection(unittest.TestCase):
    """L14.2-D: Attempt/Operation Atomicity Fault Injection (Real SQLite Rollback)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_fault_")
        self.ledger_db = Path(self.temp_dir) / "ledger.db"
        self.quest_db = Path(self.temp_dir) / "quest.db"
        self.op_store = OperationStore(self.ledger_db)
        self.quest_store = QuestStore(self.quest_db)

    def tearDown(self):
        self.op_store.close()
        self.quest_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_d1_begin_attempt_mid_transaction_fault_rollback(self):
        """D1: Inject failure after attempt INSERT, before operation UPDATE/commit; verify rollback."""
        op = OperationRecord(
            operation_id="op_d1",
            quest_id="q_d1",
            step_id="s1",
            capability_id="file_write",
            idempotency_key="idem_d1",
            argument_hash="hash_d1",
            state=MutationState.PENDING,
            current_attempt=0,
            max_attempts=3,
        )
        self.op_store.create_operation(op)

        # Inject simulated failure during atomic begin attempt
        attempt = OperationAttempt(
            operation_id="op_d1",
            attempt_number=1,
            state=AttemptState.STARTED,
            started_at=time.time(),
        )

        with self.assertRaises(sqlite3.OperationalError):
            self.op_store.begin_attempt_atomic(
                attempt,
                op.model_copy(update={"state": MutationState.IN_PROGRESS, "current_attempt": 1}),
                _fault_injection="after_attempt_insert",
            )

        # Close connections and reopen from disk to verify ZERO partial writes survived
        self.op_store.close()
        reopened = OperationStore(self.ledger_db)
        persisted_op = reopened.get_operation("op_d1")
        self.assertEqual(persisted_op.state, MutationState.PENDING, "Operation must remain in PENDING state after rollback")
        self.assertEqual(persisted_op.current_attempt, 0)
        attempts = reopened.get_attempts("op_d1")
        self.assertEqual(len(attempts), 0, "No attempt record must survive the aborted transaction")
        reopened.close()

    def test_d2_commit_attempt_fault_rollback(self):
        """D2: Inject failure between attempt COMPLETED and operation COMMITTED; verify rollback."""
        op = OperationRecord(
            operation_id="op_d2",
            quest_id="q_d2",
            step_id="s1",
            capability_id="file_write",
            idempotency_key="idem_d2",
            argument_hash="hash_d2",
            state=MutationState.IN_PROGRESS,
            current_attempt=1,
            max_attempts=3,
        )
        self.op_store.create_operation(op)
        attempt = OperationAttempt(
            operation_id="op_d2",
            attempt_number=1,
            state=AttemptState.STARTED,
            started_at=time.time(),
        )
        self.op_store.create_attempt(attempt)

        # Inject fault during commit_attempt_atomic
        with self.assertRaises(sqlite3.OperationalError):
            self.op_store.commit_attempt_atomic(
                attempt.model_copy(update={"state": AttemptState.COMPLETED, "finished_at": time.time()}),
                op.model_copy(update={"state": MutationState.COMMITTED}),
                _fault_injection="before_operation_commit",
            )

        # Reopen from disk
        self.op_store.close()
        reopened = OperationStore(self.ledger_db)
        persisted_op = reopened.get_operation("op_d2")
        self.assertEqual(persisted_op.state, MutationState.IN_PROGRESS)
        persisted_att = reopened.get_attempts("op_d2")[0]
        self.assertEqual(persisted_att.state, AttemptState.STARTED)
        reopened.close()

    def test_d4_quest_transition_fault_rollback(self):
        """D4: Inject failure between Quest status UPDATE and QuestEvent INSERT; verify rollback."""
        quest_engine = QuestEngine(self.quest_store)
        quest = quest_engine.create_quest(title="D4 Quest", goal="Test transition rollback")

        with self.assertRaises(sqlite3.OperationalError):
            self.quest_store.transition_quest_atomic(
                quest_id=quest.quest_id,
                target_status=QuestStatus.PLANNED,
                event_type=QuestEventEnum.PLAN_ATTACHED,
                reason="Testing rollback",
                _fault_injection="after_quest_update",
            )

        # Reopen from disk
        self.quest_store.close()
        reopened = QuestStore(self.quest_db)
        reopened_quest = reopened.get_quest(quest.quest_id)
        self.assertEqual(reopened_quest.status, QuestStatus.CREATED, "Quest must remain in CREATED status")
        events = reopened.get_events(quest.quest_id)
        # Only initial QUEST_CREATED event should exist
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, QuestEventEnum.QUEST_CREATED)
        reopened.close()


class TestL14_2_PlanProvenanceAndTamperFirewall(unittest.TestCase):
    """L14.2-F & G: Plan Provenance Firewall & Semantics Survival."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_firewall_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.registry = build_real_capability_registry()
        self.policy = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy,
            operation_ledger=self.operation_ledger,
            plan_validator=self.validator,
        )
        self.planner = StructuredDAGPlanner(capability_registry=self.registry)

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_f1_tampered_step_argument_blocks_execution(self):
        """F1: Directly modifying a persisted step argument in SQLite causes executor to refuse execution."""
        quest = self.quest_engine.create_quest(title="F1 Quest", goal="Test tamper firewall")
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Write greeting",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="file_write",
                    intent="Write file",
                    arguments={"filepath": str(Path(self.temp_dir) / "f.txt"), "content": "original content"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # TAMPER: Directly alter step_1 arguments in the SQLite database table
        conn = sqlite3.connect(self.quest_db)
        conn.execute(
            "UPDATE quest_steps SET arguments = ? WHERE quest_id = ? AND step_id = ?",
            ('{"filepath": "tampered.txt", "content": "MALICIOUS_TAMPERED"}', quest.quest_id, "step_1")
        )
        conn.commit()
        conn.close()

        # Execute quest: Executor firewall MUST refuse execution and raise ExecutionFirewallError
        with self.assertRaises(ExecutionFirewallError) as ctx:
            self.executor.execute(quest.quest_id)

        self.assertIn("tamper", str(ctx.exception).lower())

        # Physical proof: capability execution count must be ZERO! tampered file must not exist!
        self.assertFalse(os.path.exists("tampered.txt"))
        self.assertFalse(os.path.exists(str(Path(self.temp_dir) / "f.txt")))

    def test_f2_tampered_capability_id_blocks_execution(self):
        """F2: Directly modifying capability_id in SQLite blocks execution."""
        quest = self.quest_engine.create_quest(title="F2 Quest", goal="Test cap tamper")
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Read something",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="safe_math",
                    intent="Calculate",
                    arguments={"expression": "2 + 2"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Tamper capability_id in SQLite
        conn = sqlite3.connect(self.quest_db)
        conn.execute(
            "UPDATE quest_steps SET capability_id = 'system_diagnostics' WHERE quest_id = ?",
            (quest.quest_id,)
        )
        conn.commit()
        conn.close()

        with self.assertRaises(ExecutionFirewallError):
            self.executor.execute(quest.quest_id)

    def test_f6_generative_plan_type_preserved_after_restart(self):
        """F6: Reconstructing a generative plan preserves PlanType.GENERATIVE_SYNTHESIZED."""
        quest = self.quest_engine.create_quest(title="F6 Quest", goal="Generative plan")
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Generative goal",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="safe_math",
                    intent="Do math",
                    arguments={"expression": "10 * 5"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Simulate reboot and reconstruct
        self.quest_store.close()
        reopened_store = QuestStore(self.quest_db)
        reopened_quest = reopened_store.get_quest(quest.quest_id)

        reconstructed_plan = self.executor._reconstruct_plan(reopened_quest)
        self.assertEqual(
            reconstructed_plan.plan_type,
            PlanType.GENERATIVE_SYNTHESIZED,
            "Reconstructed plan must retain GENERATIVE_SYNTHESIZED, not revert to TEMPLATE_DERIVED",
        )
        reopened_store.close()


class TestL14_2_ReadOnlyMissingInputPause(unittest.TestCase):
    """L14.2-I: READ_ONLY Missing Input Pause & Resumption Without Duplicate Transitions."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_input_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.registry = build_real_capability_registry()
        self.policy = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy,
            operation_ledger=self.operation_ledger,
            plan_validator=self.validator,
        )
        self.planner = StructuredDAGPlanner(capability_registry=self.registry)

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_i1_read_only_missing_input_pauses_cleanly_without_duplicate_transition(self):
        """I1: READ_ONLY step with missing $inputs param pauses cleanly and resumes without InvalidStateTransitionError."""
        quest = self.quest_engine.create_quest(title="I1 Quest", goal="Calculate user formula")
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Math with input",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="safe_math",
                    intent="Evaluate user expression",
                    arguments={"expression": "$inputs.math_expr"},
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Execute without providing math_expr: must pause cleanly, NOT throw InvalidStateTransitionError
        summary = self.executor.execute(quest.quest_id, inputs={})
        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_INPUT)

        # Verify step status in store
        step = self.quest_engine.get_step(quest.quest_id, "step_1")
        self.assertEqual(step.status, StepStatus.PAUSED)

        # Resume with provided user input
        resumed = self.executor.resume(quest.quest_id, user_inputs={"math_expr": "100 / 4"})
        self.assertEqual(resumed.final_status, QuestStatus.AWAITING_VERIFICATION)
        self.assertEqual(resumed.completed_steps, 1)

        completed_step = self.quest_engine.get_step(quest.quest_id, "step_1")
        self.assertEqual(completed_step.status, StepStatus.COMPLETED)
        self.assertEqual(completed_step.execution_receipt["data"]["result"], 25.0)


class TestL14_2_ActiveCancellation(unittest.TestCase):
    """L14.2-K: Active Cancellation While Quest is RUNNING."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_cancel_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.registry = build_real_capability_registry()
        self.policy = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy,
            operation_ledger=self.operation_ledger,
            plan_validator=self.validator,
        )
        self.planner = StructuredDAGPlanner(capability_registry=self.registry)

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_k1_cancel_running_quest_without_lease_error(self):
        """K1: Operator cancel while Quest is RUNNING signals cancellation without QuestAlreadyRunningError."""
        quest = self.quest_engine.create_quest(title="K1 Quest", goal="Slow multi-step quest")
        
        # Register a slow capability to ensure quest is actively running when cancel() is called
        started_event = threading.Event()
        can_finish_event = threading.Event()

        def slow_step(**kwargs):
            started_event.set()
            can_finish_event.wait(timeout=5.0)
            return {"status": "finished"}

        from omni_engine.contracts.capability import CapabilitySpec
        spec = CapabilitySpec(
            id="slow_cap",
            name="Slow Capability",
            domain="os",
            description="Blocks until released",
            action_class=ActionClass.READ_ONLY,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"status": {"type": "string"}}},
            minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        )
        self.registry.register(spec, slow_step)

        plan = Plan(
            quest_id=quest.quest_id,
            goal="Run slow steps",
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=[
                PlanStep(step_id="step_1", capability_id="slow_cap", intent="Step 1"),
                PlanStep(step_id="step_2", capability_id="safe_math", intent="Step 2", arguments={"expression": "1+1"}, dependencies=["step_1"]),
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        # Run execute in background thread
        exec_thread = threading.Thread(target=self.executor.execute, args=(quest.quest_id,))
        exec_thread.start()

        # Wait until step 1 has actually started executing
        self.assertTrue(started_event.wait(timeout=3.0))

        # Call cancel while RUNNING! Must NOT raise QuestAlreadyRunningError!
        try:
            cancel_summary = self.executor.cancel(quest.quest_id, reason="Operator abort")
            self.assertEqual(cancel_summary.final_status, QuestStatus.CANCELLED)
        finally:
            can_finish_event.set()
            exec_thread.join(timeout=5.0)

        # Step 2 must be CANCELLED, NOT executed
        step_2 = self.quest_engine.get_step(quest.quest_id, "step_2")
        self.assertEqual(step_2.status, StepStatus.CANCELLED)
        q = self.quest_engine.get_quest(quest.quest_id)
        self.assertEqual(q.status, QuestStatus.CANCELLED)


class TestL14_2_DurableReconciliationHistory(unittest.TestCase):
    """L14.2-L: UNKNOWN_COMMIT Reconciliation Audit History."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_rec_")
        self.ledger_db = Path(self.temp_dir) / "ledger.db"
        self.store = OperationStore(self.ledger_db)
        self.ledger = OperationLedger(self.store)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_l1_reconciliation_audit_record_persisted(self):
        """L1: Reconciling UNKNOWN_COMMIT operation creates durable audit record in operation_reconciliations."""
        op_id = "op_rec_test_1"
        self.ledger.register_mutation(
            quest_id="quest_rec",
            step_id="step_1",
            capability_id="file_write",
            arguments={"filepath": "target.txt"},
            operation_id=op_id,
        )
        att = self.ledger.begin_attempt(op_id)
        self.ledger.fail_attempt(op_id, att.attempt_id, "network dropped", is_uncertain=True)

        op = self.ledger.get_operation(op_id)
        self.assertEqual(op.state, MutationState.UNKNOWN_COMMIT)

        # Reconcile with verified evidence
        reconciled_op = self.ledger.reconcile_operation(
            operation_id=op_id,
            is_verified_committed=True,
            evidence={"hash_match": True, "file_size": 1024},
            reconciliation_note="Verified file exists on disk with expected hash",
        )
        self.assertEqual(reconciled_op.state, MutationState.COMMITTED)

        # Reopen from disk to prove durable reconciliation audit record exists
        self.store.close()
        reopened_store = OperationStore(self.ledger_db)
        reconciliations = reopened_store.get_reconciliations(op_id)
        self.assertEqual(len(reconciliations), 1, "Must have exactly 1 durable reconciliation record")
        rec = reconciliations[0]
        self.assertEqual(rec["operation_id"], op_id)
        self.assertEqual(rec["prior_state"], MutationState.UNKNOWN_COMMIT.value)
        self.assertEqual(rec["reconciled_state"], MutationState.COMMITTED.value)
        self.assertEqual(rec["evidence"]["file_size"], 1024)
        reopened_store.close()


class TestL14_2_AttemptStateConsistency(unittest.TestCase):
    """L14.2-E: Attempt State Consistency & Zombie Thread Defense."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_consistency_")
        self.ledger_db = Path(self.temp_dir) / "ledger.db"
        self.store = OperationStore(self.ledger_db)
        self.ledger = OperationLedger(self.store)

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_e1_wrong_operation_attempt_rejected(self):
        """E1: An attempt belonging to Operation A cannot commit Operation B."""
        op_a, _ = self.ledger.register_mutation(quest_id="q1", step_id="s1", capability_id="c1", arguments={})
        op_b, _ = self.ledger.register_mutation(quest_id="q1", step_id="s2", capability_id="c2", arguments={})

        att_a = self.ledger.begin_attempt(op_a.operation_id)
        self.ledger.begin_attempt(op_b.operation_id)

        # Attempting to commit op_b using att_a must raise StaleAttemptError / LedgerError
        from omni_engine.contracts.operation import StaleAttemptError
        with self.assertRaises((StaleAttemptError, LedgerError)):
            self.ledger.commit_attempt(op_b.operation_id, att_a.attempt_id, {"receipt": 1})

    def test_e2_completed_attempt_cannot_commit_twice(self):
        """E2: A completed attempt cannot be committed a second time."""
        op, _ = self.ledger.register_mutation(quest_id="q1", step_id="s1", capability_id="c1", arguments={})
        att = self.ledger.begin_attempt(op.operation_id)
        self.ledger.commit_attempt(op.operation_id, att.attempt_id, {"done": True})

        from omni_engine.contracts.operation import StaleAttemptError
        with self.assertRaises((StaleAttemptError, LedgerError)):
            self.ledger.commit_attempt(op.operation_id, att.attempt_id, {"done": True})

    def test_e3_stale_attempt_cannot_overwrite_newer_state(self):
        """E3: A delayed zombie attempt (attempt 1) cannot commit when operation is already at attempt 2."""
        op, _ = self.ledger.register_mutation(quest_id="q1", step_id="s1", capability_id="c1", arguments={}, max_attempts=3)
        att1 = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(op.operation_id, att1.attempt_id, "transient error", is_uncertain=False)

        # Begin attempt 2
        att2 = self.ledger.begin_attempt(op.operation_id)

        # Zombie thread for att1 wakes up and tries to commit
        from omni_engine.contracts.operation import StaleAttemptError
        with self.assertRaises((StaleAttemptError, LedgerError)):
            self.ledger.commit_attempt(op.operation_id, att1.attempt_id, {"zombie": "late"})

    def test_e4_unknown_commit_cannot_be_bypassed_by_stale_attempt(self):
        """E4: An operation in UNKNOWN_COMMIT rejects delayed commit_attempt without reconciliation."""
        op, _ = self.ledger.register_mutation(quest_id="q1", step_id="s1", capability_id="c1", arguments={})
        att = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(op.operation_id, att.attempt_id, "timeout", is_uncertain=True)

        from omni_engine.contracts.operation import OperationCommitUncertainError
        with self.assertRaises(OperationCommitUncertainError):
            self.ledger.commit_attempt(op.operation_id, att.attempt_id, {"late": True})


class TestL14_2_PlanSemanticsRoundTrip(unittest.TestCase):
    """L14.2-G: Exact Plan Semantics Must Survive Persistence and Reconstruction."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_semantics_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.store = QuestStore(self.quest_db)
        self.engine = QuestEngine(self.store)
        self.registry = build_real_capability_registry()
        self.planner = StructuredDAGPlanner(capability_registry=self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.engine,
            capability_registry=self.registry,
            policy_engine=PolicyEngine(),
            operation_ledger=OperationLedger(OperationStore(Path(self.temp_dir) / "op.db")),
            plan_validator=DeterministicPlanValidator(self.registry),
        )

    def tearDown(self):
        self.store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_g1_exact_plan_semantics_round_trip(self):
        """G1: Plan fields survive persist -> close DB -> reload -> reconstruct."""
        quest = self.engine.create_quest(title="Semantics Quest", goal="Preserve all semantics")
        original_plan = Plan(
            plan_id="plan_fixed_id_1234",
            quest_id=quest.quest_id,
            goal="Preserve all semantics",
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            skill_id="custom_skill_xyz",
            timeout_budget_s=750.0,
            metadata={"planner_version": "2.1.0"},
            steps=[
                PlanStep(
                    step_id="step_alpha",
                    capability_id="safe_math",
                    intent="Calculate baseline",
                    arguments={"expression": "100 - 25"},
                    dependencies=[],
                    timeout_s=45.0,
                    max_attempts=1,
                    can_fail_silently=False,
                    metadata={"step_category": "math_primary"},
                )
            ],
        )
        self.planner.attach_to_quest(self.engine, original_plan)

        # Close database completely to guarantee cold restart from disk
        self.store.close()
        reopened_store = QuestStore(self.quest_db)
        reopened_quest = reopened_store.get_quest(quest.quest_id)

        reconstructed = self.executor._reconstruct_plan(reopened_quest)

        # Verify semantic identity
        self.assertEqual(reconstructed.plan_id, original_plan.plan_id)
        self.assertEqual(reconstructed.plan_type, PlanType.GENERATIVE_SYNTHESIZED)
        self.assertEqual(reconstructed.skill_id, "custom_skill_xyz")
        self.assertEqual(reconstructed.timeout_budget_s, 750.0)
        self.assertEqual(reconstructed.steps[0].step_id, "step_alpha")
        self.assertEqual(reconstructed.steps[0].timeout_s, 45.0)
        self.assertEqual(reconstructed.steps[0].max_attempts, 1)
        self.assertEqual(reconstructed.steps[0].metadata.get("step_category"), "math_primary")
        reopened_store.close()


class TestL14_2_NonDecorativeFields(unittest.TestCase):
    """L14.2-H: No Decorative Contract Fields — Rejection of Unsupported can_fail_silently."""

    def test_h1_can_fail_silently_rejected_by_validator(self):
        """H1: Validator strictly rejects can_fail_silently=True with explicit L16 replanner deferral message."""
        registry = build_real_capability_registry()
        validator = DeterministicPlanValidator(registry)

        plan = Plan(
            quest_id="q_h1",
            goal="Test unsupported field rejection",
            steps=[
                PlanStep(
                    step_id="step_1",
                    capability_id="safe_math",
                    intent="Step claiming silent failure",
                    arguments={"expression": "1 + 1"},
                    can_fail_silently=True,  # Unsupported feature in L14.2!
                )
            ],
        )
        report = validator.validate(plan)
        self.assertFalse(report.is_valid, "Validator must reject can_fail_silently=True")
        error_text = " ".join(report.errors).lower()
        self.assertTrue(
            "can_fail_silently" in error_text or "l16" in error_text,
            f"Expected diagnostic citing can_fail_silently or L16 deferral, got: {report.errors}"
        )


class TestL14_2_TruthfulTimeoutHierarchy(unittest.TestCase):
    """L14.2-J: Truthful Timeout Hierarchy & In-Flight Dispatch Protection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_test_l14_2_timeout_")
        self.quest_db = Path(self.temp_dir) / "quests.db"
        self.ledger_db = Path(self.temp_dir) / "ledger.db"

        self.quest_store = QuestStore(self.quest_db)
        self.quest_engine = QuestEngine(self.quest_store)
        self.operation_store = OperationStore(self.ledger_db)
        self.operation_ledger = OperationLedger(self.operation_store)

        self.registry = build_real_capability_registry()
        self.policy = PolicyEngine()
        self.validator = DeterministicPlanValidator(self.registry)
        self.executor = DeterministicDAGExecutor(
            quest_engine=self.quest_engine,
            capability_registry=self.registry,
            policy_engine=self.policy,
            operation_ledger=self.operation_ledger,
            plan_validator=self.validator,
        )
        self.planner = StructuredDAGPlanner(capability_registry=self.registry)

    def tearDown(self):
        self.quest_store.close()
        self.operation_store.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_j2_mutation_timeout_transitions_to_unknown_commit(self):
        """J2: A mutating capability that times out after dispatch transitions to UNKNOWN_COMMIT and pauses quest."""
        from omni_engine.contracts.capability import CapabilitySpec

        def hanging_mutation(**kwargs):
            time.sleep(2.0)
            return {"written": True}

        spec = CapabilitySpec(
            id="hanging_mut",
            name="Hanging Mutation",
            domain="os",
            description="Simulates post-dispatch hang",
            action_class=ActionClass.LOCAL_UPDATE,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
            minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.registry.register(spec, hanging_mutation)

        quest = self.quest_engine.create_quest(
            title="J2 Quest",
            goal="Test mutation timeout",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        plan = Plan(
            quest_id=quest.quest_id,
            goal="Execute hanging mutation",
            steps=[
                PlanStep(
                    step_id="step_mut",
                    capability_id="hanging_mut",
                    intent="Hang step",
                    timeout_s=0.5,  # 500ms timeout
                )
            ],
        )
        self.planner.attach_to_quest(self.quest_engine, plan)

        summary = self.executor.execute(quest.quest_id)
        self.assertEqual(summary.final_status, QuestStatus.PAUSED_FOR_RECONCILIATION)
        op = self.operation_ledger.get_operation(f"op_{quest.quest_id}_step_mut_hanging_mut")
        self.assertIsNotNone(op)
        self.assertEqual(op.state, MutationState.UNKNOWN_COMMIT)


if __name__ == "__main__":
    unittest.main()

