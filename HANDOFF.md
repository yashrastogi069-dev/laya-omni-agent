# HANDOFF.md — Operational Continuation Guide (Checkpoint L6A Complete)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: Sub-35ms bounded structured decisions via local ModernBERT-large (`laya.Router()`).
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Hierarchical Capability Routing**: Dynamic multi-tier tool catalog reduction (`Request → DecisionFrame → Domain Routing → Candidate Pruning → RouteDecision`) eliminating flat catalog slicing and token bloat.
- **Skills Layer**: Reusable workflow manifests mapping objectives to constrained capability sets.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `RouteDecision`, `DecisionFrame`, `AgentRequest`, `AgentResponse`, `TraceContext`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L6A COMPLETED**; **L7 ACTIVE (Skills Substrate & Workflow Manifests)**.
- Test Suite: **123/123 tests passing** (+ 23 subtests passed) across:
  - `tests/test_l0_baselines.py` (10 tests)
  - `tests/test_l1_repairs.py` (12 tests)
  - `tests/test_l2_contracts.py` (18 tests)
  - `tests/test_l2_1_reconciliation.py` (15 tests)
  - `tests/test_l3_capabilities.py` (25 tests, 23 subtests)
  - `tests/test_l4_providers.py` (19 tests)
  - `tests/test_l5_decision_fabric.py` (12 tests)
  - `tests/test_l6a_routing.py` (12 tests)
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L6A Executed)
1. **Routing Contracts (`omni_engine/contracts/routing.py`)**:
   - `CapabilityCandidate`: Strongly typed candidate with `capability_id`, `domain`, `score` in [0.0, 1.0], `rationale`, and `spec_summary`.
   - `RouteDecision`: Hierarchical routing envelope with `selected_domain`, `candidate_domains`, ranked `candidates`, `is_fail_open`, `fallback_reason`, `catalog_reduction_ratio`, `total_registry_capabilities`, `latency_ms`, and `metadata`.
   - Strict validators: duplicate candidate rejection, fail-open reason consistency, candidate count <= total registry capabilities, finite bounded reduction ratio.
2. **Hierarchical Capability Router (`omni_engine/routing/router.py`)**:
   - `HierarchicalRouter`: Implements multi-tier catalog reduction pipeline (`Request → DecisionFrame → Domain Routing → Candidate Pruning → RouteDecision`).
   - Conversational Fast-Path: Deterministically bypasses tool scoring for empty/whitespace prompts (<5ms) and informational non-tool queries (`reduction_ratio=1.0`).
   - Automatic Cross-Domain Pooling (Rec-1): Always pools at least top-2 domains for multi-step tasks (`needs_plan=True` or `task_class in ["multi_step_quest", "code_refactor"]`).
   - Ambiguity & Low-Confidence Fail-Open (Rec-3): Pools adjacent domains when domain confidence <0.55 or ambiguity >0.65.
   - Explicit Keyword Capability Pinning (Rec-5): Declarative `CAPABILITY_PIN_MAP` regex scanning unconditionally pins named tools at score=1.0 with rationale `"explicit_keyword_pinned"`.
   - "General" Domain Technical Promotion (Rec-6): Promotes technical domains when `"general"` co-occurs with `needs_tools=True`.
   - Elimination of Sequential Latency Cliff (Rec-2): Zero-inference short circuit for single domains (count <= max_candidates) in <0.2ms; fast deterministic lexical token overlap scoring when pruning large sets in <1ms.
   - Elimination of Legacy Truncation Defect (ISSUE-02): Proved tools 13–23 (previously dropped by legacy `[:12]` slicing like `sqlite_exec`, `inspect_data`, `safe_math`, `powershell`, `ping_test`) are reliably accessible.
3. **Decision Fabric Hardening (`omni_engine/decision/fabric.py`)**:
   - Repaired ambiguous logic condition at lines 401–406: replaced buggy `ambiguity_sig.confidence > 0.65` with checks for `ambiguity_sig.value in ["ambiguous", True]`, numerical ambiguity value > 0.65, or `probabilities["ambiguous"] > 0.65`.
4. **Comprehensive Unit & Integration Test Suite (`tests/test_l6a_routing.py`)**:
   - 12 comprehensive unit and integration tests covering contract completeness, empty prompt fast-paths, conversational gating, single-domain filtering, bound pruning, cross-domain retention, fail-open pooling, keyword pinning, general domain promotion, legacy truncation elimination, non-switching boundary, and live ModernBERT neural routing.
5. **Regression Verification**:
   - Full repository test suite passed: **123 passed in 244.52s (100% pass rate)**.
   - Adversarial diff review passed with all invariants confirmed.

---

## NEXT AGENT START HERE
- **Exact Current Branch**: `laya-autonomous-v2`
- **Active Checkpoint**: `L7 — Skills Substrate & Workflow Manifests`
- **Last Passing Command**: `python -m unittest discover tests -v` (123 passed in 244.52s)
- **Failures / Blockers**: None.
- **Relevant Files**:
  - `omni_engine/contracts/skill.py` (to create: `SkillManifest`)
  - `omni_engine/skills/registry.py` (to create: `SkillRegistry`)
  - `omni_engine/skills/definitions.py` (to create: initial canonical skills)
  - `tests/test_l7_skills.py` (to create: test suite)
- **Exact Next Action**: Implement Checkpoint L7: `SkillManifest` contract, `SkillRegistry`, and initial canonical skills verified against `CapabilityRegistry`.
- **Things NOT to change**:
  - Keep `omni_agent.py` and `omni_engine/planner.py` on the legacy dispatch path (Non-Switching Principle until L8/L9).
  - Do NOT implement L8 Argument Resolver, L9 Policy Engine, L10 Quest persistence, or L14 DAG Executor during this phase.
  - Do NOT merge into `main`.
