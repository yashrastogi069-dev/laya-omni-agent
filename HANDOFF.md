# HANDOFF.md — Operational Continuation Guide (Checkpoint L3 Complete)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: Sub-35ms bounded structured decisions via local ModernBERT-large (`laya.Router()`).
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Generative Models**: Invoked strictly for novel planning, structured argument extraction, code generation, and complex synthesis.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `ExecutionReceipt`, `VerificationResult`, `DecisionFrame`, `AgentRequest`, `AgentResponse`, `AgentEvent`, `TraceContext`) without external runtime dependencies.

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L3 COMPLETED**; **L4 ACTIVE (Provider Foundations)**.
- Test Suite: **80/80 tests passing** (+ 23 subtests passed) across `test_l0_baselines.py`, `test_l1_repairs.py`, `test_l2_contracts.py`, `test_l2_1_reconciliation.py`, and `test_l3_capabilities.py`.
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L3 Executed)
1. **Canonical CapabilityRegistry (`omni_engine/capabilities/registry.py`)**:
   - Thread-safe storage via fine-grained `threading.RLock()` scoping (locks held strictly for lookups, never during tool execution).
   - Enforces unique capability IDs, rejects duplicate registrations and unawaited coroutines.
   - Standard execution boundary `invoke(CapabilityInvocation) -> ToolResult`.
   - Automatic `ExecutionReceipt` generation recording epoch timestamps and sub-millisecond durations.
   - Clean propagation of process-control exceptions (`KeyboardInterrupt`, `SystemExit`, `GeneratorExit` are NEVER caught).
2. **Specialized Kwarg Adapters (`omni_engine/capabilities/adapters.py`)**:
   - Created dedicated kwarg normalization adapters for all 12 tools whose signatures or formats differ from canonical schemas (`visual_browse`, `list_processes`, `kill_process`, `search_code`, `directory_tree`, `run_python`, `sqlite_exec`, `file_write`, `http_api`, `download_file`, `clipboard`, `inspect_data`).
   - Every single one of the 23 capabilities accepts its valid schema arguments without `TypeError`.
3. **Prefix-Anchored Error Interception (`omni_engine/capabilities/adapters.py`)**:
   - Replaced unanchored substring matching with prefix-anchored checks.
   - Intercepts all legacy error signatures (`❌ File not found:`, `Write error:`, `Git error:`, `Ping test error:`, `Failed to terminate process:`, etc.).
   - Eliminates false-positives on content-bearing tools (`file_read`, `search_code`) when files contain phrases like "Access is denied" or "API key missing".
4. **Canonical Specifications (`omni_engine/capabilities/definitions.py`)**:
   - Defined all 23 canonical `CapabilitySpec` instances with 100% parity with `OMNI_TOOL_REGISTRY`.
   - Strict action classes, autonomy tiers, confirmation policies, retry policies, and idempotency classes.
5. **Legacy Compatibility & Non-Switching Boundary**:
   - Preserved `omni_engine.tools.OMNI_TOOL_REGISTRY` and CLI paths intact.
   - Production agent dispatch in `omni_agent.py` and `omni_engine/planner.py` remains untouched until L8 and L9.
6. **Tests & Adversarial Review**:
   - `tests/test_l3_capabilities.py` (25 unit tests + 23 subtests). Total repository suite: **80 passed in 32.99s**.
   - Adversarial plan and diff reviews completed and all findings remediated.

---

## Files to Read Next
1. `tasks/ACTIVE_PLAN.md` — Target plan for Checkpoint L4 (Provider Foundations).
2. `tasks/MASTER_PLAN.md` — Full strategic roadmap (L0–L25).
3. `omni_engine/capabilities/` — Completed canonical capability substrate.
4. `omni_engine/system1.py` & `omni_engine/system2.py` — Existing model callers to be abstracted in L4.

---

## Tests to Run
```powershell
pytest tests/ -v
```

---

## Things NOT to Change
- **DO NOT** switch the main agent dispatch loop to the new registry before Checkpoints L8 (Typed Argument Resolver) and L9 (Policy Engine) exist.
- **DO NOT** commit API secrets or keys to git.
- **DO NOT** preload multiple heavy generative models locally (respect host RAM limits).
- **DO NOT** delete legacy prototype files (`omni_agent.py`, etc.).
- **DO NOT** run destructive git commands (`git reset --hard`, `git clean -fd`).

---

## Exact Next Action
Begin Checkpoint L4 (Provider Foundations):
- Implement `omni_engine/providers/system1.py` (`SystemOneProvider`, `LayaProvider`, optional `JevProvider`).
- Implement `omni_engine/providers/generative.py` (`GenerativeProvider`, `OpenRouterProvider`).
- Record latency profiling, model provenance, and health checks.

---

NEXT AGENT START HERE
