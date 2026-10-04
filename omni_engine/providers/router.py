"""
omni_engine.providers.router
============================
Role-Aware Generative Provider Router, User Sovereignty Enforcement, and Mock Provider.

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): User model sovereignty (USER_LOCKED, USER_PREFERRED,
  AUTO) and fallback cascades are strictly controlled by deterministic logic, not prompt hints.
- System 1 vs Generative Boundary (Invariants 2 & 3): Generative calls are scoped to explicit
  agent roles: ARGUMENT_WRITER, PLANNER, REPLANNER, FINALIZER, CODING.
- Strongly Typed Capability Contracts (Invariant 4): Router configurations and telemetry records
  are strongly typed Pydantic models with extra="forbid".
- Signals are First-Class (Invariant 7): Granular telemetry records latency, tokens, attempts,
  and fallback diagnostics on every dispatch.
"""

import copy
import re
import threading
import time
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

from omni_engine.contracts.enums import ErrorCode
from omni_engine.contracts.router import (
    AgentRole,
    ModelTier,
    ModelSovereigntyLevel,
    RoleRouteConfig,
    RouterTelemetry,
    DEFAULT_ROLE_CONFIGS,
)
from omni_engine.providers.base import (
    GenerativeProvider,
    GenerationResult,
    ProviderError,
    ProviderHealth,
)
from omni_engine.providers.generative import extract_json_from_text

T = TypeVar("T", bound=BaseModel)

# Set of error codes that are considered transient / recoverable for fallback cascades
RECOVERABLE_ERROR_CODES = {
    ErrorCode.RATE_LIMITED,
    ErrorCode.TIMEOUT,
    ErrorCode.NETWORK_ERROR,
    ErrorCode.SERVICE_UNAVAILABLE,
    ErrorCode.UNCONFIGURED,
}

# Set of error codes that must never cascade and must fail fast immediately
FATAL_ERROR_CODES = {
    ErrorCode.CANCELLED,
    ErrorCode.UNAUTHORIZED_ACTION,
    ErrorCode.CONFIRMATION_REJECTED,
    ErrorCode.INVALID_ARGUMENT,
}


class MockGenerativeProvider(GenerativeProvider):
    """Thread-safe, offline-capable in-memory mock generative provider for testing.
    
    Supports:
    - Scripted text and structured Pydantic object returns.
    - FIFO response queues for simulating multi-step cascades.
    - Per-model scripted returns and error triggers.
    - Full invocation receipt logging.
    """

    def __init__(
        self,
        provider_id: str = "mock",
        model_id: str = "mock-model",
        is_configured: bool = True,
        default_text: str = "Mock response",
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.is_configured = is_configured
        self.default_text = default_text
        self._lock = threading.RLock()
        self._response_queue: List[Union[str, BaseModel, Exception]] = []
        self._model_responses: Dict[str, Union[str, BaseModel]] = {}
        self._model_errors: Dict[str, Union[Exception, ErrorCode]] = {}
        self.invocation_history: List[Dict[str, Any]] = []

    def set_response_queue(self, items: List[Union[str, BaseModel, Exception]]) -> None:
        """Sets the FIFO response queue."""
        with self._lock:
            self._response_queue = list(items)

    def enqueue_response(self, item: Union[str, BaseModel, Exception]) -> None:
        """Appends a scripted response or exception to the FIFO queue."""
        with self._lock:
            self._response_queue.append(item)

    def set_model_response(self, model: str, response: Union[str, BaseModel]) -> None:
        """Maps a specific model ID to a scripted response."""
        with self._lock:
            self._model_responses[model] = response

    def set_model_error(self, model: str, error: Union[Exception, ErrorCode]) -> None:
        """Maps a specific model ID to a simulated error."""
        with self._lock:
            self._model_errors[model] = error

    def clear(self) -> None:
        """Resets all queues, overrides, and invocation history."""
        with self._lock:
            self._response_queue.clear()
            self._model_responses.clear()
            self._model_errors.clear()
            self.invocation_history.clear()

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> GenerationResult:
        """Simulates text generation with queued or mapped responses."""
        target_model = model or self.model_id
        with self._lock:
            self.invocation_history.append({
                "method": "generate_text",
                "prompt": prompt,
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "model": target_model,
                "timeout": timeout,
                "timestamp": time.time(),
            })

            if not self.is_configured:
                raise ProviderError(
                    code=ErrorCode.UNCONFIGURED,
                    message=f"Mock provider '{self.provider_id}' is unconfigured.",
                    provider_id=self.provider_id,
                    model_id=target_model,
                )

            # Check per-model error
            if target_model in self._model_errors:
                err = self._model_errors[target_model]
                if isinstance(err, Exception):
                    raise err
                raise ProviderError(
                    code=err,
                    message=f"Simulated error for model '{target_model}'.",
                    provider_id=self.provider_id,
                    model_id=target_model,
                )

            # Check FIFO queue
            if self._response_queue:
                item = self._response_queue.pop(0)
                if isinstance(item, Exception):
                    raise item
                if isinstance(item, BaseModel):
                    return GenerationResult(
                        text=item.model_dump_json(),
                        provider_id=self.provider_id,
                        model_id=target_model,
                        latency_ms=1.0,
                        prompt_tokens=10,
                        completion_tokens=20,
                    )
                return GenerationResult(
                    text=str(item),
                    provider_id=self.provider_id,
                    model_id=target_model,
                    latency_ms=1.0,
                    prompt_tokens=10,
                    completion_tokens=20,
                )

            # Check per-model response
            if target_model in self._model_responses:
                resp = self._model_responses[target_model]
                if isinstance(resp, BaseModel):
                    text = resp.model_dump_json()
                else:
                    text = str(resp)
                return GenerationResult(
                    text=text,
                    provider_id=self.provider_id,
                    model_id=target_model,
                    latency_ms=1.0,
                    prompt_tokens=10,
                    completion_tokens=20,
                )

            # Default fallback text
            return GenerationResult(
                text=self.default_text,
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=1.0,
                prompt_tokens=10,
                completion_tokens=20,
            )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> T:
        """Simulates structured generation with schema validation."""
        target_model = model or self.model_id
        with self._lock:
            # Check if per-model response is already an instance of response_model
            if target_model in self._model_responses and isinstance(self._model_responses[target_model], response_model):
                self.invocation_history.append({
                    "method": "generate_structured",
                    "prompt": prompt,
                    "response_model": response_model.__name__,
                    "model": target_model,
                    "timeout": timeout,
                    "timestamp": time.time(),
                })
                return self._model_responses[target_model]  # type: ignore

            # Check FIFO queue for direct model instance
            if self._response_queue and isinstance(self._response_queue[0], response_model):
                self.invocation_history.append({
                    "method": "generate_structured",
                    "prompt": prompt,
                    "response_model": response_model.__name__,
                    "model": target_model,
                    "timeout": timeout,
                    "timestamp": time.time(),
                })
                return self._response_queue.pop(0)  # type: ignore

        # Delegate to generate_text for text/json resolution and validation
        gen_result = self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            model=target_model,
            timeout=timeout,
        )

        cleaned_json = extract_json_from_text(gen_result.text)
        try:
            return response_model.model_validate_json(cleaned_json)
        except ValidationError as ve:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Mock output violated schema {response_model.__name__}: {ve}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json, "errors": ve.errors()},
                provider_id=self.provider_id,
                model_id=target_model,
            )
        except Exception as e:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Failed to parse JSON response for {response_model.__name__}: {e}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json},
                provider_id=self.provider_id,
                model_id=target_model,
            )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Convenience alias for GenerativePlanner compatibility returning raw text."""
        res = self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature if temperature is not None else 0.7,
            max_tokens=max_tokens if max_tokens is not None else 2000,
            **kwargs,
        )
        return res.text

    def health_check(self) -> ProviderHealth:
        """Returns mock operational health check receipt."""
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=self.model_id,
            healthy=self.is_configured,
            status_code=ErrorCode.UNKNOWN if self.is_configured else ErrorCode.UNCONFIGURED,
            latency_ms=0.5,
            message="Mock provider operational." if self.is_configured else "Mock provider unconfigured.",
        )


class GenerativeRouter(GenerativeProvider):
    """Role-aware, user-sovereign generative model provider router.
    
    Routes generative requests based on 5 functional roles:
    - ARGUMENT_WRITER (FAST tier)
    - PLANNER (CAPABLE tier)
    - REPLANNER (BALANCED tier)
    - FINALIZER (BALANCED tier)
    - CODING (CAPABLE tier)

    Enforces deterministic User Sovereignty:
    - USER_LOCKED: Zero fallback permitted; raises ProviderError immediately on failure.
    - USER_PREFERRED: User-preferred model attempted first; cascades to fallbacks on recoverable errors.
    - AUTO: Router cascades through calibrated tier models on recoverable errors.

    Drop-In Invariant:
    Inherits from GenerativeProvider(ABC), allowing seamless plug-in anywhere a GenerativeProvider
    is expected, defaulting standard calls to AgentRole.PLANNER.
    """

    def __init__(
        self,
        providers: Optional[Dict[str, GenerativeProvider]] = None,
        role_configs: Optional[Dict[AgentRole, RoleRouteConfig]] = None,
        default_provider_id: str = "openrouter",
        max_telemetry_history: int = 1000,
    ) -> None:
        self.provider_id = "generative_router"
        self.model_id = "router-dynamic"
        self.is_configured = True
        self.default_provider_id = default_provider_id
        self.max_telemetry_history = max_telemetry_history

        self._lock = threading.RLock()
        self.providers: Dict[str, GenerativeProvider] = dict(providers or {})

        # Deep-copy default calibrated configs to allow safe per-instance mutations
        if role_configs is not None:
            self.role_configs: Dict[AgentRole, RoleRouteConfig] = {
                role: cfg.model_copy(deep=True) for role, cfg in role_configs.items()
            }
        else:
            self.role_configs = {
                role: cfg.model_copy(deep=True) for role, cfg in DEFAULT_ROLE_CONFIGS.items()
            }

        self._telemetry_history: List[RouterTelemetry] = []

    # -------------------------------------------------------------------------
    # Role Configuration & User Sovereignty Management
    # -------------------------------------------------------------------------

    def configure_role(self, role: AgentRole, config: RoleRouteConfig) -> None:
        """Sets or replaces the route configuration for a specific role."""
        with self._lock:
            self.role_configs[role] = config.model_copy(deep=True)

    def pin_model(
        self,
        role: AgentRole,
        model_id: str,
        provider_id: Optional[str] = None,
        locked: bool = True,
    ) -> None:
        """Pins a specific model for an agent role, enforcing User Sovereignty.
        
        Args:
            role: Target AgentRole.
            model_id: Target model identifier string.
            provider_id: Optional registered provider ID. If provided, must be in self.providers.
            locked: If True, sovereignty is set to USER_LOCKED (strictly no fallback).
                    If False, sovereignty is set to USER_PREFERRED (cascading fallback allowed).
        """
        with self._lock:
            if provider_id is not None and provider_id not in self.providers:
                raise ValueError(
                    f"Provider '{provider_id}' is not registered in GenerativeRouter. "
                    f"Available providers: {list(self.providers.keys())}"
                )

            current_cfg = self.role_configs.get(role)
            if current_cfg is None:
                current_cfg = copy.deepcopy(DEFAULT_ROLE_CONFIGS[role])

            sovereignty = ModelSovereigntyLevel.USER_LOCKED if locked else ModelSovereigntyLevel.USER_PREFERRED
            updated_cfg = current_cfg.model_copy(
                update={
                    "pinned_model_id": model_id,
                    "pinned_provider_id": provider_id,
                    "sovereignty": sovereignty,
                },
                deep=True,
            )
            self.role_configs[role] = updated_cfg

    def unpin_model(self, role: AgentRole) -> None:
        """Removes model pin and restores AUTO sovereignty for the role."""
        with self._lock:
            current_cfg = self.role_configs.get(role)
            if current_cfg:
                self.role_configs[role] = current_cfg.model_copy(
                    update={
                        "pinned_model_id": None,
                        "pinned_provider_id": None,
                        "sovereignty": ModelSovereigntyLevel.AUTO,
                    },
                    deep=True,
                )

    def get_role_config(self, role: AgentRole) -> RoleRouteConfig:
        """Retrieves a deep-copied configuration snapshot for a role."""
        with self._lock:
            if role not in self.role_configs:
                self.role_configs[role] = DEFAULT_ROLE_CONFIGS[role].model_copy(deep=True)
            return self.role_configs[role].model_copy(deep=True)

    def get_telemetry_history(self, role: Optional[AgentRole] = None) -> List[RouterTelemetry]:
        """Retrieves invocation telemetry records, optionally filtered by role."""
        with self._lock:
            if role is None:
                return list(self._telemetry_history)
            return [t for t in self._telemetry_history if t.role == role]

    def clear_telemetry(self) -> None:
        """Clears stored telemetry history."""
        with self._lock:
            self._telemetry_history.clear()

    # -------------------------------------------------------------------------
    # Internal Candidate Resolution & Error Classification
    # -------------------------------------------------------------------------

    def _resolve_candidate(
        self,
        candidate_str: str,
        role_config: RoleRouteConfig,
    ) -> Tuple[str, str]:
        """Resolves candidate string into (provider_id, model_id).
        
        Supports provider URI scheme:
        - If candidate contains colon (e.g. 'mock:gpt-4o' or 'openrouter:meta-llama/llama-3.3-70b'):
          splits into ('mock', 'gpt-4o').
        - Otherwise, routes to role_config.pinned_provider_id or self.default_provider_id.
        """
        if ":" in candidate_str:
            provider_id, model_id = candidate_str.split(":", 1)
            return provider_id.strip(), model_id.strip()

        provider_id = role_config.pinned_provider_id or self.default_provider_id
        return provider_id, candidate_str.strip()

    def _is_recoverable_error(self, exc: Exception, is_structured: bool = False) -> bool:
        """Evaluates whether an exception permits cascading to the next candidate."""
        if isinstance(exc, ProviderError):
            if exc.code in FATAL_ERROR_CODES:
                return False
            if exc.code in RECOVERABLE_ERROR_CODES:
                return True
            if is_structured and exc.code == ErrorCode.SCHEMA_VIOLATION:
                # Schema violations in structured output permit cascading to a frontier model
                return True
            return False

        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True

        # Generic exceptions are non-recoverable
        return False

    def _record_telemetry(self, telemetry: RouterTelemetry) -> None:
        """Appends telemetry under lock, enforcing history capacity bounds."""
        with self._lock:
            self._telemetry_history.append(telemetry)
            if len(self._telemetry_history) > self.max_telemetry_history:
                self._telemetry_history.pop(0)

    # -------------------------------------------------------------------------
    # Core Role Dispatch & Cascading Cascade Engine
    # -------------------------------------------------------------------------

    def _execute_role_generation(
        self,
        role: AgentRole,
        is_structured: bool,
        prompt: str,
        response_model: Optional[Type[T]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Tuple[Union[GenerationResult, T], RouterTelemetry]:
        """Executes generation across candidate models for a role, enforcing sovereignty and fallbacks."""
        role_config = self.get_role_config(role)

        call_kwargs = dict(kwargs)
        explicit_model = call_kwargs.pop("model", None)
        call_kwargs.pop("timeout", None)

        # Determine primary candidate model
        primary_candidate = explicit_model or role_config.pinned_model_id or role_config.primary_model

        # Build candidate sequence based on sovereignty
        if role_config.sovereignty == ModelSovereigntyLevel.USER_LOCKED:
            # Invariant: USER_LOCKED strictly forbids fallbacks under any circumstances
            candidates = [primary_candidate]
        else:
            candidates = [primary_candidate]
            for fb in role_config.fallback_models:
                if fb != primary_candidate and fb not in candidates:
                    candidates.append(fb)

        eff_temp = temperature if temperature is not None else role_config.temperature
        eff_tokens = max_tokens if max_tokens is not None else role_config.max_tokens
        eff_timeout = timeout if timeout is not None else role_config.timeout_seconds

        last_error: Optional[Exception] = None
        last_fallback_reason: Optional[str] = None
        start_time = time.perf_counter()

        for attempt_idx, candidate in enumerate(candidates, start=1):
            provider_id, model_id = self._resolve_candidate(candidate, role_config)

            # Check provider registration
            provider = self.providers.get(provider_id)
            if provider is None:
                err_msg = f"Provider '{provider_id}' is not registered."
                if role_config.sovereignty == ModelSovereigntyLevel.USER_LOCKED:
                    raise ProviderError(
                        code=ErrorCode.UNCONFIGURED,
                        message=f"Locked provider '{provider_id}' is not registered.",
                        provider_id=provider_id,
                        model_id=model_id,
                    )
                last_fallback_reason = err_msg
                continue

            # Check provider configuration
            if not provider.is_configured:
                err_msg = f"Provider '{provider_id}' is unconfigured."
                if role_config.sovereignty == ModelSovereigntyLevel.USER_LOCKED:
                    raise ProviderError(
                        code=ErrorCode.UNCONFIGURED,
                        message=f"Locked provider '{provider_id}' is unconfigured.",
                        provider_id=provider_id,
                        model_id=model_id,
                    )
                last_fallback_reason = err_msg
                continue

            # Attempt dispatch
            t0 = time.perf_counter()
            try:
                if is_structured:
                    if response_model is None:
                        raise ValueError("response_model must be specified for structured generation.")
                    result = provider.generate_structured(
                        prompt=prompt,
                        response_model=response_model,
                        system_prompt=system_prompt,
                        temperature=eff_temp,
                        max_tokens=eff_tokens,
                        model=model_id,
                        timeout=eff_timeout,
                        **call_kwargs,
                    )
                    latency_ms = round((time.perf_counter() - t0) * 1000, 3)
                    telemetry = RouterTelemetry(
                        role=role,
                        requested_model=primary_candidate,
                        selected_provider_id=provider_id,
                        selected_model_id=model_id,
                        attempts=attempt_idx,
                        was_fallback=(attempt_idx > 1),
                        fallback_reason=last_fallback_reason if attempt_idx > 1 else None,
                        latency_ms=latency_ms,
                    )
                    self._record_telemetry(telemetry)
                    return result, telemetry

                else:
                    gen_result = provider.generate_text(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=eff_temp,
                        max_tokens=eff_tokens,
                        model=model_id,
                        timeout=eff_timeout,
                        **call_kwargs,
                    )
                    latency_ms = round((time.perf_counter() - t0) * 1000, 3)
                    telemetry = RouterTelemetry(
                        role=role,
                        requested_model=primary_candidate,
                        selected_provider_id=provider_id,
                        selected_model_id=model_id,
                        attempts=attempt_idx,
                        was_fallback=(attempt_idx > 1),
                        fallback_reason=last_fallback_reason if attempt_idx > 1 else None,
                        latency_ms=latency_ms,
                        prompt_tokens=gen_result.prompt_tokens,
                        completion_tokens=gen_result.completion_tokens,
                    )
                    self._record_telemetry(telemetry)
                    # Attach telemetry in result metadata for drop-in callers
                    gen_result.metadata["router_telemetry"] = telemetry.model_dump()
                    return gen_result, telemetry

            except Exception as exc:
                last_error = exc
                # If USER_LOCKED: strictly no fallback under any circumstance
                if role_config.sovereignty == ModelSovereigntyLevel.USER_LOCKED:
                    raise exc

                # Check if error is recoverable
                if not self._is_recoverable_error(exc, is_structured=is_structured):
                    # Fatal error: abort cascade immediately
                    raise exc

                last_fallback_reason = (
                    f"Candidate {attempt_idx} '{candidate}' ({provider_id}:{model_id}) "
                    f"failed with recoverable error: {exc}"
                )

        # All candidates exhausted
        total_latency = round((time.perf_counter() - start_time) * 1000, 3)
        raise ProviderError(
            code=ErrorCode.PROCESS_FAILED,
            message=(
                f"All {len(candidates)} model candidates exhausted for role '{role.value}'. "
                f"Requested: '{primary_candidate}'. Last diagnostic: {last_fallback_reason}"
            ),
            details={
                "role": role.value,
                "requested_model": primary_candidate,
                "candidates_tried": candidates,
                "attempts": len(candidates),
                "total_latency_ms": total_latency,
                "last_error": str(last_error),
            },
            provider_id=self.provider_id,
            model_id=primary_candidate,
        )

    # -------------------------------------------------------------------------
    # Role-Aware Public Execution Methods
    # -------------------------------------------------------------------------

    def generate_text_for_role(
        self,
        role: AgentRole,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> GenerationResult:
        """Generates text for an explicit agent role, attaching router telemetry to result.metadata."""
        result, _ = self._execute_role_generation(
            role=role,
            is_structured=False,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
        return result  # type: ignore

    def generate_text_with_telemetry(
        self,
        role: AgentRole,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Tuple[GenerationResult, RouterTelemetry]:
        """Generates text for a role and explicitly returns the typed RouterTelemetry envelope."""
        result, telemetry = self._execute_role_generation(
            role=role,
            is_structured=False,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
        return result, telemetry  # type: ignore

    def generate_structured_for_role(
        self,
        role: AgentRole,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> T:
        """Generates validated Pydantic model for an explicit agent role."""
        result, _ = self._execute_role_generation(
            role=role,
            is_structured=True,
            prompt=prompt,
            response_model=response_model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
        return result  # type: ignore

    def generate_structured_with_telemetry(
        self,
        role: AgentRole,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Tuple[T, RouterTelemetry]:
        """Generates validated Pydantic model and explicitly returns the typed RouterTelemetry envelope."""
        result, telemetry = self._execute_role_generation(
            role=role,
            is_structured=True,
            prompt=prompt,
            response_model=response_model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )
        return result, telemetry  # type: ignore

    # -------------------------------------------------------------------------
    # GenerativeProvider(ABC) Drop-In Implementations
    # -------------------------------------------------------------------------

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> GenerationResult:
        """Standard GenerativeProvider text generation, defaulting to AgentRole.PLANNER."""
        # If model override provided, temporarily route as PLANNER with model override
        return self.generate_text_for_role(
            role=AgentRole.PLANNER,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            model=model,
            **kwargs,
        )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> T:
        """Standard GenerativeProvider structured generation, defaulting to AgentRole.PLANNER."""
        return self.generate_structured_for_role(
            role=AgentRole.PLANNER,
            prompt=prompt,
            response_model=response_model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            model=model,
            **kwargs,
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """GenerativePlanner compatibility alias returning raw text for AgentRole.PLANNER."""
        res = self.generate_text_for_role(
            role=AgentRole.PLANNER,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return res.text

    def health_check(self) -> ProviderHealth:
        """Probes the default provider health and returns standardized ProviderHealth."""
        provider = self.providers.get(self.default_provider_id)
        if provider is None:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.UNCONFIGURED,
                latency_ms=0.0,
                message=f"Default provider '{self.default_provider_id}' is not registered.",
            )
        health = provider.health_check()
        return ProviderHealth(
            provider_id=self.provider_id,
            model_id=health.model_id,
            healthy=health.healthy,
            status_code=health.status_code,
            latency_ms=health.latency_ms,
            message=f"Router default provider ({self.default_provider_id}): {health.message}",
            details={"underlying_provider": health.model_dump()},
        )
