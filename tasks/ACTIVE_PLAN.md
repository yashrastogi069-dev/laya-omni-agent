# ACTIVE_PLAN.md — Active Milestone: RV0 Reality Gate → L10–L14 Autonomous Runtime

## Current Active Checkpoint: L14.2 — Runtime Closure, Adversarial Durability & Evidence Integrity Gate (COMPLETED)

- **Milestone Scope**: RV0 → L10 Quest → L11 Operation Ledger → L12 Planner → L13 Validator → L14 Executor → L14.1 Runtime Hardening → L14.2 Adversarial Durability.
- **Target Branch**: `laya-autonomous-v2`
- **Baseline Verified Commit**: `214d33a` (506 automated tests + 47 subtests = 553 checks passing, 0 failures).
- **Hard Stop Boundary**: **HARD STOP IMMEDIATELY AFTER L14.2**. Do NOT begin L15 Completion Verifier, L16 Replanner, Memory V2, automation scheduling, MCP expansion, canary promotion, or legacy retirement.
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

### Step 10: L14.1 — Runtime Integrity, Durability & Failure Accountability Hardening (COMPLETED)
- [x] **Failure Accountability Ledger**: Created `tasks/FAILURE_LEDGER.md` documenting historical defects `FAIL-HIST-001` through `008` and all 16 audit findings `FAIL-L14.1-001` through `016`.
- [x] **Batch 1 (AUDIT-04, 05, 06, 07)**:
  - Atomic multi-statement SQLite transitions in `QuestStore.transition_quest_atomic()` and `OperationStore.record_attempt_atomic()`.
  - Recovery of interrupted `READ_ONLY` running steps to `READY`.
  - Uncertain mutation transitions to `StepStatus.AWAITING_RECONCILIATION` and `QuestStatus.PAUSED_FOR_RECONCILIATION` rather than terminal `FAILED`.
- [x] **Batch 2 (AUDIT-01, 02, 03)**:
  - Mutation post-dispatch timeout/network error normalization into `UNKNOWN_COMMIT` requiring reconciliation.
  - Scoped automatic ledger idempotency keys by `quest_id` (`idemp_{quest_id}_{step_id}_{capability_id}_{arg_hash}`) preventing cross-quest collision.
  - Explicit propagation of custom idempotency keys into `CapabilityInvocation` and tool implementations.
- [x] **Batch 3 (AUDIT-08, 09, 10, 11)**:
  - Deterministic `plan_hash` and `plan_provenance` computed in `attach_to_quest` and persisted in `quest.metadata`.
  - `timeout_s`, `max_attempts`, `can_fail_silently`, and `metadata` added to `QuestStep` contract, schema, and migrations.
  - Planners derive `max_attempts=1` when `retry_policy == NEVER` or `idempotency_class == NON_IDEMPOTENT`.
  - GenerativePlanner validates synthesized plan steps against `allowed_capabilities` boundary.
- [x] **Batch 4 (AUDIT-12, 13, 14, 15, 16)**:
  - Differentiated missing inputs via `MissingInputError`, pausing step as `PAUSED` and quest as `PAUSED_FOR_INPUT`, and cleanly resuming with merged user inputs.
  - Transitive ancestor calculation and concurrent resource conflict detection in Pass 9 (`MUTATION_SAFETY`).
  - Canonical resource identity extraction (`DeterministicPlanValidator.extract_resource_identity`) normalizing URI schemes.
  - Plan timeout budget enforcement in Kahn coordinator loop (`time.perf_counter() - start_time > timeout_budget_s`).
  - Deterministic `cancel(quest_id)` transitioning uncompleted steps to `CANCELLED` and emitting `QUEST_CANCELLED`.
- [x] **Test Verification & Hard Stop**:
  - Full test suite: 481 automated tests + 47 subtests = 528 checks passing across all 28 test files.
  - Non-switching boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.
  - **HARD STOP STRICTLY ENFORCED**: Zero implementation of L15 (Completion Verifier), L16 (Replanner), Memory V2, or legacy retirement.

### Step 11: L14.2 — Runtime Closure, Adversarial Durability & Evidence Integrity Gate (COMPLETED)
- [x] **LangGraph Durability Research Gate (ADR-019)**:
  - Upstream pattern audit: Durable Checkpointing (ADAPT), Interrupt & Resume (ADAPT), Side-Effect Replay & Idempotency (ADOPT & ENHANCE), State History vs Overwrite (ADOPT), Deterministic Boundaries (REJECT), Framework Installation (PERMANENTLY REJECTED).
  - Authored `docs/research/ADR_L14_2_DURABILITY_LANGGRAPH_RESEARCH.md`.
- [x] **Step-Scoped Operation Identity & Idempotency (L14.2-A)**:
  - Scoped automatic idempotency key: `idem_{quest_id}_{step_id}_{capability_id}_{arg_hash[:16]}`.
  - Logical operation ID: `op_{quest_id}_{step_id}_{capability_id}`.
  - Preserved caller-supplied `custom_idempotency_key` for explicit cross-quest bridging.
- [x] **max_attempts Propagation (L14.2-B)**:
  - Propagated `step.max_attempts` into `operation_ledger.register_mutation(..., max_attempts=step.max_attempts)`.
- [x] **Database-Level CAS Concurrency (L14.2-C)**:
  - Database-level conditional CAS update in `begin_attempt_atomic` with parameterized `MutationState.PENDING.value` and `FAILED.value`.
  - Added unique SQLite composite index: `uq_operation_attempts_op_num ON operation_attempts (operation_id, attempt_number)`.
  - Defined `ConcurrentAttemptConflictError(LedgerError)`.
  - Multi-store concurrent race test with 50 iterations verifying exactly 1 winner and 1 typed conflict loser.
- [x] **Transactional Fault Injection & Rollback (L14.2-D)**:
  - Real SQLite mid-transaction fault injection tests D1 through D6 covering `begin_attempt`, `commit_attempt`, `fail_attempt`, `transition_quest`, `transition_step`, and `attach_plan`.
  - Verified rollback and data consistency on cold database reopening.
- [x] **Attempt & Operation State Consistency (L14.2-E)**:
  - Reordered validation in `commit_attempt_atomic` and `fail_attempt_atomic` to validate aggregate root `operations` first (preventing mutations locked in `UNKNOWN_COMMIT` from being overridden), followed by attempt state verification (`STARTED`).
  - Added `StaleAttemptError(LedgerError)`.
- [x] **Plan Provenance & Tamper Firewall (L14.2-F & G)**:
  - Canonical SHA-256 `Plan.compute_hash()` sorting steps, dependencies, normalizing timeouts and floats.
  - Faithful plan reconstruction in `_reconstruct_plan` preserving `PlanType.GENERATIVE_SYNTHESIZED`, `skill_id`, `goal`, and timeouts.
  - Pre-execution Plan Tamper Firewall in `_execute_internal`: asserts recomputed plan hash matches `quest.metadata["plan_hash"]` or halts with `ExecutionFirewallError`.
- [x] **Non-Decorative Contract Fields (L14.2-H)**:
  - Pass 9 of `DeterministicPlanValidator` strictly rejects `can_fail_silently=True` with explicit deferral message to Checkpoint L16.
  - Step `timeout_s` enforced with `UNKNOWN_COMMIT` on mutation timeout.
- [x] **READ_ONLY Missing Input Clean Pause (L14.2-I)**:
  - Removed duplicate `transition_step(..., StepStatus.PAUSED)` inside `_execute_step()`.
- [x] **Truthful Timeout Hierarchy (L14.2-J)**:
  - Bounded step dispatch; mutation timeout during dispatch marks `UNKNOWN_COMMIT` and pauses for reconciliation.
- [x] **Active Cancellation Protocol (L14.2-K)**:
  - Added active cancellation support in `cancel()` via `_cancellation_events[quest_id].set()` without lease collision.
- [x] **Append-Only Reconciliation History (L14.2-L)**:
  - SQLite table `operation_reconciliations`, `record_reconciliation_atomic()`, and `get_reconciliations()`.
- [x] **Anti-Shallow-Test Rule & Failure Accountability**:
  - Captured reproducible RED failure evidence in `tasks/FAILURE_LEDGER.md` (entries `FAIL-L14.2-001` through `FAIL-L14.2-014`).
  - Created 25 adversarial tests in `tests/test_l14_2_durability.py`.
- [x] **Final Test Suite & Hard Stop**:
  - Full test suite: 506 automated tests + 47 subtests = 553 checks passing across all 27 test files (100% pass rate).
  - Non-switching boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.
  - **HARD STOP STRICTLY ENFORCED**: Zero implementation of L15 (Completion Verifier), L16 (Controlled Replanner), Memory V2, or legacy retirement.



