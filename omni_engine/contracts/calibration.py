"""
omni_engine.contracts.calibration
=================================
Calibration contracts and threshold configurations for System 1 Decision Fabric
and Hierarchical Capability Routing.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Thresholds are explicit data structures,
  not scattered magic numbers or uncalibrated inline literals.
- Calibrated Probability Bounds: Distinguishes empirical model posterior thresholds
  from deterministic policy boundaries.
- Provenance & Traceability: Tracks calibration version in DecisionSignal metadata.
"""

from typing import Optional
from pydantic import Field
from omni_engine.contracts.base import BaseContractModel


class CalibratedModelThresholds(BaseContractModel):
    """Calibrated probability and confidence thresholds applied to model posteriors."""

    domain_confidence_min: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
        description="Minimum domain classification confidence before triggering cross-domain pooling",
    )
    ambiguity_max: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Maximum model ambiguity posterior before triggering user clarification",
    )
    skill_candidate_min: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Minimum matching score for skill inclusion in candidate skills list",
    )
    skill_selection_min: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum matching score for primary skill selection and workflow template attachment",
    )
    skill_description_overlap_ceiling: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Maximum score achievable from description token overlap alone, preventing false-locking",
    )


class DeterministicPolicyThresholds(BaseContractModel):
    """Deterministic system boundaries, structural heuristics, and policy scores."""

    ambiguity_min_words: int = Field(
        default=2,
        ge=0,
        description="Prompts with word count at or below this limit are unconditionally treated as ambiguous",
    )
    pinned_capability_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Candidate score assigned to capabilities matched via explicit keyword regex",
    )
    skill_required_capability_score: float = Field(
        default=0.98,
        ge=0.0,
        le=1.0,
        description="Candidate score assigned to required capabilities of a selected skill",
    )
    skill_optional_capability_score: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Candidate score assigned to optional capabilities of a selected skill",
    )
    domain_primary_default_score: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Baseline candidate score for capabilities in the primary routed domain",
    )
    domain_pooled_default_score: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Baseline candidate score for capabilities in fail-open pooled domains",
    )
    lexical_primary_base_score: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Base score for lexical candidate scoring in primary domain",
    )
    lexical_pooled_base_score: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="Base score for lexical candidate scoring in pooled domain",
    )
    lexical_overlap_boost_per_token: float = Field(
        default=0.15,
        ge=0.0,
        description="Score boost per matching non-generic token in lexical scoring",
    )
    lexical_overlap_boost_max: float = Field(
        default=0.40,
        ge=0.0,
        description="Maximum total boost achievable from token overlap in lexical scoring",
    )
    lexical_score_cap: float = Field(
        default=0.90,
        ge=0.0,
        le=1.0,
        description="Upper ceiling for purely lexical capability matching scores",
    )


class CalibrationConfig(BaseContractModel):
    """Master calibration configuration bundle for System 1 Decision Fabric and Routing."""

    calibration_version: str = Field(
        default="modernbert-large-temp-scaled-v1",
        description="Identifier of the empirical calibration dataset and temperature scaling pass",
    )
    model_thresholds: CalibratedModelThresholds = Field(
        default_factory=CalibratedModelThresholds,
        description="Calibrated model posterior thresholds",
    )
    deterministic_policy: DeterministicPolicyThresholds = Field(
        default_factory=DeterministicPolicyThresholds,
        description="Deterministic invariant floors and scoring parameters",
    )
