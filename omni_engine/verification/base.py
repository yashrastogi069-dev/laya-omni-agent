"""
omni_engine.verification.base
=============================
Abstract base classes for deterministic outcome verifiers (Checkpoint L15).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from omni_engine.contracts.objective import RequirementItem
from omni_engine.contracts.quest import QuestStep
from omni_engine.contracts.verification import (
    RequirementVerification,
    RequirementVerificationStatus,
    VerificationCheckResult,
    CheckType,
)


class BaseVerifier(ABC):
    """Abstract contract for an evidence-based outcome verifier."""

    verifier_id: str = "base"
    verifier_version: str = "1.0.0"

    @abstractmethod
    def can_verify(self, requirement: RequirementItem, capability_id: Optional[str] = None) -> bool:
        """Returns True if this verifier has jurisdiction over the requirement or capability domain."""
        pass

    @abstractmethod
    def verify(
        self,
        requirement: RequirementItem,
        step: Optional[QuestStep] = None,
        receipt: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RequirementVerification:
        """Evaluates physical and receipt evidence to produce a strongly typed verification record."""
        pass
