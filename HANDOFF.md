# HANDOFF.md — Operational Continuation Guide

## What We Are Building
A reliable, low-latency, persistent autonomous personal operating agent where:
- **LAYA** is the primary high-frequency System 1 decision engine (<35ms, local `ModernBERT-large`).
- **Deterministic code** strictly owns state machines, permissions, operation identity, idempotency, and DAG execution.
- **System 2 (Generative Models)** are invoked solely for novel planning, structured argument extraction, code writing, and synthesis.
- **Every capability** has a strongly typed contract (`CapabilitySpec`), action classification, and evidence-based verifier.
- **Multi-step missions** execute through a persisted SQLite Quest engine.

---

## Current Architecture & State
- Repository is synchronized with public GitHub: `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `main`.
- Active Checkpoint: **L0 completed**, preparing **L1**.
- Current CLI runner: `laya_agent.py` backed by `omni_engine/`.
- 10 automated tests are in place (`tests/test_l0_baselines.py`) establishing baseline ground truth and defect reproduction.

---

## Last Changes
1. Audited the complete codebase and mapped all 22 python files, 5 batch scripts, and tool modules.
2. Verified that zero automated test assertions previously existed.
3. Created `tests/test_l0_baselines.py` asserting registry size (23 tools), defect reproduction (`safe_math` NameError, System 1 `[:12]` truncation, prompt-as-argument), and working tools.
4. Installed `pytest` and verified test suite execution (10/10 passed).
5. Created canonical governance documentation: `AGENTS.md`, `LAYA_BUILD_STATE.md`, `tasks/`, `docs/`.

---

## Unresolved Problems (Tracked in `tasks/KNOWN_ISSUES.md`)
1. **ISSUE-01 (CRITICAL)**: `tool_safe_math` in `omni_engine/tools/data_tools.py` crashes on call with `NameError: name 're' is not defined`.
2. **ISSUE-02 (CRITICAL)**: `System1Router.route_tool` in `omni_engine/system1.py` truncates `tool_catalog` to `[:12]`, leaving 11 tools completely unroutable.
3. **ISSUE-03 (CRITICAL)**: `AutonomousPlanner` passes natural-language user prompt directly to tool functions (`tool_func(mission_prompt)`), causing runtime failures in tools expecting structured inputs.
4. **ISSUE-04 (HIGH)**: `OmniMemory` schema previously had conflicting keys (`tool_effectiveness` vs `tool_success_counts`).
5. **ISSUE-05 (MEDIUM)**: Dead code: `AutonomousPlanner.is_complex_multi_step()` and `System2Engine.escalate_to_antigravity()` are never invoked in main runtime.
6. **ISSUE-06 (MEDIUM)**: Browser capabilities in README (`browser_navigate`, `browser_click_element`, `browser_type_text`, `browser_extract_text`) do not exist in `omni_engine/tools/browser_tools.py`.

---

## Files to Read Next
1. `tasks/ACTIVE_PLAN.md` — Execution plan for Checkpoint L1.
2. `tasks/MASTER_PLAN.md` — Complete L0–L25 roadmap.
3. `tasks/KNOWN_ISSUES.md` — Defect reproduction and fix criteria.
4. `docs/ARCHITECTURE.md` — Current vs Target system architecture.
5. `tests/test_l0_baselines.py` — Existing regression tests.
6. `omni_engine/tools/data_tools.py` — Target for L1 `safe_math` fix.
7. `omni_engine/system1.py` — Target for L1 catalog truncation fix.
8. `omni_engine/memory.py` — Target for L1 schema synchronization.

---

## Tests to Run
```powershell
python -m pytest tests/test_l0_baselines.py -v
```

---

## Things NOT to Change
- **DO NOT** delete legacy prototype files (`omni_agent.py`, `ultimate_autonomous_agent.py`, etc.) until Checkpoint L25.
- **DO NOT** run destructive git commands (`git reset --hard`, `git clean -fd`).
- **DO NOT** remove LAYA as the primary System 1 decision engine.
- **DO NOT** introduce heavyweight external dependencies (Kafka, Redis, Kubernetes). Keep local-first with SQLite.

---

## Exact Next Action
Begin Checkpoint L1:
1. Fix `tool_safe_math` by adding `import re` and robust arithmetic evaluation.
2. Fix `System1Router.route_tool` to eliminate the `[:12]` slice and route across all registered tools.
3. Synchronize `OmniMemory` schema and add memory test.
4. Add unit tests verifying fixes and run `pytest`.

---

NEXT AGENT START HERE
