"""DAG Graph Utilities for Structured Planning.

Provides topological sorting, cycle detection (3-color DFS),
depth computation, in-degree calculation, and ready-step evaluation (Checkpoint L12).
"""

from typing import Dict, List, Optional, Set, Tuple

from ..contracts.plan import PlanStep, PlanValidationError


class DAGTopology:
    """Graph utility algorithms for planned execution DAGs."""

    @staticmethod
    def detect_cycles(steps: List[PlanStep]) -> Optional[List[str]]:
        """Detects circular dependencies in the planned DAG using 3-color DFS.
        
        Args:
            steps: List of PlanStep nodes.
            
        Returns:
            List of step IDs forming a cycle if detected, or None if DAG is acyclic.
        """
        adj: Dict[str, List[str]] = {s.step_id: list(s.dependencies) for s in steps}
        
        # States: 0 = unvisited (white), 1 = visiting (gray), 2 = visited (black)
        state: Dict[str, int] = {s.step_id: 0 for s in steps}
        parent: Dict[str, Optional[str]] = {s.step_id: None for s in steps}
        cycle_path: Optional[List[str]] = None

        def _dfs(node: str, path: List[str]) -> bool:
            nonlocal cycle_path
            state[node] = 1
            path.append(node)

            for dep in adj.get(node, []):
                if dep not in state:
                    continue  # Unknown dependency handled by schema validation
                if state[dep] == 1:
                    # Found back-edge to visiting node -> cycle!
                    cycle_start_idx = path.index(dep)
                    cycle_path = path[cycle_start_idx:] + [dep]
                    return True
                elif state[dep] == 0:
                    parent[dep] = node
                    if _dfs(dep, path):
                        return True

            path.pop()
            state[node] = 2
            return False

        for step in steps:
            if state[step.step_id] == 0:
                if _dfs(step.step_id, []):
                    return cycle_path

        return None

    @staticmethod
    def topological_sort(steps: List[PlanStep]) -> List[PlanStep]:
        """Orders steps in topological execution order (dependencies before dependents).
        
        Args:
            steps: List of PlanStep nodes.
            
        Returns:
            List of PlanStep objects sorted such that dependencies appear before dependents.
            
        Raises:
            PlanValidationError: If the graph contains a cycle or self-loop.
        """
        cycle = DAGTopology.detect_cycles(steps)
        if cycle:
            raise PlanValidationError(f"Circular dependency detected in plan: {' -> '.join(cycle)}")

        step_map: Dict[str, PlanStep] = {s.step_id: s for s in steps}
        
        # In Kahn's algorithm, an edge A -> B means A is a dependency of B (B depends on A)
        # in_degree[B] = count of dependencies B has
        in_degree: Dict[str, int] = {s.step_id: len(s.dependencies) for s in steps}
        dependents_map: Dict[str, List[str]] = {s.step_id: [] for s in steps}
        for s in steps:
            for dep in s.dependencies:
                if dep in dependents_map:
                    dependents_map[dep].append(s.step_id)

        # Queue nodes with in_degree == 0 (no dependencies)
        queue: List[str] = [step_id for step_id, deg in in_degree.items() if deg == 0]
        # Sort queue by step_id for deterministic ordering
        queue.sort()

        ordered_step_ids: List[str] = []
        while queue:
            current = queue.pop(0)
            ordered_step_ids.append(current)

            for dependent in dependents_map.get(current, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        if len(ordered_step_ids) != len(steps):
            raise PlanValidationError(
                f"Topological sort failed: processed {len(ordered_step_ids)} of {len(steps)} steps. Possible cycle."
            )

        return [step_map[s_id] for s_id in ordered_step_ids]

    @staticmethod
    def compute_plan_depth(steps: List[PlanStep]) -> int:
        """Computes the maximum dependency depth of the DAG.
        
        A step with 0 dependencies has depth 1.
        A step depending on depth-1 step has depth 2.
        An empty plan has depth 0.
        
        Args:
            steps: List of PlanStep nodes.
            
        Returns:
            Maximum integer depth.
        """
        if not steps:
            return 0

        cycle = DAGTopology.detect_cycles(steps)
        if cycle:
            raise PlanValidationError(f"Cannot compute depth of cyclical plan: {' -> '.join(cycle)}")

        # Step map
        step_map: Dict[str, PlanStep] = {s.step_id: s for s in steps}
        depths: Dict[str, int] = {}

        def _get_depth(step_id: str) -> int:
            if step_id in depths:
                return depths[step_id]
            step = step_map.get(step_id)
            if not step or not step.dependencies:
                depths[step_id] = 1
                return 1
            max_dep_depth = max(_get_depth(dep) for dep in step.dependencies if dep in step_map)
            depth = max_dep_depth + 1
            depths[step_id] = depth
            return depth

        return max(_get_depth(s.step_id) for s in steps)

    @staticmethod
    def compute_in_degrees(
        steps: List[PlanStep],
        completed_step_ids: Optional[Set[str]] = None,
    ) -> Dict[str, int]:
        """Calculates unsatisfied dependency count for each step.
        
        Args:
            steps: List of PlanStep nodes.
            completed_step_ids: Set of step IDs that have finished execution.
            
        Returns:
            Dict mapping step_id to unsatisfied in-degree.
        """
        completed = completed_step_ids or set()
        in_degrees: Dict[str, int] = {}
        for s in steps:
            unsatisfied = sum(1 for dep in s.dependencies if dep not in completed)
            in_degrees[s.step_id] = unsatisfied
        return in_degrees

    @staticmethod
    def get_ready_steps(
        steps: List[PlanStep],
        completed_step_ids: Set[str],
        running_or_failed_step_ids: Optional[Set[str]] = None,
    ) -> List[PlanStep]:
        """Identifies steps whose dependencies are 100% satisfied and ready to run.
        
        Args:
            steps: List of PlanStep nodes.
            completed_step_ids: Set of step IDs that have finished execution.
            running_or_failed_step_ids: Set of step IDs currently running or failed.
            
        Returns:
            List of PlanStep objects that can execute immediately.
        """
        excluded = completed_step_ids.union(running_or_failed_step_ids or set())
        ready: List[PlanStep] = []
        for step in steps:
            if step.step_id in excluded:
                continue
            # All dependencies must be in completed_step_ids
            if all(dep in completed_step_ids for dep in step.dependencies):
                ready.append(step)
        return ready
