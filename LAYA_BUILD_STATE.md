# LAYA_BUILD_STATE.md — Current Ground Truth State

**Last Updated**: 2026-09-23T08:08:00+05:30  
**Current Branch**: `laya-autonomous-v2`  
**Active Checkpoint**: `L2 — Foundational Typed Contracts` (**COMPLETED**; preparing L3)  
**Last Passing Test Suite**: `tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py` (**40/40 passed via pytest in 6.11s**)  
**Mission Role**: Complete Standalone Autonomous Operating Agent.

---

## 1. Current Architecture Summary

The repository contains a standalone prototype CLI (`laya_agent.py` / `omni_engine/`) transitioning towards a **complete standalone autonomous operating agent**:
1. **System 1**: Local ModernBERT-large (`laya.Router()`) providing high-frequency decisions (<35ms).
2. **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, and execution.
3. **Phased Roadmap**: Checkpoints L0–L25 sequential evolution.
4. **Checkpoint L1 & L1.1 Milestone Reached**:
   - `tool_safe_math` rewritten with strict AST NodeVisitor, length limits (<= 256), node limits (<= 40), literal limits (<= 1e100), factorial limits (0 <= n <= 100), and exponent bounds (abs <= 100).
   - `OmniMemory` rewritten with dynamic schema key migration, atomic file persistence, corruption quarantining (`.corrupt.<timestamp>`), and 3-state verification tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`).
5. **Checkpoint L2 Milestone Reached**:
   - Canonical typed contracts created in `omni_engine/contracts/` using Pydantic v2.
   - Enums: `ActionClass` (11 levels), `AutonomyProfile` (5 tiers), `ErrorCode` (12 codes including `UNKNOWN_COMMIT`), `VerificationStatus` (3 states), `DecisionSignalType` (12 types including `REVERSIBILITY`).
   - System 1 Contracts: `DecisionSignal` (strictly bounded confidence in [0.0, 1.0], NaN/Inf rejection), `DecisionFrame`.
   - Capability Contracts: `CapabilitySpec` (pure JSON-serializable separated from callables), `ExecutableCapability`, `ToolError`, `ExecutionReceipt`, `VerificationResult`, `ToolResult` (enforcing mutual exclusivity between success and error).
   - Agent Envelopes: `AgentRequest`, `AgentResponse`, `TraceContext`, `AgentEvent`.
   - Global strict validation: `extra="forbid"` and `validate_assignment=True` across all models.

---

## 2. Component Health Matrix

| Component | Status | Operational Notes |
| :--- | :--- | :--- |
| `omni_engine.contracts` | **WORKING (VERIFIED)** | Canonical typed contracts package. Pydantic v2 data models with `extra="forbid"`, JSON round-trip serialization, strict error/success exclusivity. 18 dedicated tests passing. |
| `tool_safe_math` | **WORKING (VERIFIED)** | Strict AST NodeVisitor arithmetic evaluator with resource bounds (expression length <= 256, AST nodes <= 40, literal magnitude <= 1e100, factorial bounds 0 <= n <= 100, exponent bounds abs <= 100). Tested against sandbox escapes and computational exhaustion. |
| `OmniMemory` | **WORKING (VERIFIED)** | Backward-compatible schema migration (`schema_version = "2.5.0"`), atomic temporary-file persistence, corruption quarantining (`.corrupt.<timestamp>`), and explicit 3-state verification tracking (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`). |
| `System1Router` | **PROTOTYPE (LEGACY LIMITATION)** | Functional for first 12 registered tools. Legacy `[:12]` slice preserved for baseline regression testing; hierarchical capability routing scheduled for Checkpoint L6. |
| `AutonomousPlanner` | **LEGACY STANDALONE PROTOTYPE** | Rudimentary keyword matching. Scheduled for replacement by Structured DAG Planner & Deterministic DAG Executor in Checkpoints L12–L14. |
| `System2Engine` | **PROTOTYPE / REFERENCE** | OpenRouter LLaMA 3.3 70B client. Retained for generative planning, argument synthesis, and dossier generation. |
| Baseline Tools (OS, Dev, Web) | **WORKING / LEGACY** | Baseline capabilities functional. Scheduled for wrapping into canonical `CapabilitySpec` and `ToolResult` envelopes in Checkpoint L3. |

---

## 3. Current Blockers

- **None**. Checkpoints L0, L1, L1.1, and L2 are verified and passing 100% of automated tests (40/40).

---

## 4. Test Suite Baseline

- **Total Automated Tests**: 40 tests (`tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`).
- **Pass Rate**: 100% (40 passed, 0 failed, 0 errors).
- **Runtime**: 6.11s via `pytest`.

---

## 5. Next Checkpoint Scope: L3 (Canonical Capability Registry & ToolResult Envelopes)

1. Wrap all 23 existing tools into `CapabilitySpec` contracts with typed schemas.
2. Enforce standardized `ToolResult` return envelopes across all tools with zero uncaught exceptions.
3. Migrate tool execution from raw text strings to structured envelopes.
