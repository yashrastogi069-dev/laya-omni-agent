"""
tests.test_l18_modular_browser
==============================
Comprehensive offline unit and integration test suite for Checkpoint L18:
Modular Browser Capability Rebuild (ADR-024).

Enforces:
1. Strongly Typed Modular Contracts (Pydantic v2 extra="forbid").
2. Multi-Tab Session Management (bounded max_tabs=5, last tab protection, dead page auto-pruning).
3. Script Injection Defense in Extract (REV-L18-01 - CDP dict parameter binding).
4. Financial Safety Gating (REV-L18-02 - PolicyEngine and intrinsic driver gates for click, type, navigate).
5. Indexed Selector Translation (REV-L18-06 - @N to [data-laya-idx="N"]).
6. Registry Invariants & Aliases (REV-L18-08 - 23 tools in canonical, browser_screenshot_v2 alias).
7. Adapter Outcome Normalization (REV-L18-09 - truthful ToolOutcome mapping in CapabilityRegistry.invoke).
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    ToolOutcome,
    VerificationStatus,
)
from omni_engine.contracts.policy import PolicyEffect
from omni_engine.contracts.capability import CapabilityInvocation, CapabilitySpec, ToolError
from omni_engine.contracts.browser import (
    BrowserActionRequest,
    BrowserActionResult,
    BrowserActionType,
    BrowserClickRequest,
    BrowserClickResult,
    BrowserElement,
    BrowserExtractRequest,
    BrowserExtractResult,
    BrowserNavigateRequest,
    BrowserNavigateResult,
    BrowserScreenshotModularRequest,
    BrowserScreenshotModularResult,
    BrowserSnapshot,
    BrowserTabsRequest,
    BrowserTabsResult,
    BrowserTypeRequest,
    BrowserTypeResult,
    TabAction,
    TabInfo,
)
from omni_engine.browser.session import BrowserSession
from omni_engine.browser.indexer import DOMActionIndexer
from omni_engine.browser.driver import BrowserDriver
from omni_engine.capabilities import (
    CapabilityRegistry,
    build_canonical_registry,
    build_real_capability_registry,
    BROWSER_NAVIGATE_SPEC,
    BROWSER_SNAPSHOT_SPEC,
    BROWSER_CLICK_SPEC,
    BROWSER_TYPE_SPEC,
    BROWSER_EXTRACT_SPEC,
    BROWSER_SCREENSHOT_SPEC,
    BROWSER_TABS_SPEC,
)
from omni_engine.policy.engine import PolicyEngine
from omni_engine.arguments.resolver import ArgumentResolver


def create_mock_page(url="https://example.com", title="Example Domain", is_closed=False):
    """Helper creating a mock Playwright Page object."""
    page = MagicMock()
    page.url = url
    page.title.return_value = title
    page.is_closed.return_value = is_closed
    page.bring_to_front.return_value = None
    page.close.return_value = None
    page.evaluate.return_value = {"url": url, "title": title, "elements": []}
    locator = MagicMock()
    locator.input_value.return_value = ""
    page.locator.return_value = locator
    return page


def create_mock_context(pages=None):
    """Helper creating a mock Playwright BrowserContext."""
    ctx = MagicMock()
    initial_pages = pages if pages is not None else [create_mock_page()]
    ctx.pages = initial_pages
    ctx.new_page.side_effect = lambda: create_mock_page(url="about:blank", title="New Tab")
    return ctx


class TestL18ModularContracts(unittest.TestCase):
    """Tier 1: Proves all L18 modular contracts enforce strict Pydantic v2 schemas and extra='forbid'."""

    def test_tab_contracts(self):
        tab = TabInfo(tab_id=0, title="Home", url="https://example.com", is_active=True)
        self.assertEqual(tab.tab_id, 0)
        self.assertTrue(tab.is_active)

        with self.assertRaises(ValueError):
            TabInfo(tab_id=0, extra_forbidden="leak")

        req = BrowserTabsRequest(action=TabAction.NEW, url="https://newtab.com")
        self.assertEqual(req.action, TabAction.NEW)
        self.assertEqual(req.url, "https://newtab.com")

        with self.assertRaises(ValueError):
            BrowserTabsRequest(action=TabAction.LIST, invalid_attr=123)

        res = BrowserTabsResult(
            success=True,
            action=TabAction.LIST,
            tabs=[tab],
            active_tab_id=0,
            tab_count=1,
        )
        self.assertTrue(res.success)
        self.assertEqual(len(res.tabs), 1)

    def test_extract_contracts(self):
        req = BrowserExtractRequest(selector="h1", attribute="href", multiple=False, max_items=10)
        self.assertEqual(req.selector, "h1")
        self.assertEqual(req.max_items, 10)

        with self.assertRaises(ValueError):
            BrowserExtractRequest(undeclared_key="injection")

        res = BrowserExtractResult(
            success=True,
            url="https://example.com",
            selector="h1",
            attribute=None,
            items=["Headline 1", "Headline 2"],
            count=2,
        )
        self.assertTrue(res.success)
        self.assertEqual(res.count, 2)

    def test_atomic_action_contracts(self):
        # Navigate
        nav_req = BrowserNavigateRequest(url="https://example.com")
        self.assertEqual(nav_req.url, "https://example.com")
        with self.assertRaises(ValueError):
            BrowserNavigateRequest(url="https://example.com", extra_field=1)

        # Click
        click_req = BrowserClickRequest(target="@1", user_confirmed=True)
        self.assertEqual(click_req.target, "@1")
        self.assertTrue(click_req.user_confirmed)
        with self.assertRaises(ValueError):
            BrowserClickRequest(target="@1", forbidden=True)

        # Type
        type_req = BrowserTypeRequest(target="@2", text="hello world", press_enter=True)
        self.assertEqual(type_req.text, "hello world")
        self.assertTrue(type_req.press_enter)
        with self.assertRaises(ValueError):
            BrowserTypeRequest(target="@2", text="hi", invalid=1)

        # Screenshot
        shot_req = BrowserScreenshotModularRequest(output_path="test.png", full_page=True)
        self.assertTrue(shot_req.full_page)
        with self.assertRaises(ValueError):
            BrowserScreenshotModularRequest(bad=True)


class TestL18MultiTabSession(unittest.TestCase):
    """Tier 2: Proves bounded multi-tab management, safety limits, and dead page pruning."""

    def test_bounded_tabs_and_max_tabs_limit(self):
        """Proves maximum 5 tabs boundary enforcement."""
        ctx = create_mock_context(pages=[create_mock_page(url=f"https://site{i}.com") for i in range(3)])
        session = BrowserSession(headless=True, mock_context=ctx)

        tabs = session.list_tabs()
        self.assertEqual(len(tabs), 3)

        # Open tab 4 and tab 5
        t4 = session.new_tab("https://site4.com")
        self.assertEqual(t4["tab_id"], 3)
        t5 = session.new_tab("https://site5.com")
        self.assertEqual(t5["tab_id"], 4)

        # 6th tab exceeds max_tabs (5) and MUST raise RuntimeError
        with self.assertRaises(RuntimeError) as cm:
            session.new_tab("https://site6.com")
        self.assertIn("Maximum browser tab limit (5) reached", str(cm.exception))

    def test_last_tab_close_protection(self):
        """REV-L18-04: Proves context refuses to close the last remaining tab."""
        p0 = create_mock_page(url="https://site0.com")
        ctx = create_mock_context(pages=[p0])
        session = BrowserSession(headless=True, mock_context=ctx)

        self.assertEqual(len(session.list_tabs()), 1)
        with self.assertRaises(RuntimeError) as cm:
            session.close_tab(0)
        self.assertIn("Cannot close the last remaining browser tab", str(cm.exception))

    def test_close_tab_safe_unload_and_active_reassignment(self):
        """REV-L18-04: Proves close_tab uses run_before_unload=False and shifts active index."""
        p0 = create_mock_page(url="https://site0.com")
        p1 = create_mock_page(url="https://site1.com")
        ctx = create_mock_context(pages=[p0, p1])
        session = BrowserSession(headless=True, mock_context=ctx)

        # Switch to tab 1
        session.switch_tab(1)
        self.assertEqual(session._active_tab_index, 1)

        # Close tab 1
        res = session.close_tab(1)
        self.assertEqual(res["closed_tab_id"], 1)
        self.assertEqual(res["active_tab_id"], 0)
        self.assertEqual(res["remaining_tabs"], 1)

        # Verify page.close(run_before_unload=False) was invoked
        p1.close.assert_called_with(run_before_unload=False)

    def test_dead_page_auto_pruning(self):
        """REV-L18-03: Proves closed or crashed pages are automatically pruned."""
        p0 = create_mock_page(url="https://live.com", is_closed=False)
        p1 = create_mock_page(url="https://crashed.com", is_closed=True)
        ctx = create_mock_context(pages=[p0, p1])
        session = BrowserSession(headless=True, mock_context=ctx)

        # On list_tabs, dead page p1 must be pruned
        tabs = session.list_tabs()
        self.assertEqual(len(tabs), 1)
        self.assertEqual(tabs[0]["url"], "https://live.com")


class TestL18BrowserDriverModular(unittest.TestCase):
    """Tier 3: Proves atomic capability methods, CDP dict binding, and indexed selector translation."""

    def setUp(self):
        self.mock_page = create_mock_page(url="https://test.local/form")
        self.ctx = create_mock_context(pages=[self.mock_page])
        self.session = BrowserSession(headless=True, mock_context=self.ctx)
        self.driver = BrowserDriver(session=self.session)

    def test_extract_cdp_dict_parameter_binding(self):
        """REV-L18-01: Proves parameters are passed as dict into page.evaluate without string interpolation."""
        self.mock_page.evaluate.return_value = ["Item 1", "Item 2", "Item 3"]

        res = self.driver.extract(selector="div.item", attribute=None, multiple=True, max_items=10)
        self.assertTrue(res.success)
        self.assertEqual(res.count, 3)
        self.assertEqual(res.items, ["Item 1", "Item 2", "Item 3"])

        # Assert evaluate was called with dict arguments over the CDP bridge
        self.mock_page.evaluate.assert_called_once()
        args, kwargs = self.mock_page.evaluate.call_args
        self.assertIsInstance(args[1], dict)
        self.assertEqual(args[1]["selector"], "div.item")
        self.assertIsNone(args[1]["attribute"])
        self.assertTrue(args[1]["multiple"])
        self.assertEqual(args[1]["max_items"], 10)

    def test_indexed_selector_translation(self):
        """REV-L18-06: Proves @N translates to [data-laya-idx='N'] in extract and direct actions."""
        self.mock_page.evaluate.return_value = ["Extracted Button Text"]

        # Call extract with @4
        res = self.driver.extract(selector="@4")
        self.assertTrue(res.success)

        # Assert translated selector was passed
        args, _ = self.mock_page.evaluate.call_args
        self.assertEqual(args[1]["selector"], '[data-laya-idx="4"]')

    def test_navigate_atomic_method(self):
        """Proves driver.navigate() executes successfully and returns typed BrowserNavigateResult."""
        res = self.driver.navigate("https://example.org")
        self.assertTrue(res.success)
        self.mock_page.goto.assert_called_with("https://example.org", timeout=15000, wait_until="domcontentloaded")

    def test_click_and_type_atomic_methods(self):
        """Proves driver.click() and driver.type_text() execute and return strongly typed receipts."""
        locator = MagicMock()
        locator.input_value.return_value = "antigravity"
        self.mock_page.locator.return_value = locator
        self.mock_page.evaluate.return_value = 1  # 1 DOM mutation

        # Click
        click_res = self.driver.click("button#submit")
        self.assertTrue(click_res.success)
        locator.click.assert_called()

        # Type text
        type_res = self.driver.type_text("input#search", "antigravity", press_enter=True)
        self.assertTrue(type_res.success)
        self.assertTrue(type_res.input_value_verified)
        locator.fill.assert_called_with("antigravity", timeout=5000)
        locator.press.assert_called_with("Enter")

    def test_screenshot_atomic_method(self):
        """Proves driver.take_screenshot() writes file and validates existence."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            tf.write(b"\x89PNG\r\n\x1a\nfakeimagebytes")
            temp_path = tf.name

        try:
            self.mock_page.screenshot.side_effect = lambda path, full_page: None
            res = self.driver.take_screenshot(output_path=temp_path)
            self.assertTrue(res.success)
            self.assertEqual(res.file_path, temp_path)
            self.assertGreater(res.file_size_bytes, 0)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_manage_tabs_dispatch(self):
        """Proves driver.manage_tabs() routes tab operations accurately."""
        # 1. List
        list_res = self.driver.manage_tabs(action=TabAction.LIST)
        self.assertTrue(list_res.success)
        self.assertEqual(list_res.tab_count, 1)

        # 2. New
        new_res = self.driver.manage_tabs(action=TabAction.NEW, url="https://beta.com")
        self.assertTrue(new_res.success)
        self.assertEqual(new_res.tab_count, 2)

        # 3. Switch
        switch_res = self.driver.manage_tabs(action=TabAction.SWITCH, tab_id=0)
        self.assertTrue(switch_res.success)
        self.assertEqual(switch_res.active_tab_id, 0)


class TestL18FinancialSafetyGating(unittest.TestCase):
    """Tier 4: Proves REV-L18-02 financial safety gate protects all modular browser actions."""

    def setUp(self):
        self.mock_page = create_mock_page(url="https://store.local/cart")
        self.ctx = create_mock_context(pages=[self.mock_page])
        self.session = BrowserSession(headless=True, mock_context=self.ctx)
        self.driver = BrowserDriver(session=self.session)
        self.policy = PolicyEngine(default_autonomy=AutonomyProfile.LOCAL_OPERATOR)

    def test_driver_blocks_unconfirmed_financial_click(self):
        """Proves BrowserDriver halts financial click when user_confirmed=False."""
        res = self.driver.click("button#checkout", user_confirmed=False)
        self.assertFalse(res.success)
        self.assertIn("Financial confirmation required", res.error)

        # When confirmed, execution proceeds
        locator = MagicMock()
        self.mock_page.locator.return_value = locator
        self.mock_page.evaluate.return_value = 0
        res_ok = self.driver.click("button#checkout", user_confirmed=True)
        self.assertTrue(res_ok.success)

    def test_driver_blocks_unconfirmed_financial_type(self):
        """Proves BrowserDriver halts financial typing into credit card field when user_confirmed=False."""
        res = self.driver.type_text("input#card_number", "4111222233334444", user_confirmed=False)
        self.assertFalse(res.success)
        self.assertIn("Financial confirmation required", res.error)

    def test_policy_engine_gates_modular_browser_financial_actions(self):
        """REV-L18-02: Proves PolicyEngine Stage 3 enforces REQUIRE_CONFIRMATION for browser.click / browser.type."""
        # 1. browser.click targeting checkout
        decision_click = self.policy.evaluate(
            capability=BROWSER_CLICK_SPEC,
            arguments={"target": "button.pay_now"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertEqual(decision_click.effect, PolicyEffect.REQUIRE_CONFIRMATION)

        # 2. browser.type targeting card
        decision_type = self.policy.evaluate(
            capability=BROWSER_TYPE_SPEC,
            arguments={"target": "input#cvv", "text": "123"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertEqual(decision_type.effect, PolicyEffect.REQUIRE_CONFIRMATION)

        # 3. browser.navigate to financial URL
        decision_nav = self.policy.evaluate(
            capability=BROWSER_NAVIGATE_SPEC,
            arguments={"url": "https://secure.bank.com/checkout"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertEqual(decision_nav.effect, PolicyEffect.REQUIRE_CONFIRMATION)

        # 4. Safe browser.navigate requires no confirmation
        decision_safe = self.policy.evaluate(
            capability=BROWSER_NAVIGATE_SPEC,
            arguments={"url": "https://docs.python.org"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertEqual(decision_safe.effect, PolicyEffect.ALLOW)


class TestL18RegistryAndResolvers(unittest.TestCase):
    """Tier 5: Proves 23-tool canonical registry invariant, modular registrations, and argument resolution."""

    def test_canonical_registry_invariant_remains_exactly_23(self):
        """REV-L18-08 Invariant: Proves build_canonical_registry() contains exactly 23 source tools."""
        can = build_canonical_registry()
        self.assertEqual(can.count(), 23)

    def test_real_registry_contains_all_modular_capabilities_and_aliases(self):
        """Proves build_real_capability_registry() registers all 7 modular capabilities with dot and dotless aliases."""
        real = build_real_capability_registry()

        expected_pairs = [
            ("browser.navigate", "browser_navigate"),
            ("browser.snapshot", "browser_snapshot"),
            ("browser.click", "browser_click"),
            ("browser.type", "browser_type"),
            ("browser.extract", "browser_extract"),
            ("browser.screenshot", "browser_screenshot_v2"),  # REV-L18-08 collision defense
            ("browser.tabs", "browser_tabs"),
            ("browser.interact", "browser_interact"),
        ]

        for dot_id, dotless_id in expected_pairs:
            self.assertTrue(real.has(dot_id), f"Missing modular capability {dot_id}")
            self.assertTrue(real.has(dotless_id), f"Missing dotless alias {dotless_id}")

    def test_argument_resolver_slot_extraction(self):
        """Proves ArgumentResolver maps natural language to modular browser slots."""
        resolver = ArgumentResolver()

        # 1. Navigate
        env_nav = resolver.resolve(
            BROWSER_NAVIGATE_SPEC,
            "Navigate to https://news.ycombinator.com",
        )
        self.assertEqual(env_nav.arguments.get("url"), "https://news.ycombinator.com")

        # 2. Click
        env_click = resolver.resolve(
            BROWSER_CLICK_SPEC,
            "Click on element @5",
        )
        self.assertEqual(env_click.arguments.get("target"), "@5")

        # 3. Type
        env_type = resolver.resolve(
            BROWSER_TYPE_SPEC,
            "Type 'autonomous agent' into @2",
        )
        self.assertEqual(env_type.arguments.get("target"), "@2")
        self.assertEqual(env_type.arguments.get("text"), "autonomous agent")

        # 4. Extract
        env_ext = resolver.resolve(
            BROWSER_EXTRACT_SPEC,
            "Extract href attribute from @3",
        )
        self.assertEqual(env_ext.arguments.get("selector"), "@3")
        self.assertEqual(env_ext.arguments.get("attribute"), "href")

        # 5. Tabs
        env_tabs = resolver.resolve(
            BROWSER_TABS_SPEC,
            "Open new tab with https://google.com",
        )
        self.assertEqual(env_tabs.arguments.get("action"), "new")
        self.assertEqual(env_tabs.arguments.get("url"), "https://google.com")

    def test_adapter_outcome_normalization_in_registry_invoke(self):
        """REV-L18-09: Proves CapabilityRegistry.invoke maps (True, dict) -> SUCCESS and (False, ToolError) -> FAILURE."""
        mock_driver = MagicMock()
        mock_driver.navigate.return_value = BrowserNavigateResult(
            success=True,
            previous_url="",
            current_url="https://ok.com",
            title="OK",
            url_changed=True,
        )

        reg = build_real_capability_registry(browser_driver=mock_driver)

        # 1. Successful invocation
        inv_ok = CapabilityInvocation(
            invocation_id="inv1",
            capability_id="browser.navigate",
            arguments={"url": "https://ok.com"},
        )
        res_ok = reg.invoke(inv_ok)
        self.assertEqual(res_ok.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res_ok.success)
        self.assertIsNone(res_ok.error)

        # 2. Failed invocation
        mock_driver.navigate.return_value = BrowserNavigateResult(
            success=False,
            previous_url="",
            current_url="",
            title="",
            error="Connection timed out",
        )
        inv_fail = CapabilityInvocation(
            invocation_id="inv2",
            capability_id="browser.navigate",
            arguments={"url": "https://bad.com"},
        )
        res_fail = reg.invoke(inv_fail)
        self.assertEqual(res_fail.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res_fail.success)
        self.assertIsNotNone(res_fail.error)
        self.assertIn("Connection timed out", res_fail.error.message)


if __name__ == "__main__":
    unittest.main()
