"""Structured DAG Plan Contracts for LAYA Autonomous V2 Runtime.

Defines the core data contracts, plan types, step specifications,
and validation envelopes for Structured DAG Planning (Checkpoint L12).
"""

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import Field, field_validator, model_validator

from .base import BaseContractModel


class PlanType(str, Enum):
    """Origin type of an execution plan."""
    TEMPLATE_DERIVED = "template_derived"
    GENERATIVE_SYNTHESIZED = "generative_synthesized"
    COMPOSITE = "composite"


# Domain-specific exceptions
class PlanError(Exception):
    """Base exception for planning operations."""
    pass


class PlanValidationError(PlanError):
    """Raised when a plan violates structural, topological, or capability constraints."""
    pass


class PlanGenerationError(PlanError):
    """Raised when generative plan synthesis fails or returns malformed output."""
    pass


class PlanStep(BaseContractModel):
    """Strongly typed contract for an individual node in a planned execution DAG."""
    step_id: str = Field(..., description="Unique step identifier within the plan (e.g. 'step_1')")
    capability_id: str = Field(..., description="Target capability ID to execute")
    intent: str = Field(..., description="Semantic explanation of what this step achieves")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resolved arguments adhering to capability schema"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Step IDs that must complete before this step can execute"
    )
    timeout_s: float = Field(
        default=60.0,
        ge=0.01,
        le=3600.0,
        description="Timeout budget in seconds for this step"
    )
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts if step mutation is idempotent or retriable"
    )
    can_fail_silently: bool = Field(
        default=False,
        description="Whether failure of this step can be safely tolerated without failing the plan"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry or step-specific annotations"
    )

    @field_validator("step_id", "capability_id", "intent")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class Plan(BaseContractModel):
    """Strongly typed top-level contract for a structured execution DAG."""
    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}",
        description="Unique plan identifier"
    )
    quest_id: str = Field(..., description="Parent Quest ID to which this plan attaches")
    goal: str = Field(..., description="High-level user objective or goal")
    plan_type: PlanType = Field(
        default=PlanType.TEMPLATE_DERIVED,
        description="Origin of plan: TEMPLATE_DERIVED, GENERATIVE_SYNTHESIZED, or COMPOSITE"
    )
    steps: List[PlanStep] = Field(
        default_factory=list,
        description="Topological or ordered steps in the DAG"
    )
    max_depth: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum allowed dependency chain depth"
    )
    timeout_budget_s: float = Field(
        default=300.0,
        ge=5.0,
        le=86400.0,
        description="Total wall-clock timeout budget for the entire plan"
    )
    skill_id: Optional[str] = Field(
        default=None,
        description="Skill ID if plan was derived from a skill workflow template"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry, model attribution, or custom metadata"
    )
    created_at: float = Field(default_factory=time.time)

    @field_validator("quest_id", "goal")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()

    @model_validator(mode="after")
    def validate_plan_invariants(self) -> "Plan":
        step_ids: Set[str] = set()
        for step in self.steps:
            if step.step_id in step_ids:
                raise ValueError(f"Duplicate step_id '{step.step_id}' in plan.")
            step_ids.add(step.step_id)

        # Validate dependency references
        for step in self.steps:
            for dep in step.dependencies:
                if dep == step.step_id:
                    raise ValueError(f"Step '{step.step_id}' cannot depend on itself.")
                if dep not in step_ids:
                    raise ValueError(f"Step '{step.step_id}' references unknown dependency '{dep}'.")

        return self

    def compute_hash(self) -> str:
        """Computes a deterministic canonical SHA-256 hash of the plan structure and content.
        
        Ensures steps are sorted by step_id, dependencies sorted, numbers normalized,
        and arguments serialized canonically with sorted keys.
        """
        import hashlib
        import json

        canonical_steps = []
        for step in sorted(self.steps, key=lambda s: s.step_id):
            canonical_steps.append({
                "step_id": step.step_id,
                "capability_id": step.capability_id,
                "intent": step.intent,
                "arguments": step.arguments,
                "dependencies": sorted(step.dependencies),
                "timeout_s": round(float(step.timeout_s), 4),
                "max_attempts": int(step.max_attempts),
                "can_fail_silently": bool(step.can_fail_silently),
            })

        plan_dict = {
            "quest_id": self.quest_id,
            "goal": self.goal,
            "plan_type": self.plan_type.value,
            "timeout_budget_s": round(float(self.timeout_budget_s), 4),
            "skill_id": self.skill_id or "",
            "steps": canonical_steps,
        }
        serialized = json.dumps(plan_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
