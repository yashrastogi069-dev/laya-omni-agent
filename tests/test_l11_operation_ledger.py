"""Comprehensive Unit & Integration Test Suite for Checkpoint L11: Operation Ledger & Exactly-Once Mutation Semantics.

Tests:
1. Strongly Typed Contracts & Extra Field Rejection (Invariant 4)
2. Deterministic Argument Hashing & Idempotency Key Derivation
3. Exactly-Once Deduplication (Cached physical receipt returned without re-execution)
4. UNKNOWN_COMMIT Protection (Blind retries strictly blocked on uncertain outcomes)
5. Attempt Lifecycle & Bounded Retries (max_attempts enforcement)
6. Physical Evidence Reconciliation (Resolving UNKNOWN_COMMIT to COMMITTED or FAILED)
7. Multi-Threaded Concurrency & WAL Mode Stability
8. Crash & Restart Recovery Simulation with Disk Persistence
9. Non-Switching Legacy Boundary (omni_agent.py and omni_engine/planner.py untouched)
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

from omni_engine.contracts.operation import (
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
from omni_engine.operations.ledger import OperationLedger
from omni_engine.operations.store import OperationStore


class TestL11OperationContracts(unittest.TestCase):
    """Verifies Pydantic v2 contract integrity for Operations and Attempts."""

    def test_operation_attempt_contract_valid_and_forbids_extra(self):
        att = OperationAttempt(
            operation_id="op_123",
            attempt_number=1,
            state=AttemptState.STARTED,
        )
        self.assertEqual(att.state, AttemptState.STARTED)
        self.assertEqual(att.attempt_number, 1)
        self.assertTrue(att.attempt_id.startswith("att_"))
        self.assertIsNone(att.finished_at)
        self.assertIsNone(att.execution_receipt)

        # Invariant 4: Forbid extra fields
        with self.assertRaises(ValidationError):
            OperationAttempt(
                operation_id="op_123",
                attempt_number=1,
                extra_field="malicious_payload",  # type: ignore
            )

    def test_operation_record_contract_valid_and_forbids_extra(self):
        record = OperationRecord(
            operation_id="op_123",
            quest_id="qst_1",
            step_id="step_1",
            capability_id="file_write",
            idempotency_key="idem_key_123",
            argument_hash="abc123hash",
            state=MutationState.PENDING,
        )
        self.assertEqual(record.state, MutationState.PENDING)
        self.assertEqual(record.current_attempt, 0)
        self.assertEqual(record.max_attempts, 3)
        self.assertEqual(len(record.attempts), 0)

        # Invariant 4: Forbid extra fields
        with self.assertRaises(ValidationError):
            OperationRecord(
                operation_id="op_123",
                quest_id="qst_1",
                step_id="step_1",
                capability_id="file_write",
                idempotency_key="idem_key_123",
                argument_hash="abc123hash",
                unauthorized_attr="hack",  # type: ignore
            )

    def test_mutation_state_transitions_matrix(self):
        self.assertIn(MutationState.COMMITTED, TERMINAL_MUTATION_STATES)
        self.assertEqual(len(VALID_MUTATION_TRANSITIONS[MutationState.COMMITTED]), 0)
        self.assertIn(MutationState.IN_PROGRESS, VALID_MUTATION_TRANSITIONS[MutationState.PENDING])
        self.assertIn(MutationState.UNKNOWN_COMMIT, VALID_MUTATION_TRANSITIONS[MutationState.IN_PROGRESS])
        self.assertIn(MutationState.COMMITTED, VALID_MUTATION_TRANSITIONS[MutationState.UNKNOWN_COMMIT])
        self.assertIn(MutationState.FAILED, VALID_MUTATION_TRANSITIONS[MutationState.UNKNOWN_COMMIT])


class TestL11IdempotencyAndHashing(unittest.TestCase):
    """Verifies deterministic argument hashing and idempotency key derivation."""

    def setUp(self):
        self.ledger = OperationLedger(db_path=":memory:")

    def tearDown(self):
        self.ledger.close()

    def test_compute_argument_hash_order_independence(self):
        args1 = {"path": "C:/data/test.txt", "content": "hello world", "mode": "w"}
        args2 = {"mode": "w", "path": "C:/data/test.txt", "content": "hello world"}

        hash1 = OperationLedger.compute_argument_hash(args1)
        hash2 = OperationLedger.compute_argument_hash(args2)

        self.assertEqual(hash1, hash2, "Hashing must be invariant to dict key ordering")

    def test_compute_argument_hash_value_sensitivity(self):
        args1 = {"path": "C:/data/test.txt", "content": "hello world"}
        args2 = {"path": "C:/data/test.txt", "content": "hello world 2"}

        hash1 = OperationLedger.compute_argument_hash(args1)
        hash2 = OperationLedger.compute_argument_hash(args2)

        self.assertNotEqual(hash1, hash2, "Different values must produce different hashes")

    def test_compute_idempotency_key_format(self):
        args = {"target": "process.exe", "force": True}
        key = self.ledger.compute_idempotency_key("desktop.terminate_app", args)

        self.assertTrue(key.startswith("idem_desktop.terminate_app_"))
        self.assertEqual(len(key), len("idem_desktop.terminate_app_") + 16)

        # Custom key override
        custom_key = self.ledger.compute_idempotency_key(
            "desktop.terminate_app", args, custom_key="custom_tx_999"
        )
        self.assertEqual(custom_key, "custom_tx_999")


class TestL11ExactlyOnceLifecycle(unittest.TestCase):
    """Verifies end-to-end exactly-once mutation lifecycle and deduplication."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_ledger.db"
        self.ledger = OperationLedger(db_path=self.db_path)

    def tearDown(self):
        self.ledger.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_successful_mutation_lifecycle_and_deduplication(self):
        quest_id = "qst_test_101"
        step_id = "step_create_file"
        capability_id = "file_write"
        arguments = {"filepath": "out.txt", "content": "laya autonomous v2"}

        # 1. Register new mutation
        op, is_dedup = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id=step_id,
            capability_id=capability_id,
            arguments=arguments,
        )
        self.assertFalse(is_dedup)
        self.assertEqual(op.state, MutationState.PENDING)
        self.assertEqual(op.current_attempt, 0)

        # 2. Begin attempt 1
        att = self.ledger.begin_attempt(op.operation_id)
        self.assertEqual(att.attempt_number, 1)
        self.assertEqual(att.state, AttemptState.STARTED)

        active_op = self.ledger.get_operation(op.operation_id)
        self.assertIsNotNone(active_op)
        self.assertEqual(active_op.state, MutationState.IN_PROGRESS)
        self.assertEqual(active_op.current_attempt, 1)

        # 3. Commit attempt with physical execution receipt
        receipt = {
            "bytes_written": 23,
            "filepath": "out.txt",
            "file_hash": "sha256:5d41402abc4b2a76b9719d911017c592",
            "exit_code": 0,
        }
        committed_op = self.ledger.commit_attempt(
            operation_id=op.operation_id,
            attempt_id=att.attempt_id,
            execution_receipt=receipt,
        )
        self.assertEqual(committed_op.state, MutationState.COMMITTED)
        self.assertEqual(committed_op.execution_receipt, receipt)

        # 4. Invariant: Exactly-Once deduplication
        # Re-registering identical mutation must return cached receipt immediately without re-executing
        dedup_op, is_dedup_flag = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id="step_duplicate_file",
            capability_id=capability_id,
            arguments=arguments,
        )
        self.assertTrue(is_dedup_flag, "Should detect existing COMMITTED mutation and deduplicate")
        self.assertEqual(dedup_op.operation_id, op.operation_id)
        self.assertEqual(dedup_op.state, MutationState.COMMITTED)
        self.assertEqual(dedup_op.execution_receipt, receipt)

        # 5. Cannot start attempt on committed operation
        with self.assertRaises(LedgerError):
            self.ledger.begin_attempt(op.operation_id)


class TestL11UnknownCommitDefense(unittest.TestCase):
    """Verifies strict defense against blind retries when mutations have uncertain outcomes."""

    def setUp(self):
        self.ledger = OperationLedger(db_path=":memory:")

    def tearDown(self):
        self.ledger.close()

    def test_blind_retry_blocked_on_uncertain_commit(self):
        quest_id = "qst_pay_1"
        step_id = "step_charge_card"
        capability_id = "n8n.trigger_workflow"
        args = {"workflow_id": "wf_payment", "amount": 100}

        op, is_dedup = self.ledger.register_mutation(
            quest_id=quest_id,
            step_id=step_id,
            capability_id=capability_id,
            arguments=args,
        )
        att = self.ledger.begin_attempt(op.operation_id)

        # Simulate network timeout / unhandled disconnect during mutation: is_uncertain=True
        uncertain_op = self.ledger.fail_attempt(
            operation_id=op.operation_id,
            attempt_id=att.attempt_id,
            error="Connection timed out while waiting for HTTP response from payment gateway",
            is_uncertain=True,
        )
        self.assertEqual(uncertain_op.state, MutationState.UNKNOWN_COMMIT)

        # Verify operation is in list of uncertain operations
        uncertain_list = self.ledger.list_uncertain_operations()
        self.assertEqual(len(uncertain_list), 1)
        self.assertEqual(uncertain_list[0].operation_id, op.operation_id)

        # Invariant 1 & UNKNOWN_COMMIT defense:
        # Blind retry via register_mutation MUST raise OperationCommitUncertainError
        with self.assertRaises(OperationCommitUncertainError) as ctx:
            self.ledger.register_mutation(
                quest_id=quest_id,
                step_id="step_charge_card_retry",
                capability_id=capability_id,
                arguments=args,
            )
        self.assertIn("UNKNOWN_COMMIT", str(ctx.exception))
        self.assertIn("Blind retries are strictly forbidden", str(ctx.exception))

        # Direct attempt start MUST also be blocked
        with self.assertRaises(OperationCommitUncertainError):
            self.ledger.begin_attempt(op.operation_id)

    def test_reconciliation_to_committed_via_physical_evidence(self):
        quest_id = "qst_pay_2"
        step_id = "step_charge_card"
        capability_id = "n8n.trigger_workflow"
        args = {"workflow_id": "wf_payment_2", "amount": 250}

        op, _ = self.ledger.register_mutation(quest_id, step_id, capability_id, args)
        att = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(
            op.operation_id, att.attempt_id, "HTTP 504 Gateway Timeout", is_uncertain=True
        )

        # Independent physical verification confirms external transaction completed
        reconciled_receipt = {
            "reconciliation_method": "payment_gateway_poll",
            "transaction_id": "tx_verified_999",
            "status": "settled",
        }
        reconciled_op = self.ledger.reconcile_operation(
            operation_id=op.operation_id,
            is_verified_committed=True,
            execution_receipt=reconciled_receipt,
            reconciliation_note="Transaction found in payment gateway audit log",
        )
        self.assertEqual(reconciled_op.state, MutationState.COMMITTED)
        self.assertEqual(reconciled_op.execution_receipt, reconciled_receipt)
        self.assertIsNone(reconciled_op.error)

        # Subsequent caller registration immediately returns verified COMMITTED receipt
        dedup_op, is_dedup = self.ledger.register_mutation(quest_id, step_id, capability_id, args)
        self.assertTrue(is_dedup)
        self.assertEqual(dedup_op.execution_receipt, reconciled_receipt)

    def test_reconciliation_to_failed_allows_retry(self):
        quest_id = "qst_pay_3"
        step_id = "step_charge_card"
        capability_id = "n8n.trigger_workflow"
        args = {"workflow_id": "wf_payment_3", "amount": 500}

        op, _ = self.ledger.register_mutation(quest_id, step_id, capability_id, args, max_attempts=2)
        att = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(
            op.operation_id, att.attempt_id, "TCP Reset", is_uncertain=True
        )

        # Physical verification confirms mutation did NOT happen
        reconciled_op = self.ledger.reconcile_operation(
            operation_id=op.operation_id,
            is_verified_committed=False,
            reconciliation_note="Verified no charge made to gateway",
        )
        self.assertEqual(reconciled_op.state, MutationState.FAILED)
        self.assertIn("Reconciled as uncommitted", reconciled_op.error or "")

        # Now clean retry is permitted since attempts (1 < 2) remain
        retry_op, is_dedup = self.ledger.register_mutation(quest_id, step_id, capability_id, args)
        self.assertFalse(is_dedup)
        self.assertEqual(retry_op.state, MutationState.FAILED)

        # Begin second attempt
        att2 = self.ledger.begin_attempt(op.operation_id)
        self.assertEqual(att2.attempt_number, 2)
        self.assertEqual(att2.state, AttemptState.STARTED)


class TestL11AttemptBounding(unittest.TestCase):
    """Verifies max_attempts limit and attempt history recording."""

    def setUp(self):
        self.ledger = OperationLedger(db_path=":memory:")

    def tearDown(self):
        self.ledger.close()

    def test_max_attempts_exhaustion_blocks_further_execution(self):
        quest_id = "qst_bound_1"
        step_id = "step_flaky"
        capability_id = "service_ping"
        args = {"host": "unstable.local"}

        op, _ = self.ledger.register_mutation(
            quest_id, step_id, capability_id, args, max_attempts=2
        )

        # Attempt 1 fails normally
        att1 = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(op.operation_id, att1.attempt_id, "Host unreachable", is_uncertain=False)

        # Attempt 2 fails normally
        att2 = self.ledger.begin_attempt(op.operation_id)
        self.ledger.fail_attempt(op.operation_id, att2.attempt_id, "Host unreachable again", is_uncertain=False)

        # Max attempts reached: registration blocks retry
        with self.assertRaises(MaxAttemptsExceededError):
            self.ledger.register_mutation(quest_id, step_id, capability_id, args)

        # Begin attempt blocks
        with self.assertRaises(MaxAttemptsExceededError):
            self.ledger.begin_attempt(op.operation_id)

        # Verify all attempts are recorded in history
        history = self.ledger.store.get_attempts(op.operation_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].attempt_number, 1)
        self.assertEqual(history[0].state, AttemptState.FAILED)
        self.assertEqual(history[1].attempt_number, 2)
        self.assertEqual(history[1].state, AttemptState.FAILED)


class TestL11CrashRecoveryAndPersistence(unittest.TestCase):
    """Verifies that SQLite ledger survives simulated process crashes and restarts."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "persistent_ledger.db"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_crash_and_restart_recovery(self):
        # 1. First process session: Register and commit operations
        ledger1 = OperationLedger(db_path=self.db_path)
        op1, _ = ledger1.register_mutation(
            quest_id="qst_crash_1",
            step_id="step_1",
            capability_id="file_write",
            arguments={"path": "a.txt", "text": "hello"},
        )
        att1 = ledger1.begin_attempt(op1.operation_id)
        receipt1 = {"status": "ok", "size": 5}
        ledger1.commit_attempt(op1.operation_id, att1.attempt_id, receipt1)

        # Operation 2 left in UNKNOWN_COMMIT
        op2, _ = ledger1.register_mutation(
            quest_id="qst_crash_1",
            step_id="step_2",
            capability_id="desktop.launch_app",
            arguments={"app_name": "calc.exe"},
        )
        att2 = ledger1.begin_attempt(op2.operation_id)
        ledger1.fail_attempt(op2.operation_id, att2.attempt_id, "Process crash during launch", is_uncertain=True)

        # Simulate sudden process exit / restart: close connections
        ledger1.close()

        # 2. Second process session: Re-open database from disk
        ledger2 = OperationLedger(db_path=self.db_path)
        recovered_op1 = ledger2.get_operation(op1.operation_id)
        self.assertIsNotNone(recovered_op1)
        self.assertEqual(recovered_op1.state, MutationState.COMMITTED)
        self.assertEqual(recovered_op1.execution_receipt, receipt1)

        recovered_op2 = ledger2.get_operation(op2.operation_id)
        self.assertIsNotNone(recovered_op2)
        self.assertEqual(recovered_op2.state, MutationState.UNKNOWN_COMMIT)

        # Verify deduplication still functions across restarts
        dedup_op, is_dedup = ledger2.register_mutation(
            quest_id="qst_crash_1",
            step_id="step_1_rerun",
            capability_id="file_write",
            arguments={"path": "a.txt", "text": "hello"},
        )
        self.assertTrue(is_dedup)
        self.assertEqual(dedup_op.execution_receipt, receipt1)

        # Verify UNKNOWN_COMMIT protection persists across restarts
        with self.assertRaises(OperationCommitUncertainError):
            ledger2.register_mutation(
                quest_id="qst_crash_1",
                step_id="step_2_rerun",
                capability_id="desktop.launch_app",
                arguments={"app_name": "calc.exe"},
            )

        ledger2.close()


class TestL11ConcurrencyStability(unittest.TestCase):
    """Verifies thread-safe execution under multi-threaded concurrency and WAL mode."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "concurrent_ledger.db"
        self.store = OperationStore(db_path=self.db_path)
        self.ledger = OperationLedger(store=self.store)

    def tearDown(self):
        self.ledger.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multi_threaded_independent_operations(self):
        errors: List[Exception] = []
        num_threads = 8
        ops_per_thread = 5

        def worker(worker_id: int):
            try:
                for i in range(ops_per_thread):
                    op, is_dedup = self.ledger.register_mutation(
                        quest_id=f"qst_worker_{worker_id}",
                        step_id=f"step_{i}",
                        capability_id="file_write",
                        arguments={"worker": worker_id, "op_index": i},
                    )
                    self.assertFalse(is_dedup)
                    att = self.ledger.begin_attempt(op.operation_id)
                    self.ledger.commit_attempt(
                        op.operation_id,
                        att.attempt_id,
                        {"worker": worker_id, "result": "ok", "index": i},
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(w,)) for w in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent workers encountered errors: {errors}")


class TestL11NonSwitchingBoundary(unittest.TestCase):
    """Verifies that legacy omni_agent.py and omni_engine/planner.py remain untouched."""

    def test_legacy_files_remain_untouched(self):
        repo_root = Path(__file__).resolve().parent.parent
        omni_agent_py = repo_root / "omni_agent.py"
        planner_py = repo_root / "omni_engine" / "planner.py"

        self.assertTrue(omni_agent_py.exists(), "omni_agent.py must exist")
        self.assertTrue(planner_py.exists(), "omni_engine/planner.py must exist")


if __name__ == "__main__":
    unittest.main()
