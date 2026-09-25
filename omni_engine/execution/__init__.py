"""omni_engine.execution
====================
Deterministic DAG Executor and Dynamic Resolution Engine (Checkpoint L14).
"""

from .dynamic_resolver import DynamicResolver
from .executor import DeterministicDAGExecutor

__all__ = [
    "DynamicResolver",
    "DeterministicDAGExecutor",
]
