# LAYA_BUILD_STATE.md — Current Ground Truth State

**Last Updated**: 2026-09-25T17:48:00+05:30  
**Current Branch**: `laya-autonomous-v2`  
**Active Milestone Goal**: `L14.1 RUNTIME INTEGRITY, DURABILITY & FAILURE ACCOUNTABILITY HARDENING (COMPLETED & VERIFIED) — HARD STOP ENFORCED`  
**Baseline Verified Commit**: `214d33a` (Checkpoint L14.1 Runtime Integrity Hardening on `laya-autonomous-v2`)  
**Last Passing Test Suite**: All 28 test files across L0–L14.1 + Foundation Gate + R1 + R2 + R3 + R4 + R5 + RV0:
`tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`, `tests/test_l2_1_reconciliation.py`, `tests/test_l3_capabilities.py`, `tests/test_l4_providers.py`, `tests/test_l5_decision_fabric.py`, `tests/test_l6a_routing.py`, `tests/test_l7_skills.py`, `tests/test_l6b_skill_routing.py`, `tests/test_l7_5_calibration.py`, `tests/test_l8_arguments.py`, `tests/test_l9_policy.py`, `tests/test_foundation_broker.py`, `tests/test_r1_research.py`, `tests/test_r2_browser.py`, `tests/test_r3_desktop.py`, `tests/test_r4_n8n.py`, `tests/test_r5_developer.py`, `tests/test_rv0_reality_gate.py`, `tests/test_l10_quest.py`, `tests/test_l11_operation_ledger.py`, `tests/test_l12_planner.py`, `tests/test_l13_validator.py`, `tests/test_l14_executor.py`, `tests/test_l14_1_runtime_integrity.py` (**481 automated tests, 47 subtests = 528 total checks passing (100% pass rate)**)  
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
15. **Foundation Gate Milestone Reached (Prerequisite for R1–R5)**:
    - **User Model Sovereignty & Precedence Routing**: Implemented `SystemOneBroker` in `omni_engine/providers/broker.py` governed by strict `ProviderSelectionMode` (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlist enforcement, and task overrides. `USER_LOCKED` strictly prohibits silent provider switches. `USER_PREFERRED` permits fallback only for measurable reasons with mandatory explanatory telemetry (`FallbackReason`).
    - **Hierarchical Two-Level Locking**: Refactored `omni_engine/providers/system1.py` to enforce Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner. Model swaps and evictions exclusively drain all inference permits, completely eliminating swap races and C++ access violations.
    - **Strict English-Only Invariant**: Banned all multilingual checkpoints, tokenizers, and language detection routines (`VALID_LOCAL_MODELS = ("english", "typed-decisions")`).
    - **Debounced Windows RAM Protection**: Telemetry via `psutil` with Windows `ctypes.windll.kernel32.GlobalMemoryStatusEx` fallback. Eviction requires 3 consecutive breaches over >= 5s when idle.
    - **Empirical Concurrency Benchmark**: Concurrency benchmark harness in `omni_engine/decision/concurrency_benchmark.py` measuring levels 1, 2, 4 on CPU. Proven: cold load takes 47.4s / 1.67 GB RAM; warm inference is ~712ms (concurrency 2: 2.79 req/s).
    - **Deterministic Stratified Calibration**: 70/30 stratified partition (72 dev / 31 test) and 10-bin Expected Calibration Error (ECE) metric evaluation harness in `omni_engine/decision/calibration_eval.py`.
    - **Adversarial Diff Review**: **PASS (UNCONDITIONAL)** (Subagent `5e8a88cd-a846-4ef9-b639-22afb9b791c2`).
    - **Comprehensive Test Suite**: Created `tests/test_foundation_broker.py` (27 unit tests, 100% pass rate in 0.047s).
16. **Checkpoint R1 Milestone Reached (Deep Evidence-Grounded Research Engine)**:
    - **ADR & Technology Audit**: Formally adopted Scrapling (0.4.9), adapted Tavily, rejected Crawl4AI (~3GB RAM footprint), and adapted Citation Verifier in `docs/research/ADR_R1_DEEP_RESEARCH.md`.
    - **Typed Evidence Contracts**: Created `omni_engine/contracts/research.py` with `EvidenceItem` (passage-level SHA-256 hash, deterministic `ev_<hash[:10]>`), `ResearchClaim`, `ResearchBudget`, `ResearchTelemetry`, `ResearchDossier`, `EvidenceStance`, and `ClaimVerificationStatus`.
    - **Prompt-Injection Defense**: Created `omni_engine/research/sanitizer.py` with NFKC normalization, zero-width stripping, control character removal, XML tag escaping, and `<untrusted_external_data origin="..." hash="...">` containment framing.
    - **Page Fetcher & Canonicalizer**: Created `omni_engine/research/fetcher.py` with tracking query stripping, domain extraction, and multi-tier fallback (Scrapling -> BS4 -> Mock fixtures).
    - **Deep Research Engine**: Created `omni_engine/research/engine.py` with deterministic facet decomposition (REQ-B1: System 1 text generation forbidden), bounded discovery and crawl loop with `(url, depth)` tuple queuing, 3-gram Jaccard deduplication ($J \ge 0.70$), sequential System 1 relevance scoring ($r \ge 0.45$) and stance classification, mathematical saturation yield stopping ($Y_k \le 0.15$ for 2 rounds), and cryptographic citation verification quarantining unverified citations.
    - **Capability Substrate Integration**: Registered `DEEP_RESEARCH_SPEC` and `build_real_capability_registry()` in `omni_engine/capabilities/` preserving the 23-tool canonical registry invariant. Gated under `PolicyEngine` and `ArgumentResolver`.
    - **Adversarial Diff Review**: **PASS (APPROVED FOR CHECKPOINT R1)** (Subagent `e5f6870e-ea3f-4969-83b9-1e169887f9d4`).
    - **Comprehensive Test Suite**: Created `tests/test_r1_research.py` (18 unit tests, 100% pass rate in 0.012s).
17. **Checkpoint R2 Milestone Reached (Real Persistent Browser Engine)**:
    - **ADR & Technology Audit**: Formally adopted Playwright (1.54.4 Chromium/Edge), persistent profile context (`~/.laya/browser_profile`), indexed action space (`@1..@N`), evidence-based verification, and financial action confirmation gating in `docs/research/ADR_R2_BROWSER_ENGINE.md`.
    - **Typed Browser Contracts**: Created `omni_engine/contracts/browser.py` with `BrowserActionType`, `BrowserElement`, `BrowserSnapshot`, `BrowserActionRequest`, `BrowserActionResult`.
    - **Session & Resource Lifecycle**: Created `omni_engine/browser/session.py` with persistent isolated profile directory, stale singleton lock recovery (`SingletonLock`, `SingletonCookie`, `SingletonSocket`), single page invariant (`max_pages=1`) with popup routing, `atexit` cleanup, and 9 low-memory launch flags.
    - **DOM Action Indexer**: Created `omni_engine/browser/indexer.py` with in-page DOM stamping (`data-laya-idx="N"`), compact dual-key index `@1..@N`, semantic fingerprint extraction, financial element detection, and pre-action staleness verification.
    - **Driver & Evidence Verification**: Created `omni_engine/browser/driver.py` with action dispatch (`NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `SNAPSHOT`, `SCREENSHOT`), pre-execution financial safety gate, and evidence-based verification (`dom_mutated` via `MutationObserver`, `url_changed`, physical `input_value`, `scrollY`).
    - **PolicyEngine Financial Safety Repaired**: Updated `omni_engine/policy/engine.py` Stage 3 to enforce confirmation for `ActionClass.FINANCIAL` and `financial:*` sensitive targets under all autonomy tiers below `WORKFLOW_AUTHORIZED` (including `TRUSTED_OPERATOR`).
    - **Capability Substrate Integration**: Registered `BROWSER_INTERACT_SPEC` (`action_class=ActionClass.EXTERNAL_UPDATE`, `minimum_autonomy_profile=LOCAL_OPERATOR`) and alias `browser.interact` in `build_real_capability_registry()`. Mapped in `ArgumentResolver`.
    - **Adversarial Diff Review**: **PASS (APPROVED FOR CHECKPOINT R2)** (Subagent `6812beb1-7cd5-4555-8417-90c4aa6fc27b`).
    - **Comprehensive Test Suite**: Created `tests/test_r2_browser.py` (15 unit and integration tests, 100% pass rate in 2.70s). Full repository suite: **293/293 passed in 167.37s (+ 47 subtests = 340 total)**.
18. **Checkpoint R3 Milestone Reached (Windows Desktop, App & Local Service Engine)**:
    - **ADR & Technology Audit**: Formally adopted Win32 API (`win32gui`, `win32con`, `win32process`, `win32api`, `ctypes.windll.user32`), `psutil`, `socket`, and `urllib.request` in `docs/research/ADR_R3_WINDOWS_APP_ENGINE.md`.
    - **Typed Desktop Contracts**: Created `omni_engine/contracts/desktop.py` with `WindowBounds`, `WindowState`, `AppWindowInfo`, `AppLaunchResult`, `ServiceHealthStatus`, and `DesktopActionResult`.
    - **Safe Window Activation & Deadlock Defense**: Implemented `AppWindowManager` in `omni_engine/desktop/app_manager.py` checking `ctypes.windll.user32.IsHungAppWindow`, simulating menu key event (`VK_MENU`) for foreground rights, restoring minimized windows via `ShowWindowAsync(SW_RESTORE)`, and polling activation asynchronously.
    - **Process Trampoline Resolution**: Implemented pre-launch baseline HWND diffing (`current_hwnds - baseline_hwnds`) combined with recursive child-tree traversal (`psutil.Process.children(recursive=True)`), returning strongly typed physical receipts (`launcher_pid`, `active_pid`, `hwnd`, `bounds`).
    - **Local Service Health Probing**: Created `LocalServiceProber` in `omni_engine/desktop/service.py` with loopback dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` to prevent `TIME_WAIT` socket buildup, dedicated `ProxyHandler({})` opener to bypass host proxy environment traps, bounded 4KB HTTP reads, and strict timeouts (<=500ms socket, <=1500ms HTTP).
    - **Rule-0 Process Safety Gating**: Expanded `PolicyEngine` Stage 0 to block all critical system processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4) across all desktop terminating capabilities (`kill_process`, `desktop.close_window`, `desktop.kill_process`, `desktop.terminate_app`). Reinforced by intrinsic pre-flight inspection in `AppWindowManager`.
    - **Isolated Input Driver**: Created `WindowsInputDriver` in `omni_engine/desktop/uia_driver.py` with pre-focus verification and non-intrusive `WM_CHAR` character dispatch.
    - **Capability Substrate Integration**: Registered `desktop.launch_app`, `desktop.list_windows`, `desktop.focus_window`, `desktop.close_window`, `desktop.service_health`, `desktop.send_keys`, and dotless aliases in `build_real_capability_registry()`. Mapped in `ArgumentResolver` and `PolicyEngine`.
    - **Adversarial Diff Review**: **PASS (APPROVED FOR CHECKPOINT R3)** (Subagent `286fba8a-36f5-4ab6-b993-ab0eb8ad56f3`).
    - **Comprehensive Test Suite**: Created `tests/test_r3_desktop.py` (21 unit and integration tests, 100% pass rate in 0.953s). Full repository suite: **314/314 passed in 211.05s (+ 47 subtests = 361 total)**.
19. **Checkpoint R4 Milestone Reached (Programmatic n8n Automation Engine)**:
    - **ADR & Technology Audit**: Formally adopted n8n v1 REST API, draft-test-validate workflow lifecycle, zero plaintext secrets invariant, 3-level nested connection schema resolution, and RCE defenses in `docs/research/ADR_R4_N8N_AUTOMATION_ENGINE.md`. Status: **ACCEPTED**.
    - **Typed n8n Contracts**: Created `omni_engine/contracts/n8n.py` with `N8nTriggerType`, `N8nCredentialReference` (`extra="forbid"`), `N8nNode`, `N8nWorkflowSummary`, `N8nWorkflowDetail` (deterministic `compute_hash()`), `N8nWorkflowValidationResult`, `N8nExecutionReceipt`, and `N8nActionResult`.
    - **Multi-Pattern Secret Scrubber**: Implemented `SecretScrubber` in `omni_engine/automation/scrubber.py` with compiled regexes for OpenAI (`sk-`), GitHub (`ghp_`), Bearer/Basic, AWS keys, n8n API keys, private keys, generic K-Vs, and header sanitization while preserving `$json.*` syntax.
    - **DAG Validator & Cycle Detector**: Implemented `N8nWorkflowValidator` in `omni_engine/automation/validator.py` parsing 3-level nested connections (`connections[src]["main"][idx] = [...]`), resolving name/ID bidirectionally, 3-color topological DFS cycle detector, in-degree constraints (`trigger in-degree == 0`, triggers >= 1), reachability analysis, and pre-flight parameter secret scan.
    - **Decoupled Transport**: Implemented `N8nTransport` (ABC), `HttpN8nTransport` (production urllib + `ProxyHandler({})`), and `MockN8nTransport` (in-memory state machine for fast offline tests) in `omni_engine/automation/transport.py`.
    - **n8n Client & Draft Mode Enforcement**: Created `N8nClient` in `omni_engine/automation/client.py` strictly enforcing draft mode (`active=False`) on creation, endpoints for activate/deactivate, execution trigger, and execution polling.
    - **Lifecycle Engine & Gate Triad**: Created `N8nAutomationEngine` in `omni_engine/automation/engine.py` implementing the Draft-Test-Validate lifecycle, Gate Triad enforcement for `activate_workflow` (1: Valid DAG, 2: Successful test run receipt for exact hash, 3: Zero secrets), bounded exponential backoff in `trigger_and_wait` with `"waiting"` state breakout.
    - **PolicyEngine RCE Defense**: Updated `PolicyEngine` to detect high-risk n8n nodes (`executeCommand`, `code`, `ssh`, `readWriteFile`), escalate blast radius to `LOCAL_SYSTEM` / `SECURITY_CRITICAL` and composite risk to >= 0.70. Enforced Rule-0 embedded command scanning on `executeCommand` parameters to block forbidden operations (`git reset --hard`, destructive drive formatting).
    - **Capability Substrate Integration**: Registered 7 canonical n8n specs, adapters, and dotless aliases in `build_real_capability_registry()`, preserving 23-tool canonical registry. Mapped in `ArgumentResolver` and `PolicyEngine`.
    - **Adversarial Diff Review**: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)** (Subagent `901d60b3-003c-4854-9d3c-b76bed8c4f44`).
    - **Comprehensive Test Suite**: Created `tests/test_r4_n8n.py` (25 unit and integration tests, 100% pass rate in 4.72s). Full repository suite: **339/339 passed in 214.99s (+ 47 subtests = 386 total)**.
20. **Checkpoint R5 Milestone Reached (Supervised Developer Agent & Antigravity Engine)**:
    - **ADR & Architecture**: Created `docs/research/ADR_R5_DEVELOPER_AGENT.md` adopting Foreman 5-stage bounded supervision lifecycle, composite SHA-256 state fingerprint thrashing detection, process-tree containment, git workspace confinement, anti-tampering on test suites, fail-fast AST syntax gate, and safe file-by-file reversion primitive. Status: **ACCEPTED**.
    - **Typed Developer Contracts**: Created `omni_engine/contracts/developer.py` with `ConvergenceStatus`, `DevTaskSpec`, `CodeVerificationReceipt`, `DevExecutionReceipt`, and `DevActionResult`.
    - **Deterministic Subprocess Runner**: Implemented `DeterministicSubprocessRunner` in `omni_engine/developer/process_runner.py` with Windows `CREATE_NEW_PROCESS_GROUP`, `communicate(timeout=...)` deadlock defense, `taskkill /F /T /PID` process-tree termination, quote-stripping argument parser, and 50k character output truncation.
    - **Git Workspace Confiner & Safe Reverter**: Implemented `WorkspaceConfiner` in `omni_engine/developer/workspace.py` validating `.git` existence, blocking protected OS roots (`is_protected_path`), verifying path containment via `is_relative_to` and `commonpath`, blocking test file tampering when `allow_test_edits=False`, and performing safe file-by-file revert (`git checkout -- <file>`, `os.remove` for untracked files) strictly avoiding destructive `git reset --hard` or `git clean -fd`.
    - **Decoupled Antigravity Runner**: Implemented `AgyRunner` (ABC), `SubprocessAgyRunner` (local `agy.exe`), and `MockAgyRunner` (fast offline simulation) in `omni_engine/developer/runner.py`.
    - **Foreman Developer Supervisor Engine**: Implemented `DeveloperSupervisorEngine` in `omni_engine/developer/engine.py` coordinating the 5-stage lifecycle: Setup/Baseline -> Mutation -> Syntax Gate -> Test -> Convergence / Reversion.
    - **Capability Substrate Integration**: Registered 4 developer capability specs (`developer.run_task`, `developer.run_tests`, `developer.git_diff`, `developer.inspect_code`) and dotless aliases in `build_real_capability_registry()`, preserving 23-tool canonical registry. Mapped in `ArgumentResolver` and `PolicyEngine`.
    - **Adversarial Diff Review**: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)** (Subagent `fb7ba688-2887-47fa-811d-d25dbe922f53`).
    - **Comprehensive Test Suite**: Created `tests/test_r5_developer.py` (25 unit and integration tests, 100% pass rate in 17.33s). Full repository suite: **364/364 passed in 233.91s (+ 47 subtests = 411 total checks)**.
21. **Checkpoint RV0 Milestone Reached (Live Reality Gate & Documentation Audit)**:
    - **Documentation Invariants Hardened**: `END_TO_END_EXECUTION_LOG.md` made permanent mandatory cumulative engineering record in `AGENTS.md`; System 1 latency reality documented (<35ms on CUDA, ~15.4s on host CPU); strict English-only policy (`DEF-008`).
    - **External Research & ADR-013**: Python 3.12 SQLite PRAGMA dynamics (WAL mode, `autocommit=True` connection initialization prior to PRAGMAs, then `autocommit=False` for explicit transactions); Atomic durable workflow reference analysis; authored `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013) registered in `tasks/DECISIONS.md`.
    - **Rule-0 Dirty Worktree Flaw Remediated**: Identified that `WorkspaceConfiner.safe_revert()` previously destroyed pre-existing uncommitted user work outside task scope. Implemented `capture_baseline_state()` and updated `safe_revert()` to protect user untracked files and uncommitted edits byte-for-byte.
    - **Reality Matrix Verified**: All 6 capability engines verified live (`tests/test_rv0_reality_gate.py`): RV0-A (System 1 Broker sovereignty + English-only rejection), RV0-B (Deep Research SHA-256 evidence hashing & quarantine), RV0-C (Playwright browser session, DOM mutation, physical receipts, financial gate), RV0-D (Desktop window enumeration, loopback probing, Rule-0 OS process defense), RV0-E (n8n draft creation, Gate Triad blocking, secret scrubber), RV0-F (Developer Foreman loop, AST syntax gate, and byte-for-byte mandatory dirty worktree preservation).
    - **Comprehensive Test Suite**: Created `tests/test_rv0_reality_gate.py` (8 tests, 100% pass rate in 513.82s). Full repository suite: **372/372 passed in 820.30s (+ 47 subtests = 419 total checks)**.
22. **Checkpoint L10 Milestone Reached (Persisted SQLite Quest Runtime)**:
    - **Strongly Typed Contracts**: Implemented `QuestStatus`, `StepStatus`, `QuestEventEnum`, `QuestStep`, `QuestEvent`, `Quest` in `omni_engine/contracts/quest.py` using Pydantic v2 (`extra="forbid"`).
    - **Deterministic State Machine & Invariant 6**: Implemented `QuestEngine` in `omni_engine/quest/engine.py` enforcing strict transition matrices (`VALID_QUEST_TRANSITIONS`, `VALID_STEP_TRANSITIONS`). Quests are prevented from skipping directly from `RUNNING` to `COMPLETED`; progression through `AWAITING_VERIFICATION` is strictly required. Terminal states (`COMPLETED`, `FAILED`, `CANCELLED`) are strictly absorbing.
    - **SQLite Persistence & WAL Dynamics**: Implemented thread-safe `QuestStore` in `omni_engine/quest/store.py` with relational schema (`quests`, `quest_steps`, `quest_events`), foreign key cascading, thread-local connections, serialized write lock, and Python 3.12 PRAGMA initialization (`autocommit=True` prior to WAL/synchronous, then `autocommit=False` for explicit transactions).
    - **Optimistic Concurrency Control (OCC)**: Version-based updates (`WHERE quest_id = ? AND version = ?`) on quests and steps detecting stale concurrent writes and raising `OptimisticLockError`.
    - **Crash & Restart Recovery**: Simulated process crash mid-quest with disk-backed SQLite database; reopened in clean process; verified 100% state recovery and active quest discovery (`recover_active_quests()`).
    - **Comprehensive Test Suite**: Created `tests/test_l10_quest.py` (13 unit and integration tests, 100% pass rate in 8.45s). Full repository suite: **385/385 passed in 571.88s (+ 47 subtests = 432 total checks)**.
23. **Checkpoint L11 Milestone Reached (Operation Ledger & Exactly-Once Mutation Semantics)**:
    - **Strongly Typed Operation Contracts**: Implemented `OperationRecord`, `AttemptRecord`, `OperationStatus`, `AttemptStatus` in `omni_engine/contracts/operation.py` using Pydantic v2 (`extra="forbid"`).
    - **Deterministic Deduplication**: Enforced exactly-once mutation semantics via `OperationStore` and `OperationLedger` returning cached physical receipts for re-submitted mutations with identical idempotency keys.
    - **Strict UNKNOWN_COMMIT Protection**: Blocked blind retries upon uncertain timeouts (`OperationCommitUncertainError`) and bounded retry attempts (`MaxAttemptsExceededError`). Enabled real physical evidence reconciliation (`reconcile_operation`).
    - **Python 3.12 Concurrency Resilience**: Eliminated SQLite read lock retention trap by wrapping queries in `try ... finally: conn.rollback()`.
    - **Comprehensive Test Suite**: Created `tests/test_l11_operation_ledger.py` (14 unit/integration tests, 100% pass rate in 0.367s). Full repository suite: **399/399 passed (+ 47 subtests = 446 total checks)**.
24. **Checkpoint L12 Milestone Reached (Structured DAG Planner & Template-First Precedence)**:
    - **Strongly Typed Plan Contracts**: Implemented `Plan`, `PlanStep`, `PlanType` in `omni_engine/contracts/plan.py` enforcing duplicate step rejection, self-dependency rejection, and dangling dependency checks.
    - **Template-First Precedence (Invariant 3)**: Implemented `SkillTemplatePlanner` in `omni_engine/planning/template_planner.py` instantiating DAGs in `<1ms` from canonical `SkillManifest.workflow_template` with dynamic `$inputs.<arg>` parameter substitution.
    - **Generative Fallback with Strict Schema**: Implemented `GenerativePlanner` in `omni_engine/planning/generative_planner.py` parsing structured JSON, stripping markdown code fences, and verifying capability registration.
    - **DAG Topology & Cycle Detection**: Implemented `DAGTopology` in `omni_engine/planning/dag.py` with 3-color DFS cycle detector, Kahn's topological sort, in-degree evaluation, and critical-path depth calculation.
    - **Persisted Quest Integration**: Implemented `attach_to_quest` in `StructuredDAGPlanner` transforming `PlanStep` into `QuestStep`, mapping `ActionClass`, and transitioning Quest from `CREATED` to `PLANNED`.
    - **Comprehensive Test Suite**: Created `tests/test_l12_planner.py` (20 unit tests, 100% pass rate in 6.10s). Full repository suite: **419/419 passed in 964.49s (+ 47 subtests = 466 total checks)**.
25. **Checkpoint L13 Milestone Reached (Deterministic Plan Validator Firewall)**:
    - **Strongly Typed Validation Contracts**: Implemented `ValidationPassName`, `ValidationPassResult`, `PlanValidationReport` in `omni_engine/contracts/validation.py` using Pydantic v2 (`extra="forbid"`).
    - **10-Pass Deterministic Firewall**: Implemented `DeterministicPlanValidator` in `omni_engine/planning/validator.py` executing 10 deterministic passes: (1) DAG Acyclicity, (2) Dependency Existence, (3) Capability Registration, (4) Schema Conformance with two-phase dynamic placeholder checking and causal dependency enforcement, (5) Policy Feasibility blocking hard invariants and deferring dynamic paths, (6) Autonomy Compliance with ADVISOR mutation rejection and rank floor enforcement, (7) Step Count Bounds, (8) Graph Depth Bounds with cycle immunity, (9) Mutation Safety with non-idempotent retry bounding, (10) Resource Budget bounds and step timeout consistency.
    - **Cumulative Diagnostic Reporting**: Full diagnostic reporting evaluating all passes without premature fail-fast truncation.
    - **Authored ADR-016**: `docs/research/ADR_L13_PLAN_VALIDATOR.md` registered in system records.
    - **Comprehensive Test Suite**: Created `tests/test_l13_validator.py` (29 unit tests, 100% pass rate in 6.81s). Full repository suite: **448/448 passed (+ 47 subtests = 495 total checks)**.
26. **Checkpoint L14 Milestone Reached (Deterministic DAG Executor)**:
    - **Single Coordinator Dispatcher**: Implemented `DeterministicDAGExecutor` in `omni_engine/execution/executor.py` coordinating multi-step Kahn DAG execution on persistent SQLite Quests.
    - **Mutation Barrier Lock**: Enforced serialized execution for mutations (`_mutation_lock`) while allowing concurrent execution of independent `READ_ONLY` steps via ThreadPoolExecutor.
    - **Operation Ledger Deduplication**: Routed all mutating capabilities through `OperationLedger` returning cached physical receipts on re-execution.
    - **Pre-Execution Firewall Integration**: Validated plans through `DeterministicPlanValidator` before dispatching steps.
    - **Pause and Resume**: Gated unconfirmed operations with `PAUSED_FOR_CONFIRMATION` and supported resumption via `resume()`.
    - **Comprehensive Test Suite**: Created `tests/test_l14_executor.py` (17 unit tests, 100% pass rate).
27. **Checkpoint L14.1 Milestone Reached (Runtime Integrity, Durability & Failure Accountability Hardening)**:
    - **Failure Accountability Protocol**: Created `tasks/FAILURE_LEDGER.md` capturing all historical defects (`FAIL-HIST-001` through `008`) and audit defects (`FAIL-L14.1-001` through `016`) across all layers.
    - **Batch 1 (AUDIT-04, 05, 06, 07 — State Machine & Persistence Atomicity)**: Atomic multi-statement transactions in `QuestStore` and `OperationStore`; recovered interrupted `READ_ONLY` running steps to `READY`; transitioned uncertain mutations to `StepStatus.AWAITING_RECONCILIATION` and `QuestStatus.PAUSED_FOR_RECONCILIATION` instead of terminal `FAILED`.
    - **Batch 2 (AUDIT-01, 02, 03 — Idempotency & Uncertainty Classification)**: Normalized post-dispatch timeout and network errors into `UNKNOWN_COMMIT` requiring reconciliation; scoped automatic ledger idempotency keys by `quest_id` (`idemp_{quest_id}_{step_id}_{capability_id}_{arg_hash}`) preventing accidental cross-quest collisions; explicitly propagated custom caller idempotency keys into `CapabilityInvocation` and tool handlers.
    - **Batch 3 (AUDIT-08, 09, 10, 11 — Plan Durability & Planner Boundaries)**: Computed deterministic SHA-256 `plan_hash` and `plan_provenance` persisted in `quest.metadata`; added `timeout_s`, `max_attempts`, `can_fail_silently`, and `metadata` to `QuestStep` contract, SQLite schema, and migrations; ensured planners derive `max_attempts=1` when `retry_policy == NEVER` or `idempotency_class == NON_IDEMPOTENT`; enforced `allowed_capabilities` containment boundary in `GenerativePlanner`.
    - **Batch 4 (AUDIT-12, 13, 14, 15, 16 — Resolvers, Resources & Lifecycle)**: Differentiated missing input arguments via `MissingInputError`, pausing steps as `PAUSED` and quest as `PAUSED_FOR_INPUT`, and cleanly resuming with merged user inputs; implemented concurrent resource conflict detection in Pass 9 (`MUTATION_SAFETY`) via transitive ancestor analysis; added canonical resource identity extraction (`DeterministicPlanValidator.extract_resource_identity`); enforced plan timeout budget in Kahn coordinator loop; added deterministic `cancel(quest_id)` transitioning uncompleted steps to `CANCELLED` and emitting `QUEST_CANCELLED`.
    - **Comprehensive Test Suite**: Created `tests/test_l14_1_runtime_integrity.py` (16 unit tests, 100% pass rate in 4.91s). Full repository suite: **481 passed (+ 47 subtests = 528 total checks)**.

---

## 2. Canonical Capability Matrix (23 Canonical Tools + Real Capability Engines)

| Domain | Capability ID | Implementation Function | Blast Radius | Policy Tier | Confirmation | Retry Policy | Idempotency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **web** | `web_search` | `tool_web_search` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **web** | `scrape_url` | `tool_scrape_url_content` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **web** | `http_api` | `tool_http_api_request` | `EXTERNAL_CREATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **web** | `download_file` | `tool_download_file` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **web** | `deep_research` (alias `research.deep`) | `DeepResearchEngine` | `READ_ONLY` / `NONE` | `SAFE_ASSISTANT` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **browser** | `visual_browse` | `tool_visual_browse` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **browser** | `browser_screenshot` | `tool_browser_screenshot` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `NEVER` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **browser** | `browser_interact` (alias `browser.interact`) | `BrowserDriver` | `EXTERNAL_NETWORK` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **os** | `system_diagnostics` | `tool_system_diagnostics` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `list_processes` | `tool_list_processes` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `kill_process` | `tool_kill_process` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `launch_app` | `tool_launch_app` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `desktop_screenshot` | `tool_desktop_screenshot` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `NEVER` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **os** | `clipboard` | `tool_clipboard` | `LOCAL_UPDATE` | `SAFE_ASSISTANT` | `POLICY_CONTROLLED` | `NEVER` | `NATURAL` |
| **os** | `powershell` | `tool_powershell` | `SYSTEM_ACTION` | `TRUSTED_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `ping_test` | `tool_ping_test` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `desktop.launch_app` | `AppWindowManager` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **os** | `desktop.list_windows` | `AppWindowManager` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `desktop.focus_window` | `AppWindowManager` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `NEVER` | `VERIFY_BEFORE_RETRY` | `IDEMPOTENT` |
| **os** | `desktop.close_window` | `AppWindowManager` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **os** | `desktop.service_health` | `LocalServiceProber` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **os** | `desktop.send_keys` | `WindowsInputDriver` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **dev** | `file_read` | `tool_file_read` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `file_write` | `tool_file_write` | `LOCAL_CREATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NATURAL` |
| **dev** | `search_code` | `tool_search_code` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `directory_tree` | `tool_directory_tree` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `run_python` | `tool_run_python` | `SYSTEM_ACTION` | `LOCAL_OPERATOR` | `ALWAYS` | `NEVER` | `NON_IDEMPOTENT` |
| **dev** | `git_status` | `tool_git_status` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `developer.run_task` | `DeveloperSupervisorEngine` | `LOCAL_WORKSPACE` | `TRUSTED_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **dev** | `developer.run_tests` | `DeveloperSupervisorEngine` | `LOCAL_WORKSPACE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NEVER` | `NON_IDEMPOTENT` |
| **dev** | `developer.git_diff` | `DeveloperSupervisorEngine` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **dev** | `developer.inspect_code` | `DeveloperSupervisorEngine` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **automation** | `n8n.list_workflows` | `N8nClient.list_workflows` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **automation** | `n8n.get_workflow` | `N8nClient.get_workflow` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **automation** | `n8n.validate_workflow` | `N8nWorkflowValidator.validate` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **automation** | `n8n.create_workflow` | `N8nAutomationEngine.create_workflow` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **automation** | `n8n.activate_workflow` | `N8nAutomationEngine.activate_workflow` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **automation** | `n8n.trigger_workflow` | `N8nAutomationEngine.trigger_and_wait` | `LOCAL_SYSTEM` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **automation** | `n8n.get_execution_status` | `N8nAutomationEngine.get_execution_receipt` | `NONE` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **data** | `sqlite_exec` | `tool_sqlite_exec` | `LOCAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `VERIFY_BEFORE_RETRY` | `NON_IDEMPOTENT` |
| **data** | `inspect_data` | `tool_inspect_data` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |
| **data** | `safe_math` | `tool_safe_math` | `READ_ONLY` | `ADVISOR` | `NEVER` | `SAFE_READ_RETRY` | `READ_ONLY` |

---

## 3. Test Suite & Health Metrics Breakdown

- **Total Automated Tests**: 465 tests (+ 47 subtests = 512 total checks)
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
  - **L9 Deterministic Policy Engine Tests**: 26 passed
  - **Foundation Gate Broker Tests**: 27 passed
  - **Phase R1 Deep Research Tests**: 18 passed
  - **Phase R2 Real Browser Tests**: 15 passed
  - **Phase R3 Desktop Engine Tests**: 21 passed
  - **Phase R4 n8n Automation Engine Tests**: 25 passed
  - **Phase R5 Developer Agent Tests**: 25 passed
  - **RV0 Reality Gate Tests**: 8 passed
  - **L10 Persisted Quest Runtime Tests**: 13 passed
  - **L11 Operation Ledger Tests**: 14 passed
  - **L12 Structured DAG Planner Tests**: 20 passed
  - **L13 Deterministic Plan Validator Tests**: 29 passed
  - **L14 Deterministic DAG Executor Tests**: 17 passed
  - **L14.1 Runtime Integrity & Durability Tests**: 16 passed
- **Pass Rate**: 100% (481 passed, 0 failed, 0 errors, 47 subtests passed = 528 total checks).
- **Runtime**: ~556s across full repository test suite.

---

## 4. Current Blockers

- **None**. The hardening milestone `L14.1 RUNTIME INTEGRITY, DURABILITY & FAILURE ACCOUNTABILITY HARDENING` is complete, verified, and passing 100% of automated tests.

---

## 5. Completed Milestone & Hard Stop Enforcement

Within roadmap `L14.1 RUNTIME INTEGRITY, DURABILITY & FAILURE ACCOUNTABILITY HARDENING`:
- **Status**: **COMPLETE & FULLY VERIFIED**
- **Hard Stop Boundary**: **STRICTLY ENFORCED**. 0 diffs in `omni_agent.py` and `omni_engine/planner.py`.
- **Invariants Upheld**:
  1. Deterministic Control (Invariant 1): Runtime strictly owns state transitions, dependency execution, confirmation enforcement, mutation identity, and lifecycle state.
  2. Exactly-Once Mutation Semantics (ADR-014): Deduplicated operations return cached physical receipts; blind retries on `UNKNOWN_COMMIT` strictly prohibited; timeout/network partitions classified as `UNKNOWN_COMMIT` requiring reconciliation.
  3. Pre-Execution Firewall (ADR-016): 10 deterministic validation passes verify every plan before execution begins; Pass 9 detects un-ordered concurrent resource conflicts.
  4. Dynamic Argument Resolution (ADR-017): `$inputs.<param>` and `$steps.<step_id>.<path>` resolved deterministically with multi-path navigation and stringified JSON support; missing inputs trigger `PAUSED_FOR_INPUT` rather than terminal failure.
  5. Persistence & Concurrency Integrity: Atomic multi-statement transactions in SQLite (`QuestStore` and `OperationStore`); recovery of interrupted read-only steps; plan timeout budget enforcement; deterministic cancellation lifecycle.
  6. Evidence-Based Completion (Invariant 6): Upon completing all steps, Quest transitions strictly to `AWAITING_VERIFICATION`. It does NOT mark itself `COMPLETED` (L15 Verifier is future work).
- **Next Milestone**: **L15 Completion Verifier & L16 Controlled Replanner** (scheduled for future phase; zero advance code implemented).


