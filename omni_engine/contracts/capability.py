"""
Capability & Tool Execution Contracts
=====================================
Structures defining:
- JSON-serializable CapabilitySpec metadata contract
- Standardized ToolResult envelope with strict success/error exclusivity
- Structured ToolError with canonical ErrorCode and remediation guidance
- Physical ExecutionReceipt and VerificationResult
- ExecutableCapability runtime binding
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import Field, model_validator

from .base import BaseContractModel
from .enums import ActionClass, AutonomyProfile, ErrorCode, VerificationStatus


class CapabilitySpec(BaseContractModel):
    """Pure, JSON-serializable capability specification (separated from runtime callables)."""
    id: str = Field(..., description="Unique capability identifier, e.g. 'os.system_diagnostics'")
    version: str = Field(default="1.0.0", description="Semantic capability contract version")
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
    autonomy_profile: AutonomyProfile = Field(
        default=AutonomyProfile.SAFE_ASSISTANT,
        description="Minimum autonomy profile required to execute without prompt"
    )
    side_effects: bool = Field(default=False, description="Whether capability alters external state")
    requires_confirmation: bool = Field(default=False, description="Whether policy mandates manual confirmation")
    idempotent: bool = Field(default=True, description="Whether repeated identical executions are safe")
    retryable: bool = Field(default=False, description="Whether transient failures can be safely retried")
    timeout_seconds: float = Field(default=15.0, gt=0.0, description="Execution timeout budget in seconds")
    verification_strategy: str = Field(
        default="deterministic",
        description="Strategy for verifying outcome: deterministic, semantic, file_exists, exit_code, or manual"
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
    status: VerificationStatus = Field(..., description="Outcome verification status")
    strategy: str = Field(..., description="Strategy employed (e.g. 'file_exists', 'exit_code')")
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Physical state evidence (e.g. {'file_size': 1024, 'exists': True})"
    )
    notes: Optional[str] = Field(default=None, description="Verification notes or discrepancy details")
    verified_at: float = Field(..., description="Epoch timestamp verification occurred")


class ToolResult(BaseContractModel):
    """Canonical, strongly typed envelope returned by all capability executions."""
    capability_id: str = Field(..., description="Identifier of capability executed")
    success: bool = Field(..., description="True if operation completed successfully and produced valid data")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Structured data payload on success; must be None on failure"
    )
    error: Optional[ToolError] = Field(
        default=None,
        description="Structured error on failure; must be None on success"
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
        description="Outcome verification record"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context or provider telemetry"
    )

    @model_validator(mode="after")
    def validate_success_error_exclusivity(self) -> "ToolResult":
        """Enforces mutual exclusivity between success and error state."""
        if self.success:
            if self.error is not None:
                raise ValueError("ToolResult with success=True must not have an error populated.")
        else:
            if self.error is None:
                raise ValueError("ToolResult with success=False must have an error populated.")
            if self.data is not None:
                raise ValueError("ToolResult with success=False must have data=None.")
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
