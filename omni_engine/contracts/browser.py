"""
omni_engine.contracts.browser
=============================
Typed contracts and schemas for Phase R2: Real Persistent Browser Engine.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Actions and dynamic indexed elements are strictly typed.
- Evidence-Based Outcome (Invariant 6): Every action emits physical state receipts (DOM mutation, URL change).
- Financial Safety Gating (REQ-B4): Explicitly distinguishes and flags financial/purchase interactions.
"""

from enum import Enum
import time
import uuid
from typing import Any, Dict, List, Optional
from pydantic import Field
from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import VerificationStatus


class BrowserActionType(str, Enum):
    """Supported interactive browser primitive actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    PRESS_KEY = "press_key"
    SELECT_OPTION = "select_option"
    SCROLL = "scroll"
    SNAPSHOT = "snapshot"
    SCREENSHOT = "screenshot"
    CONFIRM_PURCHASE = "confirm_purchase"


class BrowserElement(BaseContractModel):
    """An interactive element identified within the indexed action space (@1..@N)."""
    index: str = Field(..., description="Element index identifier, e.g. '@1', '@2'")
    tag_name: str = Field(..., description="HTML tag name in lowercase, e.g. 'button', 'input'")
    role: str = Field(default="generic", description="ARIA role or semantic role")
    text: str = Field(default="", description="Accessible name or visible text (truncated to 64 chars)")
    selector: str = Field(default="", description="Deterministic locator selector")
    href: Optional[str] = Field(default=None, description="Destination URL if link")
    input_type: Optional[str] = Field(default=None, description="Type attribute for inputs (text, password, etc.)")
    value: Optional[str] = Field(default=None, description="Current value of form control")
    is_interactive: bool = Field(default=True, description="Whether element is interactive")
    is_visible: bool = Field(default=True, description="Whether element is visible in viewport")
    is_financial: bool = Field(default=False, description="Whether element triggers checkout, payment, or purchase")
    bounding_box: Optional[Dict[str, float]] = Field(default=None, description="Coordinates {x, y, width, height}")
    snapshot_id: str = Field(default="", description="Snapshot UUID to verify against staleness")


class BrowserSnapshot(BaseContractModel):
    """Structured representation of the page's current interactive action space."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = Field(..., description="Current page URL")
    title: str = Field(default="", description="Current page title")
    elements: List[BrowserElement] = Field(default_factory=list, description="Indexed interactive elements")
    interactive_count: int = Field(default=0, description="Total interactive elements extracted")
    has_financial_elements: bool = Field(default=False, description="Whether checkout/payment elements are present")
    timestamp: float = Field(default_factory=time.time)


class BrowserActionRequest(BaseContractModel):
    """Specification of an interactive browser action to execute."""
    action_type: BrowserActionType = Field(..., description="Primitive action type")
    url: Optional[str] = Field(default=None, description="Target URL for NAVIGATE")
    target: Optional[str] = Field(default=None, description="Target element index (@N) or selector for CLICK/TYPE")
    text: Optional[str] = Field(default=None, description="Text to type into input")
    key: Optional[str] = Field(default=None, description="Keyboard key to press (Enter, Tab, Escape)")
    value: Optional[str] = Field(default=None, description="Dropdown option value to select")
    scroll_direction: Optional[str] = Field(default="down", description="'up', 'down', 'top', 'bottom'")
    scroll_amount: Optional[int] = Field(default=400, ge=10, le=5000, description="Pixel delta for scrolling")
    user_confirmed: bool = Field(default=False, description="Explicit human confirmation for financial/destructive gates")
    output_path: Optional[str] = Field(default=None, description="Destination path for SCREENSHOT")


class BrowserActionResult(BaseContractModel):
    """Evidence-based outcome receipt from executing a browser interaction."""
    success: bool = Field(..., description="Whether action succeeded physically")
    action_type: BrowserActionType = Field(..., description="Executed action type")
    previous_url: str = Field(default="", description="Page URL before action")
    current_url: str = Field(default="", description="Page URL after action")
    url_changed: bool = Field(default=False, description="Whether action triggered navigation")
    dom_mutated: bool = Field(default=False, description="Whether action caused DOM element changes")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Physical verification status",
    )
    verification_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Physical evidence details (e.g. input_value, mutation_count, scroll_y)",
    )
    data: Optional[Dict[str, Any]] = Field(default=None, description="Snapshot or extracted data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
