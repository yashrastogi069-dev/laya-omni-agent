# MASTER_PLAN.md — Strategic Migration Roadmap (L0 – L25)

## Overview
This roadmap governs the disciplined transformation of the **LAYA Omni Agent** from an exploratory multi-tool prototype into a production-grade, persistent, low-latency autonomous personal operating system.

Execution is strictly phased. No checkpoint may begin until its predecessor passes all acceptance gates and verification tests.

---

## Phased Checkpoints

### Phase I: Foundation & Truth (L0 – L3)
- [x] **L0 — Repository Truth & Baseline**: Complete codebase audit, file classification, reproducing confirmed defects, establishing baseline test suite (`tests/test_l0_baselines.py`), creating canonical documentation.
- [ ] **L1 — Critical Defect Repair & Regressions**: Fix `safe_math` NameError, remove `System1Router` `[:12]` catalog truncation, synchronize `OmniMemory` JSON schema, prove fixes via regression tests.
- [ ] **L2 — Foundational Typed Contracts**: Define typed data models using Pydantic: `DecisionFrame`, `ToolResult`, `CapabilitySpec`, `ActionClass`, `AutonomyProfile`, and structured error models.
- [ ] **L3 — Canonical Capability Registry + Result Envelope**: Wrap all 23+ tools in `CapabilitySpec` contracts; enforce standard `ToolResult` envelopes with zero uncaught exceptions.

### Phase II: System One Nervous System (L4 – L7)
- [ ] **L4 — System One Provider Abstraction**: Implement `SystemOneProvider` base class with `LayaProvider` (local ModernBERT) and `JevProvider` (optional fallback/benchmark); support model caching and latency profiling.
- [ ] **L5 — DecisionFrame Engine**: Multi-question System 1 evaluation producing intent, task class, urgency, importance, risk, ambiguity, requires_clarification, and requires_plan.
- [ ] **L6 — Hierarchical Capability Routing (Shadow Mode)**: Two-stage routing (Domain → Skill → Capability) with fail-open fallback; log candidate recall telemetry in shadow mode.
- [ ] **L7 — Skills Layer & Initial Workflows**: Define `Skill` abstraction for high-frequency recipes (`system_triage`, `codebase_audit`, `web_research_dossier`, `file_transform`); bypass novel planning for known skills.

### Phase III: Argument Resolution & Safety Policy (L8 – L9)
- [ ] **L8 — Capability Argument Resolver**: Multi-tiered argument resolution (Deterministic Regex/AST → State Extraction → Skill Template → Small Structured Model); eliminate passing raw prompts into tools.
- [ ] **L9 — Action Policy & Autonomy Profiles**: Centralized deterministic policy engine; enforce confirmation gates for destructive actions (`LOCAL_DELETE`, `EXTERNAL_SEND`, `SYSTEM_ACTION`).

### Phase IV: Persistent Quest Engine & DAG Execution (L10 – L16)
- [ ] **L10 — Persisted Quest Engine**: SQLite schema for `Quest`, `QuestStep`, and `OperationExecution`; state survival across restarts and crashes.
- [ ] **L11 — Operation Ledger & Idempotency**: Logical mutation identity (`questId:stepId:capabilityId`); deduplicate side effects and prevent re-execution of completed operations.
- [ ] **L12 — Structured DAG Planner**: Generate structured acyclic plans without execution side effects.
- [ ] **L13 — Plan Validator**: Graph acyclicity checks, argument schema validation, permission checks, depth/budget limits.
- [ ] **L14 — Deterministic DAG Executor**: Parallel execution of independent read-only steps; serialized mutation barriers; step state transitions.
- [ ] **L15 — Verification & Completion Engine**: Deterministic outcome verifiers (file checks, exit codes, process absence, DOM state) + cheap semantic completion validation.
- [ ] **L16 — Controlled Replanner**: Replan only on hard dependency failures; preserve completed step receipts.

### Phase V: Advanced Capabilities & Subsystems (L17 – L21)
- [ ] **L17 — Role-Aware Generative Provider Router**: Swappable model routing for `ARGUMENT_WRITER`, `PLANNER`, `REPLANNER`, `FINALIZER`, and `CODING`.
- [ ] **L18 — Modular Browser Capabilities**: Rebuild Playwright Edge into atomic primitives (`navigate`, `snapshot`, `click`, `type`, `extract`, `screenshot`, `tabs`).
- [ ] **L19 — Memory V2 Architecture**: Segregated storage for Working, Episodic, Semantic, and Procedural memory with verified outcome scores.
- [ ] **L20 — Persistent Automation Engine**: Event-driven triggers (schedule, filesystem events, system thresholds) spawning background Quests.
- [ ] **L21 — Standard MCP Capability Adapter**: Convert Model Context Protocol (MCP) server endpoints into internal `CapabilitySpec` contracts under full policy governance.

### Phase VI: Hardening, Migration & Canary (L22 – L25)
- [ ] **L22 — Expanded Capability Families**: Additional desktop, developer, and data science toolsets.
- [ ] **L23 — Full Evaluation & Hardening**: Run end-to-end evaluation corpus, soak testing, and adversarial prompt injection defenses.
- [ ] **L24 — Canary Default Runtime**: Promote the new Quest DAG engine to default CLI runner.
- [ ] **L25 — Legacy Prototype Deprecation & Cleanup**: Archive legacy prototype files after proven stability period.
