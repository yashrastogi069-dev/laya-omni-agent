"""Unit and integration test suite for Phase R5: Developer Agent / Antigravity Engine.

Tests all 7 blocking requirements:
- REQ-BLOCK-1: Bounded Convergence & Thrashing Detection (diff/file SHA-256 oscillation, anti-tampering)
- REQ-BLOCK-2: Windows Subprocess Isolation & Zombie Defense (DeterministicSubprocessRunner)
- REQ-BLOCK-3: Workspace Containment & Path Traversal (WorkspaceConfiner, .git required, protected paths)
- REQ-BLOCK-4: Pre-Test AST Syntax Gate & Complete Contracts
- REQ-BLOCK-5: Rule-0 Policy Inviolability & Safe Reversion Primitive
- REQ-BLOCK-6: Dual Registration, Dotless Aliases & Preserving 23 Canonical Tools
- REQ-BLOCK-7: Decoupled AgyRunner & 100% Offline Test Suite
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess

from omni_engine.contracts.enums import VerificationStatus
from omni_engine.contracts.developer import (
    ConvergenceStatus,
    DevTaskSpec,
    CodeVerificationReceipt,
    DevExecutionReceipt,
    DevActionResult,
)
from omni_engine.developer.process_runner import DeterministicSubprocessRunner
from omni_engine.developer.workspace import WorkspaceConfiner
from omni_engine.developer.runner import MockAgyRunner
from omni_engine.developer.engine import DeveloperSupervisorEngine
from omni_engine.capabilities.definitions import (
    build_canonical_registry,
    build_real_capability_registry,
    DEVELOPER_RUN_TASK_SPEC,
    DEVELOPER_RUN_TESTS_SPEC,
    DEVELOPER_GIT_DIFF_SPEC,
    DEVELOPER_INSPECT_CODE_SPEC,
)
from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.policy.engine import PolicyEngine
from omni_engine.contracts.policy import PolicyEffect


class BaseGitFixtureTest(unittest.TestCase):
    """Sets up an isolated, temporary git repository fixture for offline testing."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="laya_r5_repo_")
        self.repo_path = os.path.realpath(self.temp_dir)

        # Initialize local git repository
        subprocess.run(["git", "init"], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "LayaDevAgent"], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "laya@test.local"], cwd=self.repo_path, capture_output=True, check=True)

        # Create sample files: math_lib.py (buggy) and test_math_lib.py
        self.math_py = os.path.join(self.repo_path, "math_lib.py")
        with open(self.math_py, "w", encoding="utf-8") as f:
            f.write("def add(a: int, b: int) -> int:\n    return a - b  # BUG: subtraction instead of addition\n")

        self.test_py = os.path.join(self.repo_path, "test_math_lib.py")
        with open(self.test_py, "w", encoding="utf-8") as f:
            f.write(
                "import unittest\nfrom math_lib import add\n\n"
                "class TestMath(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(add(2, 3), 5)\n\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n"
            )

        # Initial commit
        subprocess.run(["git", "add", "."], cwd=self.repo_path, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial buggy commit"], cwd=self.repo_path, capture_output=True, check=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestR5Contracts(unittest.TestCase):
    """Test strongly typed developer contracts."""

    def test_dev_task_spec_validation(self):
        spec = DevTaskSpec(
            task_id="task_001",
            repo_path="C:/repo",
            task_prompt="Fix add function in math_lib.py",
            target_files=["math_lib.py"],
            test_commands=["python -m unittest test_math_lib.py"],
            max_iterations=3,
        )
        self.assertEqual(spec.task_id, "task_001")
        self.assertFalse(spec.allow_test_edits)
        self.assertEqual(spec.max_iterations, 3)

    def test_code_verification_receipt_serialization(self):
        receipt = CodeVerificationReceipt(
            syntax_valid=True,
            tests_passed=True,
            test_exit_code=0,
            test_output="Ran 1 test in 0.001s\nOK",
            test_duration_ms=15.4,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
        )
        data = receipt.model_dump()
        self.assertTrue(data["syntax_valid"])
        self.assertTrue(data["tests_passed"])
        self.assertEqual(data["verification_status"], VerificationStatus.VERIFIED_SUCCESS)

    def test_receipt_forbids_extra_fields(self):
        with self.assertRaises(Exception):
            DevExecutionReceipt(
                task_id="t1",
                repo_path="/repo",
                verification=CodeVerificationReceipt(syntax_valid=True, tests_passed=True),
                unknown_field="injected",
            )


class TestR5SubprocessRunner(unittest.TestCase):
    """Test bounded subprocess execution and zombie defense (REQ-BLOCK-2)."""

    def test_normal_command_execution(self):
        code, stdout, stderr, dur = DeterministicSubprocessRunner.run(
            cmd=[sys.executable, "-c", "print('hello from python')"],
            cwd=os.getcwd(),
            timeout_seconds=5.0,
        )
        self.assertEqual(code, 0)
        self.assertIn("hello from python", stdout)
        self.assertGreater(dur, 0.0)

    def test_command_timeout_kills_process(self):
        code, stdout, stderr, dur = DeterministicSubprocessRunner.run(
            cmd=[sys.executable, "-c", "import time; time.sleep(10)"],
            cwd=os.getcwd(),
            timeout_seconds=0.5,
        )
        self.assertEqual(code, -1)
        self.assertIn("timed out", stderr)

    def test_output_truncation_bounds_memory(self):
        code, stdout, stderr, _ = DeterministicSubprocessRunner.run(
            cmd=[sys.executable, "-c", "print('A' * 60000)"],
            cwd=os.getcwd(),
            timeout_seconds=5.0,
        )
        self.assertEqual(code, 0)
        self.assertLessEqual(len(stdout), 50100)
        self.assertIn("TRUNCATED", stdout)


class TestR5WorkspaceConfiner(BaseGitFixtureTest):
    """Test workspace sandbox containment, anti-tampering, and safe revert (REQ-BLOCK-3, REQ-BLOCK-5)."""

    def test_valid_repository_root(self):
        resolved = WorkspaceConfiner.validate_repository_root(self.repo_path)
        self.assertEqual(os.path.normcase(resolved), os.path.normcase(self.repo_path))

    def test_reject_non_git_directory(self):
        non_git = tempfile.mkdtemp()
        try:
            with self.assertRaises(ValueError):
                WorkspaceConfiner.validate_repository_root(non_git)
        finally:
            shutil.rmtree(non_git, ignore_errors=True)

    def test_reject_protected_system_path(self):
        with self.assertRaises(PermissionError):
            WorkspaceConfiner.validate_repository_root(r"C:\Windows\System32")

    def test_resolve_target_path_within_boundary(self):
        resolved = WorkspaceConfiner.resolve_target_path(self.repo_path, "math_lib.py")
        self.assertEqual(os.path.normcase(resolved), os.path.normcase(self.math_py))

    def test_reject_path_traversal_escape(self):
        with self.assertRaises(PermissionError):
            WorkspaceConfiner.resolve_target_path(self.repo_path, "../outside.txt")

    def test_reject_test_tampering_when_disallowed(self):
        with self.assertRaises(PermissionError):
            WorkspaceConfiner.verify_not_test_tampering(
                modified_files=["math_lib.py", "test_math_lib.py"],
                allow_test_edits=False,
            )

    def test_allow_test_edits_when_flag_enabled(self):
        # Should not raise
        WorkspaceConfiner.verify_not_test_tampering(
            modified_files=["test_math_lib.py"],
            allow_test_edits=True,
        )

    def test_safe_revert_restores_tracked_and_removes_untracked(self):
        # Mutate math_lib.py
        with open(self.math_py, "w", encoding="utf-8") as f:
            f.write("# Corrupted content\n")

        # Create new untracked file
        untracked = os.path.join(self.repo_path, "new_junk.py")
        with open(untracked, "w", encoding="utf-8") as f:
            f.write("# junk\n")

        self.assertTrue(os.path.exists(untracked))

        # Perform safe revert
        success, msg = WorkspaceConfiner.safe_revert(
            repo_root=self.repo_path,
            initial_head="HEAD",
            modified_files=["math_lib.py", "new_junk.py"],
        )
        self.assertTrue(success)

        # math_lib.py should be restored
        with open(self.math_py, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("def add(a: int, b: int) -> int:", content)

        # new_junk.py should be removed
        self.assertFalse(os.path.exists(untracked))


class TestR5SupervisorEngine(BaseGitFixtureTest):
    """Test full Foreman supervision loop, AST fail-fast, thrashing detection, and verification."""

    def test_green_path_successful_bug_fix(self):
        """Mock runner applies correct fix on iteration 1, tests pass, CONVERGED returned."""
        fixed_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        mock_runner = MockAgyRunner()
        mock_runner.set_preset_mutations([{"math_lib.py": fixed_code}])

        engine = DeveloperSupervisorEngine(runner=mock_runner)
        spec = DevTaskSpec(
            task_id="t_green",
            repo_path=self.repo_path,
            task_prompt="Fix subtraction bug in add()",
            target_files=["math_lib.py"],
            test_commands=[f'"{sys.executable}" -m unittest test_math_lib.py'],
            max_iterations=3,
        )

        receipt = engine.execute_task(spec)
        self.assertEqual(receipt.status, "success")
        self.assertEqual(receipt.exit_code, 0)
        self.assertEqual(receipt.convergence_status, ConvergenceStatus.CONVERGED)
        self.assertTrue(receipt.verification.tests_passed)
        self.assertTrue(receipt.verification.syntax_valid)
        self.assertEqual(receipt.verification.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertIn("math_lib.py", receipt.modified_files)
        self.assertIn("+    return a + b", receipt.git_diff)

    def test_pre_test_ast_syntax_gate_fails_fast(self):
        """Broken Python syntax in edit fails fast without invoking tests (REQ-BLOCK-4)."""
        broken_syntax = "def add(a: int, b: int) -> int:\n    return a + \n"
        mock_runner = MockAgyRunner()
        mock_runner.set_preset_mutations([{"math_lib.py": broken_syntax}])

        engine = DeveloperSupervisorEngine(runner=mock_runner)
        spec = DevTaskSpec(
            task_id="t_syntax",
            repo_path=self.repo_path,
            task_prompt="Introduce broken syntax",
            target_files=["math_lib.py"],
            test_commands=[f'"{sys.executable}" -m unittest test_math_lib.py'],
            max_iterations=1,
        )

        receipt = engine.execute_task(spec)
        self.assertEqual(receipt.status, "failure")
        self.assertEqual(receipt.convergence_status, ConvergenceStatus.SYNTAX_ERROR)
        self.assertFalse(receipt.verification.syntax_valid)
        self.assertEqual(len(receipt.verification.syntax_errors), 1)
        self.assertIn("SyntaxError", receipt.verification.syntax_errors[0])
        self.assertEqual(receipt.verification.verification_status, VerificationStatus.VERIFIED_FAILURE)

    def test_test_tampering_rejected_and_rolled_back(self):
        """Unauthorized modification to test_math_lib.py triggers TEST_TAMPERING_DETECTED."""
        tampered_test = "import unittest\nclass TestMath(unittest.TestCase):\n    def test_add(self): pass\n"
        mock_runner = MockAgyRunner()
        mock_runner.set_preset_mutations([{"test_math_lib.py": tampered_test}])

        engine = DeveloperSupervisorEngine(runner=mock_runner)
        spec = DevTaskSpec(
            task_id="t_tamper",
            repo_path=self.repo_path,
            task_prompt="Cheat by modifying tests",
            target_files=["test_math_lib.py"],
            test_commands=[f'"{sys.executable}" -m unittest test_math_lib.py'],
            allow_test_edits=False,
            max_iterations=2,
        )

        receipt = engine.execute_task(spec)
        self.assertEqual(receipt.status, "rejected")
        self.assertEqual(receipt.convergence_status, ConvergenceStatus.TEST_TAMPERING_DETECTED)
        self.assertIn("TEST_TAMPERING_DETECTED", receipt.error)

    def test_thrashing_detection_aborts_oscillation_cycle(self):
        """Oscillating between two identical invalid states triggers THRASHING_DETECTED (REQ-BLOCK-1)."""
        edit_a = "def add(a: int, b: int) -> int:\n    return a * b\n"
        edit_b = "def add(a: int, b: int) -> int:\n    return a / b\n"
        mock_runner = MockAgyRunner()
        # Iteration 1: edit A, Iteration 2: edit B, Iteration 3: edit A again (oscillation!)
        mock_runner.set_preset_mutations([
            {"math_lib.py": edit_a},
            {"math_lib.py": edit_b},
            {"math_lib.py": edit_a},
        ])

        engine = DeveloperSupervisorEngine(runner=mock_runner)
        spec = DevTaskSpec(
            task_id="t_thrash",
            repo_path=self.repo_path,
            task_prompt="Oscillate between edits",
            target_files=["math_lib.py"],
            test_commands=[f'"{sys.executable}" -m unittest test_math_lib.py'],
            max_iterations=3,
        )

        receipt = engine.execute_task(spec)
        self.assertEqual(receipt.status, "failure")
        self.assertEqual(receipt.convergence_status, ConvergenceStatus.THRASHING_DETECTED)
        self.assertIn("THRASHING_DETECTED", receipt.error)

    def test_rule_0_command_in_test_commands_rejected(self):
        """Test commands attempting destructive operations are rejected pre-flight (REQ-BLOCK-5)."""
        engine = DeveloperSupervisorEngine()
        spec = DevTaskSpec(
            task_id="t_rule0",
            repo_path=self.repo_path,
            task_prompt="Run dangerous test",
            test_commands=["git reset --hard HEAD"],
            max_iterations=1,
        )

        receipt = engine.execute_task(spec)
        self.assertEqual(receipt.status, "rejected")
        self.assertEqual(receipt.convergence_status, ConvergenceStatus.RULE_0_VIOLATION)
        self.assertIn("Rule-0", receipt.error)

    def test_inspect_code_and_git_diff(self):
        """Inspect code returns file content and git diff returns empty for clean repo."""
        engine = DeveloperSupervisorEngine()
        diff = engine.get_diff(self.repo_path)
        self.assertEqual(diff, "")

        info = engine.inspect_file(self.repo_path, "math_lib.py")
        self.assertTrue(info["exists"])
        self.assertIn("def add", info["content"])


class TestR5SubstrateIntegration(BaseGitFixtureTest):
    """Test registry preservation, argument resolution, and policy engine integration."""

    def test_canonical_registry_invariant_preserved(self):
        """build_canonical_registry() must contain exactly 23 source tools (L3 contracts)."""
        canonical = build_canonical_registry()
        self.assertEqual(canonical.count(), 23)

    def test_real_registry_includes_developer_capabilities(self):
        """build_real_capability_registry() includes all developer capabilities and dotless aliases."""
        real = build_real_capability_registry()
        for cap_id in (
            "developer.run_task",
            "developer_run_task",
            "developer.run_tests",
            "developer_run_tests",
            "developer.git_diff",
            "developer_git_diff",
            "developer.inspect_code",
            "developer_inspect_code",
        ):
            self.assertTrue(real.has(cap_id), f"Missing capability: {cap_id}")

    def test_argument_resolver_extracts_developer_slots(self):
        resolver = ArgumentResolver()
        prompt = f"Run developer task in repo '{self.repo_path}' with prompt 'Fix bug in math_lib.py'"
        envelope = resolver.resolve(capability=DEVELOPER_RUN_TASK_SPEC, prompt=prompt)
        self.assertFalse(envelope.clarification_needed)
        self.assertEqual(os.path.normcase(envelope.arguments["repo_path"]), os.path.normcase(self.repo_path))
        self.assertIn("Fix bug in math_lib.py", envelope.arguments["task_prompt"])

    def test_policy_engine_gates_protected_path_in_developer_task(self):
        policy = PolicyEngine()
        decision = policy.evaluate(
            capability=DEVELOPER_RUN_TASK_SPEC,
            arguments={"repo_path": r"C:\Windows\System32", "task_prompt": "Test edit"},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.DENY)
        self.assertIn("RULE_0_PROTECTED_SYSTEM_PATHS", decision.matched_rules)

    def test_policy_engine_gates_rule_0_in_developer_test_command(self):
        policy = PolicyEngine()
        decision = policy.evaluate(
            capability=DEVELOPER_RUN_TASK_SPEC,
            arguments={
                "repo_path": self.repo_path,
                "task_prompt": "Safe prompt",
                "test_commands": ["git reset --hard"],
            },
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect, PolicyEffect.DENY)
        self.assertIn("RULE_0_FORBIDDEN_OPERATIONS", decision.matched_rules)


if __name__ == "__main__":
    unittest.main()
