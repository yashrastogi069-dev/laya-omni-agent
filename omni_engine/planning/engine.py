"""Structured DAG Planner Engine.

Orchestrates template-first skill workflow planning and generative fallback,
enforcing topological validation, step bounds, and seamless attachment to persisted Quests (Checkpoint L12).
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from ..capabilities.registry import CapabilityRegistry
from ..contracts.enums import ActionClass, AutonomyProfile
from ..contracts.plan import Plan, PlanError, PlanStep, PlanType, PlanValidationError
from ..contracts.quest import Quest, QuestStep, StepStatus
from ..contracts.routing import RouteDecision
from ..contracts.skill import SkillManifest
from ..providers.base import GenerativeProvider
from ..quest.engine import QuestEngine
from ..skills.registry import SkillRegistry
from .dag import DAGTopology
from .generative_planner import GenerativePlanner
from .template_planner import SkillTemplatePlanner


class StructuredDAGPlanner:
    """Master orchestrator for Structured DAG Planning in LAYA Autonomous V2.
    
    Invariants:
    1. Deterministic Control (Invariant 1): DAG structures and attachment are strictly deterministic.
    2. Template-First Precedence (Invariant 3): Reusable Skill workflow templates are prioritized
       before invoking expensive generative models.
    3. Topological Verification: Plans are validated to be acyclic, bounded in depth, and free of dangling dependencies.
    """

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
        generative_provider: Optional[GenerativeProvider] = None,
    ) -> None:
        """Initialize StructuredDAGPlanner.
        
        Args:
            skill_registry: SkillRegistry instance containing canonical skill manifests.
            capability_registry: CapabilityRegistry instance providing capability metadata.
            generative_provider: GenerativeProvider instance for fallback synthesis.
        """
        self.skill_registry = skill_registry
        self.capability_registry = capability_registry
        self.template_planner = SkillTemplatePlanner(capability_registry=capability_registry)
        self.generative_planner = GenerativePlanner(
            provider=generative_provider,
            capability_registry=capability_registry,
        )

    def create_plan(
        self,
        quest_id: str,
        goal: str,
        skill_id: Optional[str] = None,
        route_decision: Optional[RouteDecision] = None,
        arguments: Optional[Dict[str, Any]] = None,
        timeout_budget_s: float = 300.0,
        max_steps: int = 10,
        max_depth: int = 5,
        mock_generative_response: Optional[str] = None,
    ) -> Plan:
        """Creates a validated execution Plan using Template-First Precedence.
        
        Args:
            quest_id: Parent Quest ID.
            goal: User goal or objective description.
            skill_id: Explicit target skill ID if known.
            route_decision: Optional RouteDecision from router.
            arguments: Extracted user arguments to bind to plan steps.
            timeout_budget_s: Wall-clock timeout budget for plan.
            max_steps: Upper bound on total steps in plan.
            max_depth: Upper bound on dependency depth.
            mock_generative_response: Mock string for generative planner testing.
            
        Returns:
            A validated Plan instance.
            
        Raises:
            PlanError: If planning fails or violated constraints.
        """
        target_skill_id = skill_id or (
            route_decision.selected_skill if route_decision and hasattr(route_decision, "selected_skill") else None
        ) or (
            route_decision.metadata.get("skill_id") if route_decision else None
        )
        resolved_args = arguments or (route_decision.metadata.get("resolved_arguments") if route_decision else {})

        # Stage 1: Template-First Precedence (Invariant 3)
        if target_skill_id and self.skill_registry and self.skill_registry.has(target_skill_id):
            skill = self.skill_registry.get(target_skill_id)
            if skill and self.template_planner.can_plan_from_skill(skill):
                plan = self.template_planner.create_plan_from_skill(
                    quest_id=quest_id,
                    goal=goal,
                    skill=skill,
                    resolved_arguments=resolved_args,
                    timeout_budget_s=timeout_budget_s,
                )
                self._verify_bounds(plan, max_steps, max_depth)
                return plan

        # Stage 2: Generative Planning Fallback (Novel/Unmatched Objectives)
        allowed_caps = None
        if route_decision and route_decision.candidates:
            allowed_caps = [c.capability_id for c in route_decision.candidates]

        plan = self.generative_planner.synthesize_plan(
            quest_id=quest_id,
            goal=goal,
            allowed_capabilities=allowed_caps,
            timeout_budget_s=timeout_budget_s,
            max_steps=max_steps,
            max_depth=max_depth,
            mock_response=mock_generative_response,
        )
        self._verify_bounds(plan, max_steps, max_depth)
        return plan

    def _verify_bounds(self, plan: Plan, max_steps: int, max_depth: int) -> None:
        """Verifies plan step count and DAG depth do not exceed configured limits."""
        if len(plan.steps) > max_steps:
            raise PlanValidationError(
                f"Plan step count ({len(plan.steps)}) exceeds maximum allowed limit ({max_steps})."
            )
        depth = DAGTopology.compute_plan_depth(plan.steps)
        if depth > max_depth:
            raise PlanValidationError(
                f"Plan DAG depth ({depth}) exceeds maximum allowed depth limit ({max_depth})."
            )

    def attach_to_quest(
        self,
        quest_engine: QuestEngine,
        plan: Plan,
    ) -> Quest:
        """Attaches a planned DAG to an existing persisted Quest, transitioning it to PLANNED.
        
        Args:
            quest_engine: QuestEngine instance.
            plan: The structured Plan to attach.
            
        Returns:
            The updated Quest in PLANNED status.
            
        Raises:
            PlanError: If attachment fails.
        """
        quest_steps: List[QuestStep] = []
        for p_step in plan.steps:
            # Determine action_class from capability registry if available
            action_class = ActionClass.LOCAL_UPDATE
            if self.capability_registry and self.capability_registry.has(p_step.capability_id):
                spec = self.capability_registry.get_spec(p_step.capability_id)
                if spec is not None:
                    action_class = spec.action_class

            q_step = QuestStep(
                step_id=p_step.step_id,
                quest_id=plan.quest_id,
                capability_id=p_step.capability_id,
                action_class=action_class,
                intent=p_step.intent,
                arguments=p_step.arguments,
                dependencies=list(p_step.dependencies),
                status=StepStatus.PENDING,
                timeout_s=p_step.timeout_s,
                max_attempts=p_step.max_attempts,
                can_fail_silently=p_step.can_fail_silently,
                metadata=dict(p_step.metadata),
            )
            quest_steps.append(q_step)

        # Compute plan hash and provenance (AUDIT-08 / L14.2-F)
        plan_hash = plan.compute_hash()
        plan_provenance = {
            "plan_id": plan.plan_id,
            "plan_type": plan.plan_type.value,
            "plan_hash": plan_hash,
            "goal": plan.goal,
            "timeout_budget_s": plan.timeout_budget_s,
            "skill_id": plan.skill_id,
            "metadata": dict(plan.metadata),
        }

        # Attach plan to quest via QuestEngine
        updated_quest = quest_engine.attach_plan(
            quest_id=plan.quest_id,
            steps=quest_steps,
            metadata={
                "plan_hash": plan_hash,
                "plan_provenance": plan_provenance,
            },
        )
        return updated_quest

    def validate_plan(
        self,
        plan: Plan,
        autonomy_profile: Optional[AutonomyProfile] = None,
        max_steps: int = 20,
        max_depth: int = 6,
    ) -> Any:
        """Validates a planned DAG through the 10-pass DeterministicPlanValidator firewall."""
        from .validator import DeterministicPlanValidator
        validator = DeterministicPlanValidator(
            capability_registry=self.capability_registry,
        )
        return validator.validate(
            plan=plan,
            autonomy_profile=autonomy_profile,
            max_steps=max_steps,
            max_depth=max_depth,
        )

