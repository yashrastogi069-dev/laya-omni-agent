# KNOWN_ISSUES.md — Defect and Flaw Tracking

## Active Issue Index

### ISSUE-01: `tool_safe_math` NameError on Missing `re` Import & Computational Exhaustion
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint L1 & L1.1)**
- **Resolution**: Added `import re` and implemented a strict `ast.NodeVisitor` mathematical evaluator in `omni_engine/tools/data_tools.py`. Whitelisted safe arithmetic operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`), math library functions (`sqrt`, `abs`, `round`, `sin`, `cos`, etc.), and safe constants (`pi`, `e`, `tau`). In L1.1, added strict deterministic resource bounds:
  - Expression length <= 256 chars
  - AST node count <= 40 nodes
  - Factorial parameter limit: integer only, 0 <= n <= 100
  - Literal magnitude <= 1e100
  - Exponent magnitude abs(exp) <= 100, base <= 1e6 if exp > 10
- **Regression Test**: `tests/test_l1_repairs.py::TestL1SafeMathRepairs` (7 passed tests).

---

### ISSUE-02: `System1Router.route_tool` Slices Catalog to First 12 Items
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoints L6A & L6B)**
- **Resolution**: Implemented `HierarchicalRouter` in `omni_engine/routing/router.py`. Eliminates flat catalog dumps and fixed slices by routing through `Request → Domain → Skill → Small Candidate Set → Capability`, with automatic cross-domain pooling, keyword capability pinning, and anti-locking defenses.
- **Regression Test**: `tests/test_l6a_routing.py` and `tests/test_l6b_skill_routing.py`.

---

### ISSUE-03: Natural Language User Prompt Passed Verbatim as Tool Argument
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint L8)**
- **Resolution**: Implemented `ArgumentResolver` in `omni_engine/arguments/resolver.py` with deterministic regex and AST extractors in `extractors.py`, schema validation against `CapabilitySpec.input_schema`, alias bridging (`PARAM_ALIASES`), and structured clarification prompting (`CLARIFICATION_PROMPTS`).
- **Regression Test**: `tests/test_l8_arguments.py` (26 tests passing).

---

### ISSUE-04: Memory JSON Schema Key Inconsistency & Success Conflation
- **Severity**: HIGH
- **Status**: **RESOLVED (Checkpoint L1 & L1.1)**
- **Resolution**: Updated `OmniMemory._load()` in `omni_engine/memory.py` to dynamically migrate legacy keys (`tool_effectiveness` → `tool_success_counts`, `learned_facts` → `learned_insights`) with backward-compatible normalization. Implemented atomic file persistence (write-to-tmp then atomic replace) to prevent crash corruption. In L1.1:
  - Default outcome changed to `UNVERIFIED` (None). Execution never automatically implies verified success.
  - Three distinct outcome states tracked: `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`.
  - Invocations, verified successes, verified failures, and unverified runs tracked separately.
  - Corrupted or unparseable JSON files are automatically quarantined to `<filepath>.corrupt.<timestamp>` to preserve historical telemetry while recovering clean defaults.
- **Regression Test**: `tests/test_l1_repairs.py::TestL1MemoryRepairs` (4 passed tests).

---

### ISSUE-05: Dead Code in Planner and System 2
- **Severity**: MEDIUM
- **Status**: **RESOLVED (Checkpoints L10–L14)**
- **Reproduction**:
  `AutonomousPlanner.is_complex_multi_step()` and `System2Engine.escalate_to_antigravity()` were legacy prototype stubs.
- **Resolution**: Fully superseded by the persistent SQLite Quest runtime (L10), Structured DAG Planner (L12), Deterministic Plan Validator (L13), and Deterministic DAG Executor (L14). Legacy entrypoints remain untouched per the non-switching boundary.
- **Regression Test**: `tests/test_l12_planner.py` and `tests/test_l14_executor.py`.

---

### ISSUE-06: Discrepancy Between README Browser Capabilities and Codebase
- **Severity**: MEDIUM
- **Status**: **RESOLVED (Phase R2: Real Browser Engine)**
- **Resolution**: Implemented persistent session-backed Playwright engine (`omni_engine/browser/`) exposing atomic indexed action space (`@1..@N`), semantic fingerprinting, pre-execution staleness verification, evidence-based physical receipts (`dom_mutated`, `input_value`, `url_changed`), and registered capabilities `browser.interact` and `browser.perform_task`.
- **Regression Test**: `tests/test_r2_browser.py` (15 unit and integration tests passing offline).

---

### ISSUE-07: `WorkspaceConfiner.safe_revert` Wiping Pre-Existing Uncommitted User Work (Dirty Worktree Invariant)
- **Severity**: CRITICAL
- **Status**: **RESOLVED (Checkpoint RV0 Reality Gate)**
- **Description**: `WorkspaceConfiner.safe_revert()` inspected `git status --porcelain` and removed any untracked file (`??`) and checked out any modified file (`M`), which would destroy user work that existed in the working tree prior to task execution.
- **Resolution**: Implemented `WorkspaceConfiner.capture_baseline_state()` and updated `safe_revert(..., baseline_state=baseline_state)` to capture pre-existing dirty files and content byte-for-byte. Untracked baseline files are never deleted, and modified baseline files are restored to their exact baseline contents rather than clean git commit baseline.
- **Regression Test**: `tests/test_rv0_reality_gate.py::test_rv0_f_mandatory_dirty_worktree_survival` (passes 100%).

### ISSUE-08: Runtime Integrity, Durability & Failure Accountability Hardening (AUDIT-01 through AUDIT-16)
- **Severity**: HIGH
- **Status**: **RESOLVED (Checkpoint L14.1 Runtime Integrity Hardening)**
- **Description**: Independent source-level audit identified 16 latent failure modes across the L10–L14 runtime: mutation timeouts bypassing `UNKNOWN_COMMIT`, global idempotency key collision risk, missing custom idempotency key propagation, non-atomic SQLite multi-statement updates, interrupted step recovery to terminal failed, unpersisted plan provenance, loss of step semantics in QuestStep SQLite schema, planners deriving hardcoded retry attempts, generative planner capability boundary leakage, missing input parameters causing terminal quest failure instead of input pause, validator omitting concurrent resource mutation conflict detection, lack of canonical resource identity normalization, unenforced plan timeout budgets in executor coordinator loop, and absence of a deterministic cancellation lifecycle.
- **Resolution**: Implemented 16 scoped repairs across Batches 1 through 4, verified each with RED reproduced failures before repairs and GREEN passing tests after repairs. All defects, root causes, repairs, and invariants are fully documented in canonical `tasks/FAILURE_LEDGER.md`.
- **Regression Test**: `tests/test_l14_1_runtime_integrity.py` (16 unit tests, 100% passing). Total repository suite: 481 automated tests + 47 subtests = 528 checks passing.

---

### ISSUE-09: Runtime Closure, Adversarial Durability & Evidence Integrity Gate (L14.2-A through L14.2-P)
- **Severity**: HIGH
- **Status**: **RESOLVED & FULLY VERIFIED (Checkpoint L14.2)**
- **Description**: Independent audit found residual vulnerabilities in L14.1: lack of step-scoping in automatic idempotency keys, reliance on in-memory locks for attempt concurrency, missing UNIQUE constraint on `operation_attempts`, shallow `hasattr()` invariant proofs, unverified attempt consistency allowing stale attempts or zombie overwriting, unverified plan tamper firewall, loss of generative plan type during reconstruction, decorative `can_fail_silently` field, duplicate PAUSED step transitions, mutation timeout fail-fast instead of UNKNOWN_COMMIT quarantine, active cancellation blocked by lease collision, unpersisted reconciliation history, Python 3.12 SQLite `BEGIN IMMEDIATE` collisions, overly restrictive `PlanStep.timeout_s >= 1.0` constraint, ThreadPoolExecutor blocking on context exit after deadline, lack of physical interruption definition, missing durable cancellation intent on active mutation cancellation, missing custom idempotency conflict detection, missing reconciliation DB CAS, missing `fail_attempt_atomic` current-attempt parity, missing plan provenance in hash, and single-sample policy latency test flakiness.
- **Resolution**:
  1. *Step-Scoped Idempotency & Custom Conflict Protection*: Derived `idem_{quest_id}_{step_id}_{capability_id}_{arg_hash[:16]}` and raised `IdempotencyConflictError` if a custom key is reused with different capability or arguments (`test_a1`, `test_a6`).
  2. *Database-Level CAS Concurrency*: Implemented atomic conditional update `WHERE state IN ('pending', 'failed') AND current_attempt = ? AND current_attempt < max_attempts` backed by `UNIQUE(operation_id, attempt_number)` and `ConcurrentAttemptConflictError` (`test_c1`).
  3. *Transactional Fault Injection D1–D6*: Real mid-transaction exception injection verified rollback and consistency on cold reopen for begin attempt (D1), commit attempt (D2), fail attempt (D3), transition quest (D4), transition step (D5), and attach plan (D6) (`test_d1`–`test_d6`).
  4. *Attempt State Consistency & Current-Attempt Parity*: Aggregate root `operations` state validated first (freezing `UNKNOWN_COMMIT`), and `fail_attempt_atomic` checks `op_row["current_attempt"] != attempt.attempt_number` raising `StaleAttemptError` (`test_e1`–`test_e5`).
  5. *Complete Plan Provenance & Tamper Firewall F1–F5*: Canonical SHA-256 `Plan.compute_hash()` including `schema_version`, `plan_version`, `validator_version`, `validation_hash`, `validation_receipt`, and sorted `metadata`. Pre-execution firewall blocks tampered steps, capabilities, dependencies, phantom steps, and metadata/budget changes with `ExecutionFirewallError` (`test_f1`–`test_f5`).
  6. *Real Timeout Semantics & Non-Blocking Shutdown*: Eliminated ThreadPoolExecutor context block, used `pool.shutdown(wait=False, cancel_futures=True)`, documented CPython thread interruption limits, and promptly transitioned mutating steps to `UNKNOWN_COMMIT` and `AWAITING_RECONCILIATION` (`test_j1`–`test_j3`).
  7. *Active Mutation Cancellation & Reconciliation on Restart*: Persisted durable cancellation intent (`quest.metadata["cancellation_requested"] = True`), quarantined in-flight mutations as `UNKNOWN_COMMIT` in `PAUSED_FOR_RECONCILIATION` rather than premature `CANCELLED`, and on restart after reconciliation recognized cancellation intent and transitioned cleanly to `CANCELLED` (`test_k1`, `test_k2`).
  8. *Reconciliation DB CAS*: Conditional update `WHERE operation_id = ? AND state = ?` using `rec.prior_state.value`, rejecting conflicting concurrent reconciliations with `ConcurrentReconciliationConflictError` (`test_l2`).
  9. *Append-Only Reconciliation History*: SQLite table `operation_reconciliations` tracking immutable audit trail (`test_l1`).
  10. *Anti-Decorative Fields*: Pass 9 rejects `can_fail_silently=True` with explicit L16 replanner deferral note (`test_h1`).
  11. *Policy Latency Benchmark Distribution Proof*: Replaced fastest-of-five with a 20-run distribution verifying median < 2.0ms (sub-1ms SLA proof) in `tests/test_l9_policy.py`.
- **Regression Test**: `tests/test_l14_2_durability.py` (36 adversarial tests, 100% passing) and `tests/test_l9_policy.py` (26 tests, 100% passing). Total repository suite: 517 automated tests (+ 47 subtests = 564 checks) passing across 27 test files.
