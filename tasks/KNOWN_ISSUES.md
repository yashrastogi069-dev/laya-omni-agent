# KNOWN_ISSUES.md — Defect and Flaw Tracking

## Active Issue Index

### ISSUE-01: `tool_safe_math` NameError on Missing `re` Import & Computational Exhaustion
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint L1 & L1.1)**
- **Resolution**: Added `import re` and implemented a strict `ast.NodeVisitor` mathematical evaluator in `omni_engine/tools/data_tools.py`. Whitelisted safe arithmetic operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`), math library functions (`sqrt`, `abs`, `round`, `sin`, `cos`, etc.), and safe constants (`pi`, `e`, `tau`). In L1.1, added strict deterministic resource bounds:
  - Expression length <= 256 chars
  - AST node count <= 40 nodes
  - Factorial parameter limit: integer only, 0 <= n <= 100
  - Literal magnitude <= 1e100
  - Exponent magnitude abs(exp) <= 100, base <= 1e6 if exp > 10
- **Regression Test**: `tests/test_l1_repairs.py::TestL1SafeMathRepairs` (7 passed tests).

---

### ISSUE-02: `System1Router.route_tool` Slices Catalog to First 12 Items
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoints L6A & L6B)**
- **Resolution**: Implemented `HierarchicalRouter` in `omni_engine/routing/router.py`. Eliminates flat catalog dumps and fixed slices by routing through `Request → Domain → Skill → Small Candidate Set → Capability`, with automatic cross-domain pooling, keyword capability pinning, and anti-locking defenses.
- **Regression Test**: `tests/test_l6a_routing.py` and `tests/test_l6b_skill_routing.py`.

---

### ISSUE-03: Natural Language User Prompt Passed Verbatim as Tool Argument
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint L8)**
- **Resolution**: Implemented `ArgumentResolver` in `omni_engine/arguments/resolver.py` with deterministic regex and AST extractors in `extractors.py`, schema validation against `CapabilitySpec.input_schema`, alias bridging (`PARAM_ALIASES`), and structured clarification prompting (`CLARIFICATION_PROMPTS`).
- **Regression Test**: `tests/test_l8_arguments.py` (26 tests passing).

---

### ISSUE-04: Memory JSON Schema Key Inconsistency & Success Conflation
- **Severity**: HIGH
- **Status**: **RESOLVED (Checkpoint L1 & L1.1)**
- **Resolution**: Updated `OmniMemory._load()` in `omni_engine/memory.py` to dynamically migrate legacy keys (`tool_effectiveness` → `tool_success_counts`, `learned_facts` → `learned_insights`) with backward-compatible normalization. Implemented atomic file persistence (write-to-tmp then atomic replace) to prevent crash corruption. In L1.1:
  - Default outcome changed to `UNVERIFIED` (None). Execution never automatically implies verified success.
  - Three distinct outcome states tracked: `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`.
  - Invocations, verified successes, verified failures, and unverified runs tracked separately.
  - Corrupted or unparseable JSON files are automatically quarantined to `<filepath>.corrupt.<timestamp>` to preserve historical telemetry while recovering clean defaults.
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
- **Status**: **RESOLVED (Phase R2: Real Browser Engine)**
- **Resolution**: Implemented persistent session-backed Playwright engine (`omni_engine/browser/`) exposing atomic indexed action space (`@1..@N`), semantic fingerprinting, pre-execution staleness verification, evidence-based physical receipts (`dom_mutated`, `input_value`, `url_changed`), and registered capabilities `browser.interact` and `browser.perform_task`.
- **Regression Test**: `tests/test_r2_browser.py` (15 unit and integration tests passing offline).

---

### ISSUE-07: `WorkspaceConfiner.safe_revert` Wiping Pre-Existing Uncommitted User Work (Dirty Worktree Invariant)
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint RV0 Reality Gate)**
- **Description**: `WorkspaceConfiner.safe_revert()` inspected `git status --porcelain` and removed any untracked file (`??`) and checked out any modified file (`M`), which would destroy user work that existed in the working tree prior to task execution.
- **Resolution**: Implemented `WorkspaceConfiner.capture_baseline_state()` and updated `safe_revert(..., baseline_state=baseline_state)` to capture pre-existing dirty files and content byte-for-byte. Untracked baseline files are never deleted, and modified baseline files are restored to their exact baseline contents rather than clean git commit baseline.
- **Regression Test**: `tests/test_rv0_reality_gate.py::test_rv0_f_mandatory_dirty_worktree_survival` (passes 100%).

