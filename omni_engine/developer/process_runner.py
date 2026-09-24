"""Deterministic subprocess execution with Windows process-tree containment and zombie defense.

Adheres strictly to REQ-BLOCK-2 from Adversarial Plan Review:
- Spawns subprocesses with CREATE_NEW_PROCESS_GROUP on Windows
- Uses communicate(timeout=...) to prevent pipe deadlocks
- Terminates entire process trees on timeout using taskkill /F /T /PID
- Truncates captured outputs at 50,000 characters to prevent memory explosion
"""

import os
import sys
import time
import subprocess
from typing import List, Optional, Tuple, Dict


MAX_OUTPUT_CHARS = 50000


class DeterministicSubprocessRunner:
    """Safe, bounded process execution engine for developer tasks and test runners."""

    @staticmethod
    def run(
        cmd: List[str],
        cwd: str,
        timeout_seconds: float = 30.0,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple[int, str, str, float]:
        """Execute command in cwd with strict timeout and process-tree cleanup.

        Returns:
            Tuple of (exit_code, stdout, stderr, duration_ms)
        """
        t0 = time.perf_counter()
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        proc = None
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=run_env,
                creationflags=creationflags,
            )
            stdout, stderr = proc.communicate(timeout=max(1.0, timeout_seconds))
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            exit_code = proc.returncode

            # Truncate output to avoid memory explosion
            if len(stdout) > MAX_OUTPUT_CHARS:
                stdout = stdout[:MAX_OUTPUT_CHARS] + f"\n... [TRUNCATED at {MAX_OUTPUT_CHARS} chars]"
            if len(stderr) > MAX_OUTPUT_CHARS:
                stderr = stderr[:MAX_OUTPUT_CHARS] + f"\n... [TRUNCATED at {MAX_OUTPUT_CHARS} chars]"

            return exit_code, stdout, stderr, duration_ms

        except subprocess.TimeoutExpired:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if proc:
                DeterministicSubprocessRunner._kill_process_tree(proc.pid)
            return -1, "", f"Execution timed out after {timeout_seconds}s", duration_ms

        except Exception as e:
            duration_ms = round((time.perf_counter() - t0) * 1000, 2)
            if proc:
                DeterministicSubprocessRunner._kill_process_tree(proc.pid)
            return -1, "", f"Execution failed: {str(e)}", duration_ms

    @staticmethod
    def _kill_process_tree(pid: int) -> None:
        """Terminate process and all child descendants to prevent zombies and file lock retention."""
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5.0,
                )
            except Exception:
                pass
        else:
            try:
                import signal
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                try:
                    os.kill(pid, 9)
                except Exception:
                    pass
