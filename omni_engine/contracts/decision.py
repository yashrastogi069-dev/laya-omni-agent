"""
System 1 Decision Contracts
===========================
Structures defining:
- Discrete calibrated decision signals (intent, urgency, risk, reversibility, etc.)
- Composite DecisionFrame produced within <35ms by System 1 nervous system
"""

import math
from typing import Any, Dict, List, Optional
from pydantic import Field, field_validator

from .base import BaseContractModel
from .enums import DecisionSignalType


class DecisionSignal(BaseContractModel):
    """A discrete signal produced by System 1 with bounded, calibrated confidence."""
    signal_type: DecisionSignalType
    value: Any
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Calibrated model confidence strictly bounded in [0.0, 1.0]"
    )
    probabilities: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional probability distribution over candidate categories"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplemental decision telemetry or feature attribution"
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latency cost to compute this individual signal in milliseconds"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence_not_nan(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError("Confidence cannot be NaN or Infinite.")
        return v

    @field_validator("probabilities")
    @classmethod
    def validate_probabilities(cls, v: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if v is not None:
            for k, prob in v.items():
                if math.isnan(prob) or math.isinf(prob):
                    raise ValueError(f"Probability for '{k}' cannot be NaN or Infinite.")
                if not (0.0 <= prob <= 1.0):
                    raise ValueError(f"Probability for '{k}' must be between 0.0 and 1.0, got {prob}.")
        return v


class DecisionFrame(BaseContractModel):
    """Complete, immutable System 1 decision packet governing downstream routing and autonomy."""
    request_id: str = Field(..., description="Unique request identifier")
    timestamp: float = Field(..., description="Epoch timestamp when decision was reached")
    
    # Core First-Class System 1 Signals
    intent: DecisionSignal = Field(..., description="Classified user intent")
    task_class: DecisionSignal = Field(..., description="Complexity and operational task class")
    urgency: DecisionSignal = Field(..., description="Temporal urgency rating")
    importance: DecisionSignal = Field(..., description="Objective importance / priority")
    risk: DecisionSignal = Field(..., description="Safety and blast radius risk assessment")
    reversibility: DecisionSignal = Field(..., description="Action reversibility signal (Invariant 7)")
    ambiguity: DecisionSignal = Field(..., description="Instruction ambiguity / missing context rating")
    needs_plan: DecisionSignal = Field(..., description="Whether multi-step DAG planning is required")
    needs_tools: DecisionSignal = Field(..., description="Whether external tool execution is required")
    model_tier: DecisionSignal = Field(..., description="Selected model tier (System 1, flash, pro, etc.)")

    # Routing and Selection Candidates
    candidate_domains: List[str] = Field(
        default_factory=list,
        description="Ranked domains deemed relevant (e.g. ['web', 'data', 'os'])"
    )
    candidate_skills: List[str] = Field(
        default_factory=list,
        description="Ranked skill workflows deemed relevant"
    )
    selected_skill: Optional[str] = Field(
        default=None,
        description="Deterministic skill selected if confidence threshold is met"
    )

    # Provider and Observability Telemetry
    raw_signals: Dict[str, DecisionSignal] = Field(
        default_factory=dict,
        description="Any extra raw signals extracted during inference"
    )
    total_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Total end-to-end System 1 inference time in milliseconds (target: <35ms)"
    )
    provider_id: str = Field(
        default="laya-s1",
        description="Identifier of the provider that produced this decision frame"
    )
