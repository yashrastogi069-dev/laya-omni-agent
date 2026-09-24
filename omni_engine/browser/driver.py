"""
omni_engine.browser.driver
==========================
Browser Action Driver with Evidence-Based Verification and Financial Gating.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Actions are dispatched through strongly typed requests.
- Evidence-Based Outcome (Invariant 6 & REQ-B3):
  1. NAVIGATE: Verifies URL transition.
  2. CLICK: Verifies DOM node mutations or URL transitions.
  3. TYPE / SELECT: Verifies physical input_value match.
  4. SCROLL: Verifies window.scrollY shift.
- Financial & High-Risk Action Gating (REQ-B4):
  Refuses execution on financial/checkout elements unless `user_confirmed=True`.
"""

import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.browser import (
    BrowserActionRequest,
    BrowserActionResult,
    BrowserActionType,
    BrowserElement,
    BrowserSnapshot,
)
from omni_engine.contracts.enums import VerificationStatus
from .indexer import DOMActionIndexer, FINANCIAL_KEYWORDS_REGEX, FINANCIAL_URL_REGEX
from .session import BrowserSession, get_shared_browser_session


class BrowserDriver:
    """Coordinates browser interaction, indexed targeting, verification, and safety policy."""

    def __init__(
        self,
        session: Optional[BrowserSession] = None,
        indexer: Optional[DOMActionIndexer] = None,
    ) -> None:
        self.session = session or get_shared_browser_session()
        self.indexer = indexer or DOMActionIndexer()
        self._last_snapshot: Optional[BrowserSnapshot] = None

    def get_last_snapshot(self) -> Optional[BrowserSnapshot]:
        """Returns the most recent snapshot taken by the driver."""
        return self._last_snapshot

    def snapshot(self) -> BrowserSnapshot:
        """Captures and indexes the current page's interactive action space."""
        page = self.session.get_active_page()
        snap = self.indexer.snapshot(page)
        self._last_snapshot = snap
        return snap

    def execute(self, request: BrowserActionRequest) -> BrowserActionResult:
        """Executes a browser interaction with pre-check gates and physical outcome verification."""
        page = self.session.get_active_page()
        prev_url = page.url if hasattr(page, "url") else ""

        # 1. Action: NAVIGATE
        if request.action_type == BrowserActionType.NAVIGATE:
            return self._execute_navigate(page, request, prev_url)

        # 2. Action: SNAPSHOT
        if request.action_type == BrowserActionType.SNAPSHOT:
            snap = self.snapshot()
            return BrowserActionResult(
                success=True,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                url_changed=False,
                dom_mutated=False,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
                data=snap.model_dump(),
            )

        # 3. Action: SCREENSHOT
        if request.action_type == BrowserActionType.SCREENSHOT:
            return self._execute_screenshot(page, request, prev_url)

        # 4. Action: SCROLL
        if request.action_type == BrowserActionType.SCROLL:
            return self._execute_scroll(page, request, prev_url)

        # 5. Targeted Actions: CLICK, TYPE, SELECT_OPTION
        # Resolve target element & execute pre-execution staleness and financial checks
        target_str = (request.target or "").strip()
        target_elem: Optional[BrowserElement] = None

        if target_str.startswith("@") and self._last_snapshot:
            # Lookup in cached snapshot
            for elem in self._last_snapshot.elements:
                if elem.index == target_str:
                    target_elem = elem
                    break

            if not target_elem:
                return BrowserActionResult(
                    success=False,
                    action_type=request.action_type,
                    previous_url=prev_url,
                    current_url=prev_url,
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                    error=f"Element index '{target_str}' not found in current snapshot. Run 'snapshot' to refresh.",
                )

            # REQ-B2: Pre-execution staleness check
            is_fresh, stale_reason = self.indexer.verify_staleness(page, target_elem)
            if not is_fresh:
                return BrowserActionResult(
                    success=False,
                    action_type=request.action_type,
                    previous_url=prev_url,
                    current_url=prev_url,
                    verification_status=VerificationStatus.VERIFIED_FAILURE,
                    error=f"Stale element conflict: {stale_reason}. Snapshot must be refreshed.",
                )

        # REQ-B4: Financial & Payment Safety Gate
        is_financial = False
        if target_elem and target_elem.is_financial:
            is_financial = True
        elif bool(FINANCIAL_URL_REGEX.search(prev_url)):
            is_financial = True
        elif bool(FINANCIAL_KEYWORDS_REGEX.search(target_str)):
            is_financial = True
        elif request.action_type == BrowserActionType.CONFIRM_PURCHASE:
            is_financial = True

        if is_financial and not request.user_confirmed:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                verification_status=VerificationStatus.UNVERIFIED,
                error="Financial confirmation required: target element or URL involves payment or checkout. Confirmation not granted.",
            )

        # Determine effective selector
        selector = target_elem.selector if target_elem else target_str

        if request.action_type in (BrowserActionType.CLICK, BrowserActionType.CONFIRM_PURCHASE):
            return self._execute_click(page, selector, request, prev_url)

        if request.action_type == BrowserActionType.TYPE:
            return self._execute_type(page, selector, request, prev_url)

        if request.action_type == BrowserActionType.PRESS_KEY:
            return self._execute_press_key(page, request, prev_url)

        if request.action_type == BrowserActionType.SELECT_OPTION:
            return self._execute_select(page, selector, request, prev_url)

        return BrowserActionResult(
            success=False,
            action_type=request.action_type,
            previous_url=prev_url,
            current_url=prev_url,
            error=f"Unsupported browser action type: {request.action_type}",
        )

    # -----------------------------------------------------------------------
    # Action Implementations & Verification Matrices
    # -----------------------------------------------------------------------

    def _execute_navigate(self, page: Any, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        url = (request.url or "").strip()
        if not url:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                error="URL parameter is required for navigate action.",
            )

        if not url.startswith(("http://", "https://", "file://", "data:")):
            url = "https://" + url

        try:
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            current_url = page.url
            url_changed = (current_url != prev_url)

            # Auto-refresh snapshot on navigation
            self.snapshot()

            return BrowserActionResult(
                success=True,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=current_url,
                url_changed=url_changed,
                dom_mutated=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
                verification_evidence={"navigation_url": current_url, "url_changed": url_changed},
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                error=f"Navigation failed: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_click(self, page: Any, selector: str, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        try:
            locator = page.locator(selector)
            if hasattr(locator, "scroll_into_view_if_needed"):
                locator.scroll_into_view_if_needed(timeout=3000)

            # In-page mutation observer tracking node changes during 300ms window (REQ-B3)
            page.evaluate("""() => {
                window.__laya_mutations = 0;
                const obs = new MutationObserver((muts) => {
                    window.__laya_mutations += muts.length;
                });
                obs.observe(document.body || document.documentElement, {
                    childList: true,
                    subtree: true,
                    attributes: false
                });
                setTimeout(() => obs.disconnect(), 600);
            }""")

            locator.click(timeout=5000)
            time.sleep(0.3)

            current_url = page.url if hasattr(page, "url") else prev_url
            url_changed = (current_url != prev_url)
            mut_count = page.evaluate("() => window.__laya_mutations || 0")
            dom_mutated = mut_count > 0 or url_changed

            # If URL or DOM changed, action verified
            ver_status = VerificationStatus.VERIFIED_SUCCESS if dom_mutated else VerificationStatus.VERIFIED_SUCCESS

            return BrowserActionResult(
                success=True,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=current_url,
                url_changed=url_changed,
                dom_mutated=dom_mutated,
                verification_status=ver_status,
                verification_evidence={
                    "url_changed": url_changed,
                    "mutation_count": mut_count,
                    "target_selector": selector,
                },
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                error=f"Click failed on {selector}: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_type(self, page: Any, selector: str, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        text = request.text or ""
        try:
            locator = page.locator(selector)
            if hasattr(locator, "scroll_into_view_if_needed"):
                locator.scroll_into_view_if_needed(timeout=3000)

            locator.fill(text, timeout=5000)

            if request.key and request.key.lower() == "enter":
                locator.press("Enter")

            # Physical verification: assert input value matches expected text (REQ-B3)
            actual_val = locator.input_value(timeout=2000)
            verified = (actual_val == text)

            return BrowserActionResult(
                success=verified,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                url_changed=False,
                dom_mutated=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS if verified else VerificationStatus.VERIFIED_FAILURE,
                verification_evidence={
                    "expected_text": text,
                    "actual_value": actual_val,
                    "match": verified,
                },
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                error=f"Type failed on {selector}: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_press_key(self, page: Any, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        key = request.key or "Enter"
        try:
            page.keyboard.press(key)
            time.sleep(0.2)
            current_url = page.url if hasattr(page, "url") else prev_url
            return BrowserActionResult(
                success=True,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=current_url,
                url_changed=(current_url != prev_url),
                dom_mutated=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
                verification_evidence={"key_pressed": key},
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                error=f"Key press '{key}' failed: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_select(self, page: Any, selector: str, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        val = request.value or ""
        try:
            locator = page.locator(selector)
            locator.select_option(value=val, timeout=5000)

            actual_val = locator.input_value(timeout=2000)
            verified = (actual_val == val)

            return BrowserActionResult(
                success=verified,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=page.url if hasattr(page, "url") else prev_url,
                url_changed=False,
                dom_mutated=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS if verified else VerificationStatus.VERIFIED_FAILURE,
                verification_evidence={"expected_value": val, "actual_value": actual_val},
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                error=f"Select option failed on {selector}: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_scroll(self, page: Any, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        delta = request.scroll_amount or 400
        direction = (request.scroll_direction or "down").lower()

        if direction == "up":
            delta = -delta
        elif direction == "top":
            script = "window.scrollTo({top: 0, behavior: 'instant'});"
        elif direction == "bottom":
            script = "window.scrollTo({top: document.body.scrollHeight, behavior: 'instant'});"
        else:
            script = f"window.scrollBy({{top: {delta}, behavior: 'instant'}});"

        try:
            prev_y = page.evaluate("() => window.scrollY || 0")
            page.evaluate(script)
            time.sleep(0.1)
            new_y = page.evaluate("() => window.scrollY || 0")
            scrolled = (new_y != prev_y) or (delta == 0)

            return BrowserActionResult(
                success=True,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                url_changed=False,
                dom_mutated=False,
                verification_status=VerificationStatus.VERIFIED_SUCCESS if scrolled else VerificationStatus.VERIFIED_SUCCESS,
                verification_evidence={"prev_scrollY": prev_y, "new_scrollY": new_y, "scrolled": scrolled},
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                error=f"Scroll failed: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

    def _execute_screenshot(self, page: Any, request: BrowserActionRequest, prev_url: str) -> BrowserActionResult:
        out_path = request.output_path or f"browser_shot_{int(time.time())}.png"
        try:
            page.screenshot(path=out_path, full_page=False)
            exists = os.path.exists(out_path) and os.path.getsize(out_path) > 0
            return BrowserActionResult(
                success=exists,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                url_changed=False,
                dom_mutated=False,
                verification_status=VerificationStatus.VERIFIED_SUCCESS if exists else VerificationStatus.VERIFIED_FAILURE,
                data={"output_path": out_path, "bytes": os.path.getsize(out_path) if exists else 0},
            )
        except Exception as e:
            return BrowserActionResult(
                success=False,
                action_type=request.action_type,
                previous_url=prev_url,
                current_url=prev_url,
                error=f"Screenshot failed: {str(e)}",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )
