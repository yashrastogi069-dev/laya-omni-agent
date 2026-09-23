# LAYA_BUILD_STATE.md — Current Ground Truth State

**Last Updated**: 2026-09-23T09:20:00+05:30  
**Current Branch**: `laya-autonomous-v2`  
**Active Checkpoint**: `L3 — Canonical Capability Substrate` (**COMPLETED**; preparing L4)  
**Last Passing Test Suite**: `tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`, `tests/test_l2_1_reconciliation.py`, `tests/test_l3_capabilities.py` (**80/80 passed + 23 subtests passed via pytest in 32.99s**)  
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
6. **Checkpoint L3 Milestone Reached**:
   - Implemented thread-safe `CapabilityRegistry` in `omni_engine/capabilities/registry.py` with fine-grained lock scoping.
   - Created argument normalization adapters and prefix-anchored error interceptors in `omni_engine/capabilities/adapters.py` (eliminating false-positives on content-bearing tools).
   - Created 23 canonical `CapabilitySpec` instances in `omni_engine/capabilities/definitions.py` with 100% parity with source `OMNI_TOOL_REGISTRY`.
   - Guaranteed clean propagation of process-control exceptions (`KeyboardInterrupt`, `SystemExit`).
   - Strictly preserved legacy prototype paths and non-switching boundary (main dispatch unchanged until L8/L9).

---

## 2. Canonical 23-Tool Capability Matrix

| Domain | Capability ID | Implementation Function | Blast Radius | Policy Tier | Confirmation | Retry Policy | Idempotency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **web** | `web_search` | `tool_web_search` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **web** | `scrape_url` | `tool_scrape_url_content` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **web** | `http_api` | `tool_http_api_request` | `EXTERNAL_CREATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **web** | `download_file` | `tool_download_file` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **browser** | `visual_browse` | `tool_visual_browse` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **browser** | `browser_screenshot` | `tool_browser_screenshot` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `NEVER` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **os** | `system_diagnostics` | `tool_system_diagnostics` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `list_processes` | `tool_list_processes` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `kill_process` | `tool_kill_process` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `launch_app` | `tool_launch_app` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `desktop_screenshot` | `tool_desktop_screenshot` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `NEVER` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **os** | `clipboard` | `tool_clipboard` | `LOCAL_UPDATE` | `SAFE_ASSISTANT` | `POLICY_CONTROLLED` | `NEVER` | `NATURAL` |
| **os** | `powershell` | `tool_powershell` | `SYSTEM_ACTION` | `TRUSTED_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `ping_test` | `tool_ping_test` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `file_read` | `tool_file_read` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `file_write` | `tool_file_write` | `LOCAL_CREATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **dev** | `search_code` | `tool_search_code` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `directory_tree` | `tool_directory_tree` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `run_python` | `tool_run_python` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **dev** | `git_status` | `tool_git_status` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **data** | `sqlite_exec` | `tool_sqlite_exec` | `LOCAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **data** | `inspect_data` | `tool_inspect_data` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **data** | `safe_math` | `tool_safe_math` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |

---

## 3. Test Suite & Health Metrics Breakdown

- **Total Automated Tests**: 80 tests (+ 23 subtests)
  - **Feature Acceptance Tests**: 78 passed (contracts, ast math, atomic memory, baseline diagnostics, registry lifecycle, all 23 invocation adapters).
  - **Known Defect Reproduction Tests**: 2 passed (asserting expected baseline defects: System 1 `[:12]` catalog truncation and raw prompt passed as argument).
- **Pass Rate**: 100% (80 passed, 0 failed, 0 errors, 23 subtests passed).
- **Runtime**: ~32.99s via `pytest`.

---

## 4. Current Blockers

- **None**. Checkpoint L3 is verified, reviewed, and passing 100% of automated tests.

---

## 5. Next Checkpoint Scope: L4 (Provider Foundations)

1. Implement `SystemOneProvider` interface with `LayaProvider` (local ModernBERT-large) and graceful optional `JevProvider`.
2. Implement `GenerativeProvider` interface with `OpenRouterProvider` (LLaMA 3.3 70B).
3. Record model provenance, latency telemetry, and health check APIs.
4. Strictly enforce zero secrets committed.
