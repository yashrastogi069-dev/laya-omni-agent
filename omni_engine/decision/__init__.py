"""
omni_engine.decision
====================
System 1 Decision Fabric package exports.
"""

from .fabric import DecisionFabric, DEFAULT_HIGH_RISK_PATTERNS
from .corpus import BENCHMARK_CORPUS, evaluate_decision_corpus

__all__ = [
    "DecisionFabric",
    "DEFAULT_HIGH_RISK_PATTERNS",
    "BENCHMARK_CORPUS",
    "evaluate_decision_corpus",
]
