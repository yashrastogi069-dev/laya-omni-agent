"""RV0 Reality Gate Test Suite — Empirical Validation Across All Capability Engines.

Validates the complete REALITY_MATRIX:
- RV0-A: System 1 Provider Broker Sovereignty & Calibration
- RV0-B: Deep Research Engine & Cryptographic Citation Hashing
- RV0-C: Real Browser Engine & Physical Evidence Receipts
- RV0-D: Windows Desktop Engine & Trampoline Resolution & Rule-0 Defense
- RV0-E: n8n Automation Engine & Draft-Test-Validate Gate Triad & Secret Scrubber
- RV0-F: Developer Agent / Antigravity Substrate & MANDATORY DIRTY WORKTREE TEST
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess

# RV0-A Imports
from omni_engine.providers.broker import SystemOneBroker
from omni_engine.providers.system1 import LayaProvider, JevProvider
from omni_engine.contracts.broker import (
    BrokerDecision,
    ProviderSelectionMode,
    FallbackReason,
    ProviderPolicyConfig,
)
from omni_engine.contracts.decision import DecisionSignal
from omni_engine.contracts.enums import VerificationStatus

# RV0-B Imports
from omni_engine.research.engine import DeepResearchEngine
from omni_engine.research.sanitizer import clean_web_text, sanitize_untrusted_web_content
from omni_engine.contracts.research import (
    ResearchDossier,
    EvidenceItem,
    ClaimVerificationStatus,
)

# RV0-C Imports
from omni_engine.browser.session import BrowserSession
from omni_engine.browser.driver import BrowserDriver
from omni_engine.contracts.browser import (
    BrowserActionRequest,
    BrowserActionResult,
    BrowserActionType,
    BrowserElement,
    BrowserSnapshot,
)

# RV0-D Imports
from omni_engine.desktop.app_manager import AppWindowManager, Win32Backend
from tests.test_r3_desktop import MockWin32Backend
from omni_engine.desktop.service import LocalServiceProber
from omni_engine.policy.rules import is_protected_process

# RV0-E Imports
from omni_engine.automation.client import N8nClient
from omni_engine.automation.engine import N8nAutomationEngine
from omni_engine.automation.transport import MockN8nTransport
from omni_engine.automation.scrubber import SecretScrubber

# RV0-F Imports
from omni_engine.contracts.developer import DevTaskSpec, ConvergenceStatus
from omni_engine.developer.workspace import WorkspaceConfiner
from omni_engine.developer.runner import MockAgyRunner
from omni_engine.developer.engine import DeveloperSupervisorEngine


class TestRV0RealityGate(unittest.TestCase):
    """Reality Gate empirical validation tests covering all real capability engines."""

    # =========================================================================
    # RV0-A: System 1 Provider Broker Sovereignty & Calibration
    # =========================================================================
    def test_rv0_a_user_sovereignty_locked_and_preferred(self):
        """RV0-A: Verify SystemOneBroker obeys USER_LOCKED and USER_PREFERRED policy."""
        config_locked = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_LOCKED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="laya_english",
        )
        broker_locked = SystemOneBroker(policy_config=config_locked)
        prov, decision = broker_locked.resolve_provider()
        self.assertEqual(prov.provider_id, "laya")
        self.assertEqual(decision.selected_provider, "laya_english")
        self.assertFalse(decision.fallback_occurred)

        # In USER_PREFERRED mode with Jev preferred, if Jev is unconfigured it must record telemetry and fall back to laya_english
        config_pref = ProviderPolicyConfig(
            mode=ProviderSelectionMode.USER_PREFERRED,
            allowed_providers=["laya_english", "jev"],
            preferred_provider="jev",
        )
        broker_pref = SystemOneBroker(policy_config=config_pref)
        prov_pref, decision_pref = broker_pref.resolve_provider()
        self.assertEqual(prov_pref.provider_id, "laya")
        self.assertTrue(decision_pref.fallback_occurred)
        self.assertEqual(decision_pref.fallback_reason, FallbackReason.PROVIDER_UNCONFIGURED)

    def test_rv0_a_english_only_invariant(self):
        """RV0-A: Verify multilingual checkpoints are strictly rejected (English-only scope)."""
        with self.assertRaises(ValueError):
            LayaProvider(model_name="multilingual")

    # =========================================================================
    # RV0-B: Deep Research Engine & Cryptographic Citation Hashing
    # =========================================================================
    def test_rv0_b_cryptographic_citation_verification(self):
        """RV0-B: Verify research evidence hashing and cryptographic citation verification."""
        engine = DeepResearchEngine()

        # Test prompt sanitization
        dirty_input = "Safe query <script>alert('xss')</script> \u200b\uFEFFwith zero-width chars"
        sanitized, _ = sanitize_untrusted_web_content(dirty_input, origin_url="https://example.com")
        self.assertNotIn("<script>", sanitized)
        self.assertNotIn("\u200b", sanitized)

        # Test cryptographic citation verification:
        # Create known passage and verify legitimate vs hallucinated citation IDs
        p1 = "Autonomous AI agents require persistent quest state and deterministic execution."
        ev1 = EvidenceItem.create(
            canonical_url="https://example.com/arch",
            passage_text=p1,
            relevance_score=0.95,
        )
        ledger = {ev1.evidence_id: ev1}

        # Synthesis with valid citation and hallucinated citation
        raw_synthesis = f"Agents need persistence [{ev1.evidence_id}], but also magic [ev_deadbeef99]."
        raw_claims = [{"text": "Agents need persistence", "cited_ids": [ev1.evidence_id, "ev_deadbeef99"]}]
        verified_summary, verified_claims, hall_count = engine._verify_citations(raw_synthesis, raw_claims, ledger)

        # The valid citation is preserved; the fake one is rewritten
        self.assertIn(f"[{ev1.evidence_id}]", verified_summary)
        self.assertIn("[UNVERIFIED_CITATION: ev_deadbeef99]", verified_summary)
        self.assertEqual(hall_count, 1)
        self.assertEqual(verified_claims[0].verification_status, ClaimVerificationStatus.HALLUCINATED)

    # =========================================================================
    # RV0-C: Real Browser Engine & Physical Evidence Receipts
    # =========================================================================
    def test_rv0_c_browser_snapshot_interaction_and_receipts(self):
        """RV0-C: Verify browser persistent driver, @1..@N indexing, click/type receipts, and financial safety."""
        session = BrowserSession(headless=True)
        driver = BrowserDriver(session=session)
        fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "browser_test_page.html"))
        if not os.path.exists(fixture_path):
            self.skipTest(f"Fixture {fixture_path} not found")

        try:
            url = f"file:///{fixture_path.replace(os.sep, '/')}"
            nav_req = BrowserActionRequest(
                action_type=BrowserActionType.NAVIGATE,
                url=url,
            )
            nav_res = driver.execute(nav_req)
            self.assertTrue(nav_res.success)

            snap = driver.get_last_snapshot()
            self.assertIsNotNone(snap)
            self.assertGreaterEqual(snap.interactive_count, 3)

            # Check @1..@N indexing
            indices = [e.index for e in snap.elements]
            self.assertIn("@1", indices)

            # Type into input with physical verification
            input_elem = [e for e in snap.elements if e.tag_name == "input"][0]
            type_req = BrowserActionRequest(
                action_type=BrowserActionType.TYPE,
                target=input_elem.index,
                text="laya_test_user",
            )
            type_res = driver.execute(type_req)
            self.assertTrue(type_res.success)
            self.assertEqual(type_res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
            self.assertEqual(type_res.verification_evidence["actual_value"], "laya_test_user")

            # Click action with DOM mutation verification
            btn = [e for e in snap.elements if "Log In" in e.text][0]
            click_req = BrowserActionRequest(
                action_type=BrowserActionType.CLICK,
                target=btn.index,
            )
            click_res = driver.execute(click_req)
            self.assertTrue(click_res.success)
            self.assertEqual(click_res.verification_status, VerificationStatus.VERIFIED_SUCCESS)

            # Financial safety gate: unconfirmed click on checkout button must fail
            checkout_btn = [e for e in snap.elements if e.is_financial][0]
            fin_req = BrowserActionRequest(
                action_type=BrowserActionType.CLICK,
                target=checkout_btn.index,
                user_confirmed=False,
            )
            fin_res = driver.execute(fin_req)
            self.assertFalse(fin_res.success)
            self.assertIn("Financial confirmation required", fin_res.error)
        finally:
            session.close()

    # =========================================================================
    # RV0-D: Windows Desktop Engine & Trampoline Resolution & Rule-0 Defense
    # =========================================================================
    def test_rv0_d_desktop_trampoline_and_rule_0_defense(self):
        """RV0-D: Verify trampoline resolution, process receipts, and Rule-0 process defense."""
        backend = MockWin32Backend()
        manager = AppWindowManager(backend=backend)
        windows = manager.list_windows()
        self.assertGreaterEqual(len(windows), 2)

        calc_win = [w for w in windows if "Calculator" in w.title][0]
        self.assertEqual(calc_win.title, "Calculator")
        self.assertEqual(calc_win.hwnd, 1002)
        close_res = manager.close_window(calc_win.hwnd)
        self.assertTrue(close_res)

        # Rule-0 Process Safety Defense: Verify critical OS processes are permanently blocked
        self.assertTrue(is_protected_process(0)[0])
        self.assertTrue(is_protected_process(4)[0])
        self.assertTrue(is_protected_process("csrss.exe")[0])
        self.assertTrue(is_protected_process("lsass.exe")[0])
        self.assertTrue(is_protected_process("services.exe")[0])
        self.assertFalse(is_protected_process("notepad.exe")[0])

    def test_rv0_d_service_prober_dual_stack(self):
        """RV0-D: Verify LocalServiceProber dual-stack health probing with timeouts."""
        prober = LocalServiceProber()
        # Probe an unused high port: should fail gracefully without unhandled exceptions
        is_listening, latency_ms, error = prober.probe_socket(port=9999, timeout=0.2)
        self.assertFalse(is_listening)

    # =========================================================================
    # RV0-E: n8n Automation Engine & Draft-Test-Validate Gate Triad & Secret Scrubber
    # =========================================================================
    def test_rv0_e_n8n_gate_triad_and_secret_scrubber(self):
        """RV0-E: Verify n8n Gate Triad (activation blocked without receipt) and secret scrubber."""
        transport = MockN8nTransport()
        client = N8nClient(transport=transport)
        engine = N8nAutomationEngine(client=client, poll_interval=0.01, sleep_fn=lambda _: None)

        # 1. Create draft workflow
        wf_data = {
            "name": "Reality Gate Test Workflow",
            "nodes": [
                {"id": "n1", "name": "Start", "type": "n8n-nodes-base.manualTrigger"},
                {"id": "n2", "name": "SetData", "type": "n8n-nodes-base.set"},
            ],
            "connections": {
                "Start": {"main": [[{"node": "SetData", "type": "main", "index": 0}]]}
            },
        }
        create_res = engine.create_workflow(
            name=wf_data["name"],
            nodes=wf_data["nodes"],
            connections=wf_data["connections"],
        )
        self.assertTrue(create_res.success)
        wf_id = create_res.workflow_id
        # Invariant: workflows must be created in draft mode
        self.assertFalse(create_res.data["active"])

        # 2. Gate Triad: Attempting activation without test execution receipt MUST be blocked
        act_unverified = engine.activate_workflow(wf_id)
        self.assertFalse(act_unverified.success)
        self.assertIn("Gate 2 (Test Execution)", act_unverified.error)

        # 3. Execute test run to generate receipt
        test_run = engine.test_workflow(wf_id)
        self.assertTrue(test_run.success)

        # 4. Now activation MUST succeed
        act_verified = engine.activate_workflow(wf_id)
        self.assertTrue(act_verified.success)
        self.assertTrue(act_verified.data["active"])

        # 5. Secret scrubber verification: strips keys, preserves expressions
        dirty_params = {
            "api_key": "sk-1234567890abcdef1234567890abcdef",
            "bearer": "Bearer ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "expression": "={{ $json.my_variable }}",
        }
        scrubbed = SecretScrubber.scrub_dict(dirty_params)
        self.assertEqual(scrubbed["api_key"], "[REDACTED_SECRET]")
        self.assertIn("[REDACTED_SECRET]", scrubbed["bearer"])
        self.assertEqual(scrubbed["expression"], "={{ $json.my_variable }}")

    # =========================================================================
    # RV0-F: Developer Agent / Antigravity Substrate & MANDATORY DIRTY WORKTREE TEST
    # =========================================================================
    def test_rv0_f_mandatory_dirty_worktree_survival(self):
        """RV0-F MANDATORY: Pre-existing uncommitted user work must survive rollback byte-for-byte!

        Failure of this test is a BLOCKING failure for the entire RV0 reality gate.
        """
        temp_dir = tempfile.mkdtemp(prefix="laya_rv0_dirty_")
        repo_path = os.path.realpath(temp_dir)

        try:
            # 1. Initialize git repo with committed baseline
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "LayaTest"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "laya@test.local"], cwd=repo_path, capture_output=True, check=True)

            math_py = os.path.join(repo_path, "math_lib.py")
            with open(math_py, "w", encoding="utf-8") as f:
                f.write("def add(a, b):\n    return a - b  # buggy\n")

            test_py = os.path.join(repo_path, "test_math.py")
            with open(test_py, "w", encoding="utf-8") as f:
                f.write("import unittest\nfrom math_lib import add\nclass T(unittest.TestCase):\n    def test(self):\n        self.assertEqual(add(2, 3), 5)\nif __name__ == '__main__': unittest.main()\n")

            # Commit clean baseline
            subprocess.run(["git", "add", "math_lib.py", "test_math.py"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True, check=True)

            # 2. INTRODUCE PRE-EXISTING UNCOMMITTED USER WORK BEFORE TASK RUNS:
            # A) Pre-existing untracked user file
            user_untracked_file = os.path.join(repo_path, "user_scratchpad.txt")
            untracked_content = "CRITICAL UNCOMMITTED USER RESEARCH NOTES 42\nDO NOT WIPE ME!"
            with open(user_untracked_file, "w", encoding="utf-8") as f:
                f.write(untracked_content)

            # B) Pre-existing tracked user modification
            draft_py = os.path.join(repo_path, "existing_draft.py")
            with open(draft_py, "w", encoding="utf-8") as f:
                f.write("# committed placeholder\n")
            subprocess.run(["git", "add", "existing_draft.py"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "Add draft"], cwd=repo_path, capture_output=True, check=True)

            modified_user_content = "# USER UNCOMMITTED DRAFT MODIFICATION\ndef my_draft(): return 'precious user data'\n"
            with open(draft_py, "w", encoding="utf-8") as f:
                f.write(modified_user_content)

            # Verify working tree is dirty before task starts
            status_pre = subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, capture_output=True, text=True, check=True)
            self.assertIn("user_scratchpad.txt", status_pre.stdout)
            self.assertIn("existing_draft.py", status_pre.stdout)

            # 3. Run DeveloperSupervisorEngine with a task that INTENTIONALLY FAILS / ROLLS BACK:
            # The runner introduces broken syntax into math_lib.py, forcing safe_revert!
            runner = MockAgyRunner()
            runner.set_preset_mutations([{"math_lib.py": "def broken_syntax(::: invalid python syntax!"}])

            engine = DeveloperSupervisorEngine(runner=runner)
            spec = DevTaskSpec(
                task_id="rv0_dirty_test",
                repo_path=repo_path,
                task_prompt="Fix add function in math_lib.py",
                target_files=["math_lib.py"],
                test_commands=[f'"{sys.executable}" test_math.py'],
                max_iterations=1,
                timeout_seconds=15.0,
            )

            receipt = engine.execute_task(spec)
            # The task must fail due to syntax error and trigger safe_revert
            self.assertEqual(receipt.convergence_status, ConvergenceStatus.SYNTAX_ERROR)

            # 4. MANDATORY VERIFICATION: PRE-EXISTING USER WORK SURVIVES BYTE-FOR-BYTE!
            # A) Untracked file check
            self.assertTrue(os.path.exists(user_untracked_file), "Pre-existing untracked user file was DELETED during rollback!")
            with open(user_untracked_file, "r", encoding="utf-8") as f:
                actual_untracked = f.read()
            self.assertEqual(actual_untracked, untracked_content, "Pre-existing untracked user content was corrupted!")

            # B) Modified tracked file check
            self.assertTrue(os.path.exists(draft_py), "Pre-existing modified file disappeared!")
            with open(draft_py, "r", encoding="utf-8") as f:
                actual_draft = f.read()
            self.assertEqual(actual_draft, modified_user_content, "Pre-existing user modifications were wiped during rollback!")

            # C) Task target check: math_lib.py must be reverted to baseline
            with open(math_py, "r", encoding="utf-8") as f:
                math_content = f.read()
            self.assertNotIn("broken_syntax", math_content)
            self.assertIn("return a - b", math_content)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
