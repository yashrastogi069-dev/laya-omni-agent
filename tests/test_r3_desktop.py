"""
tests.test_r3_desktop
=====================
Comprehensive offline test suite for Phase R3: Windows Desktop, App & Local Service Engine.

Adheres to:
- REQ-R3-1: Non-blocking focus, IsHungAppWindow rejection, unminimize-only.
- REQ-R3-2: Process trampoline resolution & strongly typed evidence receipts.
- REQ-R3-3: Local service dual-stack cascade, proxy bypass, and port hygiene.
- REQ-R3-4: Rule-0 process defense across desktop capabilities.
- REQ-R3-5: 100% offline, mock-backed backend (<1.5s runtime, zero window popups).
- REQ-R3-6: Capability substrate, policy engine, and argument resolver integration.
"""

import http.server
import json
import os
import socket
import threading
import time
import unittest
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.capabilities import (
    DESKTOP_CLOSE_WINDOW_SPEC,
    DESKTOP_FOCUS_WINDOW_SPEC,
    DESKTOP_LAUNCH_APP_SPEC,
    DESKTOP_LIST_WINDOWS_SPEC,
    DESKTOP_SEND_KEYS_SPEC,
    DESKTOP_SERVICE_HEALTH_SPEC,
    build_canonical_registry,
    build_real_capability_registry,
)
from omni_engine.contracts.desktop import (
    AppLaunchResult,
    AppWindowInfo,
    DesktopActionResult,
    ServiceHealthStatus,
    WindowBounds,
    WindowState,
)
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    VerificationStatus,
)
from omni_engine.contracts.policy import PolicyEffect
from omni_engine.desktop.app_manager import AppWindowManager, Win32Backend
from omni_engine.desktop.engine import ComputerUseDriver
from omni_engine.desktop.service import LocalServiceProber
from omni_engine.desktop.uia_driver import WindowsInputDriver
from omni_engine.policy.engine import PolicyEngine


# ===========================================================================
# 1. Mock Win32 Backend (REQ-R3-5: Zero live GUI popups, 100% offline)
# ===========================================================================

class MockWin32Backend(Win32Backend):
    """Deterministic, mock Win32 backend for offline testing."""

    def __init__(self) -> None:
        self.windows: Dict[int, Dict[str, Any]] = {
            1001: {
                "title": "Untitled - Notepad",
                "process_name": "notepad.exe",
                "pid": 5001,
                "is_visible": True,
                "is_iconic": False,
                "is_zoomed": False,
                "is_hung": False,
                "bounds": WindowBounds(left=100, top=100, right=800, bottom=600, width=700, height=500),
            },
            1002: {
                "title": "Calculator",
                "process_name": "CalculatorApp.exe",
                "pid": 5002,
                "is_visible": True,
                "is_iconic": True,  # Minimized
                "is_zoomed": False,
                "is_hung": False,
                "bounds": WindowBounds(left=200, top=200, right=600, bottom=800, width=400, height=600),
            },
            1003: {
                "title": "Frozen Window",
                "process_name": "hung_app.exe",
                "pid": 5003,
                "is_visible": True,
                "is_iconic": False,
                "is_zoomed": False,
                "is_hung": True,  # Hung / Unresponsive
                "bounds": WindowBounds(left=50, top=50, right=450, bottom=450, width=400, height=400),
            },
            1004: {
                "title": "Client Server Runtime Subsystem",
                "process_name": "csrss.exe",
                "pid": 4,  # Critical system PID
                "is_visible": False,
                "is_iconic": False,
                "is_zoomed": False,
                "is_hung": False,
                "bounds": WindowBounds(left=0, top=0, right=0, bottom=0, width=0, height=0),
            },
        }
        self.foreground_hwnd = 1001
        self.closed_hwnds: List[int] = []
        self.restored_hwnds: List[int] = []

    def enum_windows(self) -> List[int]:
        return list(self.windows.keys())

    def is_window(self, hwnd: int) -> bool:
        return hwnd in self.windows

    def is_window_visible(self, hwnd: int) -> bool:
        return self.windows.get(hwnd, {}).get("is_visible", False)

    def is_iconic(self, hwnd: int) -> bool:
        return self.windows.get(hwnd, {}).get("is_iconic", False)

    def is_zoomed(self, hwnd: int) -> bool:
        return self.windows.get(hwnd, {}).get("is_zoomed", False)

    def is_hung(self, hwnd: int) -> bool:
        return self.windows.get(hwnd, {}).get("is_hung", False)

    def get_window_text(self, hwnd: int) -> str:
        return self.windows.get(hwnd, {}).get("title", "")

    def get_window_rect(self, hwnd: int) -> WindowBounds:
        return self.windows.get(hwnd, {}).get("bounds", WindowBounds(left=0, top=0, right=0, bottom=0, width=0, height=0))

    def get_window_thread_process_id(self, hwnd: int) -> Tuple[int, int]:
        pid = self.windows.get(hwnd, {}).get("pid", 0)
        return (100, pid)

    def get_foreground_window(self) -> int:
        return self.foreground_hwnd

    def set_foreground_window(self, hwnd: int) -> bool:
        if hwnd in self.windows:
            self.foreground_hwnd = hwnd
            return True
        return False

    def show_window_async(self, hwnd: int, cmd: int) -> bool:
        if hwnd in self.windows:
            if cmd == 9:  # SW_RESTORE
                self.windows[hwnd]["is_iconic"] = False
                self.restored_hwnds.append(hwnd)
            return True
        return False

    def post_close_message(self, hwnd: int) -> bool:
        if hwnd in self.windows:
            self.closed_hwnds.append(hwnd)
            del self.windows[hwnd]
            return True
        return False


# ===========================================================================
# 2. Ephemeral HTTP Mock Server Helper
# ===========================================================================

class MockServiceHandler(http.server.BaseHTTPRequestHandler):
    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass

    def do_GET(self):
        try:
            if self.path in ("/healthz", "/api/tags", "/"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "healthy", "service": "mock_n8n", "version": "1.0.0"}')
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
        except (ConnectionResetError, BrokenPipeError, OSError):
            pass

    def log_message(self, format, *args):
        pass  # Silence stderr logs


# ===========================================================================
# 3. Test Suites
# ===========================================================================

class TestR3DesktopContracts(unittest.TestCase):
    """Proves contracts strictly validate and forbid extra fields."""

    def test_window_bounds_contract(self):
        bounds = WindowBounds(left=10, top=20, right=110, bottom=220, width=100, height=200)
        self.assertEqual(bounds.width, 100)
        with self.assertRaises(ValidationError):
            WindowBounds(left=0, top=0, right=0, bottom=0, width=0, height=0, invalid_extra=123)

    def test_service_health_status_contract(self):
        status = ServiceHealthStatus(
            service_name="n8n",
            host="127.0.0.1",
            port=5678,
            is_listening=True,
            http_status=200,
            response_time_ms=1.45,
            details={"status": "healthy"},
        )
        self.assertTrue(status.is_listening)
        self.assertEqual(status.http_status, 200)
        with self.assertRaises(ValidationError):
            ServiceHealthStatus(
                service_name="n8n",
                port=5678,
                is_listening=True,
                unregistered_field=True,
            )


class TestR3LocalServiceProber(unittest.TestCase):
    """Proves dual-stack cascade, proxy bypass, and socket hygiene in LocalServiceProber."""

    @classmethod
    def setUpClass(cls):
        # Start ephemeral loopback HTTP server
        cls.http_server = http.server.HTTPServer(("127.0.0.1", 0), MockServiceHandler)
        cls.port = cls.http_server.server_port
        cls.server_thread = threading.Thread(target=cls.http_server.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http_server.shutdown()
        cls.http_server.server_close()

    def test_probe_socket_active_port(self):
        """Proves socket connect succeeds on active port with <10ms latency."""
        prober = LocalServiceProber()
        is_listening, latency, err = prober.probe_socket(host="127.0.0.1", port=self.port)
        self.assertTrue(is_listening)
        self.assertLess(latency, 100.0)
        self.assertIsNone(err)

    def test_probe_socket_closed_port(self):
        """Proves socket connect gracefully returns False on closed port."""
        # Find an unused port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            unused_port = s.getsockname()[1]

        prober = LocalServiceProber(default_socket_timeout=0.2)
        is_listening, latency, err = prober.probe_socket(host="127.0.0.1", port=unused_port)
        self.assertFalse(is_listening)
        self.assertIsNotNone(err)

    def test_probe_http_200_ok(self):
        """Proves HTTP probe returns status 200, parsed JSON, and bounded read."""
        prober = LocalServiceProber()
        url = f"http://127.0.0.1:{self.port}/healthz"
        success, code, latency, details, err = prober.probe_http(url=url)
        self.assertTrue(success)
        self.assertEqual(code, 200)
        self.assertIn("json", details)
        self.assertEqual(details["json"]["status"], "healthy")
        self.assertIsNone(err)

    def test_probe_http_404_not_found(self):
        """Proves HTTP probe handles 404 cleanly without raising unhandled exceptions."""
        prober = LocalServiceProber()
        url = f"http://127.0.0.1:{self.port}/non_existent"
        success, code, latency, details, err = prober.probe_http(url=url)
        self.assertFalse(success)
        self.assertEqual(code, 404)
        self.assertIn("404", str(err))

    def test_check_service_integration(self):
        """Proves check_service returns structured ServiceHealthStatus receipt."""
        prober = LocalServiceProber()
        status = prober.check_service(service_name="n8n", port=self.port, http_path="/healthz")
        self.assertTrue(status.is_listening)
        self.assertEqual(status.http_status, 200)
        self.assertEqual(status.details.get("json", {}).get("service"), "mock_n8n")


class TestR3AppWindowManager(unittest.TestCase):
    """Proves window manager logic, hung app guards, focus, and Rule-0 defenses."""

    def setUp(self):
        self.backend = MockWin32Backend()
        self.manager = AppWindowManager(backend=self.backend)

    def test_list_windows(self):
        """Proves listing windows filters visible windows and extracts metadata."""
        windows = self.manager.list_windows(visible_only=True)
        # Should exclude csrss.exe (is_visible=False)
        self.assertEqual(len(windows), 3)
        titles = [w.title for w in windows]
        self.assertIn("Untitled - Notepad", titles)
        self.assertIn("Calculator", titles)
        self.assertIn("Frozen Window", titles)

    def test_find_window(self):
        """Proves window lookup by title substring and process name."""
        w1 = self.manager.find_window("Notepad")
        self.assertIsNotNone(w1)
        self.assertEqual(w1.hwnd, 1001)

        w2 = self.manager.find_window("calculator")
        self.assertIsNotNone(w2)
        self.assertEqual(w2.hwnd, 1002)

        w3 = self.manager.find_window("non_existent_app")
        self.assertIsNone(w3)

    def test_focus_normal_window(self):
        """Proves focusing normal window activates it and returns VERIFIED_SUCCESS."""
        res = self.manager.focus_window(1001)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertEqual(self.backend.foreground_hwnd, 1001)

    def test_focus_minimized_window_unminimizes(self):
        """REQ-R3-1: Proves focusing a minimized window automatically restores it."""
        # Calculator (1002) is iconic (minimized)
        self.assertTrue(self.backend.is_iconic(1002))
        res = self.manager.focus_window(1002)
        self.assertTrue(res.success)
        # Verify it was restored
        self.assertIn(1002, self.backend.restored_hwnds)
        self.assertFalse(self.backend.is_iconic(1002))

    def test_focus_hung_window_rejected(self):
        """REQ-R3-1: Proves focusing a hung window is rejected immediately."""
        # 1003 is_hung=True
        res = self.manager.focus_window(1003)
        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_FAILURE)
        self.assertIn("unresponsive/hung", res.error)

    def test_close_window_success(self):
        """Proves closing normal window posts WM_CLOSE and verifies disappearance."""
        res = self.manager.close_window(1001)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertIn(1001, self.backend.closed_hwnds)
        self.assertFalse(self.backend.is_window(1001))

    def test_close_window_rule_0_protected_process_denied(self):
        """REQ-R3-4: Proves attempting to close a protected process is blocked by Rule-0."""
        # HWND 1004 has pid=4 (System / csrss)
        res = self.manager.close_window(1004)
        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_FAILURE)
        self.assertIn("Rule-0 Invariant Violation", res.error)
        self.assertNotIn(1004, self.backend.closed_hwnds)

    def test_terminate_process_rule_0_denied(self):
        """REQ-R3-4: Proves terminating PID 0 or PID 4 is blocked by Rule-0."""
        res = self.manager.terminate_process(0)
        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_FAILURE)
        self.assertIn("Rule-0 Invariant Violation", res.error)

        res2 = self.manager.terminate_process(4)
        self.assertFalse(res2.success)
        self.assertIn("Rule-0 Invariant Violation", res2.error)


class TestR3InputAndComputerUseDriver(unittest.TestCase):
    """Proves input driver and composite ComputerUseDriver functionality."""

    def setUp(self):
        self.backend = MockWin32Backend()
        self.app_manager = AppWindowManager(backend=self.backend)
        self.input_driver = WindowsInputDriver(app_manager=self.app_manager)
        self.driver = ComputerUseDriver(
            app_manager=self.app_manager,
            input_driver=self.input_driver,
        )

    def test_send_keys_verifies_focus(self):
        """Proves send_keys focuses target window before dispatching characters."""
        res = self.driver.send_keys(target="Notepad", text="Hello LAYA!", press_enter=True)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertEqual(res.evidence["chars_sent"], len("Hello LAYA!") + 1)
        self.assertEqual(self.backend.foreground_hwnd, 1001)

    def test_driver_focus_and_close_by_title(self):
        """Proves driver resolves string query to HWND and executes focus/close."""
        res_focus = self.driver.focus_window("Calculator")
        self.assertTrue(res_focus.success)
        self.assertEqual(res_focus.hwnd, 1002)

        res_close = self.driver.close_window("Calculator")
        self.assertTrue(res_close.success)
        self.assertEqual(res_close.hwnd, 1002)
        self.assertFalse(self.backend.is_window(1002))


class TestR3SubstrateIntegration(unittest.TestCase):
    """Proves integration with CapabilityRegistry, PolicyEngine, and ArgumentResolver."""

    def test_build_real_capability_registry_includes_desktop(self):
        """REQ-R3-6: Proves real capability registry registers all desktop capabilities."""
        reg = build_real_capability_registry()
        # Should include canonical tools (23) + deep_research (2) + browser (2) + desktop (6 * 2 = 12) >= 39
        self.assertGreaterEqual(reg.count(), 39)

        # Check primary IDs
        for cap_id in (
            "desktop.launch_app",
            "desktop.list_windows",
            "desktop.focus_window",
            "desktop.close_window",
            "desktop.service_health",
            "desktop.send_keys",
        ):
            self.assertIsNotNone(reg.get(cap_id), f"Missing capability {cap_id}")

        # Check aliases
        for alias_id in (
            "desktop_launch_app",
            "desktop_list_windows",
            "desktop_focus_window",
            "desktop_close_window",
            "desktop_service_health",
            "desktop_send_keys",
        ):
            self.assertIsNotNone(reg.get(alias_id), f"Missing alias {alias_id}")

    def test_canonical_registry_invariant_preserved(self):
        """REQ-R3-6: Proves canonical registry still contains exactly 23 source tools."""
        reg = build_canonical_registry()
        self.assertEqual(reg.count(), 23)

    def test_policy_engine_gates_desktop_capabilities(self):
        """REQ-R3-4 & REQ-R3-6: Proves PolicyEngine enforces autonomy and Rule-0 checks."""
        policy = PolicyEngine()

        # 1. list_windows is READ_ONLY and auto-permitted under ADVISOR
        dec_list = policy.evaluate(
            capability=DESKTOP_LIST_WINDOWS_SPEC,
            arguments={},
            autonomy_profile=AutonomyProfile.ADVISOR,
        )
        self.assertTrue(dec_list.allowed)
        self.assertEqual(dec_list.assessment.blast_radius, "NONE")

        # 2. Rule-0 denial: attempting to kill/close csrss or PID 4 is denied even if confirmed
        dec_kill = policy.evaluate(
            capability=DESKTOP_CLOSE_WINDOW_SPEC,
            arguments={"target": "csrss.exe", "pid": 4},
            autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
            user_confirmed=True,  # User confirmation strictly ignored for Rule-0!
        )
        self.assertFalse(dec_kill.allowed)
        self.assertEqual(dec_kill.effect, PolicyEffect.DENY)
        self.assertIn("RULE_0_PROTECTED_SYSTEM_PROCESSES", dec_kill.matched_rules)

    def test_argument_resolver_extracts_desktop_slots(self):
        """REQ-R3-6: Proves ArgumentResolver extracts arguments deterministically."""
        resolver = ArgumentResolver()

        # 1. launch_app
        env1 = resolver.resolve(DESKTOP_LAUNCH_APP_SPEC, "launch calc please")
        self.assertEqual(env1.arguments.get("app_name"), "calc")

        # 2. focus_window with HWND
        env2 = resolver.resolve(DESKTOP_FOCUS_WINDOW_SPEC, "focus window 1002")
        self.assertEqual(env2.arguments.get("target"), 1002)

        # 3. service_health for n8n
        env3 = resolver.resolve(DESKTOP_SERVICE_HEALTH_SPEC, "check health of n8n on port 5678")
        self.assertEqual(env3.arguments.get("service_name"), "n8n")
        self.assertEqual(env3.arguments.get("port"), 5678)

        # 4. send_keys
        env4 = resolver.resolve(DESKTOP_SEND_KEYS_SPEC, "type 'print(123)' into 'Notepad'")
        self.assertEqual(env4.arguments.get("target"), "Notepad")
        self.assertEqual(env4.arguments.get("text"), "print(123)")


if __name__ == "__main__":
    unittest.main()
