# ADR-017: Deterministic DAG Executor Architecture

- **Status**: ACCEPTED & IMPLEMENTED
- **Date**: 2026-09-25
- **Author**: Antigravity / LAYA Autonomous Core Team
- **Milestone**: Checkpoint L14 (LAYA Autonomous V2)
- **Supersedes**: N/A
- **Related ADRs**:
  - `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013: Persisted SQLite Quest Runtime)
  - `docs/research/ADR_L11_OPERATION_LEDGER.md` (ADR-014: Exactly-Once Mutation Semantics)
  - `docs/research/ADR_L12_STRUCTURED_DAG_PLANNER.md` (ADR-015: Structured DAG Planner)
  - `docs/research/ADR_L13_PLAN_VALIDATOR.md` (ADR-016: Deterministic Plan Validator Firewall)

---

## 1. Context & Problem Statement

Multi-step autonomous execution requires a coordinator that safely schedules and executes operations across real tools and engines without:
1. Allowing generative models to own execution state, lifecycle transitions, or error handling (Invariant 1).
2. Dispatching unvalidated plans that contain cycles, missing dependencies, or policy denials (Invariant 5).
3. Blindly retrying uncertain mutations or re-executing already committed side effects (ADR-014).
4. Prematurely marking a task complete before outcome verification (Invariant 6).
5. Suffering concurrency race conditions on SQLite state updates or file locking contention on Windows.

---

## 2. Core Architectural Design

### 2.1 Single Coordinator Dispatcher Pattern (BLK-1)
To eliminate SQLite Optimistic Concurrency Control (OCC) collisions on the `quests` table:
- A single coordinator loop manages DAG topology, checks Kahn in-degrees, computes ready steps, and updates SQLite state machines.
- Worker threads in a bounded `ThreadPoolExecutor(max_workers=4)` execute capability functions only.
- Worker threads return execution envelopes via `concurrent.futures.as_completed()` to the coordinator.
- State transitions (`transition_step`, `transition_quest`) occur strictly on the coordinator thread, avoiding lock contention and OCC version thrashing.

### 2.2 Canonical State Binding (BLK-2)
- To eliminate contract fragmentation, execution contracts bind directly to canonical `StepStatus` from `omni_engine.contracts.quest`.
- Pauses are represented by `StepStatus.PAUSED` on the step and `QuestStatus.PAUSED_FOR_CONFIRMATION` or `QuestStatus.PAUSED_FOR_INPUT` on the quest.

### 2.3 Multi-Path Dynamic Argument Resolver (BLK-3)
- Evaluates `$inputs.<param>` against quest-level inputs.
- Evaluates `$steps.<step_id>.<path>` against previous step execution receipts.
- Exposes both `output` and `data` pointing to `receipt.data`. If `receipt.data` contains key `"output"`, exposes `output` as that inner value while preserving direct access to all keys in `data`.
- Automatically deserializes stringified JSON when a subpath navigates into a string node.
- Preserves native types (`int`, `dict`, `bool`) for exact token replacements, while supporting string interpolation for embedded expressions.

### 2.4 Strict Mutation Barrier & Windows File Lock Defense (BLK-4)
- Bounded concurrency: Independent `ActionClass.READ_ONLY` steps execute concurrently up to 4 parallel workers.
- Mutation Barrier: When a mutating step (`action_class != ActionClass.READ_ONLY`) becomes ready, the coordinator drains all active read worker tasks, acquires `_MUTATION_LOCK`, and executes the mutation in strict isolation.
- Guarantees zero concurrent filesystem writes and prevents Windows `[WinError 32]` file access conflicts.

### 2.5 Exactly-Once Mutation Semantics via Operation Ledger
- For every mutating step, the executor invokes `OperationLedger.record_attempt()`.
- Generates canonical operation IDs (`op_{quest_id}_{step_id}_{capability_id}`) and external idempotency keys.
- If an operation was already committed, returns cached receipts immediately (`is_deduplicated=True`) without re-executing.
- If an unhandled exception or timeout occurs, marks mutation as `UNKNOWN_COMMIT` and halts, preventing blind duplicate execution.

### 2.6 Lease Registry & Crash Recovery (BLK-5)
- An in-memory lease registry (`_active_quest_leases: Set[str]`) rejects duplicate concurrent `execute()` or `resume()` invocations with `QuestAlreadyRunningError`.
- Crash recovery: Upon resuming a quest with steps left in `StepStatus.RUNNING` from a crashed process, `READ_ONLY` steps are safely reset to `READY`, while mutating steps are checked against `OperationLedger`.

### 2.7 Invariant 6 Boundary: Awaiting Verification
- Upon successful execution of all plan steps, the quest transitions:
  `QuestStatus.RUNNING -> QuestStatus.AWAITING_VERIFICATION`.
- The executor strictly stops at `AWAITING_VERIFICATION`. Transitioning to `COMPLETED` is reserved for Checkpoint L15 (Completion Verifier).
