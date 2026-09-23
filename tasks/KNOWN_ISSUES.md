# KNOWN_ISSUES.md — Defect and Flaw Tracking

## Active Issue Index

### ISSUE-01: `tool_safe_math` NameError on Missing `re` Import
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint L1)**
- **Resolution**: Added `import re` and implemented a strict `ast.NodeVisitor` mathematical evaluator in `omni_engine/tools/data_tools.py`. Whitelisted safe arithmetic operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`), math library functions (`sqrt`, `abs`, `round`, `sin`, `cos`, etc.), and safe constants (`pi`, `e`, `tau`). Added safeguards against computational exhaustion (`**` exponent capped at 100) and sandbox injection (`__import__`, attribute access, open).
- **Regression Test**: `tests/test_l1_repairs.py::TestL1SafeMathRepairs` (7 passed tests).

---

### ISSUE-02: `System1Router.route_tool` Slices Catalog to First 12 Items
- **Severity**: CRITICAL
- **Status**: OPEN (Slated for Checkpoint L6 — Hierarchical Capability Routing)
- **Reproduction**:
  `criteria = {k: v["desc"][:85] for k, v in list(tool_catalog.items())[:12]}`.
  Tools after index 11 (`powershell`, `file_read`, `file_write`, `run_python`, etc.) are excluded from System 1.
- **Architectural Directive**: Naive flat 23-tool dump is **REJECTED**. The resolution must be Hierarchical Capability Routing (`Request → Domain → Skill → Candidate Set → Capability`) scheduled for Checkpoint L6.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0ConfirmedDefects::test_defect_system1_tool_catalog_truncation`.

---

### ISSUE-03: Natural Language User Prompt Passed Verbatim as Tool Argument
- **Severity**: CRITICAL
- **Status**: OPEN (Slated for Checkpoint L8 — Typed Capability Argument Resolver)
- **Reproduction**:
  `result = tool_func(mission_prompt)` passes raw user prompt string to tools expecting clean paths or structured payloads.
- **Resolution Plan**: Build typed `ArgumentResolver` in Checkpoint L8.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0ConfirmedDefects::test_defect_prompt_passed_directly_as_file_read_arg`.

---

### ISSUE-04: Memory JSON Schema Key Inconsistency
- **Severity**: HIGH
- **Status**: **RESOLVED (Checkpoint L1)**
- **Resolution**: Updated `OmniMemory._load()` in `omni_engine/memory.py` to dynamically migrate legacy keys (`tool_effectiveness` → `tool_success_counts`, `learned_facts` → `learned_insights`) with backward-compatible normalization. Implemented atomic file persistence (write-to-tmp then atomic replace) to prevent crash corruption, and separated raw invocations from verified successful outcomes.
- **Regression Test**: `tests/test_l1_repairs.py::TestL1MemoryRepairs` (4 passed tests).

---

### ISSUE-05: Dead Code in Planner and System 2
- **Severity**: MEDIUM
- **Status**: OPEN (Slated for Checkpoint L10/L12)
- **Reproduction**:
  `AutonomousPlanner.is_complex_multi_step()` and `System2Engine.escalate_to_antigravity()` are defined but never called in active runtime.
- **Resolution Plan**: Superseded by Quest engine and DAG planner in Checkpoints L10–L12.

---

### ISSUE-06: Discrepancy Between README Browser Capabilities and Codebase
- **Severity**: MEDIUM
- **Status**: OPEN (Slated for Checkpoint L18)
- **Reproduction**:
  README lists `browser_navigate`, `browser_click_element`, `browser_type_text`, `browser_extract_text`. `omni_engine/tools/browser_tools.py` only defines monolithic `tool_visual_browse` and `tool_browser_screenshot`.
- **Resolution Plan**: Rebuild Playwright Edge into atomic, session-backed primitives in Checkpoint L18.
