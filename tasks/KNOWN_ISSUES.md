# KNOWN_ISSUES.md — Defect and Flaw Tracking

## Active Issue Index

### ISSUE-01: `tool_safe_math` NameError on Missing `re` Import
- **Severity**: CRITICAL
- **Status**: OPEN
- **Checkpoint**: L1
- **Reproduction**:
  ```python
  from omni_engine.tools.data_tools import tool_safe_math
  tool_safe_math("2 + 2")
  # Raises: NameError: name 're' is not defined
  ```
- **Cause**: Line 69 of `omni_engine/tools/data_tools.py` references `re.sub()` but `import re` is omitted at the top of the module.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0ConfirmedDefects::test_defect_safe_math_missing_re_import`

---

### ISSUE-02: `System1Router.route_tool` Slices Catalog to First 12 Items
- **Severity**: CRITICAL
- **Status**: OPEN
- **Checkpoint**: L1
- **Reproduction**:
  ```python
  from omni_engine.system1 import System1Router
  from omni_engine.tools import OMNI_TOOL_REGISTRY
  # Observe that tools 13-23 are never evaluated in criteria
  ```
- **Cause**: Line 42 of `omni_engine/system1.py` executes:
  `criteria = {k: v["desc"][:85] for k, v in list(tool_catalog.items())[:12]}`.
  Tools after index 11 (`powershell`, `file_read`, `file_write`, `run_python`, etc.) are completely excluded.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0ConfirmedDefects::test_defect_system1_tool_catalog_truncation`

---

### ISSUE-03: Natural Language User Prompt Passed Verbatim as Tool Argument
- **Severity**: CRITICAL
- **Status**: OPEN
- **Checkpoint**: L8 (Requires Argument Resolution Layer)
- **Reproduction**:
  ```python
  from omni_engine.tools.dev_tools import tool_file_read
  tool_file_read("read the file README.md")
  # Returns: ❌ File not found: C:\...\read the file README.md
  ```
- **Cause**: `AutonomousPlanner.plan_and_execute` executes `result = tool_func(mission_prompt)` directly without argument extraction or schema validation.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0ConfirmedDefects::test_defect_prompt_passed_directly_as_file_read_arg`

---

### ISSUE-04: Memory JSON Schema Key Inconsistency
- **Severity**: HIGH
- **Status**: OPEN
- **Checkpoint**: L1
- **Reproduction**:
  When `memory/omni_memory.json` contains legacy keys `tool_effectiveness` and `learned_facts`, calling `record_mission` attempts to index `self.data["tool_success_counts"]`, raising `KeyError`.
- **Cause**: Mismatch between the initial JSON file schema and the in-code default dictionary in `omni_engine/memory.py`.
- **Regression Test**: `tests/test_l0_baselines.py::TestL0MemoryInvariants`

---

### ISSUE-05: Dead Code in Planner and System 2
- **Severity**: MEDIUM
- **Status**: OPEN
- **Checkpoint**: L10 / L12
- **Reproduction**:
  - `AutonomousPlanner.is_complex_multi_step()` is defined in `planner.py` but never called.
  - `System2Engine.escalate_to_antigravity()` is defined in `system2.py` but never called.
- **Cause**: Incomplete prototype integration during initial development.
- **Regression Test**: Static codebase analysis / unit tests in L12.

---

### ISSUE-06: Discrepancy Between README Browser Capabilities and Codebase
- **Severity**: MEDIUM
- **Status**: OPEN
- **Checkpoint**: L18
- **Reproduction**:
  README lists `browser_navigate`, `browser_click_element`, `browser_type_text`, `browser_extract_text`. `omni_engine/tools/browser_tools.py` only defines `tool_visual_browse` and `tool_browser_screenshot`.
- **Cause**: Aspirational documentation written ahead of modular Playwright implementation.
- **Regression Test**: Will be validated in Checkpoint L18.
