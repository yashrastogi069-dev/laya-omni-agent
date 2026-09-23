"""
omni_engine.skills.registry
===========================
Canonical thread-safe SkillRegistry for the standalone LAYA Omni Agent.

Invariants:
- Zero Dangling Capabilities: Every required/optional capability in a SkillManifest
  must exist in the CapabilityRegistry.
- Policy Floor Enforcement: A skill cannot declare a weaker autonomy profile than its
  constituent required capabilities.
- Thread-safe access with fine-grained lock scoping.
- Fast intent matching for System 1 and Hierarchical Router integration.
"""

import copy
import re
import threading
from typing import Any, Dict, List, Optional, Set, Tuple

from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.enums import AutonomyProfile, ConfirmationPolicy
from omni_engine.contracts.skill import HIGH_RISK_ACTION_CLASSES, SkillManifest

AUTONOMY_RANK: Dict[AutonomyProfile, int] = {
    AutonomyProfile.ADVISOR: 1,
    AutonomyProfile.SAFE_ASSISTANT: 2,
    AutonomyProfile.LOCAL_OPERATOR: 3,
    AutonomyProfile.TRUSTED_OPERATOR: 4,
    AutonomyProfile.WORKFLOW_AUTHORIZED: 5,
}


class SkillRegistry:
    """Thread-safe canonical registry managing reusable SkillManifest specifications."""

    def __init__(self, capability_registry: Optional[CapabilityRegistry] = None) -> None:
        self._lock = threading.RLock()
        self._skills: Dict[str, SkillManifest] = {}
        self._capability_registry = capability_registry

    def _get_capability_registry_under_lock(self) -> CapabilityRegistry:
        """Retrieves or lazily constructs canonical CapabilityRegistry under lock."""
        if self._capability_registry is None:
            from omni_engine.capabilities.definitions import build_canonical_registry
            self._capability_registry = build_canonical_registry()
        return self._capability_registry

    def register(self, manifest: SkillManifest) -> None:
        """Registers a SkillManifest after validating capability parity and policy floors.
        
        Raises:
            ValueError: If duplicate skill_id, if any capability does not exist in
                        CapabilityRegistry, if constituent action classes are not declared,
                        or if autonomy profile / confirmation policy violates safety floors.
        """
        with self._lock:
            cap_reg = self._get_capability_registry_under_lock()

            # 1. Duplicate skill_id check
            if manifest.skill_id in self._skills:
                raise ValueError(
                    f"Skill '{manifest.skill_id}' is already registered in SkillRegistry. Duplicate IDs are forbidden."
                )

            # 2. Zero dangling capabilities & Constituent checks
            all_constituent_caps: Set[str] = set(manifest.required_capabilities) | set(manifest.optional_capabilities)
            if manifest.workflow_template:
                for step in manifest.workflow_template:
                    all_constituent_caps.add(step.capability_id)

            skill_autonomy_rank = AUTONOMY_RANK.get(manifest.applicable_autonomy, 1)

            # 2a. Validate all constituent capabilities exist in CapabilityRegistry
            for cap_id in sorted(list(all_constituent_caps)):
                if not cap_reg.has(cap_id):
                    raise ValueError(
                        f"Skill '{manifest.skill_id}' references capability '{cap_id}' which is NOT "
                        f"registered in CapabilityRegistry. Zero dangling capabilities invariant breached."
                    )
                spec = cap_reg.get_spec(cap_id)
                if spec is not None:
                    # Action class encompassment (Defect 3)
                    if spec.action_class not in manifest.action_classes:
                        raise ValueError(
                            f"Skill '{manifest.skill_id}' references capability '{cap_id}' with action class "
                            f"'{spec.action_class.value}', which is missing from the skill's declared action_classes."
                        )

                    # High-risk confirmation policy floor (Defect 3)
                    if spec.action_class in HIGH_RISK_ACTION_CLASSES and manifest.confirmation_policy == ConfirmationPolicy.NEVER:
                        raise ValueError(
                            f"Skill '{manifest.skill_id}' includes high-risk capability '{cap_id}' ({spec.action_class.value}) "
                            f"and cannot declare confirmation_policy=ConfirmationPolicy.NEVER."
                        )

            # 2b. Autonomy Profile Policy Floor across required capabilities
            for cap_id in manifest.required_capabilities:
                spec = cap_reg.get_spec(cap_id)
                if spec is not None:
                    cap_autonomy_rank = AUTONOMY_RANK.get(spec.minimum_autonomy_profile, 1)
                    if skill_autonomy_rank < cap_autonomy_rank:
                        raise ValueError(
                            f"Skill '{manifest.skill_id}' declares autonomy profile '{manifest.applicable_autonomy.value}', "
                            f"which is weaker than required capability '{cap_id}' profile '{spec.minimum_autonomy_profile.value}'."
                        )

            # Store deepcopy to guarantee registry state isolation
            self._skills[manifest.skill_id] = manifest.model_copy(deep=True)

    def unregister(self, skill_id: str) -> bool:
        """Removes a skill from the registry. Returns True if removed."""
        with self._lock:
            return bool(self._skills.pop(skill_id, None))

    def has(self, skill_id: str) -> bool:
        """Returns True if skill is registered."""
        with self._lock:
            return skill_id in self._skills

    def get(self, skill_id: str) -> Optional[SkillManifest]:
        """Retrieves SkillManifest by ID, returning an isolated deep copy."""
        with self._lock:
            manifest = self._skills.get(skill_id)
            return manifest.model_copy(deep=True) if manifest else None

    def list_all(self) -> List[str]:
        """Returns sorted list of all registered skill IDs."""
        with self._lock:
            return sorted(list(self._skills.keys()))

    def list_manifests(self, domain: Optional[str] = None) -> List[SkillManifest]:
        """Returns deep copies of SkillManifests, optionally filtered by domain."""
        with self._lock:
            if domain:
                return [s.model_copy(deep=True) for s in self._skills.values() if s.domain == domain]
            return [s.model_copy(deep=True) for s in self._skills.values()]

    def list_by_domain(self, domain: str) -> List[SkillManifest]:
        """Returns SkillManifests belonging to the specified domain."""
        return self.list_manifests(domain=domain)

    def find_by_intent(
        self,
        query: str,
        domain: Optional[str] = None,
        threshold: float = 0.3,
    ) -> List[Tuple[float, SkillManifest]]:
        """Finds candidate skills matching a user query based on intent patterns and description.
        
        Args:
            query: User natural language request.
            domain: Optional domain filter.
            threshold: Minimum relevance score to include in results (default 0.3).
            
        Returns:
            List of (score, SkillManifest) sorted descending by relevance.
        """
        if not query or not query.strip():
            return []

        q_lower = query.strip().lower()
        q_tokens = set(re.findall(r"\w+", q_lower))

        with self._lock:
            candidates: List[Tuple[float, SkillManifest]] = []

            for manifest in self._skills.values():
                if domain and manifest.domain != domain:
                    continue

                best_score = 0.0

                # 1. Exact or partial match against intent_patterns
                for pattern in manifest.intent_patterns:
                    p_lower = pattern.lower()
                    if p_lower in q_lower or q_lower in p_lower:
                        best_score = max(best_score, 0.95)
                    else:
                        p_tokens = set(re.findall(r"\w+", p_lower))
                        overlap = len(q_tokens.intersection(p_tokens))
                        if overlap:
                            ratio = overlap / max(1, len(p_tokens))
                            best_score = max(best_score, 0.5 + 0.45 * ratio)

                # 2. Match against name and description
                desc_text = f"{manifest.name} {manifest.description}".lower()
                desc_tokens = set(re.findall(r"\w+", desc_text))
                overlap_desc = len(q_tokens.intersection(desc_tokens))
                if overlap_desc:
                    ratio_desc = min(1.0, overlap_desc / 3.0)
                    best_score = max(best_score, 0.4 + 0.3 * ratio_desc)

                if best_score >= threshold:
                    candidates.append((round(best_score, 3), manifest.model_copy(deep=True)))

            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates

    def export_manifests(self) -> List[Dict[str, Any]]:
        """Exports all skill manifests as JSON-serializable dictionaries."""
        with self._lock:
            return [s.model_dump() for s in self._skills.values()]

    def count(self) -> int:
        """Returns total count of registered skills."""
        with self._lock:
            return len(self._skills)
