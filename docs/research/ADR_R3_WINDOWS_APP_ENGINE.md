# ADR_R3_WINDOWS_APP_ENGINE.md — Windows Desktop, Application & Local Service Engine Architecture

## Status
**ACCEPTED (Post Adversarial Plan Review)**

## Context & Problem Statement
In Phase R3 of the LAYA Omni Agent roadmap, the agent requires real capability engines to interact with the host Windows 10/11 operating system:
1. **Application Lifecycle Management**: Launching desktop applications (Notepad, Calculator, VS Code, Slack, terminal), discovering their window handles (`HWND`), focusing windows, and gracefully terminating processes.
2. **Local Service & Microservice Probing**: Deterministically verifying the health and port readiness of local background services (e.g., n8n workflow server on port 5678, Ollama LLM daemon on port 11434, Antigravity CLI server, local web servers on 3000/8000/8080).
3. **Desktop Interaction Primitives**: Inspecting window bounds/titles, bringing windows to the foreground, sending keystrokes/hotkeys, and closing windows.
4. **Evidence-Based Completion**: Complying strictly with Invariant 6: the agent must **never** report an app launched or a service started without verifying real-world physical outcome receipts (`pid` alive in `psutil`, `HWND` discovered in Win32 window table, port accepting TCP connections).

---

## Adversarial Plan Review Remediations (REQ-R3-1 to REQ-R3-6)

| ID | Requirement | Severity | Implementation Architecture |
| :--- | :--- | :--- | :--- |
| **REQ-R3-1** | Window Focus Deadlock Guard | **BLOCKING** | Pre-check `IsHungAppWindow(hwnd)`; use non-blocking menu key simulation for foreground rights; unminimize via `ShowWindowAsync(SW_RESTORE)` only if `IsIconic(hwnd)`; async activation polling (up to 500ms). |
| **REQ-R3-2** | Process Trampoline Verification | **BLOCKING** | Capture visible window baseline before launch (`baseline_hwnds`); poll across direct PID, `psutil` child-tree, and `current_hwnds - baseline_hwnds` window diffing. Capture `launcher_pid` and `active_pid`. |
| **REQ-R3-3** | Service Probing Dual-Stack & Hygiene | **BLOCKING** | Dual-stack cascade (`127.0.0.1` -> `::1`); `SO_LINGER` set to prevent `TIME_WAIT` socket accumulation; dedicated `ProxyHandler({})` opener to bypass host proxies; 4KB bounded HTTP read; 500ms socket / 1.5s HTTP timeouts. |
| **REQ-R3-4** | Rule-0 Hard Invariant Expansion | **BLOCKING** | Extend `PolicyEngine` Stage 0 to `("kill_process", "desktop.kill_process", "desktop.close_window", "desktop.terminate_app")`. Intrinsic defense in `AppWindowManager` checking PID/process name before closing/terminating. |
| **REQ-R3-5** | Offline Test Suite Isolation | **BLOCKING** | Decouple `AppWindowManager` via `Win32Backend` abstraction; test with mock handles and ephemeral loopback socket/HTTP server (<1.5s runtime, zero live window popups). |
| **REQ-R3-6** | Capability Substrate Wiring | **BLOCKING** | Register canonical `desktop.*` capabilities in `definitions.py`; update `build_real_capability_registry()`; wire slot extractors in `resolver.py`; map blast radii in `policy/engine.py`. |

---

## Technology Audit & Candidate Evaluation

| Technology | Evaluation | Verdict | Rationale |
| :--- | :--- | :--- | :--- |
| **`win32gui` / `win32process` / `win32api` / `win32con` (pywin32)** | Native Windows API wrapper already installed in environment. Provides sub-millisecond window enumeration (`EnumWindows`), window title extraction (`GetWindowText`), focus control (`SetForegroundWindow`), window placement (`GetWindowRect`), and message dispatch (`WM_CLOSE`, `WM_CHAR`). | **ADOPT** | High performance, deterministic, zero additional dependencies, direct OS API grounding. |
| **`psutil` (5.9.8)** | Process and system monitoring library already installed in environment. Provides process tree discovery, PID verification, memory/CPU statistics, and clean process termination. | **ADOPT** | Industry standard for cross-platform process management; robust error handling on Windows (`NoSuchProcess`, `AccessDenied`). |
| **Standard Library `socket` & `urllib.request`** | Native Python networking stack. Allows sub-millisecond TCP port connect probing (`socket.create_connection`) and HTTP health endpoint inspection without external requests dependencies. | **ADOPT** | Fast (<5ms per probe), deterministic timeout bounds, zero memory overhead. |
| **`ctypes.windll.user32` / `kernel32`** | Native C-level Windows runtime integration for low-level thread attachment (`AttachThreadInput`), DPI awareness (`SetProcessDpiAwarenessContext`), and keyboard event dispatch. | **ADOPT** | Provides fallback and precise Win32 control when thread input queues are locked. |
| **`pywinauto`** | High-level accessibility (UIA / MSAA) automation framework. | **REJECT** | Not installed in environment. Heavyweight overhead and slow window discovery loops. Native Win32 + ctypes provides superior speed (<1ms) and deterministic control. |
| **`pyautogui`** | Coordinate-based mouse and keyboard simulation. | **REJECT** | Not installed in environment. Coordinate-based automation is brittle to screen resolution and DPI changes, and risks interfering with the user's physical input. |

---

## Contract Schemas (`omni_engine/contracts/desktop.py`)
```python
class WindowBounds(BaseContractModel):
    left: int
    top: int
    right: int
    bottom: int
    width: int
    height: int

class WindowState(BaseContractModel):
    is_foreground: bool
    is_minimized: bool
    is_maximized: bool
    is_visible: bool
    is_hung: bool
    bounds: Optional[WindowBounds] = None

class AppWindowInfo(BaseContractModel):
    hwnd: int
    title: str
    process_name: str
    pid: int
    is_active: bool
    is_minimized: bool
    is_maximized: bool
    is_visible: bool
    bounds: WindowBounds

class AppLaunchResult(BaseContractModel):
    app_name: str
    launcher_pid: Optional[int] = None
    active_pid: Optional[int] = None
    process_name: Optional[str] = None
    hwnd: Optional[int] = None
    window_title: Optional[str] = None
    bounds: Optional[WindowBounds] = None
    exit_code: Optional[int] = None
    success: bool
    verification_status: VerificationStatus
    startup_time_ms: float
    error: Optional[str] = None

class ServiceHealthStatus(BaseContractModel):
    service_name: str
    host: str
    port: int
    is_listening: bool
    http_status: Optional[int] = None
    response_time_ms: float
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

class DesktopActionResult(BaseContractModel):
    action: str
    target: str
    hwnd: Optional[int] = None
    prior_state: Optional[Dict[str, Any]] = None
    posterior_state: Optional[Dict[str, Any]] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    success: bool
    verification_status: VerificationStatus
    error: Optional[str] = None
```
