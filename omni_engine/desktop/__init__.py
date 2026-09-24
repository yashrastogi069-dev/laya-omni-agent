"""
omni_engine.desktop
===================
Real Windows Desktop, Application Lifecycle & Local Service Engine (Phase R3).
"""

from .app_manager import (
    AppWindowManager,
    KNOWN_APP_COMMANDS,
    NativeWin32Backend,
    Win32Backend,
)
from .engine import ComputerUseDriver
from .service import KNOWN_SERVICES, LocalServiceProber
from .uia_driver import WindowsInputDriver

__all__ = [
    "Win32Backend",
    "NativeWin32Backend",
    "AppWindowManager",
    "LocalServiceProber",
    "WindowsInputDriver",
    "ComputerUseDriver",
    "KNOWN_SERVICES",
    "KNOWN_APP_COMMANDS",
]
