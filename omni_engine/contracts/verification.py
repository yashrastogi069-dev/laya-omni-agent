"""
omni_engine.contracts.verification
==================================
Strongly typed contracts for evidence-based completion verification (Checkpoint L15).

Guarantees:
1. Physical Evidence Priority (Invariant 6): Physical outcome checks always outrank
   structured receipts and model prose.
2. Negative Constraint Verification: Constraints ('do not modify workflows') are verified
   against actual operation ledgers and execution logs.
3. Cryptographic Provenance: Every verification receipt contains a canonical evidence_hash
   and verifier_version.
4. Non-decorative, strictly validated models (extra="forbid").
"""

import hashlib
import json
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator, model_validator

from .base import BaseContractModel


class CheckType(str, Enum):
    """Hierarchy tier of a verification check."""
    PHYSICAL = "PHYSICAL"                      # Direct OS/disk/process/network inspection
    STRUCTURED_RECEIPT = "STRUCTURED_RECEIPT"  # Typed tool execution envelope / API receipt
    DERIVED_VALIDATION = "DERIVED_VALIDATION"  # AST parsing, cryptographic signature, citation graph
    SEMANTIC = "SEMANTIC"                      # Bounded structured classification (cannot override physical)


class RequirementVerificationStatus(str, Enum):
    """Outcome status for an individual objective requirement verification."""
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"      # Physical/receipt evidence confirms requirement satisfied
    VERIFIED_FAILURE = "VERIFIED_FAILURE"      # Evidence proves requirement failed or was contradicted
    UNVERIFIED = "UNVERIFIED"                  # Insufficient evidence to declare outcome
    NOT_APPLICABLE = "NOT_APPLICABLE"          # Requirement deemed irrelevant or superseded


class ConstraintVerificationStatus(str, Enum):
    """Outcome status for a negative or operational constraint."""
    SATISFIED = "SATISFIED"                    # Zero violations found in execution/ledger history
    VIOLATED = "VIOLATED"                      # A forbidden action, mutation, or side-effect occurred
    UNCHECKED = "UNCHECKED"                    # Constraint was not evaluated


class VerificationCheckResult(BaseContractModel):
    """Detailed result of an individual verification check."""
    check_name: str = Field(description="Name or identifier of the check, e.g. 'file_exists'")
    check_type: CheckType = Field(description="Hierarchy classification of check")
    passed: bool = Field(description="Whether this specific check passed")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Raw physical or receipt evidence payload")
    details: Optional[str] = Field(default=None, description="Diagnostic explanation or mismatch description")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp when check executed")


class RequirementVerification(BaseContractModel):
    """Verification record for a discrete objective requirement."""
    requirement_id: str = Field(description="Requirement identifier from ObjectiveSpec, e.g. 'R1'")
    description: str = Field(description="Human-readable description of requirement")
    mandatory: bool = Field(default=True, description="Whether this requirement is mandatory for completion")
    status: RequirementVerificationStatus = Field(description="Final verification status for this requirement")
    evidence_refs: List[str] = Field(default_factory=list, description="IDs or paths of evidence (files, PIDs, receipts)")
    verifier_id: str = Field(description="Identifier of verifier that evaluated this requirement")
    verifier_version: str = Field(default="1.0.0", description="Version of the verifier implementation")
    physical_checks: List[VerificationCheckResult] = Field(default_factory=list, description="Physical state check results")
    semantic_checks: List[VerificationCheckResult] = Field(default_factory=list, description="Semantic validation results")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Verification confidence score")
    failure_reason: Optional[str] = Field(default=None, description="Detailed explanation if verification failed")
    repairable: bool = Field(default=False, description="Whether a targeted replan in L16 can repair this requirement")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp verification concluded")

    @model_validator(mode="after")
    def validate_physical_precedence(self) -> "RequirementVerification":
        """Inviolable rule: If any physical check failed, status cannot be VERIFIED_SUCCESS."""
        failed_physical = [c for c in self.physical_checks if not c.passed and c.check_type == CheckType.PHYSICAL]
        if failed_physical and self.status == RequirementVerificationStatus.VERIFIED_SUCCESS:
            raise ValueError(
                f"Physical check '{failed_physical[0].check_name}' failed; "
                f"requirement '{self.requirement_id}' cannot be marked VERIFIED_SUCCESS."
            )
        return self


class ConstraintVerification(BaseContractModel):
    """Verification record for a negative constraint or user boundary."""
    constraint_id: str = Field(description="Unique identifier for constraint, e.g. 'C1'")
    description: str = Field(description="Human-readable description of constraint, e.g. 'Do not modify workflows'")
    status: ConstraintVerificationStatus = Field(description="Constraint compliance status")
    violation_details: Optional[str] = Field(default=None, description="Details of violation if detected")
    checked_operations: List[str] = Field(default_factory=list, description="Operation/step IDs audited")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp constraint checked")


class ObjectiveVerificationResult(BaseContractModel):
    """Aggregate completion verification receipt for a Quest objective."""
    verification_id: str = Field(description="Unique identifier for this verification receipt")
    quest_id: str = Field(description="Target Quest identifier")
    plan_id: str = Field(description="DAG Plan identifier evaluated")
    objective_text: str = Field(description="User objective or goal string")
    requirement_results: List[RequirementVerification] = Field(default_factory=list, description="Per-requirement verification records")
    constraint_results: List[ConstraintVerification] = Field(default_factory=list, description="Constraint audit records")
    verified_complete: bool = Field(description="True strictly if ALL mandatory requirements and constraints are verified")
    verified_partial: bool = Field(default=False, description="True if some requirements verified but gaps remain")
    verified_failure: bool = Field(default=False, description="True if mandatory requirement failed unrecoverably or constraint violated")
    unresolved_requirements: List[str] = Field(default_factory=list, description="Requirement IDs that remain unsatisfied")
    violated_constraints: List[str] = Field(default_factory=list, description="Constraint IDs that were violated")
    evidence_hash: str = Field(description="Canonical SHA-256 digest of all physical evidence and checks")
    verifier_version: str = Field(default="1.0.0", description="Version of the completion engine")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Execution and audit metadata")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp verification concluded")

    @classmethod
    def compute_evidence_hash(
        cls,
        quest_id: str,
        plan_id: str,
        requirement_results: List[RequirementVerification],
        constraint_results: List[ConstraintVerification],
    ) -> str:
        """Computes a canonical SHA-256 evidence fingerprint."""
        components = {
            "quest_id": quest_id,
            "plan_id": plan_id,
            "requirements": [
                {
                    "id": r.requirement_id,
                    "status": r.status.value,
                    "evidence_refs": sorted(r.evidence_refs),
                    "physical_checks": [
                        {"name": c.check_name, "passed": c.passed, "evidence": c.evidence}
                        for c in sorted(r.physical_checks, key=lambda x: x.check_name)
                    ]
                }
                for r in sorted(requirement_results, key=lambda x: x.requirement_id)
            ],
            "constraints": [
                {"id": c.constraint_id, "status": c.status.value, "violation": c.violation_details}
                for c in sorted(constraint_results, key=lambda x: x.constraint_id)
            ]
        }
        raw_json = json.dumps(components, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
