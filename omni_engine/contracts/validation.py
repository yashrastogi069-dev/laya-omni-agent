"""
omni_engine.contracts.validation
================================
Strongly typed contracts for the Checkpoint L13 Deterministic Plan Validator.

Invariants:
- Invariant 1 (Deterministic Control): Verification is 100% deterministic and rule-based.
- Invariant 4 (Strongly Typed Contracts): All schemas use BaseContractModel with extra="forbid".
- Full Diagnostic Accumulation: Reports status for all 10 validation passes.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import ErrorCode


class ValidationPassName(str, Enum):
    """The 10 deterministic validation passes of the Plan Validator Firewall."""
    DAG_ACYCLICITY = "DAG_ACYCLICITY"
    DEPENDENCY_EXISTENCE = "DEPENDENCY_EXISTENCE"
    CAPABILITY_REGISTRATION = "CAPABILITY_REGISTRATION"
    SCHEMA_CONFORMANCE = "SCHEMA_CONFORMANCE"
    POLICY_FEASIBILITY = "POLICY_FEASIBILITY"
    AUTONOMY_COMPLIANCE = "AUTONOMY_COMPLIANCE"
    STEP_COUNT_BOUNDS = "STEP_COUNT_BOUNDS"
    GRAPH_DEPTH_BOUNDS = "GRAPH_DEPTH_BOUNDS"
    MUTATION_SAFETY = "MUTATION_SAFETY"
    RESOURCE_BUDGET = "RESOURCE_BUDGET"


class ValidationPassResult(BaseContractModel):
    """Outcome of an individual validation pass."""
    pass_name: ValidationPassName
    passed: bool
    message: str
    step_id: Optional[str] = None
    error_code: Optional[ErrorCode] = None
    details: Optional[Dict[str, Any]] = None


class PlanValidationReport(BaseContractModel):
    """Cumulative diagnostic report produced by DeterministicPlanValidator."""
    plan_id: str
    is_valid: bool
    passes: List[ValidationPassResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    latency_ms: float = Field(default=0.0, ge=0.0)
    validator_version: str = Field(default="1.0.0", description="Version of the DeterministicPlanValidator")
    validation_hash: Optional[str] = Field(default=None, description="Plan canonical hash verified by validator")
    validation_receipt: Optional[Dict[str, Any]] = Field(default=None, description="Detailed validation receipt")
