# ACTIVE_PLAN.md — Checkpoint L2: Foundational Typed Contracts

## 1. Objective
Establish the foundational, strongly typed contracts and data structures for the standalone LAYA autonomous agent.
All contracts will be authored using Pydantic (v2) under strict validation rules (`extra="forbid"`), ensuring deterministic boundaries between System 1 decisions, capability specifications, tool execution envelopes, verification receipts, and agent communication.

No runtime execution, planner, or executor logic will be implemented in L2; L2 is strictly the typing and contract substrate.

---

## 2. Checkpoint Scope

### Package: `omni_engine/contracts/`
1. **`enums.py`**:
   - `ActionClass`: `READ_ONLY`, `LOCAL_CREATE`, `LOCAL_UPDATE`, `LOCAL_DELETE`, `EXTERNAL_CREATE`, `EXTERNAL_UPDATE`, `EXTERNAL_SEND`, `EXTERNAL_DELETE`, `SYSTEM_ACTION`, `SECURITY_SENSITIVE`, `FINANCIAL`.
   - `AutonomyProfile`: `ADVISOR`, `SAFE_ASSISTANT`, `LOCAL_OPERATOR`, `TRUSTED_OPERATOR`, `WORKFLOW_AUTHORIZED`.
   - `ErrorCode`: `UNKNOWN`, `INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`, `CONFIRMATION_REJECTED`, `TIMEOUT`, `NETWORK_ERROR`, `PROCESS_FAILED`, `RATE_LIMITED`, `SCHEMA_VIOLATION`, `UNAUTHORIZED_ACTION`, `UNKNOWN_COMMIT`.
   - `VerificationStatus`: `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`.
   - `DecisionSignalType`: `INTENT`, `TASK_CLASS`, `DOMAIN`, `SKILL`, `URGENCY`, `IMPORTANCE`, `RISK`, `REVERSIBILITY`, `AMBIGUITY`, `NEEDS_PLAN`, `NEEDS_TOOLS`, `MODEL_TIER`.

2. **`decision.py`**:
   - `DecisionSignal`: typed single signal with value, confidence bounded in `[0.0, 1.0]` (rejecting NaN/Inf), probability distribution, latency, and metadata.
   - `DecisionFrame`: complete System 1 decision packet containing intent, task class, urgency, importance, risk, reversibility, ambiguity, needs_plan, needs_tools, model tier, candidate domains/skills, and latency profiling.

3. **`capability.py`**:
   - `CapabilitySpec`: pure JSON-serializable metadata contract separated from callables (`id`, `name`, `version`, `domain`, `description`, `action_class`, `autonomy_profile`, `idempotent`, `side_effects`, `requires_confirmation`, `retryable`, `timeout_seconds`, `input_schema`, `output_schema`, `verification_strategy`).
   - `ExecutableCapability`: Python-side runtime capability wrapper pairing a `CapabilitySpec` with an executable callable implementation and verifiers.
   - `ToolError`: structured error envelope with standardized `ErrorCode`, message, details dict, retryable boolean, and `fix_action`.
   - `ExecutionReceipt`: physical audit record of tool invocation (`receipt_id`, `operation_id`, `capability_id`, timestamps, duration_ms, exit_code, bytes_read, bytes_written, raw_output_ref).
   - `VerificationResult`: physical evidence verification record (`status`, `strategy`, `evidence`, notes, timestamp).
   - `ToolResult`: canonical tool response envelope enforcing:
     - If `success == True`, `error` MUST be `None`.
     - If `success == False`, `error` MUST NOT be `None` and `data` MUST be `None`.

4. **`agent.py`**:
   - `TraceContext`: distributed tracing context (`trace_id`, `parent_id`, `session_id`).
   - `AgentRequest`: inbound user/system query envelope with timestamp and trace context.
   - `AgentResponse`: structured terminal or intermediate agent output with decision frame, receipts, verifications, and timing.
   - `AgentEvent`: event envelope for internal asynchronous event bus.

5. **`__init__.py`**:
   - Clean top-level re-exports of all contracts.

---

## 3. Acceptance Criteria
1. Strict Pydantic model validation (`model_config = ConfigDict(extra="forbid")`) on all contract models.
2. Round-trip serialization/deserialization to JSON matches original data without loss.
3. Out-of-bounds confidence (e.g. `< 0.0` or `> 1.0`) raises `ValidationError`.
4. Invalid enum values raise `ValidationError`.
5. `ToolResult` model validator strictly rejects inconsistent states (`success=True` with `error`, or `success=False` without `error`).
6. `UNKNOWN_COMMIT` error code is present and distinct from generic failure.
7. Suite of unit tests in `tests/test_l2_contracts.py` passes 100%.

---

## 4. Rollback Plan
- Delete `omni_engine/contracts/` and `tests/test_l2_contracts.py`.
- Revert `requirements.txt` if needed.

