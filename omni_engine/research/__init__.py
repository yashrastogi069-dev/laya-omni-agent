"""
omni_engine.research
====================
Deep Evidence-Grounded Research Engine for Autonomous Investigation.
"""

from .engine import DeepResearchEngine, compute_3gram_jaccard
from .fetcher import PageFetcher, canonicalize_url, extract_domain
from .sanitizer import clean_web_text, sanitize_untrusted_web_content

__all__ = [
    "DeepResearchEngine",
    "compute_3gram_jaccard",
    "PageFetcher",
    "canonicalize_url",
    "extract_domain",
    "clean_web_text",
    "sanitize_untrusted_web_content",
]
