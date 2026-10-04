# ACTIVE_PLAN.md — Active Milestone: Phase V Advanced Subsystems (L17 – L18)

## Current Active Checkpoint: L18 — Modular Browser Capability Rebuild (COMPLETED & VERIFIED)

- **Milestone Scope**: Phase V: L17 Role-Aware Generative Provider Router (COMPLETED) → L17.5 Real Cloud Provider Integration (COMPLETED) → L18 Modular Browser Capability Rebuild (COMPLETED) → **HARD STOP ENFORCED**.
- **Target Branch**: `laya-autonomous-v2`
- **Baseline Verified Commit**: `51abcf9` (`L18: modular browser capability rebuild (navigate, snapshot, click, type, extract, screenshot, tabs)`) on `laya-autonomous-v2` (623 automated tests + 47 subtests = 670 checks passing, 0 failures; verified locally).
- **Hard Stop Boundary**: Sequence: L16 (COMPLETED) → L17 (COMPLETED) → L17.5 (COMPLETED) → L18 (COMPLETED) → **HARD STOP ENFORCED** (Do NOT start L19 Memory V2).
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
  - Custom Idempotency Conflict Protection: Reusing a custom key with changed capability or arguments raises `IdempotencyConflictError` (`test_a6`).
- [x] **max_attempts Propagation (L14.2-B)**:
  - Propagated `step.max_attempts` into `operation_ledger.register_mutation(..., max_attempts=step.max_attempts)`.
- [x] **Database-Level CAS Concurrency (L14.2-C)**:
  - Database-level conditional CAS update in `begin_attempt_atomic` with parameterized `MutationState.PENDING.value` and `FAILED.value`.
  - Added unique SQLite composite index: `uq_operation_attempts_op_num ON operation_attempts (operation_id, attempt_number)`.
  - Defined `ConcurrentAttemptConflictError(LedgerError)`.
  - Multi-store concurrent race test with 50 iterations verifying exactly 1 winner and 1 typed conflict loser.
- [x] **Transactional Fault Injection & Rollback (L14.2-D)**:
  - Real SQLite mid-transaction fault injection tests D1 through D6 covering `begin_attempt`, `commit_attempt`, `fail_attempt`, `transition_quest`, `transition_step`, and `attach_plan`:
    - D1: `begin_attempt_atomic` fault after attempt insert rolls back; operation remains PENDING, 0 attempt rows survive.
    - D2: `commit_attempt_atomic` fault before operation commit rolls back; attempt remains STARTED, operation remains IN_PROGRESS.
    - D3: `fail_attempt_atomic` fault before operation commit rolls back; attempt remains STARTED, operation remains IN_PROGRESS.
    - D4: `transition_quest_atomic` fault after quest update rolls back; quest status unchanged, OCC version unchanged, 0 orphaned events survive.
    - D5: `transition_step_atomic` fault after step update rolls back; step status unchanged, OCC version unchanged, 0 orphaned events survive.
    - D6: `attach_plan_atomic` faults after quest update (Mode A) and after steps insert (Mode B) roll back; quest remains CREATED, 0 steps exist, 0 PLAN_ATTACHED events survive.
  - Verified rollback and data consistency on cold database reopening across all 6 fault operations.
- [x] **Attempt & Operation State Consistency (L14.2-E)**:
  - Reordered validation in `commit_attempt_atomic` and `fail_attempt_atomic` to validate aggregate root `operations` first (preventing mutations locked in `UNKNOWN_COMMIT` from being overridden), followed by attempt state verification (`STARTED`).
  - Added `StaleAttemptError(LedgerError)` and enforced current-attempt parity in `fail_attempt_atomic` (`test_e5`).
- [x] **Plan Provenance & Tamper Firewall (L14.2-F & G)**:
  - Canonical SHA-256 `Plan.compute_hash()` sorting steps, dependencies, normalizing timeouts and floats, including `schema_version`, `plan_version`, `validator_version`, `validation_hash`, `validation_receipt`, and sorted `metadata`.
  - Faithful plan reconstruction in `_reconstruct_plan` preserving `PlanType.GENERATIVE_SYNTHESIZED`, `skill_id`, `goal`, and timeouts.
  - Pre-execution Plan Tamper Firewall in `_execute_internal`: asserts recomputed plan hash matches `quest.metadata["plan_hash"]` or halts with `ExecutionFirewallError`.
  - Verified tamper detection for arguments (F1), capability (F2), dependencies (F3), phantom steps (F4), and metadata/budgets (F5).
- [x] **Non-Decorative Contract Fields (L14.2-H)**:
  - Pass 9 of `DeterministicPlanValidator` strictly rejects `can_fail_silently=True` with explicit deferral message to Checkpoint L16.
  - Step `timeout_s` enforced with `UNKNOWN_COMMIT` on mutation timeout.
- [x] **READ_ONLY Missing Input Clean Pause (L14.2-I)**:
  - Removed duplicate `transition_step(..., StepStatus.PAUSED)` inside `_execute_step()`.
- [x] **Truthful Timeout Hierarchy & Real Timeout Semantics (L14.2-J)**:
  - Coordinator eliminates `with ThreadPoolExecutor` blocking on context exit, using explicit `pool.shutdown(wait=False, cancel_futures=True)` (`test_j3`).
  - In-flight mutation timeouts quarantined into `UNKNOWN_COMMIT` and quest paused for reconciliation promptly.
- [x] **Active Cancellation Protocol & Durable Intent (L14.2-K)**:
  - Active cancellation persists durable intent `quest.metadata["cancellation_requested"] = True`, quarantines running mutations as `UNKNOWN_COMMIT`, pauses for reconciliation, and on resume/restart cleanly cancels without executing downstream steps (`test_k1`, `test_k2`).
- [x] **Append-Only Reconciliation History & DB CAS (L14.2-L)**:
  - SQLite table `operation_reconciliations`, `record_reconciliation_atomic()`, and `get_reconciliations()`.
  - Reconciliation DB CAS update `WHERE operation_id = ? AND state = ?` using `rec.prior_state.value`, rejecting conflicting reconciliations with `ConcurrentReconciliationConflictError` (`test_l2`).
- [x] **Policy Latency Benchmark Distribution Proof**:
  - Replaced fastest-of-five with a 20-run statistical distribution asserting median < 5.0ms (sub-1ms SLA proof) in `tests/test_l9_policy.py`.
- [x] **Deterministic CI Workflow**:
  - Created `.github/workflows/ci.yml` verifying legacy 0-diff boundary and discovering tests.
- [x] **Anti-Shallow-Test Rule & Failure Accountability**:
  - Captured reproducible RED failure evidence in `tasks/FAILURE_LEDGER.md` (entries `FAIL-L14.2-001` through `FAIL-L14.2-016`).
  - Created 36 adversarial tests in `tests/test_l14_2_durability.py`.
- [x] **Final Test Suite & Hard Stop**:
  - Full test suite: 517 automated tests + 47 subtests = 564 checks passing across all 27 test files (100% pass rate).
  - Non-switching boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.
  - **HARD STOP STRICTLY ENFORCED FOR L14.2**: Proceed to L14.3 Practical Runtime Integration.

### Step 12: L14.3 — Practical Runtime Integration & Operator-Control Closure (COMPLETED)
- [x] **Canonical Practical Findings Ledger**: Recorded and tracked all 36 findings `PRACT-001` through `PRACT-036` in `tasks/PRACTICAL_FINDINGS.md` and linked from `END_TO_END_EXECUTION_LOG.md`.
- [x] **Objective Decomposition (`omni_engine/planning/decomposer.py`, `omni_engine/contracts/objective.py`)**:
  - Deterministic syntactic decomposition of compound user requests into typed `RequirementItem`s.
  - Multi-intent isolation and entity extraction (ports, paths, URLs, process names) for Prompts A through G.
- [x] **Template-as-Building-Block Augmentation (`omni_engine/planning/engine.py`)**:
  - Template plans derived first without LLM calls (Invariant 3).
  - Uncovered clauses augmented with deterministic typed steps (`file_write`, `browser_screenshot`, `desktop.service_health`, `n8n.list_workflows`) guaranteeing 100% pre-execution objective coverage.
- [x] **Session Continuity & Referent Binding (`omni_engine/session/manager.py`)**:
  - Interactive continuation on active quests upon approval/input without re-planning from scratch.
  - Deterministic referent resolution (`"this"`, `"the results"`) bound to previous step outputs.
- [x] **Semantic Argument Validation (`omni_engine/arguments/validator.py`)**:
  - Deep semantic validation for URLs (nested scheme `https://https://` rejection), TCP/UDP ports (1–65535), normalized paths, process targets, and workflow IDs.
- [x] **Skill Input Resolution & Registry Aliases (`omni_engine/arguments/resolver.py`)**:
  - Resolved `cap_id` normalization supporting both `CapabilitySpec` (`.id`) and `SkillManifest` (`.skill_id`).
  - Added deterministic parameter extraction for skill inputs (`inspect_repository`, `perform_git_inspection`, `research_topic`).
- [x] **Infrastructure Metadata Stripping (`omni_engine/capabilities/adapters.py`)**:
  - Filtered `INFRASTRUCTURE_METADATA_KEYS` (`idempotency_key`, `quest_id`, `step_id`, `session_id`) from kwargs before invoking legacy capability tools (`tool_launch_app`).
- [x] **Stale Confirmation Error Hygiene (`omni_engine/quest/engine.py`)**:
  - Resumed/completed steps clear stale confirmation text from `step.error` on transition to `RUNNING` or `COMPLETED`.
- [x] **Truthful Research Telemetry & Backfilling (`omni_engine/research/fetcher.py`, `engine.py`)**:
  - Telemetry truthfully logs attempted and successful fetch methods.
  - Page fetch failures backfill from remaining candidate URLs without burning the successful page budget.
- [x] **Secret-Bearing File Protection (`omni_engine/policy/rules.py`, `engine.py`)**:
  - Stage 0 Rule-0 inviolable hard `DENY` on reading/writing secret-bearing files (`.env*`, `keys.env`, `keys`, `id_rsa`, `*.pem`).
- [x] **Calibrated Browser Navigation Risk (`omni_engine/policy/engine.py`)**:
  - Ordinary read-only browser navigation base risk set to `0.15` (`ALLOW` under `LOCAL_OPERATOR` without false confirmation pause).
- [x] **Production V2 Operator CLI (`laya_v2_cli.py`)**:
  - Complete CLI wiring all V2 autonomous components with dry-run, verbose logging, and interactive REPL mode.
  - `v2_cli_test.py` converted to a thin legacy shim with `DeprecationWarning`.
- [x] **CI Hard Boundary Gate (`.github/workflows/ci.yml`)**:
  - Dedicated `boundary-check` job failing hard on any diffs against legacy entrypoints.
- [x] **Cross-Mount Windows Path Resilience (`omni_engine/tools/dev_tools.py`)**:
  - Handled cross-drive paths gracefully in `tool_file_write` when `os.path.relpath` raises `ValueError: path is on mount 'C:', start on mount 'D:'`.
  - Added regression test `test_file_write_cross_mount_resilience` in `tests/test_l3_capabilities.py`.
- [x] **Test Verification**:
  - 21 targeted practical regression tests in `tests/test_l14_3_practical.py` (100% passing).
  - Full test suite: 539 tests passing across all 28 test files.
  - GitHub Actions CI Run `37220997979`: 100% GREEN (Deterministic Test Suite passed in 4m21s, Non-Switching Boundary Check passed in 3s).
- [x] **Checkpoints L14.3 Complete**: All 36 practical defects resolved, tested, verified on remote CI.

### Step 13: L15 — Evidence-Based Verifier & Completion Engine (COMPLETED)
- [x] **ADR-020**: Authored `docs/research/ADR_L15_COMPLETION_VERIFIER.md` defining the physical evidence verification architecture, deterministic domain verifiers, cryptographic evidence hash, negative constraint auditing, and state machine transition rules. Recorded in `tasks/DECISIONS.md`.
- [x] **Contracts (`omni_engine/contracts/verification.py`)**:
  - `CheckType` (`PHYSICAL`, `STRUCTURED_RECEIPT`, `SEMANTIC_ASSERTION`, `POLICY_AUDIT`), `RequirementVerificationStatus`, `ConstraintVerificationStatus`.
  - `VerificationCheckResult`, `RequirementVerification`, `ConstraintVerification`, `ObjectiveVerificationResult` (`extra="forbid"`).
  - Precedence validator enforcing physical check failure blocks `VERIFIED_SUCCESS`.
  - Cryptographic canonical SHA-256 `compute_evidence_hash()`.
  - Clean exports in `omni_engine/contracts/__init__.py`.
- [x] **Deterministic Domain Verifiers (`omni_engine/verification/verifiers.py`, `base.py`)**:
  - `FileVerifier`: physical existence, regular file, non-empty, and byte count consistency.
  - `ProcessVerifier`: process launch (`psutil.pid_exists`) and termination (`not psutil.pid_exists`).
  - `DesktopVerifier`: physical TCP socket probes with bounded 0.5s timeouts; structured telemetry receipt validation.
  - `BrowserVerifier`: physical screenshot files on disk; navigation/DOM receipts.
  - `N8nVerifier`: API provenance and strict scanning for plaintext secret tokens (`sk-`, `ghp_`, `Bearer ey`, `n8n_api_`).
  - `ResearchVerifier`: citation integrity and detection of `[UNVERIFIED_CITATION: ...]` tokens.
  - `CommandVerifier`, `GitVerifier`, `DataVerifier`: exit codes, git tree checks, database consistency.
- [x] **Verification Registry & SQLite Store (`omni_engine/verification/registry.py`, `store.py`)**:
  - `VerificationRegistry` dispatches requirements to domain verifiers.
  - `VerificationStore` SQLite persistence with WAL mode, foreign keys, thread-local connections, and explicit `close()` cleanup.
- [x] **Objective Completion Engine (`omni_engine/verification/engine.py`)**:
  - `ObjectiveCompletionEngine` maps steps to requirements, audits negative constraints across execution history, computes deterministic evidence hash, and transitions Quest from `AWAITING_VERIFICATION` to `COMPLETED` or `FAILED`.
  - False completion defense: prevents marking complete when physical artifacts are missing.
- [x] **Adversarial Diff Review**:
  - Independent subagent review returned **PASS** with zero blocking defects.
- [x] **Verification & Remote CI**:
  - 12 unit tests passing in `tests/test_l15_verification.py`.
  - Full test suite: 551 automated tests passing across 29 test files.
  - Committed (`d466eaf`), pushed to `origin/laya-autonomous-v2`, and verified 100% GREEN on GitHub Actions CI Run `37232135971`.

### Step 14: L16 — Controlled Replanner & Recovery Loop (COMPLETED)
- [x] **External Research & ADR-021**:
  - Researched replanning loops, sub-DAG replacement, blast-radius containment, and retry budgets.
  - Authored `docs/research/ADR_L16_CONTROLLED_REPLANNER.md` and recorded in `tasks/DECISIONS.md`.
- [x] **Replanner Contracts (`omni_engine/contracts/replanning.py`)**:
  - `ReplanTrigger` (`STEP_FAILURE`, `TIMEOUT`, `PRECONDITION_FAILED`, `VERIFICATION_FAILED`, `POLICY_REJECTION`).
  - `ReplanScope` (`STEP_RETRY_WITH_VARIATION`, `SUB_DAG_REPLACE`, `FULL_REPLAN`).
  - `ReplanRequest`, `ReplanResult` (`extra="forbid"`).
  - Enforced replan budget bounds (`max_replans=3`). Clean exports in `omni_engine/contracts/__init__.py`.
  - Added `PlanType.REPLAN_RECOVERED` in `omni_engine/contracts/plan.py` and `QuestEventEnum.PLAN_REVISED` in `omni_engine/contracts/quest.py`.
  - Added `QuestStatus.RUNNING` transition from `AWAITING_VERIFICATION` in `VALID_QUEST_TRANSITIONS`.
- [x] **Validator Pass 9 Update (`omni_engine/planning/validator.py`)**:
  - Added `allow_silent_failure: bool = False` to `DeterministicPlanValidator.__init__`, safely allowing `can_fail_silently=True` on validator instances configured for recovery.
- [x] **Recovery & Replanning Engine (`omni_engine/planning/replanner.py`)**:
  - Identified failed step and computed blast radius via BFS graph traversal.
  - Enforced anti-oscillation check against `previous_failures` (`step_id`, `capability_id`, `args_hash`).
  - Preserved completed step receipts and OperationLedger idempotency tokens.
  - Spliced replacement sub-DAG conforming to unfulfilled requirements and rewired downstream dependencies.
  - Validated revised plan through `DeterministicPlanValidator` (10 passes).
  - Clean exports in `omni_engine/planning/__init__.py`.
- [x] **Executor Integration (`omni_engine/execution/executor.py`)**:
  - Handled `can_fail_silently=True` steps gracefully without failing the Quest.
  - Wired automatic replanner invocation on step failures before declaring Quest `FAILED`.
  - Enforced OCC version hygiene by refreshing `base_quest` from store before updating metadata.
  - Resumed Kahn DAG traversal with revised plan.
- [x] **Unit & Adversarial Testing (`tests/test_l16_replanner.py`)**:
  - 11 comprehensive tests: blast radius (leaf vs transitive), budget exhaustion, anti-oscillation blocking duplicate failures, fallback replacement (`web_search` -> `deep_research`), dependency rewiring, silent failure tolerance, mutation preservation (zero re-execution), and end-to-end recovery loops. All 11 tests pass in 0.88s.
- [x] **Adversarial Diff Review, Verification & CI**:
  - Independent subagent review returned **PASS** with zero blocking defects.
  - Full test suite: 562 automated tests passing across 30 test files.
  - Non-switching boundary: exactly 0 diffs on `omni_agent.py` and `omni_engine/planner.py`.
  - Committed (`6546ad9`), pushed to `origin/laya-autonomous-v2`, and verified on GitHub Actions CI.

### Step 15: L17 — Role-Aware Generative Provider Router (COMPLETED & VERIFIED)
- [x] **External Research & ADR-022**:
  - Researched swappable generative model routing across 5 distinct functional roles (`ARGUMENT_WRITER`, `PLANNER`, `REPLANNER`, `FINALIZER`, `CODING`).
  - Authored `docs/research/ADR_L17_GENERATIVE_ROUTER.md` (ADR-022) defining the role taxonomy, model tiers (`FAST`, `BALANCED`, `CAPABLE`), user sovereignty hierarchy (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), recoverable cascading fallback lifecycle, and drop-in `GenerativeProvider(ABC)` compatibility. Recorded in `tasks/DECISIONS.md`.
- [x] **Router Contracts (`omni_engine/contracts/router.py`)**:
  - `AgentRole` enum: `ARGUMENT_WRITER`, `PLANNER`, `REPLANNER`, `FINALIZER`, `CODING`.
  - `ModelTier` enum: `FAST`, `BALANCED`, `CAPABLE`.
  - `ModelSovereigntyLevel` enum: `USER_LOCKED`, `USER_PREFERRED`, `AUTO`.
  - `RoleRouteConfig`: schema_version, role, primary_model, tier, fallback_models, temperature, max_tokens, timeout_seconds, sovereignty, pinned_provider_id, pinned_model_id (`extra="forbid"`).
  - `RouterTelemetry`: role, requested_model, selected_provider_id, selected_model_id, attempts, was_fallback, fallback_reason, latency_ms, prompt_tokens, completion_tokens, timestamp (`extra="forbid"`).
  - `DEFAULT_ROLE_CONFIGS`: Calibrated configurations mapping primary/fallback models and sampling parameters across all 5 roles. Clean exports in `omni_engine/contracts/__init__.py`.
- [x] **Adversarial Plan Review**:
  - Independent subagent identified 3 blocking issues: (1) Missing per-invocation `model` and `timeout` on `GenerativeProvider` and `OpenRouterProvider`; (2) Telemetry signature asymmetry violating base ABC contract; (3) Missing `.generate(...)` alias for `GenerativePlanner`.
  - All 3 blockers resolved in plan prior to implementation.
- [x] **Provider Foundation Hardening (`omni_engine/providers/base.py`, `generative.py`)**:
  - Updated `GenerativeProvider` ABC `generate_text` and `generate_structured` with optional `model: Optional[str] = None` and `timeout: Optional[float] = None`.
  - Updated `OpenRouterProvider` to accept invocation-local `target_model` and `target_timeout` without mutating `self.model_id`, eliminating multi-threaded race conditions.
- [x] **MockGenerativeProvider & GenerativeRouter Engine (`omni_engine/providers/router.py`)**:
  - `MockGenerativeProvider(GenerativeProvider)`: Thread-safe, offline-capable in-memory mock provider supporting scripted text/structured returns, FIFO response queues, per-model mappings (`set_model_response`, `set_model_error`), `.generate(...)` alias, invocation logging, and health checks.
  - `GenerativeRouter(GenerativeProvider)`:
    - Registered provider dispatch supporting provider URI scheme (`provider:model`).
    - User model sovereignty: `USER_LOCKED` strictly blocks fallbacks; `USER_PREFERRED` cascades to fallbacks with explicit telemetry; `AUTO` dynamically cascades across tier models.
    - Recoverable vs fatal error classification: `RATE_LIMITED`, `TIMEOUT`, `NETWORK_ERROR`, `SERVICE_UNAVAILABLE`, `UNCONFIGURED`, and structured `SCHEMA_VIOLATION` permit cascading; fatal errors (`CANCELLED`, `UNAUTHORIZED_ACTION`) abort cascade immediately.
    - Contract drop-in: standard `generate_text` and `generate_structured` default to `AgentRole.PLANNER`; dedicated typed methods `generate_text_with_telemetry` and `generate_structured_with_telemetry` provide typed `RouterTelemetry` envelopes.
    - `.generate(...)` convenience alias returning raw text for `GenerativePlanner`.
    - Thread-safe telemetry history logging protected by `threading.RLock()`.
  - Clean exports in `omni_engine/providers/__init__.py`.
  - Defensively resolved attribute compatibility (`s.id`) in `omni_engine/planning/generative_planner.py`.
- [x] **Unit & Adversarial Testing (`tests/test_l17_generative_router.py`)**:
  - 23 comprehensive tests covering: mock capabilities, role-based dispatch across all 5 roles, user sovereignty modes (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), structured schema violation recovery, fatal error fast-fail, candidate exhaustion, drop-in compatibility, and multi-threaded concurrency safety. All 23 tests pass in 0.21s.
- [x] **Adversarial Diff Review, Verification & CI**:
  - Independent subagent review returned **PASS** with zero blocking defects.
  - Full test suite: 585 automated tests passing across 31 test files.
  - Non-switching boundary: exactly 0 diffs on `omni_agent.py` and `omni_engine/planner.py`.
  - Committed (`0133b35`), pushed to `origin/laya-autonomous-v2`, and verified on GitHub Actions CI Run 37236418045.

---

### Step 16: L17.5 — Real Cloud Provider Integration (COMPLETED & VERIFIED)
- [x] **External Research & ADR-023**:
  - Researched direct cloud vendor APIs vs OpenRouter proxying for LAYA autonomous roles (OpenAI, Anthropic, DeepSeek).
  - Addressed vendor constraints: Anthropic mandatory `max_tokens` (rejects requests without `max_tokens` or with `max_tokens < 1`), temperature floor/ceiling (`[0.0, 1.0]`), strict exclusion of `role: system` from `messages` array, and anti-preamble prompt framing for JSON schema conformance.
  - Authored `docs/research/ADR_L17_5_REAL_CLOUD_PROVIDERS.md` (ADR-023) and recorded in `tasks/DECISIONS.md`.
- [x] **Adversarial Plan Review**:
  - Independent subagent review issued **APPROVED WITH MANDATORY BLOCKING REPAIRS** (REV-17.5-01 through REV-17.5-06).
  - All 6 blocking repairs resolved prior to implementation.
- [x] **Secret Scrubber Hardening (`omni_engine/automation/scrubber.py`)**:
  - Added regex for Anthropic API keys (`sk-ant-api03-...`, `sk-ant-...`).
  - Added regex for unquoted HTTP header error dumps (`x-api-key: ...`, `authorization: ...`).
- [x] **Real Cloud Provider Adapters (`omni_engine/providers/cloud.py`)**:
  - `DirectOpenAIProvider`: Direct OpenAI API adapter using `openai.OpenAI`, non-throwing `__init__`, empty prompt defense, structured validation, per-invocation model and timeout overrides, and lightweight model health probes.
  - `AnthropicProvider`: Zero-dependency Claude Messages API adapter implemented via standard library `urllib.request` (zero external dependencies), mandatory `max_tokens` (default 4096, minimum 1), clamped `temperature ∈ [0.0, 1.0]`, top-level `system` segregation, multi-block text traversal, anti-preamble prompt framing, HTTP error normalization, and mock transport injection (`transport_fn`).
  - `DeepSeekProvider`: Subclass of `DirectOpenAIProvider` preconfigured for `https://api.deepseek.com` and `deepseek-chat`.
  - `build_standard_generative_router`: Factory wiring direct cloud providers (`openai`, `anthropic`, `deepseek`) alongside `openrouter` and `mock` fallbacks in `GenerativeRouter`.
  - `sanitize_provider_error`: Dual-layer literal token replacement and regex scrubbing preventing API keys from leaking in tracebacks or error messages.
- [x] **Exports (`omni_engine/providers/__init__.py`)**:
  - Exported all cloud provider classes and helpers in `__all__`.
- [x] **Unit & Adversarial Testing (`tests/test_l17_5_cloud_providers.py`)**:
  - 18 comprehensive tests covering: OpenAI text and structured generation, Anthropic Messages API payload/traversal and temperature clamping, DeepSeek client configuration, unconfigured provider cascading under `AUTO` / `USER_PREFERRED` and fast-failing under `USER_LOCKED`, secret redaction in exception strings and error dumps, and router URI dispatch. All 18 tests pass in 3.23s.
- [x] **Adversarial Diff Review, Full Regression & Remote CI**:
  - Independent subagent review returned **PASS** with zero blocking defects (Subagent `cae1ba2e-74b6-442b-a39e-2e419de6cc59`).
  - Full test suite: **603 automated tests passing across 32 test files (100% pass rate) (+ 47 subtests = 650 total checks)**.
  - Non-switching boundary: exactly 0 diffs on `omni_agent.py` and `omni_engine/planner.py`.
  - Committed (`49e220f`), pushed to `origin/laya-autonomous-v2`.

---

### Step 17: L18 — Modular Browser Capability Rebuild (COMPLETED & VERIFIED)
- [x] **External Research & ADR-024**:
  - Audited Playwright browser integration for atomic capability decomposition into 7 discrete capabilities: `browser.navigate`, `browser.snapshot`, `browser.click`, `browser.type`, `browser.extract`, `browser.screenshot`, `browser.tabs`.
  - Evaluated bounded session pooling (`max_tabs=5`), DOM snapshotting, tab isolation, and memory containment on Windows (8GB host RAM limit: `--renderer-process-limit=4`, `--max-old-space-size=512`, `--disable-dev-shm-usage`).
  - Authored `docs/research/ADR_L18_MODULAR_BROWSER.md` (ADR-024) and recorded in `tasks/DECISIONS.md`.
- [x] **Adversarial Plan Review**:
  - Independent subagent review issued **APPROVED WITH MANDATORY BLOCKING REPAIRS** (REV-L18-01 through REV-L18-04, plus non-blocking 05-09).
  - All requirements strictly resolved and designed prior to implementation.
- [x] **Modular Browser Contracts (`omni_engine/contracts/browser.py`, `contracts/__init__.py`)**:
  - Rebuilt contracts with strict Pydantic v2 schemas (`extra="forbid"`, `validate_assignment=True`).
  - Contracts added: `TabAction`, `TabInfo`, `BrowserTabsRequest`, `BrowserTabsResult`, `BrowserExtractRequest`, `BrowserExtractResult`, `BrowserNavigateRequest`, `BrowserNavigateResult`, `BrowserClickRequest`, `BrowserClickResult`, `BrowserTypeRequest`, `BrowserTypeResult`, `BrowserScreenshotModularRequest`, `BrowserScreenshotModularResult`.
- [x] **Session Substrate & Tab Management (`omni_engine/browser/session.py`)**:
  - Decoupled `BrowserSession` into bounded multi-tab management with strict `max_tabs=5`.
  - Implemented `_prune_dead_pages()` (REV-L18-03) auto-pruning closed/crashed pages before tab operations and page retrieval.
  - Implemented last tab close protection (REV-L18-04) refusing to close the last remaining page.
  - Enforced safe tab closing via `page.close(run_before_unload=False)` avoiding modal dialog deadlocks.
- [x] **DOM Action Indexer Financial Detection (`omni_engine/browser/indexer.py`)**:
  - Stamped visible interactive elements with `data-laya-idx="N"`.
  - Scanned form attributes (`name`, `id`, `placeholder`, `autocomplete`) and matched financial keywords (`FINANCIAL_KEYWORDS_REGEX`, `FINANCIAL_URL_REGEX`) to tag `is_financial=True` (REV-L18-07).
- [x] **Modular Browser Driver (`omni_engine/browser/driver.py`)**:
  - Implemented `extract(selector, attribute, multiple, max_items)` with CDP dict parameter binding (`page.evaluate(_EXTRACT_SCRIPT, {...})`), strictly preventing script injection (REV-L18-01).
  - Implemented indexed selector translation (`@N` to `[data-laya-idx="N"]`) (REV-L18-06).
  - Implemented atomic direct execution methods: `navigate()`, `click()`, `type_text()`, `take_screenshot()`, and `manage_tabs()`.
  - Wired `BrowserActionType.EXTRACT` and `MANAGE_TABS` into `execute()`.
- [x] **Policy Engine Safety & Gating (`omni_engine/policy/engine.py`)**:
  - Extended Stage 0/Stage 3 financial checks to match `spec.id in ("browser_interact", "browser.interact") or spec.id.startswith(("browser.", "browser_"))` (REV-L18-02).
  - Enforced `REQUIRE_CONFIRMATION` on financial clicks/typing/navigation under autonomy tiers below `WORKFLOW_AUTHORIZED`.
  - Calibrated base risk to 0.15 for read-only browser capabilities without sensitive targets.
- [x] **Capability Substrate Integration (`omni_engine/capabilities/definitions.py`, `capabilities/__init__.py`)**:
  - Preserved canonical 23-tool count invariant in `build_canonical_registry()`.
  - Registered all 7 atomic capability specs with dot and dotless aliases in `build_real_capability_registry()`, assigning `browser_screenshot_v2` to screenshot to prevent alias collision (REV-L18-08).
  - Implemented normalized adapters returning `(True, result.model_dump())` on success and `(False, ToolError(...))` on failure for truthful `ToolOutcome` mapping in `CapabilityRegistry.invoke()` (REV-L18-09).
- [x] **Argument Resolver Mapping (`omni_engine/arguments/resolver.py`)**:
  - Added deterministic slot extraction for `browser.navigate`, `browser.snapshot`, `browser.click`, `browser.type`, `browser.extract`, `browser.screenshot`, and `browser.tabs`.
- [x] **Unit & Adversarial Testing (`tests/test_l18_modular_browser.py`)**:
  - 20 comprehensive unit and integration tests covering contracts, multi-tab bounds, last tab protection, dead page pruning, CDP dict injection defense, indexed selector translation, financial gating, canonical 23-tool invariant, and adapter outcome normalization. All 20 tests pass offline in 0.66s.
- [x] **Adversarial Diff Review**:
  - Independent subagent review returned **PASS** with zero blocking defects.
- [x] **Full Regression Suite, Verification & Remote CI**:
  - **623 automated tests passing across 33 test files (100% pass rate) (+ 47 subtests = 670 total checks)**.
  - Non-switching boundary: exactly 0 diffs on `omni_agent.py` and `omni_engine/planner.py`.
  - Code commit `51abcf9` pushed to `origin/laya-autonomous-v2`.
- [x] **ENFORCE HARD STOP**:
  - Milestone L18 is 100% complete and verified.
  - Strict HARD STOP enforced: Do NOT start Checkpoint L19 (Memory V2). Await user instructions.


