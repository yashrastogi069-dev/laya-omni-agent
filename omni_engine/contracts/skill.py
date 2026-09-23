"""
omni_engine.contracts.skill
===========================
Strongly typed boundary contracts for skills and workflow templates.

Contracts:
- SkillStepTemplate: Individual executable step in a deterministic skill workflow DAG.
- SkillManifest: Declarative contract defining a reusable skill, capability requirements,
  safety policies, autonomy profile, and workflow templates.
"""

from typing import Any, Dict, List, Optional, Set
from pydantic import Field, field_validator, model_validator

from .base import BaseContractModel
from .enums import ActionClass, AutonomyProfile, ConfirmationPolicy

VALID_DOMAINS: Set[str] = {"web", "browser", "os", "dev", "data", "general"}

HIGH_RISK_ACTION_CLASSES: Set[ActionClass] = {
    ActionClass.LOCAL_DELETE,
    ActionClass.EXTERNAL_DELETE,
    ActionClass.EXTERNAL_SEND,
    ActionClass.SYSTEM_ACTION,
    ActionClass.SECURITY_SENSITIVE,
    ActionClass.FINANCIAL,
}


class SkillStepTemplate(BaseContractModel):
    """Declarative specification for an individual step in a skill workflow template."""
    step_id: str = Field(..., description="Unique step identifier within the skill template (e.g. 'step_1_search')")
    capability_id: str = Field(..., description="Canonical capability ID to invoke")
    description: str = Field(..., description="Human-readable explanation of step objective")
    depends_on: List[str] = Field(
        default_factory=list,
        description="Step IDs that must complete before this step executes (enables DAG planning)"
    )
    default_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Static default arguments passed to capability"
    )
    arg_mappings: Dict[str, str] = Field(
        default_factory=dict,
        description="Dynamic argument mappings (e.g. {'query': '$inputs.query', 'prev': '$steps.step_1.result'})"
    )
    verification_rule: Optional[str] = Field(
        default=None,
        description="Optional deterministic verification rule or receipt check"
    )
    can_fail_silently: bool = Field(
        default=False,
        description="Whether failure of this step can be safely tolerated without aborting workflow"
    )

    @field_validator("step_id", "capability_id", "description")
    @classmethod
    def validate_non_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()


class SkillManifest(BaseContractModel):
    """First-class skill contract mapping common user objectives to capabilities and workflows."""
    schema_version: str = Field(default="1.0.0", description="SkillManifest schema version")
    skill_id: str = Field(..., description="Unique canonical skill identifier (e.g. 'web_research')")
    version: str = Field(default="1.0.0", description="Semantic version string")
    domain: str = Field(..., description="Primary capability domain (web, dev, os, data, browser)")
    name: str = Field(..., description="Human-readable skill name")
    description: str = Field(..., description="Detailed description of skill purpose and scope")
    intent_patterns: List[str] = Field(..., description="Trigger phrases and exemplar queries for System 1 routing")
    input_schema: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema describing input parameter requirements"
    )
    output_schema: Dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        description="JSON Schema describing final expected output format"
    )
    required_capabilities: List[str] = Field(
        ...,
        description="Canonical capability IDs strictly required to execute this skill"
    )
    optional_capabilities: List[str] = Field(
        default_factory=list,
        description="Supporting capability IDs that may enhance execution if available"
    )
    action_classes: List[ActionClass] = Field(
        ...,
        description="Action classes encompassing maximum blast radius of constituent capabilities"
    )
    workflow_template: Optional[List[SkillStepTemplate]] = Field(
        default=None,
        description="Deterministic sequence of steps if predefined (DAG structure)"
    )
    planning_required: bool = Field(
        default=False,
        description="Whether novel generative DAG planning is required for variations"
    )
    verification_strategy: str = Field(
        default="deterministic_receipt",
        description="Outcome verification strategy (deterministic_receipt, file_diff, process_check, etc.)"
    )
    applicable_autonomy: AutonomyProfile = Field(
        default=AutonomyProfile.SAFE_ASSISTANT,
        description="Minimum autonomy profile required to execute this skill"
    )
    confirmation_policy: ConfirmationPolicy = Field(
        default=ConfirmationPolicy.POLICY_CONTROLLED,
        description="Human confirmation policy governing skill execution"
    )
    escalation_conditions: List[str] = Field(
        default_factory=list,
        description="Explicit triggers mandating escalation to human or supervisor"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Telemetry, authoring notes, or custom workflow attributes"
    )

    @field_validator("skill_id", "domain", "name", "description")
    @classmethod
    def validate_strings_non_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace.")
        return v.strip()

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if v not in VALID_DOMAINS:
            raise ValueError(f"Domain '{v}' is not recognized. Valid domains: {sorted(list(VALID_DOMAINS))}")
        return v

    @field_validator("required_capabilities")
    @classmethod
    def validate_required_caps(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("required_capabilities cannot be empty. Every skill must require at least one capability.")
        # Deduplication check
        seen = set()
        for cap in v:
            if not cap or not cap.strip():
                raise ValueError("Capability ID cannot be empty or whitespace.")
            if cap in seen:
                raise ValueError(f"Duplicate capability ID '{cap}' in required_capabilities.")
            seen.add(cap)
        return v

    @field_validator("intent_patterns")
    @classmethod
    def validate_intent_patterns(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("intent_patterns cannot be empty. At least one trigger pattern is required.")
        for p in v:
            if not p or not p.strip():
                raise ValueError("Intent pattern cannot be empty or whitespace.")
        return v

    @model_validator(mode="after")
    def validate_skill_manifest_invariants(self) -> "SkillManifest":
        # 1. No overlap between required and optional capabilities
        req_set = set(self.required_capabilities)
        opt_set = set(self.optional_capabilities)
        overlap = req_set.intersection(opt_set)
        if overlap:
            raise ValueError(f"Capabilities cannot be both required and optional: {sorted(list(overlap))}")

        all_caps = req_set.union(opt_set)

        # 2. Cross-validation: planning_required vs workflow_template (BLOCKING-3)
        has_template = self.workflow_template is not None and len(self.workflow_template) > 0
        if not self.planning_required and not has_template:
            raise ValueError(
                "Skills with planning_required=False MUST provide a non-empty workflow_template. "
                "Either provide a deterministic workflow template or set planning_required=True."
            )
        if (self.workflow_template is None or len(self.workflow_template) == 0) and not self.planning_required:
            raise ValueError("Empty or None workflow_template requires planning_required=True.")

        # 3. Workflow Template Invariants (BLOCKING-1, BLOCKING-4)
        if has_template and self.workflow_template:
            all_step_ids: Set[str] = {s.step_id for s in self.workflow_template}
            seen_steps: Set[str] = set()
            for step in self.workflow_template:
                # 3a. Step ID uniqueness
                if step.step_id in seen_steps:
                    raise ValueError(f"Duplicate step_id '{step.step_id}' in workflow_template.")
                seen_steps.add(step.step_id)

                # 3b. Step capability inclusion in skill's declared capabilities
                if step.capability_id not in all_caps:
                    raise ValueError(
                        f"Step '{step.step_id}' references undeclared capability '{step.capability_id}'. "
                        f"Must be declared in required_capabilities or optional_capabilities."
                    )

                # 3c. Dependencies must reference declared steps and not self
                for dep in step.depends_on:
                    if dep == step.step_id:
                        raise ValueError(f"Step '{step.step_id}' cannot depend on itself.")
                    if dep not in all_step_ids:
                        raise ValueError(
                            f"Step '{step.step_id}' references undeclared dependency '{dep}' in depends_on."
                        )

            # 3d. DAG Acyclicity Verification (Defect 2)
            adj: Dict[str, List[str]] = {s.step_id: list(s.depends_on) for s in self.workflow_template}
            visiting: Set[str] = set()
            visited: Set[str] = set()

            def _dfs(node: str, path: List[str]) -> None:
                visiting.add(node)
                path.append(node)
                for dep_node in adj.get(node, []):
                    if dep_node in visiting:
                        cycle_path = " -> ".join(path[path.index(dep_node):] + [dep_node])
                        raise ValueError(f"Circular dependency detected in workflow_template: {cycle_path}")
                    if dep_node not in visited:
                        _dfs(dep_node, path)
                path.pop()
                visiting.remove(node)
                visited.add(node)

            for step_id in adj:
                if step_id not in visited:
                    _dfs(step_id, [])

        # 4. Safety Policy Floor Validation (BLOCKING-2)
        # If any action class is high-risk, confirmation_policy CANNOT be NEVER
        has_high_risk = any(ac in HIGH_RISK_ACTION_CLASSES for ac in self.action_classes)
        if has_high_risk and self.confirmation_policy == ConfirmationPolicy.NEVER:
            raise ValueError(
                f"Skill '{self.skill_id}' includes high-risk action classes {self.action_classes} "
                f"and cannot have confirmation_policy=ConfirmationPolicy.NEVER."
            )

        return self
