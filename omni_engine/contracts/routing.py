"""
omni_engine.contracts.routing
=============================
Strongly typed boundary contracts for hierarchical capability routing.

Contracts:
- CapabilityCandidate: Individual capability candidate with score, domain, and rationale.
- RouteDecision: Complete hierarchical routing decision with candidate reduction telemetry
  and strict fail-open consistency validation.
"""

import math
import time
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator, model_validator

from .base import BaseContractModel


class CapabilityCandidate(BaseContractModel):
    """Individual candidate capability proposed by hierarchical router."""
    capability_id: str = Field(..., description="Canonical capability identifier")
    domain: str = Field(..., description="Capability domain (web, browser, os, dev, data)")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance confidence score strictly bounded in [0.0, 1.0]")
    rationale: str = Field(..., description="Selection provenance (e.g. domain_primary, explicit_keyword_pinned, pooled_fallback)")
    spec_summary: Optional[str] = Field(default=None, description="Concise capability description for downstream planning context")

    @field_validator("score")
    @classmethod
    def validate_score_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Candidate score cannot be NaN or Infinite.")
        return max(0.0, min(1.0, float(v)))


class RouteDecision(BaseContractModel):
    """Complete, strongly typed routing decision governing tool catalog reduction."""
    schema_version: str = Field(default="1.0.0", description="RouteDecision contract schema version")
    request_id: str = Field(..., description="Correlated request identifier matching DecisionFrame")
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp when routing completed")
    
    selected_domain: Optional[str] = Field(
        default=None,
        description="Primary domain selected, or None if cross-domain/conversational"
    )
    candidate_domains: List[str] = Field(
        default_factory=list,
        description="All active domains included in candidate pooling"
    )
    candidates: List[CapabilityCandidate] = Field(
        default_factory=list,
        description="Deduplicated, ranked candidate capabilities"
    )
    
    is_fail_open: bool = Field(
        default=False,
        description="Whether routing fell open due to low confidence, high ambiguity, or multi-step scope"
    )
    fallback_reason: Optional[str] = Field(
        default=None,
        description="Detailed reason for fail-open fallback, if triggered"
    )
    
    catalog_reduction_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Catalog reduction metric: 1.0 - (len(candidates) / total_registry_capabilities)"
    )
    total_registry_capabilities: int = Field(
        ...,
        ge=0,
        description="Total capability count in registry at routing time"
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total hierarchical routing execution latency in milliseconds"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diagnostic telemetry, scoring details, and provider provenance"
    )

    @field_validator("catalog_reduction_ratio")
    @classmethod
    def validate_ratio_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return max(0.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def validate_candidate_consistency(self) -> "RouteDecision":
        # 1. Reject duplicate capability IDs
        seen = set()
        for c in self.candidates:
            if c.capability_id in seen:
                raise ValueError(f"Duplicate capability candidate ID '{c.capability_id}' detected in RouteDecision.")
            seen.add(c.capability_id)

        # 2. Enforce fail-open reason consistency
        if self.is_fail_open and not self.fallback_reason:
            raise ValueError("RouteDecision with is_fail_open=True must specify a non-empty fallback_reason.")
        if not self.is_fail_open and self.fallback_reason is not None:
            raise ValueError(f"RouteDecision with is_fail_open=False must have fallback_reason=None, got '{self.fallback_reason}'.")

        # 3. Candidates cannot exceed registry size
        if len(self.candidates) > self.total_registry_capabilities:
            raise ValueError(
                f"Candidate count ({len(self.candidates)}) cannot exceed total registry capabilities ({self.total_registry_capabilities})."
            )

        return self
