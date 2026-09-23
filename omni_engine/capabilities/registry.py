"""
omni_engine.capabilities.registry
=================================
Canonical, thread-safe capability registry for the standalone LAYA Omni Agent.

Invariants:
- Exactly one canonical ID per capability; duplicates rejected.
- Pure Pydantic CapabilitySpec strictly segregated from runtime callables.
- Thread-safe access with fine-grained lock scoping (never hold lock during tool execution).
- Robust exception normalization: routine operational exceptions become structured ToolError envelopes.
- BaseException (KeyboardInterrupt, SystemExit) is NEVER swallowed.
- Automatic ExecutionReceipt telemetry generated on every execution.
"""

import inspect
import socket
import subprocess
import threading
import time
import urllib.error
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import ValidationError

from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
    ToolOutcome,
    VerificationStatus,
)
from omni_engine.contracts.capability import (
    CapabilityInvocation,
    CapabilitySpec,
    ExecutableCapability,
    ExecutionReceipt,
    ToolError,
    ToolResult,
    VerificationResult,
)


class CapabilityRegistry:
    """Canonical registry managing capability specifications, runtime executables, and safe dispatch."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._capabilities: Dict[str, ExecutableCapability] = {}

    def register(
        self,
        spec: CapabilitySpec,
        implementation: Callable[..., Any],
        verifier: Optional[Callable[[Dict[str, Any], ToolResult], bool]] = None,
        availability_check: Optional[Callable[[], bool]] = None,
    ) -> None:
        """Registers a canonical capability.
        
        Raises:
            ValueError: If a capability with the same ID is already registered or implementation is async.
        """
        if inspect.iscoroutinefunction(implementation):
            raise ValueError(
                f"Capability '{spec.id}' implementation must be synchronous; async coroutines are not supported directly."
            )

        with self._lock:
            if spec.id in self._capabilities:
                raise ValueError(
                    f"Capability '{spec.id}' is already registered in CapabilityRegistry. Duplicate IDs are forbidden."
                )

            exec_cap = ExecutableCapability(
                spec=spec,
                implementation=implementation,
                verifier=verifier,
                availability_check=availability_check,
            )
            self._capabilities[spec.id] = exec_cap

    def unregister(self, capability_id: str) -> bool:
        """Removes a capability from the registry. Returns True if removed."""
        with self._lock:
            return bool(self._capabilities.pop(capability_id, None))

    def has(self, capability_id: str) -> bool:
        """Returns True if capability is registered."""
        with self._lock:
            return capability_id in self._capabilities

    def get(self, capability_id: str) -> Optional[ExecutableCapability]:
        """Retrieves runtime executable capability binding by ID."""
        with self._lock:
            return self._capabilities.get(capability_id)

    def get_spec(self, capability_id: str) -> Optional[CapabilitySpec]:
        """Retrieves pure serializable CapabilitySpec by ID."""
        with self._lock:
            cap = self._capabilities.get(capability_id)
            return cap.spec if cap else None

    def list_all(self) -> List[str]:
        """Returns sorted list of all registered capability IDs."""
        with self._lock:
            return sorted(list(self._capabilities.keys()))

    def list_specs(self, domain: Optional[str] = None) -> List[CapabilitySpec]:
        """Returns shallow copy of CapabilitySpecs, optionally filtered by domain."""
        with self._lock:
            if domain:
                return [c.spec for c in self._capabilities.values() if c.spec.domain == domain]
            return [c.spec for c in self._capabilities.values()]

    def list_by_domain(self, domain: str) -> List[str]:
        """Returns capability IDs belonging to the specified domain."""
        with self._lock:
            return sorted([c.spec.id for c in self._capabilities.values() if c.spec.domain == domain])

    def list_by_action_class(self, action_class: ActionClass) -> List[str]:
        """Returns capability IDs belonging to the specified action class."""
        with self._lock:
            return sorted([c.spec.id for c in self._capabilities.values() if c.spec.action_class == action_class])

    def export_specs(self) -> List[Dict[str, Any]]:
        """Exports all capability specifications as JSON-safe dictionaries."""
        with self._lock:
            return [c.spec.model_dump() for c in self._capabilities.values()]

    def count(self) -> int:
        """Returns total count of registered capabilities."""
        with self._lock:
            return len(self._capabilities)

    # -----------------------------------------------------------------------
    # Structured Invocation Dispatch Boundary
    # -----------------------------------------------------------------------

    def invoke(self, invocation: CapabilityInvocation) -> ToolResult:
        """Executes a capability through its structured boundary contract.
        
        Guarantees:
        - Lock is NOT held during tool execution.
        - Process-control exceptions (KeyboardInterrupt, SystemExit) are re-raised.
        - Routine operational exceptions are translated to structured ToolError envelopes.
        - ExecutionReceipt is automatically populated.
        """
        cap_id = invocation.capability_id
        op_id = invocation.operation_id or f"op_{uuid.uuid4().hex[:8]}"

        # Step 1: Retrieve executable under lock
        with self._lock:
            exec_cap = self._capabilities.get(cap_id)

        if exec_cap is None:
            return ToolResult(
                capability_id=cap_id,
                outcome=ToolOutcome.FAILURE,
                success=False,
                error=ToolError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Capability '{cap_id}' is not registered in CapabilityRegistry.",
                    details={"requested_id": cap_id},
                    retryable=False,
                    fix_action=f"Verify capability ID against registered capabilities: {self.list_all()}",
                ),
            )

        # Step 2: Check environment availability
        if not exec_cap.is_available():
            return ToolResult(
                capability_id=cap_id,
                outcome=ToolOutcome.FAILURE,
                success=False,
                error=ToolError(
                    code=ErrorCode.UNCONFIGURED,
                    message=f"Capability '{cap_id}' prerequisites are not satisfied on this host.",
                    details={"capability_id": cap_id},
                    retryable=False,
                    fix_action="Check required environment variables, system packages, or configuration.",
                ),
            )

        # Step 3: Execute implementation OUTSIDE lock
        t0_perf = time.perf_counter()
        t0_epoch = time.time()
        exit_code: Optional[int] = None
        bytes_written: Optional[int] = None

        try:
            raw_res = exec_cap.implementation(**invocation.arguments)

            # Check if implementation returned an adapted (success: bool, data_or_err) tuple
            if isinstance(raw_res, tuple) and len(raw_res) == 2 and isinstance(raw_res[0], bool):
                success, data_or_err = raw_res
                if success:
                    outcome = ToolOutcome.SUCCESS
                    data = data_or_err if isinstance(data_or_err, dict) else {"output": data_or_err}
                    error = None
                    if "bytes_written" in data:
                        bytes_written = data.get("bytes_written")
                else:
                    outcome = ToolOutcome.FAILURE
                    data = None
                    if isinstance(data_or_err, ToolError):
                        error = data_or_err
                    else:
                        error = ToolError(
                            code=ErrorCode.INTERNAL_ERROR,
                            message=str(data_or_err),
                            details={"raw_output": str(data_or_err)},
                        )
            elif isinstance(raw_res, ToolResult):
                outcome = raw_res.outcome
                data = raw_res.data
                error = raw_res.error
                if raw_res.receipt is not None:
                    receipt = raw_res.receipt
            else:
                outcome = ToolOutcome.SUCCESS
                data = {"output": raw_res}
                error = None

        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            # PRIME DIRECTIVE: Never swallow process-control exceptions
            raise

        except FileNotFoundError as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.NOT_FOUND,
                message=str(e) or "Target file or resource not found.",
                details={"exception": type(e).__name__},
                retryable=False,
                fix_action="Check directory tree or target resource path.",
            )

        except (PermissionError, ) as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.PERMISSION_DENIED,
                message=str(e) or "OS or filesystem permission denied.",
                details={"exception": type(e).__name__},
                retryable=False,
                fix_action="Adjust OS file permissions or run with required privilege.",
            )

        except (TimeoutError, subprocess.TimeoutExpired, socket.timeout) as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.TIMEOUT,
                message=f"Capability execution timed out: {e}",
                details={"exception": type(e).__name__},
                retryable=True,
                fix_action="Retry with higher timeout budget or inspect network/service latency.",
            )

        except (urllib.error.URLError, ConnectionError) as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.NETWORK_ERROR,
                message=f"Network error during execution: {e}",
                details={"exception": type(e).__name__},
                retryable=True,
                fix_action="Check host internet connection or remote service availability.",
            )

        except subprocess.CalledProcessError as e:
            outcome = ToolOutcome.FAILURE
            data = None
            exit_code = e.returncode
            error = ToolError(
                code=ErrorCode.PROCESS_FAILED,
                message=f"Subprocess failed with exit code {e.returncode}: {e.stderr or e.output or str(e)}",
                details={"exit_code": e.returncode, "stdout": e.stdout, "stderr": e.stderr},
                retryable=False,
                fix_action="Inspect subprocess parameters and command syntax.",
            )

        except ValidationError as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Arguments or result schema violation: {e}",
                details={"errors": e.errors()},
                retryable=False,
                fix_action="Ensure arguments conform strictly to capability input_schema.",
            )

        except (ValueError, TypeError) as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.INVALID_ARGUMENT,
                message=f"Invalid arguments provided: {e}",
                details={"exception": type(e).__name__},
                retryable=False,
                fix_action="Verify argument types and bounds against schema.",
            )

        except Exception as e:
            outcome = ToolOutcome.FAILURE
            data = None
            error = ToolError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Unhandled capability execution exception: {e}",
                details={"exception": type(e).__name__, "error_str": str(e)},
                retryable=False,
                fix_action="Inspect runtime engine logs for unhandled defect.",
            )

        t1_perf = time.perf_counter()
        t1_epoch = time.time()
        duration_ms = round((t1_perf - t0_perf) * 1000, 3)

        receipt = ExecutionReceipt(
            receipt_id=f"rcpt_{uuid.uuid4().hex[:12]}",
            operation_id=op_id,
            capability_id=cap_id,
            started_at=t0_epoch,
            finished_at=t1_epoch,
            duration_ms=duration_ms,
            exit_code=exit_code,
            bytes_written=bytes_written,
        )

        # Verification step if verifier defined and outcome is SUCCESS
        verification: Optional[VerificationResult] = None
        if exec_cap.verifier is not None and outcome == ToolOutcome.SUCCESS:
            try:
                temp_res = ToolResult(
                    capability_id=cap_id,
                    outcome=outcome,
                    success=True,
                    data=data,
                    error=None,
                    receipt=receipt,
                )
                verified = exec_cap.verifier(invocation.arguments, temp_res)
                verification = VerificationResult(
                    status=VerificationStatus.VERIFIED_SUCCESS if verified else VerificationStatus.VERIFIED_FAILURE,
                    strategy="callable_verifier",
                    evidence={"verifier_returned": bool(verified)},
                    verified_at=time.time(),
                )
            except Exception as ve:
                verification = VerificationResult(
                    status=VerificationStatus.UNVERIFIED,
                    strategy="callable_verifier",
                    evidence={"verifier_error": str(ve)},
                    notes=f"Verifier raised exception: {ve}",
                    verified_at=time.time(),
                )

        return ToolResult(
            capability_id=cap_id,
            outcome=outcome,
            success=(outcome == ToolOutcome.SUCCESS),
            data=data,
            error=error,
            receipt=receipt,
            verification=verification,
        )
