# ADR_L10_QUEST_RUNTIME.md — Persistent Quest Runtime, SQLite Architecture & Durable Workflow Design

## Status: ACCEPTED (ADR-013)
**Date**: 2026-09-25  
**Milestone**: RV0 Reality Gate → L10 Quest Runtime → L11 Operation Ledger → L12 Planner → L13 Validator → L14 Executor  
**Target Branch**: `laya-autonomous-v2`  

---

## 1. Context & Problem Statement

Prior to Checkpoint L10, LAYA operates with a stateless execution loop where requests are resolved and executed within a single conversational turn. For complex real-world tasks (e.g. multi-source research, multi-file code refactors, multi-step browser interactions, and workflow automations), this architecture suffers from fundamental failure modes:
1. **Zero Crash Resilience**: If the agent process crashes, restarts, or loses power mid-task, all execution progress, intermediate receipts, and state are lost.
2. **Blind Duplicate Retries**: On timeouts or restart, retrying a multi-step task can execute destructive mutations twice (e.g. multiple git commits, duplicate API calls, repeated file writes).
3. **Generative Model Runtime Ownership**: Without a deterministic state engine, language models are asked to manage their own state transitions and history, violating Repository Invariant 1 (*Deterministic Control, Probabilistic Reasoning*).
4. **Lack of Pause/Resume for Approvals**: High-risk actions (`ActionClass.LOCAL_DELETE`, `FINANCIAL`, `SYSTEM_ACTION`) require explicit human confirmation. The agent must cleanly pause, persist its waiting state to disk, and resume when confirmation is granted without losing context.

---

## 2. Technology Audit & Architectural Evaluation

| Technology / Pattern | Evaluation | Decision | Rationale |
| :--- | :--- | :--- | :--- |
| **Temporal / Cadence** | Heavy distributed event-sourcing cluster with replay history | **REJECT / ADAPT CONCEPTS** | High operational footprint (requires JVM/Go daemon, Cassandra/Postgres, complex worker pool). Inappropriate for a lightweight local-first standalone agent on an 8GB machine. We **ADAPT** its core concepts: deterministic replay prevention, durable activity IDs, and receipt memoization. |
| **Inngest / Prefect** | Step-function DAG orchestrators | **REJECT / ADAPT CONCEPTS** | Cloud-dependent or heavy background service overhead. We **ADAPT** topological DAG dependencies, step-level memoization, and ready-step scheduling. |
| **LangGraph / Checkpointer** | In-memory graph with pickled SQLite checkpointing | **REJECT** | Fragile typing, pickle deserialization security risks, tight coupling to LangChain abstractions, and lack of typed operation identity ledger. Violates Invariant 4 (*Strongly Typed Contracts*). |
| **Atomic / Durable Workflows** | Persisted stage state, immutable artifacts, dependency graphs, approval gates, worktree isolation | **REFERENCE ONLY** | Excellent reference model for phase lifecycle and gate validation. We use its patterns as reference without introducing external dependency bloat. |
| **SQLite in Python 3.12 (Native `sqlite3`)** | Native embedded ACID database with WAL mode and PEP 249/PEP 684 explicit transactions | **ADOPT (PRIMARY RUNTIME)** | Zero background daemons, zero external processes, microsecond query latency, single-file storage, ACID transaction semantics, and universal platform compatibility on Windows/Linux/macOS. |

---

## 3. SQLite Engineering & Concurrency Invariants in Python 3.12

Python 3.12.10 includes SQLite 3.49.1 with updated transaction semantics (`autocommit=False` parameter in `sqlite3.connect`).

### 3.1 PRAGMA Configuration & WAL Mode
1. **`PRAGMA journal_mode = WAL;`**:
   - Write-Ahead Logging allows concurrent readers to operate without blocking writers, and writers do not block readers.
   - **Crucial Python 3.12 Invariant**: In SQLite, `PRAGMA journal_mode = WAL` and `PRAGMA synchronous` *cannot be changed inside an active transaction*. Therefore, initial database initialization and PRAGMA configuration must run with `autocommit=True` (or outside an open transaction block). Once set, WAL mode persists in the database file header.
2. **`PRAGMA synchronous = NORMAL;`**:
   - In WAL mode, `NORMAL` synchronous guarantees full ACID durability across application crashes while avoiding the extreme I/O overhead of `FULL` on Windows NTFS filesystems.
3. **`PRAGMA busy_timeout = 5000;`**:
   - If another connection holds a write lock, SQLite automatically waits and retries for up to 5,000 ms before raising `sqlite3.OperationalError: database is locked`.
4. **`PRAGMA foreign_keys = ON;`**:
   - SQLite disables foreign key enforcement by default for each connection. Every opened connection must explicitly execute `PRAGMA foreign_keys = ON;` to ensure cascade and referential constraints are strictly upheld between Quests, Steps, and Operations.

### 3.2 Threading & Connection Model
- SQLite connections cannot be shared across multiple threads concurrently without synchronization.
- **Connection-Per-Thread with Serialized Writers**:
  - Read-only operations use a thread-local connection with WAL mode concurrency.
  - State mutations and writes acquire an application-level `threading.RLock` (`_DB_WRITE_LOCK`) to serialize transaction commit boundaries and prevent `SQLITE_BUSY` contention on Windows.
- **Explicit Atomic Transactions**:
  - DML mutations run with `conn.autocommit = False`. Operations execute inside an explicit `try: ... conn.commit() except Exception: conn.rollback(); raise` block.

### 3.3 Optimistic Concurrency Control (OCC)
- Every mutable entity (`Quest`, `QuestStep`, `OperationRecord`) possesses an integer `version` field (starting at `1`).
- Updates must include the expected version in the `WHERE` clause:
  ```sql
  UPDATE quests 
  SET status = :new_status, version = version + 1, updated_at = :now
  WHERE id = :id AND version = :expected_version;
  ```
- If `cursor.rowcount == 0`, a concurrent update or race occurred. The runtime detects this immediately and raises `OptimisticConcurrencyError`.

---

## 4. Quest & Step State Machines

### 4.1 Quest Lifecycle State Machine
```
           ┌──────────────┐
           │   CREATED    │
           └──────┬───────┘
                  │ (Plan Generated & Validated)
                  ▼
           ┌──────────────┐
           │   PLANNED    │
           └──────┬───────┘
                  │ (Execution Dispatched)
                  ▼
    ┌────────► ┌──────────────┐ ◄──────────┐
    │          │   RUNNING    │            │
    │          └──────┬───────┘            │
    │ (Resumed)       │ (Needs Input /     │ (Resumed)
    │                 │  Confirmation)     │
    │                 ▼                    │
┌───┴──────────────┐     ┌─────────────────┴────┐
│ PAUSED_FOR_INPUT │     │ PAUSED_CONFIRMATION  │
└──────────────────┘     └──────────────────────┘
                  │ (All Steps Finished)
                  ▼
       ┌──────────────────────┐
       │ AWAITING_VERIFICATION│
       └──────────┬───────────┘
                  │ (Evidence Checked)
      ┌───────────┼───────────┐
      ▼           ▼           ▼
┌───────────┐┌───────────┐┌───────────┐
│ COMPLETED ││  FAILED   ││ CANCELLED │
└───────────┘└───────────┘└───────────┘
```

### 4.2 Step Lifecycle State Machine
- `PENDING`: Initial state waiting for dependency steps to succeed.
- `READY`: All incoming dependency steps have reached `COMPLETED`. Ready for scheduling.
- `RUNNING`: Actively being executed by capability runner.
- `PAUSED`: Waiting for user approval or slot clarification.
- `COMPLETED`: Successfully executed with valid `ToolResult` and evidence receipt.
- `FAILED`: Execution failed and retry budget exhausted.
- `SKIPPED`: Upstream dependency failed or branch condition evaluated to False.

---

## 5. Schema Design (L10 Foundation)

### 5.1 Table: `quests`
- `id` (TEXT PRIMARY KEY): Unique UUID string (`quest_<hex>`).
- `title` (TEXT NOT NULL): Short human-readable summary of the objective.
- `objective` (TEXT NOT NULL): Full original natural language objective.
- `status` (TEXT NOT NULL): Quest status enum string.
- `autonomy_profile` (TEXT NOT NULL): Autonomy tier under which quest executes.
- `session_id` (TEXT): Associated user session or thread.
- `plan_id` (TEXT): Current active plan identifier.
- `version` (INTEGER NOT NULL DEFAULT 1): OCC version counter.
- `metadata` (TEXT NOT NULL DEFAULT '{}'): JSON encoded metadata.
- `created_at` (TEXT NOT NULL): ISO-8601 UTC timestamp.
- `updated_at` (TEXT NOT NULL): ISO-8601 UTC timestamp.
- `completed_at` (TEXT): ISO-8601 UTC timestamp.

### 5.2 Table: `quest_steps`
- `step_id` (TEXT PRIMARY KEY): Unique string (`step_<hex>`).
- `quest_id` (TEXT NOT NULL REFERENCES quests(id) ON DELETE CASCADE).
- `capability_id` (TEXT NOT NULL): Canonical capability name.
- `status` (TEXT NOT NULL): Step status enum string.
- `intent` (TEXT NOT NULL): Natural language intent for this specific step.
- `arguments` (TEXT NOT NULL DEFAULT '{}'): Resolved typed input arguments JSON.
- `dependencies` (TEXT NOT NULL DEFAULT '[]'): JSON list of prerequisite `step_id`s.
- `retry_count` (INTEGER NOT NULL DEFAULT 0): Number of attempts made.
- `max_retries` (INTEGER NOT NULL DEFAULT 2): Maximum retry budget.
- `receipt` (TEXT): JSON encoded `ExecutionReceipt` or `ToolResult`.
- `error` (TEXT): Error message or JSON encoded `ToolError`.
- `version` (INTEGER NOT NULL DEFAULT 1): OCC version counter.
- `created_at` (TEXT NOT NULL): ISO-8601 UTC timestamp.
- `updated_at` (TEXT NOT NULL): ISO-8601 UTC timestamp.

### 5.3 Table: `quest_events`
- `event_id` (INTEGER PRIMARY KEY AUTOINCREMENT).
- `quest_id` (TEXT NOT NULL REFERENCES quests(id) ON DELETE CASCADE).
- `step_id` (TEXT REFERENCES quest_steps(step_id) ON DELETE CASCADE).
- `event_type` (TEXT NOT NULL): Enum string (`STATE_CHANGE`, `POLICY_EVALUATION`, `STEP_DISPATCH`, `RECEIPT_RECORDED`, `PAUSE_ENTERED`, `RESUME_TRIGGERED`, `ERROR`).
- `payload` (TEXT NOT NULL DEFAULT '{}'): JSON event payload.
- `timestamp` (TEXT NOT NULL): ISO-8601 UTC timestamp.

---

## 6. Implementation Plan & Gate Requirements

1. **Contract Definitions** (`omni_engine/contracts/quest.py`):
   - `QuestStatus`, `StepStatus`, `QuestEventEnum`.
   - `Quest`, `QuestStep`, `QuestEvent`, `QuestFilter`.
2. **SQLite Database Driver & Migrations** (`omni_engine/quest/store.py`):
   - Path default: `~/.laya/laya_quest.db`.
   - Strict connection management with `foreign_keys=ON`, `busy_timeout=5000`, WAL journal mode.
   - Transaction boundary helpers (`transaction()` context manager).
   - Atomic disk swaps and `.corrupt` quarantining.
3. **Quest State Engine** (`omni_engine/quest/engine.py`):
   - State transition validation (rejects invalid transitions).
   - Event logging for full auditability.
   - OCC error detection and recovery.
4. **Crash & Recovery Test Harness** (`tests/test_l10_quest.py`):
   - Test A: Full quest lifecycle (`CREATED -> PLANNED -> RUNNING -> COMPLETED`).
   - Test B: Restart mid-quest and recover unexecuted steps.
   - Test C: Optimistic concurrency collision detection.
   - Test D: Foreign key cascade integrity on deletion.
   - Test E: Multi-threaded concurrent readers and serialized writers under load.
