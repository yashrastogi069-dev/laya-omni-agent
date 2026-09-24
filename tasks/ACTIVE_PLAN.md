# ACTIVE_PLAN.md — Checkpoint R3: Windows / App / Local-Service Engine (ACTIVE) & R1-R2 (COMPLETED)

## 1. Summary of Completed Checkpoint R2: Real Browser Engine
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **15/15 unit and integration tests passed in 2.70s; 293/293 full repository tests (+ 47 subtests = 340 total) passed (100% pass rate)**.
- **Key Deliverables**:
  1. `docs/research/ADR_R2_BROWSER_ENGINE.md`: Technology audit adopting Playwright (1.54.4 Chromium/Edge), persistent context, indexed action space (`@1..@N`), evidence-based verification, and financial gating.
  2. `omni_engine/contracts/browser.py`: Typed contracts for `BrowserActionType`, `BrowserElement`, `BrowserSnapshot`, `BrowserActionRequest`, `BrowserActionResult`.
  3. `omni_engine/browser/session.py`: Persistent isolated profile context (`~/.laya/browser_profile`), stale singleton lock recovery, single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags.
  4. `omni_engine/browser/indexer.py`: In-page DOM stamping (`data-laya-idx="N"`), dual-key index `@1..@N`, semantic fingerprint extraction, financial keyword detection, and pre-action staleness verification.
  5. `omni_engine/browser/driver.py`: Primitive action execution (`NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `SNAPSHOT`, `SCREENSHOT`), intrinsic financial safety gate, and evidence-based post-action verification (`dom_mutated` via `MutationObserver`, `url_changed`, physical `input_value`, `scrollY`).
  6. `omni_engine/capabilities/definitions.py`: Canonical `BROWSER_INTERACT_SPEC` (`action_class=ActionClass.EXTERNAL_UPDATE`, `minimum_autonomy_profile=LOCAL_OPERATOR`), `make_browser_interact_adapter`, `register_browser_capability`.
  7. `omni_engine/policy/engine.py`: Repaired Stage 3 critical sensitive gate to enforce confirmation for `ActionClass.FINANCIAL` and `financial:*` sensitive targets under all autonomy tiers below `WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`).
  8. `omni_engine/arguments/resolver.py`: Deterministic slot extraction for browser actions, targets (`@N`), URLs, and quoted text.
  9. `tests/fixtures/browser_test_page.html`: Standalone local HTML test fixture.
  10. `tests/test_r2_browser.py`: 15 comprehensive tests with 100% pass rate.
- **Adversarial Reviews**:
  - Plan Review: Conditional Approval with 5 Blocking Requirements (`4fa42e31-d1d1-4e17-866f-a37a1402e7d5`).
  - Diff Review: **PASS (APPROVED FOR CHECKPOINT R2)** (`6812beb1-7cd5-4555-8417-90c4aa6fc27b`).
- **Non-Switching Principle**: `omni_agent.py` and `omni_engine/planner.py` remain 100% untouched.

---

## 2. Active Phase R3: Windows / App / Local-Service Engine

### Objective
Build a robust, evidence-grounded desktop, application, and local service engine for Windows 10/11 environments supporting:
1. **Application Lifecycle Management**: Launch, locate, focus, query, and gracefully terminate desktop applications (e.g. Notepad, Calculator, VS Code, Slack, n8n server, Antigravity CLI).
2. **Local Service & Health Probing**: Deterministic socket and HTTP probing for local ports and microservices (e.g. n8n on port 5678, Ollama on 11434, local dev servers on 3000/8000/8080).
3. **UI Automation Substrate (UIA / Win32)**:
   - Structured accessibility-tree querying (element titles, automation IDs, control types, bounding rectangles).
   - High-reliability fallback hierarchy (UIA -> Win32 -> Simulated Input).
4. **Safety & Confirmation Enforcement**:
   - Destructive process termination (killing non-whitelisted processes) gated under `ActionClass.SYSTEM_ACTION` / `ActionClass.LOCAL_DELETE`.
   - Never allow killing critical OS processes (csrss, lsass, smss, services, winlogon, PID 0/4) enforced as Tier-0 hard invariant.
   - Guarded keystroke injection to prevent untrusted remote injection attacks.
5. **Evidence-Based Receipts**:
   - Verification via process PID, window handle existence (`HWND`), port listening state, and window title matching.
   - Zero hallucinated status.

### Technology Audit & Candidates (`docs/research/ADR_R3_WINDOWS_APP_ENGINE.md`)
Evaluate candidates:
- Windows UI Automation (via `pywinauto` or `uiautomation` or native Win32 `ctypes`)
- Process Management: `psutil` (already installed), `subprocess` with Windows job objects / process creation flags (`CREATE_NO_WINDOW`, `DETACHED_PROCESS`)
- Port & Socket Probing: Standard library `socket`, `urllib.request`
- Display & Coordinate System: DPI awareness scaling (`SetProcessDpiAwarenessContext`)
- Record ADOPT, ADAPT, REFERENCE ONLY, REJECT decisions.

### Architecture & Pipeline Components
1. **Contracts (`omni_engine/contracts/desktop.py`)**:
   - `AppWindowInfo`: `hwnd`, `title`, `process_name`, `pid`, `is_active`, `is_minimized`, `bounds`.
   - `AppLaunchResult`: `app_name`, `pid`, `hwnd`, `success`, `verification_status`, `error`.
   - `ServiceHealthStatus`: `service_name`, `host`, `port`, `is_listening`, `http_status`, `response_time_ms`, `error`.
   - `DesktopActionResult`: `action`, `target`, `success`, `verification_status`, `evidence`, `error`.
2. **Local Service Engine (`omni_engine/desktop/service.py`)**:
   - Socket probe with timeout budget (default 1.0s).
   - HTTP health check probe (`GET /` or `GET /healthz`).
   - Service start/stop/restart abstractions.
3. **Application & Window Manager (`omni_engine/desktop/app_manager.py`)**:
   - Windows API bindings (ctypes `user32`, `kernel32`) and `psutil`.
   - DPI-aware window bounds enumeration.
   - Reliable process launch with PID capture and window discovery polling.
   - Window activation, minimize, maximize, restore.
4. **UI Automation Driver (`omni_engine/desktop/uia_driver.py`)**:
   - Accessible control enumeration by window handle.
   - Safe input dispatch with focus verification.
5. **Capability Registration (`omni_engine/capabilities/definitions.py`)**:
   - `desktop.launch_app`, `desktop.focus_window`, `desktop.service_health`, `desktop.list_windows`.
   - Registered in `build_real_capability_registry()`.
6. **Substrate & Policy Integration**:
   - Mapped in `ArgumentResolver` and `PolicyEngine`.
7. **Offline Test Suite (`tests/test_r3_desktop.py`)**:
   - Fast, deterministic tests (<2s) with mock handles and local mock socket listeners.

---

## 3. Strict Goal Boundaries
- Current Goal: `Foundation Gate (Complete) → R1 (Complete) → R2 (Complete) → R3 (Active) → R4 → R5`
- **HARD STOP AFTER R5**:
  Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
