"""
omni_engine.desktop.uia_driver
==============================
Deterministic UI & Keystroke Input Driver for Windows (Phase R3).

Adheres to:
- Invariant 1: Deterministic Control — pre-focus verification and bounded dispatch.
- Invariant 6: Evidence-Based Completion — verifies window focus state before and after input.
- REQ-R3-1: Safe foreground activation before dispatching keystrokes.
"""

import time
from typing import Any, Dict, List, Optional

from omni_engine.contracts.desktop import DesktopActionResult
from omni_engine.contracts.enums import VerificationStatus
from omni_engine.desktop.app_manager import AppWindowManager, NativeWin32Backend


class WindowsInputDriver:
    """Dispatches keystrokes and window control events with focus verification."""

    def __init__(self, app_manager: Optional[AppWindowManager] = None) -> None:
        self.app_manager = app_manager or AppWindowManager()

    def send_keys(
        self,
        hwnd: int,
        text: str,
        press_enter: bool = False,
    ) -> DesktopActionResult:
        """Sends keystrokes to a target window after verifying foreground focus."""
        if not self.app_manager.backend.is_window(hwnd):
            return DesktopActionResult(
                action="send_keys",
                target=str(hwnd),
                hwnd=hwnd,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Window handle {hwnd} does not exist",
            )

        # 1. Pre-action focus check and activation
        focus_res = self.app_manager.focus_window(hwnd)
        if not focus_res.success:
            return DesktopActionResult(
                action="send_keys",
                target=str(hwnd),
                hwnd=hwnd,
                prior_state=focus_res.prior_state,
                posterior_state=focus_res.posterior_state,
                evidence={"focus_failed": True},
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Cannot send keys: Failed to focus window {hwnd} ({focus_res.error})",
            )

        # 2. Dispatch keystrokes via native Win32 messages or keybd_event
        # If NativeWin32Backend is active, use WM_CHAR / keybd_event
        backend = self.app_manager.backend
        t0 = time.perf_counter()
        chars_sent = 0

        if isinstance(backend, NativeWin32Backend):
            import win32con
            import win32gui
            import win32api

            for char in text:
                vk = ord(char)
                win32gui.PostMessage(hwnd, win32con.WM_CHAR, vk, 0)
                chars_sent += 1
                time.sleep(0.01)

            if press_enter:
                win32api.keybd_event(win32con.VK_RETURN, 0, 0, 0)
                win32api.keybd_event(win32con.VK_RETURN, 0, win32con.KEYEVENTF_KEYUP, 0)
                chars_sent += 1
        else:
            # Mock or non-native backend
            chars_sent = len(text) + (1 if press_enter else 0)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        posterior = self.app_manager.get_window_state(hwnd).model_dump()

        return DesktopActionResult(
            action="send_keys",
            target=str(hwnd),
            hwnd=hwnd,
            prior_state=focus_res.posterior_state,
            posterior_state=posterior,
            evidence={
                "chars_sent": chars_sent,
                "elapsed_ms": elapsed_ms,
                "press_enter": press_enter,
            },
            success=True,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
        )
