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
  - Standardize error codes (`INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`, `CONFIRMATION_REJECTED`, `TIMEOUT`, `NETWORK_ERROR`, `PROCESS_FAILED`, `RATE_LIMITED`, `SCHEMA_VIOLATION`, `UNAUTHORIZED_ACTION`, `UNKNOWN_COMMIT`).
  - Strict validation (`extra="forbid"`, bounded confidence in `[0.0, 1.0]`, NaN/Inf rejection, mutual exclusivity between success and error).
  - Build test suite (`tests/test_l2_contracts.py`) and verify 100% pass rate across L0 + L1 + L2 (40 passed).
- [ ] **L3 — Canonical Capability Registry & ToolResult Envelopes**:
  - Wrap all existing 23 tools in `CapabilitySpec` contracts with typed schemas.
  - Enforce `ToolResult` return envelopes across all tools with zero uncaught exceptions.

### Phase II: System One Nervous System & Hierarchical Routing (L4 – L7)
- [ ] **L4 — Dual Provider Foundation (System One & Generative Abstractions)**:
  - Abstract base class `SystemOneProvider` with implementations `LayaProvider` (local ModernBERT-large) and `JevProvider` (TypeSafe cloud fallback/benchmark).
  - Abstract base class `GenerativeProvider` with initial OpenRouter / local LLM interfaces, establishing provider decoupling so downstream planners (L12+) and argument synthesis engines (L8+) never hardcode a specific vendor or model.
  - Add latency profiling, provider health tracking, and model lifecycle management across both provider classes.
- [ ] **L5 — Typed DecisionFrame Engine**:
  - Evaluate multi-dimensional signals: `intent`, `task_class`, `urgency`, `importance`, `risk`, `ambiguity`, `requires_clarification`, `requires_action`, `requires_tools`, `requires_plan`, `requires_generative_reasoning`.
  - Calibrated confidence and probability distributions per decision.
- [ ] **L6 — Hierarchical Capability Routing**:
  - Replace flat tool catalog slicing with multi-tier routing: `Request → Domain → Skill → Small Candidate Set → Capability`.
  - Dynamic candidate pruning with fail-open fallback (broaden pool or escalate if uncertain).
- [ ] **L7 — Skills Layer & Workflow Manifests**:
  - Implement reusable `Skill` abstractions for recurring workflows (`system_triage`, `codebase_audit`, `web_research_dossier`, `file_transform`).
  - System 1 routes to known skills before falling back to novel generative planning.

### Phase III: Argument Resolution & Safety Policy (L8 – L9)
- [ ] **L8 — Typed Capability Argument Resolver**:
  - Multi-tier argument resolution: Deterministic regex/AST → Conversation state → Skill template → Small structured model.
  - Strict validation against capability input schemas before dispatch.
- [ ] **L9 — Deterministic Action Policy & Autonomy Profiles**:
  - Centralized policy engine enforcing autonomy tiers (`ADVISOR`, `SAFE_ASSISTANT`, `LOCAL_OPERATOR`, `TRUSTED_OPERATOR`, `WORKFLOW_AUTHORIZED`).
  - Strict confirmation gates for destructive actions (`LOCAL_DELETE`, `EXTERNAL_SEND`, `SYSTEM_ACTION`).

### Phase IV: Persistent Quest Engine & DAG Execution (L10 – L16)
- [ ] **L10 — Persisted SQLite Quest Engine**:
  - Relational SQLite schema for `Quest`, `QuestStep`, and `OperationExecution`.
  - State survival across restarts, crashes, and provider timeouts.
- [ ] **L11 — Operation Ledger & Idempotency**:
  - Logical mutation identity (`questId:stepId:capabilityId`).
  - Exactly-once execution semantics; deduplicate side effects and prevent re-executing completed operations.
- [ ] **L12 — Structured DAG Planner**:
  - Multi-step goal decomposition generating validated acyclic dependency graphs (`Plan` / `PlanStep`).
- [ ] **L13 — Plan Validator**:
  - Graph acyclicity verification, schema checks, capability availability, budget, and depth limits.
- [ ] **L14 — Deterministic DAG Executor**:
  - Parallel execution of independent read-only steps; serialized mutation barriers; step lifecycle state transitions.
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
