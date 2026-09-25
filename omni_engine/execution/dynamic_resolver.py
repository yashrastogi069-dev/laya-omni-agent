"""Dynamic Argument Resolution Engine for DAG Execution.

Resolves runtime parameter expressions conforming to:
- $inputs.<key>[.<subpath>]
- $steps.<step_id>.<path>
Supporting stringified JSON navigation, exact type preservation, and string interpolation (Checkpoint L14).
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from ..contracts.execution import UnresolvedArgumentError
from ..contracts.quest import QuestStep, StepStatus

# Pattern matching dynamic reference expressions
_DYNAMIC_TOKEN_PATTERN = re.compile(r"(\$inputs\.[a-zA-Z0-9_.]+|\$steps\.[a-zA-Z0-9_.]+)")


class DynamicResolver:
    """Resolves dynamic parameter references for a plan step prior to capability invocation."""

    @classmethod
    def resolve_arguments(
        cls,
        raw_arguments: Dict[str, Any],
        quest_inputs: Optional[Dict[str, Any]] = None,
        completed_steps: Optional[Dict[str, Union[QuestStep, Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        """Resolves all dynamic references within an argument dictionary.
        
        Args:
            raw_arguments: The step's argument dictionary containing static or dynamic values.
            quest_inputs: Quest-level inputs dictionary ($inputs.<key>).
            completed_steps: Mapping of step_id to completed QuestStep or receipt dictionary.
            
        Returns:
            Resolved arguments dictionary with all dynamic references replaced by actual values.
            
        Raises:
            UnresolvedArgumentError: If any referenced input, step, or subpath cannot be resolved.
        """
        inputs = quest_inputs or {}
        steps = completed_steps or {}

        resolved: Dict[str, Any] = {}
        for key, val in raw_arguments.items():
            resolved[key] = cls._resolve_value(val, inputs, steps, path=key)
        return resolved

    @classmethod
    def _resolve_value(
        cls,
        val: Any,
        inputs: Dict[str, Any],
        steps: Dict[str, Any],
        path: str = "",
    ) -> Any:
        """Recursively resolves a single value."""
        if isinstance(val, dict):
            return {k: cls._resolve_value(v, inputs, steps, f"{path}.{k}") for k, v in val.items()}
        elif isinstance(val, list):
            return [cls._resolve_value(item, inputs, steps, f"{path}[{i}]") for i, item in enumerate(val)]
        elif isinstance(val, str):
            # Check for exact single token match (preserves native type)
            stripped = val.strip()
            if _DYNAMIC_TOKEN_PATTERN.fullmatch(stripped):
                return cls._resolve_token(stripped, inputs, steps)

            # Check for embedded tokens within a string (string interpolation)
            if "$" in val:
                def replace_token(match: re.Match) -> str:
                    token = match.group(1)
                    resolved_val = cls._resolve_token(token, inputs, steps)
                    if isinstance(resolved_val, (dict, list)):
                        return json.dumps(resolved_val)
                    return str(resolved_val)

                return _DYNAMIC_TOKEN_PATTERN.sub(replace_token, val)

            return val
        else:
            return val

    @classmethod
    def _resolve_token(
        cls,
        token: str,
        inputs: Dict[str, Any],
        steps: Dict[str, Any],
    ) -> Any:
        """Resolves a single token like $inputs.user_id or $steps.step_1.output.id."""
        if token.startswith("$inputs."):
            subpath = token[len("$inputs."):]
            return cls._lookup_path(inputs, subpath, source_desc="quest inputs")

        elif token.startswith("$steps."):
            parts = token[len("$steps."):].split(".", 1)
            step_id = parts[0]
            subpath = parts[1] if len(parts) > 1 else ""

            if step_id not in steps:
                raise UnresolvedArgumentError(
                    f"Referenced step '{step_id}' has not executed or is not completed (evaluating '{token}')."
                )

            step_data = steps[step_id]
            scope = cls._build_step_scope(step_data)

            if not subpath:
                return scope

            return cls._lookup_path(scope, subpath, source_desc=f"step '{step_id}' output")

        raise UnresolvedArgumentError(f"Unrecognized dynamic token syntax: '{token}'.")

    @classmethod
    def _build_step_scope(cls, step_data: Union[QuestStep, Dict[str, Any]]) -> Dict[str, Any]:
        """Constructs a normalized property scope dictionary for a completed step."""
        receipt: Optional[Dict[str, Any]] = None
        status: Optional[str] = None

        if isinstance(step_data, QuestStep):
            receipt = step_data.execution_receipt
            status = step_data.status.value if isinstance(step_data.status, StepStatus) else str(step_data.status)
        elif isinstance(step_data, dict):
            receipt = step_data.get("execution_receipt", step_data)
            status = str(step_data.get("status", "completed"))

        scope: Dict[str, Any] = {"status": status}
        if not receipt:
            return scope

        # Populate top-level receipt fields
        scope.update(receipt)

        # Multi-Path Navigation (BLK-3):
        # Normalize ToolResult.data vs ToolResult.output vs legacy tool dicts
        data_block = receipt.get("data")
        if isinstance(data_block, dict):
            scope.update(data_block)
            scope["data"] = data_block
            if list(data_block.keys()) == ["output"]:
                scope["output"] = data_block["output"]
            else:
                scope["output"] = data_block

        elif "output" in receipt:
            scope["output"] = receipt["output"]
            scope["data"] = {"output": receipt["output"]}
        elif data_block is not None:
            scope["output"] = data_block
            scope["data"] = data_block
        else:
            scope["output"] = receipt
            scope["data"] = receipt

        return scope

    @classmethod
    def _lookup_path(cls, root: Any, path: str, source_desc: str) -> Any:
        """Traverses a dot-separated property path, with automatic JSON deserialization."""
        segments = path.split(".")
        current = root

        for seg in segments:
            if not seg:
                continue

            # If current node is a stringified JSON, attempt deserialization
            if isinstance(current, str):
                trimmed = current.strip()
                if (trimmed.startswith("{") and trimmed.endswith("}")) or (trimmed.startswith("[") and trimmed.endswith("]")):
                    try:
                        current = json.loads(trimmed)
                    except Exception:
                        pass  # Keep as string if parsing fails

            if isinstance(current, dict):
                if seg in current:
                    current = current[seg]
                else:
                    available = list(current.keys())
                    raise UnresolvedArgumentError(
                        f"Property '{seg}' not found in {source_desc}. Available properties: {available}."
                    )
            elif isinstance(current, list):
                try:
                    idx = int(seg)
                    current = current[idx]
                except (ValueError, IndexError):
                    raise UnresolvedArgumentError(
                        f"Invalid list index '{seg}' for array of length {len(current)} in {source_desc}."
                    )
            else:
                raise UnresolvedArgumentError(
                    f"Cannot navigate property '{seg}' on leaf object of type {type(current).__name__} in {source_desc}."
                )

        return current
