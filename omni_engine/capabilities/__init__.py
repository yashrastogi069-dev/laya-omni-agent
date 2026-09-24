"""
omni_engine.capabilities
========================
Canonical capability substrate package for LAYA Omni Agent.

Provides strongly typed CapabilityRegistry, pure CapabilitySpecs,
adapters, and execution boundaries for all 23 source capabilities.
"""

from .registry import CapabilityRegistry
from .definitions import (
    CANONICAL_SPECS,
    DEEP_RESEARCH_SPEC,
    REAL_CAPABILITY_SPECS,
    build_canonical_registry,
    build_real_capability_registry,
    make_deep_research_adapter,
    register_deep_research_capability,
)
from .adapters import (
    intercept_legacy_error_string,
    make_adapter,
    make_file_write_adapter,
    make_http_api_adapter,
    make_download_file_adapter,
    make_clipboard_adapter,
    make_inspect_data_adapter,
)

__all__ = [
    "CapabilityRegistry",
    "CANONICAL_SPECS",
    "DEEP_RESEARCH_SPEC",
    "REAL_CAPABILITY_SPECS",
    "build_canonical_registry",
    "build_real_capability_registry",
    "intercept_legacy_error_string",
    "make_adapter",
    "make_deep_research_adapter",
    "register_deep_research_capability",
    "make_file_write_adapter",
    "make_http_api_adapter",
    "make_download_file_adapter",
    "make_clipboard_adapter",
    "make_inspect_data_adapter",
]

