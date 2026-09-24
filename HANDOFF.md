# HANDOFF.md — Operational Continuation Guide (Checkpoint L7.5 Complete, Proceeding to L8)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: High-frequency structured decisions via local ModernBERT-large (`laya.Router()`) with calibrated probability bounds and two-stage adaptive triage.
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Hierarchical Capability Routing**: Dynamic multi-tier tool catalog reduction (`Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`) eliminating flat catalog slicing and token bloat.
- **Skills Layer**: Reusable workflow manifests mapping objectives to constrained capability sets with safety policy floors.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `RouteDecision`, `SkillManifest`, `DecisionFrame`, `CalibrationConfig`, `AgentRequest`, `AgentResponse`, `TraceContext`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L7.5 COMPLETED & VERIFIED**; **PROCEEDING TO L8 (Typed Argument Resolution & Extraction Engine)**.
- Test Suite: **181/181 tests passing** (+ 23 subtests passed) across:
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
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L7.5 Executed)
1. **Source-Truth Gate A (SkillManifest Invariants)**:
   - `omni_engine/skills/registry.py`: Autonomy profile floor validator upgraded to inspect ALL constituent capabilities (`required_capabilities | optional_capabilities | step_capabilities`), ensuring optional tools cannot require higher autonomy than declared by the skill.
2. **Source-Truth Gate B (Hardware & Latency Truth)**:
   - Measured host reality: Windows 10, 4-core CPU, 7.81 GB RAM, PyTorch 2.13.0+cpu, NO CUDA.
   - Resident RAM: 1.64 GB RAM for ModernBERT-large. Cold load: 69.3s.
   - CPU Latency: p50 = 749ms (1 question) to 15.4s (15 questions).
   - Proven: <35ms is CUDA-only; two-stage Adaptive Triage is empirically justified.
3. **Calibration Contracts (`omni_engine/contracts/calibration.py`)**:
   - `CalibratedModelThresholds`: `domain_confidence_min: 0.55`, `ambiguity_max: 0.65`, `skill_candidate_min: 0.50`, `skill_selection_min: 0.75`, `skill_description_overlap_ceiling: 0.50`.
   - `DeterministicPolicyThresholds`: `pinned_capability_score: 1.0`, `skill_required_capability_score: 0.98`, `skill_optional_capability_score: 0.75`, `domain_primary_default_score: 0.85`, `domain_pooled_default_score: 0.70`, lexical scoring parameters.
   - `CalibrationConfig`: Master configuration bundle with version tracking.
4. **Upstream Alignment & RAM Safety (`omni_engine/providers/system1.py`)**:
   - Strict `max_loaded=1` enforcement with pre-eviction `unload()` + `gc.collect()`.
   - Process-wide thread lock (`_ROUTER_LOCK`) wrapping inference.
   - Guarded preload: `names=[model_name]`, never loading all 3 checkpoints simultaneously on 8GB host.
   - Configurable model selection (`english`, `multilingual`, `typed-decisions`).
5. **Decision Evaluation Corpus (`omni_engine/decision/eval_corpus.py`)**:
   - 103 reviewable ground-truth labeled cases across all 6 domains, prompt injection, and automation workflows.
6. **Hardware-Aware Benchmark (`omni_engine/decision/benchmark.py`)**:
   - Telemetry measuring cold start, batch scaling, adaptive triage, and graceful unconfigured Jev handling.
7. **Decision Fabric Adaptive Triage (`omni_engine/decision/fabric.py`)**:
   - `evaluate_adaptive()` evaluates 4 triage questions for informational queries and exits early, saving ~11.8s on CPU.
8. **Shadow Semantic Skill Routing (`omni_engine/routing/router.py`)**:
   - Integrated shadow semantic evaluation and agreement tracking into `HierarchicalRouter`.
9. **Test Suite & Adversarial Review**:
   - 16 new tests in `tests/test_l7_5_calibration.py`.
   - Full suite: **181/181 passing (100%)**.
   - Adversarial diff review: **PASS ✅**.

---

## NEXT AGENT START HERE
- **Exact Current Branch**: `laya-autonomous-v2`
- **Active Checkpoint**: **Checkpoint L8 — Typed Argument Resolution & Extraction Engine**
- **Last Passing Command**: `python -m unittest discover tests -v` (181 passed in 48.60s)
- **Failures / Blockers**: None.
- **Goal Scope & Hard Stopping Boundary**:
  - Current multi-phase goal covers: `L7.5 (Done) → L8 (Next) → L9 (After L8)`.
  - **STOP AFTER L9**. Do NOT implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).


