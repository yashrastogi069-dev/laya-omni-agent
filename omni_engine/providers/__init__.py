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

__all__ = [
    "GenerationResult",
    "GenerativeProvider",
    "JevProvider",
    "LayaProvider",
    "OpenRouterProvider",
    "ProviderError",
    "ProviderHealth",
    "SystemOneProvider",
    "extract_json_from_text",
    "get_shared_laya_router",
]
