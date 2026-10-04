"""Controlled Replanner & Recovery Loop for LAYA Autonomous V2 Runtime.

Orchestrates blast-radius calculation, preservation of completed step receipts,
anti-oscillation budgeting, and sub-DAG grafting (Checkpoint L16).
Enforces Invariant 1 (Deterministic Control), Invariant 5 (Validated DAG Execution),
and Invariant 6 (Evidence-Based Completion).
"""

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Set

from ..capabilities.definitions import build_real_capability_registry
from ..capabilities.registry import CapabilityRegistry
from ..contracts.enums import ActionClass, AutonomyProfile
from ..contracts.plan import Plan, PlanError, PlanStep, PlanType
from ..contracts.quest import Quest, StepStatus
from ..contracts.replanning import (
    ReplanRequest,
    ReplanResult,
    ReplanScope,
    ReplanTrigger,
)
from ..providers.base import GenerativeProvider
from ..skills.registry import SkillRegistry
from .validator import DeterministicPlanValidator

logger = logging.getLogger(__name__)


DEFAULT_CAPABILITY_FALLBACKS: Dict[str, str] = {
    "web_search": "deep_research",
    "scrape_url": "visual_browse",
    "visual_browse": "browser.interact",
    "browser_screenshot": "desktop_screenshot",
    "desktop_screenshot": "browser_screenshot",
    "launch_app": "desktop.launch_app",
    "list_processes": "system_diagnostics",
    "ping_test": "desktop.service_health",
    "powershell": "system_diagnostics",
}


class ControlledReplanner:
    """Deterministic, bounded replanning engine with blast-radius containment and receipt preservation."""

    def __init__(
        self,
        capability_registry: Optional[CapabilityRegistry] = None,
        skill_registry: Optional[SkillRegistry] = None,
        generative_provider: Optional[GenerativeProvider] = None,
        plan_validator: Optional[DeterministicPlanValidator] = None,
        max_replans: int = 3,
        max_replan_depth: int = 2,
    ) -> None:
        self.capability_registry = capability_registry or build_real_capability_registry()
        self.skill_registry = skill_registry
        self.generative_provider = generative_provider
        self.plan_validator = plan_validator or DeterministicPlanValidator(
            capability_registry=self.capability_registry,
            allow_silent_failure=True,
        )
        self.max_replans = max_replans
        self.max_replan_depth = max_replan_depth

    # =========================================================================
    # Blast Radius Analysis
    # =========================================================================

    def compute_blast_radius(self, steps: List[PlanStep], failed_step_id: str) -> Set[str]:
        """Computes the blast radius: the failed step and all transitive downstream dependents.
        
        Args:
            steps: All PlanStep objects in the current plan.
            failed_step_id: The ID of the failed step.
            
        Returns:
            A set of step IDs in the blast radius (including failed_step_id).
        """
        blast_radius: Set[str] = {failed_step_id}

        # Build forward adjacency map: parent -> children
        children_map: Dict[str, List[str]] = {s.step_id: [] for s in steps}
        for s in steps:
            for dep in s.dependencies:
                if dep in children_map:
                    children_map[dep].append(s.step_id)

        # Transitive BFS traversal
        queue: List[str] = [failed_step_id]
        while queue:
            curr = queue.pop(0)
            for child_id in children_map.get(curr, []):
                if child_id not in blast_radius:
                    blast_radius.add(child_id)
                    queue.append(child_id)

        return blast_radius

    # =========================================================================
    # Strategy Synthesis
    # =========================================================================

    def _find_fallback_capability(self, failed_cap_id: str) -> Optional[str]:
        """Finds a viable alternative capability from canonical fallbacks or aliases."""
        target = DEFAULT_CAPABILITY_FALLBACKS.get(failed_cap_id)
        if target and self.capability_registry.has(target):
            return target
        return None

    def _synthesize_replacement_steps(
        self,
        failed_step: PlanStep,
        attempt_num: int,
        preserved_step_ids: Set[str],
        previous_failures: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[PlanStep]:
        """Synthesizes alternative steps to replace the failed step."""
        # 1. Deterministic Fallback Strategy
        fallback_cap = self._find_fallback_capability(failed_step.capability_id)
        
        # Check if fallback capability itself already failed in previous attempts
        if fallback_cap:
            already_failed = any(
                f.get("capability_id") == fallback_cap for f in previous_failures
            )
            if already_failed:
                fallback_cap = None

        if fallback_cap:
            # Adapt arguments if needed
            args = dict(failed_step.arguments or {})
            if failed_step.capability_id == "web_search" and fallback_cap == "deep_research":
                if "query" in args and "topic" not in args:
                    args["topic"] = args["query"]
            elif failed_step.capability_id == "scrape_url" and fallback_cap == "visual_browse":
                if "url" in args:
                    args["action"] = "navigate"

            replacement_step = PlanStep(
                step_id=f"{failed_step.step_id}_alt{attempt_num}",
                capability_id=fallback_cap,
                intent=f"Alternative recovery step for '{failed_step.intent}' using '{fallback_cap}'",
                arguments=args,
                dependencies=[d for d in failed_step.dependencies if d in preserved_step_ids],
                timeout_s=failed_step.timeout_s,
                max_attempts=1,
                can_fail_silently=False,
                metadata={
                    **failed_step.metadata,
                    "replanned_from_step": failed_step.step_id,
                    "replan_attempt": attempt_num,
                    "strategy": "deterministic_fallback",
                },
            )
            return [replacement_step]

        # 2. Generative Fallback Synthesis
        if self.generative_provider is not None:
            prompt = (
                f"You are the LAYA Controlled Replanner. A plan step failed.\n"
                f"Failed Step ID: {failed_step.step_id}\n"
                f"Capability: {failed_step.capability_id}\n"
                f"Intent: {failed_step.intent}\n"
                f"Arguments: {json.dumps(failed_step.arguments)}\n"
                f"Propose a valid replacement PlanStep JSON adhering to the capability registry."
            )
            try:
                raw_response = self.generative_provider.generate_text(prompt)
                parsed = json.loads(raw_response)
                if isinstance(parsed, dict) and "capability_id" in parsed:
                    cap_id = parsed["capability_id"]
                    if self.capability_registry.has(cap_id):
                        replacement_step = PlanStep(
                            step_id=f"{failed_step.step_id}_alt{attempt_num}",
                            capability_id=cap_id,
                            intent=parsed.get("intent", f"Generative recovery for {failed_step.intent}"),
                            arguments=parsed.get("arguments", {}),
                            dependencies=[d for d in failed_step.dependencies if d in preserved_step_ids],
                            timeout_s=float(parsed.get("timeout_s", failed_step.timeout_s)),
                            max_attempts=1,
                            metadata={"strategy": "generative_synthesis"},
                        )
                        return [replacement_step]
            except Exception as e:
                logger.warning(f"Generative replanning synthesis failed: {e}")

        # 3. Argument Parameter Relaxation / Retry with variation
        alt_args = dict(failed_step.arguments or {})
        if "query" in alt_args and isinstance(alt_args["query"], str):
            # Simplify query by removing restrictive qualifiers
            simplified = alt_args["query"].split(" site:")[0].split(" filetype:")[0].strip()
            if simplified != alt_args["query"]:
                alt_args["query"] = simplified
                return [
                    PlanStep(
                        step_id=f"{failed_step.step_id}_alt{attempt_num}",
                        capability_id=failed_step.capability_id,
                        intent=f"Retry '{failed_step.intent}' with relaxed query",
                        arguments=alt_args,
                        dependencies=[d for d in failed_step.dependencies if d in preserved_step_ids],
                        timeout_s=failed_step.timeout_s,
                        max_attempts=1,
                        metadata={"strategy": "argument_relaxation"},
                    )
                ]

        raise PlanError(f"No viable replacement strategy found for failed step '{failed_step.step_id}' ({failed_step.capability_id}).")

    # =========================================================================
    # Main Replanning Execution
    # =========================================================================

    def replan(
        self,
        request: ReplanRequest,
        active_plan: Plan,
        quest: Quest,
    ) -> ReplanResult:
        """Executes a controlled replan, splicing replacement steps into the active DAG.
        
        Args:
            request: ReplanRequest specifying failure context and constraints.
            active_plan: The current active Plan.
            quest: The parent Quest instance.
            
        Returns:
            ReplanResult containing the validated revised plan or failure explanation.
        """
        # 1. Budget Verification
        if request.replan_attempt > request.max_replans:
            return ReplanResult(
                quest_id=request.quest_id,
                success=False,
                scope=ReplanScope.SUB_DAG_REPLACE,
                error=f"Replan attempt {request.replan_attempt} exceeds maximum allowed replans ({request.max_replans}).",
            )

        # 2. Locate Failed Step
        failed_step = next((s for s in active_plan.steps if s.step_id == request.failed_step_id), None)
        if not failed_step:
            return ReplanResult(
                quest_id=request.quest_id,
                success=False,
                scope=ReplanScope.SUB_DAG_REPLACE,
                error=f"Failed step '{request.failed_step_id}' not found in active plan.",
            )

        # 3. Anti-Oscillation Gate
        # Compute fingerprint of current failure
        curr_fingerprint = {
            "step_id": failed_step.step_id,
            "capability_id": failed_step.capability_id,
            "args_hash": hashlib.sha256(json.dumps(failed_step.arguments or {}, sort_keys=True).encode()).hexdigest()[:12],
        }
        for prev in request.previous_failures:
            if (
                prev.get("capability_id") == curr_fingerprint["capability_id"]
                and prev.get("args_hash") == curr_fingerprint["args_hash"]
                and prev.get("step_id") == curr_fingerprint["step_id"]
            ):
                return ReplanResult(
                    quest_id=request.quest_id,
                    success=False,
                    scope=ReplanScope.SUB_DAG_REPLACE,
                    error=f"Anti-oscillation gate triggered: identical step '{failed_step.step_id}' failed previously.",
                )

        # 4. Compute Blast Radius
        blast_radius = self.compute_blast_radius(active_plan.steps, request.failed_step_id)
        preserved_steps = [s for s in active_plan.steps if s.step_id not in blast_radius]
        preserved_step_ids = {s.step_id for s in preserved_steps}

        scope = (
            ReplanScope.STEP_RETRY_WITH_VARIATION
            if len(blast_radius) == 1
            else ReplanScope.SUB_DAG_REPLACE
        )

        # 5. Synthesize Replacement Sub-DAG
        try:
            replacement_steps = self._synthesize_replacement_steps(
                failed_step=failed_step,
                attempt_num=request.replan_attempt,
                preserved_step_ids=preserved_step_ids,
                previous_failures=request.previous_failures,
                context=request.metadata,
            )
        except Exception as e:
            return ReplanResult(
                quest_id=request.quest_id,
                success=False,
                scope=scope,
                blast_radius_step_ids=list(blast_radius),
                preserved_step_ids=list(preserved_step_ids),
                error=f"Failed to synthesize replacement steps: {str(e)}",
            )

        # Terminal replacement step mapping
        terminal_replacement_id = replacement_steps[-1].step_id

        # 6. Re-wire Dependent Steps in Blast Radius (if downstream steps exist)
        # Any downstream step in blast radius (excluding the failed step itself)
        # that depended on failed_step is rewired to depend on the terminal replacement step
        downstream_steps = [s for s in active_plan.steps if s.step_id in blast_radius and s.step_id != failed_step.step_id]
        rewired_downstream: List[PlanStep] = []
        for ds in downstream_steps:
            new_deps = [
                terminal_replacement_id if d == failed_step.step_id else d
                for d in ds.dependencies
            ]
            rewired = ds.model_copy(update={"dependencies": new_deps})
            rewired_downstream.append(rewired)

        # 7. Assemble Revised Plan
        revised_steps = preserved_steps + replacement_steps + rewired_downstream
        new_plan_version = active_plan.plan_version + 1

        revised_plan = Plan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            quest_id=active_plan.quest_id,
            goal=active_plan.goal,
            plan_type=PlanType.COMPOSITE,
            steps=revised_steps,
            plan_version=new_plan_version,
            max_depth=active_plan.max_depth,
            timeout_budget_s=active_plan.timeout_budget_s,
            skill_id=active_plan.skill_id,
            metadata={
                **active_plan.metadata,
                "replanned_from": active_plan.plan_id,
                "replan_version": new_plan_version,
                "replan_attempt": request.replan_attempt,
                "failed_step_id": request.failed_step_id,
                "trigger": request.trigger.value,
                "blast_radius": sorted(list(blast_radius)),
            },
        )

        # 8. Deterministic Validation Gate
        validation_report = self.plan_validator.validate(
            revised_plan,
            autonomy_profile=quest.autonomy_profile,
        )
        if not validation_report.is_valid:
            return ReplanResult(
                quest_id=request.quest_id,
                success=False,
                scope=scope,
                blast_radius_step_ids=list(blast_radius),
                preserved_step_ids=list(preserved_step_ids),
                error=f"Revised plan failed validation: {'; '.join(validation_report.errors)}",
            )

        # Attach validation metadata
        revised_plan.validator_version = "2.0"
        revised_plan.validation_hash = revised_plan.compute_hash()

        return ReplanResult(
            quest_id=request.quest_id,
            success=True,
            revised_plan=revised_plan,
            scope=scope,
            blast_radius_step_ids=sorted(list(blast_radius)),
            preserved_step_ids=sorted(list(preserved_step_ids)),
            added_step_ids=[s.step_id for s in replacement_steps],
            replan_version=new_plan_version,
            metadata={
                "trigger": request.trigger.value,
                "failed_step_id": request.failed_step_id,
            },
        )
