# HANDOFF.md — Operational Continuation Guide (Checkpoint R3 COMPLETED; Phase R4 ACTIVE)

## What We Have Built (Current State)
A **trustworthy pre-execution control plane, provider broker, and real capability execution engines** powered by:
- **Phase R3: Windows Desktop, App & Local Service Engine**:
  - `Win32Backend` & `AppWindowManager`: Safe activation without `AttachThreadInput`, `ctypes.windll.user32.IsHungAppWindow` pre-check, simulated menu key event (`VK_MENU`) for legitimate foreground rights, non-blocking `ShowWindowAsync(SW_RESTORE)` for minimized windows (`IsIconic`), and async activation polling.
  - Process Trampoline Resolution: Pre-launch baseline HWND diffing (`current_hwnds - baseline_hwnds`) combined with recursive child-tree traversal (`psutil.Process.children(recursive=True)`), returning strongly typed physical receipts (`launcher_pid`, `active_pid`, `hwnd`, `bounds`).
  - `LocalServiceProber`: Loopback dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` to prevent `TIME_WAIT` socket buildup, isolated `ProxyHandler({})` opener to bypass host proxy environment traps, bounded 4KB HTTP reads, and strict timeouts (<=500ms socket, <=1500ms HTTP).
  - Rule-0 Process Safety Defense: Dual-layer enforcement in `PolicyEngine` Stage 0 and `AppWindowManager` pre-flight checks blocking critical OS processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4), strictly ignoring human confirmation.
  - `WindowsInputDriver`: Pre-focus verification and non-intrusive `WM_CHAR` character dispatch.
  - Capability Substrate Integration: Registered `desktop.launch_app`, `desktop.list_windows`, `desktop.focus_window`, `desktop.close_window`, `desktop.service_health`, `desktop.send_keys`, and dotless aliases in `build_real_capability_registry()`. Mapped in `ArgumentResolver` and `PolicyEngine`.
  - Offline test suite `tests/test_r3_desktop.py` (21/21 passed in 0.953s).
  - Adversarial Review: **PASS (APPROVED FOR CHECKPOINT R3)** (`286fba8a-36f5-4ab6-b993-ab0eb8ad56f3`).
- **Phase R2: Real Persistent Browser Engine**:
  - `BrowserSession`: Persistent isolated profile context (`~/.laya/browser_profile`), stale singleton lock recovery (`SingletonLock`, `SingletonCookie`, `SingletonSocket`), single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags.
  - `DOMActionIndexer`: In-page DOM stamping (`data-laya-idx="N"`), compact dual-key index `@1..@N`, semantic fingerprint extraction, financial element detection, and pre-action staleness verification.
  - `BrowserDriver`: Primitive action execution (`NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `SNAPSHOT`, `SCREENSHOT`), pre-execution financial safety gate, and evidence-based post-action verification (`dom_mutated` via `MutationObserver`, `url_changed`, physical `input_value`, `scrollY`).
  - `PolicyEngine` Stage 3 Gating: Enforces user confirmation for `ActionClass.FINANCIAL` and `financial:*` sensitive targets under all autonomy tiers below `WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`).
  - `BROWSER_INTERACT_SPEC`: Registered with `action_class=ActionClass.EXTERNAL_UPDATE`, `minimum_autonomy_profile=LOCAL_OPERATOR` in `build_real_capability_registry()`. Mapped in `ArgumentResolver`.
  - Offline test fixture (`tests/fixtures/browser_test_page.html`) and test suite `tests/test_r2_browser.py` (15/15 passed).
  - Adversarial Review: **PASS (APPROVED FOR CHECKPOINT R2)** (`6812beb1-7cd5-4555-8417-90c4aa6fc27b`).
- **Phase R1: Deep Evidence-Grounded Research Engine**:
  - `DeepResearchEngine`: Deterministic facet query decomposition (System 1 generation strictly forbidden), bounded discovery and crawl loop with explicit `(url, depth)` tuple queuing ensuring depth <= 1 enforcement, 3-gram Jaccard deduplication ($J \ge 0.70$), sequential System 1 relevance scoring and stance classification, mathematical saturation yield stopping ($Y_k \le 0.15$ for 2 rounds), and cryptographic citation verification quarantining unverified citations.
  - `sanitizer.py`: Untrusted external data isolation, NFKC normalization, zero-width / control character stripping, XML tag escaping, and `<untrusted_external_data origin="..." hash="...">` containment framing.
  - `fetcher.py`: URL canonicalization (stripping tracking query parameters and fragments), domain extraction, and `PageFetcher` multi-tier fallback (Scrapling -> BS4 -> Mock fixtures).
  - Canonical `DEEP_RESEARCH_SPEC` and `build_real_capability_registry()` preserving 23 source tools on canonical registry.
- **Foundation Gate: System 1 Provider Broker**:
  - Fast provider routing under ironclad User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlist enforcement, and task overrides.
  - Hierarchical Two-Level Locking: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner, with exclusive permit draining on swaps/evictions.
  - Strict English-Only Invariant: Prohibits multilingual checkpoints and language detection routines (`VALID_LOCAL_MODELS = ("english", "typed-decisions")`).
  - Debounced Windows RAM Protection: Telemetry via `psutil` with Windows `ctypes.windll.kernel32.GlobalMemoryStatusEx` fallback; requires 3 consecutive breaches over >=5s before idle eviction.
  - Empirical Concurrency Benchmark: Cold start is ~47.4s / 1.67 GB RAM; warm inference is ~712ms (concurrency 2: 2.79 req/s).
  - Deterministic Stratified Calibration: 70/30 stratified partition (72 dev / 31 test) and 10-bin Expected Calibration Error (ECE) metric evaluation harness.
- **Pre-Execution Control Plane (L0–L9)**:
  - System 1 Decision Fabric (L7.5) with ModernBERT-large and two-stage adaptive triage.
  - Hierarchical Capability Routing (L6A/L6B) with multi-tier tool catalog reduction.
  - Skills Layer (L7) with workflow manifests and safety floors.
  - Typed Argument Resolution Engine (L8) with sub-millisecond extraction (0.118 ms).
  - Deterministic Policy Engine (L9) with sub-millisecond evaluation (~0.15ms warm) enforcing Inviolable Rule-0 Invariants.
- **Strongly Typed Capability Contracts**: Clean interface boundaries throughout (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `EvidenceItem`, `ResearchClaim`, `BrowserElement`, `BrowserSnapshot`, `BrowserActionResult`, `AppWindowInfo`, `AppLaunchResult`, `ServiceHealthStatus`, `DesktopActionResult`, `PolicyDecision`, `ArgumentResolutionEnvelope`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Milestone Goal: **Real Capability Engines: Foundation Gate (COMPLETE) → Phase R1 (COMPLETE) → Phase R2 (COMPLETE) → Phase R3 (COMPLETE) → Phase R4: n8n Automation Engine (ACTIVE)**.
- Full Test Suite: **314/314 tests passing (+ 47 subtests = 361 total, 100% pass rate)** in 211.05s across 17 test modules:
  - `tests/test_l0_baselines.py` (10 tests)
  - `tests/test_l1_repairs.py` (12 tests)
  - `tests/test_l2_contracts.py` (18 tests)
  - `tests/test_l2_1_reconciliation.py` (15 tests)
  - `tests/test_l3_capabilities.py` (25 tests, 23 subtests)
  - `tests/test_l4_providers.py` (19 tests)
  - `tests/test_l5_decision_fabric.py` (12 tests)
  - `tests/test_l6a_routing.py` (12 tests)
  - `tests/test_l7_skills.py` (26 tests)
  - `tests/test_l6b_skill_routing.py` (16 tests)
  - `tests/test_l7_5_calibration.py` (16 tests)
  - `tests/test_l8_arguments.py` (26 tests)
  - `tests/test_l9_policy.py` (26 tests)
  - `tests/test_foundation_broker.py` (27 tests)
  - `tests/test_r1_research.py` (18 tests)
  - `tests/test_r2_browser.py` (15 tests)
  - `tests/test_r3_desktop.py` (21 tests)
- Governance: All canonical documents synchronized with verified implementation truth.
- Non-Switching Boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.

---

## Operational Boundary & Next Phase
- **Active Phase**: **Phase R4 — n8n Automation Engine**.
- **Core Objectives for R4**:
  1. Produce technology audit & ADR in `docs/research/ADR_R4_N8N_AUTOMATION_ENGINE.md`.
  2. Implement n8n REST API client supporting draft-test-validate workflow lifecycle (`/workflows`, `/executions`, `/credentials`).
  3. Implement local n8n discovery & health probing via `LocalServiceProber` on port 5678.
  4. Enforce strict secret isolation and zero leaked secrets in workflow payloads, logs, and prompt contexts.
  5. Enforce evidence-based execution verification polling terminal execution states.
  6. Register `n8n.list_workflows`, `n8n.get_workflow`, `n8n.create_workflow`, `n8n.trigger_workflow`, `n8n.get_execution_status` in `CapabilityRegistry`, `PolicyEngine`, and `ArgumentResolver`.
  7. Comprehensive offline mock test suite `tests/test_r4_n8n.py`.
- **Hard Stop Boundary**: Stop cleanly after R5. Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
