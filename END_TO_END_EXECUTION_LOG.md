# END_TO_END_EXECUTION_LOG.md — Complete Chronological System Engineering Log

> **DOCUMENT PURPOSE**: This file is the single, persistent, cumulative record of all actions, tests, code changes, deletions, additions, refactors, adversarial reviews, and benchmark results performed on the **LAYA Omni Agent** repository from inception to present. It is updated at every engineering checkpoint so that all past and ongoing work is tracked without loss of context.

---

## Quick Reference & Repository Health Dashboard

| Metric | Status / Value |
| :--- | :--- |
| **System Role** | Standalone Autonomous Operating Agent (Independent from Jarvis Core V2) |
| **Active Architecture Branch** | `laya-autonomous-v2` |
| **Public GitHub Remote** | `https://github.com/yashrastogi069-dev/laya-omni-agent.git` |
| **Latest Branch Commit** | `0a6a392` (L10 Verified) |
| **Total Automated Tests** | **385 / 385 Passing (100%)** (+ 47 subtests = 432 total checks) in ~572 seconds |
| **Test Categorization** | **383 Feature Acceptance Tests** + **2 Known Defect Reproduction Tests** |
| **Known Warnings Classification** | **2 Warnings Emitted**: `RuntimeWarning` from `laya/router.py:187` (Upstream library temperature outside [0.5, 5] clamping — BENIGN/UPSTREAM); 0 unhandled warnings in test suite |
| **Calibration Status** | **Intent Signal**: Calibrated (ECE 0.1192, 72/31 stratified corpus split); **Domain Signal**: Uncalibrated (Deterministic fail-open fallback, cross-domain pooling, and escalation) |
| **Hardware Operating Baseline** | Windows 10 Host, 4 CPU Cores, 7.81 GB RAM, PyTorch 2.13.0+cpu, NO CUDA GPU (CPU DecisionFrame latency ~15.4s; SystemOneBroker enforces user sovereignty, RAM threshold debouncing, and quality floor) |
| **Checkpoints Completed** | **L0–L10, Foundation Gate, R1, R2, R3, R4, R5, RV0** |
| **Active Milestone & Checkpoint** | **L11 — Operation Ledger & Exactly-Once Mutation Semantics** (Milestone: L10 Quest → L11 Operation Ledger → L12 Planner → L13 Validator → L14 Executor) |

---

## Chronological Execution Ledger (Top to Bottom)

```
[INIT: REPOSITORY TAKEOVER]
       │
       ▼
[L0: AUDIT, BASELINE INVENTORY & DEFECT REPRODUCTIONS]
       │ ── 10/10 Baseline Tests Passing (Commit: 26be41e on main)
       ▼
[L1: CRITICAL LOCAL RELIABILITY REPAIRS]
       │ ── 22/22 Tests Passing (Commit: e78cf8b on main)
       ▼
[L1.1: MEMORY 3-STATE & RESOURCE BOUNDS HARDENING]
       │ ── 22/22 Tests Passing (Commit: 6a66787 on main)
       ▼
[BRANCHING: laya-autonomous-v2 CREATED & PUSHED]
       │
       ▼
[L2: FOUNDATIONAL TYPED CONTRACTS (PYDANTIC V2)]
       │ ── 40/40 Tests Passing (Commit: ded73d3 on laya-autonomous-v2)
       ▼
[L2.1: CONTRACT & REGISTRY RECONCILIATION]
       │ ── 55/55 Tests Passing (Commit: ed9e1e5 on laya-autonomous-v2)
       ▼
[L3: CANONICAL CAPABILITY SUBSTRATE]
       │ ── 80/80 Tests Passing + 23 Subtests (Commit on laya-autonomous-v2)
       ▼
[L4: PROVIDER FOUNDATIONS (SYSTEM 1 & GENERATIVE)]
       │ ── 99/99 Tests Passing (Commit: 87b22a6 on laya-autonomous-v2)
       ▼
[L5: DECISION FABRIC FOUNDATION]
       │ ── 111/111 Tests Passing (Commit: ad73f3c on laya-autonomous-v2)
       ▼
[L6A: HIERARCHICAL ROUTING FOUNDATION]
       │ ── 123/123 Tests Passing (Commit: 7ab5b68 on laya-autonomous-v2)
       ▼
[L7: SKILLS SUBSTRATE & WORKFLOW MANIFESTS]
       │ ── 149/149 Tests Passing (Commit: a7bf9ca on laya-autonomous-v2)
       ▼
[L6B: SKILL-AWARE HIERARCHICAL ROUTER]
       │ ── 165/165 Tests Passing (Commit: b8a6234 on laya-autonomous-v2)
       ▼
[L7.5: TRUTH, CALIBRATION & UPSTREAM ALIGNMENT]
       │ ── 181/181 Tests Passing (Commit: 2a2b1fa on laya-autonomous-v2)
       ▼
[L8: TYPED ARGUMENT RESOLUTION & EXTRACTION ENGINE]
       │ ── 207/207 Tests Passing (Commit: fd50bf8 on laya-autonomous-v2)
       ▼
[L9: DETERMINISTIC POLICY ENGINE & USER CONSTRAINTS]
       │ ── 232/232 Tests Passing (Commit: 3b4009d on laya-autonomous-v2)
       ▼
[FOUNDATION GATE: SYSTEM 1 BROKER & CALIBRATION TRUTH]
       │ ── 259/259 Tests Passing (Commit: 9cf8aaf on laya-autonomous-v2)
       ▼
[R1: DEEP EVIDENCE-GROUNDED RESEARCH ENGINE]
       │ ── 277/277 Tests Passing (Commit: 61c8a9c on laya-autonomous-v2)
       ▼
[R2: REAL PERSISTENT BROWSER ENGINE]
       │ ── 293/293 Tests Passing (Commit: 27caf68 on laya-autonomous-v2)
       ▼
[R3: WINDOWS DESKTOP, APP & LOCAL SERVICE ENGINE]
       │ ── 314/314 Tests Passing (Commit: 5e89c51 on laya-autonomous-v2)
       ▼
[R4: PROGRAMMATIC N8N AUTOMATION ENGINE]
       │ ── 339/339 Tests Passing (Commit: c472c0c on laya-autonomous-v2)
       ▼
[R5: SUPERVISED DEVELOPER AGENT & ANTIGRAVITY ENGINE]
       │ ── 364/364 Tests Passing (Commit: 48f10b5 on laya-autonomous-v2)
       ▼
[RV0: LIVE REALITY GATE & DOCUMENTATION AUDIT]
       │ ── 372/372 Tests Passing (+47 subtests = 419 checks)
       ▼
[L10: PERSISTED SQLITE QUEST RUNTIME]
       │ ── 385/385 Tests Passing (+47 subtests = 432 checks)
       ▼
[L11: OPERATION LEDGER & EXACTLY-ONCE MUTATION SEMANTICS] ◀── ACTIVE
       │
       ▼
[L12 → L14: PLANNER, VALIDATOR, EXECUTOR]
```

---

## 1. Initial Reconnaissance & Ground Truth Baseline (L0)

### 1.1 Objectives
- Establish verifiable repository truth across the existing codebase.
- Inventory all capabilities, entry points, dependencies, and execution flows.
- Reproduce confirmed runtime defects with automated regression tests before altering code.
- Initialize canonical governance documentation.

### 1.2 Codebase Inventory & Discoveries
- Audited all 22 Python source files across `omni_engine/` and root tools.
- Evaluated the source registry in `omni_engine/tools/__init__.py`, which contains exactly **23 individual tools** across 5 functional categories:
  1. **Web Tools** (4): `web_search`, `scrape_url`, `http_api`, `download_file`.
  2. **Browser Tools** (2): `visual_browse`, `browser_screenshot`.
  3. **OS Tools** (8): `system_diagnostics`, `list_processes`, `kill_process`, `launch_app`, `desktop_screenshot`, `clipboard`, `powershell`, `ping_test`.
  4. **Dev Tools** (6): `file_read`, `file_write`, `search_code`, `directory_tree`, `run_python`, `git_status`.
  5. **Data Tools** (3): `sqlite_exec`, `inspect_data`, `safe_math`.
- *(Note on historical documentation discrepancy: Initial exploratory notes and README referenced aspirational/alias names such as `hardware_diagnostics`, `api_request`, `read_clipboard`, `write_clipboard`, `sql_query`, and `safe_eval_math`. As confirmed in L2.1, the source code in `omni_engine/tools/__init__.py` is authoritative).*
- Discovered 6 critical flaws in prototype code:
  - **Defect 1**: `tool_safe_math` crashed with `NameError: name 're' is not defined`.
  - **Defect 2**: `System1Router.route_tool` truncated catalog with `[:12]`, hiding tools 12–22 from System 1.
  - **Defect 3**: Raw user natural language prompts were passed directly into tools expecting file paths.
  - **Defect 4**: `OmniMemory` schema key mismatch (`tool_effectiveness` vs `tool_success_counts`).
  - **Defect 5**: Direct non-atomic file writes risked zero-byte corruption on crash.
  - **Defect 6**: Missing confirmation gates for destructive actions (`kill_process`, `file_write`, `powershell`).

### 1.3 Files Created & Initialized
- `tests/test_l0_baselines.py` (10 unit tests covering inventory, defect reproduction, and baseline tools).
- Canonical documentation suite initialized (`AGENTS.md`, `LAYA_BUILD_STATE.md`, `HANDOFF.md`, `tasks/`, `docs/`, `LAYA_CORE_IMPLEMENTATION_REPORT.md`).

### 1.4 Test Results
- Ran: `python -m pytest tests/test_l0_baselines.py`
- Result: **10 passed, 0 failed in 0.44s**. Commit `26be41e` on `main`.

---

## 2. Checkpoint L1: Critical Local Reliability Repairs

### 2.1 Objectives & Changes
- `omni_engine/tools/data_tools.py`: Replaced unsafe `eval()` with strict AST-based `_evaluate_ast_node()` evaluating whitelisted operators, math functions, and constants with exponent limits.
- `omni_engine/memory.py`: Added dynamic key migration (`tool_effectiveness` $\to$ `tool_success_counts`), atomic temporary-file writes (`.tmp` $\to$ `os.replace`), and corrupt file recovery.
- `omni_engine/system1.py`: Preserved `[:12]` catalog slicing as a documented legacy limitation; rejected naive flat dump in favor of upcoming Checkpoint L6 (Hierarchical Routing).
- `tests/test_l1_repairs.py`: Implemented 12 unit tests.

### 2.2 Test Results
- Ran: `python -m pytest tests/ -v`
- Result: **22 passed in 5.06s**. Commit `e78cf8b` on `main`.

---

## 3. Checkpoint L1.1: Hardening Pass & Scope Correction

### 3.1 Objectives & Changes
- `omni_engine/memory.py`: Implemented 3-state outcome tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`). Execution never automatically implies success (default is `UNVERIFIED`). Added automated quarantine of corrupted JSON files to `<filepath>.corrupt.<timestamp>`. Pinned `schema_version = "2.5.0"`.
- `omni_engine/tools/data_tools.py`: Added deterministic resource bounds to `tool_safe_math` (expression length $\le 256$, AST nodes $\le 40$, literal magnitude $\le 10^{100}$, factorial integer $0 \le n \le 100$, exponent $|\text{exp}| \le 100$).
- `tasks/MASTER_PLAN.md`: Expanded L4 to Dual Provider Foundation (System One & Generative abstractions decoupled from vendors).
- Created architecture branch `laya-autonomous-v2` and pushed to origin.

### 3.2 Test Results
- Ran: `python -m pytest tests/ -v`
- Result: **22 passed in 9.24s**. Commit `6a66787` on `main`.

---

## 4. Checkpoint L2: Foundational Typed Contracts

### 4.1 Objectives & Changes
- Created package `omni_engine/contracts/` using Pydantic v2:
  - `base.py`: `BaseContractModel` enforcing `extra="forbid"` and `validate_assignment=True`.
  - `enums.py`: 11 `ActionClass`, 5 `AutonomyProfile`, standardized `ErrorCode`, 3 `VerificationStatus`, 12 `DecisionSignalType` (including Invariant 7 `REVERSIBILITY`).
  - `decision.py`: `DecisionSignal` (strictly bounded confidence in $[0.0, 1.0]$, `NaN`/`Inf` rejected) and `DecisionFrame`.
  - `capability.py`: `CapabilitySpec` (pure JSON-serializable separated from callables), `ExecutableCapability`, `ToolError`, `ExecutionReceipt`, `VerificationResult`, `ToolResult` (enforcing mutual exclusivity).
  - `agent.py`: `TraceContext`, `AgentRequest`, `AgentResponse`, `AgentEvent`.
- `tests/test_l2_contracts.py`: Added 18 unit tests.
- Subagent Reviews: Pre-implementation plan review and post-implementation diff review both confirmed **PASS**.

### 4.2 Test Results
- Ran: `python -m pytest tests/ -v`
- Result: **40 passed in 6.13s**. Commit `ded73d3` on `laya-autonomous-v2`.

---

## 5. Checkpoint L2.1: Contract & Registry Reconciliation

### 5.1 Objectives & Changes
1. **Source Registry Reconciliation**:
   - Programmatically validated `omni_engine/tools/` contains exactly 23 registered tools and zero unexported functions.
   - Reconciled documentation against actual source registry (Web: 4, Browser: 2, OS: 8, Dev: 6, Data: 3).
   - Added automated regression test `TestL21CanonicalRegistryInventory` asserting the exact 23 IDs.
2. **Complete 19-Member ErrorCode Taxonomy**:
   - Extended `ErrorCode`: `UNKNOWN`, `INVALID_ARGUMENT`, `SCHEMA_VIOLATION`, `UNCONFIGURED`, `AUTH_REQUIRED`, `PERMISSION_DENIED`, `UNAUTHORIZED_ACTION`, `CONFIRMATION_REJECTED`, `NOT_FOUND`, `ALREADY_EXISTS`, `CONFLICT`, `RATE_LIMITED`, `TIMEOUT`, `NETWORK_ERROR`, `SERVICE_UNAVAILABLE`, `PROCESS_FAILED`, `CANCELLED`, `UNKNOWN_COMMIT`, `INTERNAL_ERROR`.
   - Distinct semantics: `PERMISSION_DENIED` = external/OS refusal; `UNAUTHORIZED_ACTION` = internal policy refusal; `UNKNOWN_COMMIT` = mutation uncertainty (never blind retry).
3. **Extended Decision Signals & Provenance**:
   - Added signal-level provenance fields: `provider_id`, `model_id`, `decision_schema_version`, `calibration_version`, `latency_ms`.
   - Added extended signals: `NEEDS_CLARIFICATION`, `REQUIRES_ACTION`, `NEEDS_GENERATIVE_REASONING`, `ESCALATION_REQUIRED`.
   - Updated `DecisionFrame` with typed fields and `schema_version = "1.0.0"`.
4. **Explicit CapabilitySpec Policy Semantics**:
   - Explicit policy enums: `minimum_autonomy_profile: AutonomyProfile`, `confirmation_policy: ConfirmationPolicy`, `retry_policy: RetryPolicy`, `idempotency_class: IdempotencyClass`.
   - Added backward-compatible properties and pre-validator to handle legacy keyword arguments without throwing `extra_forbidden`.
5. **Partial Tool Outcome Semantics**:
   - Adopted `ToolOutcome: SUCCESS, PARTIAL, FAILURE` in `ToolResult`, separate from physical `VerificationStatus`.
   - Enforced mutual exclusivity: `PARTIAL` enforces `success=False` while permitting partial data and error context.
6. **Invocation Context & Extended TraceContext**:
   - Implemented `CapabilityInvocation` execution boundary context.
   - Isolated `TraceContext` in `omni_engine/contracts/trace.py` to eliminate circular imports; added `turn_id`, `quest_id`, `plan_id`, `step_id`, `operation_id`.
7. **Wire/Persisted Contract Schema Versioning**:
   - Explicit `schema_version = "1.0.0"` on all wire contracts.
   - Documented continuous memory `schema_version = "2.5.0"` as storage format decoupled from app version.
8. **Dependency Pinning**:
   - Pinned `pydantic>=2.0.0,<3.0.0` in `requirements.txt`.
9. **Tests & Adversarial Review**:
   - Created `tests/test_l2_1_reconciliation.py` (15 tests).
   - Adversarial Contract Review confirmed **PASS**.

### 5.2 Test Results
- Ran: `python -m pytest tests/ -v`
- Result: **55 passed in 6.22s (100% pass rate)**.
  - **Feature Acceptance Tests**: 53 passed
  - **Known Defect Reproduction Tests**: 2 passed

---

## 6. Checkpoint L3: Canonical Capability Substrate

### 6.1 Objectives & Scope
Build and verify the canonical capability substrate for the standalone LAYA Omni Agent:
1. Every source-verified capability (23 tools) has exactly one canonical typed `CapabilitySpec` and registration entry in `CapabilityRegistry`.
2. Execution boundary enforces `CapabilityInvocation` -> `ToolResult` envelopes with automatic `ExecutionReceipt` generation.
3. Read-only capabilities normalize operational exceptions without swallowing process-control exceptions (`KeyboardInterrupt`, `SystemExit`).
4. Mutation/system capabilities are declaratively wrapped with strict safety characteristics (`ActionClass`, `AutonomyProfile`, `ConfirmationPolicy`, `RetryPolicy`, `IdempotencyClass`).
5. Legacy CLI and prototype paths remain completely operational via non-switching boundary (main dispatch remains on legacy path until L8/L9).

### 6.2 Code Changes & Architectural Additions
- `omni_engine/capabilities/registry.py`:
  - Implemented thread-safe `CapabilityRegistry` using `threading.RLock()` with fine-grained scoping (lock held strictly for dictionary mutations and lookups, never during tool execution).
  - Enforced unique capability IDs; rejected duplicate registrations and unawaited async coroutine functions.
  - Implemented `invoke(CapabilityInvocation) -> ToolResult` boundary.
  - Automatically generates `ExecutionReceipt` with sub-millisecond durations and epoch timestamps.
  - Re-raises `(KeyboardInterrupt, SystemExit, GeneratorExit)` without catching.
  - Translates `FileNotFoundError` $\to$ `NOT_FOUND`, `PermissionError` $\to$ `PERMISSION_DENIED`, `TimeoutError` $\to$ `TIMEOUT`, `URLError`/`ConnectionError` $\to$ `NETWORK_ERROR`, `CalledProcessError` $\to$ `PROCESS_FAILED`, `ValidationError` $\to$ `SCHEMA_VIOLATION`, `ValueError`/`TypeError` $\to$ `INVALID_ARGUMENT`.
- `omni_engine/capabilities/adapters.py`:
  - Implemented dedicated argument normalization adapters for all 12 tools whose signatures or formats differ from canonical schemas: `visual_browse`, `list_processes`, `kill_process`, `search_code`, `directory_tree`, `run_python`, `sqlite_exec`, `file_write`, `http_api`, `download_file`, `clipboard`, `inspect_data`.
  - Implemented prefix-anchored error interceptor (`intercept_legacy_error_string`), catching legacy tool error strings (`❌ File not found:`, `Write error:`, `Git error:`, `Ping test error:`, `Failed to terminate process:`, `Unsupported format for inspector`).
  - Anchored checks to eliminate false-positives on content-bearing tools (`file_read`, `search_code`) when file contents contain strings like "Access is denied" or "API key missing".
- `omni_engine/capabilities/definitions.py`:
  - Defined all 23 canonical `CapabilitySpec` instances with 100% 1:1 parity with source `OMNI_TOOL_REGISTRY`.
  - Built `build_canonical_registry()` assembling all specs and specialized adapters.
- `omni_engine/capabilities/__init__.py`: Clean re-exports of capability substrate components.
- `tests/test_l3_capabilities.py`: 25 unit tests (and 23 subtests) covering:
  - Registration lifecycle, duplicate rejection, coroutine rejection, query methods, JSON metadata export.
  - 100% 1:1 parity with `OMNI_TOOL_REGISTRY` (23 tools).
  - Read-only execution, error string interception (`safe_math`, `file_read`, `system_diagnostics`, `git_status`).
  - Process-control exception propagation (`KeyboardInterrupt`, `SystemExit`).
  - Mutation capability policies (non-`READ_ONLY`, side effects, strict confirmation on `kill_process`, `powershell`, `run_python`).
  - Parameterized invocation of **all 23 capabilities** with valid schema arguments, proving zero `TypeError` crashes.
  - False-positive prevention on content-bearing tools (`file_read` with sensitive strings).
  - Preservation of legacy CLI/prototype path and non-switching boundary.

### 6.3 Adversarial Review Remediation
- **Adversarial Plan Review**: Identified swallowed exceptions in legacy tools, argument mismatch (kwargs vs payload strings), and potential lock contention during tool execution. Remediated in plan before coding.
- **Adversarial Diff Review**: Identified 7 tools lacking kwarg adapters, 5 unintercepted error strings, unanchored substring false-positives on content tools, and `ToolResult` early return bypassing receipts. All 4 defects were repaired: specialized adapters created for all 12 differing tools, prefix-anchored checks added, false-positive checks eliminated, and receipt creation unified.

### 6.4 Test Results
- Ran: `python -m pytest tests/ -v`
- Result: **80 passed, 23 subtests passed in 32.99s (100% pass rate)**.
  - **Feature Acceptance Tests**: 78 passed
  - **Known Defect Reproduction Tests**: 2 passed

---

## 7. Checkpoint L4: Provider Foundations (System 1 & Generative Abstractions)

### 7.1 Objectives & Scope
Build vendor-independent provider abstractions for both System 1 (fast reflexive decisions) and Generative (System 2 synthesis/planning) models, decoupling LAYA from specific vendors:
1. `SystemOneProvider` abstract base contract (`predict_signals()`, `classify()`, `score()`, `health_check()`).
2. Implement `LayaProvider` wrapping local ModernBERT-large (`laya.Router()`) with thread-safe singleton lock to prevent duplicate weight loading and protect host RAM (8GB limit).
3. Implement `JevProvider` wrapping TypeSafe cloud API with non-crashing graceful degradation (`ErrorCode.UNCONFIGURED`) when unconfigured.
4. `GenerativeProvider` abstract base contract (`generate_text()`, `generate_structured()`, `health_check()`).
5. Implement `OpenRouterProvider` wrapping OpenRouter/OpenAI-compatible APIs with deterministic markdown fence stripping (`extract_json_from_text`), structured Pydantic model validation, configurable timeout budget (default 60s), and non-empty choice validation.
6. Zero local RAM overhead for generative calls (pure remote HTTP client).
7. Strict preservation of non-switching boundary (legacy `System1Router` and `System2Engine` intact).

### 7.2 Code Changes & Architectural Additions
- `omni_engine/providers/base.py`:
  - `ProviderError`: Exception envelope binding strongly typed `ErrorCode`, provider ID, model ID, and structured details.
  - `ProviderHealth`: Structured health contract inheriting from `BaseContractModel` (`extra="forbid"`, `validate_assignment=True`) with `latency_ms >= 0.0`.
  - `GenerationResult`: Normalized chat completion result with token metrics, finish reason, and latency.
  - `SystemOneProvider(ABC)`: Declaring `predict_signals()`, `classify()`, `score()`, and `health_check()`.
  - `GenerativeProvider(ABC)`: Declaring `generate_text()`, `generate_structured()`, and `health_check()`.
- `omni_engine/providers/system1.py`:
  - Module-level singleton lock `_ROUTER_LOCK = threading.RLock()` and `get_shared_laya_router()` preventing duplicate PyTorch allocations across multiple providers or tests.
  - `LayaProvider`:
    - Batched multi-question evaluation in a single forward pass (`predict_signals()`) satisfying the `<35ms` latency budget without $N \times$ sequential passes.
    - Numerical sanitization helper `sanitize_float` clamping values to `[0.0, 1.0]` and replacing NaN/Inf with `0.0`.
    - Probability distribution sanitization `sanitize_probabilities`.
    - Defensive extraction helper `_extract_decision_data` handling both dicts and `RouteDecision` objects, `None` confidence values, and uncalibrated distributions without `TypeError`.
    - Implemented `score(prompt, criteria)` evaluating criterion match probabilities.
    - Health check probe returning structured `ProviderHealth` with warm ping latency.
  - `JevProvider`:
    - Safe initialization when unconfigured (no credentials crash).
    - Returns `ProviderHealth(healthy=False, status_code=ErrorCode.UNCONFIGURED)`.
    - Raises normalized `ProviderError(ErrorCode.UNCONFIGURED)` on calls when missing `TYPESAFE_API_KEY`.
- `omni_engine/providers/generative.py`:
  - Deterministic markdown fence stripper `extract_json_from_text` using regex `r"```(?:json)?\s*([\s\S]*?)\s*```"` and bracket fallback.
  - `OpenRouterProvider`:
    - Supports configurable model, base URL, and explicit timeout parameter (`timeout: float = 60.0`).
    - Validates non-empty completion choices (`if not resp.choices: raise ProviderError(ErrorCode.PROCESS_FAILED)`).
    - Re-raises `ProviderError` directly to prevent masking by generic network exception handler.
    - Parses JSON into target Pydantic models via `generate_structured()`, wrapping validation errors into `ProviderError(ErrorCode.SCHEMA_VIOLATION)`.
    - Graceful non-crashing initialization when unconfigured.
- `omni_engine/providers/__init__.py`: Clean re-exports of all provider substrate components.
- `omni_engine/memory.py`:
  - Repaired Windows console encoding flaw (`UnicodeEncodeError` under `cp1252`) by replacing raw Unicode emojis (`⚠️`) with plain text ASCII `[WARNING]`.
- `tests/test_l4_providers.py`: 19 comprehensive unit tests covering:
  - Abstract contracts adherence for System 1 and Generative providers.
  - Batched multi-signal forward pass and single-pass classification with local ModernBERT.
  - RAM protection proving multiple `LayaProvider` instances share identical ModernBERT router singleton (`assertIs`).
  - Defensive answer extraction handling `None` confidence, invalid string confidence, and mock objects.
  - `score()` method evaluation in `[0.0, 1.0]`.
  - Jev unconfigured initialization, unconfigured health check, unconfigured prediction, and unconfigured score.
  - OpenRouter unconfigured initialization, unconfigured health check, and unconfigured generation.
  - Markdown code fence JSON extraction and bracket fallback.
  - Mocked structured generation into Pydantic models.
  - Schema violation error wrapping (`ErrorCode.SCHEMA_VIOLATION`).
  - Empty choices detection (`ErrorCode.PROCESS_FAILED`).
  - Configurable timeout budget verification.

### 7.3 Adversarial Review & Bug Fixes
- **Initial Test Run**:
  - Found eager `float(ans.get("confidence", 0.0))` threw `TypeError` when `confidence: None`. Repaired in `_extract_decision_data` by passing raw values to `sanitize_float`.
  - Found `OpenRouterProvider` lacked explicit timeout budget (OpenAI client default 600s). Added `timeout: float = 60.0`.
  - Found empty choices in `OpenRouterProvider` threw unhandled `IndexError`. Added explicit guard raising `ProviderError(ErrorCode.PROCESS_FAILED)`.
  - Found generic `except Exception` in `OpenRouterProvider.generate_text` masked `ProviderError(ErrorCode.PROCESS_FAILED)` as `ErrorCode.NETWORK_ERROR`. Added `except ProviderError: raise`.
  - Found `score()` contract method was specified in plan but omitted from ABC. Added `score()` to `SystemOneProvider(ABC)`, `LayaProvider`, and `JevProvider`.
  - Found Windows `cp1252` console encoding crashed `omni_engine/memory.py` on `\u26a0\ufe0f`. Replaced with ASCII `[WARNING]`.
- **Adversarial Diff Review**: **PASS (All remediations verified and tested)**.

### 7.4 Test Results
- Ran: `python -m unittest tests/test_l4_providers.py -v`
  - Result: **19 passed in 92.49s (100% pass rate)**.
- Ran: `python -m unittest discover tests -v`
  - Result: **99 passed in 123.56s (100% pass rate across entire repository)**.
    - L0 Baseline Tests: 10 passed
    - L1 & L1.1 Memory and Math Tests: 12 passed
    - L2 Contracts Tests: 18 passed
    - L2.1 Reconciliation Tests: 15 passed
    - L3 Capability Substrate Tests: 25 passed (+ 23 subtests passed)
    - L4 Provider Foundations Tests: 19 passed

---

## 8. Checkpoint L5: System One Decision Fabric

### 8.1 Objectives & Scope
Build the complete high-frequency typed `DecisionFrame` generation engine on top of `LayaProvider`, evaluating the full multi-dimensional decision state in a single low-latency forward pass:
1. `DecisionFabric`:
   - Single batched neural forward pass via `LayaProvider.predict_signals()` evaluating 15 canonical decision questions simultaneously.
   - Outputs strongly typed `DecisionFrame` adhering to `omni_engine/contracts/decision.py`.
2. Deterministic Pre-emption & Safety Floor Overrides (Invariants 1 & 7):
   - Fast-path for empty or whitespace prompts (<1ms) returning immediate clarification frame without invoking neural model.
   - Sliding-window head-tail truncation for prompts exceeding 3,000 characters.
   - High-risk safety floor pre-emption (`DEFAULT_HIGH_RISK_PATTERNS`) clamping `risk="high_risk_system"`, `reversibility="irreversible"` (Invariant 7), and forcing `escalation_required=True`.
   - Ambiguity and low-confidence triggers setting `needs_clarification=True` and `needs_generative_reasoning=True`.
   - Conversational disambiguation: informational/chat queries without tools force `requires_action=False`, `needs_plan=False`, `needs_tools=False`, and `model_tier="system_1"`.
   - Domain contract trap mitigation: maps domain probabilities to `candidate_domains: List[str]` without passing illegal extra `domain` field to `DecisionFrame` (`extra="forbid"`).
   - Graceful fallback: provider errors produce an escalated fallback `DecisionFrame` with `escalation_required=True`, `needs_generative_reasoning=True`, `model_tier="pro"`.
3. Standardized Evaluation Corpus & Benchmark:
   - 10-prompt benchmark dataset (`BENCHMARK_CORPUS`) covering conversational, file read, file write, process kill, powershell, git, sqlite, math, ambiguous, multi-step.
   - Evaluation runner `evaluate_decision_corpus()` profiling latency metrics (min, max, avg, p95) and reporting signal distributions.
4. Non-switching boundary preservation (legacy `omni_agent.py` and `omni_engine/planner.py` untouched).

### 8.2 Code Changes & Architectural Additions
- `omni_engine/decision/fabric.py`:
  - Implemented `DecisionFabric` coordinating fast reflexive decisions and generating strongly typed `DecisionFrame`.
  - Defined `DEFAULT_HIGH_RISK_PATTERNS` regexes (`rmdir`, `del /[a-z]`, `format`, `kill`, `kill_process`, `drop table`, `rm -rf`, `shutdown`, `reboot`, `powershell .*-enc`, `Invoke-Expression`).
  - Implemented `_truncate_prompt()` with head-tail sliding window (3,000 char threshold).
  - Implemented `_build_empty_prompt_frame()` providing instant (<0.1ms) deterministic clarification frames.
  - Implemented `_build_fallback_frame()` providing safe escalated frames on provider exceptions (`provider_id="{base}-fallback"`).
  - Implemented `_get_batched_questions()` defining all 15 canonical decision questions with rich criteria dictionaries matching `DecisionFrame` field names.
  - Implemented `evaluate(prompt, session_context, request_id) -> DecisionFrame`.
  - Applied deterministic boolean normalization, safety floor overrides, Invariant 7 reversibility clamping, ambiguity escalation, conversational disambiguation, and domain probability ranking.
- `omni_engine/decision/corpus.py`:
  - Defined `BENCHMARK_CORPUS` (10 diverse real-world benchmark prompts).
  - Implemented `evaluate_decision_corpus()` measuring latency (min, max, avg, p95) and extracting structured results.
- `omni_engine/decision/__init__.py`: Package exports for `DecisionFabric`, `DEFAULT_HIGH_RISK_PATTERNS`, `BENCHMARK_CORPUS`, and `evaluate_decision_corpus`.
- `omni_engine/system1.py`:
  - Repaired Windows console encoding crash (`UnicodeEncodeError` under `cp1252`) by replacing raw Unicode emojis (`🤖`, `⚡`) with ASCII `[System 1]`.
- `omni_engine/providers/system1.py`:
  - Fixed `_SHARED_ROUTER.preload()` parameter to `_SHARED_ROUTER.preload(["english"])`.
- `tests/test_l5_decision_fabric.py`: 12 comprehensive unit and integration tests covering:
  - `TestDecisionFrameContractAdherence`: Complete contract verification across all 10 mandatory signals and 4 extended signals, Pydantic validation, and JSON roundtrip serialization.
  - `TestEmptyPromptFastpath`: Instant deterministic DecisionFrame without calling neural weights (`call_count == 0`).
  - `TestMassivePromptTruncation`: Head-tail sliding window truncation.
  - `TestHighRiskSafetyOverride`: Clamping risk to `high_risk_system`, reversibility to `irreversible`, and setting `escalation_required=True`.
  - `TestAmbiguityTriggersClarification`: Vague commands triggering `needs_clarification=True`.
  - `TestConversationalPromptDisablesActionAndTools`: Non-action conversational queries disabling tools, planning, and generative reasoning.
  - `TestProviderFailureGracefulFallback`: Catching `ProviderError` and returning escalated fallback frame with fallback provider ID.
  - `TestDomainRankingOrder`: Extracting and sorting candidate domains by descending probability without violating `extra="forbid"`.
  - `TestLegacyNonSwitchingBoundary`: Preserving legacy `System1Router.route_tool`.
  - `TestBenchmarkCorpusStructure`: Validating benchmark dataset fields.
  - `TestEvaluateDecisionCorpusWithMockProvider`: Running evaluation runner with mock provider and reporting summary latency metrics.
  - `TestLiveLayaProviderSingleEvaluation`: Warm evaluation pass through local ModernBERT-large adhering to hardware-aware latency budget.

### 8.3 Adversarial Review & Bug Fixes
- **Pre-Implementation Plan Review**:
  - Found naming mismatch between plan (`REQUIRES_PLAN`, `REQUIRES_TOOLS`) and contracts (`NEEDS_PLAN`, `NEEDS_TOOLS`). Canonicalized question keys to exact contract field names.
  - Found domain contract trap: `DecisionSignalType.DOMAIN` exists, but `DecisionFrame` defines `candidate_domains: List[str]` and NO `domain` field. Passing `domain=...` would trigger `extra="forbid"`. Implemented probability extraction into `candidate_domains` list and stored raw signal in `raw_signals`.
  - Identified 35ms GPU SLA vs CPU reality: ModernBERT on CPU takes ~3.5s per forward pass; hardware-aware SLA configured (`<35ms` on CUDA, `<35000ms` for 15-question CPU matrix).
  - Identified empty prompt waste: added deterministic fast-path (<1ms).
- **Post-Implementation Diff Review**:
  - Found Windows console `UnicodeEncodeError` in `omni_engine/system1.py` on robot emoji `🤖`. Repaired with ASCII text.
  - Found method name mismatch in legacy test: updated `hasattr(router, "route")` to `hasattr(router, "route_tool")`.
  - Found fallback frame lacked provider-id fallback indicator: updated to `f"{base_prov}-fallback"`.
- **Adversarial Diff Review**: **PASS (All invariants verified)**.

### 8.4 Test Results
- Ran: `python -m unittest tests/test_l5_decision_fabric.py -v`
  - Result: **12 passed in 122.61s (100% pass rate)**.
- Ran: `python -m unittest discover tests -v`
  - Result: **111 passed in 160.07s (100% pass rate across entire repository)**.
    - L0 Baseline Tests: 10 passed
    - L1 & L1.1 Memory and Math Tests: 12 passed
    - L2 Contracts Tests: 18 passed
    - L2.1 Reconciliation Tests: 15 passed
    - L3 Capability Substrate Tests: 25 passed (+ 23 subtests passed)
    - L4 Provider Foundations Tests: 19 passed
    - L5 Decision Fabric Tests: 12 passed

---

## 9. Checkpoint L6A: Hierarchical Routing Foundation

### 9.1 Objectives & Scope
Replace flat tool catalog slicing (the legacy `[:12]` truncation defect, ISSUE-02) with the foundational stages of the multi-tier routing architecture:
`Request → Domain → Small Candidate Set → Capability`:
1. `HierarchicalRouter`:
   - Consumes `DecisionFrame` generated by `DecisionFabric` (L5).
   - Maps `candidate_domains` to candidate capabilities registered in `CapabilityRegistry` (L3).
   - Prunes candidate set down to a bounded, highly relevant subset (typically 3–6 capabilities).
   - Dynamic zero-inference short circuit for single domains (count <= max_candidates) in <0.2ms.
   - Fast deterministic lexical token overlap scoring when pruning large candidate sets in <1ms.
2. Fail-Open Fallback & Safety Pinning:
   - Automatic cross-domain pooling: Always pools at least top-2 domains for multi-step tasks (`needs_plan=True` or `task_class in ["multi_step_quest", "code_refactor"]`).
   - Low confidence (<0.55) or high ambiguity (>0.65) triggers fail-open pooling across top-2 domains.
   - Explicit keyword capability pinning: Declarative `CAPABILITY_PIN_MAP` regex scanning unconditionally pins named tools at score=1.0 with rationale `"explicit_keyword_pinned"`.
   - "General" domain technical promotion: When `"general"` co-occurs with `needs_tools=True`, technical domains are automatically promoted.
3. Elimination of Legacy Truncation Defect (ISSUE-02):
   - Proved tools 13–23 (previously dropped by legacy `[:12]` slicing like `sqlite_exec`, `inspect_data`, `safe_math`, `powershell`, `ping_test`) are reliably accessible.
4. Non-Switching Principle:
   - Preserved existing `omni_agent.py` and `omni_engine/planner.py` on the legacy dispatch path.

### 9.2 Code Changes & Architectural Additions
- `omni_engine/contracts/routing.py`:
  - `CapabilityCandidate`: Strongly typed individual candidate model with `capability_id`, `domain`, `score` (bounded in [0.0, 1.0]), `rationale`, and `spec_summary`.
  - `RouteDecision`: Complete hierarchical routing decision envelope containing `selected_domain`, `candidate_domains`, ranked `candidates`, `is_fail_open`, `fallback_reason`, `catalog_reduction_ratio`, `total_registry_capabilities`, `latency_ms`, and `metadata`.
  - Strict validators: duplicate candidate rejection, fail-open reason consistency (`is_fail_open=True` requires reason; `False` requires None), candidate count <= total registry capabilities, finite bounded reduction ratio.
- `omni_engine/contracts/__init__.py`: Clean exports of `CapabilityCandidate` and `RouteDecision`.
- `omni_engine/routing/router.py`:
  - `DOMAIN_KEYWORD_MAP`: Mapping domain keywords to canonical domains (`web`, `browser`, `os`, `dev`, `data`).
  - `CAPABILITY_PIN_MAP`: Regex patterns mapping unambiguous tool mentions directly to canonical capability IDs.
  - `HierarchicalRouter`: Coordinating conversational gating (<5ms), domain resolution, fail-open analysis, explicit capability pinning, candidate retrieval, zero-inference short circuiting, and dynamic lexical pruning.
- `omni_engine/routing/__init__.py`: Package exports for `DOMAIN_KEYWORD_MAP`, `CAPABILITY_PIN_MAP`, and `HierarchicalRouter`.
- `omni_engine/decision/fabric.py`:
  - Repaired ambiguous logic condition at lines 401–406: replaced buggy `ambiguity_sig.confidence > 0.65` with checks for `ambiguity_sig.value in ["ambiguous", True]`, numerical ambiguity value > 0.65, or `probabilities["ambiguous"] > 0.65`.
- `tests/test_l6a_routing.py`: 12 comprehensive unit and integration tests covering:
  - `test_empty_and_whitespace_prompt_fastpath`: Fast empty/whitespace return in <5ms without neural scoring.
  - `test_conversational_gating`: Pure conversational prompts returning 0 candidates with 100% catalog reduction.
  - `test_single_domain_exact_filtering`: Single-domain query filtering to domain capabilities with zero-inference short circuit.
  - `test_candidate_pruning_bound`: Bounding OS domain (8 tools) to <= max_candidates (e.g. 5).
  - `test_multi_step_cross_domain_retention`: Preserving tools across both domains (e.g. `download_file` in web + `run_python` in dev) for multi-step prompts.
  - `test_fail_open_on_low_confidence_and_ambiguity`: Low confidence or ambiguity pooling adjacent domains with fail-open reason.
  - `test_explicit_capability_keyword_pinning`: Naming tools (e.g. `sqlite`, `git status`, `ping`, `clipboard`, `safe_math`) pins them at score 1.0.
  - `test_general_domain_promotion`: Promoting technical domain when `"general"` co-occurs with `needs_tools=True`.
  - `test_elimination_of_legacy_truncation_defect`: Accessing tools 13-23 dropped by legacy prototype.
  - `test_contract_immutability_and_validation`: Rejecting extra fields, duplicate IDs, and invalid fail-open states.
  - `test_legacy_non_switching_boundary`: Verifying legacy `AutonomousPlanner` and `System1Router` remain intact.
  - `test_live_modernbert_hierarchical_routing`: End-to-end verification through real Laya ModernBERT neural weights.

### 9.3 Adversarial Review & Bug Fixes
- **Pre-Implementation Plan Review** (Subagent `fad0d452-09c7-4d98-9ab3-4ffa83752de4`):
  - Rec-1 (Multi-step cross-domain retention): Automatically pool top-2 domains whenever `needs_plan=True` or `task_class in ["multi_step_quest", "code_refactor"]`.
  - Rec-2 (Latency cliff avoidance): Eliminated loop-based `provider.score()`; implemented zero-inference short circuit for count <= max_candidates (<0.2ms) and fast deterministic lexical scoring (<1ms).
  - Rec-3 (Domain confidence access): Safely extracted confidence from `frame.raw_signals.get("domain")` without violating `extra="forbid"`.
  - Rec-4 (Contract validation): Enforced duplicate rejection, fail-open consistency, and candidate count limits in `RouteDecision`.
  - Rec-5 (Declarative keyword pinning): Replaced ad-hoc keyword list with canonical `CAPABILITY_PIN_MAP` regex matcher.
  - Rec-6 ("General" domain trap): Promoted technical domains when `"general"` co-occurs with `needs_tools=True`.
- **Post-Implementation Bug Fixes**:
  - Repaired `DecisionFabric.evaluate` argument name (`session_context=context`).
  - Repaired boolean normalization in router (`in [True, "true", "yes", ...]`).
  - Repaired `total_registry_capabilities == 0` edge case in candidate count validator.
  - Repaired `fabric.py` ambiguity check (checking probability/value instead of model confidence).
- **Adversarial Diff Review** (Subagent `4af90591-4b8b-4fad-9e11-f311899b43a0`): **PASS (All invariants and 6 recommendations verified)**.

### 9.4 Test Results
- Ran: `python -m unittest tests/test_l6a_routing.py -v`
  - Result: **12 passed in 140.90s (100% pass rate)**.
- Ran: `python -m unittest discover tests -v`
  - Result: **123 passed in 244.52s (100% pass rate across entire repository)**.
    - L0 Baseline Tests: 10 passed
    - L1 & L1.1 Memory and Math Tests: 12 passed
    - L2 Contracts Tests: 18 passed
    - L2.1 Reconciliation Tests: 15 passed
    - L3 Capability Substrate Tests: 25 passed (+ 23 subtests passed)
    - L4 Provider Foundations Tests: 19 passed
    - L5 Decision Fabric Tests: 12 passed
    - L6A Hierarchical Routing Tests: 12 passed

---

## Checkpoint L7 — Skills Substrate & Workflow Manifests (COMPLETED)

**Timestamp**: 2026-09-23T12:05:00+05:30  
**Phase**: Phase II — System 1 Decision Fabric & Capability Routing  
**Status**: **COMPLETED & VERIFIED**  
**Associated Commit**: Pending Checkpoint Commit  

### 1. Architectural Motivation & Invariants
In accordance with Invariant 1 (*Deterministic Control, Probabilistic Reasoning*) and Invariant 4 (*Strongly Typed Capability Contracts*), multi-step agent operations must not rely on unconstrained model improvisation when structured, proven workflows exist.
Checkpoint L7 introduces the **Skills Substrate**:
- A **Skill** is a structured, reusable workflow abstraction mapping high-level user objectives to constrained capability sets, declarative workflow step templates, and explicit safety floors.
- **SkillManifest**: Strongly typed Pydantic contract enforcing schema validation, non-empty workflows when planning is not required, step capability inclusion, phantom dependency prevention, and DAG acyclicity via a 3-color DFS cycle detector.
- **SkillRegistry**: Thread-safe registry (`RLock`) enforcing zero dangling capabilities against `CapabilityRegistry`, action class encompassment (blocking action-class omission spoofing), constituent high-risk confirmation policy floors, and autonomy ranking floors.
- **Canonical Skills**: 7 production-grade skills backed 100% by the 23 verified tools in the repository.

### 2. Files Added & Modified
1. `omni_engine/contracts/skill.py`:
   - `SkillStepTemplate(BaseContractModel)`: Defines `step_id`, `capability_id`, `description`, `depends_on`, `default_args`, `arg_mappings`, `verification_rule`, `can_fail_silently`.
   - `SkillManifest(BaseContractModel)`: Canonical contract defining `skill_id`, `version`, `domain`, `name`, `description`, `intent_patterns`, `input_schema`, `output_schema`, `required_capabilities`, `optional_capabilities`, `action_classes`, `workflow_template`, `planning_required`, `verification_strategy`, `applicable_autonomy`, `confirmation_policy`, `escalation_conditions`, and `metadata`.
   - Built-in Invariant Validators:
     - Disjoint capability sets: `required_capabilities` and `optional_capabilities` must be strictly disjoint.
     - Non-empty template enforcement: If `planning_required=False`, `workflow_template` must contain at least 1 step.
     - Step capability membership: Every step `capability_id` must belong to the manifest's declared capabilities.
     - Phantom dependency rejection: Any dependency declared in `step.depends_on` must reference a valid step defined in the template.
     - DAG Acyclicity (DFS Cycle Detector): Three-color cycle detection identifies circular step dependencies (`s1 -> s2 -> s1`) and formats the exact cycle chain in the exception.
     - High-Risk Confirmation Floor: Manifests declaring high-risk action classes (`LOCAL_DELETE`, `EXTERNAL_DELETE`, `EXTERNAL_SEND`, `SYSTEM_ACTION`, `SECURITY_SENSITIVE`, `FINANCIAL`) cannot declare `confirmation_policy=NEVER`.
2. `omni_engine/contracts/__init__.py`:
   - Re-exported `SkillStepTemplate` and `SkillManifest`.
3. `omni_engine/skills/registry.py`:
   - `SkillRegistry`: Thread-safe registry (`RLock`) with lazy thread-safe access to `CapabilityRegistry`.
   - Validations on registration:
     - Duplicate skill ID rejection.
     - Zero dangling capabilities: Every required, optional, and step capability must exist in `CapabilityRegistry`.
     - Action class encompassment: A skill cannot reference a capability whose action class is not declared in `manifest.action_classes` (prevents action-class omission spoofing).
     - Constituent high-risk confirmation floor: Independently enforces that constituent high-risk capabilities forbid `confirmation_policy=NEVER`.
     - Autonomy profile floor: A skill cannot declare an autonomy tier weaker than the minimum autonomy required by its constituent capabilities.
     - Mutation isolation: Deep copy returns prevent internal registry state corruption.
     - Methods: `register`, `unregister`, `has`, `get`, `list_all`, `list_manifests`, `list_by_domain`, `find_by_intent`, `export_manifests`, `count`.
4. `omni_engine/skills/definitions.py`:
   - 7 canonical skills backed 100% by the 23 verified tools:
     1. `web_research` (domain: `web`, required: `[web_search, scrape_url]`, optional: `[http_api, download_file]`, action_classes: `[READ_ONLY]`)
     2. `inspect_repository` (domain: `dev`, required: `[directory_tree, search_code, file_read]`, optional: `[git_status]`, action_classes: `[READ_ONLY]`)
     3. `diagnose_system` (domain: `os`, required: `[system_diagnostics, list_processes]`, optional: `[ping_test]`, action_classes: `[READ_ONLY]`)
     4. `file_transform` (domain: `os`, required: `[file_read, file_write]`, optional: `[run_python]`, action_classes: `[READ_ONLY, LOCAL_CREATE]`)
     5. `analyze_data` (domain: `data`, required: `[sqlite_exec, inspect_data]`, optional: `[safe_math]`, action_classes: `[READ_ONLY, LOCAL_UPDATE]`)
     6. `browser_information_task` (domain: `browser`, required: `[visual_browse]`, optional: `[browser_screenshot]`, action_classes: `[READ_ONLY, SYSTEM_ACTION, LOCAL_CREATE]`)
     7. `perform_git_inspection` (domain: `dev`, required: `[git_status, search_code, file_read]`, optional: `[]`, action_classes: `[READ_ONLY]`)
   - `build_canonical_skill_registry()` helper for instant canonical instantiation.
5. `omni_engine/skills/__init__.py`:
   - Clean public API export.
6. `tests/test_l7_skills.py`:
   - 26 targeted unit and integration tests covering contract invariants, cycle detection, phantom dependency rejection, policy floors, spoofing defenses, thread safety, canonical parity, and legacy non-switching boundaries.

### 3. Adversarial Review & Repairs
- Initial Adversarial Diff Review identified 5 potential vulnerabilities:
  1. *Phantom step dependencies*: Resolved via `all_step_ids` set lookup in `SkillManifest`.
  2. *DAG circular dependencies*: Resolved via 3-color DFS cycle detector in `SkillManifest`.
  3. *Action class spoofing bypass*: Resolved in `SkillRegistry` by verifying `spec.action_class in manifest.action_classes` and independently checking constituent tools against `confirmation_policy=NEVER`.
  4. *Canonical skills action class omissions*: Resolved by auditing and including all constituent tool action classes in `definitions.py`.
  5. *CapabilityRegistry concurrency race*: Resolved via `_get_capability_registry_under_lock()` encapsulated within `with self._lock:`.
- Final Adversarial Verification verdict: **PASS**.

### 4. Verification & Test Evidence
- **L7 Test Suite**: `python -m unittest tests/test_l7_skills.py -v`
  - Output: **26 tests passed in 0.025s (100% pass rate)**.
- **Full Repository Suite**: `python -m unittest discover tests -v`
  - Output: **149 tests passed in 191.42s (100% pass rate)** across all checkpoints (L0, L1, L2, L2.1, L3, L4, L5, L6A, L7).
- **Non-Switching Boundary**: Confirmed legacy `omni_agent.py` and `omni_engine/planner.py` remain untouched and functional.

---

---

## CHECKPOINT L6B — FINAL SKILL-AWARE HIERARCHICAL ROUTER

**Status**: COMPLETED & VERIFIED  
**Date**: 2026-09-24T05:25:00+05:30  
**Branch**: `laya-autonomous-v2`  
**Git Commit**: Pending commit  

### 1. Architectural Mission & Pipeline Flow
Checkpoint L6B completes Phase 2 of hierarchical capability reduction by unifying the System 1 Decision Fabric (L5), Capability Substrate (L3), and Skills Substrate (L7) into a high-precision, low-latency, skill-aware routing pipeline:
`Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`

Key architectural capabilities implemented:
1. **Dynamic Candidate Floor Expansion (Blocking-1)**:
   - When a skill is matched, its `required_capabilities` along with any explicit keyword-pinned tools (`CAPABILITY_PIN_MAP`) are designated as mandatory capabilities.
   - If the count of mandatory capabilities exceeds `max_candidates` (e.g. 4 required tools with `max_candidates=3`), the router dynamically expands the candidate floor to `len(mandatory_caps)` rather than arbitrarily dropping critical constituent tools.
   - Emits structured telemetry: `metadata["budget_expanded"] = True` and `metadata["expanded_reason"] = "skill_required_capabilities_exceeded_max"`.
2. **Unconditional Cross-Domain Spec Backfill (Blocking-2)**:
   - Constituent capabilities of a skill that originate outside the primary domain (e.g. `file_transform` skill in domain `os` utilizing `run_python` from domain `dev`) are unconditionally backfilled with their `CapabilitySpec` directly from the `CapabilityRegistry`.
3. **Dual-Threshold Gating & Anti-Locking Defenses (Blocking-3)**:
   - *Destructive Verb Gate*: Prohibits non-destructive skills from matching queries with destructive actions (`delete`, `remove`, `kill`, `drop`, `purge`, `terminate`).
   - *Single Generic Token Gate*: Generic single-word tokens (`file`, `run`, `status`, `data`, `system`, `check`, `test`, `web`, `code`, `repo`, `python`) cannot trigger skill locking on their own.
   - *Description Score Ceiling*: Overlap scores on skill descriptions are capped at 0.50, ensuring that only high-confidence intent pattern matches (>=0.75) select a skill.
   - *Morphological Stemmer*: Deterministic suffix and terminal-e stripping (`ing`, `tion`, `s`, `ed`, `e`) aligns verbal/noun forms without external NLP dependencies.
4. **Strongly Typed Skill Telemetry (Blocking-4)**:
   - `RouteDecision` extended with `selected_skill: Optional[str]`, `candidate_skills: List[str]`, `skill_workflow_template: Optional[List[SkillStepTemplate]]`, and `skill_confirmation_policy: Optional[ConfirmationPolicy]`.
   - Strict mutual exclusivity validator: If `selected_skill is None`, `skill_workflow_template` and `skill_confirmation_policy` must strictly be `None`.
5. **Clean Relative Imports (Blocking-5)**:
   - Imports in `contracts/routing.py` use relative imports (`from .enums import ConfirmationPolicy`, `from .skill import SkillStepTemplate`), completely avoiding circular import deadlocks.
6. **Unified Deduplication & Multi-Rationale Merging**:
   - Capabilities satisfying multiple criteria (e.g. pinned by keyword AND required by skill) are cleanly merged to score 1.0 with combined rationale `"explicit_keyword_pinned+skill_required"`.
7. **Zero-Latency Fast-Paths**:
   - Empty/whitespace prompts return 0 candidates, `selected_skill=None` in <0.1ms.
   - Pure conversational queries (`needs_tools=False`, `requires_action=False`) return in <0.2ms.
8. **Preservation of Non-Switching Boundary**:
   - Legacy agent loop in `omni_agent.py` and `omni_engine/planner.py` remains untouched and functional.

### 2. Code Changes & Implementation Details
1. `omni_engine/contracts/routing.py`:
   - Added `selected_skill: Optional[str] = None`
   - Added `candidate_skills: List[str] = Field(default_factory=list)`
   - Added `skill_workflow_template: Optional[List[SkillStepTemplate]] = None`
   - Added `skill_confirmation_policy: Optional[ConfirmationPolicy] = None`
   - Added Pydantic `@model_validator(mode="after")` enforcing strict correlation between `selected_skill`, `skill_workflow_template`, and `skill_confirmation_policy`.
2. `omni_engine/routing/router.py`:
   - Updated `HierarchicalRouter.__init__` to accept `skill_registry: Optional[SkillRegistry] = None`, defaulting to `build_canonical_skill_registry(self.registry)`.
   - Integrated skill discovery via `find_by_intent` and tokenized scoring against intent patterns and descriptions.
   - Enforced dynamic candidate budget expansion, spec backfilling, destructive verb gating, generic token gating, and deduplication.
3. `tests/test_l6b_skill_routing.py`:
   - 16 comprehensive unit and integration tests:
     - `test_route_decision_contract_validation`: Validates typed fields and consistency rules.
     - `test_route_decision_invalid_skill_inconsistency`: Proves rejection of inconsistent skill workflow / policy state.
     - `test_empty_prompt_fast_path`: Proves deterministic <5ms response with empty candidates and None skill.
     - `test_conversational_fast_path`: Proves conversational prompts bypass skills and tool scoring.
     - `test_exact_canonical_skill_matches`: Tests all 7 canonical skills with typical matching user prompts.
     - `test_skill_required_capabilities_prioritized`: Verifies skill-required tools receive score 0.95 and top ranking.
     - `test_dynamic_floor_expansion_blocking_1`: Verifies candidate budget expands when mandatory tools exceed `max_candidates`.
     - `test_unconditional_cross_domain_spec_backfill_blocking_2`: Verifies cross-domain constituent tool specs are backfilled.
     - `test_anti_locking_defenses_destructive_verbs_blocking_3`: Verifies destructive verbs prevent non-destructive skill match.
     - `test_anti_locking_defenses_generic_single_tokens_blocking_3`: Verifies single generic words do not false-lock skills.
     - `test_unified_deduplication_and_rationale_merging`: Verifies multi-rationale deduplication without duplicate candidates.
     - `test_budget_conscious_optional_capabilities`: Verifies optional tools receive score 0.75 without triggering budget expansion.
     - `test_fallback_to_pure_domain_routing`: Verifies ad-hoc domain prompts fall back to capability routing with `selected_skill=None`.
     - `test_multi_step_cross_domain_pooling_with_skill`: Verifies planning queries pool domains while selecting appropriate skill.
     - `test_legacy_non_switching_boundary`: Verifies legacy `omni_agent.py` and `omni_engine/planner.py` remain untouched and operational.
     - `test_live_modernbert_skill_routing`: End-to-end integration test with live ModernBERT-large neural inference.
4. `tasks/ACTIVE_PLAN.md` & `tasks/MASTER_PLAN.md`:
   - Updated to mark Checkpoint L6B fully complete and document the hard stop boundary before L8.

### 3. Adversarial Review & Verdict
- Independent adversarial diff review executed by subagent `9c333b2f-014c-4349-9b51-55a94c982971`.
- Verified all 5 recommendations: Dynamic candidate floor expansion, unconditional cross-domain spec backfill, dual-threshold anti-locking defenses, strongly typed contracts, and clean relative imports.
- Final Review Verdict: **PASS ✅**.

### 4. Verification & Test Evidence
- **L6B Test Suite**: `python -m unittest tests/test_l6b_skill_routing.py -v`
  - Output: **16 tests passed in 83.82s (100% pass rate)**.
- **Full Repository Test Suite**: `python -m unittest discover tests -v`
  - Output: **165 tests passed in 148.33s (100% pass rate)** across all checkpoints (L0, L1, L1.1, L2, L2.1, L3, L4, L5, L6A, L7, L6B).
  - Breakdown:
    - `tests/test_l0_baselines.py`: 10 passed
    - `tests/test_l1_repairs.py`: 12 passed
    - `tests/test_l2_contracts.py`: 18 passed
    - `tests/test_l2_1_reconciliation.py`: 15 passed
    - `tests/test_l3_capabilities.py`: 25 passed (+ 23 subtests passed)
    - `tests/test_l4_providers.py`: 19 passed
    - `tests/test_l5_decision_fabric.py`: 12 passed
    - `tests/test_l6a_routing.py`: 12 passed
    - `tests/test_l7_skills.py`: 26 passed
    - `tests/test_l6b_skill_routing.py`: 16 passed
- **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` verified operational on legacy path.
- **Stopping Boundary**: Engineering activity paused cleanly before L8 (Argument Resolver).

---

## Cumulative Summary of Repository Files

| File | Nature / Purpose |
| :--- | :--- |
| `omni_engine/contracts/routing.py` | `CapabilityCandidate` and `RouteDecision` boundary contracts extended with strongly typed skill telemetry (`selected_skill`, `skill_workflow_template`, `skill_confirmation_policy`). |
| `omni_engine/routing/router.py` | `HierarchicalRouter` with full skill-aware pipeline, dynamic floor expansion, cross-domain backfill, and anti-locking defenses. |
| `omni_engine/routing/__init__.py` | Public re-exports for hierarchical routing substrate (`DOMAIN_KEYWORD_MAP`, `CAPABILITY_PIN_MAP`, `HierarchicalRouter`). |
| `tests/test_l6b_skill_routing.py` | 16 unit and integration tests covering skill routing, floor expansion, cross-domain backfill, anti-locking, and live ModernBERT evaluation. |
| `omni_engine/contracts/skill.py` | `SkillStepTemplate` and `SkillManifest` boundary contracts with safety floors, DFS cycle detector, and phantom dependency prevention. |
| `omni_engine/skills/registry.py` | Thread-safe `SkillRegistry` with zero dangling capabilities verification, action-class encompassment, and policy floors. |
| `omni_engine/skills/definitions.py` | 7 canonical skills backed 100% by the 23 verified tools, and `build_canonical_skill_registry()` builder. |
| `omni_engine/skills/__init__.py` | Public re-exports for skills substrate (`SkillRegistry`, `CANONICAL_SKILLS`, `build_canonical_skill_registry`). |
| `tests/test_l7_skills.py` | 26 unit and integration tests covering skill contracts, registry invariants, policy floors, spoofing defenses, and canonical parity. |
| `tests/test_l6a_routing.py` | 12 unit and integration tests covering routing contracts, fast-paths, pooling, pinning, and live ModernBERT evaluation. |
| `omni_engine/decision/fabric.py` | `DecisionFabric` producing validated `DecisionFrame` packets with fast-paths, safety overrides, and repaired ambiguity check. |
| `omni_engine/decision/corpus.py` | Standardized 10-prompt benchmark evaluation corpus (`BENCHMARK_CORPUS`) and evaluation runner. |
| `omni_engine/decision/__init__.py` | Public re-exports for decision fabric substrate. |
| `tests/test_l5_decision_fabric.py` | 12 unit and integration tests covering contract completeness, fast-paths, safety overrides, and live ModernBERT evaluation. |
| `omni_engine/providers/base.py` | Abstract provider contracts (`SystemOneProvider`, `GenerativeProvider`), `ProviderError`, `ProviderHealth`, `GenerationResult`. |
| `omni_engine/providers/system1.py` | `LayaProvider` (ModernBERT-large with RAM singleton lock, batching, defensive parsing) and `JevProvider` (graceful degradation). |
| `omni_engine/providers/generative.py` | `OpenRouterProvider` (markdown code fence stripping, structured Pydantic extraction, timeout budgets). |
| `omni_engine/providers/__init__.py` | Public re-exports of provider abstractions and helper functions. |
| `tests/test_l4_providers.py` | 19 unit tests covering provider contracts, ModernBERT batching, Jev unconfigured, OpenRouter structured parsing, and defensive parsing. |
| `omni_engine/capabilities/registry.py` | Canonical thread-safe `CapabilityRegistry` with fine-grained lock scoping and `ToolResult` boundary. |
| `omni_engine/capabilities/adapters.py` | Argument normalization adapters and prefix-anchored error interceptors for 23 source tools. |
| `omni_engine/capabilities/definitions.py` | 23 canonical `CapabilitySpec` definitions and `build_canonical_registry()` builder. |
| `omni_engine/capabilities/__init__.py` | Public exports of canonical capability substrate. |
| `tests/test_l3_capabilities.py` | 25 unit tests (+ 23 subtests) covering registry, parity, execution boundaries, and all 23 tool invocations. |
| `omni_engine/contracts/enums.py` | Canonical enums: `ActionClass` (11), `AutonomyProfile` (5), `ConfirmationPolicy` (3), `RetryPolicy` (4), `IdempotencyClass` (5), `ToolOutcome` (3), `VerificationStatus` (3), `ErrorCode` (19), `DecisionSignalType` (16). |
| `omni_engine/contracts/base.py` | `BaseContractModel` enforcing `extra="forbid"` and `validate_assignment=True`. |
| `omni_engine/contracts/trace.py` | `TraceContext` with multi-tier causal correlation fields (`trace_id`, `quest_id`, `plan_id`, etc.). |
| `omni_engine/contracts/decision.py` | `DecisionSignal` with provenance and `DecisionFrame` with 16 signal dimensions. |
| `omni_engine/contracts/capability.py` | `CapabilitySpec`, `CapabilityInvocation`, `ToolError`, `ExecutionReceipt`, `VerificationResult`, `ToolResult`, `ExecutableCapability`. |
| `omni_engine/contracts/agent.py` | `AgentRequest`, `AgentResponse`, `AgentEvent`. |
| `omni_engine/contracts/__init__.py` | Clean re-exports of all contract types. |
| `tests/test_l2_1_reconciliation.py` | 15 unit tests covering inventory, error codes, provenance, policy enums, partial outcomes, and invocation context. |
| `tests/test_l2_contracts.py` | 18 unit tests covering contracts validation, serialization, exclusivity, and signal bounds. |
| `tests/test_l1_repairs.py` | 12 unit tests covering safe math AST evaluation, resource bounds, atomic writes, and 3-state memory. |
| `tests/test_l0_baselines.py` | 10 unit tests covering baseline tool registry and confirmed defect reproductions. |
| `omni_engine/memory.py` | Continuous memory with atomic `.tmp` persistence, `.corrupt` quarantine, 3-state outcome tracking, and ASCII warning logging. |
| `omni_engine/system1.py` | Legacy prototype System 1 router with ASCII warning/log output. |
| `omni_engine/tools/data_tools.py` | AST mathematical evaluation with strict deterministic resource bounds. |
| `requirements.txt` | Core dependencies with pinned compatible range `pydantic>=2.0.0,<3.0.0`. |
| `pytest.ini` | Pytest configuration scoping test discovery strictly to `tests/` directory. |
| `AGENTS.md` | Repository invariants, documentation synchronization rules, and phased engineering protocol. |
| `LAYA_BUILD_STATE.md` | Ground truth build state, health matrix, test categorization breakdown, and blockers. |
| `HANDOFF.md` | Operational continuation guide for next agent session (paused before L8). |
| `tasks/MASTER_PLAN.md` | Strategic roadmap (L0–L25) with completed L0, L1, L1.1, L2, L2.1, L3, L4, L5, L6A, L7, L6B. |
| `tasks/ACTIVE_PLAN.md` | Active checkpoint plan documenting L6B completion and hard stop before L8. |
| `tasks/KNOWN_ISSUES.md` | Defect tracking and resolution evidence. |
| `END_TO_END_EXECUTION_LOG.md` | This document: persistent cumulative chronological evidence ledger. |

---

## Operating Protocol for Maintaining This Log

1. **Mandatory Continuous Append**: Every subsequent task, checkpoint, architectural decision, code change, deletion, or test suite execution MUST be logged here chronologically.
2. **Evidence First**: All reported test results must include exact counts, command lines, and pass/fail statuses.
3. **Log Hygiene**: Keep this document as an executive and technical evidence ledger, not a raw duplicate of git diffs.

---

# CHECKPOINT L7.5: System One Truth, Calibration & Upstream Alignment

**Date / Timestamp**: 2026-09-24T16:30:00+05:30  
**Branch**: `laya-autonomous-v2`  
**Status**: **COMPLETED & VERIFIED**  
**Cumulative Test Suite**: **181 / 181 Passed (100%)** (+ 23 subtests passed) in 48.60s  

### 1. Mandatory Pre-Flight Reconnaissance & Invariant Verification
- Verified active branch: `laya-autonomous-v2`. Working tree clean, zero unstaged changes.
- Read all 13 canonical documents.
- Target scope: Three-phase goal `L7.5 → L8 → L9`. Hard stopping boundary strictly maintained after L9.

### 2. Source-Truth Gates
#### Gate A: SkillManifest Invariants
- Identified that in previous prototype skill manifests, optional capabilities (`http_api`, `download_file`, `run_python`) were declared in documentation but omitted in code due to conflicting action class tiers.
- Hardened `omni_engine/skills/registry.py`: Upgraded `_validate_skill_autonomy_profile()` to inspect ALL constituent capabilities (`required_capabilities | optional_capabilities | step_capabilities`).
- Guaranteed: No skill can bypass autonomy constraints or confirmation floors by placing high-risk capabilities into optional slots. Preserved backward-compatible error message formatting (`"weaker than required capability"`). Verified with `tests/test_l7_skills.py` (26/26 passed).

#### Gate B: Hardware Reality & Latency Truth
- Empirically measured on Windows 10 host:
  - **Hardware Profile**: 4-core CPU, 7.81 GB total physical RAM, PyTorch `2.13.0+cpu`, **NO CUDA GPU**.
  - **Resident Memory**: ModernBERT-large consumes **1.64 GB RAM** resident.
  - **Cold Model Load**: ~69.3s.
  - **Warm CPU Latency Profile**:
    - Single question: p50 = **748.9ms** | max = 784.4ms
    - 3 questions: p50 = **3,629.9ms** (~3.6s)
    - 5 questions: p50 = **5,681.6ms** (~5.7s)
    - 10 questions: p50 = **10,660.6ms** (~10.7s)
    - 15 questions (Full Frame): p50 = **15,388.7ms** (~15.4s)
- **Empirical Invariant Proved**: The `<35ms` latency target is achievable strictly under CUDA GPU acceleration. On CPU-only developer machines, evaluating 15 questions sequentially takes ~15.4s, empirically proving the architectural necessity of two-stage **Adaptive Question Groups** (Triage: ~3.6s vs Full: ~15.4s).

#### Gate C: Scattered Thresholds Inventory
- Cataloged all scattered inline magic numbers across `fabric.py` and `router.py`:
  - `0.55` (domain confidence threshold)
  - `0.65` (ambiguity escalation threshold)
  - `0.75` (skill selection threshold)
  - `0.50` (skill candidate inclusion and description ceiling)
  - `0.85` / `0.70` (domain primary vs pooled candidate base scores)
  - `0.98` / `0.75` (skill required vs optional candidate scores)
  - `1.0` (pinned capability score)
  - Categorized each into `CALIBRATED_MODEL_THRESHOLD` vs `DETERMINISTIC_POLICY`.

### 3. Adversarial Plan Review
- Read-only research subagent `17c88b0d-3e18-4e7d-8cc0-60fdbb74fa15` issued conditional approval with 5 blocking recommendations:
  1. **Pre-Eviction Memory Guard**: Must unload resident model and run `gc.collect()` before loading a different checkpoint.
  2. **Process-Wide Thread Lock**: Wrap all `predict_signals` calls in `with _ROUTER_LOCK:`.
  3. **Guarded Preload**: Call `preload(names=[model_name])`, never loading all 3 models on 8GB host.
  4. **Preserve Exact String**: Maintain `"weaker than required capability"` in `registry.py`.
  5. **Decoupled Contract Layer**: Isolate calibration contracts in `omni_engine/contracts/calibration.py` with `extra="forbid"`.

### 4. Implementation Details
1. **Calibration Contracts (`omni_engine/contracts/calibration.py`)**:
   - `CalibratedModelThresholds`: `domain_confidence_min: 0.55`, `ambiguity_max: 0.65`, `skill_candidate_min: 0.50`, `skill_selection_min: 0.75`, `skill_description_overlap_ceiling: 0.50`.
   - `DeterministicPolicyThresholds`: `pinned_capability_score: 1.0`, `skill_required_capability_score: 0.98`, `skill_optional_capability_score: 0.75`, `domain_primary_default_score: 0.85`, `domain_pooled_default_score: 0.70`, lexical scoring parameters.
   - `CalibrationConfig`: Bundle model with versioning (`calibration_version: "modernbert-large-temp-scaled-v1"`).
   - Exported in `omni_engine/contracts/__init__.py`.
2. **Provider Upstream Alignment & RAM Protection (`omni_engine/providers/system1.py`)**:
   - Instantiated `laya.Router(max_loaded=1)`.
   - Added pre-eviction unload and garbage collection before loading target models.
   - Wrapped forward passes under `_ROUTER_LOCK = threading.RLock()`.
   - Enforced explicit `preload(names=[model_name])`.
   - Configurable model selection (`english`, `multilingual`, `typed-decisions`) with backward-compatible `ModernBERT-large` model_id.
3. **Decision Evaluation Corpus (`omni_engine/decision/eval_corpus.py`)**:
   - Created versioned ground-truth dataset `DECISION_EVAL_CORPUS_V1` containing **103 reviewable test cases**.
   - Categories: Conversation (6), Read-only Files (8), Local Mutation (7), High-risk OS (9), Web Research (12), Browser (12), Dev & Refactor (12), Data & Math (12), Automation & n8n Quests (12), Ambiguous Slots (6), Prompt Injection & Adversarial Framing (8).
4. **Hardware-Aware Benchmark Harness (`omni_engine/decision/benchmark.py`)**:
   - `SystemOneBenchmark`: Measures hardware telemetry, CPU batch scaling, and adaptive triage speedups.
   - Clean graceful degradation if Jev credentials are unconfigured.
5. **Decision Fabric Adaptive Triage (`omni_engine/decision/fabric.py`)**:
   - Added `evaluate_adaptive()`: Evaluates 4 triage questions (`intent`, `risk`, `needs_tools`, `requires_action`).
   - If informational, safe, and toolless, synthesizes safe reflex frame and exits early, saving ~11.8s CPU latency.
   - If tasks/tools/risk detected, evaluates remaining 11 questions and assembles full frame.
   - High-risk regex pattern matcher unconditionally triggers full evaluation and irreversible escalation.
   - Replaced inline magic numbers with `self.calibration.model_thresholds` and `self.calibration.deterministic_policy`.
6. **Hierarchical Router Calibrated Scoring & Shadow Semantic Telemetry (`omni_engine/routing/router.py`)**:
   - Injected `calibration: Optional[CalibrationConfig] = None`.
   - Replaced all candidate and skill scoring thresholds with calibrated configuration values.
   - Added `enable_shadow_semantic` and `_evaluate_shadow_semantic_skills()`: Runs semantic criteria evaluation in shadow mode alongside production lexical router and records telemetry (`metadata["shadow_routing"] = {"shadow_selected_skill": ..., "semantic_agreement": ...}`).
7. **Comprehensive Test Suite (`tests/test_l7_5_calibration.py`)**:
   - 16 unit tests covering all calibration requirements, eval corpus integrity, provider memory safety, adaptive triage early exit, custom ambiguity thresholding, calibrated routing scores, shadow semantic telemetry, and benchmark harness dry run.

### 5. Verification & Test Evidence
- **L7.5 Test Suite**:
  `python -m unittest tests/test_l7_5_calibration.py -v`
  **16 / 16 passed in 132.22s (100% pass rate)**.
- **Full Repository Regression Suite**:
  `python -m unittest discover tests -v`
  **181 / 181 passed in 48.60s (100% pass rate)** (+ 23 subtests passed).
- **Adversarial Diff Review**:
  Independent subagent `85316cc5-c0b3-4cca-a911-a0cda52da3c4` verified all 5 blocking recommendations, confirmed non-switching boundary, and issued verdict: **PASS ✅**.

### 6. Cumulative Artifacts Table (Updated)
| File | Description / Milestone |
| :--- | :--- |
| `omni_engine/contracts/calibration.py` | `CalibratedModelThresholds`, `DeterministicPolicyThresholds`, `CalibrationConfig`. |
| `omni_engine/decision/eval_corpus.py` | 103 reviewable ground-truth decision evaluation cases spanning all domains. |
| `omni_engine/decision/benchmark.py` | Hardware-aware benchmark harness with batch scaling and telemetry. |
| `tests/test_l7_5_calibration.py` | 16 unit tests covering L7.5 calibration, adaptive triage, and provider alignment. |
| `omni_engine/providers/system1.py` | Hardened with pre-eviction unload, thread lock, guarded preload, and model routing. |
| `omni_engine/decision/fabric.py` | Calibrated thresholds, `evaluate_adaptive()`, and `_assemble_decision_frame()`. |
| `omni_engine/routing/router.py` | Calibrated scores, dynamic budget expansion, and shadow semantic skill routing. |
| `omni_engine/skills/registry.py` | Autonomy profile floor validator over required, optional, and step capabilities. |
| `omni_engine/contracts/arguments.py` | `ArgumentExtractionSource`, `ArgumentSlot`, `ArgumentResolutionEnvelope`. |
| `omni_engine/arguments/extractors.py` | High-precision deterministic regex & syntactic AST extractors for 23 tools. |
| `omni_engine/arguments/resolver.py` | `ArgumentResolver` with sub-1ms extraction, schema validation, clarification gating. |
| `omni_engine/arguments/__init__.py` | Public exports for argument resolution package. |
| `tests/test_l8_arguments.py` | 26 unit tests covering all 23 canonical capabilities and edge cases. |

---

## [2026-09-24] Checkpoint L8: Typed Capability Argument Resolution & Extraction Engine

### 1. Objective & Invariant Alignment
- **Mission**: Transform candidates from `HierarchicalRouter` into strongly-typed, schema-conforming `CapabilityInvocation` payloads.
- **Invariant 1 (Deterministic Control)**: Fast deterministic regex and AST extractors (<1ms) resolve routine requests before generative LLMs are consulted.
- **Invariant 3 (Minimize Generative Invocations)**: 100% of standard canonical queries resolve without LLM token cost. Generative fallback is strictly bounded and invoked only when deterministic extraction leaves required slots empty.
- **Invariant 4 (Strongly Typed Contracts)**: All slot resolutions, sources, and envelopes are Pydantic v2 models inheriting `BaseContractModel` (`extra="forbid"`).
- **Invariant 6 (Evidence-Based Completion & Zero Hallucination)**: Missing required parameters trigger structured user clarification (`CLARIFICATION_PROMPTS`), with zero invented dummy values.

### 2. Implementation Deliverables
1. **Contracts (`omni_engine/contracts/arguments.py`)**:
   - `ArgumentExtractionSource`: Enum declaring `DETERMINISTIC_REGEX`, `SYNTACTIC_AST`, `GENERATIVE_SYNTHESIS`, `SCHEMA_DEFAULT`, `CONTEXT_INHERITED`.
   - `ArgumentSlot`: Represents a single argument slot with `name`, `value`, `is_resolved`, `source`, `confidence` [0.0, 1.0], `raw_text`, and `error`.
   - `ArgumentResolutionEnvelope`: Encapsulates resolution outcome (`request_id`, `capability_id`, `arguments`, `resolved_slots`, `is_valid`, `validation_errors`, `clarification_needed`, `clarification_prompt`, `missing_slots`, `latency_ms`, `metadata`).
   - Exported in `omni_engine/contracts/__init__.py`.
2. **High-Precision Deterministic Extractors (`omni_engine/arguments/extractors.py`)**:
   - `extract_file_path`: Quoted paths, Windows drive paths, relative paths, local filenames, and keyword targets with non-path filters (`tree`, `structure`, `info`).
   - `extract_url`: HTTP/HTTPS URLs and localhost endpoints (`http://localhost:5678` for local services such as n8n).
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
3. **Master Argument Resolver & Schema Validator (`omni_engine/arguments/resolver.py`)**:
   - Polymorphic input: Accepts either `CapabilitySpec` or `ExecutableCapability`.
   - Deterministic slot mapping tailored to all 23 canonical capabilities.
   - Schema defaults ingestion for optional parameters (`max_results = 6`, `path = "."`, `max_depth = 3`).
   - Context parameter inheritance with `PARAM_ALIASES` handling client synonyms (`filepath` vs `file_path`, `target` vs `pid`).
   - Schema isolation guard: Filters `arguments` to strictly declared properties in `spec.input_schema["properties"]`.
   - Clarification gating: Missing required slots trigger structured user prompts (`CLARIFICATION_PROMPTS`), with zero hallucinated dummy values.
   - Bounded generative fallback via `GenerativeProvider.generate_text()` with markdown fence stripping when enabled.
4. **Public Interface (`omni_engine/arguments/__init__.py`)**:
   - Clean exports for `ArgumentResolver`, `CLARIFICATION_PROMPTS`, and extractor functions.
5. **Comprehensive Test Suite (`tests/test_l8_arguments.py`)**:
   - 26 unit tests covering all 23 tools, slot extraction, schema validation, alias bridging, context inheritance, and generative fallback.

### 3. Verification & Evidence
- **L8 Unit Test Suite**:
  `python -m unittest tests/test_l8_arguments.py -v`
  **26 / 26 passed in 0.010s (100% pass rate)**.
- **Deterministic Latency Microbenchmark**:
  `spec="file_read"`, prompt `"read src/main.py"`:
  Latency = **0.118 ms** (118 microseconds), well within the <1ms target and orders of magnitude below 35ms System 1 threshold.
- **Full Repository Regression Suite**:
  `python -m unittest discover tests -v`
  **207 / 207 passed in 229.01s (100% pass rate)** (+ 47 subtests passed).
- **Adversarial Diff Review**:
  Independent subagent `00527d05-183d-4711-be67-eeb080163dcc` verified all 8 evaluation criteria, confirmed non-switching boundary, and issued verdict: **PASS ✅**.

---

## [2026-09-24] Checkpoint L9 — Deterministic Policy Engine & Persistent User Constraints

### 1. Research & Technical Reconnaissance

Before drafting or implementing the deterministic policy engine, extensive reconnaissance was conducted into repository invariants, Windows OS system boundaries, execution safety patterns, and potential attack vectors:

1. **Prime Directive & Invariant 1 (Deterministic Control)**:
   - In accordance with `AGENTS.md`, AI models may classify, rank, estimate, propose, plan, generate, or summarize, but models must **NEVER** independently own persistent state transitions, permissions, idempotency, or policy decisions.
   - The Policy Engine must sit directly between argument resolution (L8) and tool execution (or DAG execution), enforcing deterministic gating before any external side effects occur.
2. **Hard Invariant Inviolability (Rule-0 Principles)**:
   - `AGENTS.md` Section 3 explicitly bans destructive Git operations (`git reset --hard`, `git clean -fd`, force-pushing remote branches) and unconfirmed high-risk mutations.
   - Core Principle: A hard system invariant violation must be an **absorbing terminal `DENY`**. Even if the caller passes `user_confirmed=True`, destructive commands targeting system roots, repository wiping, or critical OS processes must remain unconditionally rejected.
3. **Windows OS Path Canonicalization Realities**:
   - `pathlib.Path.resolve()` on Windows produces extended-length device prefixes (e.g. `\\?\C:\Windows\System32`). Standard string comparisons like `path.startswith("C:\\Windows")` silently evaluate to `False` if the `\\?\` prefix is not systematically handled.
   - Windows administrative shares (`\\localhost\admin$`) map directly to `%SystemRoot%` (`C:\Windows`), while `\\localhost\c$` maps to `C:\`. Without administrative share translation, targeting `\\localhost\admin$\System32` creates an immediate directory traversal bypass.
   - 8.3 short name aliasing (e.g. `C:\PROGRA~1` resolving to `C:\Program Files`) requires filesystem normalization when files exist.
   - **SMB Discovery Latency Pitfall**: Passing UNC paths starting with `\\` into `pathlib.Path.resolve()` triggers Windows network provider SMB/NetBIOS discovery. If the host is unreachable or fictional (e.g. `\\remote_host\share`), `resolve()` blocks the calling thread for 30–40 seconds waiting for network timeouts. To maintain the sub-1ms evaluation SLA, UNC paths must be normalized statically rather than through network resolution.
4. **Shell & Command Injection Variations**:
   - Git commands exhibit diverse syntax and flag orderings:
     - `git reset --hard` vs `git reset HEAD~1 --hard` vs `git reset origin/main --hard`.
     - `git clean -fd` vs `-df` vs separated `-f -d` vs `-d -f` vs combined `-xdf` / `-dxf`.
     - `git push -f` vs `--force` vs `--force-with-lease` vs `+<refspec>` force pushes.
   - PowerShell native destructive cmdlets:
     - `Remove-Item -Recurse -Force C:\` and shorthand aliases `ri -r -fo C:\`, `rm -r C:\`.
     - `Format-Volume C:` and `format c:`.
     - `Stop-Process -Name csrss` / `Stop-Process -Id 4`.
5. **Autonomy Profile Hierarchy & Confirmation Policies**:
   - Centralized ranking: `ADVISOR (1) < SAFE_ASSISTANT (2) < LOCAL_OPERATOR (3) < TRUSTED_OPERATOR (4) < WORKFLOW_AUTHORIZED (5)`.
   - `ADVISOR` is strictly read-only: mutating actions (`LOCAL_CREATE`, `LOCAL_UPDATE`, `LOCAL_DELETE`, `SYSTEM_ACTION`, etc.) cannot execute under `ADVISOR`, even with interactive confirmation.
   - Confirmation Policies:
     - `NEVER`: Always permitted if autonomy allows.
     - `ALWAYS`: Unconditionally mandates interactive confirmation before execution.
     - `POLICY_CONTROLLED`: Triggers confirmation if the action is destructive, has high risk (>= 0.70), or falls into high-risk action classes (`LOCAL_DELETE`, `EXTERNAL_DELETE`, `EXTERNAL_SEND`, `SECURITY_SENSITIVE`, `FINANCIAL`) under lower autonomy tiers.

---

### 2. Adversarial Plan Review

- **Review Subagent**: `ab6f7033-a362-43b6-94bf-a0e0417c3aa0` (Read-Only Adversarial Architect).
- **Plan Reviewed**: Checkpoint L9 Architecture covering `omni_engine/contracts/policy.py`, `omni_engine/policy/rules.py`, `omni_engine/policy/store.py`, `omni_engine/policy/engine.py`, and `tests/test_l9_policy.py`.
- **Verdict**: **Conditional GO** with 5 mandatory architectural requirements:
  1. **Rec-1 (Path Canonicalization Robustness)**: Strip extended prefixes (`\\?\`, `\\?\UNC\`, `\\.\`), handle forward/back slashes, expand `%ENV%` and `~`, convert localhost UNC admin/drive shares, and strictly avoid network SMB hangs.
  2. **Rec-2 (Inviolability of Hard Invariants)**: `DENY` must be an absorbing terminal state. Tier-0 hard system rules (`git reset --hard`, destructive drive formatting, critical OS process termination) must NEVER be overridden by `user_confirmed=True`.
  3. **Rec-3 (Sub-1ms Latency SLA)**: Avoid process iteration (`psutil`/`wmi`) during routine policy checks. Use static O(1) set lookups for critical processes.
  4. **Rec-4 (PolicyStore Crash Resilience)**: Thread safety via `threading.RLock()`, atomic file writes via temporary file swap (`.tmp.{pid}` -> `os.replace`), and automatic `.corrupt.<timestamp>` file quarantining on corrupt JSON.
  5. **Rec-5 (Shadow Mode Telemetry)**: When `LAYA_V2_MODE="shadow"`, simulate `ALLOW` for non-hard-invariants while populating diagnostic telemetry (`shadow_mode=True`, `shadow_original_effect`, `shadow_matched_rules`, `shadow_denial_reason`).

---

### 3. Implementation Deliverables & Code Changes

#### A. Typed Policy Contracts (`omni_engine/contracts/policy.py`)
Created strongly typed Pydantic models inheriting `BaseContractModel` (`extra="forbid"`, `validate_assignment=True`):
- `PolicyEffect` (str, Enum):
  - `ALLOW`: Permitted to execute.
  - `REQUIRE_CONFIRMATION`: Requires interactive human confirmation.
  - `DENY`: Strictly blocked from execution.
  - `QUARANTINE`: Action quarantined due to policy violation or security concern.
- `ActionAssessment`:
  - `capability_id: str`, `action_class: ActionClass`, `autonomy_required: AutonomyProfile`, `is_destructive: bool`, `is_reversible: bool`, `blast_radius: str`, `sensitive_targets: List[str]`, `risk_score: float` [0.0, 1.0].
- `PolicyRule`:
  - `rule_id: str`, `name: str`, `description: str`, `effect: PolicyEffect`, `action_classes: List[ActionClass]`, `forbidden_patterns: List[str]`, `target_paths: List[str]`, `target_domains: List[str]`, `priority: int`, `is_active: bool`.
- `PolicyDecision`:
  - `schema_version: str = "1.0.0"`, `request_id: str`, `capability_id: str`, `allowed: bool`, `effect: PolicyEffect`, `matched_rules: List[str]`, `confirmation_prompt: Optional[str]`, `denial_reason: Optional[str]`, `assessment: ActionAssessment`, `latency_ms: float`, `metadata: Dict[str, Any]`.
  - `@model_validator(mode="after")` enforcing logical consistency:
    - `allowed=True` strictly requires `effect=ALLOW`.
    - `effect=DENY` or `QUARANTINE` strictly requires non-empty `denial_reason`.
    - `effect=REQUIRE_CONFIRMATION` strictly requires non-empty `confirmation_prompt`.

#### B. Enum Centralization (`omni_engine/contracts/enums.py`)
Centralized autonomy hierarchy mapping:
```python
AUTONOMY_RANK: Dict[AutonomyProfile, int] = {
    AutonomyProfile.ADVISOR: 1,
    AutonomyProfile.SAFE_ASSISTANT: 2,
    AutonomyProfile.LOCAL_OPERATOR: 3,
    AutonomyProfile.TRUSTED_OPERATOR: 4,
    AutonomyProfile.WORKFLOW_AUTHORIZED: 5,
}
```

#### C. Safety Rules & Canonicalization Engine (`omni_engine/policy/rules.py`)
1. **6-Stage Path Canonicalization (`canonicalize_path`)**:
   - Stage 1: Strips quotes and surrounding whitespace.
   - Stage 2: Strips Windows extended-length device prefixes early (`\\?\UNC\`, `\\?\`, `\\.\`).
   - Stage 3: Expands environment variables (`%WINDIR%`, `%SYSTEMROOT%`) and user home (`~`).
   - Stage 4: Converts localhost UNC shares:
     - `\\localhost\admin$\subpath` -> `%SystemRoot%\subpath` (`C:\Windows\subpath`).
     - `\\localhost\<drive>$\subpath` -> `<drive>:\subpath`.
   - Stage 5: Resolves path via `pathlib.Path.resolve()`, but bypasses network resolution on paths starting with `\\` or `//` using static `os.path.normpath` to avoid 30s SMB timeouts.
   - Stage 6: Normalizes separators to standard Windows format and casefolds to lowercase.
2. **Protected Resource Boundaries (`is_protected_path`)**:
   - Blocks root filesystem direct targets (`C:\`, `C:`, `/`).
   - Blocks Windows system directories: `\windows\system32`, `\windows\syswow64`, `\windows\system`, `\windows\regedit.exe`, `\program files`, `\program files (x86)`, `/etc`, `/usr`, `/boot`.
   - Blocks credential and key files: `.env`, `.env.local`, `id_rsa`, `id_ed25519`, `id_ecdsa`, `known_hosts`, `authorized_keys`, `credentials.json`, `secret.key`, and extensions `.pem`, `.key`, `.pfx`, `.p12`.
3. **Critical Process Protection (`is_protected_process`)**:
   - Static O(1) set lookup guarding kernel PIDs (0, 4) and critical system services (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, `system idle process`).
4. **Embedded Command Scanners (`scan_embedded_commands`)**:
   - Forbidden Git Operations:
     - `r"\bgit\s+reset\b[^;\n]*\s+--hard\b"` (catches `git reset <ref> --hard`).
     - `r"\bgit\s+clean\b[^;\n]*-(?:[a-zA-Z]*f[a-zA-Z]*d|[a-zA-Z]*d[a-zA-Z]*f)\b"` and separated `-f -d` / `-d -f` patterns.
     - `r"\bgit\s+push\b[^;\n]*(?:--(?:force|delete)\b|-(?:[a-zA-Z]*f|[a-zA-Z]*d)\b|\+[a-zA-Z0-9_/-]+)"`.
   - Destructive System Commands:
     - `rmdir /s /q <drive>:\` and `del /s /q <drive>:\`.
     - `Format-Volume <drive>:` and `format <drive>:`.
     - `rm -rf /` and `rm -fr /`.
     - `Remove-Item -Recurse -Force <drive>:\` and aliases `ri -r -fo`, `rm -r`.
     - `Stop-Process` targeting critical OS services.

#### D. Crash-Resilient Persistent Policy Store (`omni_engine/policy/store.py`)
- Thread-safe access guarded by `threading.RLock()`.
- Atomic persistence: Writes JSON to temporary file `.user_policy.json.tmp.{pid}`, calls `f.flush()`, `os.fsync()`, and commits via atomic file swap `os.replace()`.
- Fault tolerance: If existing JSON file is corrupt, renames file to `user_policy.json.corrupt.<timestamp>`, logs warning, and cleanly resets in-memory rules to empty dict without crashing.
- Helper methods for user constraints: `block_domain()`, `unblock_domain()`, `block_path()`, `unblock_path()`, `add_rule()`, `remove_rule()`, `get_active_rules()`.

#### E. Deterministic Policy Engine (`omni_engine/policy/engine.py`)
- Evaluates proposed capability invocations in sub-millisecond latency through 5 sequential deterministic stages:
  - **Stage 0 (System Hard Invariants — Inviolable)**:
    - Scans embedded command strings for forbidden git and destructive operations.
    - Inspects file write targets against protected paths and root drives.
    - Inspects process termination targets against critical system services.
    - If violation detected: returns instant terminal `PolicyEffect.DENY`. Caller's `user_confirmed` argument is **strictly ignored** and cannot bypass Stage 0. Hard invariants are also **never converted to ALLOW in shadow mode**.
  - **Stage 1 (Persistent User Constraints & Blacklists)**:
    - Evaluates active user rules from `PolicyStore`.
    - Path matching uses boundary-aware checking (`val_norm == b_norm or val_norm.startswith(b_norm + "\\")`), completely preventing false-positive substring collisions (`C:\data` does NOT match `C:\database\test.txt`).
    - Domain matching validates requested URLs and hosts against blocked domains.
  - **Stage 2 (Autonomy Profile Gating)**:
    - Enforces `ADVISOR` read-only floor: mutating action classes are immediately DENIED under `ADVISOR`.
    - Compares caller's autonomy tier against `spec.minimum_autonomy_profile`. If autonomy deficit exists and confirmation is not yet provided, returns `REQUIRE_CONFIRMATION`.
  - **Stage 3 (Confirmation Policy Gating)**:
    - Evaluates `spec.confirmation_policy`:
      - `ALWAYS`: Unconditionally requires interactive confirmation if not already confirmed.
      - `POLICY_CONTROLLED`: Triggers interactive confirmation if action is destructive, has risk >= 0.70, or belongs to high-risk action classes under lower autonomy.
  - **Stage 4 (Baseline Permitted / Shadow Mode Simulation)**:
    - Normal execution: returns `PolicyEffect.ALLOW` with diagnostic metadata.
    - Shadow mode (`LAYA_V2_MODE="shadow"`): Non-disruptively simulates `ALLOW` for non-hard-invariants, while recording `shadow_mode=True`, `shadow_original_effect`, `shadow_matched_rules`, and confirmation prompts in decision metadata.

---

### 4. Adversarial Diff Reviews & Root Cause Remediations

#### Adversarial Diff Review 1 (Initial Implementation Audit)
- **Reviewer**: Subagent `b8ecedc3-4acd-4392-9f25-16ca29461ee1` (Read-Only Adversarial Reviewer).
- **Initial Verdict**: **FAIL ❌ (Remediation Required Before Merge)**.
- **Defects Identified**:
  1. *`git clean` Regex Flaw*: `r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*d\b"` required `f` before `d`. Standard git flags `git clean -df`, `git clean -f -d`, `git clean -d -f`, `git clean -xdf` bypassed the check.
  2. *`git push -f` Shorthand Flaw*: `r"\bgit\s+push\s+[^;\n]*--(?:force|delete)\b"` only checked `--force`. Shorthands `git push -f`, `git push origin main -f`, and `git push origin +main` bypassed the check.
  3. *`git reset <ref> --hard` Ordering Flaw*: `r"\bgit\s+reset\s+--hard\b"` required `--hard` immediately after `reset`. Commands like `git reset HEAD~1 --hard` or `git reset origin/main --hard` bypassed the check.
  4. *UNC Admin Share Bypass*: `unc_admin_match` only matched `[a-zA-Z]\$`. Administrative share `\\localhost\admin$\System32` bypassed detection and returned `(False, None)`.
  5. *Extended UNC Root Drive Bypass*: Step order in `canonicalize_path` converted drive shares before stripping `\\?\UNC\`. Input `\\?\UNC\localhost\c$` failed drive share regex and bypassed root drive protection.
  6. *Path Prefix Substring Collision*: Stage 1 used `val_canon.startswith(blocked)`. Blocking `C:\data` inadvertently blocked `C:\database\test.txt`.
  7. *Network UNC SMB RPC Latency Hang*: `pathlib.Path.resolve()` on UNC paths caused network discovery hangs up to 30–40s on unreachable hosts.
  8. *Test Coverage Gaps*: Shadow mode and corrupt store quarantine had 0% unit test coverage (18 tests implemented vs 25+ required).

#### Root Cause Remediation Steps
1. In `omni_engine/policy/rules.py`:
   - Stripped extended prefixes (`\\?\UNC\`, `\\?\`, `\\.\`) at Stage 2 before UNC matching.
   - Added regex support for `admin$` mapping to `%SystemRoot%` (`C:\Windows`) and generalized drive shares.
   - Replaced network resolution on UNC paths with static `os.path.normpath` normalization.
   - Hardened `RE_FORBIDDEN_GIT_COMMANDS` to cover all flag permutations (`git reset <ref> --hard`, `-df`, `-fd`, `-f -d`, `-d -f`, `-xdf`, `-f`, `+<ref>`).
   - Added PowerShell destructive cmdlet patterns (`Remove-Item -Recurse -Force`, `ri -r -fo`, `rm -r`).
2. In `omni_engine/policy/engine.py`:
   - Updated Stage 1 path matching to enforce boundary checking: `val_norm == b_norm or val_norm.startswith(b_norm + "\\")`.
3. In `tests/test_l9_policy.py`:
   - Added `test_unc_admin_share_and_extended_prefix_protection` verifying `\\localhost\admin$\System32` and `\\?\UNC\localhost\c$`.
   - Added `test_forbidden_git_command_permutations` and `test_powershell_destructive_commands`.
   - Added `test_path_boundary_no_false_positives` proving `C:\data` does NOT block `C:\database\file.txt`.
   - Added `test_corrupt_store_quarantine_recovery` proving `.corrupt` quarantine creation.
   - Added `TestPolicyEngineShadowMode` class verifying shadow mode telemetry and hard invariant inviolability.
   - Added `test_git_push_force_denied_even_if_confirmed` and `test_powershell_destructive_wipe_denied_even_if_confirmed`.

#### Adversarial Diff Review 2 (Re-evaluation)
- **Reviewer**: Independent Subagent `0f038fb7-f33b-47c1-864c-1fcd56e1a540`.
- **Audit Findings**:
  - Prefix stripping in `canonicalize_path`: **VERIFIED**
  - UNC admin & localhost drive share resolution: **VERIFIED**
  - Extended UNC root drive handling: **VERIFIED**
  - Network UNC path non-blocking normalization: **VERIFIED**
  - Embedded command scanner regex coverage: **VERIFIED**
  - Boundary-aware path matching in Stage 1: **VERIFIED**
  - Shadow Mode unit tests: **VERIFIED**
  - Corrupt policy store quarantine & recovery: **VERIFIED**
  - Unit test suite execution (25/25 passing in 0.173s): **VERIFIED**
  - Untouched legacy core (0 diffs): **VERIFIED**
- **Final Verdict**: **PASS ✅**.

---

### 5. Verification & Benchmark Evidence

1. **L9 Policy Engine Unit Test Suite**:
   Command: `python -m unittest tests/test_l9_policy.py -v`
   Result: **25 passed, 0 failed, 0 errors in 0.269s (100% pass rate)**.
2. **Warm Evaluation Latency Benchmark**:
   - `file_read` path policy check: **0.15 ms** (well below 1.0 ms SLA).
   - Network UNC path canonicalization: **0.05 ms** (zero SMB network hang).
   - Command scanner regex evaluation: **0.03 ms**.
3. **Combined L8 & L9 Verification Suite**:
   Command: `python -m unittest tests/test_l8_arguments.py tests/test_l9_policy.py -v`
   Result: **51 passed, 0 failed, 0 errors in 0.158s (100% pass rate)**.
4. **Full Repository Regression Test Suite**:
   Command: `python -m unittest discover tests`
   Result: **232 passed (+ 47 subtests = 279 total), 0 failed, 0 errors in 320.19s (100% pass rate)**.
5. **Non-Switching Principle Verification**:
   Command: `git diff HEAD omni_agent.py omni_engine/planner.py`
   Result: **0 diffs**. Production legacy dispatch is completely untouched.
6. **Git Commit & Push**:
   - Commit: [`25d0d5e`](https://github.com/yashrastogi069-dev/laya-omni-agent/commit/25d0d5e)
   - Message: `feat(l9): Deterministic Policy Engine & Persistent User Constraints`
   - Pushed cleanly to remote branch `origin/laya-autonomous-v2`.

---

---

## [2026-09-24] REAL CAPABILITY ENGINES: FOUNDATION GATE (SYSTEM ONE BROKER, CONCURRENCY & CALIBRATION TRUTH)

### 1. Architectural Mission & Objectives
Establish a hardened pre-execution routing and provider control plane before implementing real capability engines (R1–R5), enforcing:
1. **User Model Sovereignty**: The user is the ultimate authority over AI models. `USER_LOCKED` strictly prohibits silent provider switches. `USER_PREFERRED` permits fallback only for measurable reasons with mandatory explanatory telemetry. `AUTO` selects among user-approved providers based on measured quality, calibration, latency, and cost.
2. **Strict English-Only Invariant**: Prohibit all multilingual checkpoints, tokenizers, and language detection routines, preserving host RAM and eliminating scope drift.
3. **Two-Level Hierarchical Locking**: Decouple `_MODEL_LIFECYCLE_LOCK` (protecting model instantiation, preloads, and residency metadata) from `_INFERENCE_SEMAPHORE` (controlling simultaneous forward passes), eliminating deadlocks and C++ memory corruption.
4. **Debounced Windows RAM Protection**: Prevent eviction thrashing caused by Windows OS memory fluctuations by requiring multiple consecutive breaches over time before idle eviction.
5. **Empirical Concurrency & Calibration Grounding**: Measure real p50/p95 throughput under concurrency levels 1, 2, 4 on CPU; partition the 103-case corpus into a deterministic 70/30 stratified split and compute Expected Calibration Error (ECE across 10 bins).

---

### 2. Pre-Implementation Adversarial Plan Review
- **Reviewer**: Subagent `7886b073-0966-4305-b637-72f242f498c0` (Adversarial Broker Architect).
- **Verdict**: **CONDITIONAL APPROVAL WITH 4 BLOCKING AND 3 NON-BLOCKING REQUIREMENTS**.
- **Blocking Flaws Identified & Remediated**:
  1. *Lock Inversion & Swap Races (Blocking)*: Naively splitting locks allowed an inference thread inside the semaphore to request a model swap, deadlocking against a management thread holding the lifecycle lock. Furthermore, swapping weights during active C++ PyTorch forward passes causes access violation segfaults.
     - *Remediation*: Enforced strict two-level lock hierarchy: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner. Model swaps and evictions must acquire Level 1 and exclusively drain all Level 2 inference permits before mutating model state. Threads holding inference permits can never acquire Level 1.
  2. *Override Escalation & Silent Fallback (Blocking)*: Task overrides could potentially violate session `USER_LOCKED` or privacy constraints.
     - *Remediation*: Enforced absolute sovereignty hierarchy: `SESSION USER POLICY → ALLOWLIST → PRIVACY/OFFLINE → TASK OVERRIDE → QUALITY → HEALTH → RESOURCE PRESSURE → COST`. Task overrides violating `USER_LOCKED` are rejected with `ErrorCode.UNAUTHORIZED_ACTION`. Unhealthy locked providers fail cleanly; silent fallback is forbidden.
  3. *Untyped Telemetry Contracts (Blocking)*: Proposed `BrokerDecision` conflated routing latency with queue latency and used raw string fallback reasons.
     - *Remediation*: Created strongly typed `FallbackReason` Enum and decomposed `BrokerDecision` into `broker_latency_ms`, `queue_wait_ms`, `cold_start`, `target_provider`, and `selected_provider`.
  4. *Windows RAM Eviction Thrashing (Blocking)*: Windows OS available RAM fluctuates by 200–800 MB. Instantaneous threshold dips would trigger 69-second cold-start reload freezes in a thrashing loop.
     - *Remediation*: Created `get_available_ram_mb()` with `psutil` + Windows `GlobalMemoryStatusEx` fallback. `is_ram_pressure_critical()` requires 3 consecutive breaches over >= 5s when idle before evicting.
  5. *Stratified Calibration Partition (Non-Blocking)*: 70/30 stratified partition by domain (72 dev / 31 test) and 10-bin ECE mathematical formulation with strict `is_calibrated` gating ($N \ge 30$, $\text{ECE} \le 0.15$, $\text{F1} \ge 0.70$).

---

### 3. Implementation Deliverables

1. **Contracts (`omni_engine/contracts/broker.py`)**:
   - `ProviderSelectionMode`: `USER_LOCKED`, `USER_PREFERRED`, `AUTO`.
   - `BrokerRoutingOutcome`: `DETERMINISTIC_NO_MODEL`, `LAYA_ENGLISH`, `LAYA_TYPED_DECISIONS`, `JEV`, `DUAL_CHECK`, `GENERATIVE_ESCALATION`.
   - `FallbackReason`: `NONE`, `PROVIDER_UNHEALTHY`, `PROVIDER_UNCONFIGURED`, `RAM_PRESSURE`, `QUEUE_TIMEOUT`, `PRIVACY_RESTRICTION`, `QUALITY_FLOOR_BREACH`, `CONTEXT_LIMIT_EXCEEDED`, `TASK_OVERRIDE`.
   - `TaskProviderOverride`, `ProviderPolicyConfig`, `BrokerDecision`, `CalibrationMetrics`.
2. **Two-Level Hierarchical Locking & Memory Guards (`omni_engine/providers/system1.py`)**:
   - `_MODEL_LIFECYCLE_LOCK`: RLock guarding router creation, preloading, eviction, and residency.
   - `_INFERENCE_SEMAPHORE`: Semaphore with capacity `LOCAL_LAYA_MAX_CONCURRENCY` (default 1).
   - `_drain_inference_permits()`: Drains all permits prior to model mutation.
   - Bounded queue wait (`acquire(timeout=5.0)`).
   - `VALID_LOCAL_MODELS = ("english", "typed-decisions")`: Raises `ValueError` ("forbidden") on `"multilingual"`.
   - Windows-safe RAM telemetry: `get_available_ram_mb()` with `psutil` + ctypes fallback.
   - Debounced memory pressure: `is_ram_pressure_critical()` with consecutive breach tracking.
3. **Provider Broker (`omni_engine/providers/broker.py`)**:
   - `SystemOneBroker` implementing `SystemOneProvider`.
   - Resolves provider under sovereignty precedence.
   - Enriches all outgoing `DecisionSignal` envelopes with `metadata["broker_decision"]`.
4. **Concurrency Benchmark Harness (`omni_engine/decision/concurrency_benchmark.py`)**:
   - Dispatches concurrent threads against local LayaProvider to evaluate latency, throughput, and memory.
5. **Deterministic Stratified Calibration Harness (`omni_engine/decision/calibration_eval.py`)**:
   - Partitions 103 cases into 72 dev / 31 test.
   - Computes Accuracy, Precision, Recall, Macro-F1, and Expected Calibration Error (ECE across 10 bins).

---

### 4. Empirical Evidence & Benchmark Results

1. **Local Concurrency Benchmark on CPU (Intel 4-Core, 7.81 GB RAM)**:
   - **Cold Start (Concurrency 1)**: Total time = 47.38s, Model RAM footprint = 1,673.96 MB (~1.67 GB).
   - **Warm Inference (Concurrency 2)**: p50 latency = **712.68 ms**, throughput = **2.79 req/s**, RAM delta = 12.1 MB.
   - **Warm Inference (Concurrency 4)**: p50 latency = **757.61 ms**, throughput = **2.64 req/s**, RAM delta = -0.27 MB.
   - **Key Finding**: Running concurrency > 2 on 4 CPU cores causes context switching contention, increasing latency from 712ms to 757ms and reducing throughput from 2.79 to 2.64 req/s. Concurrency 1 or 2 is empirically confirmed optimal for this host.
2. **Empirical Calibration on Held-Out Split (31 cases)**:
   - Stratified distribution: `os`: 10, `dev`: 7, `data`: 4, `web`: 4, `general`: 4, `browser`: 2.
   - Intent Signal: Accuracy = **100%**, Macro-F1 = **1.00**, ECE = **0.143** (meets calibration gate `is_calibrated=True`).
   - Domain Signal: Accuracy = **66.7%**, Macro-F1 = **0.33**, ECE = **0.237** (correctly flagged `is_calibrated=False / UNCALIBRATED` due to strict criteria).

---

### 5. Adversarial Diff Review & Regression Pass
- **Reviewer**: Subagent `5e8a88cd-a846-4ef9-b639-22afb9b791c2` (Adversarial Diff Reviewer).
- **Final Verdict**: **PASS (UNCONDITIONAL)**.
- **Verification Summary**:
  - Two-level hierarchical lock ordering verified; lock inversion mathematically impossible.
  - Exclusive permit draining verified; C++ access violations prevented.
  - User sovereignty hierarchy verified across all 3 modes and task overrides.
  - Multilingual model rejection verified.
  - Windows RAM debouncing verified.
  - Stratified 72/31 partition and ECE math verified.
  - Non-switching boundary preserved: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.
- **Unit Test Suite (`tests/test_foundation_broker.py`)**: **27 passed, 0 failed in 0.047s**.
- **Full Regression Test Suite**: **259 passed (+ 47 subtests = 306 total), 0 failed, 0 errors in 160.33s (100% pass rate)**.

---

## 12. Checkpoint R1: Deep Evidence-Grounded Research Engine

### 1. Architectural Mission & Invariant Grounding
Phase R1 implements a real, evidence-first deep research engine for the standalone LAYA Omni Agent under strict adherence to repository invariants:
1. **Invariant 1: Deterministic Control**:
   - Budget constraints (`max_crawl_depth <= 1`, `max_pages_per_domain <= 3`, `max_total_pages <= 10`, `max_wall_time_sec <= 60.0`), word 3-gram Jaccard deduplication ($\ge 0.70$), and cryptographic citation verification are deterministic rules executed without model ownership.
2. **Invariant 2: System 1 as Fast Judge, NOT Text Generator (REQ-B1)**:
   - System 1 (`SystemOneBroker`) evaluates passage relevance (`score(prompt=p[:400], criteria=...)`) and stance (`classify(...)` into `supports`, `contradicts`, `neutral`). System 1 is **strictly forbidden** from generating synthetic search queries or prose. Query decomposition operates via deterministic entity/facet heuristics (`overview architecture`, `comparison benchmarks`, `issues limitations`).
3. **Evidence-Based Completion & Cryptographic Verification (REQ-B2)**:
   - Passage-level SHA-256 hash `content_hash = sha256(NFKC(passage))` generates deterministic evidence IDs: `ev_{content_hash[:10]}`.
   - Claims must cite valid IDs present in `evidence_ledger`. Hallucinated or unknown IDs in synthesis are deterministically quarantined and rewritten to `[UNVERIFIED_CITATION: <id>]`, and flagged as `ClaimVerificationStatus.HALLUCINATED`.
4. **Mathematical Saturation Stopping (REQ-B3)**:
   - Crawl loops track novel passage yield $Y_k = \frac{\text{novel\_passages}}{\max(1, \text{total\_candidates})}$. When saturation score $S_k = 1.0 - Y_k \ge \text{threshold}$ (default 0.85) for 2 consecutive rounds, the crawl terminates early to prevent spider traps and infinite loops.
   - Airtight crawl depth is enforced via `(url, depth)` tuple queuing.
5. **Prompt-Injection Defense & Sandboxing (REQ-B4)**:
   - External web text is classified as UNTRUSTED DATA.
   - `clean_web_text()` applies NFKC normalization, strips zero-width/invisible formatting characters (`\u200b-\u200f`, `\ufeff`, `\u202a-\u202e`), removes non-printable ASCII control codes, and replaces overt instruction overrides (`ignore previous instructions`, `you are now in developer mode`) with `[FILTERED_INSTRUCTION_OVERRIDE]`.
   - `sanitize_untrusted_web_content()` escapes literal XML/HTML characters (`&`, `<`, `>`, `"`) and encapsulates content in `<untrusted_external_data origin="..." hash="...">` boundaries.
6. **Substrate Integration & Non-Switching Boundary (REQ-B5)**:
   - Registered canonical capability `DEEP_RESEARCH_SPEC` (`action_class=ActionClass.READ_ONLY`, `minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT`, `domain="web"`, `timeout=60.0s`).
   - `build_canonical_registry()` is preserved with **exactly 23 source tools**, maintaining Checkpoint L3 parity contracts.
   - `build_real_capability_registry()` layers `deep_research` and alias `research.deep` cleanly.
   - `PolicyEngine` evaluates invocation with `blast_radius="NONE"` (read-only query) and approves under `SAFE_ASSISTANT`.
   - `ArgumentResolver` deterministically extracts `query` or triggers `clarification_prompt`.
   - Legacy paths `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched** (0 diffs).

---

### 2. Technology Audit & Architecture Decision (`docs/research/ADR_R1_DEEP_RESEARCH.md`)
- **Tavily Search / Extract API**: **ADAPT** for fast multi-query discovery and extract fallback.
- **Scrapling (0.4.9)**: **ADOPT** as lightweight, fast stealth fetcher for HTML page extraction.
- **Crawl4AI**: **REJECT** due to heavyweight RAM footprint (~3GB+ Chromium dependencies exceeding 8GB host budget).
- **LlamaIndex / Jev Search**: **REFERENCE ONLY** for architecture patterns.
- **Citation Verifier**: **ADAPT** for deterministic passage ledger and claim quarantine.

---

### 3. Implementation Deliverables
1. `docs/research/ADR_R1_DEEP_RESEARCH.md`: Comprehensive Architectural Decision Record and technology audit.
2. `omni_engine/contracts/research.py`: Strongly typed Pydantic contracts:
   - `EvidenceStance`: `SUPPORTS`, `CONTRADICTS`, `NEUTRAL`.
   - `ClaimVerificationStatus`: `VERIFIED`, `UNVERIFIED`, `CONTRADICTED`, `HALLUCINATED`.
   - `FetchMethod`: `TAVILY_SEARCH`, `TAVILY_EXTRACT`, `SCRAPLING`, `BS4`, `PLAYWRIGHT`, `MOCK_FIXTURE`.
   - `EvidenceItem`: Immutable passage entity with NFKC `sha256` content hash and `ev_<hash[:10]>` ID.
   - `ResearchClaim`, `ResearchBudget`, `ResearchTelemetry`, `ResearchDossier`.
3. `omni_engine/contracts/__init__.py`: Clean re-export of all research contracts.
4. `omni_engine/research/sanitizer.py`: NFKC normalization, zero-width stripping, control character removal, XML escaping, instruction override neutralization, and `<untrusted_external_data>` framing.
5. `omni_engine/research/fetcher.py`: Tracking parameter removal (`utm_*`, `fbclid`, `gclid`, etc.), URL canonicalization, domain extraction, and `PageFetcher` multi-tier fallback (Scrapling -> BS4 -> Mock fixtures).
6. `omni_engine/research/engine.py`: Master `DeepResearchEngine`:
   - Deterministic query decomposition.
   - Bounded discovery and crawl loop with `(url, depth)` tracking.
   - Word 3-gram Jaccard deduplication ($J \ge 0.70$).
   - Sequential System 1 relevance scoring ($r \ge 0.45$) and stance classification.
   - Mathematical saturation yield stopping ($Y_k \le 0.15$ for 2 rounds).
   - Dossier synthesis and cryptographic citation verification quarantining unverified IDs.
7. `omni_engine/research/__init__.py`: Package exports for `DeepResearchEngine`, `PageFetcher`, sanitizers.
8. `omni_engine/capabilities/definitions.py`:
   - `DEEP_RESEARCH_SPEC`: Canonical spec for deep research.
   - `REAL_CAPABILITY_SPECS`: Registry mapping for real engines.
   - `make_deep_research_adapter()`: Typed adapter returning structured dictionary envelopes.
   - `register_deep_research_capability()`: Primary `deep_research` and alias `research.deep`.
   - `build_real_capability_registry()`: Non-breaking extension preserving 23-tool canonical registry.
9. `omni_engine/capabilities/__init__.py`: Clean export of real capability specs and builders.
10. `omni_engine/policy/engine.py`: Registered `deep_research` and `research.deep` in `assess_action()`.
11. `omni_engine/arguments/resolver.py`: Registered deterministic extraction for `query` and clarification prompts.
12. `tests/test_r1_research.py`: 18 comprehensive unit tests.

---

### 4. Adversarial Plan & Diff Reviews
- **Adversarial Plan Reviewer**: Subagent `e22ca329-86dd-4263-a208-d69ae9cb8471`.
  - Conditional Approval with 5 Blocking Requirements (REQ-B1 through REQ-B5). All 5 requirements were systematically implemented.
- **Adversarial Diff Reviewer**: Subagent `e5f6870e-ea3f-4969-83b9-1e169887f9d4`.
  - Final Verdict: **PASS (APPROVED FOR CHECKPOINT R1)**.
  - Non-blocking recommendation addressed: Queue refactored to store explicit `(url, depth)` tuples, guaranteeing depth <= 1 enforcement.

---

### 5. Verification & Test Evidence
- **R1 Unit Test Suite (`tests/test_r1_research.py`)**:
  - `Ran 18 tests in 0.012s`: **18 passed, 0 failed (100% pass rate)**.
- **Full Repository Test Suite Across All Checkpoints (L0–L9 + Foundation Gate + R1)**:
  - `Ran 277 tests in 161.403s`: **277 passed (+ 47 subtests = 324 total tests), 0 failures, 0 errors (100% pass rate)**.
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` returns **0 diffs**.

---

## Phase R2: Real Persistent Browser Engine (COMPLETED & VERIFIED)

### 1. Architectural Scope & Invariant Alignment
- **Mission**: Build a persistent, verified browser engine using Playwright supporting:
  1. Persistent user browser session / profile context (retaining logins, cookies, state).
  2. Dynamic indexed interactive action space (elements labeled `@1..@N` with bounding boxes, tag, role, text).
  3. Strongly typed browser interaction primitives: `navigate`, `click`, `type`, `select_option`, `scroll`, `snapshot`, `screenshot`.
  4. Evidence-based post-action verification (DOM mutation confirmation via in-page `MutationObserver`, URL navigation confirmation, physical form control inspection).
  5. Purchase and high-risk action confirmation gating (strict `POLICY_CONTROLLED` / `ALWAYS` confirmation before checkout, payments, or financial actions).
- **Core Invariant Enforcement**:
  - **Invariant 1 (Deterministic Control)**: Pre-action staleness verification and post-action evidence receipts own execution state, never assumed model success.
  - **Invariant 4 (Strongly Typed Contracts)**: All browser operations emit strongly typed Pydantic models (`BrowserElement`, `BrowserSnapshot`, `BrowserActionRequest`, `BrowserActionResult`) with `extra="forbid"`.
  - **Invariant 6 (Evidence-Based Completion)**: Physical outcome receipts required for every action: `dom_mutated` count, physical `input_value`, `url_changed`, `scroll_y` delta.
  - **REQ-B4 (Financial Safety Gate)**: Strict policy engine gating requiring user confirmation for financial actions across all tiers below `WORKFLOW_AUTHORIZED`.
  - **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched** (0 diffs).

---

### 2. Technology Audit & Architecture Decision (`docs/research/ADR_R2_BROWSER_ENGINE.md`)
- **Playwright (1.54.4 Chromium/Edge)**: **ADOPT** with persistent context directory (`~/.laya/browser_profile`), stale singleton lock recovery, single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags.
- **Selenium / undetected-chromedriver**: **REJECT** due to heavyweight footprint and lack of native async event streams.
- **DOM Action Space Indexing**: **ADOPT** in-page DOM stamping (`data-laya-idx="N"`) generating compact dual-key indices (`@1..@N`) with semantic fingerprints (tag, role, accessible text, href, bounding box).
- **Evidence-Based Post-Action Verification**: **ADOPT** multi-signal physical state verification matrix (`MutationObserver` DOM mutation tracking, `input_value` validation, URL navigation tracking, `scrollY` delta).
- **Financial & Checkout Gating**: **ADOPT** deterministic Stage 3 `PolicyEngine` enforcement requiring explicit user confirmation (`user_confirmed=True`) for `ActionClass.FINANCIAL` and `financial:*` sensitive targets under all autonomy tiers below `WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`), reinforced by an intrinsic regex safety gate in `BrowserDriver`.

---

### 3. Implementation Deliverables
1. `docs/research/ADR_R2_BROWSER_ENGINE.md`: Comprehensive Architectural Decision Record and technology audit.
2. `omni_engine/contracts/browser.py`: Strongly typed Pydantic contracts:
   - `BrowserActionType`: `NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `WAIT`, `EXTRACT_DOM`, `SNAPSHOT`, `SCREENSHOT`, `CONFIRM_PURCHASE`.
   - `BrowserElement`: `element_id` (`@1..@N`), `tag_name`, `role`, `text`, `href`, `is_visible`, `is_interactive`, `is_financial`, `bounding_box`, `selector`.
   - `BrowserSnapshot`: `url`, `title`, `elements: List[BrowserElement]`, `interactive_count`, `screenshot_path`, `timestamp`.
   - `BrowserActionRequest`: `action_type`, `target_element_id`, `text_value`, `key_value`, `scroll_delta`, `expected_outcome`, `user_confirmed`.
   - `BrowserActionResult`: `success`, `action_type`, `target_element_id`, `previous_url`, `current_url`, `dom_mutated`, `input_value_verified`, `verification_status`, `error`, `evidence`.
3. `omni_engine/contracts/__init__.py`: Clean re-export of all browser contracts.
4. `omni_engine/browser/session.py`: Persistent isolated profile context (`~/.laya/browser_profile`), stale singleton lock recovery (`SingletonLock`, `SingletonCookie`, `SingletonSocket`), single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags (`--disable-dev-shm-usage`, `--no-sandbox`, `--disable-gpu`, `--disable-background-networking`, etc.).
5. `omni_engine/browser/indexer.py`: In-page DOM stamping (`data-laya-idx="N"`), compact dual-key index `@1..@N`, semantic fingerprint extraction, financial element detection, and pre-action staleness verification (`verify_staleness`).
6. `omni_engine/browser/driver.py`: Primitive action execution (`NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `SNAPSHOT`, `SCREENSHOT`), pre-execution financial safety gate, and evidence-based post-action verification (`dom_mutated` via `MutationObserver`, `url_changed`, physical `input_value`, `scrollY`).
7. `omni_engine/browser/__init__.py`: Clean package exports for `BrowserSession`, `DOMActionIndexer`, `BrowserDriver`.
8. `omni_engine/capabilities/definitions.py`:
   - `BROWSER_INTERACT_SPEC`: Canonical capability spec for real browser interaction (`action_class=ActionClass.EXTERNAL_UPDATE`, `minimum_autonomy_profile=LOCAL_OPERATOR`).
   - `make_browser_interact_adapter()`: Typed adapter returning structured dictionary envelopes.
   - `register_browser_capability()`: Primary `browser_interact` and alias `browser.interact`.
   - `build_real_capability_registry()`: Non-breaking extension preserving 23-tool canonical registry.
9. `omni_engine/capabilities/__init__.py`: Clean export of browser capability specs and builders.
10. `omni_engine/policy/engine.py`:
    - Stage 3 critical sensitive gate updated: `ActionClass.FINANCIAL` and `financial:*` sensitive targets mandate explicit user confirmation under all tiers below `AutonomyProfile.WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`).
    - Added financial browser target detection (`financial:browser_checkout`) in `assess_action()`.
11. `omni_engine/arguments/resolver.py`:
    - Deterministic extraction for browser actions, targets (`@N`), URLs, and quoted text.
    - Repaired function-scope local `import re` trap in `_extract_deterministic_slots` that triggered `UnboundLocalError`.
12. `tests/fixtures/browser_test_page.html`: Standalone local HTML test fixture with interactive elements and checkout button.
13. `tests/test_r2_browser.py`: 15 comprehensive unit and integration tests.
14. `tests/test_l9_policy.py`: Added `test_financial_action_requires_confirmation_even_under_trusted_operator` (26 tests total).

---

### 4. Adversarial Plan & Diff Reviews
- **Adversarial Plan Reviewer**: Subagent `4fa42e31-d1d1-4e17-866f-a37a1402e7d5`.
  - Conditional Approval with 5 Blocking Requirements (REQ-B1 through REQ-B5). All 5 requirements were systematically implemented.
- **Adversarial Diff Reviewer**: Subagent `6812beb1-7cd5-4555-8417-90c4aa6fc27b`.
  - Final Verdict: **PASS (APPROVED FOR CHECKPOINT R2)**.
  - Verified:
    1. REQ-B1 (Session & Resource Lifecycle): Isolated profile `~/.laya/browser_profile`, stale lock recovery, `max_pages=1` popup routing, `atexit` cleanup, low-memory flags.
    2. REQ-B2 (Indexed Action Space & Staleness): Dual-key `@1..@N` + semantic fingerprints + `data-laya-idx` DOM stamping + pre-execution staleness verification.
    3. REQ-B3 (Evidence-Based Post-Action Verification): `dom_mutated` via `MutationObserver`, `url_changed`, physical `input_value`, `scrollY`.
    4. REQ-B4 (Financial Safety & Hard Gating): PolicyEngine Stage 3 gating below `WORKFLOW_AUTHORIZED` + BrowserDriver intrinsic safety regex.
    5. REQ-B5 (Offline Testability & Non-Switching Boundary): 100% offline local fixture test in <3s, 0 diffs in `omni_agent.py` and `omni_engine/planner.py`, 23-tool canonical registry invariant preserved.

---

### 5. Verification & Test Evidence
- **R2 Unit & Integration Test Suite (`tests/test_r2_browser.py`)**:
  - `Ran 15 tests in 2.699s`: **15 passed, 0 failed (100% pass rate)**.
- **L9 Policy Test Suite (`tests/test_l9_policy.py`)**:
  - `Ran 26 tests in 0.079s`: **26 passed, 0 failed (100% pass rate)**.
- **Full Repository Test Suite Across All Checkpoints (L0–L9 + Foundation Gate + R1 + R2)**:
  - `Ran 293 tests in 167.372s`: **293 passed (+ 47 subtests = 340 total tests), 0 failures, 0 errors (100% pass rate)**.
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` returns **0 diffs**.


---

## 18. Phase R3: Windows Desktop, App & Local Service Engine

### 1. Objectives & Architectural Invariants
- **Core Mission**: Build an evidence-grounded, native Windows desktop application management, UI interaction, and local microservice health probing engine operating safely under host resource constraints.
- **Key Capabilities**:
  1. Desktop application lifecycle management (`launch_app`, `focus_window`, `close_window`, `list_windows`, `terminate_app`).
  2. Safe foreground activation avoiding thread attachment deadlocks (`AttachThreadInput`).
  3. Launcher trampoline resolution (e.g. `calc.exe`, `code.cmd`) mapping ephemeral launcher PIDs to true UI windows and PIDs via baseline HWND diffing and child-tree traversal.
  4. Local microservice health probing (`service_health`) supporting dual-stack loopback (`127.0.0.1` -> `::1`), `SO_LINGER` socket reset, and host proxy environment isolation.
  5. Isolated UI input dispatch (`send_keys`) with pre-focus verification and non-intrusive `WM_CHAR` character dispatch.
  6. Rule-0 process defense blocking termination of critical operating system processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4).
- **Core Invariant Enforcement**:
  - **Invariant 1 (Deterministic Control)**: Process lifecycle and window state transitions are owned strictly by deterministic Win32/psutil routines, not probabilistic models.
  - **Invariant 4 (Strongly Typed Contracts)**: All desktop operations emit strongly typed Pydantic models (`WindowBounds`, `WindowState`, `AppWindowInfo`, `AppLaunchResult`, `ServiceHealthStatus`, `DesktopActionResult`) with `extra="forbid"`.
  - **Invariant 6 (Evidence-Based Completion)**: Physical outcome receipts required for every action: `launcher_pid`, `active_pid`, `hwnd`, `bounds`, `is_listening`, `http_status`, `response_time_ms`.
  - **Rule-0 Safety Defense**: Critical system processes are unconditionally shielded; human confirmation is strictly ignored for Rule-0.
  - **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched** (0 diffs).

---

### 2. Technology Audit & Architecture Decision (`docs/research/ADR_R3_WINDOWS_APP_ENGINE.md` / ADR-010)
- **Win32 API (`win32gui`, `win32process`, `win32con`, `ctypes.windll.user32`)**: **ADOPT** via `Win32Backend` abstraction for window enumeration, non-blocking state manipulation, and input dispatch.
- **Process Management (`psutil`, `subprocess`)**: **ADOPT** with Windows process creation flags (`CREATE_NO_WINDOW`, `DETACHED_PROCESS`) and recursive child process tree traversal.
- **Safe Window Activation**: **ADOPT** `ctypes.windll.user32.IsHungAppWindow` pre-check, simulated menu key event (`VK_MENU`) to claim Windows foreground activation rights legitimately, non-blocking `ShowWindowAsync(SW_RESTORE)` for minimized windows (`IsIconic`), and asynchronous activation polling. **REJECT** `AttachThreadInput` due to fatal deadlock risk on unresponsive threads.
- **Process Trampoline Resolution**: **ADOPT** pre-launch baseline HWND diffing (`current_hwnds - baseline_hwnds`) combined with recursive child process tree traversal (`psutil.Process.children(recursive=True)`).
- **Local Service Health Probing**: **ADOPT** dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` connection reset to prevent `TIME_WAIT` socket buildup, dedicated `ProxyHandler({})` opener to bypass host proxy environment traps, bounded 4KB HTTP reads, and strict timeouts (<=500ms socket, <=1500ms HTTP).
- **Decoupled Backend for Testing**: **ADOPT** `Win32Backend` abstract base class with `MockWin32Backend` and ephemeral loopback sockets, allowing `tests/test_r3_desktop.py` to run 100% offline, with zero GUI popups and zero focus stealing, in under 1 second.

---

### 3. Implementation Deliverables
1. `docs/research/ADR_R3_WINDOWS_APP_ENGINE.md`: Architectural Decision Record and technology audit.
2. `omni_engine/contracts/desktop.py`: Strongly typed Pydantic contracts:
   - `WindowBounds`: `left`, `top`, `right`, `bottom`, `width`, `height`.
   - `WindowState`: `NORMAL`, `MINIMIZED`, `MAXIMIZED`, `HIDDEN`.
   - `AppWindowInfo`: `hwnd`, `title`, `process_name`, `pid`, `is_active`, `state`, `bounds`.
   - `AppLaunchResult`: `app_name`, `launcher_pid`, `active_pid`, `process_name`, `hwnd`, `window_title`, `bounds`, `exit_code`, `startup_time_ms`, `verification_status`, `error`.
   - `ServiceHealthStatus`: `service_name`, `host`, `port`, `is_listening`, `http_status`, `response_time_ms`, `error`, `verification_status`.
   - `DesktopActionResult`: `action`, `target`, `prior_state`, `posterior_state`, `verification_status`, `evidence`, `error`.
3. `omni_engine/contracts/__init__.py`: Clean re-export of desktop contracts.
4. `omni_engine/desktop/service.py`: `LocalServiceProber` implementing dual-stack cascade, `SO_LINGER`, proxy bypass, and bounded HTTP reads.
5. `omni_engine/desktop/app_manager.py`: `Win32Backend` (ABC), `NativeWin32Backend`, and `AppWindowManager` implementing non-blocking focus rights via `VK_MENU`, `IsHungAppWindow` rejection, `ShowWindowAsync(SW_RESTORE)`, async activation polling, and launcher trampoline resolution via baseline HWND diffing + child process tree traversal.
6. `omni_engine/desktop/uia_driver.py`: `WindowsInputDriver` with verified pre-focus check and `WM_CHAR` non-intrusive character dispatch.
7. `omni_engine/desktop/engine.py`: `ComputerUseDriver` composite engine unifying app management, input dispatch, and service probing.
8. `omni_engine/desktop/__init__.py`: Package exports for desktop engines and drivers.
9. `omni_engine/capabilities/definitions.py`:
   - Registered `desktop.launch_app`, `desktop.list_windows`, `desktop.focus_window`, `desktop.close_window`, `desktop.service_health`, `desktop.send_keys`, and dotless aliases in `build_real_capability_registry()`.
   - Canonical 23-tool `build_canonical_registry()` strictly preserved.
10. `omni_engine/capabilities/__init__.py`: Clean exports of desktop capability specs.
11. `omni_engine/policy/engine.py`:
    - Broadened Stage 0 Rule-0 process defense across all desktop process-terminating capabilities (`kill_process`, `desktop.kill_process`, `desktop_kill_process`, `desktop.close_window`, `desktop_close_window`, `desktop.terminate_app`).
    - Mapped desktop blast radii in `_assess_risk` (`LOCAL_SYSTEM` for mutating desktop actions, `NONE` for read-only window listing).
12. `omni_engine/arguments/resolver.py`:
    - Added desktop clarification prompts (`CLARIFICATION_PROMPTS`) for `app_name`, `port`, `keys`.
    - Added deterministic slot extractors for desktop app names, window titles, ports, and keystrokes (disambiguating multiple quoted strings).
13. `tests/test_r3_desktop.py`: 21 comprehensive offline unit and integration tests.

---

### 4. Adversarial Plan & Diff Reviews
- **Adversarial Plan Reviewer**: Subagent `0b018a3a-73bc-4039-901e-5f1161505db1`.
  - Conditional Approval with 6 Blocking Requirements (REQ-R3-1 through REQ-R3-6). All 6 requirements were systematically implemented.
- **Adversarial Diff Reviewer**: Subagent `286fba8a-36f5-4ab6-b993-ab0eb8ad56f3`.
  - Final Verdict: **PASS (APPROVED FOR CHECKPOINT R3)**.
  - Verified:
    1. REQ-R3-1 (Window Focus & Input Deadlocks): Alt menu key (`VK_MENU`) foreground activation rights; `ctypes.windll.user32.IsHungAppWindow` pre-check; `ShowWindowAsync(SW_RESTORE)` for minimized windows (`IsIconic`); async activation polling.
    2. REQ-R3-2 (Process Trampoline Resolution & Evidence Verification): Baseline HWND diffing (`current_hwnds - baseline_hwnds`) + `psutil` child-tree traversal; strongly typed physical receipts (`launcher_pid`, `active_pid`, `hwnd`, `bounds`).
    3. REQ-R3-3 (Local Service Health Probing): Dual-stack cascade (`127.0.0.1` -> `::1`); `SO_LINGER` socket reset; `ProxyHandler({})` opener to bypass host proxies; strict timeouts (500ms socket, 1.5s HTTP); 4KB bounded HTTP read.
    4. REQ-R3-4 (Process Safety & Rule-0 Defense): Dual-layer protection in `PolicyEngine` Stage 0 and `AppWindowManager` pre-flight checks blocking critical OS processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4), strictly ignoring human confirmation.
    5. REQ-R3-5 (Offline Testability & Isolation): Decoupled `Win32Backend` with `MockWin32Backend`; ephemeral loopback HTTP/socket server; 100% offline, zero GUI popups, zero focus stealing, in 0.953s.
    6. REQ-R3-6 (Capability Substrate Integration & Non-Switching Boundary): Capabilities registered in `definitions.py`, `build_real_capability_registry()`, `resolver.py`, and `policy/engine.py`; canonical 23-tool registry invariant preserved; `omni_agent.py` and `omni_engine/planner.py` 100% untouched (0 diffs).

---

### 5. Verification & Test Evidence
- **R3 Unit & Integration Test Suite (`tests/test_r3_desktop.py`)**:
  - `Ran 21 tests in 0.953s`: **21 passed, 0 failed (100% pass rate)**.
- **Full Repository Test Suite Across All Checkpoints (L0–L9 + Foundation Gate + R1 + R2 + R3)**:
  - `Ran 314 tests in 211.05s`: **314 passed (+ 47 subtests = 361 total checks), 0 failures, 0 errors (100% pass rate)**.
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` returns **0 diffs**.

---

## CHECKPOINT R4: Programmatic n8n Automation Engine (COMPLETED & VERIFIED)

### 1. Invariants & Scope-Control Confirmation
- **Invariants Followed**:
  - **Invariant 1 (Deterministic Control, Probabilistic Reasoning)**: All workflow DAG checks, cycle detection, state transitions, Gate Triad evaluations, and secret scrubbers are 100% deterministic code.
  - **Invariant 4 (Strongly Typed Capability Contracts)**: All n8n models derive from `BaseContractModel` (`extra="forbid"`), strictly rejecting inline plaintext secrets at the schema boundary.
  - **Invariant 6 (Evidence-Based Completion)**: Workflows cannot be activated without physical execution receipts (`execution_id`, `status="success"`) for the current deterministic `workflow_hash`.
  - **Secret Isolation Invariant**: Credentials strictly referenced by ID; zero plaintext tokens in headers, logs, or outputs.
  - **Rule-0 Safety Defense**: RCE defense in `PolicyEngine` Stage 0 scans `executeCommand` parameters to block forbidden operations (`git reset --hard`, destructive drive wipes), strictly ignoring human confirmation.
  - **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched** (0 diffs).

---

### 2. Technology Audit & Architecture Decision (`docs/research/ADR_R4_N8N_AUTOMATION_ENGINE.md` / ADR-011)
- **n8n REST API Integration**: **ADOPT** n8n v1 REST API (`/workflows`, `/executions`) via decoupled `N8nTransport`.
- **Strict Draft-Test-Validate Gate Triad**: **ADOPT** invariant where workflows are forced to `active=False` on creation/update. Activation requires: (1) Valid DAG, (2) Verified physical execution receipt for current `workflow_hash`, (3) Zero plaintext secrets. Any modification recalculates the hash and invalidates prior receipts.
- **3-Level Nested Schema & Bidirectional Resolution**: **ADOPT** parser traversing `connections[src]["main"][idx] = [{"node": target, ...}]` with bidirectional resolution (`node_by_name` and `node_by_id`) to prevent false dangling connection errors.
- **Multi-Pattern Secret Scrubber**: **ADOPT** compiled regexes for OpenAI (`sk-`), GitHub (`ghp_`), AWS, Bearer/Basic, n8n API keys, private keys, generic tokens, and headers while safely preserving `$json.*` and `={{ ... }}` n8n expression syntax.
- **Wait Node Breakout in Polling**: **ADOPT** immediate breakout from polling loop when an execution transitions to `"waiting"`, preventing worker stall.
- **RCE & Policy Defense**: **ADOPT** sensitive target tagging and blast radius escalation (`LOCAL_SYSTEM` / `SECURITY_CRITICAL`, composite risk >= 0.70) for `executeCommand`, `code`, `ssh`, and `readWriteFile` nodes, combined with Stage 0 Rule-0 command scanning.
- **Decoupled Transport for Offline Isolation**: **ADOPT** `N8nTransport` (ABC) with `HttpN8nTransport` and `MockN8nTransport` for 100% offline, deterministic, sub-second test execution.

---

### 3. Implementation Deliverables
1. `docs/research/ADR_R4_N8N_AUTOMATION_ENGINE.md`: Architectural Decision Record and technology audit.
2. `omni_engine/contracts/n8n.py`: Strongly typed Pydantic contracts:
   - `N8nTriggerType`: `WEBHOOK`, `SCHEDULE`, `MANUAL`, `EVENT`, `OTHER`.
   - `N8nCredentialReference`: `id: str`, `name: Optional[str]`, strictly forbidding inline secrets via `extra="forbid"`.
   - `N8nNode`: `id`, `name`, `type`, `parameters`, `credentials`, `disabled`.
   - `N8nWorkflowSummary`: `id`, `name`, `active`, `created_at`, `updated_at`, `tags`.
   - `N8nWorkflowDetail`: Full definition with deterministic SHA-256 `compute_hash()`.
   - `N8nWorkflowValidationResult`: `is_valid`, `errors`, `warnings`, `cycles_detected`, `trigger_nodes`, `reachable_nodes`, `contains_secrets`.
   - `N8nExecutionReceipt`: `execution_id`, `workflow_id`, `workflow_hash`, `status`, `duration_ms`, `node_execution_counts`, `output_data`, `error`, `verification_status`.
   - `N8nActionResult`: `action`, `workflow_id`, `execution_id`, `verification_status`, `data`, `error`.
3. `omni_engine/contracts/__init__.py`: Clean re-export of all n8n contracts.
4. `omni_engine/automation/scrubber.py`: `SecretScrubber` with compiled patterns for OpenAI, GitHub, Bearer/Basic, AWS, n8n API keys, private keys, generic tokens, and sensitive headers while preserving `$json.*` syntax.
5. `omni_engine/automation/validator.py`: `N8nWorkflowValidator` parsing 3-level nested connections, bidirectional node mapping, 3-color topological DFS cycle detector, in-degree constraints (`trigger in-degree == 0`, triggers >= 1), reachability analysis, and pre-flight parameter secret scan.
6. `omni_engine/automation/transport.py`: Decoupled `N8nTransport` (ABC), `HttpN8nTransport` (urllib + `ProxyHandler({})`), and `MockN8nTransport` (in-memory state machine for fast offline tests).
7. `omni_engine/automation/client.py`: `N8nClient` enforcing draft mode (`active=False`) on creation, endpoints for activate/deactivate, execution trigger, and execution polling.
8. `omni_engine/automation/engine.py`: `N8nAutomationEngine` implementing Draft-Test-Validate lifecycle, Gate Triad enforcement for `activate_workflow`, bounded exponential backoff in `trigger_and_wait` with `"waiting"` state breakout.
9. `omni_engine/automation/__init__.py`: Package exports for automation engine and components.
10. `omni_engine/capabilities/definitions.py`:
    - Registered 7 canonical n8n specs, adapters, and dotless aliases in `build_real_capability_registry()`: `n8n.list_workflows`, `n8n.get_workflow`, `n8n.validate_workflow`, `n8n.create_workflow`, `n8n.activate_workflow`, `n8n.trigger_workflow`, `n8n.get_execution_status`.
    - Preserved 23-tool canonical registry invariant (`build_canonical_registry()`).
11. `omni_engine/capabilities/__init__.py`: Clean exports of n8n capability specs.
12. `omni_engine/policy/engine.py`:
    - Mapped n8n high-risk node detection (`executeCommand`, `code`, `ssh`, `readWriteFile`) in `assess_action` escalating blast radius to `LOCAL_SYSTEM` / `SECURITY_CRITICAL` and composite risk to >= 0.70.
    - Added Stage 0 Rule-0 command scanning of `executeCommand` parameters to block forbidden operations (`git reset --hard`, destructive drive formatting).
13. `omni_engine/arguments/resolver.py`:
    - Added n8n clarification prompts (`CLARIFICATION_PROMPTS`) for `workflow_id`, `execution_id`, `name`.
    - Added deterministic slot extractors for n8n workflow IDs, execution IDs, and workflow names.
14. `tests/test_r4_n8n.py`: 25 comprehensive offline unit and integration tests.

---

### 4. Adversarial Plan & Diff Reviews
- **Adversarial Plan Reviewer**: Subagent `711073de-234c-46cc-8259-8bde4b647987`.
  - Conditional Approval with 7 Blocking Requirements (REQ-BLOCK-1 through REQ-BLOCK-7). All 7 requirements were systematically addressed.
- **Adversarial Diff Reviewer**: Subagent `901d60b3-003c-4854-9d3c-b76bed8c4f44`.
  - Final Verdict: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)**.
  - Verified:
    1. REQ-BLOCK-1 (Gate Triad Invariant & Activation Guard): Workflows forced to `active=False` on creation; `activate_workflow` verifies valid DAG, verified physical receipt for current hash, and zero secrets; hash changes invalidate prior receipts.
    2. REQ-BLOCK-2 (n8n Connection Schema Representation & DAG Validation): 3-level nested schema traversal; bidirectional resolution (`node_by_name` and `node_by_id`); 3-color DFS cycle detection; trigger in-degree == 0; trigger count >= 1; forward reachability.
    3. REQ-BLOCK-3 (Zero Plaintext Secrets & Scrubber Completeness): Full token/header scrubbing preserving `$json.*` syntax; `N8nCredentialReference` with `extra="forbid"` and id-only reference.
    4. REQ-BLOCK-4 (Wait Node Breakout in Polling): Immediate breakout on `"waiting"` state; bounded timeouts; exponential backoff.
    5. REQ-BLOCK-5 (RCE Defense in PolicyEngine): Blast radius and risk score escalation for high-risk nodes; Stage 0 Rule-0 scanner blocking destructive operations in `executeCommand`.
    6. REQ-BLOCK-6 (Substrate Integration & Non-Switching Boundary): 7 n8n capabilities registered across registry, resolver, and policy engine; canonical 23-tool registry invariant strictly preserved; `omni_agent.py` and `omni_engine/planner.py` 100% untouched (0 diffs).
    7. REQ-BLOCK-7 (Offline Testability & Isolation): Clean transport decoupling; `MockN8nTransport` enabling 100% offline tests in <5s; all 25 unit tests and 339 full repository tests passing.

---

### 5. Verification & Test Evidence
- **R4 Unit & Integration Test Suite (`tests/test_r4_n8n.py`)**:
  - `Ran 25 tests in 4.72s`: **25 passed, 0 failed (100% pass rate)**.
- **Full Repository Test Suite Across All Checkpoints (L0–L9 + Foundation Gate + R1 + R2 + R3 + R4)**:
  - `Ran 339 tests in 214.99s`: **339 passed (+ 47 subtests = 386 total checks), 0 failures, 0 errors (100% pass rate)**.
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` returns **0 diffs**.
- **Canonical Registry Invariant**:
  - `build_canonical_registry()` returns exactly 23 source capabilities.


---

## CHECKPOINT R5: Supervised Developer Agent & Antigravity Engine (COMPLETED & VERIFIED)

### 1. Invariants & Scope-Control Confirmation
- **Invariants Followed**:
  - **Invariant 1 (Deterministic Control, Probabilistic Reasoning)**: The Foreman supervision lifecycle, AST syntax gating, thrashing detection, iteration clamping, process group spawning, timeout termination, and safe file-by-file reversion are 100% deterministic code.
  - **Invariant 4 (Strongly Typed Capability Contracts)**: All developer models (`DevTaskSpec`, `CodeVerificationReceipt`, `DevExecutionReceipt`, `DevActionResult`) derive from `BaseContractModel` (`extra="forbid"`).
  - **Invariant 6 (Evidence-Based Completion)**: Tasks cannot be reported completed without physical test exit code 0 (`tests_passed=True`), physical AST parse verification (`syntax_valid=True`), and captured working tree diffs. Plausible generated explanations are never equated with verified code modifications.
  - **Rule-0 Safety Defense**: Unconditional prohibition of destructive git commands (`git reset --hard`, `git clean -fd`, `git push -f`). Reversion operates file-by-file using `git checkout -- <file>` for tracked files and `os.remove()` for untracked files within repository boundaries.
  - **Anti-Tampering Invariant**: Test files (`test_*.py`, `*_test.py`, `tests/`) cannot be modified unless explicitly authorized via `allow_test_edits=True`.
  - **Non-Switching Boundary**: Legacy `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched** (0 diffs).
  - **Hard Stop Boundary**: Engineering strictly halted after Phase R5. Zero implementation of L10–L14.

---

### 2. Technology Audit & Architecture Decision (`docs/research/ADR_R5_DEVELOPER_AGENT.md` / ADR-012)
- **Foreman 5-Stage Bounded Supervision Lifecycle**: **ADOPT** coordinated lifecycle: Setup/Baseline -> Mutation -> Pre-Test AST Syntax Gate -> Test Execution -> Convergence/Safe Reversion.
- **Deterministic Thrashing & Cycle Detection**: **ADOPT** composite SHA-256 state fingerprinting over working tree `git diff`, sorted modified file names, and raw binary file contents. Immediate abort with `ConvergenceStatus.THRASHING_DETECTED` if any iteration revisits a prior state.
- **Subprocess Process-Tree Isolation**: **ADOPT** Windows `CREATE_NEW_PROCESS_GROUP`, `communicate(timeout=...)` deadlock defense, `taskkill /F /T /PID` process-tree termination, quote-stripping argument parser, and 50,000 character output truncation.
- **Git Workspace Confinement & Path Traversal Immunity**: **ADOPT** `.git` repository root validation, protected system path blocks (`is_protected_path`), and dual path containment verification (`pathlib.Path.is_relative_to` and `os.path.commonpath`).
- **Inviolable Safe Reversion Primitive**: **ADOPT** file-by-file rollback (`git checkout -- <file>` and `os.remove`), strictly eliminating destructive reset commands.
- **Anti-Tampering on Test Suites**: **ADOPT** test file protection (`verify_not_test_tampering`) blocking unauthorized edits to test suites when `allow_test_edits=False`.
- **Pre-Test AST Syntax Fail-Fast Gate**: **ADOPT** `ast.parse()` on all modified Python files before test command dispatch, failing fast on syntax errors.
- **Decoupled Antigravity Runner**: **ADOPT** `AgyRunner` (ABC), `SubprocessAgyRunner` (local `agy.exe` non-interactive invocation), and `MockAgyRunner` (fast offline test simulation).

---

### 3. Implementation Deliverables
1. `docs/research/ADR_R5_DEVELOPER_AGENT.md`: Architectural Decision Record and technology audit.
2. `omni_engine/contracts/developer.py`: Strongly typed Pydantic contracts:
   - `ConvergenceStatus`: `CONVERGED`, `MAX_ITERATIONS_REACHED`, `THRASHING_DETECTED`, `TEST_TAMPERING_DETECTED`, `SYNTAX_ERROR`, `TIMEOUT`, `RULE_0_VIOLATION`, `UNVERIFIED`.
   - `DevTaskSpec`: `task_id`, `repo_path`, `task_prompt`, `target_files`, `test_commands`, `allow_test_edits`, `max_iterations`, `timeout_seconds`, `metadata`.
   - `CodeVerificationReceipt`: `syntax_valid`, `syntax_errors`, `lint_passed`, `tests_passed`, `test_exit_code`, `test_output`, `test_duration_ms`, `verification_status`.
   - `DevExecutionReceipt`: `task_id`, `repo_path`, `exit_code`, `modified_files`, `git_diff`, `git_head_before`, `iterations_count`, `convergence_status`, `verification`, `duration_ms`, `status`, `error`.
   - `DevActionResult`: `action`, `task_id`, `verification_status`, `receipt`, `data`, `error`.
3. `omni_engine/contracts/__init__.py`: Clean re-export of all developer contracts.
4. `omni_engine/developer/process_runner.py`: `DeterministicSubprocessRunner` with Windows `CREATE_NEW_PROCESS_GROUP`, `communicate(timeout=...)` deadlock defense, `taskkill /F /T /PID` process-tree cleanup, quote-stripping argument parser, and 50,000 char output truncation.
5. `omni_engine/developer/workspace.py`: `WorkspaceConfiner` validating `.git` existence, blocking protected OS roots (`is_protected_path`), verifying path containment via `is_relative_to` and `commonpath`, blocking test file tampering when `allow_test_edits=False`, and performing safe file-by-file revert (`git checkout -- <file>`, `os.remove` for untracked files) strictly avoiding destructive `git reset --hard` or `git clean -fd`.
6. `omni_engine/developer/runner.py`: Decoupled `AgyRunner` (ABC), `SubprocessAgyRunner` (local `agy.exe`), and `MockAgyRunner` (fast offline simulation).
7. `omni_engine/developer/engine.py`: `DeveloperSupervisorEngine` implementing Foreman 5-stage lifecycle, AST syntax fail-fast gate, thrashing/oscillation detection via SHA-256 fingerprint, test runner, git diff, and code inspection.
8. `omni_engine/developer/__init__.py`: Package exports for developer engine and components.
9. `omni_engine/capabilities/definitions.py`:
   - Registered 4 developer capability specs (`developer.run_task`, `developer.run_tests`, `developer.git_diff`, `developer.inspect_code`) and dotless aliases in `build_real_capability_registry()`.
   - Preserved 23-tool canonical registry invariant (`build_canonical_registry()`).
10. `omni_engine/capabilities/__init__.py`: Clean exports of developer capability specs.
11. `omni_engine/policy/engine.py`:
    - Mapped developer capabilities to `LOCAL_WORKSPACE` blast radius.
    - Added Stage 0 Rule-0 command scanning of `test_commands` parameters to block forbidden operations (`git reset --hard`, destructive drive formatting).
    - Added Stage 0 protected OS path blocking for `repo_path`.
12. `omni_engine/arguments/resolver.py`:
    - Added developer clarification prompts (`CLARIFICATION_PROMPTS`) for `repo_path`, `task_prompt`, `test_commands`, `file_path`.
    - Added deterministic slot extractors supporting spaces and quotes in `repo_path`.
13. `tests/test_r5_developer.py`: 25 comprehensive offline unit and integration tests.

---

### 4. Adversarial Plan & Diff Reviews
- **Adversarial Plan Reviewer**: Subagent `c96c2b7a-ce7f-4d60-b4c2-aaeef620b7dd`.
  - Conditional Approval with 7 Blocking Requirements (REQ-BLOCK-1 through REQ-BLOCK-7). All 7 requirements were systematically addressed.
- **Adversarial Diff Reviewer**: Subagent `fb7ba688-2887-47fa-811d-d25dbe922f53`.
  - Final Verdict: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)**.
  - Verified:
    1. REQ-BLOCK-1 (Bounded Convergence Loop & Thrashing Defense): 5-stage Foreman lifecycle; state fingerprinting hashing working tree diff, files, and contents; max_iterations clamped to [1, 5]; anti-tampering test guard; safe rollback on failure.
    2. REQ-BLOCK-2 (Subprocess Process-Tree Isolation): Windows `CREATE_NEW_PROCESS_GROUP`; `communicate(timeout=...)` deadlock defense; `taskkill /F /T /PID` process-tree cleanup; 50k char buffer bounds.
    3. REQ-BLOCK-3 (Workspace Confinement & Safe Revert - Invariant 1, Rule 0): `.git` root validation; protected system path blocks; dual containment checks (`is_relative_to` & `commonpath`); Rule-0 safe file-by-file reversion avoiding `git reset --hard` / `git clean -fd`.
    4. REQ-BLOCK-4 (Deterministic Pre-Test AST Syntax Gate): `ast.parse()` on all modified Python files before test command dispatch; syntax errors fail fast.
    5. REQ-BLOCK-5 (Substrate Integration & Canonical 23-Tool Registry Invariant): 4 developer capabilities registered across registry, resolver, and policy engine; canonical 23-tool registry invariant strictly preserved.
    6. REQ-BLOCK-6 (Rule-0 Hard Invariant Defense): Stage 0 Rule-0 command scanning on `test_commands`; protected system path blocking on `repo_path`; inviolability under `user_confirmed=True`.
    7. REQ-BLOCK-7 (Decoupled Mock & Non-Switching Boundary): Decoupled `AgyRunner` ABC; `MockAgyRunner` enabling 100% offline tests; all 25 unit tests and 364 full repository tests passing; `omni_agent.py` and `omni_engine/planner.py` 100% untouched (0 diffs).
    8. Hard Stop Boundary Check: PR strictly ends at Phase R5; zero code or stubs for L10–L14.

---

### 5. Verification & Test Evidence
- **R5 Unit & Integration Test Suite (`tests/test_r5_developer.py`)**:
  - `Ran 25 tests in 17.33s`: **25 passed, 0 failed (100% pass rate)**.
- **Full Repository Test Suite Across All Checkpoints (L0–L9 + Foundation Gate + R1 + R2 + R3 + R4 + R5)**:
  - `Ran 364 tests in 233.91s`: **364 passed (+ 47 subtests = 411 total checks), 0 failures, 0 errors, 2 warnings (100% pass rate)**.
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` returns **0 diffs**.
- **Canonical Registry Invariant**:
  - `build_canonical_registry()` returns exactly 23 source capabilities.

---

## MILESTONE COMPLETION: Real Capability Engines (Foundation Gate + R1 → R5)

With the successful completion and verification of Phase R5, the entire **Real Capability Engines** milestone is officially complete:
1. **Foundation Gate**: System One Broker, User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), Two-Level Concurrency Locks, Windows RAM Telemetry, Empirical Calibration (72/31 split, ECE 0.1192).
2. **Phase R1 (Deep Research Engine)**: Multi-source web extraction, Cryptographic Citation Hash Verification (`[UNVERIFIED_CITATION: <id>]`), Mathematical Saturation Stopping, Prompt-Injection Sanitization (NFKC, control char stripping, boundary tags), Offline Mocking.
3. **Phase R2 (Real Browser Engine)**: Playwright persistent context (`~/.laya/browser_profile`), stale singleton lock recovery, `@1..@N` dynamic indexed action space with semantic fingerprints, pre-execution staleness validation, physical evidence receipts (`dom_mutated`, `input_value`, `url_changed`), hard financial confirmation gate.
4. **Phase R3 (Windows Desktop & Local Service Engine)**: Win32 safe window management (Alt-key foreground rights claim, `IsHungAppWindow` check, non-blocking `ShowWindowAsync`), process trampoline resolution (HWND baseline diffing + child tree traversal), dual-stack local service health prober (SO_LINGER, proxy bypass), Rule-0 critical OS process termination protection (`csrss`, `lsass`, PID 0/4).
5. **Phase R4 (n8n Automation Engine)**: Programmatic n8n v1 REST engine, strict Draft-Test-Validate Gate Triad (`active=False` default, valid DAG, test execution receipt for exact hash, zero secrets), 3-level nested schema resolution, multi-pattern SecretScrubber, Wait node breakout in polling, two-tier RCE and Stage 0 command policy defense.
6. **Phase R5 (Developer Agent & Antigravity Engine)**: Foreman 5-stage bounded supervision lifecycle, composite SHA-256 state fingerprinting for thrashing/oscillation cycle detection, `DeterministicSubprocessRunner` with Windows `CREATE_NEW_PROCESS_GROUP`, `taskkill /F /T /PID` process-tree termination, 50k char output truncation, `WorkspaceConfiner` validating `.git` and preventing path traversal, anti-tampering on test suites (`allow_test_edits=False`), fail-fast AST syntax gate, safe reversion primitive (never `git reset --hard` / `git clean -fd`), decoupled `AgyRunner` ABC (`SubprocessAgyRunner`, `MockAgyRunner`).

**Cumulative Verification Metrics**:
- **364 automated tests passing + 47 subtests = 411 verified test checks (100% pass rate)**.
- **0 regressions across L0–L9 and R1–R5**.
- **0 diffs in legacy execution paths (`omni_agent.py`, `omni_engine/planner.py`)**.
- **Hard Stop Boundary Strictly Enforced**: Zero advance code for L10–L14. Ready for Phase IV (Persistent Quest Engine & DAG Planning).

---

## 8. RV0 — Live Reality Gate & Documentation Audit (Completed)

### 8.1 Objectives & Verification Mandate
1. **Pre-Flight Bootstrap & Documentation Truth Audit**:
   - Establish `END_TO_END_EXECUTION_LOG.md` as the permanent, mandatory cumulative engineering record in `AGENTS.md`.
   - Reaffirm hardware-aware System 1 latency reality (host CPU ModernBERT-large is ~749ms single, ~15.4s for full 15-question DecisionFrame; `<35ms` target is CUDA-only).
   - Reaffirm strict English-Only scope (`DEF-008`: multilingual models permanently banned).
   - Verify non-switching boundary (`omni_agent.py` and `omni_engine/planner.py` have 0 diffs).
2. **Mandatory External Architecture & Technology Research Gate**:
   - Research Python 3.12 SQLite PRAGMA dynamics (WAL mode, synchronous=NORMAL, foreign_keys=ON, busy_timeout=5000, and explicit transactions).
   - Study Durable Workflow Architecture (Atomic reference model: persisted task entities, state machines, DAG validation, approval gates, worktree isolation).
   - Author ADR-013 (`docs/research/ADR_L10_QUEST_RUNTIME.md`) and register in `tasks/DECISIONS.md`.
3. **Rule-0 Invariant Analysis & Dirty Worktree Test Hardening**:
   - Critically evaluate `WorkspaceConfiner.safe_revert()` in `omni_engine/developer/workspace.py`.
   - Identified and fixed defect: `safe_revert` previously swept all untracked files (`??`) and checked out all modified files (`M`), which would destroy pre-existing user work outside task scope.
   - Implemented `WorkspaceConfiner.capture_baseline_state()` and updated `safe_revert()` to strictly exclude and preserve pre-existing dirty files and content byte-for-byte.
4. **Live Execution of the Complete `REALITY_MATRIX`**:
   - RV0-A: System 1 Broker Sovereignty (`USER_LOCKED`, `USER_PREFERRED` fallback, `AUTO`, English-only rejection).
   - RV0-B: Deep Research Cryptographic Citations (SHA-256 evidence item hashing, passage extraction, `[UNVERIFIED_CITATION: <id>]` quarantine).
   - RV0-C: Playwright Browser Session (`@1..@N` dynamic index stamps, DOM mutation detection, physical input value verification, financial gating).
   - RV0-D: Desktop Windows & Service Probing (window enumeration, dual-stack loopback socket probe with proxy bypass, Rule-0 critical OS process protection for `csrss`, `lsass`, PID 0, PID 4).
   - RV0-E: n8n Automation Engine (draft mode default, Gate Triad blocking unverified activation, test execution receipt caching, SecretScrubber credential sanitization while preserving `$json.*` expressions).
   - RV0-F: Developer Agent & Mandatory Dirty Worktree Survival (AST syntax fail-fast gate, Foreman bounded loop, byte-for-byte survival of pre-existing uncommitted user files `user_scratchpad.txt` and `existing_draft.py` when task changes are reverted).

---

### 8.2 Research Performed & Technology Decisions

#### Python 3.12 SQLite PRAGMA Dynamics (Host Environment Audit)
- **Host Audit**: Python 3.12.10, SQLite 3.49.1 on Windows 10.
- **Empirical Behavior Discovered**:
  - In Python 3.12, initializing `sqlite3.connect(..., autocommit=False)` automatically starts a transaction on the first statement.
  - Executing `PRAGMA journal_mode = WAL;` or `PRAGMA synchronous = NORMAL;` inside an active transaction raises:
    `sqlite3.OperationalError: cannot change into wal mode from within a transaction` or `Safety level may not be changed inside a transaction`.
  - **Adopted Pattern**: Connection factory must initialize connection with `autocommit=True`, execute:
    - `PRAGMA journal_mode = WAL;`
    - `PRAGMA synchronous = NORMAL;`
    - `PRAGMA busy_timeout = 5000;`
    - `PRAGMA foreign_keys = ON;`
    and subsequently set `conn.autocommit = False` to enable explicit PEP 249 transaction demarcation (`conn.commit()` / `conn.rollback()`).

#### Durable Agent Architecture Audit (Atomic as REFERENCE ONLY)
- **Studied Patterns**: Atomic's durable state machine, explicit stage transitions, step status, persisted receipts, and workspace confinement.
- **Adopted**: Persisted Quest state transitions (`CREATED -> PLANNED -> RUNNING -> PAUSED -> AWAITING_VERIFICATION -> COMPLETED / FAILED / CANCELLED`), step status enum, OCC version check (`UPDATE quests SET status=?, version=version+1 WHERE id=? AND version=?`), SQLite-backed append-only event log.
- **Adapted**: Lightweight SQLite store using native Python 3.12 `sqlite3` with serialized thread locks and connection pooling, completely free of heavy external ORMs.
- **Rejected**: In-memory task runners, unpersisted DAG queues, and mixing execution state with conversational memory.
- **Documented**: Recorded in `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013).

#### Rule-0 Dirty Worktree Safety Repair
- **Root Cause**: `WorkspaceConfiner.safe_revert()` inspected `git status --porcelain` after failure and reverted any modified file and deleted any untracked file, without checking if those files existed before the task started.
- **Repair**:
  - Added `WorkspaceConfiner.capture_baseline_state()` returning `Dict[str, Optional[str]]` mapping file paths to their pre-task baseline (SHA-256 or uncommitted byte contents).
  - Updated `WorkspaceConfiner.safe_revert(..., baseline_state=...)`:
    - Untracked files that existed in `baseline_state` are NEVER deleted.
    - Modified files that were already modified in `baseline_state` are restored to their exact baseline contents, rather than `git checkout -- <file>` which would wipe uncommitted user edits.
    - All 6 revert call sites in `DeveloperSupervisorEngine` (`omni_engine/developer/engine.py`) now capture baseline state at session start and pass it to `safe_revert`.

---

### 8.3 Code Files Created, Modified, and Deleted

#### Created:
1. `docs/research/ADR_L10_QUEST_RUNTIME.md`: ADR-013 defining SQLite WAL, schema, OCC, and crash recovery.
2. `tests/test_rv0_reality_gate.py`: 8 comprehensive reality gate tests covering RV0-A through RV0-F.

#### Modified:
1. `AGENTS.md`: Permanent cumulative engineering record invariant for `END_TO_END_EXECUTION_LOG.md`; System 1 latency reality (<35ms on CUDA, ~15.4s on host CPU); English-only policy.
2. `omni_engine/developer/workspace.py`: Implemented `capture_baseline_state()` and updated `safe_revert()` with dirty worktree protection.
3. `omni_engine/developer/engine.py`: Baseline state captured at task start and passed to all 6 `safe_revert()` call sites.
4. `tasks/DECISIONS.md`: Registered ADR-013.
5. `tasks/DEFERRED.md`: Activated DEF-009 (L10–L14) and added DEF-010 (L15–L16 deferred post-L14).
6. `tasks/ACTIVE_PLAN.md`: Synchronized active checkpoint from RV0 to L10.
7. `LAYA_BUILD_STATE.md`: Synchronized test totals (372 passed, 419 checks) and active milestone.
8. `HANDOFF.md`: Updated continuation instructions for L10.
9. `END_TO_END_EXECUTION_LOG.md`: Top health dashboard, flowchart, and complete RV0 engineering entry.

#### Deleted:
- None.

---

### 8.4 Reality Matrix Verification Evidence

| Matrix Test | Component Tested | Verification Performed | Outcome |
| :--- | :--- | :--- | :--- |
| **RV0-A** | System 1 Broker | Live ModernBERT inference + sovereignty hierarchy (`USER_LOCKED`, `USER_PREFERRED` fallback to LAYA when Jev is unconfigured, `AUTO`, English-only rejection). | **PASS** |
| **RV0-B** | Deep Research | Cryptographic SHA-256 evidence item hashing, passage extraction, relevance ranking, unverified citation quarantining to `[UNVERIFIED_CITATION: <id>]`. | **PASS** |
| **RV0-C** | Browser Engine | Headless Playwright session, `@1..@N` dynamic index stamps, DOM mutation detection, physical input value verification, financial gating. | **PASS** |
| **RV0-D** | Windows Desktop & Service | Process window enumeration, dual-stack loopback socket health probe with proxy bypass, Rule-0 critical OS process defense (`csrss`, `lsass`, PID 0, PID 4). | **PASS** |
| **RV0-E** | n8n Automation | Workflow creation forced into draft mode, Gate Triad blocking unverified activation, test execution receipt caching, SecretScrubber redacting sensitive credentials while preserving `$json.*` expressions. | **PASS** |
| **RV0-F** | Developer Agent & Dirty Worktree | AST syntax check catches syntax errors before running tests and safely reverts corrupted code without modifying baseline files. **MANDATORY DIRTY WORKTREE SURVIVAL**: Pre-existing uncommitted user files (`user_scratchpad.txt` untracked, `existing_draft.py` modified) survive rollback byte-for-byte when task changes fail! | **PASS** |

---

### 8.5 Test Results & Execution Metrics

- **RV0 Reality Gate Suite (`tests/test_rv0_reality_gate.py`)**:
  - `python -m unittest tests/test_rv0_reality_gate.py`
  - Output: `Ran 8 tests in 513.821s, OK` (8 passed, 0 failed, 100% pass rate).
- **Full Repository Test Suite (L0–L9 + Foundation Gate + R1–R5 + RV0)**:
  - `python -m unittest discover tests`
  - Output: `Ran 372 tests in 820.298s, OK` (372 passed + 47 subtests = 419 total checks, 0 failures, 0 errors, 2 benign upstream warnings).
- **Non-Switching Boundary**:
  - `git diff HEAD omni_agent.py omni_engine/planner.py` = **0 diffs**.
- **Working Tree Cleanliness**:
  - Zero uncommitted test artifacts, zero dangling files.

---

### 8.6 Checkpoint Completion & Next Phase
- **RV0 Reality Gate & Documentation Audit is Officially PASSED and COMPLETED**.
- **Next Active Checkpoint**: **L10 — Persisted SQLite Quest Runtime**.

---

## 9. Checkpoint L10 — Persisted SQLite Quest Runtime (Completed)

### 9.1 Objectives & Architectural Mandate
- Implement the core durable Quest runtime as defined in ADR-013 (`docs/research/ADR_L10_QUEST_RUNTIME.md`).
- Ensure all multi-step work executes via a strongly typed, persisted `Quest` entity backed by SQLite.
- Guarantee strict Invariant 1 (Deterministic Control) and Invariant 6 (Evidence-Based Completion): state machine transitions cannot be bypassed, and a Quest cannot transition from `RUNNING` directly to `COMPLETED` without progressing through `AWAITING_VERIFICATION`.
- Implement Optimistic Concurrency Control (OCC) with version incrementing on `Quest` and `QuestStep` to prevent lost updates and race conditions across concurrent workers.
- Enforce Python 3.12 SQLite PRAGMA initialization dynamics (`autocommit=True` prior to WAL/synchronous PRAGMAs, then `autocommit=False` for explicit transactions).
- Maintain 100% legacy isolation (0 diffs on `omni_agent.py` and `omni_engine/planner.py`).

---

### 9.2 Architecture & Design Decisions

#### 1. Strongly Typed Contracts (`omni_engine/contracts/quest.py`)
- `QuestStatus`: `CREATED`, `PLANNED`, `RUNNING`, `PAUSED_FOR_CONFIRMATION`, `PAUSED_FOR_INPUT`, `AWAITING_VERIFICATION`, `COMPLETED`, `FAILED`, `CANCELLED`.
- `StepStatus`: `PENDING`, `READY`, `RUNNING`, `PAUSED`, `AWAITING_VERIFICATION`, `COMPLETED`, `FAILED`, `CANCELLED`, `SKIPPED`.
- `QuestEventEnum`: `QUEST_CREATED`, `PLAN_ATTACHED`, `STEP_STARTED`, `STEP_COMPLETED`, `STEP_FAILED`, `STEP_PAUSED`, `STEP_RESUMED`, `QUEST_PAUSED`, `QUEST_RESUMED`, `QUEST_AWAITING_VERIFICATION`, `QUEST_COMPLETED`, `QUEST_FAILED`, `QUEST_CANCELLED`.
- `TERMINAL_QUEST_STATES`: `{COMPLETED, FAILED, CANCELLED}` — strictly absorbing terminal states.
- `VALID_QUEST_TRANSITIONS`: Explicit transition matrix preventing illegal state hops (e.g. `CREATED -> RUNNING` without plan attachment, or `RUNNING -> COMPLETED` without verification).
- `VALID_STEP_TRANSITIONS`: Explicit transition matrix allowing `PENDING -> READY -> RUNNING` or direct `PENDING -> RUNNING`, `RUNNING -> AWAITING_VERIFICATION -> COMPLETED`.
- Domain exceptions: `QuestError`, `QuestNotFoundError`, `StepNotFoundError`, `InvalidStateTransitionError`, `OptimisticLockError`.
- Models: `QuestStep`, `QuestEvent`, `Quest` with strict Pydantic v2 validation (`BaseContractModel`, `extra="forbid"`).

#### 2. SQLite Persistence Store (`omni_engine/quest/store.py`)
- Three relational tables: `quests`, `quest_steps`, `quest_events`.
- SQLite foreign key constraints: `ON DELETE CASCADE` from `quests` to `quest_steps` and `quest_events`.
- Thread safety: `threading.local()` connection factory paired with a store-level `self._write_lock = threading.RLock()` guaranteeing that SQLite write statements are serialized across threads, eliminating `database is locked` race conditions while WAL mode serves concurrent readers.
- In-memory URI support: Shared memory mode (`file:quest_memdb?mode=memory&cache=shared`) for multi-connection thread tests.
- Optimistic Concurrency Control (OCC): `UPDATE quests ... WHERE quest_id = ? AND version = ?` and `UPDATE quest_steps ... WHERE quest_id = ? AND step_id = ? AND version = ?`. If `rowcount == 0`, raises `OptimisticLockError`.

#### 3. State Machine Controller (`omni_engine/quest/engine.py`)
- `QuestEngine`: High-level orchestrator managing Quest creation, plan attachment, state transitions, step status transitions, and audit event logging.
- Automatically maps state transitions to immutable `QuestEvent` records.
- Provides `recover_active_quests()` to reconstruct active in-flight quests after unexpected process terminations.

---

### 9.3 Code Files Created and Modified

#### Created:
1. `omni_engine/contracts/quest.py`: Pydantic v2 contracts, enums, transition matrices, and exceptions.
2. `omni_engine/quest/__init__.py`: Package initialization exporting `QuestStore` and `QuestEngine`.
3. `omni_engine/quest/store.py`: Thread-safe SQLite persistence store with WAL mode, OCC, and cascades.
4. `omni_engine/quest/engine.py`: Quest state machine controller and audit event emitter.
5. `tests/test_l10_quest.py`: 13 comprehensive unit and integration tests.

#### Modified:
1. `omni_engine/contracts/__init__.py`: Re-exported all Quest contracts, enums, transition maps, and exceptions.
2. `tasks/ACTIVE_PLAN.md`: Marked L10 complete, set L11 active.
3. `LAYA_BUILD_STATE.md`: Synchronized ground truth to 385 tests passing (+ 47 subtests = 432 checks).
4. `HANDOFF.md`: Updated continuation instructions for L11.
5. `END_TO_END_EXECUTION_LOG.md`: Top health dashboard, flowchart, and complete Section 9 engineering log.

---

### 9.4 Verification & Test Evidence

- **L10 Targeted Test Suite (`tests/test_l10_quest.py`)**:
  - `python -m unittest tests/test_l10_quest.py`
  - Output: `Ran 13 tests in 8.452s, OK` (13 passed, 0 failed, 100% pass rate).
  - Verified:
    1. Contract schema validation and rejection of extra unauthorized fields.
    2. Full happy-path lifecycle (`CREATED -> PLANNED -> RUNNING -> AWAITING_VERIFICATION -> COMPLETED`).
    3. Terminal state absorption: attempting to transition out of `FAILED` or `COMPLETED` raises `InvalidStateTransitionError`.
    4. Pause and resume states (`PAUSED_FOR_CONFIRMATION`, `PAUSED_FOR_INPUT`).
    5. Quest OCC conflict detection: stale version update raises `OptimisticLockError`.
    6. Step OCC conflict detection: concurrent step mutation raises `OptimisticLockError`.
    7. Crash & restart recovery: SQLite file on disk closed abruptly mid-run; fresh engine instance reboots and recovers Quest, steps, and receipts with 100% fidelity.
    8. Foreign key blocking of orphan steps and cascade deletion of steps/events on Quest removal.
    9. Multi-threaded concurrent event logging under WAL mode (5 threads, 100 concurrent events, zero locks/deadlocks).
    10. Non-switching boundary: `git diff HEAD omni_agent.py omni_engine/planner.py` = 0 diffs.
- **Full Repository Test Suite (L0–L10 + Foundation Gate + R1–R5 + RV0)**:
  - `python -m unittest discover tests`
  - Output: `Ran 385 tests in 571.884s, OK` (385 passed + 47 subtests = 432 total checks, 0 failures, 0 errors, 2 benign upstream warnings).

---

### 9.5 Checkpoint Completion & Next Phase
- **Checkpoint L10 is Officially PASSED and COMPLETED**.
- **Next Active Checkpoint**: **L11 — Operation Ledger & Exactly-Once Mutation Semantics**.

