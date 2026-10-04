"""Structured DAG Planner Engine.

Orchestrates template-first skill workflow planning and generative fallback,
enforcing topological validation, step bounds, and seamless attachment to persisted Quests (Checkpoint L12).
"""

import hashlib
import json
from typing import Any, Dict, List, Optional

from ..capabilities.registry import CapabilityRegistry
from ..contracts.enums import ActionClass, AutonomyProfile
from ..contracts.objective import (
    ObjectiveSpec,
    RequirementCoverageState,
    RequirementItem,
)
from ..contracts.plan import Plan, PlanError, PlanStep, PlanType, PlanValidationError
from ..contracts.quest import Quest, QuestStep, StepStatus
from ..contracts.routing import RouteDecision
from ..contracts.skill import SkillManifest
from ..providers.base import GenerativeProvider
from ..quest.engine import QuestEngine
from ..skills.registry import SkillRegistry
from .dag import DAGTopology
from .decomposer import ObjectiveDecomposer
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

        # Stage 0: Objective Decomposition & Clause Isolation (PRACT-022, PRACT-036)
        decomposer = ObjectiveDecomposer()
        objective_spec = decomposer.decompose(goal)

        # Stage 1: Template-First Precedence (Invariant 3)
        if target_skill_id and self.skill_registry and self.skill_registry.has(target_skill_id):
            skill = self.skill_registry.get(target_skill_id)
            if skill and self.template_planner.can_plan_from_skill(skill):
                base_plan = self.template_planner.create_plan_from_skill(
                    quest_id=quest_id,
                    goal=goal,
                    skill=skill,
                    resolved_arguments=resolved_args,
                    timeout_budget_s=timeout_budget_s,
                )
                plan = self._augment_plan_for_objective(base_plan, objective_spec, resolved_args)
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
        plan = self._augment_plan_for_objective(plan, objective_spec, resolved_args)
        self._verify_bounds(plan, max_steps, max_depth)
        return plan

    def _augment_plan_for_objective(
        self,
        base_plan: Plan,
        objective_spec: ObjectiveSpec,
        resolved_args: Dict[str, Any],
    ) -> Plan:
        """Augments a base template plan with steps covering any uncovered requirements."""
        if not objective_spec.is_compound or not objective_spec.requirements:
            return base_plan

        steps = list(base_plan.steps)
        existing_caps = {s.capability_id for s in steps}

        # 1. Map existing steps to requirements
        for req in objective_spec.requirements:
            for s in steps:
                if req.domain == "system" and s.capability_id in ("system_diagnostics", "list_processes"):
                    req.mark_covered_by(s.step_id)
                elif req.domain == "browser" and "navigate" in req.description.lower() and s.capability_id == "visual_browse":
                    req.mark_covered_by(s.step_id)
                elif req.domain == "browser" and "screenshot" in req.description.lower() and s.capability_id == "browser_screenshot":
                    req.mark_covered_by(s.step_id)
                elif req.domain == "repository" and s.capability_id in ("directory_tree", "search_code", "git_status"):
                    req.mark_covered_by(s.step_id)
                elif req.domain == "web" and s.capability_id in ("web_search", "scrape_url", "deep_research", "research.deep"):
                    req.mark_covered_by(s.step_id)
                elif req.domain == "file" and s.capability_id in ("file_read", "file_write"):
                    req.mark_covered_by(s.step_id)
                elif req.domain in ("automation", "desktop") and s.capability_id in ("n8n.list_workflows", "n8n_list_workflows", "n8n.get_workflow"):
                    req.mark_covered_by(s.step_id)
                elif req.domain in ("automation", "desktop") and s.capability_id in ("desktop.service_health", "service_health"):
                    req.mark_covered_by(s.step_id)

        # 2. Check for uncovered requirements and augment
        uncovered = objective_spec.uncovered_mandatory_requirements()
        for req in uncovered:
            # File save augmentation (e.g. Prompt A, E)
            if req.domain == "file" or "save" in req.description.lower():
                file_path = resolved_args.get("filepath") or resolved_args.get("file_path")
                if not file_path:
                    decomposer = ObjectiveDecomposer()
                    _, file_path, _ = decomposer._extract_file_save(objective_spec.objective)
                if not file_path:
                    file_path = "output_report.txt"

                step_num = len(steps) + 1
                save_step_id = f"step_{step_num}_save_file"
                last_step_id = steps[-1].step_id if steps else "step_0"

                save_step = PlanStep(
                    step_id=save_step_id,
                    capability_id="file_write",
                    intent=f"Save report to file {file_path}",
                    arguments={
                        "filepath": file_path,
                        "content": f"$steps.{last_step_id}.output",
                    },
                    dependencies=[last_step_id] if steps else [],
                    timeout_s=15.0,
                    metadata={"requirement_id": req.requirement_id},
                )
                steps.append(save_step)
                existing_caps.add("file_write")
                req.mark_covered_by(save_step_id)

            # Browser screenshot augmentation (e.g. Prompt B)
            elif req.domain == "browser" and "screenshot" in req.description.lower() and "browser_screenshot" not in existing_caps:
                target_url = resolved_args.get("url") or "https://www.python.org"
                for s in steps:
                    if s.capability_id == "visual_browse" and "url" in s.arguments:
                        target_url = s.arguments["url"]
                        break

                step_num = len(steps) + 1
                ss_step_id = f"step_{step_num}_screenshot"
                last_step_id = steps[-1].step_id if steps else "step_0"

                ss_step = PlanStep(
                    step_id=ss_step_id,
                    capability_id="browser_screenshot",
                    intent="Capture visual verification screenshot",
                    arguments={"url": target_url},
                    dependencies=[last_step_id] if steps else [],
                    timeout_s=15.0,
                    metadata={"requirement_id": req.requirement_id},
                )
                steps.append(ss_step)
                existing_caps.add("browser_screenshot")
                req.mark_covered_by(ss_step_id)

            # n8n service health check augmentation (e.g. Prompt G)
            elif (req.domain in ("automation", "desktop") or "port 5678" in req.description.lower()) and "desktop.service_health" not in existing_caps and "service_health" not in existing_caps:
                step_num = len(steps) + 1
                health_step_id = f"step_{step_num}_n8n_health"
                last_step_id = steps[-1].step_id if steps else "step_0"

                health_step = PlanStep(
                    step_id=health_step_id,
                    capability_id="desktop.service_health",
                    intent="Verify n8n service health on port 5678",
                    arguments={"port": 5678, "service_name": "n8n"},
                    dependencies=[last_step_id] if steps else [],
                    timeout_s=10.0,
                    metadata={"requirement_id": req.requirement_id},
                )
                steps.append(health_step)
                existing_caps.add("desktop.service_health")
                req.mark_covered_by(health_step_id)

            # n8n list workflows augmentation (e.g. Prompt G)
            elif req.domain in ("automation", "desktop") and "workflows" in req.description.lower() and "n8n.list_workflows" not in existing_caps and "n8n_list_workflows" not in existing_caps:
                step_num = len(steps) + 1
                list_step_id = f"step_{step_num}_list_workflows"
                last_step_id = steps[-1].step_id if steps else "step_0"

                list_step = PlanStep(
                    step_id=list_step_id,
                    capability_id="n8n.list_workflows",
                    intent="List n8n automation workflows",
                    arguments={},
                    dependencies=[last_step_id] if steps else [],
                    timeout_s=15.0,
                    metadata={"requirement_id": req.requirement_id},
                )
                steps.append(list_step)
                existing_caps.add("n8n.list_workflows")
                req.mark_covered_by(list_step_id)

            # Synthesis step (e.g. Prompt A, C, D, F, G)
            elif req.domain == "synthesis":
                req.mark_covered_by(steps[-1].step_id if steps else "step_0")

        # Record coverage metadata in plan
        meta = dict(base_plan.metadata)
        meta["objective_spec"] = objective_spec.model_dump()
        meta["coverage_state"] = objective_spec.overall_coverage.value
        meta["is_augmented"] = len(steps) > len(base_plan.steps)

        plan_type = base_plan.plan_type
        if meta["is_augmented"] and base_plan.plan_type == PlanType.TEMPLATE_DERIVED:
            plan_type = PlanType.COMPOSITE

        return Plan(
            plan_id=base_plan.plan_id,
            quest_id=base_plan.quest_id,
            goal=base_plan.goal,
            plan_type=plan_type,
            steps=steps,
            timeout_budget_s=base_plan.timeout_budget_s,
            skill_id=base_plan.skill_id,
            metadata=meta,
        )

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
            "schema_version": getattr(plan, "schema_version", "2.0"),
            "plan_version": getattr(plan, "plan_version", 1),
            "validator_version": getattr(plan, "validator_version", None),
            "validation_hash": getattr(plan, "validation_hash", None),
            "validation_receipt": getattr(plan, "validation_receipt", None),
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

