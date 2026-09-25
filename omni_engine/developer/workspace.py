"""Workspace containment and path traversal protection for developer engine.

Adheres strictly to REQ-BLOCK-3 and REQ-BLOCK-5:
- Validates repository root against is_protected_path() and mandates .git directory
- Resolves paths via canonicalize_path and Path.resolve() with is_relative_to & commonpath checks
- Guards against symlinks / junction escapes
- Detects test tampering attempts
- Safe Reversion Primitive: restores files via git checkout / os.remove; strictly forbids git reset --hard
"""

import os
import pathlib
from typing import List, Tuple, Dict, Any, Optional, Set
from omni_engine.policy.rules import is_protected_path, canonicalize_path
from omni_engine.developer.process_runner import DeterministicSubprocessRunner


class WorkspaceConfiner:
    """Enforces strict sandbox containment to approved git repository boundaries."""

    @staticmethod
    def validate_repository_root(repo_path: str) -> str:
        """Validate that repo_path is an accessible, non-protected directory containing .git."""
        canonical_repo = canonicalize_path(repo_path)
        is_prot, reason = is_protected_path(canonical_repo)
        if is_prot:
            raise PermissionError(f"Repository root cannot be a protected system path: {reason}")

        resolved_repo = str(pathlib.Path(canonical_repo).resolve())
        if not os.path.exists(resolved_repo) or not os.path.isdir(resolved_repo):
            raise FileNotFoundError(f"Repository root does not exist or is not a directory: {resolved_repo}")

        git_dir = os.path.join(resolved_repo, ".git")
        if not os.path.exists(git_dir):
            raise ValueError(f"Repository root must contain a .git directory: {resolved_repo}")

        return resolved_repo

    @staticmethod
    def resolve_target_path(repo_root: str, target_path: str) -> str:
        """Resolve target_path and strictly verify it resides within repo_root."""
        canonical_repo = canonicalize_path(repo_root)
        resolved_repo = str(pathlib.Path(canonical_repo).resolve())

        # Combine relative paths to repo_root
        if not os.path.isabs(target_path):
            combined = os.path.join(resolved_repo, target_path)
        else:
            combined = target_path

        canonical_target = canonicalize_path(combined)
        resolved_target = str(pathlib.Path(canonical_target).resolve())

        # Check relative_to and commonpath
        try:
            is_rel = pathlib.Path(resolved_target).is_relative_to(pathlib.Path(resolved_repo))
        except (ValueError, AttributeError):
            is_rel = False

        try:
            common = os.path.commonpath([resolved_repo, resolved_target])
            common_matches = os.path.normcase(common) == os.path.normcase(resolved_repo)
        except (ValueError, Exception):
            common_matches = False

        if not (is_rel and common_matches):
            raise PermissionError(f"Target path '{target_path}' escapes repository boundary '{repo_root}'")

        return resolved_target

    @staticmethod
    def verify_not_test_tampering(modified_files: List[str], allow_test_edits: bool) -> None:
        """Reject modifications to test files if allow_test_edits is False (REQ-BLOCK-1)."""
        if allow_test_edits:
            return

        for filepath in modified_files:
            norm = filepath.replace("\\", "/").lower()
            filename = os.path.basename(norm)
            is_test_file = (
                filename.startswith("test_")
                or filename.endswith("_test.py")
                or "/tests/" in norm
                or norm.startswith("tests/")
                or "/test/" in norm
                or norm.startswith("test/")
            )
            if is_test_file:
                raise PermissionError(
                    f"TEST_TAMPERING_DETECTED: Unauthorized modification to test file '{filepath}' "
                    f"while allow_test_edits is False."
                )

    @staticmethod
    def capture_baseline_state(repo_root: str) -> Dict[str, Any]:
        """Capture pre-existing dirty files and content snapshots before task execution.

        This enables safe rollback of task mutations while guaranteeing that
        pre-existing uncommitted user work is preserved byte-for-byte.
        """
        resolved_repo = WorkspaceConfiner.validate_repository_root(repo_root)
        untracked = set()
        modified = {}

        code, out, _, _ = DeterministicSubprocessRunner.run(
            ["git", "status", "--porcelain"],
            cwd=resolved_repo,
            timeout_seconds=5.0,
        )
        if code == 0 and out:
            for line in out.strip().splitlines():
                if len(line) > 3:
                    status = line[:2].strip()
                    rel_path = line[3:].strip()
                    target = os.path.join(resolved_repo, rel_path)
                    if status in ("??", "A"):
                        untracked.add(rel_path)
                    elif status in ("M", "MM", "D"):
                        if os.path.isfile(target):
                            try:
                                with open(target, "rb") as f:
                                    modified[rel_path] = f.read()
                            except Exception:
                                pass

        return {"untracked": untracked, "modified": modified}

    @staticmethod
    def safe_revert(
        repo_root: str,
        initial_head: str,
        modified_files: List[str],
        baseline_state: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str]:
        """Safely revert workspace changes without violating Rule-0 (REQ-BLOCK-5).

        STRICT INVARIANT:
        - NEVER calls 'git reset --hard' or 'git clean -fd'.
        - Restores tracked files via 'git checkout -- <file>'.
        - Restores pre-existing modified files from baseline snapshot if touched by task.
        - Deletes newly created untracked files introduced by the task via os.remove().
        - STRICTLY PRESERVES pre-existing uncommitted user files and modifications byte-for-byte.
        """
        resolved_repo = WorkspaceConfiner.validate_repository_root(repo_root)
        errors = []
        untracked_baseline = set()
        modified_baseline = {}
        if baseline_state:
            untracked_baseline = set(baseline_state.get("untracked", []))
            modified_baseline = dict(baseline_state.get("modified", {}))

        # 1. Restore tracked modified files
        for f in modified_files:
            try:
                target = WorkspaceConfiner.resolve_target_path(resolved_repo, f)
                rel_path = os.path.relpath(target, resolved_repo)

                if rel_path in modified_baseline:
                    # Pre-existing user modification: restore to user's baseline bytes
                    with open(target, "wb") as bf:
                        bf.write(modified_baseline[rel_path])
                    continue

                if rel_path in untracked_baseline:
                    # Pre-existing untracked user file: DO NOT DELETE OR OVERWRITE
                    continue

                # Check if file is tracked in git
                code, _, _, _ = DeterministicSubprocessRunner.run(
                    ["git", "ls-files", "--error-unmatch", rel_path],
                    cwd=resolved_repo,
                    timeout_seconds=5.0,
                )
                if code == 0:
                    # Tracked: restore to HEAD
                    checkout_code, _, checkout_err, _ = DeterministicSubprocessRunner.run(
                        ["git", "checkout", "--", rel_path],
                        cwd=resolved_repo,
                        timeout_seconds=5.0,
                    )
                    if checkout_code != 0:
                        errors.append(f"Failed to checkout {rel_path}: {checkout_err}")
                else:
                    # Untracked and NOT in baseline: remove safely
                    if os.path.exists(target) and os.path.isfile(target):
                        os.remove(target)
            except Exception as e:
                errors.append(f"Revert error for {f}: {str(e)}")

        # 2. Check git status --porcelain for any remaining task-created dirty files
        status_code, status_out, _, _ = DeterministicSubprocessRunner.run(
            ["git", "status", "--porcelain"],
            cwd=resolved_repo,
            timeout_seconds=5.0,
        )
        if status_code == 0 and status_out:
            for line in status_out.strip().splitlines():
                if len(line) > 3:
                    file_status = line[:2]
                    dirty_file = line[3:].strip()
                    # Skip pre-existing untracked files
                    if dirty_file in untracked_baseline:
                        continue
                    # Restore pre-existing modified files if they were altered
                    if dirty_file in modified_baseline:
                        try:
                            target = WorkspaceConfiner.resolve_target_path(resolved_repo, dirty_file)
                            with open(target, "wb") as bf:
                                bf.write(modified_baseline[dirty_file])
                        except Exception:
                            pass
                        continue

                    # Only revert if file was in modified_files list
                    if modified_files and dirty_file not in [
                        os.path.relpath(WorkspaceConfiner.resolve_target_path(resolved_repo, mf), resolved_repo)
                        for mf in modified_files
                    ]:
                        continue

                    try:
                        target = WorkspaceConfiner.resolve_target_path(resolved_repo, dirty_file)
                        if file_status.strip() in ("M", "MM", "D"):
                            DeterministicSubprocessRunner.run(
                                ["git", "checkout", "--", dirty_file],
                                cwd=resolved_repo,
                                timeout_seconds=5.0,
                            )
                        elif file_status.strip() in ("??", "A"):
                            if os.path.exists(target) and os.path.isfile(target):
                                os.remove(target)
                    except Exception:
                        pass

        if errors:
            return False, "; ".join(errors)
        return True, "Safe revert completed successfully"

