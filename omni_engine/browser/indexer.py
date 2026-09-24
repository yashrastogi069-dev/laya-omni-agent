"""
omni_engine.browser.indexer
===========================
Dynamic Indexed Action Space and Element Stamping Engine.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Eliminates selector hallucinations via
  compact, numbered indices (@1..@N).
- Dual-Key Addressing & Staleness Prevention (REQ-B2):
  1. Stamps `data-laya-idx="N"` directly on interactive DOM nodes.
  2. Captures semantic fingerprint (tag, role, accessible text, bounding box).
  3. Pre-execution fingerprint check detects SPA DOM shifts and halts with `ErrorCode.CONFLICT`.
  4. Intrinsic Financial Keyword Detection (REQ-B4) tags elements triggering checkout/payment.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.browser import BrowserElement, BrowserSnapshot

FINANCIAL_KEYWORDS_REGEX = re.compile(
    r"\b(checkout|pay(\s+now)?|place\s+order|buy(\s+now)?|complete\s+(order|purchase)|submit\s+payment|confirm\s+purchase|subscribe|card(\s+number)?|cvv|cvc|credit\s+card|billing)\b",
    re.IGNORECASE,
)

FINANCIAL_URL_REGEX = re.compile(
    r"(?i)/(checkout|pay|billing|order|purchase|subscribe)|paypal\.com|stripe\.com"
)


# In-page JavaScript scanning visible interactive elements, stamping data-laya-idx,
# and returning structured metadata.
_DOM_INDEXING_SCRIPT = """
(maxElements) => {
    // Clean prior stamps
    document.querySelectorAll('[data-laya-idx]').forEach(el => el.removeAttribute('data-laya-idx'));

    const interactiveSelectors = [
        'button',
        'a[href]',
        'input:not([type="hidden"])',
        'select',
        'textarea',
        '[role="button"]',
        '[role="link"]',
        '[role="checkbox"]',
        '[role="radio"]',
        '[role="menuitem"]',
        '[role="tab"]',
        '[role="combobox"]',
        '[tabindex]:not([tabindex="-1"])',
    ];

    const elements = [];
    let count = 0;
    const candidates = document.querySelectorAll(interactiveSelectors.join(', '));

    for (let el of candidates) {
        if (count >= maxElements) break;

        // Verify visibility
        const rect = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;
        if (rect.width <= 2 || rect.height <= 2) continue;

        // Viewport presence check (or within reasonable scroll distance)
        const isVisible = (
            rect.bottom >= 0 &&
            rect.right >= 0 &&
            rect.top <= (window.innerHeight || document.documentElement.clientHeight) * 2 &&
            rect.left <= (window.innerWidth || document.documentElement.clientWidth) * 2
        );
        if (!isVisible) continue;

        count++;
        const idx = count;
        el.setAttribute('data-laya-idx', String(idx));

        const tag = el.tagName.toLowerCase();
        const role = el.getAttribute('role') || el.type || tag;
        let text = (el.innerText || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.value || '').trim();
        text = text.replace(/\\s+/g, ' ').substring(0, 64);

        const href = el.getAttribute('href') || null;
        const inputType = el.getAttribute('type') || (tag === 'input' ? 'text' : null);
        const value = el.value || null;

        elements.push({
            index: '@' + idx,
            tag_name: tag,
            role: role,
            text: text,
            selector: `[data-laya-idx="${idx}"]`,
            href: href,
            input_type: inputType,
            value: value,
            is_interactive: true,
            is_visible: true,
            bounding_box: {
                x: Math.round(rect.x),
                y: Math.round(rect.y),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
            }
        });
    }

    return {
        url: window.location.href,
        title: document.title,
        elements: elements,
    };
}
"""


class DOMActionIndexer:
    """Extracts, stamps, and validates interactive action space elements from a Page."""

    def __init__(self, max_elements: int = 100) -> None:
        self.max_elements = max_elements

    def snapshot(self, page: Any) -> BrowserSnapshot:
        """Executes in-page indexing, stamps data-laya-idx, and returns a BrowserSnapshot."""
        snapshot_id = str(uuid.uuid4())[:8]

        # Execute evaluation
        data = page.evaluate(_DOM_INDEXING_SCRIPT, self.max_elements)
        raw_elements = data.get("elements", [])
        url = data.get("url", page.url if hasattr(page, "url") else "")
        title = data.get("title", "")

        is_page_financial = bool(FINANCIAL_URL_REGEX.search(url))
        parsed_elements: List[BrowserElement] = []

        for item in raw_elements:
            text = item.get("text", "")
            role = item.get("role", "")
            href = item.get("href") or ""
            target_str = f"{text} {role} {href}"

            is_financial = is_page_financial or bool(FINANCIAL_KEYWORDS_REGEX.search(target_str))

            elem = BrowserElement(
                index=item["index"],
                tag_name=item["tag_name"],
                role=role,
                text=text,
                selector=item["selector"],
                href=item.get("href"),
                input_type=item.get("input_type"),
                value=item.get("value"),
                is_interactive=True,
                is_visible=item.get("is_visible", True),
                is_financial=is_financial,
                bounding_box=item.get("bounding_box"),
                snapshot_id=snapshot_id,
            )
            parsed_elements.append(elem)

        has_financial = any(e.is_financial for e in parsed_elements) or is_page_financial

        return BrowserSnapshot(
            snapshot_id=snapshot_id,
            url=url,
            title=title,
            elements=parsed_elements,
            interactive_count=len(parsed_elements),
            has_financial_elements=has_financial,
        )

    def verify_staleness(self, page: Any, expected_element: BrowserElement) -> Tuple[bool, Optional[str]]:
        """REQ-B2: Pre-execution fingerprint verification against active DOM node.

        Returns (is_valid, error_reason).
        """
        selector = expected_element.selector
        try:
            # Query stamped element in page
            locator = page.locator(selector)
            if locator.count() == 0:
                return False, f"Element {expected_element.index} not found in DOM (detached or refreshed)."

            actual_tag = locator.evaluate("el => el.tagName.toLowerCase()")
            if actual_tag != expected_element.tag_name:
                return False, f"Element {expected_element.index} tag changed from {expected_element.tag_name} to {actual_tag}."

            actual_text = locator.evaluate("el => (el.innerText || el.getAttribute('aria-label') || el.value || '').trim()")
            actual_text = re.sub(r"\s+", " ", actual_text)[:64]

            # Allow fuzzy prefix match on text to tolerate minor badge or count shifts
            if expected_element.text and actual_text:
                if not (expected_element.text in actual_text or actual_text in expected_element.text):
                    return False, f"Element {expected_element.index} text changed from '{expected_element.text}' to '{actual_text}'."

            return True, None
        except Exception as e:
            return False, f"Staleness verification failed on {expected_element.index}: {str(e)}"
