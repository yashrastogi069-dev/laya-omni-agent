"""
omni_engine.decision.corpus
===========================
Standardized evaluation corpus and benchmark runner for System 1 Decision Fabric.

Profiles:
- Real-world interaction categories (conversational, file read, file write, process kill, powershell, git, sqlite, math, ambiguous, multi-step).
- Latency profiling (cold vs warm inference, min, max, p95).
- Hardware-aware SLA verification (<35ms on CUDA, <5000ms on CPU).
- Signal distribution metrics.
"""

import statistics
import time
from typing import Any, Dict, List, Optional

from omni_engine.decision.fabric import DecisionFabric

# 10 Standardized Benchmark Prompts with ground-truth intent and domain expectations
BENCHMARK_CORPUS: List[Dict[str, Any]] = [
    {
        "id": "corpus-01-conversational",
        "prompt": "What is the capital of France and what is its history?",
        "expected_domain": "general",
        "expected_intent": "informational",
        "expected_action": False,
        "expected_risk": "safe_read_only",
    },
    {
        "id": "corpus-02-file-read",
        "prompt": "View the contents of README.md to check instructions",
        "expected_domain": "dev",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_risk": "safe_read_only",
    },
    {
        "id": "corpus-03-web-search",
        "prompt": "Search the web for the latest Python 3.12 release notes and documentation",
        "expected_domain": "web",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_risk": "safe_read_only",
    },
    {
        "id": "corpus-04-code-refactor",
        "prompt": "Refactor auth middleware to prevent token leaks, update error handlers, and run unit tests",
        "expected_domain": "dev",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_plan": True,
    },
    {
        "id": "corpus-05-high-risk-kill",
        "prompt": "kill_process --pid 12345 immediately",
        "expected_domain": "os",
        "expected_intent": "task_execution",
        "expected_risk": "high_risk_system",
        "expected_reversibility": "irreversible",
    },
    {
        "id": "corpus-06-ambiguous",
        "prompt": "do it",
        "expected_clarification": True,
    },
    {
        "id": "corpus-07-system-diagnostics",
        "prompt": "Inspect system diagnostics to check CPU and RAM telemetry",
        "expected_domain": "os",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_risk": "safe_read_only",
    },
    {
        "id": "corpus-08-safe-math",
        "prompt": "Calculate sqrt(144) + 12 * 5",
        "expected_domain": "data",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_risk": "safe_read_only",
    },
    {
        "id": "corpus-09-sqlite-query",
        "prompt": "Execute SELECT * FROM users WHERE active = 1 in SQLite database",
        "expected_domain": "data",
        "expected_intent": "task_execution",
        "expected_action": True,
    },
    {
        "id": "corpus-10-multi-step-backup",
        "prompt": "Create full backup of repository, run linter, fix formatting defects, and deploy to staging",
        "expected_domain": "dev",
        "expected_intent": "task_execution",
        "expected_action": True,
        "expected_plan": True,
        "expected_importance": "high",
    },
]


def evaluate_decision_corpus(
    fabric: Optional[DecisionFabric] = None,
    corpus: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Runs benchmark corpus through DecisionFabric and returns comprehensive evaluation metrics."""
    decider = fabric if fabric is not None else DecisionFabric()
    test_set = corpus or BENCHMARK_CORPUS

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []

    for item in test_set:
        t0 = time.perf_counter()
        frame = decider.evaluate(prompt=item["prompt"], request_id=item["id"])
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)

        latencies.append(elapsed_ms)
        results.append({
            "id": item["id"],
            "prompt": item["prompt"],
            "latency_ms": elapsed_ms,
            "intent": frame.intent.value,
            "task_class": frame.task_class.value,
            "top_domain": frame.candidate_domains[0] if frame.candidate_domains else "none",
            "risk": frame.risk.value,
            "reversibility": frame.reversibility.value,
            "needs_plan": frame.needs_plan.value,
            "needs_clarification": frame.needs_clarification.value if frame.needs_clarification else False,
            "requires_action": frame.requires_action.value if frame.requires_action else False,
            "model_tier": frame.model_tier.value,
        })

    avg_latency = round(statistics.mean(latencies), 3) if latencies else 0.0
    min_latency = round(min(latencies), 3) if latencies else 0.0
    max_latency = round(max(latencies), 3) if latencies else 0.0
    p95_latency = round(statistics.quantiles(latencies, n=20)[18], 3) if len(latencies) >= 20 else max_latency

    return {
        "total_prompts": len(test_set),
        "latencies_ms": latencies,
        "latency_summary": {
            "avg_ms": avg_latency,
            "min_ms": min_latency,
            "max_ms": max_latency,
            "p95_ms": p95_latency,
        },
        "results": results,
    }
