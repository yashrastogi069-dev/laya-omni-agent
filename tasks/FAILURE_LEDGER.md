# FAILURE_LEDGER.md — Canonical Record of Meaningful Failures, Defects, and Invariant Violations

> **DOCUMENT PURPOSE**: This ledger is the permanent, immutable engineering record for meaningful test failures, discovered defects, fault-injection failures, and invariant violations in the **LAYA Omni Agent** repository. Failures recorded here indicate architectural misunderstandings, state-machine defects, concurrency defects, persistence defects, crash-window vulnerabilities, idempotency defects, policy/safety defects, boundary defects, incorrect test assumptions, or false-success conditions. Failures must never be deleted or rewritten.

---

## Failure Accounting Protocol

Every meaningful failure must adhere to the lifecycle:
`CAPTURE → CLASSIFY → ROOT CAUSE → REPRODUCE → REPAIR → ADVERSARIALIZE → REGRESSION TEST → VERIFY → DOCUMENT`

Root-Cause Layers:
- `TEST`: Test fixture, mock, assertion, or expectation was incorrect or misaligned with contract.
- `IMPLEMENTATION`: Bug, omission, or logic error in runtime implementation code.
- `CONTRACT`: Schema, type, enum, or protocol definition was flawed or underspecified.
- `ARCHITECTURE`: Structural design flaw, concurrency deadlock, or persistence vulnerability.
- `DOCUMENTATION`: Discrepancy between stated behavior and source/runtime truth.
- `ENVIRONMENT`: Platform-specific behavior (Windows Win32, PyTorch CPU, SQLite WAL).

---

## 1. Historical Failure Archaeology (Pre-L14.1)

### FAIL-HIST-001: Missing `re` Import in `tool_safe_math`
- **Failure ID**: `FAIL-HIST-001`
- **Checkpoint / Subsystem**: L0 / OS & Math Tools (`omni_engine/tools/data_tools.py`)
- **Exact Failing Test(s)**: `tests/test_l0_reproductions.py::test_reproduce_defect_1_safe_math_name_error`
- **Observed Behavior**: Calling `tool_safe_math` raised `NameError: name 're' is not defined` immediately on any expression containing spaces or functions.
- **Expected Behavior**: Safe evaluation of mathematical expressions without runtime NameError.
- **Root Cause**: `import re` was missing from module scope in `omni_engine/tools/data_tools.py`. Zero automated tests existed prior to L0, allowing a syntax defect to sit undetected.
- **Root-Cause Layer**: `IMPLEMENTATION`
- **Repair Made**: Added `import re` and implemented full AST `NodeVisitor` mathematical evaluator.
- **Why the Repair Fixes Root Cause**: Re-exports `re` at module level and replaces insecure string evaluation with a parsed AST visitor.
- **Regression Test Added**: `tests/test_l1_repairs.py::TestL1SafeMathRepairs`
- **Adversarial/Fault Test Added**: `tests/test_l1_1_bounds.py`
- **Nearby Invariants Checked**: Whitelisted operators, exponential bounds, AST node limits.
- **Commit Introducing Failure**: Initial repository commit (`26be41e`).
- **Commit Repairing Failure**: `e78cf8b`
- **Final Status**: RESOLVED

---

### FAIL-HIST-002: Computational Exhaustion via Unbounded Exponents in `tool_safe_math`
- **Failure ID**: `FAIL-HIST-002`
- **Checkpoint / Subsystem**: L1.1 / Sandboxed Math Evaluator
- **Exact Failing Test(s)**: `tests/test_l1_1_bounds.py::test_math_computational_exhaustion_bounds`
- **Observed Behavior**: Expressions such as `9**9**9**9` froze Python GIL indefinitely, causing unbounded CPU consumption.
- **Expected Behavior**: Deterministic rejection of expressions exceeding safe computational bounds with structured error.
- **Root Cause**: AST whitelist checked operator types but placed no magnitude limits on exponents or AST tree complexity.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Repair Made**: Added AST node limits (<=40), expression length limits (<=256 chars), literal magnitude limits (<=1e100), and exponent limits (abs(exp) <= 100).
- **Why the Repair Fixes Root Cause**: Halts parser before AST evaluation can trigger CPU exhaustion.
- **Regression Test Added**: `tests/test_l1_1_bounds.py`
- **Adversarial/Fault Test Added**: Multiple factorial and exponent boundary tests.
- **Nearby Invariants Checked**: Deterministic Control (Invariant 1).
- **Commit Introducing Failure**: `e78cf8b`
- **Commit Repairing Failure**: `6a66787`
- **Final Status**: RESOLVED

---

### FAIL-HIST-003: Memory JSON Corruption and Success Conflation in `OmniMemory`
- **Failure ID**: `FAIL-HIST-003`
- **Checkpoint / Subsystem**: L1 & L1.1 / Persistent Memory (`omni_engine/memory.py`)
- **Exact Failing Test(s)**: `tests/test_l0_reproductions.py::test_reproduce_defect_2_memory_schema_inconsistency`
- **Observed Behavior**: Uncaught JSON decoding errors when loading corrupt files; memory marked tools as "successful" regardless of whether the physical tool returned an error string or zero rows.
- **Expected Behavior**: Graceful recovery from corrupt storage files via quarantining; explicit 3-state verification tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`).
- **Root Cause**: Raw invocation counting conflated with outcome verification; direct in-place file writes without atomic replacement.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Repair Made**: Implemented write-to-tmp + `os.replace` atomic persistence; `.corrupt.<timestamp>` file quarantining; 3-state verification model.
- **Why the Repair Fixes Root Cause**: Prevents partial file writes on crash and decouples physical invocation from verified semantic success.
- **Regression Test Added**: `tests/test_l1_repairs.py::TestL1MemoryRepairs`
- **Adversarial/Fault Test Added**: `tests/test_l1_1_bounds.py`
- **Nearby Invariants Checked**: Evidence-Based Completion (Invariant 6).
- **Commit Introducing Failure**: Initial repository commit (`26be41e`).
- **Commit Repairing Failure**: `e78cf8b`, `6a66787`
- **Final Status**: RESOLVED

---

### FAIL-HIST-004: Catalog Truncation at 12 Tools in System 1 Router
- **Failure ID**: `FAIL-HIST-004`
- **Checkpoint / Subsystem**: L6A & L6B / Hierarchical Capability Routing
- **Exact Failing Test(s)**: `tests/test_l6a_routing.py`
- **Observed Behavior**: 11 out of 23 registered capabilities could never be selected by the system because the router evaluated only `tool_catalog[:12]`.
- **Expected Behavior**: All registered capabilities accessible via hierarchical routing (Domain → Skill → Candidate Set).
- **Root Cause**: Hardcoded slice `[:12]` introduced to keep prompt within context limits.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Repair Made**: Built `HierarchicalRouter` with domain routing, candidate pooling, and skill manifests.
- **Why the Repair Fixes Root Cause**: Eliminates flat catalog dumps while bounding prompt size through hierarchical triage.
- **Regression Test Added**: `tests/test_l6a_routing.py`, `tests/test_l6b_skill_routing.py`
- **Adversarial/Fault Test Added**: Out-of-domain and cross-domain routing tests.
- **Nearby Invariants Checked**: Bounded System 1 SLA, Strongly Typed Contracts.
- **Commit Introducing Failure**: Legacy codebase.
- **Commit Repairing Failure**: `7ab5b68`, `b8a6234`
- **Final Status**: RESOLVED

---

### FAIL-HIST-005: Raw Prompt Passed Verbatim to Tool Execution
- **Failure ID**: `FAIL-HIST-005`
- **Checkpoint / Subsystem**: L8 / Typed Argument Resolution Engine
- **Exact Failing Test(s)**: `tests/test_l8_arguments.py`
- **Observed Behavior**: `AutonomousPlanner` passed full user instruction (e.g. `"read README.md"`) as `filepath` to `tool_file_read`, failing file lookup.
- **Expected Behavior**: Deterministic extraction of typed arguments adhering to `CapabilitySpec.input_schema`.
- **Root Cause**: Absence of argument resolution layer between natural language and tool invocation.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Repair Made**: Created `ArgumentResolver` with deterministic extractors, schema validation, alias mapping, and clarification gating.
- **Why the Repair Fixes Root Cause**: Ensures natural language prompt is never passed directly into typed capabilities.
- **Regression Test Added**: `tests/test_l8_arguments.py` (26 tests)
- **Adversarial/Fault Test Added**: Injection prompts, missing required argument tests.
- **Nearby Invariants Checked**: Strongly Typed Capability Contracts (Invariant 4).
- **Commit Introducing Failure**: Legacy codebase.
- **Commit Repairing Failure**: `131ae95`
- **Final Status**: RESOLVED

---

### FAIL-HIST-006: Windows RAM Eviction Thrashing
- **Failure ID**: `FAIL-HIST-006`
- **Checkpoint / Subsystem**: Foundation Gate / System 1 Provider Broker
- **Exact Failing Test(s)**: `tests/test_foundation_broker.py`
- **Observed Behavior**: ModernBERT model evicted on instantaneous 200 MB Windows OS cache dips, causing 47–69s reload latency on every subsequent request.
- **Expected Behavior**: Stable model residency with debounced eviction requiring sustained memory pressure.
- **Root Cause**: Instantaneous single-sample RAM threshold checking without time-window debouncing.
- **Root-Cause Layer**: `ENVIRONMENT`
- **Repair Made**: Debounced eviction checking (3 consecutive breaches over >=5 seconds) and idle-only eviction gating.
- **Why the Repair Fixes Root Cause**: Accommodates Windows OS memory caching fluctuations.
- **Regression Test Added**: `tests/test_foundation_broker.py`
- **Adversarial/Fault Test Added**: Rapid RAM fluctuation simulation tests.
- **Nearby Invariants Checked**: System 1 Fast Decision SLA (Invariant 2).
- **Commit Introducing Failure**: `2a2b1fa`
- **Commit Repairing Failure**: `9cf8aaf`
- **Final Status**: RESOLVED

---

### FAIL-HIST-007: Developer Supervisor Dirty Worktree Destruction on Revert
- **Failure ID**: `FAIL-HIST-007`
- **Checkpoint / Subsystem**: RV0 Reality Gate & R5 / Supervised Developer Engine
- **Exact Failing Test(s)**: `tests/test_rv0_reality_gate.py::test_dirty_worktree_survival_during_safe_revert`
- **Observed Behavior**: Calling safe revert after a failed developer iteration destroyed pre-existing uncommitted user edits in the working tree.
- **Expected Behavior**: Rule-0 Inviolable: Pre-existing user modifications must survive autonomous agent rollbacks byte-for-byte.
- **Root Cause**: `safe_revert` tracked only modified files from the current iteration without baseline working-tree diff comparison.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Repair Made**: Implemented `capture_baseline_state()` and file-by-file surgical rollback using `git checkout -- <file>` against pre-run baseline.
- **Why the Repair Fixes Root Cause**: Preserves uncommitted user changes outside the agent's targeted edits.
- **Regression Test Added**: `tests/test_rv0_reality_gate.py`
- **Adversarial/Fault Test Added**: Dirty worktree fault injection test.
- **Nearby Invariants Checked**: Rule-0 (No destructive git operations).
- **Commit Introducing Failure**: `48f10b5`
- **Commit Repairing Failure**: `a2b81b6`
- **Final Status**: RESOLVED

---

### FAIL-HIST-008: Checkpoint L14 Six-Test Failure Batch
- **Failure ID**: `FAIL-HIST-008`
- **Checkpoint / Subsystem**: L14 / Deterministic DAG Executor (`tests/test_l14_executor.py`)
- **Exact Failing Test(s)**:
  1. `test_confirmation_gate_pause_and_resume`
  2. `test_confirmation_gate_rejection_fails_quest`
  3. `test_crash_recovery_resumes_cleanly_from_sqlite`
  4. `test_diamond_dag_concurrent_reads_and_aggregation`
  5. `test_linear_dag_execution_passes_to_awaiting_verification`
  6. `test_mutation_barrier_and_operation_ledger_deduplication`
- **Observed Behavior**: 6 out of 17 tests failed during initial execution of `test_l14_executor.py`.
- **Expected Behavior**: Deterministic DAG execution, concurrency synchronization, crash resumption, and policy gating.
- **Root Causes**:
  - Tests 1 & 2 (`confirmation_gate`): Pass 6 of `DeterministicPlanValidator` failed because test used default `SAFE_ASSISTANT` autonomy, while `file_write` requires `LOCAL_OPERATOR`. Pre-flight validation rejected plan before reaching confirmation gate.
  - Test 3 (`crash_recovery`): `StructuredDAGPlanner.attach_to_quest` was called as an unbound class method without instance; `Plan.plan_type` serialization defaulted to None.
  - Test 4 (`diamond_dag`): `tool_safe_math` output was formatted as a Markdown string (`"### Math Evaluation:\n... = **30**"`), which lacked numeric extraction; `$steps.step_1.output.result` failed dynamic resolution.
  - Test 5 (`linear_dag`): `CapabilityRegistry.invoke` expected `CapabilityInvocation` object, but executor called `invoke(capability_id, arguments)`.
  - Test 6 (`mutation_barrier`): `OperationLedger` lacked convenience method `commit_operation(operation_id, receipt)`.
- **Root-Cause Layer**: `CONTRACT` / `IMPLEMENTATION` / `TEST`
- **Repair Made**:
  - B1: Validator constructor alias for `registry` / `capability_registry`.
  - B2: Default `PlanType.TEMPLATE_DERIVED` in `Plan` schema.
  - B3: Instantiated `StructuredDAGPlanner` before calling `attach_to_quest`.
  - B4: Overloaded `CapabilityRegistry.invoke()` to accept both invocation objects and direct capability IDs with dictionaries.
  - B5: Added `make_safe_math_adapter` to extract numeric float/int into `ToolResult.data`.
  - B6: Enhanced `DynamicResolver` multi-path navigation for dictionary outputs.
  - B7: Added `commit_operation` and `fail_operation` to `OperationLedger`.
  - B8: Updated test autonomy profile to `AutonomyProfile.LOCAL_OPERATOR`.
- **Why the Repair Fixes Root Cause**: Addressed interface mismatches between executor, registry, validator, and test fixtures.
- **Audit Deficiencies Remaining from Repair**:
  - The repair in B8 masked the deeper contract issue: the test was modified, but the executor lacked test coverage for how a step handles missing inputs vs missing autonomy vs unconfirmed actions.
  - Test 3 (`crash_recovery`) only tested recovery from `COMPLETED` + `PENDING`, completely omitting steps persisted in `RUNNING` status (which exposes AUDIT-06).
- **Regression Test Added**: `tests/test_l14_executor.py` (17 tests)
- **Commit Introducing Failure**: `b9a2dbe` (initial draft)
- **Commit Repairing Failure**: `b9a2dbe`
- **Final Status**: SYMPTOM REPAIRED IN L14; DEEPER DURABILITY DEFECTS REOPENED UNDER L14.1

---

## 2. Independent Audit Defect Catalog (L14.1 Active Investigation)

### FAIL-L14.1-001 (AUDIT-01): Mutation Timeout/Network Exception Normalization Bypasses `UNKNOWN_COMMIT`
- **Failure ID**: `FAIL-L14.1-001`
- **Checkpoint / Subsystem**: L14 / Capability Invocation & Operation Ledger Integration
- **Source Location**: `omni_engine/capabilities/registry.py:272-292` & `omni_engine/execution/executor.py:681-693`
- **Observed Behavior**: When a mutating capability execution experienced a `TimeoutError`, `socket.timeout`, `URLError`, or `ConnectionError`, `CapabilityRegistry.invoke()` caught the exception and returned `ToolResult(success=False, error=ToolError(code=ErrorCode.TIMEOUT/NETWORK_ERROR, retryable=True))`. In `executor.py`, this entered the failure branch and invoked `self.operation_ledger.fail_operation(op_id, error=err_msg, is_uncertain=False)`, falsely declaring the mutation definitely uncommitted and allowing dangerous blind retries.
- **Expected Behavior**: Safety Invariant: Any mutating capability that times out or loses connection *after* dispatch has an uncertain real-world commit status. It must strictly transition to `UNKNOWN_COMMIT` (`is_uncertain=True`), step must transition to `StepStatus.AWAITING_RECONCILIATION`, and Quest must pause as `QuestStatus.PAUSED_FOR_RECONCILIATION`.
- **Root Cause**: `CapabilityRegistry.invoke()` normalized timeouts into routine failures, and `executor.py` treated all normalized failures as certain failures (`is_uncertain=False`), reserving `is_uncertain=True` only for unhandled exceptions.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: In `DeterministicDAGExecutor._execute_step()`, if capability is a mutation and `tool_res.error.code` is `ErrorCode.TIMEOUT` or `ErrorCode.NETWORK_ERROR`, marked operation `is_uncertain=True` (`UNKNOWN_COMMIT`) and step as `StepStatus.AWAITING_RECONCILIATION`. In `_run_coordinator_loop`, paused quest immediately as `PAUSED_FOR_RECONCILIATION` when any mutation enters this uncertain state.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch2_IdempotencyAndTimeouts::test_audit_01_mutation_timeout_enters_unknown_commit_and_pauses_for_reconciliation`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-002 (AUDIT-02): Global Argument-Hash Idempotency Key Causes Unintended Cross-Quest Deduplication
- **Failure ID**: `FAIL-L14.1-002`
- **Checkpoint / Subsystem**: L11 & L14 / Operation Ledger Idempotency Key Derivation
- **Source Location**: `omni_engine/operations/ledger.py:75-76, 114-121`
- **Observed Behavior**: `compute_idempotency_key()` derived key as `f"idem_{capability_id}_{arg_hash[:16]}"`. In `register_mutation()`, it looked up `self.store.get_by_idempotency_key(idempotency_key)`. If Quest A ran `file_write(path="out.txt", content="hello")` and committed, and Quest B ran the identical operation later, Quest B matched Quest A's committed operation, returned `is_deduplicated=True`, skipped execution, and returned Quest A's old cached receipt.
- **Expected Behavior**: Logical operation identity must be bounded by the quest context (`quest_id:step_id:capability_id`). Two independent Quests must never accidentally deduplicate each other unless explicitly sharing an external idempotency key.
- **Root Cause**: Idempotency key derivation conflated physical argument hashing with logical operation identity and omitted `quest_id`.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Updated `compute_idempotency_key` and `register_mutation` in `OperationLedger` to scope automatic idempotency keys by `quest_id` (`f"idem_{quest_id}_{capability_id}_{arg_hash[:16]}"`). Preserved global cross-quest deduplication strictly when an explicit `custom_idempotency_key` is provided.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch2_IdempotencyAndTimeouts::test_audit_02_ledger_idempotency_keys_scoped_by_quest_id`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-003 (AUDIT-03): External Idempotency Key Not Propagated to Capability Invocations
- **Failure ID**: `FAIL-L14.1-003`
- **Checkpoint / Subsystem**: L14 / Capability Dispatch
- **Source Location**: `omni_engine/execution/executor.py:667`
- **Observed Behavior**: `executor.py` called `self.capability_registry.invoke(step.capability_id, resolved_args)`. The derived `idempotency_key` was stored in SQLite but never passed into the capability invocation envelope, preventing downstream remote APIs or capability handlers from receiving the execution context.
- **Expected Behavior**: When invoking capabilities, the external idempotency key, `quest_id`, `step_id`, and `operation_id` must be propagated through the invocation context to enable remote deduplication and audit tracking.
- **Root Cause**: `CapabilityInvocation` lacked `idempotency_key`, and `CapabilityRegistry.invoke()` did not accept or inject invocation context into callables.
- **Root-Cause Layer**: `CONTRACT`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Added `idempotency_key` to `CapabilityInvocation` contract. Updated `CapabilityRegistry.invoke()` to accept `idempotency_key`, `quest_id`, `step_id`, and `operation_id`, forwarding them into callables that accept `**kwargs` or specific context parameters. Updated `DeterministicDAGExecutor` to pass this context during dispatch.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch2_IdempotencyAndTimeouts::test_audit_03_custom_idempotency_key_propagated_to_invocation`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-004 (AUDIT-04): Operation and Attempt Transitions Lack Transactional Atomicity
- **Failure ID**: `FAIL-L14.1-004`
- **Checkpoint / Subsystem**: L11 / Operation Store & Ledger Persistence
- **Source Location**: `omni_engine/operations/ledger.py:211-221, 250-270, 310-330`
- **Observed Behavior**: In `begin_attempt`, `self.store.record_attempt(attempt)` was committed, and then in a separate transaction, `self.store.update_operation(updated_op)` was committed. A crash between these statements left an attempt in `STARTED` state while the operation remained in `PENDING` state. Similarly, `commit_attempt` and `fail_attempt` updated the attempt and operation in separate database commits.
- **Expected Behavior**: Attempt creation/update and operation state transition must occur within a single atomic database transaction (`BEGIN IMMEDIATE ... COMMIT`).
- **Root Cause**: Methods in `OperationLedger` delegated to individual `OperationStore` methods that each managed their own transaction context (`with self._transaction():`).
- **Root-Cause Layer**: `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Implemented `begin_attempt_atomic()`, `commit_attempt_atomic()`, and `fail_attempt_atomic()` on `OperationStore` executing multi-statement operations inside a single SQLite transaction with rollbacks on failure; updated `OperationLedger` to route all attempt lifecycle transitions through these atomic store methods.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch1_StateMachineAndAtomicity::test_audit_04_operation_and_attempt_atomicity`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-005 (AUDIT-05): Quest State Transitions and Event Emission Lack Transactional Atomicity
- **Failure ID**: `FAIL-L14.1-005`
- **Checkpoint / Subsystem**: L10 / Quest Store & Engine Persistence
- **Source Location**: `omni_engine/quest/engine.py:195-212, 250-270`
- **Observed Behavior**: `transition_quest()` called `self.store.update_quest(updated_quest)` which committed to SQLite. Then it called `self.store.record_event(...)` which committed in a second transaction. A crash between them resulted in a state change with no corresponding audit event in the immutable event ledger.
- **Expected Behavior**: A state transition and its audit event must commit together atomically or neither commits.
- **Root Cause**: `QuestStore` provided separate methods `update_quest`, `update_step`, and `record_event`, each opening and committing its own transaction.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Implemented `transition_quest_atomic(quest, event)`, `transition_step_atomic(step, event)`, and `attach_plan_atomic(quest, steps, event)` on `QuestStore` running in a single transaction; updated `QuestEngine` to use atomic store methods for all state transitions and plan attachments.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch1_StateMachineAndAtomicity::test_audit_05_quest_transition_and_event_atomicity`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-006 (AUDIT-06): Interrupted READ_ONLY Step Crash Recovery Fails with `InvalidStateTransitionError`
- **Failure ID**: `FAIL-L14.1-006`
- **Checkpoint / Subsystem**: L14 & L10 / Quest State Machine & Crash Recovery
- **Source Location**: `omni_engine/execution/executor.py:278` vs `omni_engine/contracts/quest.py:126-132`
- **Observed Behavior**: When recovering from an interrupted process where a `READ_ONLY` step was left in `RUNNING` status, `executor.py:278` attempted `self.quest_engine.transition_step(quest_id, s.step_id, StepStatus.READY)`. However, `VALID_STEP_TRANSITIONS[StepStatus.RUNNING]` contained only `{PAUSED, AWAITING_VERIFICATION, COMPLETED, FAILED, CANCELLED}`. The transition raised `InvalidStateTransitionError`, crashing the executor recovery routine.
- **Expected Behavior**: An interrupted read-only step must be recoverable to `READY` upon process reboot so it can safely re-execute without invariant violation.
- **Root Cause**: Mismatch between executor recovery logic and the contract state transition matrix in `contracts/quest.py`.
- **Root-Cause Layer**: `CONTRACT` / `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Added `StepStatus.READY` to `VALID_STEP_TRANSITIONS[StepStatus.RUNNING]` in `omni_engine/contracts/quest.py` to allow interrupted read-only step recovery upon engine reboot.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch1_StateMachineAndAtomicity::test_audit_06_interrupted_read_only_running_step_recovery`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-007 (AUDIT-07): `UNKNOWN_COMMIT` Mutation Uncertainty Terminalizes Quest Permanently
- **Failure ID**: `FAIL-L14.1-007`
- **Checkpoint / Subsystem**: L14 / Failure Handling & Lifecycle States
- **Source Location**: `omni_engine/execution/executor.py:286-307`
- **Observed Behavior**: When an interrupted mutation step was found in `IN_PROGRESS`, executor marked it `UNKNOWN_COMMIT` in the ledger, transitioned the step to `StepStatus.FAILED`, and transitioned the Quest to `QuestStatus.FAILED`. Because `FAILED` is an absorbing terminal state, the Quest could not be resumed even after external evidence reconciled the mutation.
- **Expected Behavior**: Mutation uncertainty should place the step into a recoverable reconciliation state (`StepStatus.AWAITING_RECONCILIATION`) and the Quest into a non-terminal paused state (`QuestStatus.PAUSED_FOR_RECONCILIATION`), allowing an operator or verifier to reconcile reality and resume.
- **Root Cause**: Binary classification of step outcomes as either `COMPLETED` or `FAILED`.
- **Root-Cause Layer**: `ARCHITECTURE` / `CONTRACT`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Added `StepStatus.AWAITING_RECONCILIATION` and `QuestStatus.PAUSED_FOR_RECONCILIATION` to contracts, state transitions, and event enums. Updated `DeterministicDAGExecutor` crash recovery to transition interrupted mutations to `AWAITING_RECONCILIATION` and pause quest as `PAUSED_FOR_RECONCILIATION`. Updated `DeterministicDAGExecutor.resume()` to inspect operation ledger upon resumption, transition reconciled steps to `COMPLETED` (or `READY` if failed with attempts remaining), and continue DAG execution to `AWAITING_VERIFICATION`.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch1_StateMachineAndAtomicity::test_audit_07_unknown_commit_pauses_for_reconciliation_not_terminal_failed`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-008 (AUDIT-08): Validated Plan Identity and Validation Receipt Not Persisted
- **Failure ID**: `FAIL-L14.1-008`
- **Checkpoint / Subsystem**: L12, L13, L14 / Plan Persistence & Tamper Resistance
- **Source Location**: `omni_engine/planning/engine.py:152-178` & `omni_engine/execution/executor.py:723-745`
- **Observed Behavior**: When attaching a plan to a quest, only steps were persisted. Plan-level identity (`plan_id`, `plan_version`, `plan_hash`, `validation_hash`, `validated_at`) was discarded. On subsequent execution or resume, `executor.py` fabricated a synthetic `Plan` object on the fly with a newly generated `plan_id` and default `PlanType.TEMPLATE_DERIVED`.
- **Expected Behavior**: The exact plan identity, SHA-256 hash, and validation report receipt must be persisted durably. The executor must refuse to execute an unvalidated, modified, or stale plan.
- **Root Cause**: `Quest` schema only stored a list of `QuestStep`s and lacked durable plan provenance fields.
- **Root-Cause Layer**: `ARCHITECTURE` / `CONTRACT`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: In `omni_engine/planning/engine.py:attach_to_quest()`, computed deterministic SHA-256 `plan_hash` and constructed structured `plan_provenance` (`plan_id`, `plan_type`, `plan_hash`, `timeout_budget_s`, `skill_id`). Extended `QuestEngine.attach_plan()` to accept `metadata` and atomically persist `plan_provenance` into `Quest.metadata` in SQLite.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch3_PlanDurabilityAndPlanners::test_audit_08_plan_provenance_persisted_in_quest_metadata`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-009 (AUDIT-09): `PlanStep` Execution Semantics Lost During Persistence
- **Failure ID**: `FAIL-L14.1-009`
- **Checkpoint / Subsystem**: L12 & L10 / PlanStep to QuestStep Mapping
- **Source Location**: `omni_engine/planning/engine.py:161-171` & `omni_engine/contracts/quest.py:90-110`
- **Observed Behavior**: When `PlanStep` was converted to `QuestStep` in `attach_to_quest()`, fields `timeout_s`, `max_attempts`, `can_fail_silently`, and `metadata` were dropped because `QuestStep` lacked corresponding attributes.
- **Expected Behavior**: All validated execution semantics must survive persistence and be respected by the executor runtime.
- **Root Cause**: `QuestStep` schema in L10 was designed before `PlanStep` in L12 and was not reconciled.
- **Root-Cause Layer**: `CONTRACT`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Added `timeout_s`, `max_attempts`, `can_fail_silently`, and `metadata` to `QuestStep` in `omni_engine/contracts/quest.py`. Updated SQLite schema with migrations in `omni_engine/quest/store.py` (`_init_schema`, `_step_to_insert_row`, `_row_to_step`, `save_steps`, `update_step`, `get_step`, `attach_plan_atomic`, and `transition_step_atomic`). Updated `StructuredDAGPlanner.attach_to_quest()` to copy all semantics from `PlanStep` to `QuestStep`.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch3_PlanDurabilityAndPlanners::test_audit_09_plan_step_semantics_preserved_in_quest_step`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-010 (AUDIT-10): Template and Generative Planners Assign Blanket `max_attempts=3` Ignoring CapabilitySpec
- **Failure ID**: `FAIL-L14.1-010`
- **Checkpoint / Subsystem**: L12 / Planning Engines
- **Source Location**: `omni_engine/planning/template_planner.py:82` & `omni_engine/planning/generative_planner.py:182`
- **Observed Behavior**: Both planners instantiated `PlanStep` with hardcoded `max_attempts=3`, even for capabilities declared as `RetryPolicy.NEVER` or `IdempotencyClass.NON_IDEMPOTENT`.
- **Expected Behavior**: Step retry budgets must derive deterministically from `CapabilitySpec.retry_policy` and `idempotency_class` (e.g. non-idempotent mutations get `max_attempts=1`).
- **Root Cause**: Planners constructed steps with static defaults without querying `CapabilitySpec`.
- **Root-Cause Layer**: `IMPLEMENTATION` / `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Updated `SkillTemplatePlanner` and `GenerativePlanner` to query `CapabilitySpec`. When `spec.retry_policy == RetryPolicy.NEVER` or `spec.idempotency_class == IdempotencyClass.NON_IDEMPOTENT`, planners strictly set `max_attempts = 1`. Planners also propagate `spec.timeout_seconds` into `PlanStep.timeout_s`.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch3_PlanDurabilityAndPlanners::test_audit_10_planners_derive_max_attempts_from_capability_spec`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-011 (AUDIT-11): Generative Planner Allowed-Capability Boundary Escape
- **Failure ID**: `FAIL-L14.1-011`
- **Checkpoint / Subsystem**: L12 / Generative Planner
- **Source Location**: `omni_engine/planning/generative_planner.py:168-173`
- **Observed Behavior**: `generative_planner.py` only validated that synthesized capabilities exist in `self.registry`. If `allowed_capabilities` was supplied by routing, the planner formatted it in the prompt but never checked output steps against it, allowing model hallucinations to invoke arbitrary registered capabilities.
- **Expected Behavior**: Synthesized plan steps must strictly belong to `allowed_capabilities` if specified.
- **Root Cause**: Missing post-generation containment check against `allowed_capabilities`.
- **Root-Cause Layer**: `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: In `GenerativePlanner.synthesize_plan()`, added deterministic containment validation: if `allowed_capabilities` is not None and any synthesized step references a capability outside that list, raises `PlanValidationError`.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch3_PlanDurabilityAndPlanners::test_audit_11_generative_planner_enforces_allowed_capabilities_boundary`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-012 (AUDIT-12): Missing Input Argument Causes Terminal Step/Quest Failure Instead of `PAUSED_FOR_INPUT`
- **Failure ID**: `FAIL-L14.1-012`
- **Checkpoint / Subsystem**: L14 / Dynamic Argument Resolution & Pause Lifecycle
- **Source Location**: `omni_engine/contracts/execution.py`, `omni_engine/execution/dynamic_resolver.py`, `omni_engine/execution/executor.py`
- **Observed Behavior**: When dynamic resolution failed because a required `$inputs.<param>` was missing, `DynamicResolver` raised a generic `UnresolvedArgumentError`. `_execute_step()` caught it and marked the step as `FAILED`, and the coordinator loop halted the Quest as terminal `FAILED`.
- **Expected Behavior**: When a step requires an input parameter that is absent from `quest_inputs`, the resolution engine must differentiate missing user inputs from syntax/step lookup errors by raising `MissingInputError`. The executor must transition the step to `StepStatus.PAUSED` and the Quest to `QuestStatus.PAUSED_FOR_INPUT`. Resuming via `resume(quest_id, user_inputs={...})` merges user inputs, persists them in `quest.metadata["inputs"]`, transitions the quest back to `RUNNING`, and resumes DAG execution.
- **Root Cause**: `executor.py` and `DynamicResolver` conflated missing quest input arguments with internal resolution errors, failing terminally without giving the user or caller an opportunity to supply required parameters.
- **Root-Cause Layer**: `ARCHITECTURE` / `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**:
  1. Defined `MissingInputError(UnresolvedArgumentError)` with `input_key` attribute in `omni_engine/contracts/execution.py` and exported it from `omni_engine/contracts/__init__.py`.
  2. In `DynamicResolver._resolve_token()`, when looking up `$inputs.<subpath>`, if the path resolution fails, caught `UnresolvedArgumentError` and raised `MissingInputError(input_key=root_key)`.
  3. In `DeterministicDAGExecutor._execute_step()`, specifically caught `MissingInputError`, transitioned the step to `StepStatus.PAUSED`, and returned `StepExecutionReceipt(status=StepStatus.PAUSED)`.
  4. In `DeterministicDAGExecutor._run_coordinator_loop()`, when a receipt returns `StepStatus.PAUSED` with `"Missing required input"`, transitioned the quest to `QuestStatus.PAUSED_FOR_INPUT`.
  5. In `DeterministicDAGExecutor._resume_internal()`, merged `user_inputs` into `quest.metadata["inputs"]` and persisted it via `QuestStore.update_quest(quest)` before resuming traversal.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch4_ResolversResourcesAndLifecycle::test_audit_12_missing_input_pauses_quest_for_input_and_resumes`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-013 (AUDIT-13): Deterministic Plan Validator Missing Semantic Resource and Conflict Passes
- **Failure ID**: `FAIL-L14.1-013`
- **Checkpoint / Subsystem**: L13 / Plan Validation Firewall
- **Source Location**: `omni_engine/planning/validator.py`
- **Observed Behavior**: `DeterministicPlanValidator` executed 10 syntactic/boundary passes, but Pass 9 (`MUTATION_SAFETY`) only checked per-step attempt counts. It omitted checking whether two concurrent mutation steps target the same physical or logical resource without a causal dependency between them, risking race conditions and data corruption.
- **Expected Behavior**: Pass 9 (`MUTATION_SAFETY`) must compute transitive ancestors for all mutation steps and detect un-ordered concurrent mutations targeting the identical canonical resource identity (e.g. concurrent writes to `file:conflict.txt` with no dependency edge between them).
- **Root Cause**: Pass 9 lacked topological ancestor checking and resource identity collision analysis between concurrent mutation steps.
- **Root-Cause Layer**: `ARCHITECTURE`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**:
  1. Implemented transitive ancestor calculation (`step_ancestors[step_id] = ancestors`) via DFS traversal over `dependencies`.
  2. For every pair of non-read-only steps `(s1, s2)` that extract the same non-None `canonical_resource`: verified whether `s1` is an ancestor of `s2` or `s2` is an ancestor of `s1`. If neither is an ancestor, recorded a validation failure in Pass 9 (`MUTATION_SAFETY`) with detailed diagnostic error naming the conflicting steps and resource.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch4_ResolversResourcesAndLifecycle::test_audit_13_validator_detects_concurrent_resource_conflicts`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-014 (AUDIT-14): Mutation Locking is Purely Global Without Granular Resource Modeling
- **Failure ID**: `FAIL-L14.1-014`
- **Checkpoint / Subsystem**: L14 & L13 / Concurrency & Resource Isolation
- **Source Location**: `omni_engine/planning/validator.py`
- **Observed Behavior**: `DeterministicPlanValidator` lacked a canonical resource identity extractor, and `DeterministicDAGExecutor` relied solely on a global coarse lock without granular modeling.
- **Expected Behavior**: Deterministic extraction of canonical resource identities across capabilities: file paths (`file:<normalized_path>` with normalized slashes and traversal resolution), process IDs (`process:<pid>`), repo paths (`repo:<normalized_path>`), and browser sessions (`browser:<session_id>`).
- **Root Cause**: Resource extraction logic was not centralized or normalized into canonical URI schemes.
- **Root-Cause Layer**: `ARCHITECTURE` / `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Added `DeterministicPlanValidator.extract_resource_identity(step: PlanStep) -> Optional[str]` implementing canonical prefixing (`file:`, `repo:`, `process:`, `browser:`, `n8n:`) and POSIX path normalization using `os.path.normpath` and forward slashes.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch4_ResolversResourcesAndLifecycle::test_audit_14_canonical_resource_identity_extraction`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-015 (AUDIT-15): Deadline and Timeout Hierarchy Completely Unenforced in DAG Executor
- **Failure ID**: `FAIL-L14.1-015`
- **Checkpoint / Subsystem**: L14 / Resource Bounds & Timeout Enforcement
- **Source Location**: `omni_engine/execution/executor.py:350-420`
- **Observed Behavior**: Zero timeout checking existed in `executor.py`. If a plan execution ran indefinitely, the coordinator loop never checked elapsed time against `plan.timeout_budget_s`.
- **Expected Behavior**: Enforcement of Plan timeout budget in coordinator loop. When elapsed time exceeds `timeout_budget_s`, all in-flight workers must be cancelled, the Quest must transition to `QuestStatus.FAILED` with a diagnostic timeout reason, and the summary must report `final_status=QuestStatus.FAILED`.
- **Root Cause**: `timeout_budget_s` was stored in plan contracts and metadata, but never checked inside the Kahn coordinator traversal loop.
- **Root-Cause Layer**: `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**:
  1. Extracted `timeout_budget_s` from `quest.metadata["plan_provenance"]["timeout_budget_s"]` (defaulting to 3600.0).
  2. Reconstructed `Plan.timeout_budget_s` and `PlanStep.timeout_s` in `_reconstruct_plan(quest)`.
  3. At the top of every iteration of the coordinator while loop, computed `elapsed = time.perf_counter() - start_time`. If `elapsed > timeout_budget_s`, cancelled in-flight futures, transitioned quest to `FAILED`, and returned failure summary.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch4_ResolversResourcesAndLifecycle::test_audit_15_executor_enforces_plan_timeout_budget`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)

---

### FAIL-L14.1-016 (AUDIT-16): Cancellation Lifecycle Missing from DAG Executor
- **Failure ID**: `FAIL-L14.1-016`
- **Checkpoint / Subsystem**: L14 & L10 / Lifecycle Coordination
- **Source Location**: `omni_engine/execution/executor.py`
- **Observed Behavior**: No `cancel()` method existed on `DeterministicDAGExecutor`. Callers had no deterministic API to cancel active or paused quests.
- **Expected Behavior**: Deterministic cancellation: acquires execution lease, transitions all uncompleted steps (not already `COMPLETED`, `FAILED`, `SKIPPED`, `CANCELLED`) to `StepStatus.CANCELLED`, transitions Quest to `QuestStatus.CANCELLED`, records audit event `QuestEventEnum.QUEST_CANCELLED`, and returns `QuestExecutionSummary`.
- **Root Cause**: Cancellation method was omitted from executor public API.
- **Root-Cause Layer**: `IMPLEMENTATION`
- **Audit Status**: **REPRODUCED & VERIFIED REPAIRED**
- **Repair Made**: Implemented `DeterministicDAGExecutor.cancel(quest_id: str, reason: str = "Execution cancelled by user") -> QuestExecutionSummary` with lease acquisition, uncompleted step transitions, atomic quest cancellation, event logging, and execution summary envelope.
- **Regression Test Added**: `tests/test_l14_1_runtime_integrity.py::TestL14_1_Batch4_ResolversResourcesAndLifecycle::test_audit_16_deterministic_cancellation_lifecycle`
- **Commit Repairing Failure**: Working tree (staged for L14.1 commit)
