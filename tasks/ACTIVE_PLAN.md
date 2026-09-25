# ACTIVE_PLAN.md — Active Milestone: RV0 Reality Gate → L10–L14 Autonomous Runtime

## Current Active Checkpoint: L14 — Deterministic DAG Executor

- **Milestone Scope**: RV0 → L10 Quest → L11 Operation Ledger → L12 Planner → L13 Validator → L14 Executor.
- **Target Branch**: `laya-autonomous-v2`
- **Baseline Verified Commit**: `aae7de8` (419 automated tests + 47 subtests = 466 checks passing, 0 failures).
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

### Step 5: L11 — Operation Ledger & Exactly-Once Mutation Semantics (COMPLETED)
- [x] Operation Ledger schema: `operations`, `attempts`, `receipts`.
- [x] Strongly typed contracts: `OperationId` (`op_{quest_id}_{step_id}_{capability_id}`), `AttemptId`, `ExternalIdempotencyKey`, `ArgumentFingerprint`.
- [x] Mutation states: `PENDING -> IN_PROGRESS -> COMMITTED -> FAILED -> UNKNOWN_COMMIT`.
- [x] Protection against duplicate execution: deduplicate identical mutations; prevent blind retries on `UNKNOWN_COMMIT`.
- [x] Crash & persistence tests (kill during mutation, restart with pending/uncertain mutation, verify exactly-once execution).
- [x] Concurrency stability under WAL mode with lock inversion elimination (`conn.rollback()` in read `finally`).
- [x] Authored ADR-014 (`docs/research/ADR_L11_OPERATION_LEDGER.md`).
- [x] Full test suite (14 unit/integration tests passing in 0.37s) and verified commit for L11.

### Step 6: L12 — Structured DAG Planner (COMPLETED)
- [x] Strongly typed contracts: `Plan`, `PlanStep`, dependency IDs, argument intent, timeout budget.
- [x] Template-first precedence: Skill workflow templates prioritized before invoking generative planning (<1ms execution).
- [x] Generative planner fallback using strict JSON schema output and markdown fence stripping.
- [x] Bounded graph depth (max 6) and step limits (max 20).
- [x] 3-color DFS cycle detector, Kahn's topological sort, in-degree evaluation, plan depth calculation (`DAGTopology`).
- [x] Authored ADR-015 (`docs/research/ADR_L12_STRUCTURED_DAG_PLANNER.md`).
- [x] Full test suite (20 unit tests in `tests/test_l12_planner.py` passing in 6.10s).

### Step 7: L13 — Deterministic Plan Validator (COMPLETED)
- [x] Strongly typed contracts: `ValidationPassName`, `ValidationPassResult`, `PlanValidationReport` (`extra="forbid"`).
- [x] Plan Validator Firewall: 10 validation passes:
  1. `DAG_ACYCLICITY`: 3-color DFS cycle detector, self-dependency rejection, duplicate step ID detection.
  2. `DEPENDENCY_EXISTENCE`: Zero dangling dependencies across all step definitions.
  3. `CAPABILITY_REGISTRATION`: Verified against canonical 23 tools + real capability engines in `CapabilityRegistry`.
  4. `SCHEMA_CONFORMANCE`: Two-phase schema conformance; causal dependency checking for dynamic references (`$steps.<id>`); type-safe placeholder masking.
  5. `POLICY_FEASIBILITY`: Pre-flight `PolicyEngine` evaluation; blocks hard invariants (`git reset --hard`, protected OS paths); masks dynamic references to prevent false denials.
  6. `AUTONOMY_COMPLIANCE`: Rank floor enforcement; strict rejection of mutating actions under `ADVISOR` autonomy.
  7. `STEP_COUNT_BOUNDS`: `1 <= len(plan.steps) <= max_steps` enforcement.
  8. `GRAPH_DEPTH_BOUNDS`: `1 <= depth <= max_depth` enforcement; cycle-immune depth evaluation.
  9. `MUTATION_SAFETY`: Enforces `max_attempts <= 1` on `NON_IDEMPOTENT` capabilities with `RetryPolicy.NEVER`.
  10. `RESOURCE_BUDGET`: Timeout budget bounds and step-level consistency checks.
- [x] Cumulative diagnostic reporting: reports all 10 passes with zero fail-fast premature truncation.
- [x] Authored ADR-016 (`docs/research/ADR_L13_PLAN_VALIDATOR.md`).
- [x] Full test suite (29 unit tests in `tests/test_l13_validator.py` passing in 6.81s).

### Step 8: L14 — Deterministic DAG Executor (COMPLETED)
- [x] Execution runtime: Pre-execution firewall (`DeterministicPlanValidator`), Kahn-style ready-step computation (in-degree == 0 among uncompleted steps).
- [x] Parallel execution of independent read-only steps via `ThreadPoolExecutor` (`max_parallel_workers=4`).
- [x] Serialized execution of mutation steps protected by strict mutation barrier lock (`_mutation_lock`).
- [x] Exactly-once mutation deduplication via `OperationLedger.register_mutation()`, returning cached receipts on replay.
- [x] In-memory lease registry (`_active_leases`) preventing duplicate concurrent execution of the same quest.
- [x] Dynamic argument resolution (`DynamicResolver`) supporting `$inputs.<key>`, `$steps.<step_id>.<path>`, multi-path `data` vs `output` navigation, stringified JSON parsing, and string interpolation.
- [x] Explicit pauses for user confirmation (`PAUSED_FOR_CONFIRMATION`) with policy confirmation prompts and safe resumption (`resume()`).
- [x] Safe resumption from persistent SQLite state across crashes and process termination.
- [x] Invariant 6 evidence completion boundary: upon step completion, quest transitions strictly to `AWAITING_VERIFICATION` (does not self-proclaim `COMPLETED`).
- [x] Authored ADR-017 (`docs/research/ADR_L14_DETERMINISTIC_DAG_EXECUTOR.md`).
- [x] Full test suite (17 unit and integration tests in `tests/test_l14_executor.py` passing in 7.06s).

### Step 9: Final Multi-Step Milestone Audit & Hard Stop (COMPLETED)
- [x] Run full repository test suite (all checkpoints L0–L14): 465 automated tests + 47 subtests passing across 27 test files.
- [x] Verify 0 diffs on non-switching boundary (`omni_agent.py`, `omni_engine/planner.py` 100% untouched).
- [x] Complete documentation audit and synchronize all canonical `.md` files (`AGENTS.md`, `LAYA_BUILD_STATE.md`, `HANDOFF.md`, `tasks/ACTIVE_PLAN.md`, `tasks/DECISIONS.md`, `END_TO_END_EXECUTION_LOG.md`).
- [x] **ENFORCE HARD STOP AFTER L14**: Zero implementation of L15 (Completion Verifier), L16 (Replanner), Memory V2, or legacy retirement.

