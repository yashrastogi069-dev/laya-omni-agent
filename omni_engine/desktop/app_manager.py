"""
omni_engine.desktop.app_manager
===============================
Windows Application Lifecycle & Window Manager Engine (Phase R3).

Adheres to:
- Invariant 1: Deterministic Control — strongly typed receipts, bounded polling.
- Invariant 6: Evidence-Based Completion — verifies physical HWNDs, PIDs, and window states.
- REQ-R3-1: Non-blocking focus, IsHungAppWindow guard, unminimize-only, async activation poll.
- REQ-R3-2: Baseline window diffing and child-tree traversal resolving process trampolines (Calc, VS Code).
- REQ-R3-4: Intrinsic Rule-0 defense against terminating critical OS processes.
- REQ-R3-5: Decoupled Win32Backend abstraction for 100% offline unit testability.
"""

import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple

import psutil

from omni_engine.contracts.desktop import (
    AppLaunchResult,
    AppWindowInfo,
    DesktopActionResult,
    WindowBounds,
    WindowState,
)
from omni_engine.contracts.enums import VerificationStatus
from omni_engine.policy.rules import is_protected_process


# Known application executable mapping
KNOWN_APP_COMMANDS: Dict[str, List[str]] = {
    "calc": ["calc.exe"],
    "calculator": ["calc.exe"],
    "notepad": ["notepad.exe"],
    "explorer": ["explorer.exe"],
    "terminal": ["powershell.exe"],
    "powershell": ["powershell.exe"],
    "cmd": ["cmd.exe"],
    "code": ["code.cmd"],
    "vscode": ["code.cmd"],
    "vs code": ["code.cmd"],
}


class Win32Backend(ABC):
    """Abstract interface for Windows GUI, window management, and process query APIs."""

    @abstractmethod
    def enum_windows(self) -> List[int]:
        """Enumerates all top-level window handles."""
        raise NotImplementedError

    @abstractmethod
    def is_window(self, hwnd: int) -> bool:
        """Determines whether hwnd identifies an existing window."""
        raise NotImplementedError

    @abstractmethod
    def is_window_visible(self, hwnd: int) -> bool:
        """Determines window visibility."""
        raise NotImplementedError

    @abstractmethod
    def is_iconic(self, hwnd: int) -> bool:
        """Determines if window is minimized."""
        raise NotImplementedError

    @abstractmethod
    def is_zoomed(self, hwnd: int) -> bool:
        """Determines if window is maximized."""
        raise NotImplementedError

    @abstractmethod
    def is_hung(self, hwnd: int) -> bool:
        """Checks if window is unresponsive."""
        raise NotImplementedError

    @abstractmethod
    def get_window_text(self, hwnd: int) -> str:
        """Retrieves window caption text."""
        raise NotImplementedError

    @abstractmethod
    def get_window_rect(self, hwnd: int) -> WindowBounds:
        """Retrieves window bounding rectangle."""
        raise NotImplementedError

    @abstractmethod
    def get_window_thread_process_id(self, hwnd: int) -> Tuple[int, int]:
        """Returns (thread_id, process_id) for the window."""
        raise NotImplementedError

    @abstractmethod
    def get_foreground_window(self) -> int:
        """Returns HWND of the current foreground window."""
        raise NotImplementedError

    @abstractmethod
    def set_foreground_window(self, hwnd: int) -> bool:
        """Activates and brings window to the foreground."""
        raise NotImplementedError

    @abstractmethod
    def show_window_async(self, hwnd: int, cmd: int) -> bool:
        """Sets show state asynchronously."""
        raise NotImplementedError

    @abstractmethod
    def post_close_message(self, hwnd: int) -> bool:
        """Posts WM_CLOSE message to the window."""
        raise NotImplementedError


class NativeWin32Backend(Win32Backend):
    """Production Win32 API implementation using pywin32 and ctypes."""

    def __init__(self) -> None:
        import ctypes
        import win32api
        import win32con
        import win32gui
        import win32process

        self._win32gui = win32gui
        self._win32process = win32process
        self._win32con = win32con
        self._win32api = win32api
        self._ctypes = ctypes
        self._user32 = ctypes.windll.user32

        # REC-R3-7: Set DPI awareness for accurate coordinates
        try:
            self._ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
        except Exception:
            try:
                self._user32.SetProcessDPIAware()
            except Exception:
                pass

    def enum_windows(self) -> List[int]:
        hwnds: List[int] = []

        def _enum_cb(hwnd: int, extra: Any) -> bool:
            hwnds.append(hwnd)
            return True

        self._win32gui.EnumWindows(_enum_cb, None)
        return hwnds

    def is_window(self, hwnd: int) -> bool:
        return bool(self._win32gui.IsWindow(hwnd))

    def is_window_visible(self, hwnd: int) -> bool:
        return bool(self._win32gui.IsWindowVisible(hwnd))

    def is_iconic(self, hwnd: int) -> bool:
        return bool(self._win32gui.IsIconic(hwnd))

    def is_zoomed(self, hwnd: int) -> bool:
        # IsZoomed in Win32
        return bool(self._user32.IsZoomed(hwnd))

    def is_hung(self, hwnd: int) -> bool:
        # REQ-R3-1: IsHungAppWindow
        return bool(self._user32.IsHungAppWindow(hwnd))

    def get_window_text(self, hwnd: int) -> str:
        return str(self._win32gui.GetWindowText(hwnd) or "")

    def get_window_rect(self, hwnd: int) -> WindowBounds:
        rect = self._win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        return WindowBounds(
            left=left,
            top=top,
            right=right,
            bottom=bottom,
            width=max(0, right - left),
            height=max(0, bottom - top),
        )

    def get_window_thread_process_id(self, hwnd: int) -> Tuple[int, int]:
        thread_id, pid = self._win32process.GetWindowThreadProcessId(hwnd)
        return thread_id, pid

    def get_foreground_window(self) -> int:
        return int(self._win32gui.GetForegroundWindow() or 0)

    def set_foreground_window(self, hwnd: int) -> bool:
        # REQ-R3-1: Simulate innocuous menu key to gain foreground activation rights
        try:
            self._win32api.keybd_event(self._win32con.VK_MENU, 0, 0, 0)
            self._win32api.keybd_event(self._win32con.VK_MENU, 0, self._win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

        try:
            return bool(self._win32gui.SetForegroundWindow(hwnd))
        except Exception:
            return False

    def show_window_async(self, hwnd: int, cmd: int) -> bool:
        return bool(self._win32gui.ShowWindow(hwnd, cmd))

    def post_close_message(self, hwnd: int) -> bool:
        try:
            self._win32gui.PostMessage(hwnd, self._win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False


class AppWindowManager:
    """Master application launcher, window inspector, and focus coordinator."""

    def __init__(self, backend: Optional[Win32Backend] = None) -> None:
        if backend is not None:
            self.backend = backend
        else:
            self.backend = NativeWin32Backend()

    def list_windows(
        self,
        filter_title: Optional[str] = None,
        visible_only: bool = True,
    ) -> List[AppWindowInfo]:
        """Enumerates active desktop windows with titles and process metadata."""
        all_hwnds = self.backend.enum_windows()
        foreground_hwnd = self.backend.get_foreground_window()
        windows: List[AppWindowInfo] = []

        filter_lower = filter_title.lower().strip() if filter_title else None

        for hwnd in all_hwnds:
            if not self.backend.is_window(hwnd):
                continue
            is_vis = self.backend.is_window_visible(hwnd)
            if visible_only and not is_vis:
                continue

            title = self.backend.get_window_text(hwnd)
            if visible_only and not title.strip():
                continue

            if filter_lower and filter_lower not in title.lower():
                continue

            try:
                _, pid = self.backend.get_window_thread_process_id(hwnd)
                try:
                    proc_name = psutil.Process(pid).name()
                except Exception:
                    proc_name = "unknown"
            except Exception:
                pid = 0
                proc_name = "unknown"

            try:
                bounds = self.backend.get_window_rect(hwnd)
            except Exception:
                bounds = WindowBounds(left=0, top=0, right=0, bottom=0, width=0, height=0)

            is_iconic = self.backend.is_iconic(hwnd)
            is_zoomed = self.backend.is_zoomed(hwnd)
            is_active = (hwnd == foreground_hwnd)

            windows.append(
                AppWindowInfo(
                    hwnd=hwnd,
                    title=title,
                    process_name=proc_name,
                    pid=pid,
                    is_active=is_active,
                    is_minimized=is_iconic,
                    is_maximized=is_zoomed,
                    is_visible=is_vis,
                    bounds=bounds,
                )
            )

        return windows

    def find_window(self, query: str) -> Optional[AppWindowInfo]:
        """Finds the best matching window by caption substring or process name."""
        q_lower = query.lower().strip()
        windows = self.list_windows(visible_only=True)

        # 1. Exact title match
        for w in windows:
            if w.title.lower() == q_lower:
                return w

        # 2. Substring in title
        for w in windows:
            if q_lower in w.title.lower():
                return w

        # 3. Process name match
        for w in windows:
            if q_lower in w.process_name.lower() or f"{q_lower}.exe" == w.process_name.lower():
                return w

        return None

    def get_window_state(self, hwnd: int) -> WindowState:
        """Retrieves live dynamic state for a given window handle."""
        if not self.backend.is_window(hwnd):
            return WindowState(
                is_foreground=False,
                is_minimized=False,
                is_maximized=False,
                is_visible=False,
                is_hung=False,
                bounds=None,
            )

        is_fg = (self.backend.get_foreground_window() == hwnd)
        is_min = self.backend.is_iconic(hwnd)
        is_max = self.backend.is_zoomed(hwnd)
        is_vis = self.backend.is_window_visible(hwnd)
        is_hung = self.backend.is_hung(hwnd)

        try:
            bounds = self.backend.get_window_rect(hwnd)
        except Exception:
            bounds = None

        return WindowState(
            is_foreground=is_fg,
            is_minimized=is_min,
            is_maximized=is_max,
            is_visible=is_vis,
            is_hung=is_hung,
            bounds=bounds,
        )

    def focus_window(self, hwnd: int, timeout: float = 0.5) -> DesktopActionResult:
        """Brings the target window to the foreground with hung app guard and verification.
        
        REQ-R3-1: Checks IsHungAppWindow, unminimizes only if iconic, polls for activation.
        """
        if not self.backend.is_window(hwnd):
            return DesktopActionResult(
                action="focus",
                target=str(hwnd),
                hwnd=hwnd,
                prior_state=None,
                posterior_state=None,
                evidence={"error": "HWND does not exist"},
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Window handle {hwnd} does not exist",
            )

        prior_state = self.get_window_state(hwnd).model_dump()

        # REQ-R3-1: Guard against hanging on unresponsive windows
        if self.backend.is_hung(hwnd):
            return DesktopActionResult(
                action="focus",
                target=str(hwnd),
                hwnd=hwnd,
                prior_state=prior_state,
                posterior_state=prior_state,
                evidence={"is_hung": True},
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Target window {hwnd} is unresponsive/hung (IsHungAppWindow=True)",
            )

        # REQ-R3-1: Unminimize only if minimized (SW_RESTORE = 9)
        if self.backend.is_iconic(hwnd):
            self.backend.show_window_async(hwnd, 9)

        # Set foreground
        self.backend.set_foreground_window(hwnd)

        # REQ-R3-1: Asynchronous activation polling (up to timeout)
        t0 = time.perf_counter()
        is_focused = False
        while (time.perf_counter() - t0) <= timeout:
            if self.backend.get_foreground_window() == hwnd:
                is_focused = True
                break
            time.sleep(0.05)

        posterior_state = self.get_window_state(hwnd).model_dump()
        evidence = {
            "foreground_hwnd": self.backend.get_foreground_window(),
            "target_hwnd": hwnd,
            "poll_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

        v_status = VerificationStatus.VERIFIED_SUCCESS if is_focused else VerificationStatus.VERIFIED_FAILURE
        return DesktopActionResult(
            action="focus",
            target=str(hwnd),
            hwnd=hwnd,
            prior_state=prior_state,
            posterior_state=posterior_state,
            evidence=evidence,
            success=is_focused,
            verification_status=v_status,
            error=None if is_focused else f"Window {hwnd} did not acquire foreground focus within {timeout}s",
        )

    def close_window(self, hwnd: int, timeout: float = 1.0) -> DesktopActionResult:
        """Sends WM_CLOSE to window and verifies closure, enforcing Rule-0 process defense.
        
        REQ-R3-4: Intrinsic check prevents closing windows of critical system processes.
        """
        if not self.backend.is_window(hwnd):
            return DesktopActionResult(
                action="close",
                target=str(hwnd),
                hwnd=hwnd,
                prior_state=None,
                posterior_state=None,
                evidence={"already_closed": True},
                success=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
            )

        # REQ-R3-4: Intrinsic Rule-0 defense against critical system processes
        try:
            _, pid = self.backend.get_window_thread_process_id(hwnd)
            proc = psutil.Process(pid)
            proc_name = proc.name()
            is_prot, reason = is_protected_process(pid)
            if not is_prot:
                is_prot, reason = is_protected_process(proc_name)
            if is_prot:
                return DesktopActionResult(
                    action="close",
                    target=str(hwnd),
                    hwnd=hwnd,
                    evidence={"rule_0_blocked": True, "pid": pid, "process": proc_name},
                    success=False,
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                    error=f"Rule-0 Invariant Violation: Cannot close protected process {proc_name} (PID: {pid}): {reason}",
                )
        except Exception:
            pass

        prior_state = self.get_window_state(hwnd).model_dump()
        self.backend.post_close_message(hwnd)

        # Verification poll for window disappearance
        t0 = time.perf_counter()
        closed = False
        while (time.perf_counter() - t0) <= timeout:
            if not self.backend.is_window(hwnd):
                closed = True
                break
            time.sleep(0.05)

        posterior_state = self.get_window_state(hwnd).model_dump() if not closed else None
        evidence = {
            "window_destroyed": closed,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        }
        v_status = VerificationStatus.VERIFIED_SUCCESS if closed else VerificationStatus.VERIFIED_FAILURE

        return DesktopActionResult(
            action="close",
            target=str(hwnd),
            hwnd=hwnd,
            prior_state=prior_state,
            posterior_state=posterior_state,
            evidence=evidence,
            success=closed,
            verification_status=v_status,
            error=None if closed else f"Window {hwnd} did not close within {timeout}s",
        )

    def terminate_process(self, pid: int, timeout: float = 2.0) -> DesktopActionResult:
        """Terminates an OS process by PID with Rule-0 hard invariant protection."""
        # REQ-R3-4: Intrinsic Rule-0 defense
        is_prot, reason = is_protected_process(pid)
        if is_prot:
            return DesktopActionResult(
                action="terminate_process",
                target=str(pid),
                evidence={"rule_0_blocked": True, "pid": pid},
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Rule-0 Invariant Violation: Cannot terminate protected PID {pid}: {reason}",
            )

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
            is_prot_name, reason_name = is_protected_process(proc_name)
            if is_prot_name:
                return DesktopActionResult(
                    action="terminate_process",
                    target=str(pid),
                    evidence={"rule_0_blocked": True, "pid": pid, "process": proc_name},
                    success=False,
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                    error=f"Rule-0 Invariant Violation: Cannot terminate protected process {proc_name}: {reason_name}",
                )

            prior_state = {"pid": pid, "name": proc_name, "status": proc.status()}
            proc.terminate()
            proc.wait(timeout=timeout)

            return DesktopActionResult(
                action="terminate_process",
                target=str(pid),
                prior_state=prior_state,
                posterior_state={"is_running": False},
                evidence={"terminated": True, "pid": pid},
                success=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
            )

        except psutil.NoSuchProcess:
            return DesktopActionResult(
                action="terminate_process",
                target=str(pid),
                evidence={"already_terminated": True},
                success=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
            )
        except Exception as e:
            return DesktopActionResult(
                action="terminate_process",
                target=str(pid),
                evidence={"exception": str(e)},
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Failed to terminate process {pid}: {e}",
            )

    def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        timeout: float = 3.0,
    ) -> AppLaunchResult:
        """Launches an application with process trampoline & window appearance verification.
        
        REQ-R3-2: Captures baseline HWNDs, inspects child processes, resolves trampolines.
        """
        t0 = time.perf_counter()
        clean_app = app_name.lower().strip()
        cmd = KNOWN_APP_COMMANDS.get(clean_app)

        if not cmd:
            cmd = [clean_app]

        if args:
            cmd.extend(args)

        # REQ-R3-2: Pre-launch baseline top-level HWNDs
        baseline_hwnds: Set[int] = set(self.backend.enum_windows())

        try:
            p = subprocess.Popen(
                cmd,
                shell=(sys.platform == "win32" and cmd[0].endswith((".cmd", ".bat"))),
            )
            launcher_pid = p.pid
        except Exception as e:
            startup_ms = round((time.perf_counter() - t0) * 1000, 2)
            return AppLaunchResult(
                app_name=app_name,
                launcher_pid=None,
                active_pid=None,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                startup_time_ms=startup_ms,
                error=f"Failed to execute '{cmd[0]}': {e}",
            )

        # REQ-R3-2: Polling for window and active PID across direct, child, and diff paths
        active_pid: Optional[int] = None
        target_hwnd: Optional[int] = None
        window_title: Optional[str] = None
        bounds: Optional[WindowBounds] = None
        proc_name: Optional[str] = None

        poll_start = time.perf_counter()
        while (time.perf_counter() - poll_start) <= timeout:
            current_hwnds = self.backend.enum_windows()
            new_hwnds = [h for h in current_hwnds if h not in baseline_hwnds]

            # Path A: Direct PID match
            for h in current_hwnds:
                try:
                    _, h_pid = self.backend.get_window_thread_process_id(h)
                    if h_pid == launcher_pid and self.backend.is_window_visible(h):
                        target_hwnd = h
                        active_pid = launcher_pid
                        break
                except Exception:
                    continue

            # Path B: Child process traversal via psutil
            if not target_hwnd:
                try:
                    proc = psutil.Process(launcher_pid)
                    children_pids = {c.pid for c in proc.children(recursive=True)}
                    for h in current_hwnds:
                        try:
                            _, h_pid = self.backend.get_window_thread_process_id(h)
                            if h_pid in children_pids and self.backend.is_window_visible(h):
                                target_hwnd = h
                                active_pid = h_pid
                                break
                        except Exception:
                            continue
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Path C: Window diff matching (trampoline resolution)
            if not target_hwnd and new_hwnds:
                for h in new_hwnds:
                    if self.backend.is_window_visible(h):
                        txt = self.backend.get_window_text(h)
                        try:
                            _, h_pid = self.backend.get_window_thread_process_id(h)
                            h_pname = psutil.Process(h_pid).name().lower()
                        except Exception:
                            h_pid = launcher_pid
                            h_pname = clean_app

                        # Match title or process name
                        if clean_app in txt.lower() or clean_app in h_pname:
                            target_hwnd = h
                            active_pid = h_pid
                            break
                # If still none, take the first visible new window
                if not target_hwnd and new_hwnds:
                    for h in new_hwnds:
                        if self.backend.is_window_visible(h) and self.backend.get_window_text(h):
                            target_hwnd = h
                            try:
                                _, active_pid = self.backend.get_window_thread_process_id(h)
                            except Exception:
                                active_pid = launcher_pid
                            break

            if target_hwnd:
                break

            time.sleep(0.1)

        startup_ms = round((time.perf_counter() - t0) * 1000, 2)
        exit_code = p.poll()

        if target_hwnd:
            window_title = self.backend.get_window_text(target_hwnd)
            try:
                bounds = self.backend.get_window_rect(target_hwnd)
            except Exception:
                bounds = None
            try:
                proc_name = psutil.Process(active_pid or launcher_pid).name()
            except Exception:
                proc_name = clean_app

            return AppLaunchResult(
                app_name=app_name,
                launcher_pid=launcher_pid,
                active_pid=active_pid or launcher_pid,
                process_name=proc_name,
                hwnd=target_hwnd,
                window_title=window_title,
                bounds=bounds,
                exit_code=exit_code,
                success=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
                startup_time_ms=startup_ms,
            )

        # Did launcher exit with error without producing a window?
        if exit_code is not None and exit_code != 0:
            return AppLaunchResult(
                app_name=app_name,
                launcher_pid=launcher_pid,
                active_pid=None,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                exit_code=exit_code,
                startup_time_ms=startup_ms,
                error=f"Process exited with non-zero code {exit_code} without creating a window",
            )

        # Process is running or exited cleanly, but no window was discovered
        # (Could be a background daemon)
        is_running = psutil.pid_exists(launcher_pid)
        return AppLaunchResult(
            app_name=app_name,
            launcher_pid=launcher_pid,
            active_pid=launcher_pid if is_running else None,
            process_name=clean_app,
            hwnd=None,
            window_title=None,
            bounds=None,
            exit_code=exit_code,
            success=is_running,
            verification_status=VerificationStatus.VERIFIED_SUCCESS if is_running else VerificationStatus.VERIFIED_FAILURE,
            startup_time_ms=startup_ms,
            error=None if is_running else f"No window detected for '{app_name}' within {timeout}s",
        )
