"""Strongly Typed Replanning & Recovery Contracts for LAYA Autonomous V2 Runtime.

Defines triggers, scopes, requests, and results for Controlled Replanning (Checkpoint L16).
Enforces Invariant 1 (Deterministic Control) and Invariant 4 (Strongly Typed Contracts).
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from .base import BaseContractModel
from .plan import Plan


class ReplanTrigger(str, Enum):
    """Reason why replanning was initiated."""
    STEP_FAILURE = "step_failure"
    TIMEOUT = "timeout"
    PRECONDITION_FAILED = "precondition_failed"
    VERIFICATION_FAILED = "verification_failed"
    POLICY_REJECTION = "policy_rejection"


class ReplanScope(str, Enum):
    """Scope of plan revision."""
    STEP_RETRY_WITH_VARIATION = "step_retry_with_variation"
    SUB_DAG_REPLACE = "sub_dag_replace"
    FULL_REPLAN = "full_replan"


class ReplanRequest(BaseContractModel):
    """Strongly typed input specification for initiating a controlled replan."""
    quest_id: str = Field(..., description="Target Quest ID")
    failed_step_id: str = Field(..., description="Step ID where the failure occurred")
    trigger: ReplanTrigger = Field(..., description="Reason for triggering replanning")
    error_message: str = Field(..., description="Description of the failure or error encountered")
    replan_attempt: int = Field(
        default=1,
        ge=1,
        description="Current replan attempt count for this quest"
    )
    max_replans: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum permitted replans before halting as failed"
    )
    preserved_step_ids: List[str] = Field(
        default_factory=list,
        description="Steps that succeeded and must be preserved with their outputs"
    )
    pruned_step_ids: List[str] = Field(
        default_factory=list,
        description="Steps within the blast radius that are being replaced or pruned"
    )
    previous_failures: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of previous failures in this quest to prevent oscillation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for replanning"
    )

    @field_validator("quest_id", "failed_step_id", "error_message")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class ReplanResult(BaseContractModel):
    """Strongly typed output specification produced by the Controlled Replanner."""
    replan_id: str = Field(
        default_factory=lambda: f"replan_{uuid.uuid4().hex[:12]}",
        description="Unique identifier for this replan operation"
    )
    quest_id: str = Field(..., description="Target Quest ID")
    success: bool = Field(..., description="Whether a valid revised plan was synthesized")
    revised_plan: Optional[Plan] = Field(
        default=None,
        description="Validated replacement Plan, if success=True"
    )
    scope: ReplanScope = Field(
        default=ReplanScope.SUB_DAG_REPLACE,
        description="Scope of the revision performed"
    )
    blast_radius_step_ids: List[str] = Field(
        default_factory=list,
        description="Step IDs identified as belonging to the failure blast radius"
    )
    preserved_step_ids: List[str] = Field(
        default_factory=list,
        description="Step IDs preserved from the prior plan version"
    )
    added_step_ids: List[str] = Field(
        default_factory=list,
        description="Newly introduced step IDs in the revised plan"
    )
    replan_version: int = Field(
        default=1,
        ge=1,
        description="Resulting replan version number"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error explanation if replanning failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry, strategy notes, or diagnostic information"
    )
    created_at: float = Field(default_factory=time.time)

    @field_validator("quest_id")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()
