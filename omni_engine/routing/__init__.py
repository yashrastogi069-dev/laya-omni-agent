"""
omni_engine.routing
===================
Hierarchical capability routing package for the standalone LAYA Omni Agent.
"""

from .router import (
    DOMAIN_KEYWORD_MAP,
    CAPABILITY_PIN_MAP,
    HierarchicalRouter,
)

__all__ = [
    "DOMAIN_KEYWORD_MAP",
    "CAPABILITY_PIN_MAP",
    "HierarchicalRouter",
]
