# ACTIVE_PLAN.md — Checkpoint L2.1: Contract & Registry Reconciliation (COMPLETED)

## 1. Objective & Scope (Completed)
Eliminate ambiguities in foundational contracts, establish the true source tool inventory (23 tools), expand the error taxonomy to 19 discrete error codes, add partial tool execution outcome semantics (`ToolOutcome: SUCCESS, PARTIAL, FAILURE`), establish `CapabilityInvocation` execution boundary, enrich `DecisionSignal` with provenance and calibration metadata, extend `TraceContext` with causal correlation fields, and pin dependencies.

---

## 2. Completed Scope Items (L2.1)

1. **Re-established 23-Tool Source Inventory**:
   - Programmatically validated `omni_engine/tools/` contains exactly 23 registered tools and zero unexported functions.
   - Categorization: Web (4), Browser (2), OS (8), Dev (6), Data (3).
   - Documented exact discrepancy: L0 inventory and README used legacy/aspirational aliases; source registry in `omni_engine/tools/__init__.py` is authoritative.
   - Added regression test `TestL21CanonicalRegistryInventory` in `tests/test_l2_1_reconciliation.py`.

2. **Complete 19-Member Error Taxonomy**:
   - `UNKNOWN`, `INVALID_ARGUMENT`, `SCHEMA_VIOLATION`
   - `UNCONFIGURED`, `AUTH_REQUIRED`, `PERMISSION_DENIED`, `UNAUTHORIZED_ACTION`, `CONFIRMATION_REJECTED`
   - `NOT_FOUND`, `ALREADY_EXISTS`, `CONFLICT`
   - `RATE_LIMITED`, `TIMEOUT`, `NETWORK_ERROR`, `SERVICE_UNAVAILABLE`
   - `PROCESS_FAILED`, `CANCELLED`
   - `UNKNOWN_COMMIT`, `INTERNAL_ERROR`
   - Clearly documented: `PERMISSION_DENIED` = external/OS refusal; `UNAUTHORIZED_ACTION` = internal policy refusal; `UNKNOWN_COMMIT` = mutation uncertainty (never blind retry).

3. **Extended Decision Signal Semantics & Provenance**:
   - Added `NEEDS_CLARIFICATION`, `REQUIRES_ACTION`, `NEEDS_GENERATIVE_REASONING`, `ESCALATION_REQUIRED`.
   - Added signal-level provenance fields: `provider_id`, `model_id`, `decision_schema_version`, `calibration_version`, `latency_ms`.
   - Updated `DecisionFrame` with typed fields for extended signals and `schema_version`.

4. **Explicit CapabilitySpec Policy Semantics**:
   - Renamed/clarified `minimum_autonomy_profile: AutonomyProfile`.
   - Introduced `ConfirmationPolicy`: `NEVER`, `POLICY_CONTROLLED`, `ALWAYS`.
   - Introduced `RetryPolicy`: `NEVER`, `SAFE_READ_RETRY`, `SAFE_WITH_IDEMPOTENCY`, `VERIFY_BEFORE_RETRY`.
   - Introduced `IdempotencyClass`: `READ_ONLY`, `NATURAL`, `LEDGER_REQUIRED`, `REMOTE_IDEMPOTENCY_KEY`, `NON_IDEMPOTENT`.
   - Maintained backward-compatible property facades (`autonomy_profile`, `requires_confirmation`, `retryable`, `idempotent`).

5. **Partial Tool Outcome Semantics**:
   - Introduced `ToolOutcome`: `SUCCESS`, `PARTIAL`, `FAILURE`.
   - Kept strictly separate from `VerificationStatus` (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`).
   - Enforced mutual exclusivity:
     - `SUCCESS` $\implies$ `success=True`, `error=None`.
     - `FAILURE` $\implies$ `success=False`, `error!=None`, `data=None`.
     - `PARTIAL` $\implies$ `success=False`, permits both partial `data` and `error` context.

6. **Capability Invocation Boundary Context**:
   - Created `CapabilityInvocation` with `invocation_id`, `capability_id`, `arguments`, `trace_context`, `attempt`, `deadline_seconds`, `current_autonomy_profile`, `quest_id`, `plan_id`, `step_id`, `operation_id`, `metadata`.

7. **Extended TraceContext**:
   - Created `omni_engine/contracts/trace.py` isolating `TraceContext` from circular dependencies.
   - Added correlation fields: `turn_id`, `quest_id`, `plan_id`, `step_id`, `operation_id`.

8. **Contract Versioning**:
   - Explicit `schema_version = "1.0.0"` on all wire/persisted contracts (`CapabilitySpec`, `CapabilityInvocation`, `DecisionFrame`, `AgentRequest`, `AgentResponse`, `AgentEvent`, `ToolResult`).
   - Documented continuous memory `schema_version = "2.5.0"` as storage format version decoupled from app version.

9. **Pydantic Dependency Compatibility Range**:
   - Pinned `pydantic>=2.0.0,<3.0.0` in `requirements.txt`.

10. **Test Coverage & Adversarial Review**:
    - Implemented `tests/test_l2_1_reconciliation.py` (15 comprehensive tests).
    - Total test suite: **55/55 passed (100%)** via `pytest`.
    - Adversarial review confirmed **PASS**.

---

## 3. Next Checkpoint: Checkpoint L3 Phased Architecture

Do **NOT** migrate everything at once. Structure L3 into 4 sub-phases:

### Phase L3A — Canonical Capability Registry
- Implement central `CapabilityRegistry`.
- Register the verified 23 tools under canonical IDs.
- Validate: unique IDs, versions, domains, schemas, action classes, availability metadata.
- Do NOT switch production agent dispatch yet.

### Phase L3B — Read-Only Capability Result Boundary
- Wrap read-only capabilities first (`ActionClass.READ_ONLY`).
- Catch runtime exceptions at capability boundary and normalize into structured `ToolResult(outcome=ToolOutcome.FAILURE, error=ToolError(...))`.
- Do NOT swallow `KeyboardInterrupt`, `SystemExit`, or process-control exceptions.

### Phase L3C — Mutation/System Capability Wrappers
- Add declarative wrappers and `CapabilitySpec` contracts for mutation and system-action capabilities.
- Do NOT expose them to broad autonomous dispatch before Checkpoint L9 (Policy Engine).

### Phase L3D — Legacy Compatibility
- Keep existing CLI/runtime operational via legacy path.
- Do NOT prematurely solve natural language argument extraction in L3 (slated for L8).
- Exercise new architecture tests strictly through typed `CapabilityInvocation` objects.
