"""
omni_engine.desktop.engine
==========================
Master ComputerUseDriver & Windows Local Service Engine (Phase R3).

Unifies:
1. AppWindowManager: Application lifecycle, process trampoline resolution, window focus & close.
2. LocalServiceProber: Dual-stack TCP port connect & HTTP health verification (n8n, Ollama, dev servers).
3. WindowsInputDriver: Verified foreground keyboard & UI interaction.
"""

from typing import Any, Dict, List, Optional, Union

from omni_engine.contracts.desktop import (
    AppLaunchResult,
    AppWindowInfo,
    DesktopActionResult,
    ServiceHealthStatus,
)
from omni_engine.contracts.enums import VerificationStatus
from omni_engine.desktop.app_manager import AppWindowManager, Win32Backend
from omni_engine.desktop.service import LocalServiceProber
from omni_engine.desktop.uia_driver import WindowsInputDriver


class ComputerUseDriver:
    """Composite driver coordinating desktop applications, windows, and local services."""

    def __init__(
        self,
        app_manager: Optional[AppWindowManager] = None,
        service_prober: Optional[LocalServiceProber] = None,
        input_driver: Optional[WindowsInputDriver] = None,
        backend: Optional[Win32Backend] = None,
    ) -> None:
        if app_manager is not None:
            self.app_manager = app_manager
        elif backend is not None:
            self.app_manager = AppWindowManager(backend=backend)
        else:
            self.app_manager = AppWindowManager()

        self.service_prober = service_prober or LocalServiceProber()
        self.input_driver = input_driver or WindowsInputDriver(app_manager=self.app_manager)

    def _resolve_hwnd(self, query_or_hwnd: Union[int, str]) -> Optional[int]:
        """Resolves an integer HWND or string window title/process to a window handle."""
        if isinstance(query_or_hwnd, int):
            return query_or_hwnd
        if isinstance(query_or_hwnd, str) and query_or_hwnd.isdigit():
            return int(query_or_hwnd)

        w = self.app_manager.find_window(str(query_or_hwnd))
        return w.hwnd if w else None

    def launch_app(
        self,
        app_name: str,
        args: Optional[List[str]] = None,
        timeout: float = 3.0,
    ) -> AppLaunchResult:
        """Launches an application and returns verified PID and HWND evidence."""
        return self.app_manager.launch_app(app_name=app_name, args=args, timeout=timeout)

    def list_windows(
        self,
        filter_title: Optional[str] = None,
        visible_only: bool = True,
    ) -> List[AppWindowInfo]:
        """Lists active top-level desktop windows."""
        return self.app_manager.list_windows(filter_title=filter_title, visible_only=visible_only)

    def focus_window(
        self,
        target: Union[int, str],
        timeout: float = 0.5,
    ) -> DesktopActionResult:
        """Brings the designated window to the foreground."""
        hwnd = self._resolve_hwnd(target)
        if hwnd is None:
            return DesktopActionResult(
                action="focus",
                target=str(target),
                hwnd=None,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"No matching window found for '{target}'",
            )
        return self.app_manager.focus_window(hwnd=hwnd, timeout=timeout)

    def close_window(
        self,
        target: Union[int, str],
        timeout: float = 1.0,
    ) -> DesktopActionResult:
        """Closes the designated window (with Rule-0 protected process check)."""
        hwnd = self._resolve_hwnd(target)
        if hwnd is None:
            return DesktopActionResult(
                action="close",
                target=str(target),
                hwnd=None,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"No matching window found for '{target}'",
            )
        return self.app_manager.close_window(hwnd=hwnd, timeout=timeout)

    def check_service(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        http_path: Optional[str] = None,
    ) -> ServiceHealthStatus:
        """Probes health and readiness of a local background service (e.g. n8n, Ollama)."""
        return self.service_prober.check_service(
            service_name=service_name,
            host=host,
            port=port,
            http_path=http_path,
        )

    def send_keys(
        self,
        target: Union[int, str],
        text: str,
        press_enter: bool = False,
    ) -> DesktopActionResult:
        """Sends keystrokes to target window after bringing it to the foreground."""
        hwnd = self._resolve_hwnd(target)
        if hwnd is None:
            return DesktopActionResult(
                action="send_keys",
                target=str(target),
                hwnd=None,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"No matching window found for '{target}'",
            )
        return self.input_driver.send_keys(hwnd=hwnd, text=text, press_enter=press_enter)
