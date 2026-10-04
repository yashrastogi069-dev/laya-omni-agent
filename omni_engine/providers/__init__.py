"""
omni_engine.providers
=====================
Vendor-independent provider foundations for System 1 and Generative models.
"""

from .base import (
    GenerationResult,
    GenerativeProvider,
    ProviderError,
    ProviderHealth,
    SystemOneProvider,
)
from .system1 import JevProvider, LayaProvider, get_shared_laya_router
from .generative import OpenRouterProvider, extract_json_from_text
from .broker import SystemOneBroker
from .router import GenerativeRouter, MockGenerativeProvider
from .cloud import (
    AnthropicProvider,
    DeepSeekProvider,
    DirectOpenAIProvider,
    build_standard_generative_router,
    sanitize_provider_error,
)

__all__ = [
    "AnthropicProvider",
    "DeepSeekProvider",
    "DirectOpenAIProvider",
    "GenerationResult",
    "GenerativeProvider",
    "GenerativeRouter",
    "JevProvider",
    "LayaProvider",
    "MockGenerativeProvider",
    "OpenRouterProvider",
    "ProviderError",
    "ProviderHealth",
    "SystemOneBroker",
    "SystemOneProvider",
    "build_standard_generative_router",
    "extract_json_from_text",
    "get_shared_laya_router",
    "sanitize_provider_error",
]
