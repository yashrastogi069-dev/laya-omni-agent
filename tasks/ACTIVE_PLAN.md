# ACTIVE_PLAN.md — Active Milestone: RV0 Reality Gate → L10–L14 Autonomous Runtime

## Current Active Checkpoint: L11 — Operation Ledger & Exactly-Once Mutation Semantics

- **Milestone Scope**: RV0 → L10 Quest → L11 Operation Ledger → L12 Planner → L13 Validator → L14 Executor.
- **Target Branch**: `laya-autonomous-v2`
- **Baseline Verified Commit**: `72bc3fc` (385 automated tests + 47 subtests = 432 checks passing, 0 failures, 2 benign upstream warnings).
- **Hard Stop Boundary**: **HARD STOP IMMEDIATELY AFTER L14**. Do NOT begin L15 Completion Verifier, L16 Replanner, Memory V2, automation scheduling, MCP expansion, canary promotion, or legacy retirement.
- **Permanent Invariants**:
  1. `END_TO_END_EXECUTION_LOG.md` is the master cumulative engineering record (must record research, plans, diffs, tests, reviews, repairs, decisions, and documentation updates).
  2. Legacy non-switching boundary: `omni_agent.py` and `omni_engine/planner.py` remain 100% untouched (0 diffs).
  3. Rule-0 Inviolable: Never run `git reset --hard` or `git clean -fd`; safe reversion is file-by-file and strictly preserves uncommitted user modifications.
  4. English-Only LAYA: Multilingual models permanently banned (`DEF-008`).

---

## Phase Breakdown

### Step 1: Pre-Flight Bootstrap & Documentation-Truth Repair (COMPLETED)
- [x] Verify Git status, branch, clean tree (`git status`, `git branch`, `git log`).
- [x] Update `AGENTS.md` with the permanent cumulative engineering record invariant for `END_TO_END_EXECUTION_LOG.md` and hardware-aware System 1 latency / user sovereignty rules.
- [x] Update top dashboard of `END_TO_END_EXECUTION_LOG.md` with commit `48f10b5`, 364 tests (+47 subtests), warning classification, calibration truth, and RV0 active gate.
- [x] Update `tasks/ACTIVE_PLAN.md` to reflect RV0 as active checkpoint.

### Step 2: Mandatory External Research Gate (L10–L14 Foundations) (COMPLETED)
- [x] SQLite in Python 3.12: WAL mode, `PRAGMA synchronous = NORMAL`, `PRAGMA busy_timeout = 5000`, `PRAGMA foreign_keys = ON`, explicit transactions (`autocommit=False` after PRAGMA initialization with `autocommit=True`), connection-per-thread / serialized writer queue.
- [x] Durable Agent / Workflow Architecture (Atomic as REFERENCE ONLY): persisted stage state, artifacts, dependencies, approval gates, worktree isolation.
- [x] Author concise research ADR `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013) and record decisions in `tasks/DECISIONS.md` and `END_TO_END_EXECUTION_LOG.md`.

### Step 3: RV0 — Live Reality Gate Execution (COMPLETED)
- [x] Execute `REALITY_MATRIX` across all real capability engines (`tests/test_rv0_reality_gate.py`):
  - **RV0-A (System 1 Broker)**: Evaluate LAYA vs Jev (if credentials available), verify fallback explanations and User Sovereignty enforcement (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`).
  - **RV0-B (Research Engine)**: Execute 1 live safe web-research query and verify cryptographic citation hashing, relevance ranking, and evidence receipts.
  - **RV0-C (Browser Engine)**: Execute harmless live browser interaction on local fixture/test page and verify physical receipts (`dom_mutated`, `input_value`, `url_changed`).
  - **RV0-D (Windows Desktop Engine)**: Launch Calculator or Notepad, resolve PID/HWND via trampoline resolution, safe close window, verify Rule-0 process defense.
  - **RV0-E (n8n Engine)**: Inspect local n8n instance, run safe draft workflow test, verify Gate Triad and secret scrubber.
  - **RV0-F (Antigravity Developer Engine)**: Execute real `SubprocessAgyRunner` / mock runner + **MANDATORY DIRTY WORKTREE TEST** (pre-existing user edit must survive rollback byte-for-byte; verified 100% passing).
- [x] Fix Rule-0 dirty worktree flaw in `omni_engine/developer/workspace.py` and `engine.py` via `capture_baseline_state()`.
- [x] Run full repository test suite across all 21 test files: 372 tests (+ 47 subtests = 419 checks) all passed in 820s.
- [x] Log complete evidence in `END_TO_END_EXECUTION_LOG.md`.

### Step 4: L10 — Persisted SQLite Quest Runtime (COMPLETED)
- [x] SQLite schema: `quests`, `quest_steps`, `quest_events`.
- [x] Strong Pydantic contracts: `Quest`, `QuestStep`, `QuestEvent`, `QuestStatus`, `StepStatus`.
- [x] State transitions: `CREATED -> PLANNED -> RUNNING -> PAUSED -> AWAITING_VERIFICATION -> COMPLETED / FAILED / CANCELLED`.
- [x] Optimistic concurrency control (`version` counter), WAL mode, connection management.
- [x] Crash & recovery test harness (Tests A–E: restart mid-quest, foreign key enforcement, thread concurrency, OCC version conflict).
- [x] Full test suite (13 unit/integration tests passing in 8.45s) and verified commit for L10.

### Step 5: L11 — Operation Ledger & Exactly-Once Mutation Semantics (ACTIVE)
- [ ] Operation Ledger schema: `operations`, `attempts`, `receipts`.
- [ ] Strongly typed contracts: `OperationId` (`quest_id:step_id:capability_id`), `AttemptId`, `ExternalIdempotencyKey`, `ArgumentFingerprint`.
- [ ] Mutation states: `PENDING -> IN_PROGRESS -> COMMITTED -> FAILED -> UNKNOWN_COMMIT`.
- [ ] Protection against duplicate execution: deduplicate identical mutations; prevent blind retries on `UNKNOWN_COMMIT`.
- [ ] Crash tests 1–6 (kill during mutation, restart with pending mutation, verify exactly-once execution).
- [ ] Full test suite and separate git commit for L11.

### Step 6: L12 — Structured DAG Planner
- [ ] Strongly typed contracts: `Plan`, `PlanStep`, dependency IDs, argument intent, timeout budget.
- [ ] Template-first precedence: Skill workflow templates prioritized before invoking generative planning.
- [ ] Generative planner fallback using strict JSON schema output.
- [ ] Bounded graph depth and step limits.
- [ ] Full test suite and separate git commit for L12.

### Step 7: L13 — Deterministic Plan Validator
- [ ] Plan Validator Firewall: 10 validation passes:
  1. DAG acyclicity (topological sort / 3-color DFS).
  2. Dependency existence (no dangling step IDs).
  3. Capability registration (all referenced capabilities exist in registry).
  4. Capability schema conformance (arguments match CapabilitySpec).
  5. Policy feasibility (no hard-denied operations or protected paths).
  6. Autonomy profile compliance.
  7. Step limit bounds ([1, max_steps]).
  8. Graph depth bounds ([1, max_depth]).
  9. Idempotency and mutation safety verification.
  10. Resource & budget constraint checks.
- [ ] Adversarial invalid plan test corpus (cycles, self-loops, dangling refs, unauthorized mutations, schema mismatches).
- [ ] Full test suite and separate git commit for L13.

### Step 8: L14 — Deterministic DAG Executor
- [ ] Execution runtime: scheduling firewall, ready-step computation (in-degree == 0 among uncompleted steps).
- [ ] Parallel execution of independent read-only steps; serialized execution of mutation steps.
- [ ] Resource locking & concurrency limits.
- [ ] Explicit pauses for user confirmation (`PAUSED_FOR_CONFIRMATION`) and clarifying input (`PAUSED_FOR_INPUT`).
- [ ] Safe resumption from persistent SQLite state.
- [ ] Full test suite and separate git commit for L14.

### Step 9: Final Multi-Step Milestone Audit & Hard Stop
- [ ] Run full repository test suite (all checkpoints L0–L14).
- [ ] Verify 0 diffs on non-switching boundary (`omni_agent.py`, `omni_engine/planner.py`).
- [ ] Complete documentation audit and synchronize all canonical `.md` files.
- [ ] **ENFORCE HARD STOP AFTER L14**.
