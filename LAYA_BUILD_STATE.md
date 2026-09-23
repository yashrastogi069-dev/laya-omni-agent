# LAYA_BUILD_STATE.md — Current Ground Truth State

**Last Updated**: 2026-09-23T08:50:00+05:30  
**Current Branch**: `laya-autonomous-v2`  
**Active Checkpoint**: `L2.1 — Contract & Registry Reconciliation` (**COMPLETED**; preparing L3A)  
**Last Passing Test Suite**: `tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`, `tests/test_l2_1_reconciliation.py` (**55/55 passed via pytest in 6.22s**)  
**Mission Role**: Complete Standalone Autonomous Operating Agent.

---

## 1. Current Architecture Summary

The repository contains a standalone prototype CLI (`laya_agent.py` / `omni_engine/`) transitioning towards a **complete standalone autonomous operating agent**:
1. **System 1**: Local ModernBERT-large (`laya.Router()`) providing high-frequency decisions (<35ms).
2. **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, and execution.
3. **Phased Roadmap**: Checkpoints L0–L25 sequential evolution.
4. **Checkpoint L1 & L1.1 Milestone Reached**:
   - `tool_safe_math` rewritten with strict AST NodeVisitor, length limits (<= 256), node limits (<= 40), literal limits (<= 1e100), factorial limits (0 <= n <= 100), and exponent bounds (abs <= 100).
   - `OmniMemory` rewritten with dynamic schema key migration, atomic file persistence, corruption quarantining (`.corrupt.<timestamp>`), and 3-state verification tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`).
5. **Checkpoint L2 & L2.1 Milestone Reached**:
   - Canonical typed contracts created in `omni_engine/contracts/` using Pydantic v2 (`pydantic>=2.0.0,<3.0.0`).
   - True 23-tool source inventory verified (Web: 4, Browser: 2, OS: 8, Dev: 6, Data: 3) with zero unregistered functions.
   - 19-member `ErrorCode` taxonomy distinguishing `PERMISSION_DENIED` (external/OS denial) from `UNAUTHORIZED_ACTION` (internal policy refusal) and encapsulating `UNKNOWN_COMMIT` (mutation uncertainty).
   - System 1 Contracts: `DecisionSignal` with provider provenance fields (`provider_id`, `model_id`, calibration), bounded confidence in [0.0, 1.0], NaN/Inf rejection, and extended signals (`NEEDS_CLARIFICATION`, `REQUIRES_ACTION`, `NEEDS_GENERATIVE_REASONING`, `ESCALATION_REQUIRED`).
   - Capability Contracts: `CapabilitySpec` with explicit policy enums (`minimum_autonomy_profile`, `ConfirmationPolicy`, `RetryPolicy`, `IdempotencyClass`), `CapabilityInvocation` execution boundary, `ToolError`, `ExecutionReceipt`, `VerificationResult`, `ToolResult` (supporting `ToolOutcome: SUCCESS, PARTIAL, FAILURE`).
   - Agent Envelopes: `AgentRequest`, `AgentResponse`, `AgentEvent`, and extended `TraceContext` (with multi-tier causal correlation: `turn_id`, `quest_id`, `plan_id`, `step_id`, `operation_id`).
   - Wire/persisted contract schema versioning (`schema_version = "1.0.0"`).

---

## 2. Canonical 23-Tool Source Inventory Matrix

| Domain | Tool ID | Implementation Function | Blast Radius | Notes / Status |
| :--- | :--- | :--- | :--- | :--- |
| **web** | `web_search` | `tool_web_search` | `READ_ONLY` | Verified source tool (Tavily search) |
| **web** | `scrape_url` | `tool_scrape_url_content` | `EXTERNAL_READ` | Verified source tool (HTTP scrape) |
| **web** | `http_api` | `tool_http_api_request` | `EXTERNAL_CREATE` / `READ` | Verified source tool (README alias: `api_request`) |
| **web** | `download_file` | `tool_download_file` | `LOCAL_CREATE` | Verified source tool |
| **browser** | `visual_browse` | `tool_visual_browse` | `EXTERNAL_READ` / `SYSTEM` | Verified source tool (monolithic Edge runner) |
| **browser** | `browser_screenshot` | `tool_browser_screenshot` | `LOCAL_CREATE` | Verified source tool |
| **os** | `system_diagnostics` | `tool_system_diagnostics` | `READ_ONLY` | Verified source tool (README alias: `hardware_diagnostics`) |
| **os** | `list_processes` | `tool_list_processes` | `READ_ONLY` | Verified source tool |
| **os** | `kill_process` | `tool_kill_process` | `SYSTEM_ACTION` | Destructive: mandates confirmation gate in L9 |
| **os** | `launch_app` | `tool_launch_app` | `SYSTEM_ACTION` | Verified source tool |
| **os** | `desktop_screenshot` | `tool_desktop_screenshot` | `LOCAL_CREATE` | Verified source tool (README alias: `take_screenshot`) |
| **os** | `clipboard` | `tool_clipboard` | `LOCAL_UPDATE` / `READ` | Unified tool (README aliases: `read/write_clipboard`) |
| **os** | `powershell` | `tool_powershell` | `SYSTEM_ACTION` | Destructive: mandates confirmation gate in L9 |
| **os** | `ping_test` | `tool_ping_test` | `EXTERNAL_READ` | Verified source tool |
| **dev** | `file_read` | `tool_file_read` | `READ_ONLY` | Verified source tool (README alias: `read_file`) |
| **dev** | `file_write` | `tool_file_write` | `LOCAL_CREATE` / `UPDATE` | Destructive: mandates confirmation gate in L9 |
| **dev** | `search_code` | `tool_search_code` | `READ_ONLY` | Verified source tool (README alias: `search_codebase`) |
| **dev** | `directory_tree` | `tool_directory_tree` | `READ_ONLY` | Verified source tool |
| **dev** | `run_python` | `tool_run_python` | `SYSTEM_ACTION` | Sandboxed Python code runner |
| **dev** | `git_status` | `tool_git_status` | `READ_ONLY` | Verified source tool |
| **data** | `sqlite_exec` | `tool_sqlite_exec` | `LOCAL_UPDATE` / `READ` | Verified source tool (README alias: `sql_query`) |
| **data** | `inspect_data` | `tool_inspect_data` | `READ_ONLY` | Verified source tool (README alias: `inspect_dataset`) |
| **data** | `safe_math` | `tool_safe_math` | `READ_ONLY` | AST arithmetic evaluator with resource bounds |

---

## 3. Test Suite & Health Metrics Breakdown

> [!IMPORTANT]
> A 100% green test suite (55/55 passed) confirms baseline integrity, defect isolation, and contract soundness; it does **not** imply that the autonomous agent is functionally complete. Destructive policy gates (L9), multi-step DAG planning (L12), and autonomous execution (L14) remain sequentially scheduled.

- **Total Automated Tests**: 55 tests
  - **Feature Acceptance Tests**: 53 passed (contracts, ast math, atomic memory, baseline diagnostics).
  - **Known Defect Reproduction Tests**: 2 passed (asserting expected baseline defects: System 1 `[:12]` catalog truncation and raw prompt passed as argument).
- **Pass Rate**: 100% (55 passed, 0 failed, 0 errors).
- **Runtime**: 6.22s via `pytest`.

---

## 4. Current Blockers

- **None**. Checkpoint L2.1 is verified, reviewed, and passing 100% of automated tests.

---

## 5. Next Checkpoint Scope: L3A (Canonical Capability Registry)

1. Implement `CapabilityRegistry` registering the verified 23 canonical tools.
2. Validate canonical IDs, semvers, domains, and Pydantic argument schemas.
3. Strict Non-Switching Principle: Main agent dispatch remains on legacy path until L8 typed argument resolution and L9 policy engine exist.
