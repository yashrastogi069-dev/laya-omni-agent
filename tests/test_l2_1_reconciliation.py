"""
Checkpoint L2.1 Contract & Registry Reconciliation Test Suite
============================================================
Validates:
1. Exact programmatic source tool inventory (23 tools, zero unregistered functions, no duplicates).
2. Complete 19-member ErrorCode taxonomy, with distinct PERMISSION_DENIED, UNAUTHORIZED_ACTION, and UNKNOWN_COMMIT.
3. DecisionSignal rich provenance fields and extended signals (NEEDS_CLARIFICATION, REQUIRES_ACTION, etc.).
4. Explicit CapabilitySpec policy enums (ConfirmationPolicy, RetryPolicy, IdempotencyClass, minimum_autonomy_profile).
5. ToolOutcome partial outcome semantics (SUCCESS, PARTIAL, FAILURE) and mutual exclusivity invariants.
6. CapabilityInvocation structured context and validation.
7. Extended TraceContext causal correlation fields.
8. Wire/persisted contract schema versioning.
"""

import os
import sys
import unittest
from pydantic import ValidationError

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.tools import OMNI_TOOL_REGISTRY
import omni_engine.tools.web_tools as wt
import omni_engine.tools.browser_tools as bt
import omni_engine.tools.os_tools as ot
import omni_engine.tools.dev_tools as dt
import omni_engine.tools.data_tools as dat

from omni_engine.contracts import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    RetryPolicy,
    IdempotencyClass,
    ToolOutcome,
    VerificationStatus,
    ErrorCode,
    DecisionSignalType,
    DecisionSignal,
    DecisionFrame,
    CapabilitySpec,
    CapabilityInvocation,
    ToolError,
    ExecutionReceipt,
    VerificationResult,
    ToolResult,
    TraceContext,
    AgentRequest,
    AgentResponse,
    AgentEvent,
)


class TestL21CanonicalRegistryInventory(unittest.TestCase):
    CANONICAL_TOOL_IDS = {
        # Web (4)
        "web_search", "scrape_url", "http_api", "download_file",
        # Browser (2)
        "visual_browse", "browser_screenshot",
        # OS (8)
        "system_diagnostics", "list_processes", "kill_process", "launch_app",
        "desktop_screenshot", "clipboard", "powershell", "ping_test",
        # Dev (6)
        "file_read", "file_write", "search_code", "directory_tree", "run_python", "git_status",
        # Data (3)
        "sqlite_exec", "inspect_data", "safe_math"
    }

    def test_registry_count_and_keys_match_canonical_source(self):
        """Asserts exactly 23 tools exist in source with exact canonical IDs and no duplicates."""
        actual_keys = set(OMNI_TOOL_REGISTRY.keys())
        self.assertEqual(len(OMNI_TOOL_REGISTRY), 23)
        self.assertEqual(actual_keys, self.CANONICAL_TOOL_IDS)

    def test_zero_unregistered_tool_functions_in_source_modules(self):
        """Inspects all tool modules to prove zero unexported tool functions exist."""
        registered_funcs = {v["func"] for v in OMNI_TOOL_REGISTRY.values()}
        
        all_module_funcs = set()
        for mod in (wt, bt, ot, dt, dat):
            for attr in dir(mod):
                if attr.startswith("tool_"):
                    all_module_funcs.add(getattr(mod, attr))

        self.assertEqual(len(all_module_funcs), 23)
        self.assertEqual(registered_funcs, all_module_funcs)

    def test_tool_domain_categorization(self):
        """Verifies exact category distribution across the 23 tools."""
        domain_counts = {}
        for v in OMNI_TOOL_REGISTRY.values():
            cat = v["category"]
            domain_counts[cat] = domain_counts.get(cat, 0) + 1

        self.assertEqual(domain_counts["web"], 4)
        self.assertEqual(domain_counts["browser"], 2)
        self.assertEqual(domain_counts["os"], 8)
        self.assertEqual(domain_counts["dev"], 6)
        self.assertEqual(domain_counts["data"], 3)


class TestL21ErrorTaxonomy(unittest.TestCase):
    def test_all_19_error_codes_defined(self):
        """Asserts complete 19-member taxonomy with exact string values."""
        expected = {
            "UNKNOWN", "INVALID_ARGUMENT", "SCHEMA_VIOLATION",
            "UNCONFIGURED", "AUTH_REQUIRED",
            "PERMISSION_DENIED", "UNAUTHORIZED_ACTION", "CONFIRMATION_REJECTED",
            "NOT_FOUND", "ALREADY_EXISTS", "CONFLICT",
            "RATE_LIMITED", "TIMEOUT", "NETWORK_ERROR", "SERVICE_UNAVAILABLE",
            "PROCESS_FAILED", "CANCELLED",
            "UNKNOWN_COMMIT", "INTERNAL_ERROR"
        }
        self.assertEqual({e.value for e in ErrorCode}, expected)

    def test_permission_denied_vs_unauthorized_action_distinct(self):
        """Verifies clear distinction between OS/external denial and internal policy refusal."""
        self.assertNotEqual(ErrorCode.PERMISSION_DENIED, ErrorCode.UNAUTHORIZED_ACTION)
        err_perm = ToolError(code=ErrorCode.PERMISSION_DENIED, message="EACCES: permission denied")
        err_unauth = ToolError(code=ErrorCode.UNAUTHORIZED_ACTION, message="Autonomy tier blocked deletion")
        self.assertEqual(err_perm.code.value, "PERMISSION_DENIED")
        self.assertEqual(err_unauth.code.value, "UNAUTHORIZED_ACTION")

    def test_unknown_commit_representation(self):
        """UNKNOWN_COMMIT is distinct and represents uncertain side-effect mutation state."""
        err = ToolError(
            code=ErrorCode.UNKNOWN_COMMIT,
            message="HTTP POST timed out after transmission; server state unconfirmed",
            retryable=False,
            fix_action="Manual reconciliation required via audit log"
        )
        self.assertEqual(err.code, ErrorCode.UNKNOWN_COMMIT)
        self.assertFalse(err.retryable)


class TestL21DecisionSignalsAndFrame(unittest.TestCase):
    def test_extended_decision_signal_types(self):
        """All 16 decision signal types are present including L2.1 additions."""
        types = {dst.value for dst in DecisionSignalType}
        self.assertIn("NEEDS_CLARIFICATION", types)
        self.assertIn("REQUIRES_ACTION", types)
        self.assertIn("NEEDS_GENERATIVE_REASONING", types)
        self.assertIn("ESCALATION_REQUIRED", types)
        self.assertEqual(len(types), 16)

    def test_decision_signal_provenance_fields(self):
        """DecisionSignal stores calibration, model, and provider provenance."""
        sig = DecisionSignal(
            signal_type=DecisionSignalType.NEEDS_CLARIFICATION,
            value=True,
            confidence=0.91,
            provider_id="laya-modernbert",
            model_id="modernbert-large-s1-v2",
            decision_schema_version="1.0.0",
            calibration_version="isotonic-2026-q3",
            latency_ms=1.8
        )
        self.assertEqual(sig.provider_id, "laya-modernbert")
        self.assertEqual(sig.model_id, "modernbert-large-s1-v2")
        self.assertEqual(sig.decision_schema_version, "1.0.0")
        self.assertEqual(sig.calibration_version, "isotonic-2026-q3")

    def test_decision_frame_schema_version_and_extended_signals(self):
        """DecisionFrame supports schema_version and extended signals."""
        def make_sig(sig_type, val):
            return DecisionSignal(signal_type=sig_type, value=val, confidence=0.9)

        frame = DecisionFrame(
            schema_version="1.0.0",
            request_id="req-l21",
            timestamp=1727060000.0,
            intent=make_sig(DecisionSignalType.INTENT, "search"),
            task_class=make_sig(DecisionSignalType.TASK_CLASS, "query"),
            urgency=make_sig(DecisionSignalType.URGENCY, "normal"),
            importance=make_sig(DecisionSignalType.IMPORTANCE, "normal"),
            risk=make_sig(DecisionSignalType.RISK, "low"),
            reversibility=make_sig(DecisionSignalType.REVERSIBILITY, "reversible"),
            ambiguity=make_sig(DecisionSignalType.AMBIGUITY, "unambiguous"),
            needs_plan=make_sig(DecisionSignalType.NEEDS_PLAN, False),
            needs_tools=make_sig(DecisionSignalType.NEEDS_TOOLS, True),
            model_tier=make_sig(DecisionSignalType.MODEL_TIER, "system1"),
            needs_clarification=make_sig(DecisionSignalType.NEEDS_CLARIFICATION, False),
            requires_action=make_sig(DecisionSignalType.REQUIRES_ACTION, True),
            needs_generative_reasoning=make_sig(DecisionSignalType.NEEDS_GENERATIVE_REASONING, False),
            escalation_required=make_sig(DecisionSignalType.ESCALATION_REQUIRED, False),
            total_latency_ms=14.2
        )
        self.assertEqual(frame.schema_version, "1.0.0")
        self.assertFalse(frame.needs_clarification.value)
        self.assertTrue(frame.requires_action.value)


class TestL21CapabilityPolicyAndInvocation(unittest.TestCase):
    def test_explicit_policy_enums_on_capability_spec(self):
        """CapabilitySpec uses explicit ConfirmationPolicy, RetryPolicy, and IdempotencyClass."""
        spec = CapabilitySpec(
            schema_version="1.0.0",
            id="dev.file_write",
            name="File Write",
            domain="dev",
            description="Writes file to disk",
            input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
            action_class=ActionClass.LOCAL_CREATE,
            minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
            confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
            retry_policy=RetryPolicy.SAFE_WITH_IDEMPOTENCY,
            idempotency_class=IdempotencyClass.NATURAL,
            side_effects=True,
            timeout_seconds=10.0
        )
        self.assertEqual(spec.minimum_autonomy_profile, AutonomyProfile.LOCAL_OPERATOR)
        self.assertEqual(spec.confirmation_policy, ConfirmationPolicy.POLICY_CONTROLLED)
        self.assertEqual(spec.retry_policy, RetryPolicy.SAFE_WITH_IDEMPOTENCY)
        self.assertEqual(spec.idempotency_class, IdempotencyClass.NATURAL)
        
        # Test backward-compatible properties
        self.assertEqual(spec.autonomy_profile, AutonomyProfile.LOCAL_OPERATOR)
        self.assertFalse(spec.requires_confirmation)  # POLICY_CONTROLLED != ALWAYS
        self.assertTrue(spec.retryable)
        self.assertTrue(spec.idempotent)

    def test_capability_invocation_roundtrip_and_trace_correlation(self):
        """CapabilityInvocation captures execution boundary and correlation fields."""
        trace = TraceContext(
            trace_id="tr-100",
            session_id="sess-100",
            turn_id="turn-5",
            quest_id="quest-77",
            plan_id="plan-12",
            step_id="step-3",
            operation_id="op-99"
        )
        inv = CapabilityInvocation(
            schema_version="1.0.0",
            invocation_id="inv-001",
            capability_id="dev.file_read",
            arguments={"filepath": "config.json"},
            trace_context=trace,
            attempt=1,
            deadline_seconds=5.0,
            current_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
            quest_id="quest-77",
            plan_id="plan-12",
            step_id="step-3",
            operation_id="op-99"
        )
        dumped = inv.model_dump_json()
        loaded = CapabilityInvocation.model_validate_json(dumped)
        self.assertEqual(inv, loaded)
        self.assertEqual(loaded.trace_context.quest_id, "quest-77")
        self.assertEqual(loaded.operation_id, "op-99")


class TestL21ToolOutcomeSemantics(unittest.TestCase):
    def test_tool_outcome_success(self):
        """Outcome SUCCESS enforces success=True and error=None."""
        res = ToolResult(
            capability_id="web.web_search",
            outcome=ToolOutcome.SUCCESS,
            success=True,
            data={"results": ["https://example.com"]}
        )
        self.assertEqual(res.outcome, ToolOutcome.SUCCESS)
        self.assertTrue(res.success)
        self.assertIsNone(res.error)

    def test_tool_outcome_failure(self):
        """Outcome FAILURE enforces success=False, data=None, and error populated."""
        err = ToolError(code=ErrorCode.TIMEOUT, message="Request timed out")
        res = ToolResult(
            capability_id="web.web_search",
            outcome=ToolOutcome.FAILURE,
            success=False,
            error=err
        )
        self.assertEqual(res.outcome, ToolOutcome.FAILURE)
        self.assertFalse(res.success)
        self.assertIsNone(res.data)
        self.assertIsNotNone(res.error)

    def test_tool_outcome_partial(self):
        """Outcome PARTIAL enforces success=False and allows partial data + error context."""
        err = ToolError(
            code=ErrorCode.RATE_LIMITED,
            message="Retrieved 4 of 10 pages before upstream rate limit exceeded"
        )
        res = ToolResult(
            capability_id="web.web_search",
            outcome=ToolOutcome.PARTIAL,
            success=False,
            data={"partial_records": [1, 2, 3, 4], "total_expected": 10},
            error=err
        )
        self.assertEqual(res.outcome, ToolOutcome.PARTIAL)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.data)
        self.assertIsNotNone(res.error)

    def test_tool_outcome_inconsistency_rejections(self):
        """Invalid outcome states raise ValidationError."""
        err = ToolError(code=ErrorCode.PROCESS_FAILED, message="Crashed")

        # PARTIAL with success=True -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="os.launch",
                outcome=ToolOutcome.PARTIAL,
                success=True,
                data={"pid": 123}
            )

        # PARTIAL with no data and no error -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="os.launch",
                outcome=ToolOutcome.PARTIAL,
                success=False
            )

        # SUCCESS with error -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="os.launch",
                outcome=ToolOutcome.SUCCESS,
                success=True,
                error=err
            )

        # FAILURE with data -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="os.launch",
                outcome=ToolOutcome.FAILURE,
                success=False,
                data={"output": "leaked"},
                error=err
            )


if __name__ == "__main__":
    unittest.main()
