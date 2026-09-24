"""Developer Supervisor Engine (Foreman Architecture).

Adheres strictly to AGENTS.md Prime Directive:
- Invariant 1: Deterministic Control, Probabilistic Reasoning
- Invariant 4: Strongly Typed Contracts
- Invariant 6: Evidence-Based Completion
- REQ-BLOCK-1 through REQ-BLOCK-7 from Adversarial Plan Review
"""

import os
import ast
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple

from omni_engine.contracts.enums import VerificationStatus
from omni_engine.contracts.developer import (
    ConvergenceStatus,
    DevTaskSpec,
    CodeVerificationReceipt,
    DevExecutionReceipt,
)
from omni_engine.policy.rules import scan_embedded_commands
from omni_engine.policy.engine import PolicyEngine
from omni_engine.developer.process_runner import DeterministicSubprocessRunner
from omni_engine.developer.workspace import WorkspaceConfiner
from omni_engine.developer.runner import AgyRunner, SubprocessAgyRunner


class DeveloperSupervisorEngine:
    """Supervised developer agent orchestrator implementing disciplined 5-stage lifecycle."""

    def __init__(
        self,
        runner: Optional[AgyRunner] = None,
        policy_engine: Optional[PolicyEngine] = None,
    ):
        self.runner = runner or SubprocessAgyRunner()
        self.policy_engine = policy_engine or PolicyEngine()

    def execute_task(self, spec: DevTaskSpec) -> DevExecutionReceipt:
        """Execute a supervised software engineering task over bounded iterations."""
        t0 = time.perf_counter()
        deadline = t0 + spec.timeout_seconds

        # Stage 1: Validate repository root and pre-flight baseline
        try:
            resolved_repo = WorkspaceConfiner.validate_repository_root(spec.repo_path)
        except Exception as e:
            return self._make_failure_receipt(
                spec=spec,
                error=f"Workspace validation failed: {str(e)}",
                status="failure",
                convergence=ConvergenceStatus.UNVERIFIED,
                duration_ms=(time.perf_counter() - t0) * 1000,
            )

        # Pre-flight Rule-0 scan on test commands
        for cmd_str in spec.test_commands:
            violation, reason = scan_embedded_commands(cmd_str)
            if violation:
                return self._make_failure_receipt(
                    spec=spec,
                    error=f"Test command violated Rule-0: {reason}",
                    status="rejected",
                    convergence=ConvergenceStatus.RULE_0_VIOLATION,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                )

        # Capture pre-flight git HEAD
        git_head_before = self._get_git_head(resolved_repo)

        # Iteration tracking for thrashing / oscillation detection (REQ-BLOCK-1)
        iteration_history: List[str] = []
        max_iters = min(5, max(1, spec.max_iterations))
        current_iter = 0

        last_verification = CodeVerificationReceipt(
            syntax_valid=True,
            tests_passed=False,
            verification_status=VerificationStatus.UNVERIFIED,
        )
        last_diff = ""
        last_modified: List[str] = []

        while current_iter < max_iters:
            current_iter += 1

            # Check timeout
            if time.perf_counter() >= deadline:
                WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", last_modified)
                return self._make_failure_receipt(
                    spec=spec,
                    error=f"Task exceeded overall timeout budget of {spec.timeout_seconds}s",
                    status="timeout",
                    convergence=ConvergenceStatus.TIMEOUT,
                    iterations_count=current_iter,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    git_head_before=git_head_before,
                )

            # Stage 2: Supervised Mutation via Runner
            mutation_timeout = min(45.0, max(5.0, deadline - time.perf_counter()))
            success, log, modified_files = self.runner.execute_mutation(
                repo_path=resolved_repo,
                prompt=spec.task_prompt,
                target_files=spec.target_files,
                timeout_seconds=mutation_timeout,
            )
            last_modified = modified_files

            if not success and not modified_files:
                # Mutation failed completely
                WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", modified_files)
                return self._make_failure_receipt(
                    spec=spec,
                    error=f"Code mutation execution failed: {log}",
                    status="failure",
                    convergence=ConvergenceStatus.UNVERIFIED,
                    iterations_count=current_iter,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    git_head_before=git_head_before,
                )

            # Anti-tampering check (REQ-BLOCK-1)
            try:
                WorkspaceConfiner.verify_not_test_tampering(modified_files, spec.allow_test_edits)
            except PermissionError as e:
                WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", modified_files)
                return self._make_failure_receipt(
                    spec=spec,
                    error=str(e),
                    status="rejected",
                    convergence=ConvergenceStatus.TEST_TAMPERING_DETECTED,
                    iterations_count=current_iter,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    git_head_before=git_head_before,
                )

            # Compute diff and fingerprint for thrashing detection
            current_diff = self.get_diff(resolved_repo)
            last_diff = current_diff
            state_fingerprint = self._compute_state_hash(current_diff, modified_files, resolved_repo)

            if state_fingerprint in iteration_history:
                # Thrashing / oscillation detected (REQ-BLOCK-1)
                WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", modified_files)
                return self._make_failure_receipt(
                    spec=spec,
                    error="THRASHING_DETECTED: Edit-verify loop oscillated to a previously seen state.",
                    status="failure",
                    convergence=ConvergenceStatus.THRASHING_DETECTED,
                    iterations_count=current_iter,
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    git_head_before=git_head_before,
                )
            iteration_history.append(state_fingerprint)

            # Stage 3: Deterministic AST & Syntax Gate (REQ-BLOCK-4)
            syntax_valid, syntax_errors = self._verify_syntax(resolved_repo, modified_files)
            if not syntax_valid:
                last_verification = CodeVerificationReceipt(
                    syntax_valid=False,
                    syntax_errors=syntax_errors,
                    tests_passed=False,
                    test_exit_code=-1,
                    test_output=f"Syntax check failed:\n" + "\n".join(syntax_errors),
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                )
                if current_iter >= max_iters:
                    WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", modified_files)
                    return DevExecutionReceipt(
                        task_id=spec.task_id,
                        repo_path=resolved_repo,
                        exit_code=1,
                        modified_files=modified_files,
                        git_diff=last_diff,
                        git_head_before=git_head_before,
                        iterations_count=current_iter,
                        convergence_status=ConvergenceStatus.SYNTAX_ERROR,
                        verification=last_verification,
                        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                        status="failure",
                        error="Syntax validation failed on all iterations.",
                    )
                # Retry next iteration
                continue

            # Stage 4: Physical Test Verification
            test_receipt = self.run_tests(
                repo_path=resolved_repo,
                test_commands=spec.test_commands,
                timeout_seconds=min(30.0, max(5.0, deadline - time.perf_counter())),
            )
            last_verification = test_receipt

            if test_receipt.tests_passed:
                # CONVERGENCE ACHIEVED!
                return DevExecutionReceipt(
                    task_id=spec.task_id,
                    repo_path=resolved_repo,
                    exit_code=0,
                    modified_files=modified_files,
                    git_diff=current_diff,
                    git_head_before=git_head_before,
                    iterations_count=current_iter,
                    convergence_status=ConvergenceStatus.CONVERGED,
                    verification=test_receipt,
                    duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                    status="success",
                )

        # Iteration budget exhausted without passing tests
        WorkspaceConfiner.safe_revert(resolved_repo, git_head_before or "HEAD", last_modified)
        return DevExecutionReceipt(
            task_id=spec.task_id,
            repo_path=resolved_repo,
            exit_code=1,
            modified_files=[],
            git_diff="",
            git_head_before=git_head_before,
            iterations_count=current_iter,
            convergence_status=ConvergenceStatus.MAX_ITERATIONS_REACHED,
            verification=last_verification,
            duration_ms=round((time.perf_counter() - t0) * 1000, 2),
            status="failure",
            error=f"Task reached maximum iterations ({max_iters}) without passing tests.",
        )

    def run_tests(
        self,
        repo_path: str,
        test_commands: List[str],
        timeout_seconds: float = 30.0,
    ) -> CodeVerificationReceipt:
        """Execute test commands within repository and return physical receipt."""
        t0 = time.perf_counter()
        if not test_commands:
            # If no test commands configured, verification is UNVERIFIED
            return CodeVerificationReceipt(
                syntax_valid=True,
                tests_passed=True,
                test_exit_code=0,
                test_output="No test commands specified.",
                test_duration_ms=0.0,
                verification_status=VerificationStatus.UNVERIFIED,
            )

        all_outputs = []
        overall_exit_code = 0

        for cmd_str in test_commands:
            # Rule-0 embedded command scanner check
            violation, reason = scan_embedded_commands(cmd_str)
            if violation:
                return CodeVerificationReceipt(
                    syntax_valid=True,
                    tests_passed=False,
                    test_exit_code=1,
                    test_output=f"Rule-0 violation in test command: {reason}",
                    test_duration_ms=round((time.perf_counter() - t0) * 1000, 2),
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                )

            # Split command arguments safely and strip enclosing quotes
            import shlex
            cmd_args = [a.strip('"\'') for a in shlex.split(cmd_str, posix=False)]

            exit_code, stdout, stderr, _ = DeterministicSubprocessRunner.run(
                cmd=cmd_args,
                cwd=repo_path,
                timeout_seconds=timeout_seconds,
            )
            out = stdout if stdout else stderr
            all_outputs.append(f"[{cmd_str}] (exit code {exit_code}):\n{out}")

            if exit_code != 0:
                overall_exit_code = exit_code
                break

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        tests_passed = (overall_exit_code == 0)
        status = VerificationStatus.VERIFIED_SUCCESS if tests_passed else VerificationStatus.VERIFIED_FAILURE

        return CodeVerificationReceipt(
            syntax_valid=True,
            tests_passed=tests_passed,
            test_exit_code=overall_exit_code,
            test_output="\n\n".join(all_outputs),
            test_duration_ms=duration_ms,
            verification_status=status,
        )

    def get_diff(self, repo_path: str, target_files: Optional[List[str]] = None) -> str:
        """Extract physical git diff from repository."""
        cmd = ["git", "diff", "HEAD"]
        if target_files:
            cmd.append("--")
            cmd.extend(target_files)

        exit_code, stdout, stderr, _ = DeterministicSubprocessRunner.run(
            cmd=cmd,
            cwd=repo_path,
            timeout_seconds=10.0,
        )
        if exit_code == 0:
            return stdout
        return ""

    def inspect_file(self, repo_path: str, file_path: str) -> Dict[str, Any]:
        """Inspect a file within repository with strict containment verification."""
        target = WorkspaceConfiner.resolve_target_path(repo_path, file_path)
        if not os.path.exists(target) or not os.path.isfile(target):
            return {"exists": False, "error": f"File not found: {file_path}"}

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return {
                "exists": True,
                "file_path": file_path,
                "size_bytes": os.path.getsize(target),
                "content": content,
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}

    def _verify_syntax(self, repo_root: str, modified_files: List[str]) -> Tuple[bool, List[str]]:
        """Run AST syntax parse on all modified .py files (fail-fast gate)."""
        syntax_errors = []
        for rel_path in modified_files:
            if not rel_path.endswith(".py"):
                continue
            abs_path = WorkspaceConfiner.resolve_target_path(repo_root, rel_path)
            if os.path.exists(abs_path) and os.path.isfile(abs_path):
                try:
                    with open(abs_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast.parse(source, filename=rel_path)
                except SyntaxError as e:
                    syntax_errors.append(f"{rel_path}:{e.lineno}:{e.offset}: SyntaxError: {e.msg}")
                except Exception as e:
                    syntax_errors.append(f"{rel_path}: Failed to parse AST: {str(e)}")

        return (len(syntax_errors) == 0), syntax_errors

    def _get_git_head(self, repo_path: str) -> Optional[str]:
        """Capture current git commit hash."""
        code, stdout, _, _ = DeterministicSubprocessRunner.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path,
            timeout_seconds=5.0,
        )
        if code == 0 and stdout:
            return stdout.strip()
        return None

    def _compute_state_hash(self, git_diff: str, modified_files: List[str], repo_root: str) -> str:
        """Compute composite deterministic SHA-256 fingerprint of current iteration state."""
        h = hashlib.sha256()
        h.update(git_diff.encode("utf-8"))
        for f in sorted(modified_files):
            h.update(f.encode("utf-8"))
            try:
                target = WorkspaceConfiner.resolve_target_path(repo_root, f)
                if os.path.exists(target):
                    with open(target, "rb") as fp:
                        h.update(fp.read())
            except Exception:
                pass
        return h.hexdigest()

    def _make_failure_receipt(
        self,
        spec: DevTaskSpec,
        error: str,
        status: str,
        convergence: ConvergenceStatus,
        duration_ms: float,
        iterations_count: int = 0,
        git_head_before: Optional[str] = None,
    ) -> DevExecutionReceipt:
        return DevExecutionReceipt(
            task_id=spec.task_id,
            repo_path=spec.repo_path,
            exit_code=1,
            modified_files=[],
            git_diff="",
            git_head_before=git_head_before,
            iterations_count=iterations_count,
            convergence_status=convergence,
            verification=CodeVerificationReceipt(
                syntax_valid=False,
                tests_passed=False,
                test_exit_code=1,
                test_output=error,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            ),
            duration_ms=round(duration_ms, 2),
            status=status,
            error=error,
        )
