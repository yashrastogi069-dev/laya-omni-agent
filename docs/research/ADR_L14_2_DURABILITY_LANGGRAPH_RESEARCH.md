# ADR-019: Durable Execution, Failure Accountability & Upstream Architecture Alignment (LangGraph Durability Research Gate)

**Status**: ACCEPTED  
**Date**: 2026-09-26  
**Checkpoint**: L14.2 — Runtime Closure, Adversarial Durability & Evidence Integrity Gate  
**Deciders**: Antigravity Engineering & Architecture Reviewer  

---

## 1. Context & Problem Statement

Checkpoint L14.1 implemented critical durability features for the LAYA Omni Agent autonomous runtime (OperationLedger atomic writes, QuestStore atomic transitions, recovery of interrupted read-only steps, and UNKNOWN_COMMIT pausing). However, an independent source audit identified residual durability and consistency edge cases:
1. Conflation of logical operation identity across distinct steps in the same quest.
2. In-memory locking without database-level conditional CAS (Compare-And-Swap) for attempt concurrency.
3. Lack of an enforced plan provenance firewall (tampered steps in SQLite could execute).
4. Absence of an append-only audit trail for UNKNOWN_COMMIT reconciliation.
5. Inability to actively cancel a running Quest without encountering lease contention (`QuestAlreadyRunningError`).

To ensure LAYA's durable execution model adheres to modern industry state-of-the-art standards, this architectural research gate evaluates upstream durable workflow patterns (specifically from LangGraph and related durable workflow engines) as **REFERENCE ONLY**.

---

## 2. Upstream Technology Audit & Pattern Classification

> **CRITICAL INVARIANT**: Under no circumstances will LangGraph, LangChain, or heavy external workflow orchestrators be installed or imported into LAYA Core during L14.2. LAYA is a standalone, lightweight (<15MB resident footprint), deterministic autonomous operating agent. The patterns below are analyzed strictly for design principles to inform LAYA's native SQLite and contract substrate.

| Upstream Durable Pattern | How LangGraph / Upstream Implements It | How LAYA Evaluates It | Classification | L14.2 Native Implementation |
| :--- | :--- | :--- | :--- | :--- |
| **Durable Checkpointing** | Saves state channels at every super-step via persistent checkpointer (e.g. `SqliteSaver`, `PostgresSaver`). | Essential for fault tolerance. LAYA already persists state in SQLite (`quests`, `quest_steps`, `operations`). | **ADAPT** | Transition from multi-statement writes to database-level atomic transactions and CAS conditional updates (`WHERE state IN (...) AND current_attempt = ?`). |
| **Interrupt & Resume (HITL)** | Nodes call `interrupt(value)`, halting execution; resumed via external `Command(resume=value)` with thread configuration. | Essential for human confirmation and missing argument collection without polling or busy loops. | **ADAPT** | Native `PAUSED_FOR_CONFIRMATION` and `PAUSED_FOR_INPUT` states. Resumed cleanly with `resume(user_confirmation=..., user_inputs=...)` without duplicate state transitions. |
| **Side-Effect Replay & Idempotency** | Relies on nodes being idempotent or external caching wrappers. Replaying from checkpoint can duplicate external side effects if not handled. | LangGraph's weakness is LAYA's core strength. LAYA rejects blind side-effect replay. | **ADOPT & ENHANCE** | `OperationLedger` enforces cryptographic argument hashing, quest-and-step-scoped idempotency keys, and cached receipt reuse (`is_deduplicated=True`). |
| **State History vs Overwriting** | Versions checkpoints and state diffs so execution history and time-travel are preserved. | Overwriting uncertain mutation states destroys operational audit truth. | **ADOPT** | Added append-only `operation_reconciliations` table recording prior state, reconciled state, physical evidence, timestamp, and audit notes. |
| **Deterministic Boundary Control** | Nodes execute arbitrary Python code. Generative LLMs often direct graph routing dynamically. | Violates Invariant 1 (Deterministic Control). Models propose; deterministic runtime executes. | **REJECT** | Maintain strict pre-execution firewall (`DeterministicPlanValidator` 10 passes) and plan provenance verification (`Plan.compute_hash()`). |
| **Framework Installation** | Importing `langgraph` or `langchain_core` as runtime dependencies. | Adds 50+ transitive dependencies, unpredictable memory consumption, and outside orchestration locks. | **REJECT** | Zero imports of LangGraph/LangChain. 100% native Python 3.12 standard library (`sqlite3`, `concurrent.futures`, `hashlib`, `json`). |

---

## 3. Detailed Architectural Decisions for L14.2

### 3.1 Database-Level CAS (Compare-And-Swap) for Attempt Concurrency
- **Problem**: In L14.1, `OperationLedger.begin_attempt()` read state and then called `store.begin_attempt_atomic()`. If two concurrent threads or processes competed, both could observe `PENDING / current_attempt=0` and race. In-process `RLock` does not protect against multi-process or separate connection contention.
- **Decision**: Implement database-level conditional update in `OperationStore.begin_attempt_cas()`:
  ```sql
  UPDATE operations
  SET state = 'IN_PROGRESS',
      current_attempt = current_attempt + 1,
      updated_at = ?
  WHERE operation_id = ?
    AND state IN ('PENDING', 'FAILED')
    AND current_attempt = ?
    AND current_attempt < max_attempts
  ```
  If `cur.rowcount == 1`, the caller won the attempt CAS lease and proceeds to insert `operation_attempts`. If `cur.rowcount == 0`, raises `ConcurrentAttemptConflictError`.
- **Constraint**: Add `UNIQUE(operation_id, attempt_number)` to SQLite `operation_attempts` schema.

### 3.2 Scoped Logical Operation Identity
- **Problem**: Automatic idempotency key was previously `idem_{quest_id}_{capability_id}_{arg_hash[:16]}`. Two different steps in the same Quest running identical capabilities with identical arguments collided.
- **Decision**: Update automatic idempotency key to include `step_id`:
  `idem_{quest_id}_{step_id}_{capability_id}_{arg_hash[:16]}`.
  Caller-supplied custom idempotency keys remain supported for explicit cross-quest bridging when desired.

### 3.3 Plan Provenance & Tamper Firewall
- **Problem**: L14.1 stored `plan_hash` in `quest.metadata`, but `executor.py` never verified it upon execution or restart. Persisted arguments in SQLite could be tampered with without detection.
- **Decision**: Add `Plan.compute_hash()` to generate canonical SHA-256 over all steps, dependencies, arguments, and bounds. Upon execution and recovery, `DeterministicDAGExecutor` reconstructs the plan, recomputes the hash, and asserts match with `quest.metadata["plan_hash"]`. If tampered, halts immediately with `ExecutionFirewallError` (zero capability executions).

### 3.4 Active Cancellation Protocol
- **Problem**: `cancel(quest_id)` acquired `_lease_lock` with `_active_leases`, raising `QuestAlreadyRunningError` if called while a Quest was active.
- **Decision**: Implement cancellation token / intent registry:
  - If quest is active, `cancel(quest_id)` registers a cancellation token `_cancellation_tokens[quest_id] = reason`.
  - The Kahn coordinator loop checks `_cancellation_tokens` on every iteration.
  - Upon cancellation signal: coordinator ceases scheduling new steps, drains running workers, marks uncompleted steps `CANCELLED`, and transitions the quest to `CANCELLED`.

### 3.5 Append-Only Reconciliation History
- **Problem**: When an `UNKNOWN_COMMIT` operation was reconciled, `operations.state` was overwritten, erasing the record that an uncertainty had occurred.
- **Decision**: Create relational table `operation_reconciliations` in SQLite. When `reconcile_operation()` is invoked, an immutable record is inserted storing `reconciliation_id`, `operation_id`, `prior_state`, `reconciled_state`, `evidence`, `note`, `timestamp`, and `actor`.

---

## 4. Consequences & Invariant Protections

- **Safety**: Exactly-once mutation semantics are physically guaranteed at the SQLite database layer rather than relying on in-memory locks.
- **Auditability**: Every uncertainty, state change, and reconciliation is preserved in append-only SQLite tables.
- **Zero Framework Bloat**: Achieved with 0 external dependencies, maintaining sub-15MB runtime footprint.
- **Isolation**: Non-switching boundary (`omni_agent.py` and `omni_engine/planner.py`) remains 100% untouched (**0 diffs**).
