"""
tests.test_r2_browser
=====================
Comprehensive test suite for Phase R2: Real Persistent Browser Engine.

Enforces REQ-B1 through REQ-B5:
1. Typed Browser contracts (BrowserElement, BrowserSnapshot, BrowserActionRequest, BrowserActionResult).
2. Resource lifecycle safety & isolated profile directory.
3. DOM Action Indexer with dynamic numbered indices (@1..@N) and staleness verification.
4. Intrinsic Financial & Checkout Safety Gating (REQ-B4).
5. CapabilityRegistry, PolicyEngine, and ArgumentResolver substrate integration.
6. Local offline HTML Playwright integration test running in <1.5s.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    VerificationStatus,
)
from omni_engine.contracts.browser import (
    BrowserActionRequest,
    BrowserActionResult,
    BrowserActionType,
    BrowserElement,
    BrowserSnapshot,
)
from omni_engine.capabilities import (
    CapabilityRegistry,
    build_canonical_registry,
    build_real_capability_registry,
    BROWSER_INTERACT_SPEC,
    make_browser_interact_adapter,
)
from omni_engine.policy.engine import PolicyEngine
from omni_engine.arguments.resolver import ArgumentResolver
from omni_engine.browser.session import (
    BrowserSession,
    _cleanup_stale_locks,
)
from omni_engine.browser.indexer import (
    DOMActionIndexer,
    FINANCIAL_KEYWORDS_REGEX,
    FINANCIAL_URL_REGEX,
)
from omni_engine.browser.driver import BrowserDriver


class TestR1BrowserContractsAndSafetyRegex(unittest.TestCase):
    """Tier 1: Pure Unit Tests for browser contracts, staleness detection, and safety regexes."""

    def test_browser_element_contract(self):
        """Proves BrowserElement validates strictly with extra='forbid'."""
        elem = BrowserElement(
            index="@1",
            tag_name="button",
            role="button",
            text="Add to Cart",
            selector='[data-laya-idx="1"]',
            snapshot_id="snap123",
        )
        self.assertEqual(elem.index, "@1")
        self.assertTrue(elem.is_interactive)
        self.assertFalse(elem.is_financial)

        # Forbid undeclared attributes
        with self.assertRaises(ValueError):
            BrowserElement(
                index="@2",
                tag_name="a",
                selector="a",
                snapshot_id="snap",
                undeclared_field="invalid",
            )

    def test_financial_keywords_regex(self):
        """Proves financial regex accurately tags checkout/payment actions and ignores normal buttons."""
        # Financial targets
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Checkout Now ($29.99)")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Pay with Credit Card")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Place Order")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Buy Now")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Confirm Purchase")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("Enter Card Number")))
        self.assertTrue(bool(FINANCIAL_KEYWORDS_REGEX.search("CVV Code")))

        # Safe targets
        self.assertFalse(bool(FINANCIAL_KEYWORDS_REGEX.search("Log In")))
        self.assertFalse(bool(FINANCIAL_KEYWORDS_REGEX.search("Submit Query")))
        self.assertFalse(bool(FINANCIAL_KEYWORDS_REGEX.search("Next Page")))
        self.assertFalse(bool(FINANCIAL_KEYWORDS_REGEX.search("Read Documentation")))

    def test_financial_url_regex(self):
        """Proves financial URL regex matches checkout domains and paths."""
        self.assertTrue(bool(FINANCIAL_URL_REGEX.search("https://store.com/checkout/step2")))
        self.assertTrue(bool(FINANCIAL_URL_REGEX.search("https://shop.org/pay?id=123")))
        self.assertTrue(bool(FINANCIAL_URL_REGEX.search("https://paypal.com/signin")))
        self.assertTrue(bool(FINANCIAL_URL_REGEX.search("https://checkout.stripe.com/pay")))

        self.assertFalse(bool(FINANCIAL_URL_REGEX.search("https://example.com/about")))
        self.assertFalse(bool(FINANCIAL_URL_REGEX.search("https://docs.python.org/3/")))

    def test_stale_lock_cleanup(self):
        """Proves stale lock files in profile dir are safely cleaned."""
        temp_dir = tempfile.mkdtemp()
        try:
            lock_file = os.path.join(temp_dir, "SingletonLock")
            with open(lock_file, "w") as f:
                f.write("test_lock")
            self.assertTrue(os.path.exists(lock_file))

            _cleanup_stale_locks(temp_dir)
            self.assertFalse(os.path.exists(lock_file))
        finally:
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)


class TestR2SubstrateIntegration(unittest.TestCase):
    """Validates registration in CapabilityRegistry, PolicyEngine, and ArgumentResolver."""

    def test_canonical_registry_invariant_preserved(self):
        """Proves canonical registry retains exactly 23 source tools."""
        canonical = build_canonical_registry()
        self.assertEqual(canonical.count(), 23)

    def test_build_real_capability_registry(self):
        """Proves real capability registry includes browser_interact and alias browser.interact."""
        reg = build_real_capability_registry()
        self.assertGreaterEqual(reg.count(), 27)
        self.assertIsNotNone(reg.get("browser_interact"))
        self.assertIsNotNone(reg.get("browser.interact"))

        spec = reg.get("browser_interact").spec
        self.assertEqual(spec.action_class, ActionClass.EXTERNAL_UPDATE)
        self.assertEqual(spec.minimum_autonomy_profile, AutonomyProfile.LOCAL_OPERATOR)
        self.assertEqual(spec.confirmation_policy, ConfirmationPolicy.POLICY_CONTROLLED)

    def test_policy_engine_evaluates_browser_interact(self):
        """Proves PolicyEngine approves normal browser navigation under LOCAL_OPERATOR with EXTERNAL_NETWORK blast radius."""
        policy = PolicyEngine()
        spec = BROWSER_INTERACT_SPEC
        decision = policy.evaluate(
            capability=spec,
            arguments={"action": "navigate", "url": "https://example.com"},
            autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.assessment.blast_radius, "EXTERNAL_NETWORK")

    def test_policy_engine_gates_financial_browser_action(self):
        """REQ-B4: Proves PolicyEngine gates financial browser actions requiring confirmation."""
        policy = PolicyEngine()
        spec = BROWSER_INTERACT_SPEC

        # Unconfirmed checkout target -> REQUIRE_CONFIRMATION
        decision = policy.evaluate(
            capability=spec,
            arguments={"action": "click", "target": "Checkout Now ($49.99)"},
            autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
            user_confirmed=False,
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.effect.value, "REQUIRE_CONFIRMATION")

        # Confirmed checkout target -> ALLOW
        decision_confirmed = policy.evaluate(
            capability=spec,
            arguments={"action": "click", "target": "Checkout Now ($49.99)"},
            autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
            user_confirmed=True,
        )
        self.assertTrue(decision_confirmed.allowed)

    def test_argument_resolver_extracts_browser_slots(self):
        """Proves ArgumentResolver extracts action, target (@N), and text deterministically."""
        resolver = ArgumentResolver()
        spec = BROWSER_INTERACT_SPEC

        # Navigate
        env1 = resolver.resolve(spec, "navigate to https://github.com/login")
        self.assertTrue(env1.is_valid)
        self.assertEqual(env1.arguments["action"], "navigate")
        self.assertEqual(env1.arguments["url"], "https://github.com/login")

        # Click on @3
        env2 = resolver.resolve(spec, "click button @3")
        self.assertTrue(env2.is_valid)
        self.assertEqual(env2.arguments["action"], "click")
        self.assertEqual(env2.arguments["target"], "@3")

        # Type with quotes
        env3 = resolver.resolve(spec, 'type "antigravity" into @2')
        self.assertTrue(env3.is_valid)
        self.assertEqual(env3.arguments["action"], "type")
        self.assertEqual(env3.arguments["target"], "@2")
        self.assertEqual(env3.arguments["text"], "antigravity")


class TestR2DriverMockedSafety(unittest.TestCase):
    """Tier 2: Mocked Driver Unit Tests for staleness detection and financial gate."""

    def test_financial_gate_in_driver_blocks_unconfirmed_action(self):
        """REQ-B4: Proves BrowserDriver refuses financial action without user confirmation."""
        mock_session = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com/cart"
        mock_session.get_active_page.return_value = mock_page

        driver = BrowserDriver(session=mock_session)

        # Unconfirmed purchase request
        req = BrowserActionRequest(
            action_type=BrowserActionType.CLICK,
            target="Place Order ($19.99)",
            user_confirmed=False,
        )
        res = driver.execute(req)

        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.UNVERIFIED)
        self.assertIn("Financial confirmation required", res.error)

    def test_staleness_verification_failure(self):
        """REQ-B2: Proves staleness mismatch halts action with clear conflict error."""
        mock_session = MagicMock()
        mock_page = MagicMock()
        mock_page.url = "https://example.com/app"
        mock_session.get_active_page.return_value = mock_page

        mock_indexer = MagicMock()
        mock_indexer.verify_staleness.return_value = (False, "Tag changed from button to div")

        driver = BrowserDriver(session=mock_session, indexer=mock_indexer)

        # Set cached snapshot containing @1
        elem = BrowserElement(
            index="@1",
            tag_name="button",
            role="button",
            text="Submit",
            selector='[data-laya-idx="1"]',
            snapshot_id="s1",
        )
        driver._last_snapshot = BrowserSnapshot(
            snapshot_id="s1",
            url="https://example.com/app",
            elements=[elem],
        )

        req = BrowserActionRequest(
            action_type=BrowserActionType.CLICK,
            target="@1",
        )
        res = driver.execute(req)

        self.assertFalse(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_FAILURE)
        self.assertIn("Stale element conflict", res.error)


class TestR2LocalBrowserIntegration(unittest.TestCase):
    """Tier 3: Single Headless Playwright Integration Test against local HTML fixture."""

    @classmethod
    def setUpClass(cls):
        cls.temp_profile = tempfile.mkdtemp()
        cls.session = BrowserSession(profile_dir=cls.temp_profile, headless=True)
        cls.driver = BrowserDriver(session=cls.session)
        cls.fixture_path = os.path.join(ROOT_DIR, "tests", "fixtures", "browser_test_page.html")
        cls.fixture_url = f"file:///{cls.fixture_path.replace(os.sep, '/')}"

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        import shutil
        shutil.rmtree(cls.temp_profile, ignore_errors=True)

    def test_01_navigate_and_snapshot(self):
        """Proves navigation to local fixture, element indexing, and financial detection."""
        req = BrowserActionRequest(
            action_type=BrowserActionType.NAVIGATE,
            url=self.fixture_url,
        )
        res = self.driver.execute(req)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)

        snap = self.driver.get_last_snapshot()
        self.assertIsNotNone(snap)
        self.assertGreaterEqual(snap.interactive_count, 3)

        # Check elements: input, login button, dropdown, and checkout button
        indices = [e.index for e in snap.elements]
        self.assertIn("@1", indices)
        self.assertIn("@2", indices)

        # Financial button must be tagged is_financial=True
        checkout_elems = [e for e in snap.elements if "Purchase" in e.text or "Checkout" in e.text]
        self.assertTrue(len(checkout_elems) > 0)
        self.assertTrue(checkout_elems[0].is_financial)

    def test_02_type_action_with_physical_verification(self):
        """Proves typing text into input physically verifies input_value."""
        snap = self.driver.get_last_snapshot()
        input_elem = [e for e in snap.elements if e.tag_name == "input"][0]

        req = BrowserActionRequest(
            action_type=BrowserActionType.TYPE,
            target=input_elem.index,
            text="antigravity_tester",
        )
        res = self.driver.execute(req)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)
        self.assertEqual(res.verification_evidence["actual_value"], "antigravity_tester")

    def test_03_click_action_and_dom_mutation(self):
        """Proves clicking login button triggers DOM mutation and verifies success."""
        snap = self.driver.get_last_snapshot()
        btn = [e for e in snap.elements if "Log In" in e.text][0]

        req = BrowserActionRequest(
            action_type=BrowserActionType.CLICK,
            target=btn.index,
        )
        res = self.driver.execute(req)
        self.assertTrue(res.success)
        self.assertEqual(res.verification_status, VerificationStatus.VERIFIED_SUCCESS)

    def test_04_financial_button_safety_gate(self):
        """REQ-B4: Proves checkout button click is blocked unconfirmed and allowed when confirmed."""
        snap = self.driver.get_last_snapshot()
        checkout_btn = [e for e in snap.elements if e.is_financial][0]

        # 1. Unconfirmed -> Blocked
        req_unconfirmed = BrowserActionRequest(
            action_type=BrowserActionType.CLICK,
            target=checkout_btn.index,
            user_confirmed=False,
        )
        res_blocked = self.driver.execute(req_unconfirmed)
        self.assertFalse(res_blocked.success)
        self.assertIn("Financial confirmation required", res_blocked.error)

        # 2. Confirmed -> Allowed
        req_confirmed = BrowserActionRequest(
            action_type=BrowserActionType.CLICK,
            target=checkout_btn.index,
            user_confirmed=True,
        )
        res_allowed = self.driver.execute(req_confirmed)
        self.assertTrue(res_allowed.success)


if __name__ == "__main__":
    unittest.main()
