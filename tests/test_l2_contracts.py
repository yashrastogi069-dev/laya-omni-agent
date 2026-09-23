"""
Checkpoint L2 Contracts Test Suite
==================================
Comprehensive test suite validating:
1. Enum completeness, canonical representations, and rejection of invalid values.
2. DecisionSignal confidence bounds [0.0, 1.0], NaN/Inf rejection, and probability distributions.
3. DecisionFrame completeness, including first-class reversibility signal and extra='forbid'.
4. CapabilitySpec pure JSON serialization round-tripping (separated from callables).
5. ExecutableCapability runtime callable wrapper and availability checks.
6. ToolResult strict mutual exclusivity between success and error envelopes.
7. Explicit representation of UNKNOWN_COMMIT error code.
8. AgentRequest, AgentResponse, TraceContext, and AgentEvent round-trip serialization.
"""

import os
import sys
import json
import math
import unittest
from pydantic import ValidationError

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from omni_engine.contracts import (
    ActionClass,
    AutonomyProfile,
    ErrorCode,
    VerificationStatus,
    DecisionSignalType,
    DecisionSignal,
    DecisionFrame,
    CapabilitySpec,
    ExecutableCapability,
    ToolError,
    ExecutionReceipt,
    VerificationResult,
    ToolResult,
    TraceContext,
    AgentRequest,
    AgentResponse,
    AgentEvent,
)


class TestL2Enums(unittest.TestCase):
    def test_action_classes(self):
        """All 11 canonical action classes are defined with exact string representations."""
        expected = {
            "READ_ONLY", "LOCAL_CREATE", "LOCAL_UPDATE", "LOCAL_DELETE",
            "EXTERNAL_CREATE", "EXTERNAL_UPDATE", "EXTERNAL_SEND", "EXTERNAL_DELETE",
            "SYSTEM_ACTION", "SECURITY_SENSITIVE", "FINANCIAL"
        }
        self.assertEqual({ac.value for ac in ActionClass}, expected)

    def test_autonomy_profiles(self):
        """All 5 autonomy profiles are defined."""
        expected = {
            "ADVISOR", "SAFE_ASSISTANT", "LOCAL_OPERATOR",
            "TRUSTED_OPERATOR", "WORKFLOW_AUTHORIZED"
        }
        self.assertEqual({ap.value for ap in AutonomyProfile}, expected)

    def test_error_codes_include_unknown_commit(self):
        """Canonical error codes include UNKNOWN_COMMIT, NETWORK_ERROR, and CONFIRMATION_REJECTED."""
        codes = {ec.value for ec in ErrorCode}
        self.assertIn("UNKNOWN_COMMIT", codes)
        self.assertIn("NETWORK_ERROR", codes)
        self.assertIn("CONFIRMATION_REJECTED", codes)
        self.assertIn("INVALID_ARGUMENT", codes)
        self.assertIn("PERMISSION_DENIED", codes)
        self.assertIn("TIMEOUT", codes)

    def test_verification_statuses(self):
        """Three-state verification status enum contains required outcomes."""
        expected = {"VERIFIED_SUCCESS", "VERIFIED_FAILURE", "UNVERIFIED"}
        self.assertEqual({vs.value for vs in VerificationStatus}, expected)

    def test_decision_signals_include_reversibility(self):
        """Invariant 7: DecisionSignalType explicitly includes REVERSIBILITY."""
        types = {dst.value for dst in DecisionSignalType}
        self.assertIn("REVERSIBILITY", types)
        self.assertIn("INTENT", types)
        self.assertIn("RISK", types)
        self.assertIn("URGENCY", types)


class TestL2DecisionContracts(unittest.TestCase):
    def test_valid_decision_signal(self):
        """Valid signal constructs cleanly and serializes to dict."""
        sig = DecisionSignal(
            signal_type=DecisionSignalType.URGENCY,
            value="HIGH",
            confidence=0.92,
            probabilities={"LOW": 0.03, "MEDIUM": 0.05, "HIGH": 0.92},
            latency_ms=1.4
        )
        self.assertEqual(sig.confidence, 0.92)
        self.assertEqual(sig.value, "HIGH")

    def test_confidence_bounds_enforced(self):
        """Confidence outside [0.0, 1.0] raises ValidationError."""
        # Below zero
        with self.assertRaises(ValidationError):
            DecisionSignal(signal_type=DecisionSignalType.RISK, value="LOW", confidence=-0.01)

        # Above one
        with self.assertRaises(ValidationError):
            DecisionSignal(signal_type=DecisionSignalType.RISK, value="LOW", confidence=1.01)

        # NaN
        with self.assertRaises(ValidationError):
            DecisionSignal(signal_type=DecisionSignalType.RISK, value="LOW", confidence=float("nan"))

        # Inf
        with self.assertRaises(ValidationError):
            DecisionSignal(signal_type=DecisionSignalType.RISK, value="LOW", confidence=float("inf"))

    def test_confidence_assignment_validation(self):
        """Assignment to confidence is re-validated automatically."""
        sig = DecisionSignal(signal_type=DecisionSignalType.RISK, value="LOW", confidence=0.5)
        with self.assertRaises(ValidationError):
            sig.confidence = 2.0

    def test_probability_distribution_validation(self):
        """Invalid probability values raise ValidationError."""
        with self.assertRaises(ValidationError):
            DecisionSignal(
                signal_type=DecisionSignalType.RISK,
                value="LOW",
                confidence=0.5,
                probabilities={"LOW": 1.2, "HIGH": -0.2}
            )

    def test_decision_frame_complete(self):
        """DecisionFrame contains all required signals including reversibility."""
        def make_sig(sig_type, val):
            return DecisionSignal(signal_type=sig_type, value=val, confidence=0.95, latency_ms=1.0)

        frame = DecisionFrame(
            request_id="req-123",
            timestamp=1727050000.0,
            intent=make_sig(DecisionSignalType.INTENT, "system_health_check"),
            task_class=make_sig(DecisionSignalType.TASK_CLASS, "diagnostic"),
            urgency=make_sig(DecisionSignalType.URGENCY, "normal"),
            importance=make_sig(DecisionSignalType.IMPORTANCE, "high"),
            risk=make_sig(DecisionSignalType.RISK, "low"),
            reversibility=make_sig(DecisionSignalType.REVERSIBILITY, "reversible"),
            ambiguity=make_sig(DecisionSignalType.AMBIGUITY, "unambiguous"),
            needs_plan=make_sig(DecisionSignalType.NEEDS_PLAN, False),
            needs_tools=make_sig(DecisionSignalType.NEEDS_TOOLS, True),
            model_tier=make_sig(DecisionSignalType.MODEL_TIER, "system1"),
            candidate_domains=["os", "dev"],
            candidate_skills=["system_triage"],
            total_latency_ms=12.5,
            provider_id="laya-modernbert-large"
        )
        self.assertEqual(frame.request_id, "req-123")
        self.assertEqual(frame.reversibility.value, "reversible")
        self.assertEqual(frame.total_latency_ms, 12.5)

    def test_extra_fields_forbidden(self):
        """Injecting extra undeclared keys raises ValidationError."""
        with self.assertRaises(ValidationError):
            DecisionSignal(
                signal_type=DecisionSignalType.INTENT,
                value="query",
                confidence=0.9,
                spurious_unknown_key="disallowed"
            )


class TestL2CapabilityContracts(unittest.TestCase):
    def setUp(self):
        self.valid_spec = CapabilitySpec(
            id="os.system_diagnostics",
            version="1.0.0",
            name="System Diagnostics",
            domain="os",
            description="Inspects CPU, RAM, and Disk metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "detailed": {"type": "boolean", "default": False}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "cpu_percent": {"type": "number"},
                    "memory_percent": {"type": "number"}
                }
            },
            action_class=ActionClass.READ_ONLY,
            autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
            side_effects=False,
            requires_confirmation=False,
            idempotent=True,
            retryable=True,
            timeout_seconds=5.0,
            verification_strategy="deterministic"
        )

    def test_spec_json_roundtrip(self):
        """CapabilitySpec serializes and deserializes from JSON without loss."""
        json_str = self.valid_spec.model_dump_json()
        reconstructed = CapabilitySpec.model_validate_json(json_str)
        self.assertEqual(self.valid_spec, reconstructed)

    def test_executable_capability_runtime_binding(self):
        """ExecutableCapability pairs spec with callables and checks availability."""
        called = []
        def dummy_impl(detailed=False):
            called.append(detailed)
            return {"cpu_percent": 12.5}

        cap = ExecutableCapability(
            spec=self.valid_spec,
            implementation=dummy_impl,
            availability_check=lambda: True
        )
        self.assertTrue(cap.is_available())
        res = cap.implementation(detailed=True)
        self.assertEqual(res, {"cpu_percent": 12.5})
        self.assertEqual(called, [True])

    def test_tool_result_success_consistency(self):
        """ToolResult with success=True requires error=None."""
        receipt = ExecutionReceipt(
            receipt_id="rcpt-1",
            operation_id="op-1",
            capability_id="os.system_diagnostics",
            started_at=100.0,
            finished_at=100.05,
            duration_ms=50.0,
            exit_code=0
        )
        verification = VerificationResult(
            status=VerificationStatus.VERIFIED_SUCCESS,
            strategy="deterministic",
            evidence={"metrics_present": True},
            verified_at=100.06
        )

        # Valid success
        result = ToolResult(
            capability_id="os.system_diagnostics",
            success=True,
            data={"cpu_percent": 15.2},
            receipt=receipt,
            verification=verification
        )
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(result.data["cpu_percent"], 15.2)

        # Inconsistent success with error populated -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="os.system_diagnostics",
                success=True,
                data={"cpu_percent": 15.2},
                error=ToolError(code=ErrorCode.TIMEOUT, message="Timeout occurred")
            )

    def test_tool_result_failure_consistency(self):
        """ToolResult with success=False requires error populated and data=None."""
        err = ToolError(
            code=ErrorCode.UNKNOWN_COMMIT,
            message="Database mutation unconfirmed due to socket drop",
            retryable=False,
            fix_action="Execute manual inspection via dev.sqlite_query"
        )

        # Valid failure
        result = ToolResult(
            capability_id="db.transact",
            success=False,
            error=err
        )
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error.code, ErrorCode.UNKNOWN_COMMIT)
        self.assertEqual(result.error.fix_action, "Execute manual inspection via dev.sqlite_query")

        # Inconsistent failure with no error -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="db.transact",
                success=False,
                error=None
            )

        # Inconsistent failure with data populated -> must fail
        with self.assertRaises(ValidationError):
            ToolResult(
                capability_id="db.transact",
                success=False,
                data={"some": "payload"},
                error=err
            )


class TestL2AgentContracts(unittest.TestCase):
    def test_agent_request_roundtrip(self):
        """AgentRequest serializes to JSON and deserializes cleanly."""
        trace = TraceContext(trace_id="tr-001", session_id="sess-abc")
        req = AgentRequest(
            request_id="req-999",
            user_prompt="Run full disk and memory diagnostics",
            context={"workspace": "C:\\Workspace"},
            trace_context=trace,
            created_at=1727051000.0
        )
        dumped = req.model_dump_json()
        loaded = AgentRequest.model_validate_json(dumped)
        self.assertEqual(req, loaded)

    def test_agent_response_with_receipts(self):
        """AgentResponse bundles execution receipts and physical verifications."""
        receipt = ExecutionReceipt(
            receipt_id="rcpt-2",
            operation_id="op-2",
            capability_id="os.disk_free",
            started_at=200.0,
            finished_at=200.02,
            duration_ms=20.0
        )
        verification = VerificationResult(
            status=VerificationStatus.VERIFIED_SUCCESS,
            strategy="deterministic",
            evidence={"free_bytes": 102400000},
            verified_at=200.03
        )

        resp = AgentResponse(
            request_id="req-999",
            content="Disk free space: 102.4 MB available.",
            executed_tools=["os.disk_free"],
            receipts=[receipt],
            verifications=[verification],
            total_duration_ms=45.2,
            completed_at=200.05
        )
        self.assertEqual(len(resp.receipts), 1)
        self.assertEqual(resp.verifications[0].status, VerificationStatus.VERIFIED_SUCCESS)

    def test_agent_event(self):
        """AgentEvent records domain telemetry cleanly."""
        event = AgentEvent(
            event_id="evt-42",
            event_type="quest.step.completed",
            payload={"step_id": "step-1", "outcome": "SUCCESS"},
            timestamp=1727052000.0
        )
        self.assertEqual(event.event_type, "quest.step.completed")


if __name__ == "__main__":
    unittest.main()
