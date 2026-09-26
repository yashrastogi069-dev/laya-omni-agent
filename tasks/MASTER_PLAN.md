# MASTER_PLAN.md — LAYA Standalone Autonomous Agent Roadmap (L0 – L25)

## 1. Prime Directive & Strategic Vision
**LAYA Omni Agent** is engineered as a **complete standalone autonomous operating agent** that executes real-world objectives independently.

It does not depend on external agent runtimes. It possesses its own:
- **System 1 Fast Decision Nervous System** (<35ms bounded structured decisions via local ModernBERT-large);
- **Persistent Quest Runtime** (SQLite-backed multi-step mission state machine);
- **Skills Layer & Hierarchical Routing** (`Request → Task Class → Domain → Skill → Candidate Set → Capability`);
- **Canonical Capability Registry** (strongly typed `CapabilitySpec` and structured `ToolResult` envelopes);
- **Typed Argument Resolver** (eliminating prompt-as-argument fragility);
- **Deterministic Action Policy & Autonomy Profiles**;
- **Operation Ledger** (logical mutation identity & exactly-once idempotency);
- **Structured DAG Planner & Plan Validator**;
- **Deterministic DAG Executor & Evidence-Based Verifier**;
- **Continuous Memory Engine** (working, episodic, semantic, and procedural experience);
- **Persistent Automation & Event Triggers**.

### Future Compatibility Boundary
Although LAYA operates 100% independently, all module boundaries adhere to clean, standardized interface types:
`AgentRequest`, `AgentResponse`, `DecisionFrame`, `Quest`, `CapabilitySpec`, `ToolResult`, `ExecutionReceipt`, `VerificationResult`, and `AgentEvent`.
This guarantees that future multi-agent coordination or supervisor routing can be achieved cleanly without refactoring LAYA's internal autonomous engine.

---

## 2. Phased Checkpoint Sequence (L0 – L25)

### Phase I: Ground Truth & Reliability Repairs (L0 – L3)
- [x] **L0 — Repository Truth & Baseline**:
  - Full codebase audit of 22 Python files and 5 batch scripts.
  - Identification of production, prototype, demo, and legacy assets.
  - Comprehensive capability inventory (23 tools), routing analysis, memory schema audit.
  - Confirmed defect reproduction in baseline test suite (`tests/test_l0_baselines.py`).
  - Canonical documentation initialization. (Commit `26be41e`).
- [x] **L1 — Critical Local Reliability Repairs & L1.1 Hardening Pass**:
  - Fix `tool_safe_math` NameError via strict `ast.NodeVisitor` arithmetic evaluation with strict resource bounds (length <= 256, AST nodes <= 40, literal <= 1e100, factorial bounds 0 <= n <= 100, exponent bounds abs <= 100).
  - Fix `OmniMemory` schema key mismatch, backward-compatible migration, atomic file persistence, 3-state verification tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`), and corrupted file quarantining (`.corrupt.<timestamp>`).
  - Retain legacy System 1 `[:12]` defect test; label current behavior clearly as legacy prototype constraint.
  - Build test suite (`tests/test_l1_repairs.py`) and verify 100% pass rate across L0 + L1 (22 passed).
- [x] **L2 — Foundational Typed Contracts**:
  - Implement Pydantic data contracts: `DecisionFrame`, `CapabilitySpec`, `ToolResult`, `ActionClass`, `AutonomyProfile`, `ExecutionReceipt`, `VerificationResult`, `AgentRequest`, `AgentResponse`, `AgentEvent`, `TraceContext`.
  - Strict validation (`extra="forbid"`, bounded confidence in `[0.0, 1.0]`, NaN/Inf rejection, mutual exclusivity between success and error).
  - Build test suite (`tests/test_l2_contracts.py`) and verify 100% pass rate across L0 + L1 + L2 (40 passed).
- [x] **L2.1 — Contract & Registry Reconciliation**:
  - Re-establish exact 23-tool source inventory (Web: 4, Browser: 2, OS: 8, Dev: 6, Data: 3) and resolve documentation discrepancies.
  - Complete 19-member `ErrorCode` taxonomy, distinguishing `PERMISSION_DENIED` (external/OS refusal) from `UNAUTHORIZED_ACTION` (internal policy refusal) and representing `UNKNOWN_COMMIT`.
  - Extend `DecisionSignal` with provenance fields (`provider_id`, `model_id`, calibration) and add signals `NEEDS_CLARIFICATION`, `REQUIRES_ACTION`, `NEEDS_GENERATIVE_REASONING`, `ESCALATION_REQUIRED`.
  - Clarify `CapabilitySpec` policy semantics: `minimum_autonomy_profile`, `ConfirmationPolicy`, `RetryPolicy`, `IdempotencyClass`.
  - Adopt `ToolOutcome: SUCCESS, PARTIAL, FAILURE` distinct from physical `VerificationStatus`.
  - Add `CapabilityInvocation` context and extend `TraceContext` with multi-tier causal correlation.
  - Pinned `pydantic>=2.0.0,<3.0.0`.
  - Add test suite (`tests/test_l2_1_reconciliation.py`) bringing repository to 55 passing tests.
- [x] **L3 — Canonical Capability Registry & Phased Boundary Envelopes**:
  - **L3A — Canonical Capability Registry**: Created thread-safe `CapabilityRegistry` registering all 23 source tools with 100% parity.
  - **L3B — Read-Only Capability Result Boundary**: Wrapped read-only capabilities with `ToolResult`, prefix-anchored error interception, and clean process-control propagation (`KeyboardInterrupt`, `SystemExit` never caught).
  - **L3C — Mutation/System Capability Wrappers**: Declarative `CapabilitySpec` contracts with explicit policies for all 12 mutation/system tools.
  - **L3D — Legacy Compatibility**: Fully preserved legacy prototype path; non-switching boundary strictly enforced.
  - Test suite `tests/test_l3_capabilities.py` (25 tests, 23 subtests). Total repository suite: **80 passed in 32.99s**.

### Phase II: System One Nervous System & Hierarchical Routing (L4 – L7)
- [x] **L4 — Dual Provider Foundation (System One & Generative Abstractions)**:
  - Abstract base class `SystemOneProvider` with implementations `LayaProvider` (local ModernBERT-large with RAM-preserving thread lock, single-pass batching, and defensive parsing) and `JevProvider` (graceful non-crashing degradation when unconfigured).
  - Abstract base class `GenerativeProvider` with implementation `OpenRouterProvider` (markdown code fence extraction, structured JSON validation, configurable timeout budget, and zero local RAM footprint).
  - Repaired Windows console encoding flaw (`UnicodeEncodeError` under `cp1252`) in `omni_engine/memory.py`.
  - Comprehensive unit test suite `tests/test_l4_providers.py` (19 tests). Total repository test suite: **99 passed in 123.56s (100% pass rate)**.
- [x] **L5 — Typed DecisionFrame Engine**:
  - Implemented `DecisionFabric` in `omni_engine/decision/fabric.py` evaluating 15 canonical decision signals in a single batched neural pass.
  - Deterministic fast-path (<1ms) for empty/whitespace prompts.
  - Deterministic safety floor overrides for high-risk commands and Invariant 7 reversibility clamping.
  - Ambiguity detection and clarifying question triggers.
  - Candidate domain ranking without violating `extra="forbid"`.
  - Standardized 10-prompt benchmark evaluation corpus and runner in `omni_engine/decision/corpus.py`.
  - Comprehensive unit test suite `tests/test_l5_decision_fabric.py` (12 tests). Total repository test suite: **111 passed in 160.07s (100% pass rate)**.
- [x] **L6A — Hierarchical Capability Routing Foundation**:
  - Foundational multi-tier routing: `Request → Domain → Small Candidate Set → Capability`.
  - Implemented `HierarchicalRouter` in `omni_engine/routing/router.py` and contracts in `omni_engine/contracts/routing.py`.
  - Conversational gating (<5ms) bypassing tool scoring for non-tool queries.
  - Automatic cross-domain pooling for multi-step tasks (`needs_plan=True`).
  - Ambiguity & low-confidence fail-open pooling.
  - Explicit capability synonym pinning (`CAPABILITY_PIN_MAP`) guaranteeing zero tool dropping.
  - "General" domain technical promotion.
  - Elimination of sequential latency cliff: zero-inference short-circuit (<0.2ms) and fast deterministic lexical scoring (<1ms).
  - Elimination of legacy `[:12]` truncation defect (ISSUE-02).
- [x] **L7 — Skills Substrate & Workflow Manifests (COMPLETED)**:
  - Implement reusable `SkillManifest` abstractions for recurring workflows (`web_research`, `inspect_repository`, `diagnose_system`, `file_transform`, `analyze_data`, `browser_information_task`, `perform_git_inspection`).
  - Zero dangling capabilities: all required capabilities verified against `CapabilityRegistry`.
  - Multi-layer safety floors: DAG cycle DFS, phantom dependency prevention, action-class encompassment, high-risk confirmation floor, autonomy ranking floor.
- [x] **L6B — Final Skill-Aware Hierarchical Router (COMPLETED)**:
  - Final integration of multi-tier routing: `Request → Domain → Skill → Small Candidate Set → Capability`.
  - Dynamic candidate floor expansion, cross-domain spec backfill, dual-threshold anti-locking defenses.
  - Test suite `tests/test_l6b_skill_routing.py` (16 tests). Full repository test suite: **165 passed in 148.33s (100% pass rate)**.

### Phase III: Argument Resolution & Safety Policy (L8 – L9) (COMPLETED & VERIFIED)
- [x] **L8 — Typed Capability Argument Resolver**:
  - Deterministic parameter extraction in 0.118 ms across 23 canonical tools with schema validation, alias bridging, and zero-hallucination clarification gating (`CLARIFICATION_PROMPTS`).
  - Unit test suite `tests/test_l8_arguments.py` (26 tests, 100% pass rate).
- [x] **L9 — Deterministic Action Policy & Autonomy Profiles**:
  - Centralized policy engine enforcing autonomy tiers (`ADVISOR`, `SAFE_ASSISTANT`, `LOCAL_OPERATOR`, `TRUSTED_OPERATOR`, `WORKFLOW_AUTHORIZED`).
  - Inviolable Rule-0 hard invariants (`user_confirmed` strictly ignored), boundary-aware user blacklists, and non-disruptive shadow mode simulation.
  - Unit test suite `tests/test_l9_policy.py` (25 tests, 100% pass rate).

### Phase IIIA: Real Capability Engines (R1 – R5) (COMPLETED & VERIFIED)
- [x] **Foundation Gate — System One Broker, Concurrency Correction & Calibration Truth**:
  - User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlist enforcement, and task-level overrides.
  - Two-level hierarchical locking (`_MODEL_LIFECYCLE_LOCK` outer, `_INFERENCE_SEMAPHORE` inner) with exclusive permit draining on swaps/evictions.
  - Strict English-only invariant: banned multilingual checkpoints.
  - Debounced Windows RAM protection: psutil with ctypes fallback, requiring 3 consecutive breaches over >=5s before idle eviction.
  - Empirical concurrency benchmark (concurrency 1 vs 2 vs 4 on CPU): proven cold start is 47.4s / 1.67 GB RAM, warm inference is ~712ms.
  - Deterministic 70/30 stratified calibration partition (72 dev / 31 test) and 10-bin ECE evaluation harness.
  - Unit test suite `tests/test_foundation_broker.py` (27 tests, 100% pass rate). Total repository suite: **259 passed (+ 47 subtests = 306 total)**.
- [x] **R1 — Deep Research Engine (COMPLETED & VERIFIED)**:
  - Multi-source discovery, crawl, extraction, dynamic-page fallback (Scrapling -> BS4), evidence normalization, relevance ranking, gap detection, evidence saturation stop, generative synthesis, and cryptographic citation verification.
- [x] **R2 — Real Browser Engine (COMPLETED & VERIFIED)**:
  - Persistent browser context (`~/.laya/browser_profile`), stale lock recovery, single page invariant (`max_pages=1`), dynamic indexed action space (`@1..@N`), staleness pre-verification, physical evidence receipts (`dom_mutated`, `input_value`, `url_changed`), and hard financial action confirmation gating. 15/15 tests passing.
- [x] **R3 — Windows / App / Local-Service Engine (COMPLETED & VERIFIED)**:
  - ComputerUseDriver (AppWindowManager, WindowsInputDriver, LocalServiceProber), Win32 safe activation and non-blocking foreground rights, process trampoline resolution via HWND baseline diffing and child-tree traversal, dual-stack loopback probing (`127.0.0.1` -> `::1`) with `SO_LINGER`, Rule-0 system process protection, and 100% offline isolated tests. 21/21 tests passing. Total suite: **314 passed**.
- [x] **R4 — n8n Automation Engine (COMPLETED & VERIFIED)**:
  - Official programmatic n8n REST client, draft-test-validate workflow lifecycle, Gate Triad enforcement, 3-level nested connection schema resolution (bidirectional node IDs & names), 3-color topological cycle detector, SecretScrubber (OpenAI, GitHub, AWS, Bearer/Basic, n8n API keys, private keys, headers), Wait node breakout, RCE & Rule-0 policy defense. 25/25 unit tests passing. Full repository suite: **339 passed (+ 47 subtests = 386 total)**.
- [x] **R5 — Developer Agent / Antigravity Engine (COMPLETED & VERIFIED)**:
  - Foreman 5-stage bounded supervision lifecycle, composite SHA-256 state fingerprinting for thrashing/oscillation cycle detection, `DeterministicSubprocessRunner` with Windows `CREATE_NEW_PROCESS_GROUP`, `taskkill /F /T /PID` process-tree cleanup, 50k char output truncation, `WorkspaceConfiner` validating `.git` and preventing path traversal, anti-tampering on test suites (`allow_test_edits=False`), fail-fast AST syntax gate, safe reversion primitive (never `git reset --hard` / `git clean -fd`), decoupled `AgyRunner` ABC (`SubprocessAgyRunner`, `MockAgyRunner`). 25/25 unit tests passing in 17.33s. Full repository suite: **364 passed (+ 47 subtests = 411 total checks)**.
  - Hard Stop Boundary: STOPPED AFTER R5. Ready for Phase IV (L10–L14) in next session.

### Phase IV: Persistent Quest Engine & DAG Execution (L10 – L16) (L10–L14 COMPLETED)
- [x] **L10 — Persisted SQLite Quest Engine (COMPLETED & VERIFIED)**:
  - Relational SQLite schema for `quests`, `quest_steps`, and `quest_events`.
  - State survival across restarts, crashes, and provider timeouts. 13/13 tests passing. Total suite: **385 passed (+ 47 subtests = 432 checks)**.
- [x] **L11 — Operation Ledger & Idempotency (COMPLETED & VERIFIED)**:
  - Logical mutation identity (`quest_id:step_id:capability_id`).
  - Exactly-once execution semantics; deduplicate side effects and prevent re-executing completed operations. 14/14 tests passing. Total suite: **399 passed (+ 47 subtests = 446 checks)**.
- [x] **L12 — Structured DAG Planner (COMPLETED & VERIFIED)**:
  - Multi-step goal decomposition generating validated acyclic dependency graphs (`Plan` / `PlanStep`). 20/20 tests passing. Total suite: **419 passed (+ 47 subtests = 466 checks)**.
- [x] **L13 — Plan Validator (COMPLETED & VERIFIED)**:
  - 10 deterministic validation passes: graph acyclicity verification, schema checks, capability availability, budget, autonomy, mutation safety, and depth limits. 29/29 tests passing. Total suite: **448 passed (+ 47 subtests = 495 checks)**.
- [x] **L14 — Deterministic DAG Executor (COMPLETED & VERIFIED)**:
  - Parallel execution of independent read-only steps; serialized mutation barriers; dynamic argument resolution; OperationLedger integration; policy confirmation pauses; step lifecycle state transitions. 17/17 tests passing. Total suite: **465 passed (+ 47 subtests = 512 checks)**.
- [x] **L14.1 — Runtime Integrity, Durability & Failure Accountability Hardening (COMPLETED & VERIFIED)**:
  - Failure Accountability Ledger (`tasks/FAILURE_LEDGER.md`); atomic SQLite multi-statement mutations; post-dispatch timeout/network error normalization into `UNKNOWN_COMMIT`; quest-scoped idempotency keys; caller idempotency key forwarding; plan hash and provenance persistence; step semantics durability; capability-spec-derived `max_attempts`; generative planner capability boundary; `MissingInputError` and input pause/resume lifecycle; concurrent resource conflict detection in Pass 9; canonical resource identity extraction; plan timeout budget enforcement; deterministic cancellation lifecycle. 16/16 tests passing. Total suite: **481 passed (+ 47 subtests = 528 checks)**.
- [x] **L14.2 — Runtime Closure, Adversarial Durability & Evidence Integrity Gate (COMPLETED & VERIFIED)**:
  - ADR-019 (LangGraph Technology Audit & Durable Patterns); step-scoped operation identity & auto-idempotency key derivation; caller-supplied custom idempotency key cross-quest bridging; `step.max_attempts` propagation; database-level CAS concurrency updates with `UNIQUE(operation_id, attempt_number)` and `ConcurrentAttemptConflictError`; transactional fault injection & cold-restart rollback (D1–D6); aggregate root consistency check before attempt update; canonical SHA-256 `Plan.compute_hash()` and pre-execution plan tamper firewall (`ExecutionFirewallError`); Pass 9 strict rejection of `can_fail_silently=True`; step `timeout_s` enforcement; clean READ_ONLY missing input pause; active cancellation without lease collision; append-only `operation_reconciliations` SQLite audit trail; 25 adversarial tests in `tests/test_l14_2_durability.py`. Total suite: **506 passed (+ 47 subtests = 553 checks)**.
- [ ] **L15 — Evidence-Based Verifier & Completion Engine**:
  - Deterministic outcome checks first (file existence, process checks, DOM state, exit codes) + cheap semantic completion validation.
  - Never report task completion without physical receipts.
- [ ] **L16 — Controlled Replanner**:
  - Replan triggered only on hard dependency failures; preserve completed step receipts.

### Phase V: Advanced Subsystems (L17 – L21)
- [ ] **L17 — Role-Aware Generative Provider Router**:
  - Swappable model routing for `ARGUMENT_WRITER`, `PLANNER`, `REPLANNER`, `FINALIZER`, and `CODING`.
- [ ] **L18 — Modular Browser Capability Rebuild**:
  - Rebuild Playwright Edge into atomic, session-backed primitives (`navigate`, `snapshot`, `click`, `type`, `extract`, `screenshot`, `tabs`).
- [ ] **L19 — Memory V2 (Working, Episodic, Semantic, Procedural)**:
  - Persistent SQLite memory storing verified outcome receipts and skill effectiveness scores.
- [ ] **L20 — Persistent Event-Driven Automation Engine**:
  - Triggers (schedule, file events, system thresholds, webhooks) spawning background Quests under policy governance.
- [ ] **L21 — Standard MCP Capability Adapter**:
  - Convert Model Context Protocol (MCP) server endpoints into internal `CapabilitySpec` contracts.

### Phase VI: Hardening, Migration & Canary (L22 – L25)
- [ ] **L22 — Expanded Capability Families & Evaluation**:
  - Desktop, developer, and data science tool expansion.
- [ ] **L23 — Soak Testing & Adversarial Defenses**:
  - 100-turn soak tests, concurrency validation, and prompt injection defense verification.
- [ ] **L24 — Canary Default Runtime**:
  - Promote the Quest DAG engine to default CLI runner.
- [ ] **L25 — Legacy Prototype Deprecation & Cleanup**:
  - Archive legacy prototype scripts after proven stability period.
