# HANDOFF.md — Operational Continuation Guide (Checkpoint L8 Complete, Proceeding to L9)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: High-frequency structured decisions via local ModernBERT-large (`laya.Router()`) with calibrated probability bounds and two-stage adaptive triage.
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Hierarchical Capability Routing**: Dynamic multi-tier tool catalog reduction (`Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`) eliminating flat catalog slicing and token bloat.
- **Skills Layer**: Reusable workflow manifests mapping objectives to constrained capability sets with safety policy floors.
- **Typed Argument Resolution**: Deterministic parameter extraction in 0.118 ms with schema validation, alias bridging, and zero-hallucination clarification gating.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `RouteDecision`, `SkillManifest`, `DecisionFrame`, `CalibrationConfig`, `ArgumentResolutionEnvelope`, `AgentRequest`, `AgentResponse`, `TraceContext`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L8 COMPLETED & VERIFIED**; **PROCEEDING TO L9 (Deterministic Policy Engine & Persistent User Constraints)**.
- Test Suite: **207/207 tests passing** (+ 47 subtests passed) across:
  - `tests/test_l0_baselines.py` (10 tests)
  - `tests/test_l1_repairs.py` (12 tests)
  - `tests/test_l2_contracts.py` (18 tests)
  - `tests/test_l2_1_reconciliation.py` (15 tests)
  - `tests/test_l3_capabilities.py` (25 tests, 23 subtests)
  - `tests/test_l4_providers.py` (19 tests)
  - `tests/test_l5_decision_fabric.py` (12 tests)
  - `tests/test_l6a_routing.py` (12 tests)
  - `tests/test_l7_skills.py` (26 tests)
  - `tests/test_l6b_skill_routing.py` (16 tests)
  - `tests/test_l7_5_calibration.py` (16 tests)
  - `tests/test_l8_arguments.py` (26 tests)
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L8 Executed)
1. **Typed Argument Contracts (`omni_engine/contracts/arguments.py`)**:
   - `ArgumentExtractionSource` (Enum: `DETERMINISTIC_REGEX`, `SYNTACTIC_AST`, `GENERATIVE_SYNTHESIS`, `SCHEMA_DEFAULT`, `CONTEXT_INHERITED`).
   - `ArgumentSlot`: Property name, typed value, resolution status, source, confidence, and error.
   - `ArgumentResolutionEnvelope`: Complete resolution payload with arguments dict, resolved slots, validity, missing slots, clarification prompt, latency telemetry, and metadata.
2. **High-Precision Deterministic Extractors (`omni_engine/arguments/extractors.py`)**:
   - `extract_file_path`: Quoted paths, Windows drive paths, relative paths, local filenames, and keyword targets with non-path filters (`tree`, `structure`, `info`).
   - `extract_url`: HTTP/HTTPS URLs and localhost endpoints (`http://localhost:5678`).
   - `extract_pid`: Numeric process IDs (`pid: 1234`, `kill process 4567`).
   - `extract_process_name`: Executable names (`.exe`) and known processes (`node`, `python`, `n8n`, `calc`).
   - `extract_app_name`: Desktop applications and services (`launch calc`, `start n8n`).
   - `extract_sql_query`: Quoted and unquoted SQL statements (`SELECT`, `INSERT`, `UPDATE`).
   - `extract_math_expression`: Arithmetic and mathematical expressions (`calculate 1024 * 768`).
   - `extract_powershell_script`: PowerShell commands and one-liners (`powershell 'Get-Date'`).
   - `extract_python_code`: Markdown fenced blocks (````python ... ````) and inline code.
   - `extract_search_query`: Quoted and natural search queries.
   - `extract_ping_host`: IPv4 addresses and domain hosts.
   - `extract_clipboard_data`: Read vs write actions with text payloads.
3. **Master Argument Resolver & Validator (`omni_engine/arguments/resolver.py`)**:
   - `ArgumentResolver.resolve()`: Resolves and validates arguments against `CapabilitySpec.input_schema`.
   - Sub-1ms deterministic SLA: Benchmarked at **0.118 ms** per resolution.
   - Schema defaults ingestion for optional parameters (`max_results = 6`, `path = "."`, `max_depth = 3`).
   - Context parameter inheritance with `PARAM_ALIASES` handling client synonyms (`filepath` vs `file_path`, `target` vs `pid`).
   - Evidence-based clarification gating: Missing required slots trigger structured user prompts (`CLARIFICATION_PROMPTS`), with zero hallucinated dummy values.
   - Generative fallback synthesis via `GenerativeProvider.generate_text()` with markdown fence stripping when enabled.
4. **Comprehensive Test Suite & Diff Review**:
   - 26 new tests in `tests/test_l8_arguments.py`.
   - Full suite: **207/207 passing (100%)** in 229s.
   - Independent adversarial diff review: **PASS ✅** (Subagent `00527d05-183d-4711-be67-eeb080163dcc`).

---

## Next Steps for Checkpoint L9 (Deterministic Policy Engine & Persistent User Constraints)
1. **Contracts (`omni_engine/contracts/policy.py`)**:
   - Implement `PolicyEffect`, `ActionAssessment`, `PolicyRule`, and `PolicyDecision`.
2. **Persistent User Constraints & Rule Store (`omni_engine/policy/rules.py` & `store.py`)**:
   - System rules: Forbidden operations (`git reset --hard`, `git clean -fd`, `rmdir /s /q C:\`), protected system paths (`C:\Windows`, `System32`, `Program Files`, `.ssh`, `.env`), and critical system processes.
   - Custom user constraints persistence (JSON-backed rule store).
3. **Deterministic Policy Engine (`omni_engine/policy/engine.py`)**:
   - `PolicyEngine.evaluate()` evaluating action classes, blast radius, autonomy ceilings, and confirmation enforcement in <1ms.
   - Support shadow runner telemetry (`LAYA_V2_MODE=off|shadow|active`).
4. **Test Suite (`tests/test_l9_policy.py`)**:
   - 25+ unit tests covering all action classes, autonomy tiers, confirmation policies, protected paths, forbidden operations, and custom constraints.
5. **Adversarial Diff Review for L9**.
6. **Final Goal Report & Hard Stop** (STOP AFTER L9).
