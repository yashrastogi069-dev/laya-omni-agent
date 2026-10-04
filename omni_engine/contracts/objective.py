"""
omni_engine.contracts.objective
===============================
Strongly typed contracts for objective decomposition and pre-execution plan coverage.

Adheres to:
- Invariant 1: Deterministic Control & Invariant 4: Strongly Typed Contracts.
- L14.3 Section 6: Pre-execution Plan Coverage (mandatory requirements must have explicit
  plan step coverage before physical execution begins).
- Non-decorative, strictly validated models (extra="forbid").
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RequirementCoverageState(str, Enum):
    """Coverage status of an objective requirement by the plan."""
    UNCOVERED = "UNCOVERED"
    PARTIAL = "PARTIAL"
    COVERED = "COVERED"


class RequirementItem(BaseModel):
    """A discrete, verifiable requirement decomposed from an objective."""
    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(description="Unique identifier for requirement, e.g. 'R1', 'R2'")
    description: str = Field(description="Human-readable description of requirement")
    mandatory: bool = Field(default=True, description="Whether this requirement is mandatory for goal completion")
    domain: str = Field(description="Target capability domain: system, desktop, web, browser, repository, automation, file, synthesis")
    expected_evidence_type: Optional[str] = Field(default=None, description="Expected physical evidence, e.g. file, receipt, process, dom")
    mapped_step_ids: List[str] = Field(default_factory=list, description="IDs of plan steps that satisfy this requirement")
    coverage_state: RequirementCoverageState = Field(
        default=RequirementCoverageState.UNCOVERED,
        description="Whether requirement is covered by current plan"
    )

    def mark_covered_by(self, step_id: str) -> None:
        """Associates a plan step with this requirement and marks it covered."""
        if step_id not in self.mapped_step_ids:
            self.mapped_step_ids.append(step_id)
        self.coverage_state = RequirementCoverageState.COVERED


class ObjectiveSpec(BaseModel):
    """Typed objective-requirement specification tracking complete pre-execution plan coverage."""
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(description="Raw user objective or compound goal")
    requirements: List[RequirementItem] = Field(default_factory=list, description="List of decomposed requirements")
    is_compound: bool = Field(default=False, description="Whether objective contains multiple distinct clauses/domains")

    @property
    def overall_coverage(self) -> RequirementCoverageState:
        """Evaluates overall coverage state across all mandatory requirements."""
        if not self.requirements:
            return RequirementCoverageState.UNCOVERED
        mandatory = [r for r in self.requirements if r.mandatory]
        if not mandatory:
            return RequirementCoverageState.COVERED
        covered_count = sum(1 for r in mandatory if r.coverage_state == RequirementCoverageState.COVERED)
        if covered_count == len(mandatory):
            return RequirementCoverageState.COVERED
        if covered_count > 0:
            return RequirementCoverageState.PARTIAL
        return RequirementCoverageState.UNCOVERED

    def is_fully_covered(self) -> bool:
        """Returns True if and only if all mandatory requirements are COVERED."""
        return self.overall_coverage == RequirementCoverageState.COVERED

    def uncovered_mandatory_requirements(self) -> List[RequirementItem]:
        """Returns all mandatory requirements that do not have COVERED status."""
        return [
            r for r in self.requirements
            if r.mandatory and r.coverage_state != RequirementCoverageState.COVERED
        ]

    def get_requirement(self, requirement_id: str) -> Optional[RequirementItem]:
        """Finds a requirement by ID."""
        for r in self.requirements:
            if r.requirement_id == requirement_id:
                return r
        return None
