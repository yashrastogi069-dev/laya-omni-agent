"""Generative Structured DAG Planner Fallback.

Synthesizes novel execution plans when no pre-defined skill template applies,
enforcing strict JSON schema output and deterministic validation (Checkpoint L12).
"""

import json
import re
from typing import Any, Dict, List, Optional

from ..capabilities.registry import CapabilityRegistry
from ..contracts.capability import CapabilitySpec
from ..contracts.plan import Plan, PlanGenerationError, PlanStep, PlanType, PlanValidationError
from ..providers.base import GenerativeProvider
from .dag import DAGTopology


class GenerativePlanner:
    """Generates structured DAG plans using LLM synthesis with strict JSON schema constraints."""

    SYSTEM_PROMPT = """You are the deterministic DAG planning system for LAYA Autonomous V2.
Your goal is to decompose the user's objective into a structured execution DAG consisting of valid capabilities.

RULES:
1. Output ONLY a valid raw JSON object conforming to the schema below.
2. Do NOT include markdown code fences (```json or ```).
3. Do NOT include any conversational preamble or explanations.
4. Each step must use a valid capability_id from the available capabilities catalog.
5. All dependencies must reference valid preceding step_ids. Cycles are strictly forbidden.

JSON SCHEMA:
{
  "steps": [
    {
      "step_id": "step_1",
      "capability_id": "file_read",
      "intent": "Read the configuration file",
      "arguments": {"filepath": "config.json"},
      "dependencies": []
    }
  ]
}
"""

    def __init__(
        self,
        provider: Optional[GenerativeProvider] = None,
        capability_registry: Optional[CapabilityRegistry] = None,
    ) -> None:
        """Initialize GenerativePlanner.
        
        Args:
            provider: GenerativeProvider instance (e.g. OpenRouterProvider or mock).
            capability_registry: CapabilityRegistry providing valid capabilities catalog.
        """
        self.provider = provider
        self.registry = capability_registry

    def _format_catalog(self, allowed_capabilities: Optional[List[str]] = None) -> str:
        """Formats available capabilities into a concise summary prompt."""
        if not self.registry:
            return "No capability catalog provided."
        
        specs = self.registry.list_specs()
        if allowed_capabilities:
            specs = [s for s in specs if s.capability_id in allowed_capabilities]

        lines = []
        for s in specs:
            props = list((s.input_schema.get("properties") or {}).keys())
            lines.append(f"- {s.capability_id}: {s.description} (params: {props})")
        return "\n".join(lines)

    @staticmethod
    def _clean_json_response(raw_text: str) -> str:
        """Extracts and strips JSON payload from model response."""
        text = raw_text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def synthesize_plan(
        self,
        quest_id: str,
        goal: str,
        allowed_capabilities: Optional[List[str]] = None,
        timeout_budget_s: float = 300.0,
        max_steps: int = 10,
        max_depth: int = 5,
        mock_response: Optional[str] = None,
    ) -> Plan:
        """Synthesizes a structured Plan from the goal using generative provider.
        
        Args:
            quest_id: Parent Quest ID.
            goal: User objective description.
            allowed_capabilities: Optional filter on allowed capability IDs.
            timeout_budget_s: Wall-clock budget for plan.
            max_steps: Maximum step limit.
            max_depth: Maximum DAG depth limit.
            mock_response: Raw JSON string override for offline unit testing.
            
        Returns:
            A validated Plan with plan_type = PlanType.GENERATIVE_SYNTHESIZED.
            
        Raises:
            PlanGenerationError: If provider fails or output violates schema.
            PlanValidationError: If the synthesized DAG contains cycles or exceeds limits.
        """
        if mock_response is not None:
            raw_output = mock_response
        elif self.provider is not None:
            catalog_str = self._format_catalog(allowed_capabilities)
            prompt = (
                f"OBJECTIVE: {goal}\n\n"
                f"AVAILABLE CAPABILITIES:\n{catalog_str}\n\n"
                f"Generate the execution DAG in strict JSON format."
            )
            try:
                raw_output = self.provider.generate(
                    prompt=prompt,
                    system_prompt=self.SYSTEM_PROMPT,
                    temperature=0.1,
                )
            except Exception as e:
                raise PlanGenerationError(f"Generative provider failed during plan synthesis: {e}") from e
        else:
            raise PlanGenerationError("No GenerativeProvider or mock_response configured for generative planning.")

        # Clean and parse JSON
        cleaned_json = self._clean_json_response(raw_output)
        try:
            parsed = json.loads(cleaned_json)
        except json.JSONDecodeError as exc:
            raise PlanGenerationError(
                f"Generative planner output is not valid JSON: {exc}. Raw output: {raw_output[:200]}"
            ) from exc

        if not isinstance(parsed, dict) or "steps" not in parsed:
            raise PlanGenerationError("Synthesized plan JSON must be an object with a 'steps' list.")

        raw_steps = parsed["steps"]
        if not isinstance(raw_steps, list) or len(raw_steps) == 0:
            raise PlanGenerationError("Synthesized plan must contain at least 1 step.")

        if len(raw_steps) > max_steps:
            raise PlanValidationError(
                f"Synthesized plan exceeds maximum step limit ({len(raw_steps)} > {max_steps})."
            )

        # Build PlanSteps
        plan_steps: List[PlanStep] = []
        for i, s_dict in enumerate(raw_steps):
            if not isinstance(s_dict, dict):
                raise PlanGenerationError(f"Step {i} must be a JSON object.")

            step_id = s_dict.get("step_id") or f"step_{i+1}"
            cap_id = s_dict.get("capability_id")
            intent = s_dict.get("intent") or f"Execute {cap_id}"
            arguments = s_dict.get("arguments") or {}
            dependencies = s_dict.get("dependencies") or []

            if not cap_id:
                raise PlanGenerationError(f"Step '{step_id}' is missing required capability_id.")

            # Verify capability exists in registry if available
            if self.registry and not self.registry.has_capability(cap_id):
                raise PlanValidationError(
                    f"Step '{step_id}' references unknown capability '{cap_id}' not in registry."
                )

            try:
                plan_step = PlanStep(
                    step_id=step_id,
                    capability_id=cap_id,
                    intent=intent,
                    arguments=arguments,
                    dependencies=dependencies,
                    timeout_s=60.0,
                    max_attempts=3,
                    metadata={"source": "generative_synthesis"},
                )
                plan_steps.append(plan_step)
            except Exception as exc:
                raise PlanGenerationError(f"Failed to instantiate PlanStep '{step_id}': {exc}") from exc

        # Validate DAG topology
        sorted_steps = DAGTopology.topological_sort(plan_steps)
        plan_depth = DAGTopology.compute_plan_depth(sorted_steps)

        if plan_depth > max_depth:
            raise PlanValidationError(
                f"Synthesized plan exceeds maximum depth limit ({plan_depth} > {max_depth})."
            )

        return Plan(
            quest_id=quest_id,
            goal=goal,
            plan_type=PlanType.GENERATIVE_SYNTHESIZED,
            steps=sorted_steps,
            max_depth=plan_depth,
            timeout_budget_s=timeout_budget_s,
            metadata={
                "source": "generative_planner",
                "model_id": getattr(self.provider, "model_id", "mock"),
                "step_count": len(sorted_steps),
            },
        )
