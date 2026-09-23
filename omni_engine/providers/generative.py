"""
omni_engine.providers.generative
================================
Generative Model Providers: OpenRouterProvider and Local/Remote OpenAI-compatible APIs.

Adheres to Prime Directive & Invariants:
- Reserved strictly for novel planning (L12), argument resolution (L8), and complex synthesis.
- Vendor decoupling: configurable models and base URLs (OpenRouter, Ollama, vLLM).
- Graceful non-crashing initialization when API key is missing.
- Deterministic markdown fence stripping for structured JSON generation.
- Zero local RAM overhead (pure remote HTTP client).
"""

import json
import os
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from omni_engine.contracts.enums import ErrorCode
from .base import GenerativeProvider, GenerationResult, ProviderError, ProviderHealth

T = TypeVar("T", bound=BaseModel)


def extract_json_from_text(raw_text: str) -> str:
    """Strips markdown code fences and whitespace to isolate JSON payload."""
    text = raw_text.strip()
    
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Check if text is enclosed in curly or square brackets
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()
        
    return text


class OpenRouterProvider(GenerativeProvider):
    """Generative provider accessing OpenRouter or any OpenAI-compatible API endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.provider_id = "openrouter"
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("OPENROUTER_API_KEY", "")

        self.model_id = model or os.environ.get("OPENROUTER_MODEL") or "meta-llama/llama-3.3-70b-instruct"
        self.base_url = base_url or os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1"
        self.timeout = float(timeout)
        self.is_configured = bool(self.api_key and self.api_key.strip())
        self._client = None

        if self.is_configured:
            try:
                from openai import OpenAI
                self._client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.timeout)
            except ImportError:
                self.is_configured = False
            except Exception:
                self.is_configured = False

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> GenerationResult:
        """Sends chat completion request and returns normalized GenerationResult."""
        if not self.is_configured or self._client is None:
            raise ProviderError(
                code=ErrorCode.UNCONFIGURED,
                message="OpenRouter provider is unconfigured. Set OPENROUTER_API_KEY.",
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t0 = time.perf_counter()
        try:
            resp = self._client.chat.completions.create(
                model=self.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.timeout,
            )
            t1 = time.perf_counter()
            latency_ms = round((t1 - t0) * 1000, 3)

            if not resp.choices or not resp.choices[0].message:
                raise ProviderError(
                    code=ErrorCode.PROCESS_FAILED,
                    message="OpenRouter returned empty completion choices.",
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                )

            choice = resp.choices[0]
            usage = getattr(resp, "usage", None)

            return GenerationResult(
                text=choice.message.content or "",
                provider_id=self.provider_id,
                model_id=self.model_id,
                latency_ms=latency_ms,
                prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
                completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
                finish_reason=choice.finish_reason,
            )

        except ProviderError:
            raise
        except Exception as e:
            err_msg = str(e).lower()
            code = ErrorCode.NETWORK_ERROR
            if "auth" in err_msg or "api key" in err_msg or "401" in err_msg:
                code = ErrorCode.AUTH_REQUIRED
            elif "rate" in err_msg or "429" in err_msg:
                code = ErrorCode.RATE_LIMITED
            elif "timeout" in err_msg:
                code = ErrorCode.TIMEOUT

            raise ProviderError(
                code=code,
                message=f"OpenRouter generation failed: {e}",
                details={"model": self.model_id},
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2000,
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
        )

        cleaned_json = extract_json_from_text(gen_result.text)

        try:
            return response_model.model_validate_json(cleaned_json)
        except ValidationError as ve:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Model output violated expected schema {response_model.__name__}: {ve}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json, "errors": ve.errors()},
                provider_id=self.provider_id,
                model_id=self.model_id,
            )
        except Exception as e:
            raise ProviderError(
                code=ErrorCode.SCHEMA_VIOLATION,
                message=f"Failed to parse JSON response for {response_model.__name__}: {e}",
                details={"raw_text": gen_result.text, "cleaned_json": cleaned_json},
                provider_id=self.provider_id,
                model_id=self.model_id,
            )

    def health_check(self) -> ProviderHealth:
        """Checks API configuration and endpoint reachability."""
        if not self.is_configured:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.UNCONFIGURED,
                latency_ms=0.0,
                message="OpenRouter provider is unconfigured (OPENROUTER_API_KEY missing).",
            )

        try:
            t0 = time.perf_counter()
            res = self.generate_text(prompt="Ping", max_tokens=5, temperature=0.1)
            t1 = time.perf_counter()
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=True,
                status_code=ErrorCode.UNKNOWN,
                latency_ms=round((t1 - t0) * 1000, 3),
                message="OpenRouter API operational.",
                details={"model": self.model_id},
            )
        except Exception as e:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                healthy=False,
                status_code=ErrorCode.NETWORK_ERROR,
                latency_ms=0.0,
                message=f"OpenRouter probe failed: {e}",
            )
