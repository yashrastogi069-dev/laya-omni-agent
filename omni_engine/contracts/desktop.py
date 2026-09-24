"""
omni_engine.contracts.desktop
=============================
Strongly typed contracts for Windows Desktop, Application Lifecycle,
and Local Service Probing (Phase R3).

Adheres to:
- Invariant 1: Deterministic Control — strongly typed fields, extra='forbid'.
- Invariant 6: Evidence-Based Completion — tracks physical receipts (PIDs, HWNDs, bounds, port states).
"""

from typing import Any, Dict, Optional
from pydantic import Field

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import VerificationStatus


class WindowBounds(BaseContractModel):
    """Screen coordinate bounding rectangle for a desktop window."""
    left: int = Field(..., description="X coordinate of left edge")
    top: int = Field(..., description="Y coordinate of top edge")
    right: int = Field(..., description="X coordinate of right edge")
    bottom: int = Field(..., description="Y coordinate of bottom edge")
    width: int = Field(..., description="Width in pixels")
    height: int = Field(..., description="Height in pixels")


class WindowState(BaseContractModel):
    """Dynamic operational state of a desktop window."""
    is_foreground: bool = Field(default=False, description="Whether window currently has OS foreground focus")
    is_minimized: bool = Field(default=False, description="Whether window is minimized (IsIconic)")
    is_maximized: bool = Field(default=False, description="Whether window is maximized (IsZoomed)")
    is_visible: bool = Field(default=True, description="Whether window is marked visible (IsWindowVisible)")
    is_hung: bool = Field(default=False, description="Whether window is unresponsive (IsHungAppWindow)")
    bounds: Optional[WindowBounds] = Field(default=None, description="Window bounds if available")


class AppWindowInfo(BaseContractModel):
    """Snapshot information for an open desktop window."""
    hwnd: int = Field(..., description="Win32 Window Handle integer")
    title: str = Field(..., description="Extracted window caption / title text")
    process_name: str = Field(..., description="Name of process owning the window")
    pid: int = Field(..., description="Process ID owning the window")
    is_active: bool = Field(default=False, description="Whether this window currently has foreground focus")
    is_minimized: bool = Field(default=False, description="Whether window is minimized")
    is_maximized: bool = Field(default=False, description="Whether window is maximized")
    is_visible: bool = Field(default=True, description="Whether window is visible")
    bounds: WindowBounds = Field(..., description="Physical pixel coordinates")


class AppLaunchResult(BaseContractModel):
    """Evidence receipt emitted upon application launch."""
    app_name: str = Field(..., description="Requested application name")
    launcher_pid: Optional[int] = Field(default=None, description="Process ID directly spawned by launcher")
    active_pid: Optional[int] = Field(default=None, description="Active PID owning the verified main window")
    process_name: Optional[str] = Field(default=None, description="Verified process name")
    hwnd: Optional[int] = Field(default=None, description="Window handle of launched main window")
    window_title: Optional[str] = Field(default=None, description="Caption of launched window")
    bounds: Optional[WindowBounds] = Field(default=None, description="Initial window bounds")
    exit_code: Optional[int] = Field(default=None, description="Exit code if launcher process terminated")
    success: bool = Field(..., description="Whether launch and verification succeeded")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    startup_time_ms: float = Field(default=0.0, description="Time spent launching and discovering window")
    error: Optional[str] = Field(default=None, description="Error diagnostic if launch or verification failed")


class ServiceHealthStatus(BaseContractModel):
    """Evidence receipt for local microservice and port probing."""
    service_name: str = Field(..., description="Canonical or requested service identifier")
    host: str = Field(default="127.0.0.1", description="Target network host")
    port: int = Field(..., description="Target TCP port number")
    is_listening: bool = Field(..., description="Whether port accepted TCP connection")
    http_status: Optional[int] = Field(default=None, description="HTTP response code if HTTP probe succeeded")
    response_time_ms: float = Field(default=0.0, description="Latency of port connect or HTTP probe in milliseconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Parsed diagnostic payload or metadata")
    error: Optional[str] = Field(default=None, description="Error details if probe failed")


class DesktopActionResult(BaseContractModel):
    """Evidence-grounded receipt for desktop window, process, or input manipulation."""
    action: str = Field(..., description="Executed action type (focus, close, minimize, maximize, send_keys)")
    target: str = Field(..., description="Target identifier (HWND, window title, or process name)")
    hwnd: Optional[int] = Field(default=None, description="Target window handle if applicable")
    prior_state: Optional[Dict[str, Any]] = Field(default=None, description="Window or process state before action")
    posterior_state: Optional[Dict[str, Any]] = Field(default=None, description="Window or process state after action")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Physical state verification receipts")
    success: bool = Field(..., description="Whether action achieved verified expected state")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    error: Optional[str] = Field(default=None, description="Failure reason if action or verification failed")
