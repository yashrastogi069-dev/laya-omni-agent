"""
omni_engine.planning.validator
==============================
Deterministic Plan Validator Firewall (Checkpoint L13).

Enforces 10 deterministic validation passes on planned DAGs prior to execution:
1. DAG_ACYCLICITY: 3-color DFS cycle detector from DAGTopology.
2. DEPENDENCY_EXISTENCE: Zero dangling step dependencies.
3. CAPABILITY_REGISTRATION: All referenced capabilities registered in CapabilityRegistry.
4. SCHEMA_CONFORMANCE: Arguments conform to CapabilitySpec.input_schema; causal dependency
   enforcement on $steps.<step_id>.<key> expressions; type-safe placeholder masking.
5. POLICY_FEASIBILITY: Pre-flight PolicyEngine evaluation; blocks hard DENY commands/paths;
   defers dynamic placeholder evaluations to L14 runtime.
6. AUTONOMY_COMPLIANCE: Enforces rank floor; strictly disallows mutations under ADVISOR.
7. STEP_COUNT_BOUNDS: [1, max_steps] enforcement.
8. GRAPH_DEPTH_BOUNDS: [1, max_depth] enforcement.
9. MUTATION_SAFETY: Enforces exactly-once single-flight attempts on NON_IDEMPOTENT mutations.
10. RESOURCE_BUDGET: Timeout budget bounds and step-level consistency.

Invariants:
- Deterministic Control (Invariant 1): 100% deterministic rule-based verification.
- Full Diagnostic Accumulation: Evaluates all 10 passes without crashing.
- Non-Switching Boundary: omni_agent.py and omni_engine/planner.py untouched.
"""

import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import jsonschema

from omni_engine.capabilities.definitions import build_real_capability_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    AUTONOMY_RANK,
    ErrorCode,
    IdempotencyClass,
    RetryPolicy,
)
from omni_engine.contracts.policy import PolicyEffect
from omni_engine.contracts.plan import Plan, PlanStep
from omni_engine.contracts.validation import (
    PlanValidationReport,
    ValidationPassName,
    ValidationPassResult,
)
from omni_engine.planning.dag import DAGTopology
from omni_engine.policy.engine import PolicyEngine


# Regex patterns for dynamic expression resolution
DYNAMIC_REF_FULL = re.compile(
    r"^\$(?:inputs\.[a-zA-Z0-9_.-]+|steps\.(?P<ref_step>[a-zA-Z0-9_-]+)(?:\.[a-zA-Z0-9_.-]+)*)$"
)
STEP_REF_SEARCH = re.compile(r"\$steps\.(?P<ref_step>[a-zA-Z0-9_-]+)")


class DeterministicPlanValidator:
    """Production Plan Validator Firewall executing 10 deterministic passes on structured DAGs."""

    def __init__(
        self,
        capability_registry: Optional[CapabilityRegistry] = None,
        policy_engine: Optional[PolicyEngine] = None,
        registry: Optional[CapabilityRegistry] = None,
    ) -> None:
        self.capability_registry = capability_registry or registry or build_real_capability_registry()
        self.policy_engine = policy_engine or PolicyEngine()

    @staticmethod
    def extract_resource_identity(step: PlanStep) -> Optional[str]:
        """Extracts canonical resource target (e.g. 'file:<normalized_path>', 'process:<pid>', 'repo:<path>')."""
        args = step.arguments or {}
        # File paths
        filepath = args.get("filepath") or args.get("file_path") or args.get("path")
        if filepath and isinstance(filepath, str) and not filepath.startswith("$"):
            norm = os.path.normpath(filepath).replace("\\", "/")
            return f"file:{norm}"

        # PIDs / Processes
        pid = args.get("pid") or args.get("target")
        if pid is not None and not str(pid).startswith("$"):
            return f"process:{pid}"

        # Repositories
        repo = args.get("repo_path")
        if repo and isinstance(repo, str) and not repo.startswith("$"):
            norm_repo = os.path.normpath(repo).replace("\\", "/")
            return f"repo:{norm_repo}"

        return None

    def validate(
        self,
        plan: Plan,
        autonomy_profile: Optional[AutonomyProfile] = None,
        max_steps: int = 20,
        max_depth: int = 6,
        max_timeout_budget_s: float = 3600.0,
    ) -> PlanValidationReport:
        """Executes all 10 deterministic validation passes and returns a cumulative diagnostic report.
        
        Args:
            plan: The structured Plan to validate.
            autonomy_profile: Target autonomy profile (defaults to SAFE_ASSISTANT).
            max_steps: Maximum allowed total steps in plan.
            max_depth: Maximum allowed DAG critical-path depth.
            max_timeout_budget_s: Upper limit on total wall-clock timeout budget.
            
        Returns:
            PlanValidationReport with detailed results for each pass, accumulated errors,
            warnings, and execution latency.
        """
        t0 = time.perf_counter()
        target_profile = autonomy_profile or AutonomyProfile.SAFE_ASSISTANT
        passes: List[ValidationPassResult] = []
        errors: List[str] = []
        warnings: List[str] = []

        # Track internal state across passes
        has_cycle = False
        all_step_ids: Set[str] = set()

        # =====================================================================
        # PASS 1: DAG_ACYCLICITY
        # =====================================================================
        p1_errors: List[str] = []
        duplicate_ids: List[str] = []
        seen_ids: Set[str] = set()
        for step in plan.steps:
            if step.step_id in seen_ids:
                duplicate_ids.append(step.step_id)
            seen_ids.add(step.step_id)
            all_step_ids.add(step.step_id)

        if duplicate_ids:
            p1_errors.append(f"Duplicate step ID(s) detected: {duplicate_ids}")

        # Check self-dependencies
        for step in plan.steps:
            if step.step_id in step.dependencies:
                p1_errors.append(f"Self-dependency detected: step '{step.step_id}' depends on itself")

        # Run 3-color DFS cycle detector
        if not duplicate_ids and plan.steps:
            cycle_path = DAGTopology.detect_cycles(plan.steps)
            if cycle_path:
                has_cycle = True
                p1_errors.append(f"Cycle detected in plan DAG: {' -> '.join(cycle_path)}")

        if p1_errors:
            has_cycle = True
            msg = "; ".join(p1_errors)
            errors.append(f"[{ValidationPassName.DAG_ACYCLICITY.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.DAG_ACYCLICITY,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.CONFLICT,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.DAG_ACYCLICITY,
                    passed=True,
                    message="Plan DAG is strictly acyclic.",
                )
            )

        # =====================================================================
        # PASS 2: DEPENDENCY_EXISTENCE
        # =====================================================================
        p2_errors: List[str] = []
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in all_step_ids:
                    p2_errors.append(f"Step '{step.step_id}' references unknown dependency '{dep}'")

        if p2_errors:
            msg = "; ".join(p2_errors)
            errors.append(f"[{ValidationPassName.DEPENDENCY_EXISTENCE.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.DEPENDENCY_EXISTENCE,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.INVALID_ARGUMENT,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.DEPENDENCY_EXISTENCE,
                    passed=True,
                    message="All step dependencies exist within the plan.",
                )
            )

        # =====================================================================
        # PASS 3: CAPABILITY_REGISTRATION
        # =====================================================================
        p3_errors: List[str] = []
        for step in plan.steps:
            if not self.capability_registry.has(step.capability_id):
                p3_errors.append(f"Step '{step.step_id}' references unregistered capability '{step.capability_id}'")

        if p3_errors:
            msg = "; ".join(p3_errors)
            errors.append(f"[{ValidationPassName.CAPABILITY_REGISTRATION.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.CAPABILITY_REGISTRATION,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.NOT_FOUND,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.CAPABILITY_REGISTRATION,
                    passed=True,
                    message="All plan steps reference registered capabilities.",
                )
            )

        # =====================================================================
        # PASS 4: SCHEMA_CONFORMANCE (Two-Phase with Dynamic Reference Checking)
        # =====================================================================
        p4_errors: List[str] = []
        for step in plan.steps:
            if not self.capability_registry.has(step.capability_id):
                continue

            spec = self.capability_registry.get_spec(step.capability_id)
            if spec is None:
                continue

            # Phase A: Causal dependency checking for dynamic references
            referenced_step_ids = self._extract_referenced_steps(step.arguments)
            for ref_id in referenced_step_ids:
                if ref_id not in all_step_ids:
                    p4_errors.append(
                        f"Step '{step.step_id}' references non-existent step '$steps.{ref_id}' in arguments"
                    )
                elif ref_id == step.step_id:
                    p4_errors.append(
                        f"Step '{step.step_id}' cannot reference its own output '$steps.{ref_id}' in arguments"
                    )
                elif ref_id not in step.dependencies:
                    p4_errors.append(
                        f"Step '{step.step_id}' references '$steps.{ref_id}' without declaring it as a dependency"
                    )

            # Phase B: Schema validation with placeholder masking
            schema = spec.input_schema or {}
            required_props = set(schema.get("required", []))
            for req in required_props:
                if req not in step.arguments:
                    p4_errors.append(
                        f"Step '{step.step_id}' missing required argument '{req}' for capability '{spec.id}'"
                    )

            properties = schema.get("properties", {})
            masked_args = self._mask_dynamic_args_for_schema(step.arguments, properties)
            try:
                jsonschema.validate(instance=masked_args, schema=schema)
            except jsonschema.ValidationError as e:
                p4_errors.append(f"Step '{step.step_id}' schema validation error: {e.message}")
            except Exception as e:
                p4_errors.append(f"Step '{step.step_id}' schema error: {str(e)}")

        if p4_errors:
            msg = "; ".join(p4_errors)
            errors.append(f"[{ValidationPassName.SCHEMA_CONFORMANCE.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.SCHEMA_CONFORMANCE,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.SCHEMA_VIOLATION,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.SCHEMA_CONFORMANCE,
                    passed=True,
                    message="All step arguments conform to capability input schemas.",
                )
            )

        # =====================================================================
        # PASS 5: POLICY_FEASIBILITY
        # =====================================================================
        p5_errors: List[str] = []
        for step in plan.steps:
            if not self.capability_registry.has(step.capability_id):
                continue

            spec = self.capability_registry.get_spec(step.capability_id)
            if spec is None:
                continue

            has_dynamic, masked_policy_args = self._mask_dynamic_args_for_policy(step.arguments)
            if has_dynamic:
                warnings.append(
                    f"Step '{step.step_id}' contains dynamic arguments; policy check deferred to L14 execution runtime."
                )

            decision = self.policy_engine.evaluate(
                capability=spec,
                arguments=masked_policy_args,
                autonomy_profile=target_profile,
                user_confirmed=False,
            )
            if decision.effect == PolicyEffect.DENY:
                p5_errors.append(
                    f"Step '{step.step_id}' violates policy: {decision.denial_reason or 'Operation hard denied'}"
                )

        if p5_errors:
            msg = "; ".join(p5_errors)
            errors.append(f"[{ValidationPassName.POLICY_FEASIBILITY.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.POLICY_FEASIBILITY,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.PERMISSION_DENIED,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.POLICY_FEASIBILITY,
                    passed=True,
                    message="All plan steps pass pre-flight policy feasibility checks.",
                )
            )

        # =====================================================================
        # PASS 6: AUTONOMY_COMPLIANCE
        # =====================================================================
        p6_errors: List[str] = []
        granted_rank = AUTONOMY_RANK.get(target_profile, 2)

        # Invariant: ADVISOR profile permits strictly READ_ONLY actions
        if target_profile == AutonomyProfile.ADVISOR:
            for step in plan.steps:
                if not self.capability_registry.has(step.capability_id):
                    continue
                spec = self.capability_registry.get_spec(step.capability_id)
                if spec and spec.action_class != ActionClass.READ_ONLY:
                    p6_errors.append(
                        f"Step '{step.step_id}' has mutating action '{spec.action_class.value}', which is forbidden under ADVISOR autonomy."
                    )

        # Rank floor check
        for step in plan.steps:
            if not self.capability_registry.has(step.capability_id):
                continue
            spec = self.capability_registry.get_spec(step.capability_id)
            if spec:
                req_rank = AUTONOMY_RANK.get(spec.minimum_autonomy_profile, 1)
                if granted_rank < req_rank:
                    p6_errors.append(
                        f"Step '{step.step_id}' capability '{spec.id}' requires autonomy '{spec.minimum_autonomy_profile.value}' (rank {req_rank}), exceeding granted '{target_profile.value}' (rank {granted_rank})."
                    )

        if p6_errors:
            msg = "; ".join(p6_errors)
            errors.append(f"[{ValidationPassName.AUTONOMY_COMPLIANCE.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.AUTONOMY_COMPLIANCE,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.UNAUTHORIZED_ACTION,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.AUTONOMY_COMPLIANCE,
                    passed=True,
                    message=f"All plan steps comply with autonomy profile '{target_profile.value}'.",
                )
            )

        # =====================================================================
        # PASS 7: STEP_COUNT_BOUNDS
        # =====================================================================
        p7_passed = True
        p7_msg = ""
        if len(plan.steps) == 0:
            p7_passed = False
            p7_msg = "Plan contains 0 steps; minimum 1 step required."
            errors.append(f"[{ValidationPassName.STEP_COUNT_BOUNDS.value}] {p7_msg}")
        elif len(plan.steps) > max_steps:
            p7_passed = False
            p7_msg = f"Plan step count ({len(plan.steps)}) exceeds maximum allowed ({max_steps})."
            errors.append(f"[{ValidationPassName.STEP_COUNT_BOUNDS.value}] {p7_msg}")
        else:
            p7_msg = f"Plan step count ({len(plan.steps)}) within allowed bounds [1, {max_steps}]."

        passes.append(
            ValidationPassResult(
                pass_name=ValidationPassName.STEP_COUNT_BOUNDS,
                passed=p7_passed,
                message=p7_msg,
                error_code=None if p7_passed else ErrorCode.INVALID_ARGUMENT,
            )
        )

        # =====================================================================
        # PASS 8: GRAPH_DEPTH_BOUNDS
        # =====================================================================
        p8_passed = True
        p8_msg = ""
        if has_cycle:
            p8_passed = False
            p8_msg = "Depth bounds check skipped due to circular dependencies in DAG."
            errors.append(f"[{ValidationPassName.GRAPH_DEPTH_BOUNDS.value}] {p8_msg}")
        elif len(plan.steps) == 0:
            p8_passed = False
            p8_msg = "Depth bounds check skipped: plan has 0 steps."
            errors.append(f"[{ValidationPassName.GRAPH_DEPTH_BOUNDS.value}] {p8_msg}")
        else:
            try:
                depth = DAGTopology.compute_plan_depth(plan.steps)
                if depth > max_depth:
                    p8_passed = False
                    p8_msg = f"Plan DAG depth ({depth}) exceeds maximum allowed depth limit ({max_depth})."
                    errors.append(f"[{ValidationPassName.GRAPH_DEPTH_BOUNDS.value}] {p8_msg}")
                else:
                    p8_msg = f"Plan DAG depth ({depth}) within allowed bounds [1, {max_depth}]."
            except Exception as e:
                p8_passed = False
                p8_msg = f"Error computing plan depth: {str(e)}"
                errors.append(f"[{ValidationPassName.GRAPH_DEPTH_BOUNDS.value}] {p8_msg}")

        passes.append(
            ValidationPassResult(
                pass_name=ValidationPassName.GRAPH_DEPTH_BOUNDS,
                passed=p8_passed,
                message=p8_msg,
                error_code=None if p8_passed else ErrorCode.INVALID_ARGUMENT,
            )
        )

        # =====================================================================
        # PASS 9: MUTATION_SAFETY
        # =====================================================================
        p9_errors: List[str] = []
        for step in plan.steps:
            if not self.capability_registry.has(step.capability_id):
                continue
            spec = self.capability_registry.get_spec(step.capability_id)
            if spec:
                if (
                    spec.idempotency_class == IdempotencyClass.NON_IDEMPOTENT
                    and spec.retry_policy == RetryPolicy.NEVER
                ):
                    if step.max_attempts > 1:
                        p9_errors.append(
                            f"Step '{step.step_id}' capability '{spec.id}' is NON_IDEMPOTENT with RetryPolicy.NEVER but declares max_attempts={step.max_attempts} > 1."
                        )

        # Check 2: Conflicting concurrent mutations on identical resources (AUDIT-13, AUDIT-14)
        ancestors: Dict[str, Set[str]] = {s.step_id: set() for s in plan.steps}
        for s in plan.steps:
            queue = list(s.dependencies)
            visited = set(queue)
            while queue:
                curr = queue.pop(0)
                ancestors[s.step_id].add(curr)
                curr_step = next((x for x in plan.steps if x.step_id == curr), None)
                if curr_step:
                    for dep in curr_step.dependencies:
                        if dep not in visited:
                            visited.add(dep)
                            queue.append(dep)

        for i in range(len(plan.steps)):
            s1 = plan.steps[i]
            spec1 = self.capability_registry.get_spec(s1.capability_id) if self.capability_registry.has(s1.capability_id) else None
            if not spec1 or spec1.action_class == ActionClass.READ_ONLY:
                continue
            res1 = self.extract_resource_identity(s1)
            if not res1:
                continue

            for j in range(i + 1, len(plan.steps)):
                s2 = plan.steps[j]
                spec2 = self.capability_registry.get_spec(s2.capability_id) if self.capability_registry.has(s2.capability_id) else None
                if not spec2 or spec2.action_class == ActionClass.READ_ONLY:
                    continue
                res2 = self.extract_resource_identity(s2)
                if not res2 or res1 != res2:
                    continue

                # Conflict if neither is ancestor of the other (they could run concurrently or in undefined order)
                if s1.step_id not in ancestors[s2.step_id] and s2.step_id not in ancestors[s1.step_id]:
                    p9_errors.append(
                        f"Steps '{s1.step_id}' and '{s2.step_id}' have concurrent conflicting mutations targeting resource '{res1}' without causal dependency ordering."
                    )

        if p9_errors:
            msg = "; ".join(p9_errors)
            errors.append(f"[{ValidationPassName.MUTATION_SAFETY.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.MUTATION_SAFETY,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.INVALID_ARGUMENT,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.MUTATION_SAFETY,
                    passed=True,
                    message="Mutation idempotency and retry constraints verified.",
                )
            )

        # =====================================================================
        # PASS 10: RESOURCE_BUDGET
        # =====================================================================
        p10_errors: List[str] = []
        if plan.timeout_budget_s <= 0.0:
            p10_errors.append(f"Plan timeout budget ({plan.timeout_budget_s}s) must be strictly positive.")
        elif plan.timeout_budget_s > max_timeout_budget_s:
            p10_errors.append(
                f"Plan timeout budget ({plan.timeout_budget_s}s) exceeds maximum allowed limit ({max_timeout_budget_s}s)."
            )

        for step in plan.steps:
            if step.timeout_s > plan.timeout_budget_s:
                p10_errors.append(
                    f"Step '{step.step_id}' timeout ({step.timeout_s}s) exceeds plan timeout budget ({plan.timeout_budget_s}s)."
                )

        if p10_errors:
            msg = "; ".join(p10_errors)
            errors.append(f"[{ValidationPassName.RESOURCE_BUDGET.value}] {msg}")
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.RESOURCE_BUDGET,
                    passed=False,
                    message=msg,
                    error_code=ErrorCode.TIMEOUT,
                )
            )
        else:
            passes.append(
                ValidationPassResult(
                    pass_name=ValidationPassName.RESOURCE_BUDGET,
                    passed=True,
                    message=f"Plan timeout budget ({plan.timeout_budget_s}s) and step budgets within valid bounds.",
                )
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        is_valid = len(errors) == 0

        return PlanValidationReport(
            plan_id=plan.plan_id,
            is_valid=is_valid,
            passes=passes,
            errors=errors,
            warnings=warnings,
            latency_ms=round(elapsed_ms, 3),
        )

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _extract_referenced_steps(self, obj: Any) -> Set[str]:
        """Recursively finds all referenced step IDs in dynamic expressions."""
        refs: Set[str] = set()
        if isinstance(obj, str):
            for m in STEP_REF_SEARCH.finditer(obj):
                refs.add(m.group("ref_step"))
        elif isinstance(obj, dict):
            for v in obj.values():
                refs.update(self._extract_referenced_steps(v))
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                refs.update(self._extract_referenced_steps(item))
        return refs

    def _mask_dynamic_args_for_schema(
        self,
        arguments: Dict[str, Any],
        properties: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Substitutes dynamic string tokens with compliant dummy values for JSON schema checking."""
        masked: Dict[str, Any] = {}
        for k, v in arguments.items():
            prop_spec = properties.get(k, {})
            masked[k] = self._mask_value(v, prop_spec)
        return masked

    def _mask_value(self, val: Any, prop_spec: Dict[str, Any]) -> Any:
        if isinstance(val, str) and DYNAMIC_REF_FULL.match(val.strip()):
            prop_type = prop_spec.get("type")
            if prop_type == "integer":
                return 1
            elif prop_type == "number":
                return 1.0
            elif prop_type == "boolean":
                return True
            elif prop_type == "array":
                return []
            elif prop_type == "object":
                return {}
            elif "enum" in prop_spec and prop_spec["enum"]:
                return prop_spec["enum"][0]
            else:
                return "DYNAMIC_PLACEHOLDER"
        elif isinstance(val, dict):
            sub_props = prop_spec.get("properties", {})
            return {sk: self._mask_value(sv, sub_props.get(sk, {})) for sk, sv in val.items()}
        elif isinstance(val, list):
            item_spec = prop_spec.get("items", {})
            return [self._mask_value(item, item_spec) for item in val]
        return val

    def _mask_dynamic_args_for_policy(
        self,
        arguments: Dict[str, Any],
    ) -> Tuple[bool, Dict[str, Any]]:
        """Replaces dynamic expressions with safe placeholder strings to prevent false path denials."""
        has_dynamic = False
        masked: Dict[str, Any] = {}
        for k, v in arguments.items():
            sub_dyn, sub_val = self._mask_policy_val(v)
            if sub_dyn:
                has_dynamic = True
            masked[k] = sub_val
        return has_dynamic, masked

    def _mask_policy_val(self, val: Any) -> Tuple[bool, Any]:
        if isinstance(val, str):
            if re.search(r"\$(?:inputs|steps)\.", val):
                return True, "DYNAMIC_SAFE_ARG"
            return False, val
        elif isinstance(val, dict):
            sub_dyn = False
            sub_dict = {}
            for sk, sv in val.items():
                d, v = self._mask_policy_val(sv)
                if d:
                    sub_dyn = True
                sub_dict[sk] = v
            return sub_dyn, sub_dict
        elif isinstance(val, list):
            sub_dyn = False
            sub_list = []
            for item in val:
                d, v = self._mask_policy_val(item)
                if d:
                    sub_dyn = True
                sub_list.append(v)
            return sub_dyn, sub_list
        return False, val
