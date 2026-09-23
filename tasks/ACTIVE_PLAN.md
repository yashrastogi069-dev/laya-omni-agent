# ACTIVE_PLAN.md — Checkpoint L1: Critical Local Reliability Repairs

## 1. Objective
Remediate confirmed foundational runtime defects to ensure LAYA's baseline execution, memory, and evaluation infrastructure is robust and crash-free before constructing higher-level contracts.

Do **NOT** implement an unconstrained flat 23-tool dump into `System1Router`. Hierarchical capability routing is scheduled for Checkpoint L6.

---

## 2. Checkpoint Scope

### Item 1: `tool_safe_math` Repair (`omni_engine/tools/data_tools.py`)
- **Problem**: Missing `import re` causes immediate `NameError`. Unconstrained `eval()` allows potential sandbox escapes and computational exhaustion (`9**9**9**9`).
- **Fix**:
  1. Add `import re`.
  2. Implement an AST-based mathematical expression evaluator (`ast.NodeVisitor` / `ast.parse`).
  3. Strictly whitelist safe AST nodes: `ast.Expression`, `ast.BinOp`, `ast.UnaryOp`, `ast.Constant`, `ast.Name`, `ast.Call`.
  4. Whitelist permitted math functions from `math` (`sqrt`, `sin`, `cos`, `tan`, `log`, `floor`, `ceil`, `abs`, `round`).
  5. Enforce safety bounds on exponentiation: reject exponents greater than 100 to prevent computational exhaustion (`9**9**9**9`).
  6. Reject all attribute lookups (`ast.Attribute`), imports, indexing, comprehensions, and statements.

### Item 2: `OmniMemory` Schema Normalization & Atomic Persistence (`omni_engine/memory.py`)
- **Problem**: Mismatch between `tool_effectiveness` in loaded JSON and `tool_success_counts` in code causes `KeyError`. Direct non-atomic `open(..., "w")` risks zero-byte file corruption on process crash. Execution count is incremented blindly without distinguishing execution from verified success.
- **Fix**:
  1. In `_load()`: Migrate legacy keys dynamically (`tool_effectiveness` → `tool_success_counts`, `learned_facts` → `learned_insights`).
  2. In `record_mission()`: Accept an optional `success: bool = True` parameter; track both total invocations and verified successes.
  3. In `save()`: Implement atomic file writes (write to `omni_memory.json.tmp` then `os.replace`) to eliminate crash corruption.
  4. Add corrupted/empty file resilience: if the JSON file is empty or corrupted, recover with defaults rather than raising unhandled JSONDecodeError.

### Item 3: System 1 `[:12]` Legacy Defect Preservation & Labeling (`omni_engine/system1.py`)
- **Requirement**: Maintain the regression test proving the `[:12]` truncation defect.
- **Rule**: Do NOT implement a naive flat 23-tool dump. Keep the current slice clearly labeled as a legacy standalone prototype constraint; architectural resolution belongs to **L6 (Hierarchical Capability Routing)**.

### Item 4: Smoke & Integration Tests (`tests/test_l1_repairs.py`)
- Test safe arithmetic: `2 + 2`, `sqrt(16)`, `sin(0)`, `abs(-10)`, `round(3.14159, 2)`.
- Test safety rejection: `9**9**9**9` (exhaustion), `__import__('os')` (injection), `open('foo')` (file access).
- Test memory normalization: load legacy JSON with `tool_effectiveness`, verify no `KeyError`, verify atomic write created valid JSON.
- Test import/startup smoke: verify all `omni_engine` submodules import cleanly without warnings or errors.

---

## 3. Acceptance Criteria
1. `tool_safe_math("2 + 2")` returns `"### Math Evaluation:\n`2 + 2` = **4**"` with zero `NameError`.
2. `tool_safe_math("9**9**9**9")` returns `"Expression rejected for safety (exponent too large)."` within <10ms.
3. `tool_safe_math("__import__('os').system('dir')")` returns `"Expression rejected for safety."`.
4. `OmniMemory` initializes, loads legacy JSON, records missions, and saves atomically without raising `KeyError` or crashing.
5. All tests in `tests/test_l0_baselines.py` and `tests/test_l1_repairs.py` pass 100% via `pytest`.

---

## 4. Rollback Plan
- Restore modified files using `git checkout -- omni_engine/tools/data_tools.py omni_engine/memory.py`.
- Re-run `python -m pytest tests/test_l0_baselines.py` to confirm baseline stability.
