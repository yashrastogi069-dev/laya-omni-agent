# LAYA_BUILD_STATE.md — Current Ground Truth State

**Last Updated**: 2026-09-24T17:28:00+05:30  
**Current Branch**: `laya-autonomous-v2`  
**Active Milestone Goal**: `L7.5 → L8 → L9` (**100% COMPLETE & VERIFIED — HARD STOPPED BEFORE L10**)  
**Last Passing Test Suite**: `tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`, `tests/test_l2_1_reconciliation.py`, `tests/test_l3_capabilities.py`, `tests/test_l4_providers.py`, `tests/test_l5_decision_fabric.py`, `tests/test_l6a_routing.py`, `tests/test_l7_skills.py`, `tests/test_l6b_skill_routing.py`, `tests/test_l7_5_calibration.py`, `tests/test_l8_arguments.py`, `tests/test_l9_policy.py` (**232/232 passed in 320s, 47 subtests passed = 279 total (100% pass rate)**)  
**Mission Role**: Complete Standalone Autonomous Operating Agent.

---

## 1. Current Architecture Summary

The repository contains a standalone prototype CLI (`laya_agent.py` / `omni_engine/`) transitioning towards a **complete standalone autonomous operating agent**:
1. **System 1**: Local ModernBERT-large (`laya.Router()`) providing high-frequency decisions.
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
7. **Checkpoint L4 Milestone Reached**:
   - Implemented `SystemOneProvider(ABC)` with `LayaProvider` (local ModernBERT-large with singleton lock RAM protection, batched multi-question evaluation, bounded numerical sanitization, and defensive extraction) and `JevProvider` (graceful non-crashing degradation when unconfigured).
   - Implemented `GenerativeProvider(ABC)` with `OpenRouterProvider` (markdown code fence extraction, structured JSON parsing into Pydantic models, configurable timeout budget, non-empty choice validation, and zero local RAM footprint).
   - Fixed Windows console encoding flaw (`UnicodeEncodeError` on `\u26a0\ufe0f`) in `omni_engine/memory.py`.
   - Comprehensive unit test suite `tests/test_l4_providers.py` (19 tests).
8. **Checkpoint L5 Milestone Reached**:
   - Implemented `DecisionFabric` in `omni_engine/decision/fabric.py` evaluating 15 canonical decision signals in a single batched neural pass.
   - Deterministic fast-path (<1ms) for empty/whitespace prompts.
   - Deterministic safety floor overrides for high-risk commands and Invariant 7 reversibility clamping.
   - Ambiguity detection and clarifying question triggers.
   - Candidate domain ranking without violating `extra="forbid"`.
   - Standardized 10-prompt benchmark evaluation corpus and runner in `omni_engine/decision/corpus.py`.
   - Comprehensive unit test suite `tests/test_l5_decision_fabric.py` (12 tests).
9. **Checkpoint L6A Milestone Reached**:
   - Implemented `HierarchicalRouter` in `omni_engine/routing/router.py` with multi-tier catalog reduction.
   - Conversational fast-path (<5ms), cross-domain pooling for multi-step tasks, ambiguity fail-open, explicit keyword capability pinning (`CAPABILITY_PIN_MAP`), and "general" domain technical promotion.
   - Eliminated sequential latency cliff via zero-inference short-circuit (<0.2ms) and fast deterministic lexical scoring (<1ms).
   - Eliminated legacy `[:12]` tool truncation defect (ISSUE-02).
   - Comprehensive unit test suite `tests/test_l6a_routing.py` (12 tests).
10. **Checkpoint L7 Milestone Reached**:
    - Implemented `SkillManifest` and `SkillStepTemplate` typed contracts in `omni_engine/contracts/skill.py`.
    - Implemented multi-layer safety floors: phantom dependency rejection, 3-color DFS cycle detector, action class encompassment (blocking omission spoofing), and constituent tool high-risk confirmation policy floors.
    - Implemented thread-safe `SkillRegistry` in `omni_engine/skills/registry.py` verifying zero dangling capabilities against `CapabilityRegistry`.
    - Defined 7 canonical skills backed 100% by the 23 verified tools in `omni_engine/skills/definitions.py`.
    - Comprehensive unit test suite `tests/test_l7_skills.py` (26 tests).
11. **Checkpoint L6B Milestone Reached**:
    - Extended `RouteDecision` in `omni_engine/contracts/routing.py` with strongly typed skill telemetry (`selected_skill`, `candidate_skills`, `skill_workflow_template: List[SkillStepTemplate]`, `skill_confirmation_policy: ConfirmationPolicy`).
    - Implemented skill-aware multi-tier routing pipeline in `omni_engine/routing/router.py`:
      `Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`
    - Implemented Dynamic Candidate Floor Expansion (`effective_max = max(max_candidates, len(mandatory_caps))`) ensuring required and pinned capabilities are never dropped.
    - Implemented Unconditional Cross-Domain Spec Backfill for constituent tools of selected skills.
    - Implemented Dual-Threshold Gating & Anti-Locking Defenses (destructive verb gate, single generic token gate, description score ceiling at 0.50, morphological stemming).
    - Preserved zero-latency fast-paths (<5ms) and legacy non-switching boundary.
    - Comprehensive unit test suite `tests/test_l6b_skill_routing.py` (16 tests).
12. **Checkpoint L7.5 Milestone Reached**:
    - **Source-Truth Gate A (SkillManifest Invariants)**: Updated autonomy profile floor in `SkillRegistry` to inspect all constituent capabilities (`required_capabilities | optional_capabilities | step_capabilities`), guaranteeing no skill can bypass autonomy constraints via optional tools.
    - **Source-Truth Gate B (Hardware & Latency Truth)**: Empirically measured on host CPU: ModernBERT-large consumes 1.64 GB RAM, cold load = 69.3s, warm latency = 749ms (1 question) to 15.4s (15 questions). Proven that <35ms is CUDA-only, justifying two-stage Adaptive Triage.
    - **Calibration Contracts**: Created `omni_engine/contracts/calibration.py` with `CalibratedModelThresholds`, `DeterministicPolicyThresholds`, and `CalibrationConfig`, eliminating scattered inline magic numbers.
    - **Upstream Alignment & RAM Safety**: Hardened `omni_engine/providers/system1.py` with pre-eviction unload/gc, process-wide thread lock (`_ROUTER_LOCK`), single-model preload guard (`names=[model_name]`), configurable model selection (`english`, `multilingual`, `typed-decisions`), and backward-compatible ModernBERT-large naming.
    - **Decision Evaluation Corpus**: Created `omni_engine/decision/eval_corpus.py` with 103 reviewable ground-truth labeled cases covering 6 domains, prompt injection, and automation workflows.
    - **Hardware-Aware Benchmark**: Created `omni_engine/decision/benchmark.py` measuring cold load, warm latency, batch scaling, and graceful unconfigured Jev handling.
    - **Adaptive Decision Fabric**: Implemented `DecisionFabric.evaluate_adaptive()` with fast 4-question triage early exit for conversational queries, achieving a ~4.2x speedup on CPU.
    - **Shadow Semantic Skill Routing**: Integrated shadow semantic evaluation and agreement tracking into `HierarchicalRouter`.
    - **Comprehensive Test Suite**: Created `tests/test_l7_5_calibration.py` (16 unit tests, 100% pass rate).
13. **Checkpoint L8 Milestone Reached**:
    - **Typed Argument Contracts**: Created `omni_engine/contracts/arguments.py` with `ArgumentExtractionSource` (Enum), `ArgumentSlot`, and `ArgumentResolutionEnvelope`.
    - **High-Precision Deterministic Extractors**: Implemented `omni_engine/arguments/extractors.py` handling file paths (Windows drive, POSIX, quoted, relative), URLs (HTTP/HTTPS, localhost ports like `:5678`), PIDs, process names, desktop apps/services (`n8n`, `calc`, `notepad`), SQL statements, arithmetic expressions, PowerShell commands, and search queries.
    - **Argument Resolver & Schema Validator**: Implemented `ArgumentResolver` in `omni_engine/arguments/resolver.py` validating against `CapabilitySpec.input_schema`. Executes deterministic resolution in **0.118 ms**, enforces zero-hallucination clarification gating via `CLARIFICATION_PROMPTS`, and bridges schema aliases via `PARAM_ALIASES`.
    - **Generative Fallback Synthesis**: Bounded synthesis via `GenerativeProvider.generate_text()` with markdown fence stripping when deterministic extraction leaves required slots unfulfilled.
    - **Comprehensive Test Suite**: Created `tests/test_l8_arguments.py` (26 unit tests, 100% pass rate in 0.010s).
14. **Checkpoint L9 Milestone Reached**:
    - **Typed Policy Contracts**: Created `omni_engine/contracts/policy.py` with `PolicyEffect` (ALLOW, REQUIRE_CONFIRMATION, DENY, QUARANTINE), `ActionAssessment`, `PolicyRule`, and `PolicyDecision` (with Pydantic `@model_validator` enforcing logical consistency).
    - **Hard System Invariants (Rule-0)**: Implemented in `omni_engine/policy/rules.py`: `canonicalize_path` (early prefix stripping, UNC admin$/drive$ share resolution, static network UNC normalization to prevent SMB network hangs), protected path boundary gating (`C:\Windows`, `System32`, `Program Files`, `.ssh`, `.env`, root drives), critical process protection (PIDs 0/4, `csrss`, `lsass`, `smss`, `services`), and embedded command regex scanner (`scan_embedded_commands`) for forbidden operations (`git reset <ref> --hard`, all `git clean` flag permutations, `git push -f`, PowerShell root wipes `Remove-Item -Recurse -Force C:\`).
    - **Crash-Resilient Policy Store**: Implemented `PolicyStore` in `omni_engine/policy/store.py` with thread-safe `RLock`, atomic disk swaps (`.tmp` to target via `os.replace`), and automatic `.corrupt` quarantining.
    - **Deterministic Policy Engine**: Implemented `PolicyEngine` in `omni_engine/policy/engine.py` executing sub-millisecond evaluation (~0.15ms warm, sub-1ms SLA) across Stage 0 (Inviolable Hard Invariants: `user_confirmed` strictly ignored), Stage 1 (Boundary-aware persistent user blacklists: zero substring false-positives), Stage 2 (Autonomy gating: ADVISOR read-only floor, elevation gating), Stage 3 (Confirmation policy gating: ALWAYS, POLICY_CONTROLLED high-risk), and Stage 4 (Permitted baseline / Shadow mode).
    - **Shadow Mode Simulation**: Non-disruptive production simulation recording `shadow_mode=True`, `shadow_original_effect`, and diagnostics in decision metadata while strictly preserving Tier-0 hard invariant denials.
    - **Adversarial Diff Review**: **PASS ✅** (Independent subagents `b8ecedc3-4acd-4392-9f25-16ca29461ee1` [vulnerability identification] & `0f038fb7-f33b-47c1-864c-1fcd56e1a540` [verification of remediation]).
    - **Comprehensive Test Suite**: Created `tests/test_l9_policy.py` (25 unit tests, 100% pass rate in 0.269s).

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

- **Total Automated Tests**: 207 tests (+ 47 subtests)
  - **L0 Baseline Tests**: 10 passed
  - **L1 & L1.1 Memory and Math Tests**: 12 passed
  - **L2 Contracts Tests**: 18 passed
  - **L2.1 Reconciliation Tests**: 15 passed
  - **L3 Capability Substrate Tests**: 25 passed (+ 23 subtests passed)
  - **L4 Provider Foundations Tests**: 19 passed
  - **L5 Decision Fabric Tests**: 12 passed
  - **L6A Hierarchical Routing Tests**: 12 passed
  - **L7 Skills Substrate Tests**: 26 passed
  - **L6B Skill-Aware Routing Tests**: 16 passed
  - **L7.5 Truth, Calibration & Upstream Alignment Tests**: 16 passed
  - **L8 Typed Argument Resolution Tests**: 26 passed
- **Pass Rate**: 100% (207 passed, 0 failed, 0 errors, 47 subtests passed).
- **Runtime**: ~229s across full test suite.

---

## 4. Current Blockers

- **None**. Checkpoint L8 is verified, reviewed, and passing 100% of automated tests.

---

## 5. Next Checkpoint Scope: L9 (Deterministic Policy Engine & Persistent User Constraints)

Within active goal `L7.5 → L8 → L9`:
- Active Phase: **L9 — Deterministic Policy Engine & Persistent User Constraints**
- Core Objectives for L9:
  1. Build policy contracts (`PolicyEffect`, `ActionAssessment`, `PolicyRule`, `PolicyDecision`).
  2. Implement canonical system rules (forbidden operations, protected path boundaries, process protections).
  3. Implement persistent user constraints store (JSON-backed custom policy overrides).
  4. Implement `PolicyEngine` evaluating action classes, blast radius, autonomy ceilings, and confirmation enforcement in <1ms.
  5. Support shadow runner telemetry (`LAYA_V2_MODE=off|shadow|active`).
  6. Final Goal Boundary: **HARD STOP AFTER L9**.
