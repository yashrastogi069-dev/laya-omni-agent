"""
omni_engine.contracts.arguments
===============================
Strongly typed contracts for capability argument resolution, extraction sources,
and validation envelopes.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Arguments are validated against strict JSON schemas.
- Invariant 4: Strongly Typed Contracts — All slot resolutions and envelopes are Pydantic v2 models.
- Evidence-Based Completion: Unresolved slots trigger structured clarifications, never hallucinated defaults.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field
from omni_engine.contracts.base import BaseContractModel


class ArgumentExtractionSource(str, Enum):
    """Source origin of an extracted capability argument."""
    DETERMINISTIC_REGEX = "deterministic_regex"
    SYNTACTIC_AST = "syntactic_ast"
    GENERATIVE_SYNTHESIS = "generative_synthesis"
    SCHEMA_DEFAULT = "schema_default"
    CONTEXT_INHERITED = "context_inherited"


class ArgumentSlot(BaseContractModel):
    """Represents a single extracted or resolved argument slot."""
    name: str = Field(..., description="Target property name in capability input_schema")
    value: Any = Field(default=None, description="Resolved typed value")
    is_resolved: bool = Field(default=False, description="Whether slot was successfully resolved")
    source: ArgumentExtractionSource = Field(..., description="Extraction methodology")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    raw_text: Optional[str] = Field(default=None, description="Source substring extracted from prompt")
    error: Optional[str] = Field(default=None, description="Validation or parsing error if resolution failed")


class ArgumentResolutionEnvelope(BaseContractModel):
    """Complete envelope containing resolved arguments, schema validation state, and clarification triggers."""
    schema_version: str = Field(default="1.0.0", description="Contract schema version")
    request_id: str = Field(..., description="Correlation request ID")
    capability_id: str = Field(..., description="Target capability ID")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Resolved arguments dictionary ready for invocation")
    resolved_slots: Dict[str, ArgumentSlot] = Field(default_factory=dict, description="Detailed slot breakdown")
    is_valid: bool = Field(default=False, description="Whether arguments satisfy input_schema requirements")
    validation_errors: List[str] = Field(default_factory=list, description="Schema validation failure messages")
    clarification_needed: bool = Field(default=False, description="Whether interactive user clarification is required")
    clarification_prompt: Optional[str] = Field(default=None, description="User-facing clarifying question if slots are missing")
    missing_slots: List[str] = Field(default_factory=list, description="List of required property names that could not be resolved")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Resolution latency in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry and source metadata")
