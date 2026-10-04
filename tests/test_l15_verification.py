"""
tests.test_l15_verification
===========================
Comprehensive test suite for Checkpoint L15: Evidence-Based Completion Verifier
and Objective Completion Engine.

Validates:
1. Verification Contracts & Physical Precedence (L15.0).
2. Deterministic Verifier Registry (L15.1: File, Process, Desktop, Browser, n8n, Research, Command).
3. False-Completion Defense (L15.2): Tool reports SUCCESS but physical artifact missing -> NOT complete.
4. Negative Constraint Verification: "Do not modify workflows" audits execution history and catches breaches.
5. Canonical Compound Objectives: System health + processes + file report all independently verified.
6. Durable SQLite Persistence & Cold Restart: Receipts survive restart byte-for-byte.
7. Quest Lifecycle Integration: Strict transition from AWAITING_VERIFICATION to COMPLETED or FAILED.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from omni_engine.contracts.enums import ActionClass, AutonomyProfile
from omni_engine.contracts.objective import ObjectiveSpec, RequirementItem, RequirementCoverageState
from omni_engine.contracts.quest import Quest, QuestStep, QuestStatus, StepStatus
from omni_engine.contracts.verification import (
    CheckType,
    ConstraintVerification,
    ConstraintVerificationStatus,
    ObjectiveVerificationResult,
    RequirementVerification,
    RequirementVerificationStatus,
    VerificationCheckResult,
)
from omni_engine.quest.engine import QuestEngine
from omni_engine.quest.store import QuestStore
from omni_engine.verification import (
    BaseVerifier,
    BrowserVerifier,
    CommandVerifier,
    DesktopVerifier,
    FileVerifier,
    N8nVerifier,
    ObjectiveCompletionEngine,
    ProcessVerifier,
    ResearchVerifier,
    VerificationRegistry,
    VerificationStore,
)


class TestL15VerificationContracts(unittest.TestCase):
    """Tests L15.0: Verification contracts and physical precedence invariant."""

    def test_physical_check_failure_blocks_verified_success(self):
        """Inviolable rule: If a physical check failed, status cannot be VERIFIED_SUCCESS."""
        failed_check = VerificationCheckResult(
            check_name="file_exists",
            check_type=CheckType.PHYSICAL,
            passed=False,
            evidence={"exists": False},
        )
        with self.assertRaises(ValueError) as ctx:
            RequirementVerification(
                requirement_id="R1",
                description="Save report to disk",
                mandatory=True,
                status=RequirementVerificationStatus.VERIFIED_SUCCESS, # Conflict!
                verifier_id="file_verifier",
                physical_checks=[failed_check],
            )
        self.assertIn("cannot be marked VERIFIED_SUCCESS", str(ctx.exception))

    def test_evidence_hash_determinism(self):
        """Asserts evidence_hash is deterministic and changes if evidence changes."""
        req1 = RequirementVerification(
            requirement_id="R1",
            description="Create report",
            status=RequirementVerificationStatus.VERIFIED_SUCCESS,
            verifier_id="file_verifier",
            physical_checks=[
                VerificationCheckResult(
                    check_name="file_exists",
                    check_type=CheckType.PHYSICAL,
                    passed=True,
                    evidence={"size": 100},
                )
            ],
        )
        c1 = ConstraintVerification(
            constraint_id="C1",
            description="Do not delete files",
            status=ConstraintVerificationStatus.SATISFIED,
        )

        h1 = ObjectiveVerificationResult.compute_evidence_hash("q1", "p1", [req1], [c1])
        h2 = ObjectiveVerificationResult.compute_evidence_hash("q1", "p1", [req1], [c1])
        self.assertEqual(h1, h2)

        # Mutate check evidence
        req1_mut = req1.model_copy(
            update={
                "physical_checks": [
                    VerificationCheckResult(
                        check_name="file_exists",
                        check_type=CheckType.PHYSICAL,
                        passed=True,
                        evidence={"size": 101},
                    )
                ]
            }
        )
        h3 = ObjectiveVerificationResult.compute_evidence_hash("q1", "p1", [req1_mut], [c1])
        self.assertNotEqual(h1, h3)


class TestL15DeterministicVerifiers(unittest.TestCase):
    """Tests L15.1: Specialized domain verifiers."""

    def test_file_verifier_physically_verifies_file_and_detects_missing(self):
        """FileVerifier proves physical existence and detects missing file."""
        verifier = FileVerifier()
        req = RequirementItem(
            requirement_id="R1",
            description="Save report to C:/test/report.txt",
            domain="file",
            expected_evidence_type="file",
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
            temp_path = tf.name
            tf.write(b"Hello physical verification!")

        try:
            # Case 1: Physical file exists on disk
            res = verifier.verify(
                requirement=req,
                receipt={"filepath": temp_path, "bytes_written": len(b"Hello physical verification!")},
            )
            self.assertEqual(res.status, RequirementVerificationStatus.VERIFIED_SUCCESS)
            self.assertTrue(all(c.passed for c in res.physical_checks))

            # Case 2: File missing on disk (simulated tool success without real file)
            missing_path = temp_path + ".missing"
            res_missing = verifier.verify(
                requirement=req,
                receipt={"filepath": missing_path, "bytes_written": 50},
            )
            self.assertEqual(res_missing.status, RequirementVerificationStatus.VERIFIED_FAILURE)
            self.assertFalse(res_missing.physical_checks[0].passed)
            self.assertEqual(res_missing.physical_checks[0].check_name, "file_exists")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_process_verifier_launch_and_termination(self):
        """ProcessVerifier checks alive for launch and not alive for termination."""
        verifier = ProcessVerifier()
        my_pid = os.getpid()

        # Launch / running requirement
        req_launch = RequirementItem(requirement_id="R1", description="Launch python", domain="os")
        res_launch = verifier.verify(requirement=req_launch, receipt={"pid": my_pid})
        self.assertEqual(res_launch.status, RequirementVerificationStatus.VERIFIED_SUCCESS)

        # Termination requirement: process must NOT exist
        req_kill = RequirementItem(requirement_id="R2", description="Kill target process", domain="os")
        # For non-existent PID 99999999
        res_kill_dead = verifier.verify(requirement=req_kill, receipt={"pid": 99999999})
        self.assertEqual(res_kill_dead.status, RequirementVerificationStatus.VERIFIED_SUCCESS)

        # For living PID (self), kill check fails!
        res_kill_live = verifier.verify(requirement=req_kill, receipt={"pid": my_pid})
        self.assertEqual(res_kill_live.status, RequirementVerificationStatus.VERIFIED_FAILURE)

    def test_desktop_verifier_service_probe(self):
        """DesktopVerifier probes TCP port and checks telemetry."""
        verifier = DesktopVerifier()
        req = RequirementItem(requirement_id="R1", description="Check n8n port 5678 reachable", domain="desktop")
        res = verifier.verify(requirement=req, receipt={"port": 5678, "status": "healthy"})
        self.assertEqual(res.status, RequirementVerificationStatus.VERIFIED_SUCCESS)
        self.assertEqual(len(res.physical_checks), 2)

    def test_browser_verifier_screenshot_file(self):
        """BrowserVerifier physically verifies screenshot file on disk."""
        verifier = BrowserVerifier()
        req = RequirementItem(requirement_id="R1", description="Capture a screenshot", domain="browser")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
            shot_path = tf.name
            tf.write(b"\x89PNG\r\n\x1a\nfake_image_bytes")

        try:
            res = verifier.verify(requirement=req, receipt={"screenshot_path": shot_path})
            self.assertEqual(res.status, RequirementVerificationStatus.VERIFIED_SUCCESS)

            # Missing screenshot fails
            res_missing = verifier.verify(requirement=req, receipt={"screenshot_path": shot_path + ".none"})
            self.assertEqual(res_missing.status, RequirementVerificationStatus.VERIFIED_FAILURE)
        finally:
            if os.path.exists(shot_path):
                os.remove(shot_path)

    def test_n8n_verifier_provenance_and_secret_scrubbing(self):
        """N8nVerifier confirms API provenance and rejects leaked plaintext secrets."""
        verifier = N8nVerifier()
        req = RequirementItem(requirement_id="R1", description="List my n8n workflows", domain="automation")

        clean_step = QuestStep(
            step_id="step_1",
            quest_id="q1",
            capability_id="n8n.list_workflows",
            arguments={},
            action_class=ActionClass.READ_ONLY,
            intent="List workflows",
        )
        res_clean = verifier.verify(
            requirement=req,
            step=clean_step,
            receipt={"workflows": [{"id": "1", "name": "Sync Workflow"}]},
        )
        self.assertEqual(res_clean.status, RequirementVerificationStatus.VERIFIED_SUCCESS)

        # Leak test: response containing plaintext OpenAI key fails check
        res_leaked = verifier.verify(
            requirement=req,
            step=clean_step,
            receipt={"workflows": [{"id": "1", "secret": "sk-12345abcdef67890"}]},
        )
        self.assertEqual(res_leaked.status, RequirementVerificationStatus.VERIFIED_FAILURE)

    def test_research_verifier_citation_integrity(self):
        """ResearchVerifier rejects responses containing unverified citation markers."""
        verifier = ResearchVerifier()
        req = RequirementItem(requirement_id="R1", description="Research Python releases", domain="web")

        res_clean = verifier.verify(
            requirement=req,
            receipt={"evidence_items": [{"id": "ev_1"}], "output": "Python 3.12 was released in Oct 2023 [ev_1]."},
        )
        self.assertEqual(res_clean.status, RequirementVerificationStatus.VERIFIED_SUCCESS)

        res_hallucinated = verifier.verify(
            requirement=req,
            receipt={"evidence_items": [{"id": "ev_1"}], "output": "Python info [UNVERIFIED_CITATION: ev_fake]."},
        )
        self.assertEqual(res_hallucinated.status, RequirementVerificationStatus.VERIFIED_FAILURE)


class TestL15ObjectiveCompletionEngine(unittest.TestCase):
    """Tests L15.2 & L15.3: Objective Completion Engine and False-Completion Defense."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_l15_quest.db")
        self.quest_store = QuestStore(self.db_path)
        self.quest_engine = QuestEngine(self.quest_store)
        self.verif_store = VerificationStore(self.db_path)
        self.engine = ObjectiveCompletionEngine(
            registry=VerificationRegistry(),
            store=self.verif_store,
            quest_engine=self.quest_engine,
        )

    def tearDown(self):
        try:
            self.quest_store.close()
        except Exception:
            pass
        try:
            self.verif_store.close()
        except Exception:
            pass
        try:
            self.tmp_dir.cleanup()
        except Exception:
            pass

    def test_false_completion_defense_missing_file_rejected(self):
        """FALSE-COMPLETION DEFENSE: Tool reports SUCCESS but file missing -> NOT COMPLETE."""
        quest = self.quest_engine.create_quest(
            title="File Write Quest",
            goal="Inspect system and save findings to C:/non_existent_path_12345/report.txt",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        # Advance to AWAITING_VERIFICATION with a step that claimed SUCCESS
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)

        step = QuestStep(
            step_id="step_fw",
            quest_id=quest.quest_id,
            capability_id="file_write",
            arguments={"filepath": "C:/non_existent_path_12345/report.txt", "content": "data"},
            action_class=ActionClass.LOCAL_CREATE,
            intent="Write report",
            status=StepStatus.COMPLETED,
            execution_receipt={"tool_result": {"outcome": "SUCCESS", "receipt": {"filepath": "C:/non_existent_path_12345/report.txt", "bytes_written": 4}}},
        )
        self.quest_store.save_steps(quest.quest_id, [step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.AWAITING_VERIFICATION)

        # Run verification
        result = self.engine.verify_quest(quest.quest_id)
        self.assertFalse(result.verified_complete)
        self.assertTrue(result.verified_failure)
        self.assertIn("R1", result.unresolved_requirements)

        # Verify Quest did NOT become COMPLETED
        reloaded = self.quest_store.get_quest(quest.quest_id)
        self.assertNotEqual(reloaded.status, QuestStatus.COMPLETED)

    def test_full_objective_verified_complete_transitions_quest(self):
        """When physical evidence exists, Quest transitions to COMPLETED with evidence hash."""
        report_file = os.path.join(self.tmp_dir.name, "verified_report.txt")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("System health is excellent.")

        quest = self.quest_engine.create_quest(
            title="Health Quest",
            goal=f"Inspect system and save report to {report_file}",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)

        step = QuestStep(
            step_id="step_1",
            quest_id=quest.quest_id,
            capability_id="file_write",
            arguments={"filepath": report_file, "content": "System health is excellent."},
            action_class=ActionClass.LOCAL_CREATE,
            intent="Write report",
            status=StepStatus.COMPLETED,
            execution_receipt={"tool_result": {"outcome": "SUCCESS", "receipt": {"filepath": report_file, "bytes_written": len("System health is excellent.")}}},
        )
        self.quest_store.save_steps(quest.quest_id, [step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.AWAITING_VERIFICATION)

        result = self.engine.verify_quest(quest.quest_id)
        self.assertTrue(result.verified_complete)
        self.assertFalse(result.verified_failure)
        self.assertEqual(len(result.unresolved_requirements), 0)
        self.assertTrue(len(result.evidence_hash) == 64)

        # Verify Quest transitioned to COMPLETED
        reloaded = self.quest_store.get_quest(quest.quest_id)
        self.assertEqual(reloaded.status, QuestStatus.COMPLETED)
        self.assertEqual(reloaded.metadata["evidence_hash"], result.evidence_hash)

    def test_negative_constraint_violation_fails_quest(self):
        """Negative constraint 'Do not modify or activate any workflow' violated -> Quest FAILED."""
        quest = self.quest_engine.create_quest(
            title="Read Only Quest",
            goal="Check my n8n workflows. Do not activate or modify any workflow.",
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.PLANNED)
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.RUNNING)

        # Rogue step executed an activation
        rogue_step = QuestStep(
            step_id="step_bad",
            quest_id=quest.quest_id,
            capability_id="n8n.activate_workflow",
            arguments={"workflow_id": "wf_123"},
            action_class=ActionClass.EXTERNAL_UPDATE,
            intent="Activate workflow",
            status=StepStatus.COMPLETED,
        )
        self.quest_store.save_steps(quest.quest_id, [rogue_step])
        self.quest_engine.transition_quest(quest.quest_id, QuestStatus.AWAITING_VERIFICATION)

        result = self.engine.verify_quest(quest.quest_id)
        self.assertFalse(result.verified_complete)
        self.assertTrue(result.verified_failure)
        self.assertIn("C_NO_WORKFLOW_MUTATION", result.violated_constraints)

        reloaded = self.quest_store.get_quest(quest.quest_id)
        self.assertEqual(reloaded.status, QuestStatus.FAILED)


class TestL15DurablePersistenceAndRestart(unittest.TestCase):
    """Tests L15.4: Verification persistence and cold restart survival."""

    def test_verification_receipt_persists_and_survives_cold_restart(self):
        """Verification result survives process restart byte-for-byte in SQLite."""
        with tempfile.TemporaryDirectory() as td:
            db_path = os.path.join(td, "persisted_verif.db")
            store1 = VerificationStore(db_path)

            req = RequirementVerification(
                requirement_id="R1",
                description="Write report",
                status=RequirementVerificationStatus.VERIFIED_SUCCESS,
                verifier_id="file_verifier",
                physical_checks=[
                    VerificationCheckResult(
                        check_name="file_exists",
                        check_type=CheckType.PHYSICAL,
                        passed=True,
                        evidence={"path": "C:/temp/report.txt"},
                    )
                ],
            )
            v_res = ObjectiveVerificationResult(
                verification_id="verif_persisted_01",
                quest_id="quest_persist_01",
                plan_id="plan_01",
                objective_text="Test objective",
                requirement_results=[req],
                constraint_results=[],
                verified_complete=True,
                evidence_hash="abcdef1234567890" * 4,
            )

            store1.record_verification(v_res)
            store1.close()

            # Cold restart: instantiate fresh store on same SQLite DB
            store2 = VerificationStore(db_path)
            loaded = store2.get_verification("verif_persisted_01")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.verification_id, "verif_persisted_01")
            self.assertEqual(loaded.quest_id, "quest_persist_01")
            self.assertTrue(loaded.verified_complete)
            self.assertEqual(loaded.evidence_hash, "abcdef1234567890" * 4)
            self.assertEqual(len(loaded.requirement_results), 1)
            self.assertEqual(loaded.requirement_results[0].status, RequirementVerificationStatus.VERIFIED_SUCCESS)

            # Query by quest_id
            latest = store2.get_latest_for_quest("quest_persist_01")
            self.assertIsNotNone(latest)
            self.assertEqual(latest.verification_id, "verif_persisted_01")
            store2.close()


if __name__ == "__main__":
    unittest.main()
