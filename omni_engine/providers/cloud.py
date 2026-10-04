"""
omni_engine.providers.cloud
===========================
Direct, production-grade cloud model provider adapters:
- DirectOpenAIProvider (https://api.openai.com/v1)
- AnthropicProvider (https://api.anthropic.com/v1/messages)
- DeepSeekProvider (https://api.deepseek.com)

Adheres to Prime Directive & Repository Invariants:
- Deterministic Control (Invariant 1): Credentials resolved safely from environment;
  unconfigured providers degrade gracefully without throwing during initialization.
- Strongly Typed Contracts (Invariant 4): Strictly returns normalized GenerationResult
  and validated Pydantic models.
- Secret Hygiene (docs/SECURITY_AND_POLICY.md): Dual-layer sanitization ensures zero
  API key leakage in error strings, logs, or telemetry.
- Thread-Safe Invocation: Accepts per-invocation model and timeout overrides without
  mutating instance state.
- Decoupled Offline Testability: Accepts mock transport/client injection for 100% offline
  deterministic testing in <1 second.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from omni_engine.automation.scrubber import SecretScrubber
from omni_engine.contracts.enums import ErrorCode
from omni_engine.providers.base import (
    GenerativeProvider,
    GenerationResult,
    ProviderError,
    ProviderHealth,
)
from omni_engine.providers.generative import extract_json_from_text

T = TypeVar("T", bound=BaseModel)


def sanitize_provider_error(error_msg: str, api_key: Optional[str] = None) -> str:
    """Applies dual-layer sanitization: literal token replacement followed by regex scrubbing."""
    text = str(error_msg)
    if api_key and len(api_key) >= 6:
        text = text.replace(api_key, "[REDACTED_API_KEY]")
    return SecretScrubber.scrub_text(text)


class DirectOpenAIProvider(GenerativeProvider):
    """Direct provider connecting to OpenAI's official chat completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        client: Optional[Any] = None,
    ) -> None:
        self.provider_id = "openai"
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self.model_id = model or os.environ.get("OPENAI_MODEL") or "gpt-4o"
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        self.timeout = float(timeout)
        self.is_configured = bool(self.api_key and self.api_key.strip())
        self._client = client

        # Non-throwing initialization invariant: never crash __init__ if unconfigured
        if self._client is None and self.is_configured:
            try:
                from openai import OpenAI
                self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)
            except Exception:
                self.is_configured = False

    def __repr__(self) -> str:
        return f"<DirectOpenAIProvider id='{self.provider_id}' model='{self.model_id}' configured={self.is_configured}>"

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> GenerationResult:
        """Sends chat completion to OpenAI and returns normalized GenerationResult."""
        target_model = model or self.model_id
        target_timeout = float(timeout) if timeout is not None else self.timeout

        if not self.is_configured or self._client is None:
            raise ProviderError(
                code=ErrorCode.UNCONFIGURED,
                message=f"OpenAI provider '{self.provider_id}' is unconfigured. Set OPENAI_API_KEY.",
                provider_id=self.provider_id,
                model_id=target_model,
            )

        if not prompt or not prompt.strip():
            raise ProviderError(
                code=ErrorCode.INVALID_ARGUMENT,
                message="Prompt cannot be empty or whitespace.",
                provider_id=self.provider_id,
                model_id=target_model,
            )

        messages = []
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})

        t0 = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=target_timeout,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 3)

            if not resp.choices or not resp.choices[0].message:
                raise ProviderError(
                    code=ErrorCode.PROCESS_FAILED,
                    message="OpenAI returned empty completion choices.",
                    provider_id=self.provider_id,
                    model_id=target_model,
                )

            choice = resp.choices[0]
            usage = getattr(resp, "usage", None)

            return GenerationResult(
                text=choice.message.content or "",
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=latency_ms,
                prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
                completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
                finish_reason=getattr(choice, "finish_reason", None),
            )

        except ProviderError:
            raise
        except Exception as e:
            raw_err = str(e)
            sanitized_err = sanitize_provider_error(raw_err, self.api_key)
            lower_err = raw_err.lower()

            code = ErrorCode.NETWORK_ERROR
            if "auth" in lower_err or "api key" in lower_err or "401" in lower_err:
                code = ErrorCode.AUTH_REQUIRED
            elif "rate" in lower_err or "429" in lower_err:
                code = ErrorCode.RATE_LIMITED
            elif "timeout" in lower_err:
                code = ErrorCode.TIMEOUT

            raise ProviderError(
                code=code,
                message=f"OpenAI generation failed: {sanitized_err}",
                details={"model": target_model},
                provider_id=self.provider_id,
                model_id=target_model,
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
        """Generates structured Pydantic object, extracting and validating JSON."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_instruction = (
            f"{system_prompt}\n\n" if system_prompt else ""
        ) + f"You MUST return ONLY valid JSON matching this schema:\n```json\n{schema_json}\n```\nDo NOT include conversational commentary."

        gen_result = self.generate_text(
            prompt=prompt,
            system_prompt=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            timeout=timeout,
        )

        cleaned_json = extract_json_from_text(gen_result.text)

        try:
            return response_model.model_validate_json(cleaned_json)
        except ValidationError as ve:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"OpenAI output violated schema {response_model.__name__}: {ve}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json, "errors": ve.errors()},
                provider_id=self.provider_id,
                model_id=model or self.model_id,
            )
        except Exception as e:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Failed to parse JSON response for {response_model.__name__}: {e}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json},
                provider_id=self.provider_id,
                model_id=model or self.model_id,
            )

    def health_check(self) -> ProviderHealth:
        """Probes endpoint reachability."""
        if not self.is_configured:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.UNCONFIGURED,
                latency_ms=0.0,
                message="OpenAI provider is unconfigured (OPENAI_API_KEY missing).",
            )
        try:
            t0 = time.perf_counter()
            self.generate_text(prompt="Ping", max_tokens=5, temperature=0.1)
            latency = round((time.perf_counter() - t0) * 1000, 3)
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=True,
                status_code=ErrorCode.UNKNOWN,
                latency_ms=latency,
                message="OpenAI API operational.",
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.NETWORK_ERROR,
                latency_ms=0.0,
                message=f"OpenAI probe failed: {sanitize_provider_error(str(e), self.api_key)}",
            )


class AnthropicProvider(GenerativeProvider):
    """Direct provider connecting to Anthropic's official Claude Messages API.
    
    Implemented using Python's standard library urllib.request to avoid external dependency bloat.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        transport_fn: Optional[Callable[[Dict[str, Any], float], Dict[str, Any]]] = None,
    ) -> None:
        self.provider_id = "anthropic"
        self.api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self.model_id = model or os.environ.get("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022"
        self.base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com/v1/messages"
        self.timeout = float(timeout)
        self.is_configured = bool(self.api_key and self.api_key.strip())
        self.transport_fn = transport_fn

    def __repr__(self) -> str:
        return f"<AnthropicProvider id='{self.provider_id}' model='{self.model_id}' configured={self.is_configured}>"

    def _execute_http_request(self, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
        """Sends HTTP POST to Anthropic Messages endpoint."""
        if self.transport_fn is not None:
            return self.transport_fn(payload, timeout)

        data = json.dumps(payload).encode("utf-8")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
            "accept": "application/json",
        }

        req = urllib.request.Request(self.base_url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as he:
            err_body = ""
            try:
                err_body = he.read().decode("utf-8")
            except Exception:
                pass
            raise RuntimeError(f"HTTP {he.code}: {err_body or he.reason}")
        except urllib.error.URLError as ue:
            raise RuntimeError(f"URLError: {ue.reason}")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> GenerationResult:
        """Sends Messages request to Anthropic and returns normalized GenerationResult."""
        target_model = model or self.model_id
        target_timeout = float(timeout) if timeout is not None else self.timeout

        if not self.is_configured:
            raise ProviderError(
                code=ErrorCode.UNCONFIGURED,
                message=f"Anthropic provider '{self.provider_id}' is unconfigured. Set ANTHROPIC_API_KEY.",
                provider_id=self.provider_id,
                model_id=target_model,
            )

        if not prompt or not prompt.strip():
            raise ProviderError(
                code=ErrorCode.INVALID_ARGUMENT,
                message="Prompt cannot be empty or whitespace.",
                provider_id=self.provider_id,
                model_id=target_model,
            )

        # REV-17.5-01: Mandatory max_tokens and clamped temperature in [0.0, 1.0]
        target_tokens = max(1, int(max_tokens if max_tokens is not None else 4096))
        target_temp = min(max(float(temperature if temperature is not None else 0.7), 0.0), 1.0)

        # REV-17.5-02: System prompt segregation (Anthropic strictly forbids role=system in messages)
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": [{"role": "user", "content": prompt.strip()}],
            "max_tokens": target_tokens,
            "temperature": target_temp,
        }
        if system_prompt and system_prompt.strip():
            payload["system"] = system_prompt.strip()

        t0 = time.perf_counter()
        try:
            resp_dict = self._execute_http_request(payload, timeout=target_timeout)
            latency_ms = round((time.perf_counter() - t0) * 1000, 3)

            # REV-17.5-06: Robust content block traversal (join all text blocks)
            content_blocks = resp_dict.get("content", [])
            extracted_text = "".join(
                b.get("text", "")
                for b in content_blocks
                if isinstance(b, dict) and b.get("type") == "text"
            )

            usage = resp_dict.get("usage", {})
            return GenerationResult(
                text=extracted_text,
                provider_id=self.provider_id,
                model_id=target_model,
                latency_ms=latency_ms,
                prompt_tokens=usage.get("input_tokens"),
                completion_tokens=usage.get("output_tokens"),
                finish_reason=resp_dict.get("stop_reason"),
            )

        except ProviderError:
            raise
        except Exception as e:
            raw_err = str(e)
            sanitized_err = sanitize_provider_error(raw_err, self.api_key)
            lower_err = raw_err.lower()

            code = ErrorCode.NETWORK_ERROR
            if "401" in lower_err or "auth" in lower_err or "api key" in lower_err or "authentication_error" in lower_err:
                code = ErrorCode.AUTH_REQUIRED
            elif "429" in lower_err or "rate" in lower_err or "rate_limit_error" in lower_err:
                code = ErrorCode.RATE_LIMITED
            elif "timeout" in lower_err or "timed out" in lower_err:
                code = ErrorCode.TIMEOUT
            elif "400" in lower_err or "invalid_request_error" in lower_err:
                code = ErrorCode.INVALID_ARGUMENT

            raise ProviderError(
                code=code,
                message=f"Anthropic generation failed: {sanitized_err}",
                details={"model": target_model},
                provider_id=self.provider_id,
                model_id=target_model,
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
        """Generates structured Pydantic object with anti-preamble prompt framing."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)

        # REV-17.5-05: Strict preamble suppression instruction
        strict_system = (
            f"{system_prompt.strip()}\n\n" if system_prompt and system_prompt.strip() else ""
        ) + (
            "CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object matching the JSON schema below.\n"
            "Do NOT include any explanatory text, markdown code blocks, backticks, or conversational preamble.\n"
            "Your response must begin with '{' and end with '}'.\n\n"
            f"JSON Schema:\n{schema_json}"
        )

        gen_result = self.generate_text(
            prompt=prompt,
            system_prompt=strict_system,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
            timeout=timeout,
        )

        cleaned_json = extract_json_from_text(gen_result.text)

        try:
            return response_model.model_validate_json(cleaned_json)
        except ValidationError as ve:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Anthropic output violated schema {response_model.__name__}: {ve}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json, "errors": ve.errors()},
                provider_id=self.provider_id,
                model_id=model or self.model_id,
            )
        except Exception as e:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Failed to parse JSON response for {response_model.__name__}: {e}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json},
                provider_id=self.provider_id,
                model_id=model or self.model_id,
            )

    def health_check(self) -> ProviderHealth:
        """Probes Anthropic API reachability."""
        if not self.is_configured:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.UNCONFIGURED,
                latency_ms=0.0,
                message="Anthropic provider is unconfigured (ANTHROPIC_API_KEY missing).",
            )
        try:
            t0 = time.perf_counter()
            self.generate_text(prompt="Ping", max_tokens=5, temperature=0.1)
            latency = round((time.perf_counter() - t0) * 1000, 3)
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=True,
                status_code=ErrorCode.UNKNOWN,
                latency_ms=latency,
                message="Anthropic API operational.",
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.NETWORK_ERROR,
                latency_ms=0.0,
                message=f"Anthropic probe failed: {sanitize_provider_error(str(e), self.api_key)}",
            )


class DeepSeekProvider(DirectOpenAIProvider):
    """Direct provider connecting to DeepSeek's official OpenAI-compatible API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        client: Optional[Any] = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY", "")
        url = base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        mod = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat"
        super().__init__(api_key=key, model=mod, base_url=url, timeout=timeout, client=client)
        self.provider_id = "deepseek"

    def __repr__(self) -> str:
        return f"<DeepSeekProvider id='{self.provider_id}' model='{self.model_id}' configured={self.is_configured}>"


def build_standard_generative_router(
    openrouter_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    deepseek_api_key: Optional[str] = None,
    mock_provider: Optional[GenerativeProvider] = None,
    default_provider_id: str = "openrouter",
) -> Any:
    """Builds a GenerativeRouter populated with standard cloud providers and fallbacks."""
    from omni_engine.providers.generative import OpenRouterProvider
    from omni_engine.providers.router import GenerativeRouter

    providers: Dict[str, GenerativeProvider] = {}

    # OpenRouter Proxy
    providers["openrouter"] = OpenRouterProvider(api_key=openrouter_api_key)

    # Direct Cloud Providers
    providers["openai"] = DirectOpenAIProvider(api_key=openai_api_key)
    providers["anthropic"] = AnthropicProvider(api_key=anthropic_api_key)
    providers["deepseek"] = DeepSeekProvider(api_key=deepseek_api_key)

    # Optional in-memory mock provider
    if mock_provider is not None:
        providers["mock"] = mock_provider

    return GenerativeRouter(
        providers=providers,
        default_provider_id=default_provider_id,
    )
