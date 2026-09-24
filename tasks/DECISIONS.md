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

