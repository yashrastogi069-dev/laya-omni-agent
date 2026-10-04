"""
omni_engine.verification.registry
=================================
Central registry for evidence-based outcome verifiers (Checkpoint L15).
"""

from typing import Any, Dict, List, Optional
import time

from omni_engine.contracts.objective import RequirementItem
from omni_engine.contracts.quest import QuestStep
from omni_engine.contracts.verification import (
    CheckType,
    RequirementVerification,
    RequirementVerificationStatus,
    VerificationCheckResult,
)
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


class VerificationRegistry:
    """Registry coordinating specialized outcome verifiers."""

    def __init__(self, register_defaults: bool = True):
        self._verifiers: List[BaseVerifier] = []
        if register_defaults:
            self._register_defaults()

    def _register_defaults(self) -> None:
        """Registers the canonical domain verifiers in priority order."""
        # File verifier is first priority for physical artifact verification
        self.register(FileVerifier())
        self.register(BrowserVerifier())
        self.register(DesktopVerifier())
        self.register(ProcessVerifier())
        self.register(N8nVerifier())
        self.register(ResearchVerifier())
        self.register(CommandVerifier())

    def register(self, verifier: BaseVerifier) -> None:
        """Registers a verifier instance."""
        self._verifiers.append(verifier)

    def find_verifier(
        self,
        requirement: RequirementItem,
        capability_id: Optional[str] = None,
    ) -> Optional[BaseVerifier]:
        """Finds the most specific verifier capable of evaluating the requirement."""
        for v in self._verifiers:
            if v.can_verify(requirement, capability_id):
                return v
        return None

    def verify_requirement(
        self,
        requirement: RequirementItem,
        step: Optional[QuestStep] = None,
        receipt: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RequirementVerification:
        """Routes requirement verification to the appropriate verifier."""
        cap_id = step.capability_id if step else None
        verifier = self.find_verifier(requirement, cap_id)

        if verifier is not None:
            return verifier.verify(requirement, step, receipt, context)

        # Fallback generic verifier: requires non-failing execution receipt
        now = time.time()
        has_receipt = bool(receipt or (step and step.status.value == "completed"))
        check = VerificationCheckResult(
            check_name="generic_execution_receipt",
            check_type=CheckType.STRUCTURED_RECEIPT,
            passed=has_receipt,
            evidence={"receipt": receipt, "step_status": step.status.value if step else None},
            details=None if has_receipt else "No execution receipt or completed step found.",
            timestamp=now,
        )
        return RequirementVerification(
            requirement_id=requirement.requirement_id,
            description=requirement.description,
            mandatory=requirement.mandatory,
            status=RequirementVerificationStatus.VERIFIED_SUCCESS if has_receipt else RequirementVerificationStatus.VERIFIED_FAILURE,
            evidence_refs=[str(step.step_id)] if step else [],
            verifier_id="generic_fallback_verifier",
            physical_checks=[check],
            failure_reason=None if has_receipt else "Generic execution receipt was missing or failed.",
            repairable=not has_receipt,
            timestamp=now,
        )
