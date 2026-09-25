# lessons.md — Durable Engineering Lessons

## Lesson 1: Documentation Drift Outpaces Reality
- **Observation**: The initial README claimed 23+ tools including detailed Playwright primitives (`browser_navigate`, `browser_click_element`, `browser_type_text`). In reality, only 2 monolithic browser functions existed.
- **Principle**: Code and automated test assertions are the only verifiable truth. Documentation must be generated or verified against running tests, never written aspirational-first without immediate implementation.

## Lesson 2: Invisible Failures in Fixed Slices
- **Observation**: In `system1.py`, `list(tool_catalog.items())[:12]` was used to construct criteria. This silently severed 11 out of 23 tools from ever being chosen by the system.
- **Principle**: Never use magic hard-coded slices on dynamic registries. When limits are necessary, implement hierarchical grouping (e.g., Domain → Skill → Capability) with explicit logging and fail-open fallbacks.

## Lesson 3: The "Prompt-as-Argument" Fallacy
- **Observation**: `AutonomousPlanner` called `tool_func(mission_prompt)`, passing user text like "read the file README.md" directly to `tool_file_read(filepath)`. The tool attempted to open a file with the literal string name, failing 100% of the time.
- **Principle**: Natural language is NOT an argument. An explicit typed argument resolution step (regex, structured entity extraction, or schema-guided model generation) is mandatory between user intent and tool execution.

## Lesson 4: Execution Count ≠ True Learning
- **Observation**: `OmniMemory` marked a tool as "successful" simply because `tool_func()` returned without an unhandled Python exception. A tool that returned "File not found" or "Query returned 0 rows" was counted as a success.
- **Principle**: Memory must log verified outcome status (`success: bool`, `exit_code: int`, `receipt: dict`), not raw invocations.

## Lesson 5: Automated Tests Are Essential Grounding
- **Observation**: Prior to Checkpoint L0, zero automated test assertions (`assert`) existed in the codebase. As a result, a blatant `NameError: name 're' is not defined` in `tool_safe_math` sat undetected in production.
- **Principle**: Every single tool and decision layer must have at least one automated unit test executed by CI/test runners.

## Lesson 6: Token Blacklisting Is Insufficient for Safe Evaluation
- **Observation**: Blacklisting strings like `import` and `open` in `eval()` or AST does not protect against computational exhaustion attacks like `9**9**9**9`, which will lock the Python GIL and freeze the agent process.
- **Principle**: Sandboxed execution must use an explicit AST NodeVisitor whitelist that only allows verified operations, enforces numeric bounds on exponents, and pairs with execution timeouts.

## Lesson 7: Hierarchical Two-Level Locking Prevents Swap Races
- **Observation**: Separating model lifecycle synchronization from inference concurrency naively can cause deadlocks if an inference thread triggers a model swap while holding an inference semaphore. In C++ PyTorch runtimes, mutating loaded weights during active forward passes causes access violation segfaults.
- **Principle**: Model swaps and evictions must acquire the Level 1 lock (`_MODEL_LIFECYCLE_LOCK`) and exclusively drain all Level 2 inference permits before modifying model state. Threads holding inference permits must never acquire the lifecycle lock.

## Lesson 8: Windows RAM Fluctuations Mandate Debounced Eviction
- **Observation**: Windows 10 available RAM fluctuates by 200–800 MB due to OS file caching and background services. Evicting a 1.64 GB ModernBERT model on an instantaneous dip below a headroom threshold causes catastrophic eviction thrashing, where each request triggers a 47–69 second cold start.
- **Principle**: RAM eviction must require multiple consecutive threshold breaches over time (e.g., 3 breaches over >= 5 seconds) and only execute when the system is completely idle (zero active inferences).

## Lesson 9: Cryptographic Passage Hashing Defeats Citation Hallucination
- **Observation**: Generative models and heuristics frequently cite plausible-looking but non-existent sources (e.g. `[ev_1234567890]`) when synthesizing multi-page research digests.
- **Principle**: An immutable evidence ledger indexed by passage-level SHA-256 hashes must serve as the single source of truth. Post-synthesis citation verification must deterministically scan all citation tokens, verify ledger inclusion, and quarantine invalid references to `[UNVERIFIED_CITATION: <id>]`.

## Lesson 10: Explicit Depth Tuples in Crawl Queues Prevent Spider Traps
- **Observation**: When candidate URLs are placed in a flat list queue (`urls_to_crawl: List[str]`), shallow link expansion (depth <= 1) can accidentally traverse into depth 2 if child links are popped after seed URLs are exhausted.
- **Principle**: Crawl queues must track explicit `(url: str, depth: int)` tuples. Link extraction must strictly check `depth < max_crawl_depth` before appending child URLs with `depth + 1`.

## Lesson 11: Python Function Scope Local `import` Creates Shadow `UnboundLocalError`
- **Observation**: Placing `import re` inside a single conditional branch of a function (e.g. `if capability_id == "file_write": import re`) causes Python bytecode compilation to treat `re` as a local variable for the ENTIRE function scope. When any other branch executes `re.search()`, Python throws `UnboundLocalError` even though `re` is imported at the module level.
- **Principle**: Never place conditional or nested `import` statements inside functions when the module is already imported at module level. Standard library modules must strictly be imported at top level.

## Lesson 12: Dual-Key Addressing & Pre-Action Staleness Verification Defeats SPA Churn
- **Observation**: In modern Single Page Applications (React/Vue/Angular), DOM nodes are frequently destroyed and replaced during client-side state changes. Relying solely on a transient numeric index (`@1`) risks clicking the wrong target if an element moves or shifts between snapshot capture and action dispatch.
- **Principle**: Pair transient DOM indices (`@1..@N` stamped with `data-laya-idx`) with semantic fingerprints (tag, role, accessible text). Before executing physical input, verify node attachment and attribute consistency. If a mismatch is detected, halt execution immediately with a structured staleness error rather than firing blind clicks.

## Lesson 13: Windows Launcher Trampolines Mandate HWND Baseline Diffing & Child-Tree Traversal
- **Observation**: Modern Windows applications (e.g. `calc.exe`, `code.cmd`, UWP/WinUI app wrappers) launch a short-lived bootstrap process that delegates window ownership to another process and terminates immediately with exit code 0. Querying the initial launcher PID for visible HWNDs yields zero windows.
- **Principle**: Capture the system-wide top-level HWND set immediately prior to process launch (`baseline_hwnds`). When resolving the active window, combine `psutil.Process(launcher_pid).children(recursive=True)` traversal with HWND set diffing (`current_hwnds - baseline_hwnds`) matching window caption substrings or process executable names.

## Lesson 14: Windows Foreground Rights & Hung Windows Mandate Non-Blocking Activation
- **Observation**: Calling Win32 `SetForegroundWindow` without foreground rights causes the taskbar icon to flash orange rather than activating the window. Calling `AttachThreadInput` to force foreground rights deadlocks the caller if the target thread is unresponsive, blocked on I/O, or displaying a modal message box.
- **Principle**: Check `IsHungAppWindow(hwnd)` before any activation attempt and abort hung targets immediately. Simulate an innocuous menu key event (`VK_MENU`) to legitimately claim foreground rights without thread attachment. Restore minimized windows via non-blocking `ShowWindowAsync(SW_RESTORE)`, and poll foreground activation asynchronously.

## Lesson 15: n8n 3-Level Nested Schema & Bidirectional Resolution
- **Observation**: n8n connection schemas are not flat source-target adjacency lists. They are nested 3 levels deep (`connections[source_node]["main"][output_idx] = [{"node": target_node, "type": "main", "index": input_idx}]`), and target nodes may be referenced either by unique node ID (`uuid`) or display label (`name`). Resolving by ID alone produces false dangling connection errors on valid workflows exported from n8n UI.
- **Principle**: Graph validators must traverse connections through all 3 nesting levels and construct bidirectional resolution maps (`node_by_id` and `node_by_name`). Edges must resolve cleanly to a canonical node identity before cycle or reachability analysis.

## Lesson 16: The Gate Triad Invariant & Hash-Based Invalidation
- **Observation**: Autonomous agents frequently attempt to activate unverified or broken workflows, and caching a test run result across subsequent edits creates a critical window where broken or secret-leaking modifications are deployed directly to production.
- **Principle**: Activation must be blocked unless 3 gates pass: (1) DAG structural validation, (2) Evidence-based physical receipt of successful execution, and (3) Zero plaintext secrets. Any mutation to workflow nodes, connections, credentials, or parameters must compute a new deterministic SHA-256 hash, automatically invalidating any prior execution receipts and strictly forcing re-testing before activation.

## Lesson 17: Windows Subprocess Invocation & `shlex.split` Quote Retention
- **Observation**: When `shlex.split(cmd_str, posix=False)` splits a command on Windows, outer quotation marks around arguments are retained as literal characters within the tokens (e.g. `['"C:\\Python312\\python.exe"', '-m', ...]`). When `subprocess.Popen` receives a list starting with a literal quote, Windows `CreateProcessW` fails to locate the binary and raises `[WinError 5] Access is denied`.
- **Principle**: Always strip outer quotation marks from tokens (`[a.strip('"\'') for a in shlex.split(cmd_str, posix=False)]`) before passing command argument lists to `subprocess.Popen`.

## Lesson 18: Deterministic Thrashing Detection via Composite State Fingerprinting
- **Observation**: Autonomous coding loops frequently fall into oscillation cycles, flipping back and forth between two contradictory edits (e.g. alternating between two variable names or reverting an earlier edit), consuming iteration and timeout budgets without making progress.
- **Principle**: Compute a composite SHA-256 state fingerprint over the repository `git diff`, sorted modified file names, and raw binary file contents on each iteration. Compare against an iteration history list; if any state fingerprint repeats, abort immediately with `THRASHING_DETECTED` and revert the working tree to the baseline commit.

## Lesson 19: Safe Reversion Must Never Use Destructive Reset Commands (Rule-0)
- **Observation**: In real-world developer repositories, users frequently have uncommitted exploratory work, scratch files, or unrelated modified files in the working tree. Running `git reset --hard` or `git clean -fd` irrevocably wipes user files outside the task scope, violating safety invariants.
- **Principle**: Rollbacks must operate file-by-file: inspect tracked files via `git ls-files` and restore them individually with `git checkout -- <rel_path>`, and remove untracked files individually via `os.remove()` only after verifying containment within repository boundaries.

## Lesson 20: Pre-Existing Uncommitted User Work Must Be Excluded from Safe Reverts (Dirty Worktree Invariant)
- **Observation**: Even a file-by-file `safe_revert` can wipe user data if it unconditionally reverts every dirty file reported by `git status --porcelain`. If the user had uncommitted files or dirty modifications before the task began, reverting all dirty files upon task failure wipes the user's pre-existing work.
- **Principle**: Always capture a baseline snapshot of the working tree (`capture_baseline_state()`) before touching any repository files. Untracked files present in baseline state must never be deleted on rollback, and modified files present in baseline state must be restored to their pre-task baseline byte content rather than checked out to git HEAD.

## Lesson 21: Python 3.12 SQLite PRAGMA Dynamics (WAL and autocommit)
- **Observation**: In Python 3.12, `sqlite3.connect(..., autocommit=False)` automatically starts an implicit transaction on the first statement. Executing `PRAGMA journal_mode = WAL;` or `PRAGMA synchronous = NORMAL;` inside an active transaction raises `sqlite3.OperationalError: cannot change into wal mode from within a transaction` or `Safety level may not be changed inside a transaction`.
- **Principle**: SQLite connection factories in Python 3.12 must initialize the connection with `autocommit=True`, execute all configuration PRAGMAs (`journal_mode = WAL`, `synchronous = NORMAL`, `busy_timeout = 5000`, `foreign_keys = ON`), and only then switch `conn.autocommit = False` to enable explicit PEP 249 transaction demarcation (`conn.commit()` / `conn.rollback()`).

