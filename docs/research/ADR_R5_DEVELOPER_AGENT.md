# ADR_R5_DEVELOPER_AGENT.md — Architectural Decision Record: Supervised Developer Agent & Antigravity Orchestration Engine

- **Status**: ACCEPTED (Incorporating 7 Remediations from Adversarial Plan Review)
- **Date**: 2026-09-24
- **Author**: LAYA Omni Agent Engineering Team
- **Milestone**: Phase R5: Developer Agent / Antigravity Engine
- **Target Architecture**: Autonomous Developer Supervision, Antigravity CLI Integration, Workspace Sandboxing, and Evidence-Based Code Verification.

---

## 1. Context & Problem Statement

Autonomous software engineering agents must solve non-trivial coding tasks (debugging, refactoring, test repair, feature additions) without introducing catastrophic failures:
1. **Unbounded Hallucination & Code Corruption**: A probabilistic model left unchecked can destroy working codebases, hallucinate non-existent APIs, introduce syntax errors, or create infinite loops.
2. **Breach of Rule-0 Invariants**: Standard coding agents frequently run destructive commands (`git reset --hard`, `git clean -fd`, `rm -rf /`, force-pushing to remote branches) when attempting to "clean up" after an error.
3. **Lack of Evidence-Based Verification (Invariant 6)**: Plausible-sounding model summaries ("I have fixed the bug and verified the tests pass") are frequently untruthful. Completion must be proven with physical receipts: deterministic AST parsing, execution exit codes, and physical diff inspection.
4. **Tool Isolation & Subagent Supervision**: LAYA operates as the fast, deterministic nervous system and supervisor ("Foreman"). LAYA must orchestrate developer operations using strongly typed capability contracts without violating the Non-Switching Boundary or leaking state.
5. **Offline Testability & Determinism**: Development tools often require active remote LLMs or interactive terminal prompts. The engine must support deterministic, offline simulation and verified fixture repositories for automated CI testing.

---

## 2. Technology Audit & Remediated Architecture Decisions

### 2.1 Bounded Convergence & Thrashing Detection (REQ-BLOCK-1)
- **Thrashing & Oscillation Detection**: The supervisor maintains an `iteration_history` storing SHA-256 hashes of modified files and diffs. If the diff hash or file hash set matches any prior iteration state in the current session, the loop immediately aborts with `ConvergenceStatus.THRASHING_DETECTED` and triggers safe rollback.
- **Iteration Ceiling**: `max_iterations: int = 3` (bounded in `[1, 5]`).
- **Hierarchical Timeouts**: Overall task timeout (120s default), per-test timeout (30s default), per-mutation timeout (45s default).
- **Anti-Tampering Invariant**: `allow_test_edits: bool = False` by default. If modified files include test suite paths (`test_*.py`, `tests/...`) and `allow_test_edits` is False, the iteration is rejected immediately with `ConvergenceStatus.TEST_TAMPERING_DETECTED`.

### 2.2 Windows Subprocess Isolation & Zombie Defense (REQ-BLOCK-2)
- Implement `DeterministicSubprocessRunner` (or `SafeProcessRunner`):
  1. Spawn subprocesses on Windows with `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP`.
  2. Read safely via `proc.communicate(timeout=timeout_seconds)`.
  3. On timeout, invoke process-tree termination: `taskkill /F /T /PID <pid>`.
  4. Truncate captured stdout/stderr to a maximum of 50,000 characters to prevent memory explosion.

### 2.3 Strict Workspace Confiner & Path Traversal Defense (REQ-BLOCK-3)
- Implement `WorkspaceConfiner`:
  1. Pre-flight check: Verify `repo_path` is not a protected system path via `is_protected_path(repo_path)` and verify it contains a valid `.git` directory.
  2. Canonicalize all target paths via `canonicalize_path()` and `pathlib.Path(p).resolve()`.
  3. Verify containment using `pathlib.Path(target).is_relative_to(repo)` AND `os.path.commonpath([repo, target]) == repo`.
  4. Disallow `--git-dir`, `--work-tree`, or `-C` flags on all subprocess invocations; set `cwd=repo`.
  5. Post-mutation audit: Run `git status --porcelain` and verify all modified/untracked files reside strictly within the repository boundaries.

### 2.4 Pre-Test AST Syntax Gate & Complete Contracts (REQ-BLOCK-4)
- **Pre-Test AST Syntax Gate**: Before executing test commands, run `ast.parse()` on all modified `.py` files. If a `SyntaxError` is encountered, fail fast immediately (`syntax_valid = False`, `verification_status = FAILED`), capture error details, and do NOT invoke the test runner.
- **Strongly Typed Developer Contracts (`omni_engine/contracts/developer.py`)**:
  - `DevTaskSpec`: `task_id`, `repo_path`, `task_prompt`, `target_files`, `test_commands`, `allow_test_edits`, `max_iterations`, `timeout_seconds`.
  - `CodeVerificationReceipt`: `syntax_valid`, `syntax_errors`, `lint_passed`, `tests_passed`, `test_exit_code`, `test_output`, `test_duration_ms`, `verification_status`.
  - `DevExecutionReceipt`: `task_id`, `repo_path`, `exit_code`, `modified_files`, `git_diff`, `git_head_before`, `iterations_count`, `verification`, `duration_ms`, `status`, `error`.

### 2.5 Rule-0 Policy Inviolability & Safe Reversion Primitive (REQ-BLOCK-5)
- **Policy Inviolability**: Scan all test commands and subprocess arguments via `scan_embedded_commands()` and `PolicyEngine.evaluate()`. Rule-0 violations unconditionally produce `PolicyEffect.DENY` with `is_hard_invariant=True`, strictly ignoring human confirmation.
- **Safe Reversion Primitive**: On failure or rollback, tracked files are restored via `git checkout -- <file>` or `git restore <file>`, and new untracked files are removed individually via `os.remove()` after containment validation. `git reset --hard` and `git clean -fd` are **permanently banned** from the engine codebase.

### 2.6 Dual Registration, Dotless Aliases & Preserving 23 Canonical Tools (REQ-BLOCK-6)
- Register `developer.run_task`, `developer.run_tests`, `developer.git_diff`, `developer.inspect_code` and dotless aliases (`developer_run_task`, etc.) in `build_real_capability_registry()`.
- Add slot extractors and clarification prompts in `omni_engine/arguments/resolver.py`.
- Preserve the 23-tool canonical registry invariant: `build_canonical_registry()` retains exactly 23 tools.

### 2.7 Decoupled AgyRunner & 100% Offline Test Suite (REQ-BLOCK-7)
- Decouple execution behind `AgyRunner` ABC:
  - `SubprocessAgyRunner`: Invokes `agy.exe` when available with `--print`, `--output-format json`, `--mode accept-edits`, `--sandbox`.
  - `MockAgyRunner`: In-memory code mutation simulator for fast offline testing.
- Unit and integration test suite `tests/test_r5_developer.py` running in <3s offline using isolated git fixture repositories.

---

## 3. Capability Registration Matrix

The following capabilities are registered in `build_real_capability_registry()`:

| Capability ID | Implementation | Action Class | Autonomy Profile | Confirmation | Idempotency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `developer.run_task` | `DeveloperSupervisorEngine.execute_task` | `LOCAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NON_IDEMPOTENT` |
| `developer.run_tests` | `DeveloperSupervisorEngine.run_tests` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` |
| `developer.git_diff` | `DeveloperSupervisorEngine.get_diff` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` |
| `developer.inspect_code` | `DeveloperSupervisorEngine.inspect_file` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` |

---

## 4. Non-Switching Boundary & Goal Boundary Invariants

1. **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.
2. **Canonical 23 Tools Invariant**: `build_canonical_registry()` retains exactly 23 tools.
3. **HARD STOP AFTER R5**: Under NO circumstances proceed to Quest (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).

