"""Skill Workflow Template Planner.

Derives deterministic execution DAGs directly from pre-defined SkillManifest workflow templates,
eliminating generative model invocations for known capability workflows (Checkpoint L12).
"""

from typing import Any, Dict, List, Optional

from ..capabilities.registry import CapabilityRegistry
from ..contracts.enums import IdempotencyClass, RetryPolicy
from ..contracts.plan import Plan, PlanStep, PlanType, PlanValidationError
from ..contracts.skill import SkillManifest, SkillStepTemplate
from .dag import DAGTopology


class SkillTemplatePlanner:
    """Instantiates structured execution plans from deterministic skill workflow templates."""

    def __init__(self, capability_registry: Optional[CapabilityRegistry] = None) -> None:
        self.capability_registry = capability_registry

    def can_plan_from_skill(self, skill: SkillManifest) -> bool:
        """Determines if the given skill has an actionable deterministic workflow template."""
        return skill.workflow_template is not None and len(skill.workflow_template) > 0

    def create_plan_from_skill(
        self,
        quest_id: str,
        goal: str,
        skill: SkillManifest,
        resolved_arguments: Optional[Dict[str, Any]] = None,
        timeout_budget_s: float = 300.0,
    ) -> Plan:
        """Derives a structured Plan directly from a SkillManifest's workflow template.
        
        Args:
            quest_id: Parent Quest ID.
            goal: User objective or task description.
            skill: The matched SkillManifest.
            resolved_arguments: Extracted user arguments to bind to step templates.
            timeout_budget_s: Overall timeout budget for the plan.
            
        Returns:
            A validated Plan with plan_type = PlanType.TEMPLATE_DERIVED.
            
        Raises:
            PlanValidationError: If skill has no workflow template or fails topological checks.
        """
        if not self.can_plan_from_skill(skill):
            raise PlanValidationError(
                f"Skill '{skill.skill_id}' has no workflow template and requires generative planning."
            )

        user_args = resolved_arguments or {}
        plan_steps: List[PlanStep] = []

        for step_tpl in skill.workflow_template:  # type: ignore
            # 1. Bind arguments
            step_args = step_tpl.default_args.copy() if step_tpl.default_args else {}

            # Apply explicit arg_mappings (e.g. {"query": "$inputs.query"})
            for target_param, source_expr in (step_tpl.arg_mappings or {}).items():
                if source_expr.startswith("$inputs."):
                    input_key = source_expr[len("$inputs."):]
                    if input_key in user_args:
                        step_args[target_param] = user_args[input_key]
                elif source_expr.startswith("$steps."):
                    # Dynamic inter-step references are preserved for runtime evaluation
                    step_args[target_param] = source_expr

            # Fallback direct parameter overlay if not specified in mappings
            for k, v in user_args.items():
                if k not in step_args:
                    step_args[k] = v

            # 2. Build PlanStep
            timeout_s = 60.0
            max_attempts = 3
            if self.capability_registry and self.capability_registry.has(step_tpl.capability_id):
                spec = self.capability_registry.get_spec(step_tpl.capability_id)
                if spec is not None:
                    if spec.retry_policy == RetryPolicy.NEVER or spec.idempotency_class == IdempotencyClass.NON_IDEMPOTENT:
                        max_attempts = 1
                    if getattr(spec, "timeout_seconds", None):
                        timeout_s = spec.timeout_seconds

            plan_step = PlanStep(
                step_id=step_tpl.step_id,
                capability_id=step_tpl.capability_id,
                intent=step_tpl.description,
                arguments=step_args,
                dependencies=list(step_tpl.depends_on or []),
                timeout_s=timeout_s,
                max_attempts=max_attempts,
                can_fail_silently=step_tpl.can_fail_silently,
                metadata={
                    "skill_id": skill.skill_id,
                    "verification_rule": step_tpl.verification_rule,
                },
            )
            plan_steps.append(plan_step)

        # 3. Sort topologically
        sorted_steps = DAGTopology.topological_sort(plan_steps)
        max_depth = DAGTopology.compute_plan_depth(sorted_steps)

        return Plan(
            quest_id=quest_id,
            goal=goal,
            plan_type=PlanType.TEMPLATE_DERIVED,
            steps=sorted_steps,
            max_depth=max(max_depth, 1),
            timeout_budget_s=timeout_budget_s,
            skill_id=skill.skill_id,
            metadata={
                "template_source": "skill_manifest",
                "skill_name": skill.name,
                "step_count": len(sorted_steps),
            },
        )
