# HANDOFF.md — Operational Continuation Guide (Foundation Gate COMPLETED; Phase R1 ACTIVE)

## What We Have Built (Current State)
A **trustworthy pre-execution control plane, provider broker, and autonomous agent routing substrate** powered by:
- **System 1 Provider Broker (Foundation Gate)**: Fast provider routing under ironclad User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlist enforcement, and task overrides.
- **Hierarchical Two-Level Locking**: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner, with exclusive permit draining on swaps/evictions, eliminating lock inversions and PyTorch C++ access violations.
- **Strict English-Only Invariant**: Prohibits multilingual checkpoints and language detection routines, conserving host RAM and eliminating scope drift.
- **Debounced Windows RAM Protection**: Telemetry via `psutil` with Windows `ctypes.windll.kernel32.GlobalMemoryStatusEx` fallback; requires 3 consecutive breaches over >=5s before idle eviction.
- **Empirical Concurrency Benchmark**: Concurrency benchmark harness in `omni_engine/decision/concurrency_benchmark.py` measuring levels 1, 2, 4 on CPU. Proven: cold load takes 47.4s / 1.67 GB RAM; warm inference is ~712ms (concurrency 2: 2.79 req/s).
- **Deterministic Stratified Calibration**: 70/30 stratified partition (72 dev / 31 test) and 10-bin Expected Calibration Error (ECE) metric evaluation harness in `omni_engine/decision/calibration_eval.py`.
- **System 1 Decision Fabric (L7.5)**: High-frequency structured decisions via local ModernBERT-large (`laya.Router()`) with calibrated probability bounds and two-stage adaptive triage.
- **Hierarchical Capability Routing (L6A/L6B)**: Dynamic multi-tier tool catalog reduction (`Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`) eliminating flat catalog slicing and token bloat.
- **Skills Layer (L7)**: Reusable workflow manifests mapping objectives to constrained capability sets with safety policy floors and cycle detection.
- **Typed Argument Resolution Engine (L8)**: Deterministic parameter extraction in 0.118 ms across 23 canonical tools with schema validation, alias bridging, and zero-hallucination clarification gating.
- **Deterministic Policy Engine & Constraints (L9)**: Sub-millisecond (~0.15ms warm) deterministic policy gate enforcing Inviolable Rule-0 Invariants (`user_confirmed` strictly ignored on forbidden operations), boundary-aware user blacklists, autonomy profiles (ADVISOR read-only floor), confirmation policies (ALWAYS/POLICY_CONTROLLED), and non-disruptive shadow mode simulation.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `RouteDecision`, `SkillManifest`, `DecisionFrame`, `CalibrationConfig`, `ArgumentResolutionEnvelope`, `PolicyDecision`, `PolicyRule`, `ActionAssessment`, `BrokerDecision`, `CalibrationMetrics`, `AgentRequest`, `AgentResponse`, `TraceContext`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Milestone Goal: **Real Capability Engines: Foundation Gate (COMPLETE & VERIFIED) → Phase R1 (ACTIVE)**.
- Full Test Suite: **259/259 tests passing (+ 47 subtests = 306 total, 100% pass rate)** in 160.33s across 14 test modules:
  - `tests/test_l0_baselines.py` (10 tests)
  - `tests/test_l1_repairs.py` (12 tests)
  - `tests/test_l2_contracts.py` (18 tests)
  - `tests/test_l2_1_reconciliation.py` (15 tests)
  - `tests/test_l3_capabilities.py` (25 tests, 23 subtests)
  - `tests/test_l4_providers.py` (19 tests)
  - `tests/test_l5_decision_fabric.py` (12 tests)
  - `tests/test_l6a_routing.py` (12 tests)
  - `tests/test_l7_skills.py` (26 tests)
  - `tests/test_l6b_skill_routing.py` (16 tests)
  - `tests/test_l7_5_calibration.py` (16 tests)
  - `tests/test_l8_arguments.py` (26 tests)
  - `tests/test_l9_policy.py` (25 tests)
  - `tests/test_foundation_broker.py` (27 tests)
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Deliverables Summary for Foundation Gate
1. **Contracts (`omni_engine/contracts/broker.py`)**:
   - `ProviderSelectionMode` (USER_LOCKED, USER_PREFERRED, AUTO).
   - `BrokerRoutingOutcome` (DETERMINISTIC_NO_MODEL, LAYA_ENGLISH, LAYA_TYPED_DECISIONS, JEV, DUAL_CHECK, GENERATIVE_ESCALATION).
   - `FallbackReason` (NONE, PROVIDER_UNHEALTHY, PROVIDER_UNCONFIGURED, RAM_PRESSURE, QUEUE_TIMEOUT, PRIVACY_RESTRICTION, QUALITY_FLOOR_BREACH, CONTEXT_LIMIT_EXCEEDED).
   - `TaskProviderOverride` & `ProviderPolicyConfig`.
   - `BrokerDecision` with decomposed latencies (`broker_latency_ms`, `queue_wait_ms`), target/selected provider provenance, and fallback telemetry.
   - `CalibrationMetrics` with ECE, F1, accuracy, and calibration gate evaluation.
2. **Two-Level Hierarchical Locking & Memory Guards (`omni_engine/providers/system1.py`)**:
   - Level 1 `_MODEL_LIFECYCLE_LOCK` (RLock) outer; Level 2 `_INFERENCE_SEMAPHORE` (Semaphore) inner.
   - `_drain_inference_permits()` for exclusive mutation safety.
   - Bounded queue timeout (`5.0s`).
   - English-only model constraint (`VALID_LOCAL_MODELS = ("english", "typed-decisions")`).
   - Debounced Windows RAM protection.
3. **Provider Broker (`omni_engine/providers/broker.py`)**:
   - `SystemOneBroker` implementing `SystemOneProvider`.
   - Precedence hierarchy: `USER POLICY → ALLOWLIST → PRIVACY/OFFLINE → TASK OVERRIDE → QUALITY → HEALTH → RESOURCE PRESSURE → COST`.
4. **Empirical Benchmarks & Calibration Partitioning**:
   - `omni_engine/decision/concurrency_benchmark.py`: concurrency levels 1, 2, 4.
   - `omni_engine/decision/calibration_eval.py`: 72 dev / 31 test stratified split.
5. **Independent Adversarial Review**: **PASS (UNCONDITIONAL)** (`5e8a88cd-a846-4ef9-b639-22afb9b791c2`).

---

## Operational Boundary & Next Phase
- **Active Phase**: **Phase R1 — Deep Research Engine**.
- **Hard Stop Boundary**: Stop cleanly after R5. Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
