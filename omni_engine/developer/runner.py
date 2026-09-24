"""Decoupled Antigravity CLI runner and test mock.

Adheres strictly to REQ-BLOCK-7 from Adversarial Plan Review:
- AgyRunner: Abstract interface decoupling code mutation execution
- SubprocessAgyRunner: Invokes agy.exe with --print, --output-format json, --mode accept-edits, --sandbox
- MockAgyRunner: Fast, deterministic in-memory file mutation for 100% offline tests
"""

import os
import shutil
import pathlib
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Optional, Callable
from omni_engine.developer.process_runner import DeterministicSubprocessRunner
from omni_engine.developer.workspace import WorkspaceConfiner


class AgyRunner(ABC):
    """Abstract runner for developer agent code mutation."""

    @abstractmethod
    def execute_mutation(
        self,
        repo_path: str,
        prompt: str,
        target_files: List[str],
        timeout_seconds: float = 45.0,
    ) -> Tuple[bool, str, List[str]]:
        """Dispatch prompt and apply edits within repo_path.

        Returns:
            Tuple of (success: bool, output_log: str, modified_files: List[str])
        """
        pass


class SubprocessAgyRunner(AgyRunner):
    """Production runner executing local agy.exe CLI non-interactively."""

    def __init__(self, agy_binary_path: Optional[str] = None):
        self.agy_binary = agy_binary_path or shutil.which("agy") or shutil.which("agy.exe")
        if not self.agy_binary:
            default_path = os.path.expanduser(r"~\AppData\Local\agy\bin\agy.exe")
            if os.path.exists(default_path):
                self.agy_binary = default_path

    def execute_mutation(
        self,
        repo_path: str,
        prompt: str,
        target_files: List[str],
        timeout_seconds: float = 45.0,
    ) -> Tuple[bool, str, List[str]]:
        if not self.agy_binary or not os.path.exists(self.agy_binary):
            return False, f"agy binary not found: {self.agy_binary}", []

        cmd = [
            self.agy_binary,
            "--print", prompt,
            "--output-format", "json",
            "--mode", "accept-edits",
            "--sandbox",
            "--add-dir", repo_path,
            "--print-timeout", f"{int(timeout_seconds)}s",
        ]

        exit_code, stdout, stderr, _ = DeterministicSubprocessRunner.run(
            cmd=cmd,
            cwd=repo_path,
            timeout_seconds=timeout_seconds + 5.0,
        )

        output_log = stdout if stdout else stderr

        # Discover modified files via git status --porcelain
        modified_files = []
        status_code, status_out, _, _ = DeterministicSubprocessRunner.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            timeout_seconds=5.0,
        )
        if status_code == 0 and status_out:
            for line in status_out.strip().splitlines():
                if len(line) > 3:
                    dirty_file = line[3:].strip()
                    modified_files.append(dirty_file)

        success = (exit_code == 0)
        return success, output_log, modified_files


class MockAgyRunner(AgyRunner):
    """Fast, deterministic offline mock runner for unit and integration testing."""

    def __init__(
        self,
        mutation_handler: Optional[Callable[[str, str, List[str]], Tuple[bool, str, Dict[str, str]]]] = None,
    ):
        """Args:
            mutation_handler: Optional function taking (repo_path, prompt, target_files)
                              and returning (success, log, dict_of_file_updates).
        """
        self.mutation_handler = mutation_handler
        self._preset_mutations: List[Dict[str, str]] = []
        self._call_count = 0

    def set_preset_mutations(self, mutations: List[Dict[str, str]]) -> None:
        """Configure sequential mutations per iteration."""
        self._preset_mutations = mutations
        self._call_count = 0

    def execute_mutation(
        self,
        repo_path: str,
        prompt: str,
        target_files: List[str],
        timeout_seconds: float = 45.0,
    ) -> Tuple[bool, str, List[str]]:
        self._call_count += 1
        modified_files: List[str] = []

        file_updates: Dict[str, str] = {}
        log = "Mock mutation executed"
        success = True

        if self.mutation_handler:
            success, log, file_updates = self.mutation_handler(repo_path, prompt, target_files)
        elif self._preset_mutations:
            idx = min(self._call_count - 1, len(self._preset_mutations) - 1)
            file_updates = self._preset_mutations[idx]

        # Apply file updates to disk
        for rel_path, content in file_updates.items():
            abs_target = WorkspaceConfiner.resolve_target_path(repo_path, rel_path)
            os.makedirs(os.path.dirname(abs_target), exist_ok=True)
            with open(abs_target, "w", encoding="utf-8") as f:
                f.write(content)
            modified_files.append(rel_path)

        return success, log, modified_files
