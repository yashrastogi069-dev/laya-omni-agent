"""
omni_engine.providers.base
==========================
Vendor-independent abstract contracts and telemetry models for System 1 and Generative providers.

Decouples high-frequency decision making and generative reasoning from specific vendors
and libraries (Laya, Jev, OpenRouter, Anthropic, local vLLM).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import Field, BaseModel

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import ErrorCode
from omni_engine.contracts.decision import DecisionSignal

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    """Normalized exception raised by all providers."""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        provider_id: str = "unknown",
        model_id: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.provider_id = provider_id
        self.model_id = model_id

    def __str__(self) -> str:
        return f"[{self.provider_id}:{self.code.value}] {self.message}"


class ProviderHealth(BaseContractModel):
    """Standardized health check receipt across all providers."""
    provider_id: str = Field(..., description="Unique provider identifier")
    model_id: str = Field(..., description="Model identifier / release tag")
    healthy: bool = Field(..., description="Whether provider is operational and ready")
    status_code: ErrorCode = Field(default=ErrorCode.UNKNOWN, description="Health status code")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Observed round-trip ping/probe latency")
    message: str = Field(default="Operational", description="Human-readable health diagnostic message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry")


class GenerationResult(BaseContractModel):
    """Normalized structured result envelope from GenerativeProvider."""
    text: str = Field(..., description="Generated text output")
    provider_id: str = Field(..., description="Unique provider identifier")
    model_id: str = Field(..., description="Underlying model identifier")
    latency_ms: float = Field(..., ge=0.0, description="End-to-end inference latency in ms")
    prompt_tokens: Optional[int] = Field(default=None, description="Input token count if reported")
    completion_tokens: Optional[int] = Field(default=None, description="Output token count if reported")
    finish_reason: Optional[str] = Field(default=None, description="Model completion stop reason")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific telemetry")


class SystemOneProvider(ABC):
    """Vendor-independent interface for high-frequency System 1 decision engines.
    
    Target performance: <35ms inference per decision frame.
    Supports batched multi-question evaluation to prevent latency linear scaling.
    """
    provider_id: str
    model_id: str
    is_configured: bool

    @abstractmethod
    def predict_signals(
        self,
        context: Dict[str, Any],
        questions: Dict[str, Any],
    ) -> Dict[str, DecisionSignal]:
        """Evaluates multiple decision criteria simultaneously in a single forward pass.
        
        Args:
            context: State dictionary (e.g. {"prompt": "..."})
            questions: Dictionary mapping signal names to question configurations (type, criteria, etc.)
            
        Returns:
            Dictionary mapping signal names to strongly typed DecisionSignals with provenance.
        """
        pass

    @abstractmethod
    def classify(
        self,
        prompt: str,
        criteria: Dict[str, str],
        instructions: str = "Classify target category:",
    ) -> DecisionSignal:
        """Convenience method for single-choice classification."""
        pass

    @abstractmethod
    def score(
        self,
        prompt: str,
        criteria: str,
    ) -> float:
        """Evaluates relevance or probability score in [0.0, 1.0] for a single criterion."""
        pass

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Probes engine health and records latency."""
        pass


class GenerativeProvider(ABC):
    """Vendor-independent interface for System 2 generative LLMs.
    
    Used strictly when deterministic code or System 1 cannot solve the task:
    - Novel multi-step planning (L12)
    - Structured argument synthesis (L8)
    - Code generation & deep research synthesis
    """
    provider_id: str
    model_id: str
    is_configured: bool

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> GenerationResult:
        """Generates raw text from model."""
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
    ) -> T:
        """Generates a structured Pydantic object, extracting and validating JSON."""
        pass

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Probes remote or local generative service health and latency."""
        pass
