"""Workflow Graph and Schema Validator for n8n.

REQ-BLOCK-2 & REQ-BLOCK-3:
- Parses 3-level nested connection map: connections[src]["main"][idx] = [...]
- Resolves nodes bidirectionally by name and by id
- Detects dangling connections and self-loops
- Performs 3-color topological DFS cycle detection
- Enforces trigger in-degree == 0 and trigger count >= 1
- Detects orphaned nodes via forward reachability
- Performs pre-flight parameter scan against plaintext secrets
"""

from collections import deque
from typing import Dict, List, Set, Tuple

from omni_engine.contracts.n8n import (
    N8nWorkflowDetail,
    N8nWorkflowValidationResult,
    N8nTriggerType,
)
from omni_engine.automation.scrubber import SecretScrubber


class N8nWorkflowValidator:
    """Rigorous static validator for n8n workflow definitions."""

    @classmethod
    def validate(cls, workflow: N8nWorkflowDetail) -> N8nWorkflowValidationResult:
        """Performs comprehensive graph validation, cycle detection, and security checks."""
        errors: List[str] = []
        warnings: List[str] = []
        trigger_nodes: List[str] = []
        workflow_hash = workflow.compute_hash()

        nodes = workflow.nodes
        if not nodes:
            return N8nWorkflowValidationResult(
                is_valid=False,
                workflow_hash=workflow_hash,
                errors=["Workflow contains no nodes."],
                warnings=[],
                trigger_nodes=[],
                node_count=0,
                has_cycles=False,
            )

        # 1. Build lookup tables (by name and by id)
        node_by_name = {n.name: n for n in nodes}
        node_by_id = {n.id: n for n in nodes}

        # Check for duplicate node names or duplicate IDs
        if len(node_by_name) < len(nodes):
            seen_names: Set[str] = set()
            for n in nodes:
                if n.name in seen_names:
                    errors.append(f"Duplicate node name found: '{n.name}'. Node names must be unique.")
                seen_names.add(n.name)

        if len(node_by_id) < len(nodes):
            seen_ids: Set[str] = set()
            for n in nodes:
                if n.id in seen_ids:
                    errors.append(f"Duplicate node id found: '{n.id}'. Node IDs must be unique.")
                seen_ids.add(n.id)

        # 2. Identify trigger nodes
        known_trigger_types = {t.value for t in N8nTriggerType}
        for n in nodes:
            lower_type = n.type.lower()
            if (
                n.type in known_trigger_types
                or "trigger" in lower_type
                or "webhook" in lower_type
                or "cron" in lower_type
            ):
                trigger_nodes.append(n.name)

        if not trigger_nodes:
            errors.append(
                "Workflow contains no trigger or entry-point nodes (e.g. webhook, scheduleTrigger, manualTrigger)."
            )

        # 3. Parse 3-level connections map and construct adjacency list
        # adjacency: Dict[node_name, List[target_node_name]]
        adjacency: Dict[str, List[str]] = {n.name: [] for n in nodes}
        in_degrees: Dict[str, int] = {n.name: 0 for n in nodes}
        has_self_loop = False

        connections = workflow.connections or {}
        for src_key, outputs_map in connections.items():
            # Resolve src_node
            src_node = node_by_name.get(src_key) or node_by_id.get(src_key)
            if not src_node:
                errors.append(f"Connection source '{src_key}' does not match any node name or ID.")
                continue

            if not isinstance(outputs_map, dict):
                continue

            for category, output_branches in outputs_map.items():
                if not isinstance(output_branches, list):
                    continue
                for branch in output_branches:
                    if not isinstance(branch, list):
                        continue
                    for edge in branch:
                        if not isinstance(edge, dict):
                            continue
                        target_key = edge.get("node")
                        if not target_key:
                            continue

                        # Resolve target_node
                        target_node = node_by_name.get(target_key) or node_by_id.get(target_key)
                        if not target_node:
                            errors.append(
                                f"Dangling connection: source '{src_node.name}' connects to non-existent node '{target_key}'."
                            )
                            continue

                        # Check self-loop
                        if target_node.name == src_node.name:
                            errors.append(f"Self-loop detected: node '{src_node.name}' connects to itself.")
                            has_self_loop = True
                            continue

                        adjacency[src_node.name].append(target_node.name)
                        in_degrees[target_node.name] += 1

        # 4. Check trigger in-degree invariant (triggers must have in-degree == 0)
        for trig in trigger_nodes:
            if in_degrees.get(trig, 0) > 0:
                errors.append(
                    f"Trigger node '{trig}' has incoming connections (in-degree={in_degrees[trig]}). Trigger nodes cannot have incoming edges."
                )

        # 5. Cycle Detection using 3-color DFS (WHITE=0, GRAY=1, BLACK=2)
        # 0 = unvisited, 1 = visiting (in active recursion stack), 2 = visited
        WHITE, GRAY, BLACK = 0, 1, 2
        colors: Dict[str, int] = {n.name: WHITE for n in nodes}
        has_cycles = has_self_loop
        cycle_paths: List[str] = []

        def _dfs_cycle(node: str, path: List[str]):
            nonlocal has_cycles
            colors[node] = GRAY
            path.append(node)

            for neighbor in adjacency.get(node, []):
                if colors[neighbor] == GRAY:
                    has_cycles = True
                    idx = path.index(neighbor) if neighbor in path else 0
                    cycle_slice = path[idx:] + [neighbor]
                    cycle_paths.append(" -> ".join(cycle_slice))
                elif colors[neighbor] == WHITE:
                    _dfs_cycle(neighbor, path)

            path.pop()
            colors[node] = BLACK

        for n in nodes:
            if colors[n.name] == WHITE:
                _dfs_cycle(n.name, [])

        if cycle_paths:
            for cp in set(cycle_paths):
                errors.append(f"Circular dependency detected in workflow graph: {cp}")

        # 6. Reachability & Orphaned Node Detection (Forward BFS from all triggers)
        reachable: Set[str] = set()
        queue = deque(trigger_nodes)
        for trig in trigger_nodes:
            reachable.add(trig)

        while queue:
            curr = queue.popleft()
            for neighbor in adjacency.get(curr, []):
                if neighbor not in reachable:
                    reachable.add(neighbor)
                    queue.append(neighbor)

        for n in nodes:
            if n.name not in reachable:
                warnings.append(
                    f"Orphaned node '{n.name}' is unreachable from any trigger entry point."
                )

        # 7. Pre-flight Secret Scan on Parameters (REQ-BLOCK-3)
        for n in nodes:
            if SecretScrubber.contains_secret(n.parameters):
                errors.append(
                    f"Node '{n.name}' ({n.type}) contains plaintext secrets or tokens in its parameters. Use vault credential references instead."
                )

        is_valid = len(errors) == 0

        return N8nWorkflowValidationResult(
            is_valid=is_valid,
            workflow_hash=workflow_hash,
            errors=errors,
            warnings=warnings,
            trigger_nodes=trigger_nodes,
            node_count=len(nodes),
            has_cycles=has_cycles,
        )
