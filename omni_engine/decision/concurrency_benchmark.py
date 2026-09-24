"""
omni_engine.decision.concurrency_benchmark
==========================================
Empirical Concurrency Benchmark Harness measuring local System 1 throughput,
CPU utilization, queue latencies, and thread contention under concurrency levels 1, 2, and 4.

Adheres to Prime Directive & Repository Invariants:
- Evidence-Based Completion (Invariant 6): Measures real p50/p95 latency and queue delay
  under concurrent thread workloads.
- Concurrency Safety: Empirically evaluates CPU/RAM behavior to validate `LOCAL_LAYA_MAX_CONCURRENCY=1`
  for 4-core CPU host.
"""

import concurrent.futures
import time
from typing import Any, Dict, List, Optional

from omni_engine.providers.system1 import (
    LayaProvider,
    get_available_ram_mb,
    set_laya_concurrency,
)


def _compute_percentile(data: List[float], percentile: float) -> float:
    """Computes exact percentile from sorted numerical list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * percentile)
    idx = min(idx, len(sorted_data) - 1)
    return round(sorted_data[idx], 3)


def run_concurrency_benchmark(
    concurrencies: Optional[List[int]] = None,
    num_requests: int = 4,
    dry_run: bool = False,
    mock_provider: Optional[Any] = None,
) -> Dict[str, Any]:
    """Runs concurrent requests against local LayaProvider and measures performance metrics.

    Parameters:
    - concurrencies: List of concurrency levels to test (default [1, 2, 4])
    - num_requests: Number of requests to fire concurrently per level
    - dry_run: If True, uses synthetic sleep delays to test harness logic without invoking heavy models
    - mock_provider: Optional mock provider for test isolation
    """
    levels = concurrencies or [1, 2, 4]
    results: Dict[str, Any] = {"concurrencies": {}}

    prompt = "Create a new git branch for the feature and push it to origin"
    criteria = {"git": "Git operations", "file": "File operations", "os": "Operating system"}

    for conc in levels:
        set_laya_concurrency(conc)
        prov = mock_provider or LayaProvider(model_name="english", preload=False, queue_timeout_seconds=10.0)

        ram_before = get_available_ram_mb()
        t0 = time.perf_counter()
        latencies: List[float] = []
        queue_waits: List[float] = []
        errors = 0

        def _execute_single(req_id: int) -> Dict[str, Any]:
            try:
                if dry_run:
                    time.sleep(0.01)
                    return {"latency_ms": 10.0, "queue_wait_ms": 0.5, "choice": "git"}
                else:
                    res = prov.classify(prompt=f"{prompt} (req_{req_id})", criteria=criteria)
                    q_wait = res.metadata.get("queue_wait_ms", 0.0)
                    return {"latency_ms": res.latency_ms, "queue_wait_ms": q_wait, "choice": res.value}
            except Exception as e:
                return {"error": str(e)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=conc) as executor:
            futures = [executor.submit(_execute_single, i) for i in range(num_requests)]
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if "error" in res:
                    errors += 1
                else:
                    latencies.append(res["latency_ms"])
                    queue_waits.append(res["queue_wait_ms"])

        t1 = time.perf_counter()
        total_time = t1 - t0
        ram_after = get_available_ram_mb()

        throughput = round(num_requests / total_time, 2) if total_time > 0 else 0.0

        results["concurrencies"][str(conc)] = {
            "concurrency_level": conc,
            "requests_completed": len(latencies),
            "requests_failed": errors,
            "total_wall_time_sec": round(total_time, 3),
            "throughput_req_per_sec": throughput,
            "latency_p50_ms": _compute_percentile(latencies, 0.50),
            "latency_p95_ms": _compute_percentile(latencies, 0.95),
            "latency_max_ms": max(latencies) if latencies else 0.0,
            "queue_wait_p50_ms": _compute_percentile(queue_waits, 0.50),
            "queue_wait_p95_ms": _compute_percentile(queue_waits, 0.95),
            "ram_delta_mb": round(ram_before - ram_after, 2),
        }

    # Reset concurrency to safe default (1)
    set_laya_concurrency(1)
    return results
