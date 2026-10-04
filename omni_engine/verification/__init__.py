"""
omni_engine.verification
========================
Evidence-based completion verifier, deterministic verifier registry, and
requirement-level objective verification engine (Checkpoint L15).
"""

from .base import BaseVerifier
from .verifiers import (
    FileVerifier,
    ProcessVerifier,
    DesktopVerifier,
    BrowserVerifier,
    N8nVerifier,
    ResearchVerifier,
    CommandVerifier,
)
from .registry import VerificationRegistry
from .store import VerificationStore
from .engine import ObjectiveCompletionEngine

__all__ = [
    "BaseVerifier",
    "FileVerifier",
    "ProcessVerifier",
    "DesktopVerifier",
    "BrowserVerifier",
    "N8nVerifier",
    "ResearchVerifier",
    "CommandVerifier",
    "VerificationRegistry",
    "VerificationStore",
    "ObjectiveCompletionEngine",
]
