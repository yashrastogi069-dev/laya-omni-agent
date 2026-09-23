"""
tests.test_l3_capabilities
==========================
Comprehensive test suite for Checkpoint L3: Canonical Capability Substrate.

Validates:
1. Canonical CapabilityRegistry implementation and lifecycle (L3A).
2. Continuous 1:1 parity with source OMNI_TOOL_REGISTRY (exact 23 tools).
3. Read-only capability execution returning structured ToolResult envelopes (L3B).
4. Error interception: legacy string errors converted to typed ToolErrors.
5. Process-control exceptions (KeyboardInterrupt, SystemExit) are NEVER swallowed.
6. Mutation capabilities declaratively specified with strict policies (L3C).
7. Legacy prototype path preservation and non-switching boundary (L3D).
"""

import inspect
import os
import sys
import tempfile
import unittest
from typing import Any, Dict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.tools import OMNI_TOOL_REGISTRY
from omni_engine.contracts import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
    ToolOutcome,
    VerificationStatus,
    CapabilityInvocation,
    CapabilitySpec,
    ToolResult,
)
from omni_engine.capabilities import (
    CapabilityRegistry,
    CANONICAL_SPECS,
    build_canonical_registry,
    intercept_legacy_error_string,
)


class TestL3ACapabilityRegistry(unittest.TestCase):
    """Tests L3A: Canonical CapabilityRegistry substrate and metadata management."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_registry_count_is_exactly_23(self):
        """Asserts exactly 23 capabilities are registered in canonical registry."""
        self.assertEqual(self.registry.count(), 23)
        self.assertEqual(len(self.registry.list_all()), 23)

    def test_reject_duplicate_registration(self):
        """Asserts registering a capability with an existing ID raises ValueError."""
        spec = CANONICAL_SPECS["safe_math"]
        with self.assertRaises(ValueError) as ctx:
            self.registry.register(spec=spec, implementation=lambda expression: "42")
        self.assertIn("already registered", str(ctx.exception))

    def test_reject_async_coroutine_implementation(self):
        """Asserts registering an async coroutine directly raises ValueError."""
        async def dummy_async():
            pass

        dummy_spec = CapabilitySpec(
            id="dummy_async_cap",
            name="Dummy Async",
            domain="dev",
            description="Dummy",
            input_schema={},
        )
        with self.assertRaises(ValueError) as ctx:
            self.registry.register(spec=dummy_spec, implementation=dummy_async)
        self.assertIn("must be synchronous", str(ctx.exception))

    def test_query_methods(self):
        """Tests get, get_spec, has, list_specs, list_by_domain, list_by_action_class."""
        self.assertTrue(self.registry.has("safe_math"))
        self.assertFalse(self.registry.has("non_existent_tool"))

        exec_cap = self.registry.get("safe_math")
        self.assertIsNotNone(exec_cap)
        self.assertEqual(exec_cap.spec.id, "safe_math")

        spec = self.registry.get_spec("safe_math")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.domain, "data")
        self.assertEqual(spec.action_class, ActionClass.READ_ONLY)

        # Domain filtering
        web_caps = self.registry.list_by_domain("web")
        self.assertEqual(len(web_caps), 4)
        self.assertEqual(sorted(web_caps), ["download_file", "http_api", "scrape_url", "web_search"])

        # Action class filtering
        read_only_caps = self.registry.list_by_action_class(ActionClass.READ_ONLY)
        self.assertEqual(len(read_only_caps), 11)

    def test_export_specs_is_json_serializable(self):
        """Asserts exported specifications are pure JSON-safe dicts."""
        import json
        specs = self.registry.export_specs()
        self.assertEqual(len(specs), 23)
        serialized = json.dumps(specs)
        self.assertIsInstance(serialized, str)


class TestL3AParityWithSourceRegistry(unittest.TestCase):
    """Enforces continuous 1:1 parity between CapabilityRegistry and OMNI_TOOL_REGISTRY."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_exact_1_to_1_id_parity(self):
        """Asserts every tool in OMNI_TOOL_REGISTRY has exact match in CapabilityRegistry."""
        source_ids = set(OMNI_TOOL_REGISTRY.keys())
        canonical_ids = set(self.registry.list_all())
        self.assertEqual(source_ids, canonical_ids)

    def test_domain_distribution_parity(self):
        """Asserts domain counts match source categorizations."""
        expected_distribution = {
            "web": 4,
            "browser": 2,
            "os": 8,
            "dev": 6,
            "data": 3,
        }
        for domain, count in expected_distribution.items():
            actual = len(self.registry.list_by_domain(domain))
            self.assertEqual(actual, count, f"Domain count mismatch for {domain}")


class TestL3BReadOnlyToolResultBoundary(unittest.TestCase):
    """Tests L3B: Read-only capability result boundary and error normalization."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_safe_math_successful_execution(self):
        """Safe math execution returns structured ToolResult with outcome=SUCCESS."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_001",
            capability_id="safe_math",
            arguments={"expression": "sqrt(144) + 10"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res.success)
        self.assertIsNone(res.error)
        self.assertIsNotNone(res.data)
        self.assertIn("22", str(res.data["output"]))
        self.assertIsNotNone(res.receipt)
        self.assertGreaterEqual(res.receipt.duration_ms, 0.0)

    def test_safe_math_error_interception(self):
        """Division by zero returns ToolOutcome.FAILURE with INVALID_ARGUMENT error."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_002",
            capability_id="safe_math",
            arguments={"expression": "10 / 0"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertIsNone(res.data)
        self.assertIsNotNone(res.error)
        self.assertEqual(res.error.code, ErrorCode.INVALID_ARGUMENT)
        self.assertIn("Division by zero", res.error.message)

    def test_file_read_successful_execution(self):
        """Reading an existing file returns ToolOutcome.SUCCESS with content."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_003",
            capability_id="file_read",
            arguments={"filepath": "requirements.txt"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res.success)
        self.assertIn("pydantic", res.data["output"])

    def test_file_read_missing_file_error_interception(self):
        """Reading a non-existent file returns ToolOutcome.FAILURE with NOT_FOUND error."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_004",
            capability_id="file_read",
            arguments={"filepath": "non_existent_file_xyz_12345.txt"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertIsNone(res.data)
        self.assertIsNotNone(res.error)
        self.assertEqual(res.error.code, ErrorCode.NOT_FOUND)

    def test_system_diagnostics_execution(self):
        """System diagnostics returns ToolOutcome.SUCCESS with CPU and RAM telemetry."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_005",
            capability_id="system_diagnostics",
            arguments={},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res.success)
        self.assertIn("CPU Load", res.data["output"])

    def test_git_status_execution(self):
        """Git status execution returns ToolOutcome.SUCCESS."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_006",
            capability_id="git_status",
            arguments={},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res.success)

    def test_unregistered_capability_invocation(self):
        """Invoking an unregistered capability returns ToolOutcome.FAILURE with NOT_FOUND."""
        invocation = CapabilityInvocation(
            invocation_id="inv_test_007",
            capability_id="hypothetical_unknown_cap",
            arguments={},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertEqual(res.error.code, ErrorCode.NOT_FOUND)


class TestL3BProcessControlExceptions(unittest.TestCase):
    """Proves process-control exceptions (KeyboardInterrupt, SystemExit) are never swallowed."""

    def setUp(self):
        self.registry = CapabilityRegistry()

    def test_keyboard_interrupt_propagates(self):
        spec = CapabilitySpec(
            id="test_ki",
            name="Test KI",
            domain="dev",
            description="Test KeyboardInterrupt",
            input_schema={},
        )
        def raise_ki():
            raise KeyboardInterrupt("Simulated user interrupt")

        self.registry.register(spec=spec, implementation=raise_ki)
        invocation = CapabilityInvocation(invocation_id="ki_01", capability_id="test_ki")

        with self.assertRaises(KeyboardInterrupt):
            self.registry.invoke(invocation)

    def test_system_exit_propagates(self):
        spec = CapabilitySpec(
            id="test_se",
            name="Test SE",
            domain="dev",
            description="Test SystemExit",
            input_schema={},
        )
        def raise_se():
            raise SystemExit(1)

        self.registry.register(spec=spec, implementation=raise_se)
        invocation = CapabilityInvocation(invocation_id="se_01", capability_id="test_se")

        with self.assertRaises(SystemExit):
            self.registry.invoke(invocation)


class TestL3CMutationDeclarativeWrappers(unittest.TestCase):
    """Tests L3C: Mutation and system-action capabilities have strict policy contracts."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_mutation_capabilities_have_non_read_only_action_classes(self):
        """All 12 mutation capabilities declare non-READ_ONLY action classes."""
        mutation_ids = [
            "http_api", "download_file", "visual_browse", "browser_screenshot",
            "kill_process", "launch_app", "desktop_screenshot", "clipboard",
            "powershell", "file_write", "run_python", "sqlite_exec"
        ]
        self.assertEqual(len(mutation_ids), 12)
        for mid in mutation_ids:
            spec = self.registry.get_spec(mid)
            self.assertIsNotNone(spec, f"Missing spec for {mid}")
            self.assertNotEqual(
                spec.action_class,
                ActionClass.READ_ONLY,
                f"Capability {mid} must not be ActionClass.READ_ONLY"
            )
            self.assertTrue(spec.side_effects, f"Capability {mid} must have side_effects=True")

    def test_destructive_capabilities_require_high_autonomy_or_confirmation(self):
        """Critical destructive tools (kill_process, powershell, run_python) have strict confirmation policies."""
        strict_tools = ["kill_process", "powershell", "run_python"]
        for tid in strict_tools:
            spec = self.registry.get_spec(tid)
            self.assertEqual(
                spec.confirmation_policy,
                ConfirmationPolicy.ALWAYS,
                f"Destructive tool {tid} must require ConfirmationPolicy.ALWAYS"
            )

    def test_structured_file_write_via_kwargs_adapter(self):
        """Tests that file_write accepts structured kwargs {'filepath': ..., 'content': ...}."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
            temp_path = tf.name

        try:
            invocation = CapabilityInvocation(
                invocation_id="inv_fw_01",
                capability_id="file_write",
                arguments={"filepath": temp_path, "content": "Unit test content 123"},
            )
            res = self.registry.invoke(invocation)
            self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
            self.assertTrue(res.success)
            self.assertEqual(res.receipt.bytes_written, len("Unit test content 123".encode("utf-8")))

            # Verify file content on disk
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertEqual(content, "Unit test content 123")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestL3DLegacyCompatibilityAndNonSwitching(unittest.TestCase):
    """Tests L3D: Existing CLI / prototype functions remain untouched and operational."""

    def test_omni_tool_registry_intact(self):
        """Source OMNI_TOOL_REGISTRY still contains 23 raw callables returning strings."""
        self.assertEqual(len(OMNI_TOOL_REGISTRY), 23)
        raw_res = OMNI_TOOL_REGISTRY["safe_math"]["func"]("10 + 25")
        self.assertIsInstance(raw_res, str)
        self.assertIn("35", raw_res)

    def test_autonomous_planner_instantiable(self):
        """AutonomousPlanner is importable and operates on legacy path."""
        from omni_engine.planner import AutonomousPlanner
        planner = AutonomousPlanner(sys1_engine=None, sys2_engine=None, memory_engine=None)
        self.assertIsNotNone(planner)
        self.assertTrue(hasattr(planner, "plan_and_execute"))


class TestL3All23CapabilitiesInvocation(unittest.TestCase):
    """Proves every single one of the 23 capabilities can be invoked with its schema arguments without TypeError."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_all_23_capabilities_accept_schema_arguments_without_type_error(self):
        test_invocations = {
            "web_search": {"query": "python"},
            "scrape_url": {"url": "https://example.com"},
            "http_api": {"url": "https://example.com/api", "method": "GET"},
            "download_file": {"url": "https://example.com/file.txt", "filename": "test_dl.txt"},
            "visual_browse": {"url": "https://example.com"},
            "browser_screenshot": {"url": "https://example.com"},
            "system_diagnostics": {},
            "list_processes": {"filter_name": "python"},
            "kill_process": {"target": "99999999"},
            "launch_app": {"app_name": "notepad"},
            "desktop_screenshot": {},
            "clipboard": {"action": "read"},
            "powershell": {"command": "Write-Output 'test'"},
            "ping_test": {"host": "127.0.0.1"},
            "file_read": {"filepath": "requirements.txt"},
            "file_write": {"filepath": "_test_scratch_fw.txt", "content": "unit test"},
            "search_code": {"query": "import", "path": "."},
            "directory_tree": {"path": ".", "max_depth": 1},
            "run_python": {"code": "print(42)"},
            "git_status": {},
            "sqlite_exec": {"query": "SELECT 1"},
            "inspect_data": {"file_path": "requirements.txt"},
            "safe_math": {"expression": "1 + 1"},
        }

        self.assertEqual(len(test_invocations), 23)

        for cap_id, args in test_invocations.items():
            with self.subTest(capability=cap_id):
                invocation = CapabilityInvocation(
                    invocation_id=f"inv_all_{cap_id}",
                    capability_id=cap_id,
                    arguments=args,
                )
                try:
                    res = self.registry.invoke(invocation)
                    self.assertIsInstance(res, ToolResult)
                    self.assertEqual(res.capability_id, cap_id)
                    self.assertIsNotNone(res.receipt)
                    self.assertGreaterEqual(res.receipt.duration_ms, 0.0)
                except TypeError as e:
                    self.fail(f"Capability '{cap_id}' crashed with TypeError on valid schema args: {e}")
                finally:
                    # Clean up any scratch files created
                    if cap_id == "file_write" and os.path.exists("_test_scratch_fw.txt"):
                        os.remove("_test_scratch_fw.txt")


class TestL3NoErrorFalsePositivesOnContent(unittest.TestCase):
    """Proves content-bearing tools (file_read, search_code) do NOT trigger false-positive error interception."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_file_read_with_sensitive_strings_succeeds(self):
        """Reading a file containing 'Access is denied' or 'API key missing' returns ToolOutcome.SUCCESS."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w", encoding="utf-8") as tf:
            tf.write("Line 1: Access is denied in some policy.\nLine 2: API key missing warning.\nLine 3: process PID not found.")
            temp_path = tf.name

        try:
            invocation = CapabilityInvocation(
                invocation_id="inv_fp_01",
                capability_id="file_read",
                arguments={"filepath": temp_path},
            )
            res = self.registry.invoke(invocation)
            self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
            self.assertTrue(res.success)
            self.assertIsNone(res.error)
            self.assertIn("Access is denied", res.data["output"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestL3ComprehensiveErrorInterception(unittest.TestCase):
    """Validates that real-world failure outputs from legacy tools are reliably converted to ToolOutcome.FAILURE."""

    def setUp(self):
        self.registry = build_canonical_registry()

    def test_kill_process_missing_pid_returns_not_found(self):
        invocation = CapabilityInvocation(
            invocation_id="inv_err_kill",
            capability_id="kill_process",
            arguments={"target": "999999999"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertEqual(res.error.code, ErrorCode.NOT_FOUND)

    def test_inspect_data_unsupported_format_returns_invalid_argument(self):
        invocation = CapabilityInvocation(
            invocation_id="inv_err_inspect",
            capability_id="inspect_data",
            arguments={"file_path": "requirements.txt"},
        )
        res = self.registry.invoke(invocation)
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertEqual(res.error.code, ErrorCode.INVALID_ARGUMENT)


if __name__ == "__main__":
    unittest.main()
