# ACTIVE_PLAN.md — Checkpoint R4: n8n Automation Engine (ACTIVE) & R1-R3 (COMPLETED)

## 1. Summary of Completed Checkpoint R3: Windows Desktop, App & Local Service Engine
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **21/21 unit and integration tests passed in 0.953s; 314/314 full repository tests (+ 47 subtests = 361 total) passed (100% pass rate)**.
- **Key Deliverables**:
  1. `docs/research/ADR_R3_WINDOWS_APP_ENGINE.md`: Architecture audit adopting Win32 API (`win32gui`, `win32con`, `win32process`, `win32api`, `ctypes.windll.user32`), `psutil`, `socket`, and `urllib.request`.
  2. `omni_engine/contracts/desktop.py`: Strongly typed contracts (`WindowBounds`, `WindowState`, `AppWindowInfo`, `AppLaunchResult`, `ServiceHealthStatus`, `DesktopActionResult`).
  3. `omni_engine/desktop/service.py`: `LocalServiceProber` implementing dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` socket reset, `ProxyHandler({})` isolation opener, bounded 4KB reads, and strict timeouts.
  4. `omni_engine/desktop/app_manager.py`: `Win32Backend`, `NativeWin32Backend`, `AppWindowManager` implementing non-blocking focus rights via `VK_MENU`, `IsHungAppWindow` rejection, `ShowWindowAsync(SW_RESTORE)`, async activation polling, and launcher trampoline resolution via baseline HWND diffing + child process tree traversal.
  5. `omni_engine/desktop/uia_driver.py`: `WindowsInputDriver` with verified pre-focus check and `WM_CHAR` non-intrusive character dispatch.
  6. `omni_engine/desktop/engine.py`: `ComputerUseDriver` composite engine.
  7. `omni_engine/desktop/__init__.py`: Package exports.
  8. `omni_engine/capabilities/definitions.py`: Registered `desktop.launch_app`, `desktop.list_windows`, `desktop.focus_window`, `desktop.close_window`, `desktop.service_health`, `desktop.send_keys`, and dotless aliases in `build_real_capability_registry()`.
  9. `omni_engine/policy/engine.py`: Broadened Stage 0 Rule-0 process defense across desktop capabilities; mapped desktop blast radii.
  10. `omni_engine/arguments/resolver.py`: Added desktop clarification prompts and slot extractors (disambiguating multiple quoted strings).
  11. `tests/test_r3_desktop.py`: 21 comprehensive offline unit and integration tests passing in 0.953s.
- **Adversarial Reviews**:
  - Plan Review: Conditional Approval with 6 Blocking Requirements (`0b018a3a-73bc-4039-901e-5f1161505db1`).
  - Diff Review: **PASS (APPROVED FOR CHECKPOINT R3)** (`286fba8a-36f5-4ab6-b993-ab0eb8ad56f3`).
- **Non-Switching Principle**: `omni_agent.py` and `omni_engine/planner.py` remain 100% untouched (0 diffs).

---

## 2. Active Phase R4: n8n Automation Engine

### Objective
Build an official programmatic n8n automation engine integrating n8n workflows with LAYA:
1. **n8n REST API Client & Lifecycle Substrate**:
   - Programmatic integration with n8n v1 REST API (`/workflows`, `/executions`, `/credentials`, `/nodes`).
   - Support draft-test-validate workflow lifecycle:
     - `create_workflow_draft`: Create or update workflow without activating.
     - `validate_workflow`: Acyclicity verification, schema checking, and node connection validation.
     - `test_workflow`: Execute with test payload and capture execution receipt.
     - `activate_workflow`: Promote validated workflow to active status.
     - `trigger_workflow`: Programmatically trigger workflow execution with structured parameters.
2. **Local n8n Microservice Discovery & Health Probing**:
   - Utilize `LocalServiceProber` to detect running local n8n instances on default port 5678 (or configurable host/port).
   - Fallback to remote n8n instances via base URL and API key authentication.
3. **Secret Isolation & Zero Leaked Secrets (Invariant)**:
   - Credentials strictly referenced by ID or vault key (`credential_id`), never passed as plaintext in workflow definitions, prompt contexts, logs, or tool results.
   - Comprehensive secret scrubber sanitizing Authorization headers and webhook tokens.
4. **Evidence-Based Execution Receipts (Invariant 6)**:
   - Poll execution state until terminal status (`success`, `error`, `crashed`, `waiting`).
   - Return strongly typed `N8nExecutionReceipt` containing `execution_id`, `status`, `duration_ms`, `node_execution_counts`, and output data.
5. **Capability Registration & Substrate Integration**:
   - `n8n.list_workflows`, `n8n.get_workflow`, `n8n.create_workflow`, `n8n.trigger_workflow`, `n8n.get_execution_status`.
   - Wired into `build_real_capability_registry()`, `ArgumentResolver`, and `PolicyEngine`.
6. **100% Offline Testability**:
   - Mock transport and local fixture responses covering all API operations, graph validation, and secret sanitization without requiring an active n8n server.

---

## 3. Strict Goal Boundaries
- Current Goal: `Foundation Gate (Complete) → R1 (Complete) → R2 (Complete) → R3 (Complete) → R4 (Active) → R5`
- **HARD STOP AFTER R5**:
  Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
