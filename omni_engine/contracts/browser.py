"""
omni_engine.contracts.browser
=============================
Typed contracts and schemas for Phase R2 & L18: Modular Persistent Browser Engine.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Actions, tabs, and dynamic indexed elements are strictly typed.
- Evidence-Based Outcome (Invariant 6): Every action emits physical state receipts (DOM mutation, URL change, file size).
- Financial Safety Gating (REQ-B4 / REV-L18-02): Explicitly distinguishes and flags financial/purchase interactions.
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
    EXTRACT = "extract"
    MANAGE_TABS = "manage_tabs"
    TABS = "tabs"


class TabAction(str, Enum):
    """Supported multi-tab management operations."""
    LIST = "list"
    NEW = "new"
    SWITCH = "switch"
    CLOSE = "close"


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
    """Specification of an interactive browser action to execute (legacy facade)."""
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
    selector: Optional[str] = Field(default=None, description="Selector for EXTRACT")
    attribute: Optional[str] = Field(default=None, description="Attribute for EXTRACT")
    multiple: bool = Field(default=True, description="Whether to extract multiple items")
    max_items: int = Field(default=50, ge=1, le=500, description="Maximum items for EXTRACT")
    tab_action: Optional[TabAction] = Field(default=None, description="Tab operation for TABS")
    tab_id: Optional[int] = Field(default=None, description="Tab index for TABS")


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
        description="Physical evidence details (e.g. input_value, mutation_count, scroll_y, tab_count)",
    )
    data: Optional[Dict[str, Any]] = Field(default=None, description="Snapshot or extracted data")
    error: Optional[str] = Field(default=None, description="Error message if failed")


# ---------------------------------------------------------------------------
# L18 Modular Capability Specific Contracts (extra="forbid")
# ---------------------------------------------------------------------------

class TabInfo(BaseContractModel):
    """Metadata describing a single browser page/tab."""
    tab_id: int = Field(..., ge=0, description="0-indexed tab identifier")
    title: str = Field(default="", description="Page title")
    url: str = Field(default="", description="Current URL of tab")
    is_active: bool = Field(default=False, description="Whether this tab is currently the active foreground page")


class BrowserTabsRequest(BaseContractModel):
    """Specification for browser tab lifecycle management."""
    action: TabAction = Field(default=TabAction.LIST, description="Tab operation: list, new, switch, close")
    tab_id: Optional[int] = Field(default=None, ge=0, description="Target tab index for switch or close")
    url: Optional[str] = Field(default=None, description="Initial destination URL when opening a new tab")


class BrowserTabsResult(BaseContractModel):
    """Evidence receipt resulting from tab management."""
    success: bool = Field(..., description="Whether tab operation succeeded")
    action: TabAction = Field(..., description="Executed tab action")
    tabs: List[TabInfo] = Field(default_factory=list, description="List of currently open tabs")
    active_tab_id: int = Field(default=0, ge=0, description="Currently active tab index")
    tab_count: int = Field(default=1, ge=0, description="Total active tab count")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserExtractRequest(BaseContractModel):
    """Specification for in-page DOM text or attribute extraction."""
    selector: Optional[str] = Field(default=None, description="Target selector (CSS or @N index). Defaults to body.")
    attribute: Optional[str] = Field(default=None, description="Attribute name to extract (e.g. href, src, value). None extracts innerText.")
    multiple: bool = Field(default=True, description="Whether to extract from all matching elements or single element.")
    max_items: int = Field(default=50, ge=1, le=500, description="Maximum number of items to return.")


class BrowserExtractResult(BaseContractModel):
    """Structured extraction receipt."""
    success: bool = Field(..., description="Whether extraction succeeded")
    url: str = Field(default="", description="Page URL where extraction was performed")
    selector: str = Field(default="body", description="Resolved selector used")
    attribute: Optional[str] = Field(default=None, description="Attribute extracted, or None for text")
    items: List[str] = Field(default_factory=list, description="Extracted string values")
    count: int = Field(default=0, ge=0, description="Number of items extracted")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


class BrowserNavigateRequest(BaseContractModel):
    """Specification for browser navigation."""
    url: str = Field(..., min_length=1, description="Target web page URL to navigate to")
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0, description="Timeout budget for navigation")


class BrowserNavigateResult(BaseContractModel):
    """Receipt for browser navigation."""
    success: bool = Field(..., description="Whether navigation succeeded")
    previous_url: str = Field(default="", description="URL before navigation")
    current_url: str = Field(default="", description="URL after navigation")
    title: str = Field(default="", description="Page title after navigation")
    url_changed: bool = Field(default=False, description="Whether navigation changed URL")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserClickRequest(BaseContractModel):
    """Specification for clicking an interactive element."""
    target: str = Field(..., min_length=1, description="Target element index (@1..@N) or CSS selector")
    user_confirmed: bool = Field(default=False, description="Explicit human confirmation for checkout/financial elements")
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0, description="Timeout budget for click")


class BrowserClickResult(BaseContractModel):
    """Receipt for browser click."""
    success: bool = Field(..., description="Whether click succeeded")
    target: str = Field(..., description="Target element selector or index clicked")
    current_url: str = Field(default="", description="URL after click")
    url_changed: bool = Field(default=False, description="Whether click triggered navigation")
    dom_mutated: bool = Field(default=False, description="Whether click caused DOM mutation")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserTypeRequest(BaseContractModel):
    """Specification for typing into an input field."""
    target: str = Field(..., min_length=1, description="Target element index (@1..@N) or CSS selector")
    text: str = Field(..., description="Text value to fill into targeted input element")
    press_enter: bool = Field(default=False, description="Whether to press Enter key after typing")
    clear_first: bool = Field(default=True, description="Whether to clear existing value before typing")
    user_confirmed: bool = Field(default=False, description="Explicit human confirmation for financial forms")


class BrowserTypeResult(BaseContractModel):
    """Receipt for browser text entry."""
    success: bool = Field(..., description="Whether typing succeeded")
    target: str = Field(..., description="Target element selector or index")
    typed_text: str = Field(default="", description="Text submitted")
    input_value_verified: bool = Field(default=False, description="Whether physical input value matches")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    error: Optional[str] = Field(default=None, description="Error message if failed")


class BrowserScreenshotModularRequest(BaseContractModel):
    """Specification for capturing a browser screenshot."""
    output_path: Optional[str] = Field(default=None, description="Destination path for captured screenshot")
    full_page: bool = Field(default=False, description="Whether to capture full scrollable page")


class BrowserScreenshotModularResult(BaseContractModel):
    """Receipt for browser screenshot."""
    success: bool = Field(..., description="Whether screenshot capture succeeded")
    file_path: str = Field(default="", description="Path on disk where screenshot was saved")
    file_size_bytes: int = Field(default=0, ge=0, description="Physical file size in bytes")
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    error: Optional[str] = Field(default=None, description="Error message if failed")
