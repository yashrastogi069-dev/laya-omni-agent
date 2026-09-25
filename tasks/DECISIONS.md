# DECISIONS.md — Architecture Decision Records (ADRs)

## ADR-001: Local-First Cognitive Dual-System (System 1 Local ModernBERT + System 2 Cloud/Antigravity)
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Running large generative LLMs (7B+ parameters) locally exhausts RAM and freezes older host machines (8GB RAM, 4 CPU cores). Conversely, relying purely on cloud LLMs for every micro-decision introduces prohibitive latency (500ms - 2000ms) and monetary cost.
- **Decision**: Adopt local lightweight ModernBERT-large (Laya, ~400MB RAM, <35ms) for high-frequency System 1 decisions, backed by cloud APIs for heavy generative reasoning.
- **Reasons**: Guarantees sub-35ms routing on local CPU without freezing system memory.

---

## ADR-002: Deterministic DAG Planning vs Unconstrained ReAct Tool Loops
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Unconstrained ReAct loops ("think-act-observe" in a free-form while loop) frequently wander, repeat destructive operations, hallucinate tool completion, and suffer from prompt-injection vulnerabilities.
- **Decision**: Adopt Validated Directed Acyclic Graph (DAG) Plan + Deterministic Executor for multi-step work.
- **Reasons**: Planning is separated from execution. The planner generates a structured DAG; a deterministic runtime validates the graph, executes ready nodes, manages dependencies, enforces policies, and verifies real-world side effects.

---

## ADR-003: SQLite as Canonical Local Storage for Quests and State
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Agent state and memory must survive process crashes, client disconnects, and provider timeouts without data loss or corruption.
- **Decision**: Adopt SQLite embedded database for Quests, step states, operation ledger, and automation rules.
- **Reasons**: Zero setup, zero background daemon overhead, ACID transactions, atomic updates, and proven reliability for local-first software.

---

## ADR-004: Evidence-First Outcome Verification
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Language models frequently report tasks as complete when actions failed or were never actually executed.
- **Decision**: Actions must be verified with physical receipts (file diffs, process tables, DOM state, exit codes) before being reported as completed.

---

## ADR-005: Standalone Autonomous Agent with Clean Interface Boundaries
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: LAYA must function as a complete, fully autonomous standalone agent without depending on external runtimes. At the same time, future multi-agent coordination must remain possible without rewriting internal engines.
- **Decision**: Build LAYA as a complete standalone autonomous agent with its own Quest runtime, DAG executor, action policy, capability contracts, and memory. Expose all external boundaries via clean, standardized interface types: `AgentRequest`, `AgentResponse`, `DecisionFrame`, `Quest`, `CapabilitySpec`, `ToolResult`, `ExecutionReceipt`, `VerificationResult`, and `AgentEvent`.
- **Reasons**: Decouples LAYA completely from external runtimes while preserving modularity.

---

## ADR-006: Hierarchical Capability Routing Over Flat Tool Catalog Dumps
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: The legacy `[:12]` slice in `system1.py` excluded 11 tools. However, simply removing the slice and dumping all 23+ tool descriptions into a flat choice prompt exceeds context constraints, degrades classification accuracy, and fails to scale to 50–100 tools.
- **Decision**: Reject the flat 23-tool dump. Implement hierarchical capability routing in Checkpoint L6: `Request → Domain → Skill → Small Candidate Set → Capability`, with fail-open fallback.

---

## ADR-007: SystemOneBroker, User Model Sovereignty & Two-Level Hierarchical Locking
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Upstream single-lock concurrency serialized both model management (load/unload/preload) and inference, threatening deadlocks or memory corruption during swaps. Furthermore, model selection lacked explicit user sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlists, or task overrides.
- **Decision**: Implement `SystemOneBroker` implementing `SystemOneProvider` under ironclad User Model Sovereignty (`USER_LOCKED` strictly prohibits silent fallback; `USER_PREFERRED` permits fallback only for measurable reasons with mandatory telemetry). Enforce two-level hierarchical locking: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner, with exclusive permit draining on swaps/evictions. Ban multilingual models (English-only scope). Implement debounced Windows RAM protection (3 consecutive breaches over >=5s before idle eviction).

---

## ADR-008: Deep Evidence-Grounded Research Engine Architecture
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Autonomous web research easily falls prey to hallucinated citations, infinite spider-trap crawling, prompt-injection attacks from adversarial web pages, and heavy RAM exhaustion from headless browsers.
- **Decision**:
  1. **Adopt Scrapling (0.4.9)** as the primary lightweight stealth HTML extractor; **adapt Tavily Search API** for multi-query discovery; **reject Crawl4AI** due to excessive ~3GB RAM footprint.
  2. Enforce **cryptographic passage ledger**: Every piece of evidence has a deterministic SHA-256 passage hash ID (`ev_<hash[:10]>`). Citations in synthesis must match ledger keys; hallucinated IDs are deterministically quarantined to `[UNVERIFIED_CITATION: <id>]`.
  3. Enforce **mathematical saturation stopping**: Terminate crawl when novel passage yield $Y_k \le 0.15$ for 2 consecutive rounds.
  4. Enforce **prompt-injection defenses**: NFKC normalize, strip zero-width characters and control codes, escape literal HTML tags, and encapsulate external text in sandboxed `<untrusted_external_data origin="..." hash="...">` boundaries.
  5. Enforce **strict non-generative System 1 boundary (REQ-B1)**: System 1 is used strictly for passage relevance scoring and stance classification; text generation for query decomposition operates via deterministic facet templates or dedicated generative providers.

---

## ADR-009: Real Persistent Browser Engine Architecture
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Autonomous browser automation often suffers from lost sessions/cookies on restart, fragile DOM selectors that break upon minor CSS changes, element staleness during dynamic SPA re-renders, dangling processes causing OOM on 8GB host, and catastrophic unconfirmed financial actions (accidental checkouts/purchases).
- **Decision**:
  1. **Adopt Playwright (1.54.4 Chromium/Edge)** with persistent context directory (`~/.laya/browser_profile`), automated stale singleton lock recovery (`SingletonLock`, `SingletonCookie`, `SingletonSocket`), single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags.
  2. **Dynamic Indexed Action Space**: Inject in-page DOM stamping (`data-laya-idx="N"`) generating compact dual-key indices (`@1..@N`) with semantic fingerprints (tag, role, accessible text, href, bounding box).
  3. **Pre-Execution Staleness Verification**: Before clicking or typing, verify node attachment, tag equality, and accessible text match; immediately halt on DOM mutation conflict with structured diagnostic error.
  4. **Evidence-Based Post-Action Verification**: Physical state receipts required for every action: in-page `MutationObserver` on `document.body` for clicks (`dom_mutated`), physical `locator.input_value()` inspection for typing, URL transition tracking for navigation, and `window.scrollY` sampling for scrolling.
  5. **Hard Financial Confirmation Gate**: Deterministic Stage 3 `PolicyEngine` enforcement requiring explicit user confirmation (`user_confirmed=True`) for `ActionClass.FINANCIAL` and `financial:*` sensitive targets under all autonomy tiers below `WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`), reinforced by an intrinsic regex safety gate in `BrowserDriver`.

---

---

## ADR-010: Windows Desktop, App Lifecycle, and Local Service Engine Architecture
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Desktop application management and OS interaction on Windows often suffers from thread input attachment deadlocks (`AttachThreadInput`), launcher trampolines (e.g. `calc.exe` or `code.cmd` launching a stub process that exits while a different PID hosts the window), accidental termination of critical OS processes (`csrss`, `lsass`, PID 0/4), TCP port exhaustion during rapid local service probing, and test suites that steal user focus or require installed third-party apps.
- **Decision**:
  1. **Safe Window Activation & Deadlock Defense**: Eliminate risky `AttachThreadInput`; verify `ctypes.windll.user32.IsHungAppWindow` before activation; simulate an innocuous Alt menu key event (`VK_MENU`) to claim Windows foreground activation rights; restore minimized windows (`IsIconic`) via non-blocking `ShowWindowAsync(SW_RESTORE)`; and poll asynchronously for foreground activation.
  2. **Process Trampoline Resolution**: Resolve application launching via pre-launch top-level HWND baseline diffing (`current_hwnds - baseline_hwnds`) combined with `psutil` recursive child process tree traversal. Return strongly typed physical receipts: `launcher_pid`, `active_pid`, `process_name`, `hwnd`, `bounds`, and verification status.
  3. **Local Service Health Probing**: Implement dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` to prevent `TIME_WAIT` socket accumulation, dedicated `urllib.request.ProxyHandler({})` opener to bypass host proxy environment variables, bounded 4KB HTTP reads, and strict timeouts (<=500ms socket, <=1500ms HTTP).
  4. **Rule-0 Process Defense**: Enforce dual-layer protection across `PolicyEngine` Stage 0 and `AppWindowManager` pre-flight checks, unconditionally blocking termination of critical system processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4), strictly ignoring human confirmation.
  5. **Decoupled Backend & Isolated Testing**: Decouple Win32 operations behind `Win32Backend` abstract base class, allowing `tests/test_r3_desktop.py` to run 100% offline, with zero GUI popups and zero focus stealing, in under 1 second via `MockWin32Backend`.

---

## ADR-011: Programmatic n8n Automation Engine Architecture
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Programmatic orchestration of enterprise workflow engines (n8n) introduces critical failure modes: accidental activation of broken workflows or infinite execution loops, credential/secret leakage via plaintext node configurations, worker thread stalling during long-running Wait nodes, and remote code execution (RCE) via `executeCommand` and `code` nodes.
- **Decision**:
  1. **Strict Draft-Test-Validate Gate Triad**: Workflows are forced to `active=False` upon creation/update. Activation is strictly blocked unless 3 gates pass: (1) Structural DAG validation (cycle-free 3-color DFS, trigger in-degree == 0, trigger count >= 1), (2) Evidence-based physical receipt verifying successful execution (`status="success"`) for the current deterministic `workflow_hash`, (3) Zero plaintext secrets detected. Any parameter/connection modification recalculates the hash and invalidates prior receipts.
  2. **3-Level Nested Schema & Bidirectional Resolution**: n8n connection schemas (`connections[src]["main"][idx] = [{"node": target, ...}]`) are resolved bidirectionally using both node ID and node display name to eliminate false dangling connection errors.
  3. **Multi-Pattern Secret Scrubber**: Enforce pre-flight credential scrubbing across headers, payload dicts, and node parameters using compiled regexes for OpenAI, GitHub, AWS, Bearer/Basic, n8n API keys, private keys, and generic tokens, while strictly preserving `$json.*` and `={{ ... }}` n8n expression syntax. Enforce `extra="forbid"` on `N8nCredentialReference` to reject inline plaintext secrets at schema validation.
  4. **Wait Node Breakout in Polling**: In `trigger_and_wait`, detect execution transition to `"waiting"` state (e.g. n8n Wait node awaiting external webhook) and break out immediately with intermediate execution receipt, preventing thread stalling. Enforce bounded timeouts with exponential backoff.
  5. **Two-Tier RCE & Policy Defense**: Node types capable of arbitrary command execution (`executeCommand`, `code`, `ssh`) are flagged as sensitive targets in `PolicyEngine`, escalating blast radius to `LOCAL_SYSTEM` / `SECURITY_CRITICAL` and composite risk to >= 0.70. Stage 0 Rule-0 command scanning inspects embedded parameters to unconditionally block forbidden destructive operations (`git reset --hard`, destructive drive formatting).

---

## ADR-012: Supervised Developer Agent and Antigravity Orchestration Substrate
- **Date**: 2026-09-24
- **Status**: ACCEPTED
- **Problem**: Autonomous coding agents often loop infinitely or thrash between contradictory edits, escape repository boundaries, corrupt or bypass test suites to simulate false success, hang on hung test subprocesses or leave zombie processes on Windows, or invoke destructive Git commands (`git reset --hard`, `git clean -fd`) that wipe uncommitted user work.
- **Decision**:
  1. **Foreman 5-Stage Bounded Supervision Lifecycle**: Supervised execution proceeds through: (1) Setup / Baseline, (2) Mutation via decoupled `AgyRunner`, (3) Deterministic AST & Syntax Gate, (4) Physical Test Verification, and (5) Convergence / Safe Reversion. Max iterations clamped to [1, 5] (default 3), bounded by overall wall-clock deadline.
  2. **Deterministic Thrashing & Cycle Detection**: Compute a composite SHA-256 state fingerprint over the working tree `git diff`, sorted modified file names, and raw binary file contents on each iteration. If a fingerprint matches any previously visited state in the task's history, the engine immediately aborts with `ConvergenceStatus.THRASHING_DETECTED` and restores the tree.
  3. **Subprocess Process-Tree Isolation & Zombie Defense**: Process execution in `DeterministicSubprocessRunner` uses `CREATE_NEW_PROCESS_GROUP` on Windows, bounded `communicate(timeout=...)` to avoid pipe deadlocks, recursive process-tree termination via `taskkill /F /T /PID` upon timeout, and strict 50,000 character output truncation to protect memory.
  4. **Strict Git Workspace Confinement**: `WorkspaceConfiner` validates the presence of `.git`, blocks protected OS roots (`is_protected_path`), and verifies all file operations stay within repository bounds using dual checks (`is_relative_to` and `commonpath`).
  5. **Inviolable Safe Reversion (Rule-0 Compliance)**: Permanent prohibition of `git reset --hard` and `git clean -fd`. Rollbacks use file-by-file `git checkout -- <file>` for tracked files and boundary-verified `os.remove()` for untracked files, completely preventing loss of uncommitted developer work outside the task scope.
  6. **Anti-Tampering on Test Suites**: Test files (`test_*.py`, `*_test.py`, `tests/`) are protected by default (`allow_test_edits=False`). Any unauthorized edit to test files raises an immediate tampering exception and triggers automatic rollback (`ConvergenceStatus.TEST_TAMPERING_DETECTED`).
  7. **Fail-Fast AST Syntax Gate**: Before executing test commands, all modified `.py` files are parsed with `ast.parse()`. Syntax errors short-circuit immediately without invoking subprocess test commands.
  8. **Decoupled Runner Architecture**: Decouple CLI invocation behind `AgyRunner` ABC (`SubprocessAgyRunner` for local non-interactive `agy.exe`, `MockAgyRunner` for offline unit and integration tests), enabling 100% offline, deterministic testing.

---

## ADR-013: Persistent SQLite Quest Runtime and Durable Workflow Architecture
- **Date**: 2026-09-25
- **Status**: ACCEPTED
- **Problem**: Multi-step agent tasks lose state upon process crash/restart, risk blind duplicate retries of destructive mutations, allow language models to improperly own runtime state transitions, and lack a mechanism to pause cleanly for human confirmations.
- **Decision**:
  1. **SQLite Native Persistence**: Adopt embedded SQLite (`~/.laya/laya_quest.db`) with Write-Ahead Logging (`PRAGMA journal_mode = WAL`), `PRAGMA synchronous = NORMAL`, `PRAGMA busy_timeout = 5000`, and `PRAGMA foreign_keys = ON` on every connection.
  2. **Python 3.12 Transaction Invariants**: Configure PRAGMAs while in autocommit mode, then use explicit atomic transactions (`conn.autocommit = False`) with connection-per-thread and serialized writes via `_DB_WRITE_LOCK` (`threading.RLock`).
  3. **Optimistic Concurrency Control (OCC)**: Enforce monotonic integer `version` field on Quests and Steps with `WHERE id = :id AND version = :expected_version` checks, raising `OptimisticConcurrencyError` on collision.
  4. **Strict State Machine**: Enforce deterministic Quest lifecycle: `CREATED -> PLANNED -> RUNNING -> PAUSED (FOR_CONFIRMATION / FOR_INPUT) -> AWAITING_VERIFICATION -> COMPLETED / FAILED / CANCELLED`.
  5. **Audit Event Log**: Log immutable structured events in `quest_events` for state changes, policy checks, step dispatches, and receipts.

---

## ADR-014: Operation Ledger & Exactly-Once Mutation Semantics
- **Date**: 2026-09-25
- **Status**: ACCEPTED
- **Problem**: In autonomous tool execution, network blips, capability timeouts, and process crashes during mutations create uncertainty: did the external mutation take effect, or did it fail before execution? Blindly retrying mutations causes duplicate side-effects (duplicate emails, double charges, overwrites).
- **Decision**:
  1. **Canonical Operation Identity**: Generate deterministic operation IDs (`op_{quest_id}_{step_id}_{capability_id}`) and external idempotency keys (`idem_{op_id}_{attempt_num}`).
  2. **Three-State Mutation Lifecycle**: Enforce `PENDING -> IN_PROGRESS -> COMMITTED / FAILED / UNKNOWN_COMMIT`.
  3. **Exactly-Once Deduplication**: Completed operations cache physical execution receipts; subsequent duplicate calls return cached receipts immediately without re-execution (`is_deduplicated=True`).
  4. **Strict UNKNOWN_COMMIT Protection**: Unhandled exceptions during mutation transition to `UNKNOWN_COMMIT`. Blind retries are strictly blocked with `OperationCommitUncertainError` until physical evidence reconciliation (`reconcile_operation`) confirms true state.
  5. **Bounded Attempts**: Enforce `max_attempts` limit with `MaxAttemptsExceededError`.
  6. **WAL Lock Inversion Defense**: Enforce `conn.rollback()` in read queries' `finally` blocks to release SQLite shared read locks immediately.

---

## ADR-015: Structured DAG Planner with Template-First Precedence
- **Date**: 2026-09-25
- **Status**: ACCEPTED
- **Problem**: Language models generate unconstrained multi-step plans that contain circular dependencies, missing steps, unauthorized capabilities, or deep recursive chains. Generating plans from scratch for common tasks is slow and non-deterministic.
- **Decision**:
  1. **Template-First Precedence (Invariant 3)**: When a canonical skill provides a `workflow_template`, instantiate the DAG plan deterministically in <1ms with dynamic `$inputs.<arg>` parameter substitution, bypassing expensive generative calls.
  2. **Generative Fallback with Strict Schema**: For novel tasks without matching templates, invoke generative planning with strict JSON schema instructions, markdown fence stripping, and capability validation.
  3. **Deterministic DAG Topology**: Verify acyclicity via 3-color DFS cycle detector, topologically sort via Kahn's algorithm, evaluate in-degree for parallel ready steps, and compute critical-path depth.
  4. **Hard Plan Bounds**: Enforce max 20 steps and max depth of 6 levels.

---

## ADR-016: Deterministic Plan Validator Firewall
- **Date**: 2026-09-25
- **Status**: ACCEPTED
- **Problem**: Plans generated by models or templates must be proven structurally sound, schema-compliant, policy-feasible, and safe prior to dispatch.
- **Decision**:
  1. **10-Pass Deterministic Firewall**: Validate all plans across 10 deterministic passes (`DAG_ACYCLICITY`, `DEPENDENCY_EXISTENCE`, `CAPABILITY_REGISTRATION`, `SCHEMA_CONFORMANCE`, `POLICY_FEASIBILITY`, `AUTONOMY_COMPLIANCE`, `STEP_COUNT_BOUNDS`, `GRAPH_DEPTH_BOUNDS`, `MUTATION_SAFETY`, `RESOURCE_BUDGET`).
  2. **Two-Phase Schema Conformance**: Phase A verifies causal dependencies for dynamic references (`$steps.<id>`); Phase B masks dynamic expressions with type-compliant dummy values for JSON schema verification.
  3. **False-Positive Policy Denial Prevention**: Mask dynamic string references during pre-flight policy evaluation to prevent premature denials on unresolved parameters, deferring dynamic policy enforcement to execution runtime.
  4. **Cumulative Diagnostic Reporting**: Return complete diagnostic reports of all detected issues across all passes without premature fail-fast truncation.

