"""
Capability & Tool Execution Contracts
=====================================
Structures defining:
- JSON-serializable CapabilitySpec metadata contract with explicit policy semantics
  (ConfirmationPolicy, RetryPolicy, IdempotencyClass, minimum_autonomy_profile)
- Standardized ToolResult envelope supporting full ToolOutcome semantics
  (SUCCESS, PARTIAL, FAILURE) and physical VerificationResult
- Structured ToolError with canonical ErrorCode and remediation guidance
- Physical ExecutionReceipt
- CapabilityInvocation structured execution boundary
- ExecutableCapability runtime binding
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import Field, model_validator

from .base import BaseContractModel
from .enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
    ToolOutcome,
    VerificationStatus,
)
from .trace import TraceContext


class CapabilitySpec(BaseContractModel):
    """Pure, JSON-serializable capability specification (separated from runtime callables)."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for CapabilitySpec"
    )
    id: str = Field(..., description="Unique canonical capability identifier, e.g. 'os.system_diagnostics'")
    version: str = Field(default="1.0.0", description="Semantic version of capability implementation")
    name: str = Field(..., description="Human-readable capability name")
    domain: str = Field(..., description="Capability domain: web, browser, os, dev, data")
    description: str = Field(..., description="Clear description used for routing and documentation")
    input_schema: Dict[str, Any] = Field(
        ...,
        description="JSON Schema defining required and optional invocation arguments"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema defining the output structure"
    )
    action_class: ActionClass = Field(
        default=ActionClass.READ_ONLY,
        description="Safety and blast radius classification"
    )
    minimum_autonomy_profile: AutonomyProfile = Field(
        default=AutonomyProfile.SAFE_ASSISTANT,
        description="Minimum autonomy profile required to execute without interactive human prompt"
    )
    confirmation_policy: ConfirmationPolicy = Field(
        default=ConfirmationPolicy.POLICY_CONTROLLED,
        description="Confirmation requirement policy: NEVER, POLICY_CONTROLLED, or ALWAYS"
    )
    retry_policy: RetryPolicy = Field(
        default=RetryPolicy.NEVER,
        description="Retry policy: NEVER, SAFE_READ_RETRY, SAFE_WITH_IDEMPOTENCY, or VERIFY_BEFORE_RETRY"
    )
    idempotency_class: IdempotencyClass = Field(
        default=IdempotencyClass.READ_ONLY,
        description="Idempotency classification: READ_ONLY, NATURAL, LEDGER_REQUIRED, etc."
    )
    side_effects: bool = Field(default=False, description="Whether capability alters external state")
    timeout_seconds: float = Field(default=15.0, gt=0.0, description="Execution timeout budget in seconds")
    verification_strategy: str = Field(
        default="deterministic",
        description="Strategy for verifying outcome: deterministic, semantic, file_exists, exit_code, or manual"
    )

    @model_validator(mode="before")
    @classmethod
    def translate_legacy_fields(cls, data: Any) -> Any:
        """Translates legacy boolean and profile fields into explicit policy enums."""
        if isinstance(data, dict):
            data = dict(data)
            if "autonomy_profile" in data and "minimum_autonomy_profile" not in data:
                data["minimum_autonomy_profile"] = data.pop("autonomy_profile")
            if "requires_confirmation" in data and "confirmation_policy" not in data:
                req = data.pop("requires_confirmation")
                data["confirmation_policy"] = ConfirmationPolicy.ALWAYS if req else ConfirmationPolicy.POLICY_CONTROLLED
            if "retryable" in data and "retry_policy" not in data:
                ret = data.pop("retryable")
                data["retry_policy"] = RetryPolicy.SAFE_READ_RETRY if ret else RetryPolicy.NEVER
            if "idempotent" in data and "idempotency_class" not in data:
                idem = data.pop("idempotent")
                data["idempotency_class"] = IdempotencyClass.NATURAL if idem else IdempotencyClass.NON_IDEMPOTENT
        return data

    # Backward-compatible property facades
    @property
    def autonomy_profile(self) -> AutonomyProfile:
        return self.minimum_autonomy_profile

    @property
    def requires_confirmation(self) -> bool:
        return self.confirmation_policy == ConfirmationPolicy.ALWAYS

    @property
    def retryable(self) -> bool:
        return self.retry_policy != RetryPolicy.NEVER

    @property
    def idempotent(self) -> bool:
        return self.idempotency_class in (
            IdempotencyClass.READ_ONLY,
            IdempotencyClass.NATURAL,
            IdempotencyClass.REMOTE_IDEMPOTENCY_KEY,
        )


class CapabilityInvocation(BaseContractModel):
    """Structured boundary context for invoking a capability."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for CapabilityInvocation"
    )
    invocation_id: str = Field(..., description="Unique invocation identifier")
    capability_id: str = Field(..., description="Target capability identifier to execute")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured arguments conforming to capability input_schema"
    )
    trace_context: Optional[TraceContext] = Field(
        default=None,
        description="Correlation and distributed tracing context"
    )
    attempt: int = Field(default=1, ge=1, description="Invocation attempt sequence number")
    deadline_seconds: Optional[float] = Field(
        default=None,
        gt=0.0,
        description="Maximum execution time budget in seconds"
    )
    current_autonomy_profile: Optional[AutonomyProfile] = Field(
        default=None,
        description="Active autonomy profile governing this invocation"
    )
    quest_id: Optional[str] = Field(default=None, description="Enclosing Quest identifier if applicable")
    plan_id: Optional[str] = Field(default=None, description="Enclosing DAG plan identifier if applicable")
    step_id: Optional[str] = Field(default=None, description="Enclosing plan step identifier if applicable")
    operation_id: Optional[str] = Field(default=None, description="Persistent mutation operation identity")
    idempotency_key: Optional[str] = Field(
        default=None,
        description="External/network idempotency key for exactly-once execution"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental invocation metadata"
    )


class ToolError(BaseContractModel):
    """Structured error envelope representing a routine tool failure."""
    code: ErrorCode = Field(..., description="Canonical error code")
    message: str = Field(..., description="Human-readable explanation of failure")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Technical context, stdout/stderr, or argument details"
    )
    retryable: bool = Field(
        default=False,
        description="Whether a retry with identical arguments could succeed"
    )
    fix_action: Optional[str] = Field(
        default=None,
        description="Suggested remediation action or alternative capability"
    )


class ExecutionReceipt(BaseContractModel):
    """Physical audit record of a single capability execution."""
    receipt_id: str = Field(..., description="Unique receipt identifier")
    operation_id: str = Field(..., description="Logical mutation / step operation identifier")
    capability_id: str = Field(..., description="Capability that was executed")
    started_at: float = Field(..., description="Epoch timestamp execution began")
    finished_at: float = Field(..., description="Epoch timestamp execution ended")
    duration_ms: float = Field(..., ge=0.0, description="Duration in milliseconds")
    exit_code: Optional[int] = Field(default=None, description="Subprocess exit code if applicable")
    bytes_read: Optional[int] = Field(default=None, ge=0, description="Number of bytes read from external resource")
    bytes_written: Optional[int] = Field(default=None, ge=0, description="Number of bytes written to external resource")
    raw_output_ref: Optional[str] = Field(default=None, description="Reference or URI to raw artifact output")


class VerificationResult(BaseContractModel):
    """Physical outcome verification record confirming real-world state change."""
    status: VerificationStatus = Field(..., description="Physical outcome verification status")
    strategy: str = Field(..., description="Strategy employed (e.g. 'file_exists', 'exit_code')")
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Physical state evidence (e.g. {'file_size': 1024, 'exists': True})"
    )
    notes: Optional[str] = Field(default=None, description="Verification notes or discrepancy details")
    verified_at: float = Field(..., description="Epoch timestamp verification occurred")


class ToolResult(BaseContractModel):
    """Canonical, strongly typed envelope returned by all capability executions."""
    schema_version: str = Field(
        default="1.0.0",
        description="Contract schema version for ToolResult"
    )
    capability_id: str = Field(..., description="Identifier of capability executed")
    outcome: ToolOutcome = Field(
        default=ToolOutcome.SUCCESS,
        description="Execution outcome: SUCCESS, PARTIAL, or FAILURE"
    )
    success: bool = Field(
        ...,
        description="True strictly if outcome == ToolOutcome.SUCCESS; False for PARTIAL or FAILURE"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured data payload on success or partial completion"
    )
    error: Optional[ToolError] = Field(
        default=None,
        description="Structured error on failure or partial completion; must be None on full success"
    )
    observations: List[str] = Field(
        default_factory=list,
        description="Ordered trace of steps observed during execution"
    )
    receipt: Optional[ExecutionReceipt] = Field(
        default=None,
        description="Physical execution receipt"
    )
    verification: Optional[VerificationResult] = Field(
        default=None,
        description="Outcome verification record (physically proven state)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context or provider telemetry"
    )

    @model_validator(mode="before")
    @classmethod
    def synchronize_outcome_and_success(cls, data: Any) -> Any:
        """Infers outcome from success or success from outcome when one is omitted."""
        if isinstance(data, dict):
            data = dict(data)
            if "success" in data and "outcome" not in data:
                data["outcome"] = ToolOutcome.SUCCESS if data["success"] else ToolOutcome.FAILURE
            elif "outcome" in data and "success" not in data:
                outcome_val = data["outcome"]
                if isinstance(outcome_val, ToolOutcome):
                    outcome_val = outcome_val.value
                data["success"] = (outcome_val == "SUCCESS")
        return data

    @model_validator(mode="after")
    def validate_outcome_state_consistency(self) -> "ToolResult":
        """Enforces rigorous consistency between outcome, success flag, data, and error."""
        if self.outcome == ToolOutcome.SUCCESS:
            if not self.success:
                raise ValueError("ToolResult with outcome=SUCCESS must have success=True.")
            if self.error is not None:
                raise ValueError("ToolResult with outcome=SUCCESS must not have an error populated.")
        elif self.outcome == ToolOutcome.FAILURE:
            if self.success:
                raise ValueError("ToolResult with outcome=FAILURE must have success=False.")
            if self.error is None:
                raise ValueError("ToolResult with outcome=FAILURE must have an error populated.")
            if self.data is not None:
                raise ValueError("ToolResult with outcome=FAILURE must have data=None.")
        elif self.outcome == ToolOutcome.PARTIAL:
            if self.success:
                raise ValueError("ToolResult with outcome=PARTIAL must have success=False (not 100% successful).")
            if self.data is None and self.error is None:
                raise ValueError("ToolResult with outcome=PARTIAL must provide data or error details.")
        return self


class ExecutableCapability:
    """Runtime binding pairing a serializable CapabilitySpec with executable Python callables."""
    def __init__(
        self,
        spec: CapabilitySpec,
        implementation: Callable[..., Any],
        verifier: Optional[Callable[[Dict[str, Any], ToolResult], bool]] = None,
        availability_check: Optional[Callable[[], bool]] = None,
    ):
        self.spec = spec
        self.implementation = implementation
        self.verifier = verifier
        self.availability_check = availability_check

    def is_available(self) -> bool:
        """Returns True if capability prerequisites are satisfied on this host."""
        if self.availability_check is None:
            return True
        try:
            return bool(self.availability_check())
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"<ExecutableCapability {self.spec.id} v{self.spec.version}>"
