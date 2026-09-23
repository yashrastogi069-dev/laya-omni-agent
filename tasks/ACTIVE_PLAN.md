# ACTIVE_PLAN.md — Checkpoint L1: Critical Defect Repair & Regressions

## Objective
Remediate the confirmed runtime defects identified during Checkpoint L0 reconnaissance and incorporate mitigations from the Adversarial Systems Review:
1. Fix `NameError: name 're' is not defined` in `tool_safe_math` (`omni_engine/tools/data_tools.py`) using a strict `ast.NodeVisitor` whitelist (only numeric constants, binary/unary operations, and safe math functions), with strict bounds on exponentiation (`**`) to prevent computational exhaustion (e.g. `9**9**9**9`).
2. Fix catalog truncation in `System1Router.route_tool` (`omni_engine/system1.py`) by removing the hardcoded `[:12]` slice and replacing it with dynamic description compression and safe length limits so all 23 registered tools are evaluable without exceeding ModernBERT context limits.
3. Synchronize `OmniMemory` schema keys (`tool_success_counts`, `learned_insights`) in `omni_engine/memory.py` with backward-compatibility for legacy files, and implement atomic file writes (write-to-tmp then replace) to prevent zero-byte file corruption during crashes.

---

## Affected Files
- `omni_engine/tools/data_tools.py` — add missing `import re`, implement strict AST NodeVisitor with exponent bounds.
- `omni_engine/system1.py` — expand criteria to include all 23 tools with compressed descriptions.
- `omni_engine/memory.py` — backward-compatible key loading and atomic write persistence.
- `memory/omni_memory.json` — ensure clean initial JSON structure matching memory engine.
- `tests/test_l1_repairs.py` — new regression test suite verifying fixes and edge cases (computational exhaustion rejection, memory corruption resilience).

---

## Acceptance Criteria
1. `tool_safe_math("2 + 2")` evaluates successfully and returns formatted result without `NameError`.
2. `tool_safe_math` rejects dangerous AST constructs (`__import__`, attribute access, eval) and rejects massive exponents (`9**9**9**9` or exponent > 100) before execution.
3. `System1Router.route_tool` includes all 23 registered tools in the criteria dict without exceeding context constraints.
4. `OmniMemory` loads, saves, and records missions atomically without raising `KeyError`, and handles corrupted/empty JSON gracefully.
5. `pytest tests/` runs both `test_l0_baselines.py` and `test_l1_repairs.py` with 100% pass rate.

---

## Rollback Plan
If regressions occur:
- Restore previous state of target files using `git checkout -- <file>`.
- Re-run `test_l0_baselines.py` to confirm baseline stability.
