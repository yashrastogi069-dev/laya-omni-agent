# HANDOFF.md — Operational Continuation Guide (Checkpoint L7 Complete, L6B Active)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: Sub-35ms bounded structured decisions via local ModernBERT-large (`laya.Router()`).
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Hierarchical Capability Routing**: Dynamic multi-tier tool catalog reduction (`Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`) eliminating flat catalog slicing and token bloat.
- **Skills Layer**: Reusable workflow manifests mapping objectives to constrained capability sets with safety policy floors.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `RouteDecision`, `SkillManifest`, `DecisionFrame`, `AgentRequest`, `AgentResponse`, `TraceContext`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L7 COMPLETED**; **L6B ACTIVE (Final Skill-Aware Hierarchical Router)**.
- Test Suite: **149/149 tests passing** (+ 23 subtests passed) across:
  - `tests/test_l0_baselines.py` (10 tests)
  - `tests/test_l1_repairs.py` (12 tests)
  - `tests/test_l2_contracts.py` (18 tests)
  - `tests/test_l2_1_reconciliation.py` (15 tests)
  - `tests/test_l3_capabilities.py` (25 tests, 23 subtests)
  - `tests/test_l4_providers.py` (19 tests)
  - `tests/test_l5_decision_fabric.py` (12 tests)
  - `tests/test_l6a_routing.py` (12 tests)
  - `tests/test_l7_skills.py` (26 tests)
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L7 Executed)
1. **Skill Contracts (`omni_engine/contracts/skill.py`)**:
   - `SkillStepTemplate`: Declarative workflow step model with `step_id`, `capability_id`, `description`, `depends_on`, `default_args`, `arg_mappings`, `verification_rule`, and `can_fail_silently`.
   - `SkillManifest`: Strongly typed skill contract defining `skill_id`, `version`, `domain`, `name`, `description`, `intent_patterns`, `input_schema`, `output_schema`, `required_capabilities`, `optional_capabilities`, `action_classes`, `workflow_template`, `planning_required`, `verification_strategy`, `applicable_autonomy`, `confirmation_policy`, and `escalation_conditions`.
   - Multi-Layer Safety Floors:
     - Phantom dependency rejection: `depends_on` entries must reference valid prior step IDs within the template.
     - Cycle detection: Three-color DFS cycle detector strictly forbids circular dependencies (`s1 -> s2 -> s1`).
     - High-risk confirmation floor: Skills containing high-risk action classes cannot declare `confirmation_policy=NEVER`.
2. **Skill Registry (`omni_engine/skills/registry.py`)**:
   - `SkillRegistry`: Thread-safe registry (`RLock`) enforcing:
     - Zero dangling capabilities: Every required, optional, and step capability must exist in `CapabilityRegistry`.
     - Action class encompassment: A skill cannot reference a capability whose action class is not declared in `manifest.action_classes` (blocks action-class omission spoofing).
     - High-risk confirmation floor: Registry independently verifies that constituent high-risk capabilities forbid `confirmation_policy=NEVER`.
     - Autonomy profile floor: A skill cannot declare an autonomy tier weaker than the minimum autonomy required by its constituent capabilities.
     - Mutation isolation: Deep copy returns prevent internal registry state corruption.
3. **Canonical Skill Definitions (`omni_engine/skills/definitions.py`)**:
   - 7 canonical skills backed 100% by the 23 verified tools: `web_research`, `inspect_repository`, `diagnose_system`, `file_transform`, `analyze_data`, `browser_information_task`, `perform_git_inspection`.
   - `build_canonical_skill_registry()` helper for canonical instantiation.
4. **Comprehensive Unit & Integration Test Suite (`tests/test_l7_skills.py`)**:
   - 26 tests covering contract invariants, cycle detection, phantom dependency rejection, policy floors, spoofing defenses, thread safety, canonical parity, and non-switching boundary.
5. **Regression Verification**:
   - Full repository test suite passed: **149 passed in 191.42s (100% pass rate)**.
   - Adversarial diff review passed with all 5 repairs verified.

---

## NEXT AGENT START HERE
- **Exact Current Branch**: `laya-autonomous-v2`
- **Active Checkpoint**: `L6B — Final Skill-Aware Hierarchical Router`
- **Last Passing Command**: `python -m unittest discover tests -v` (149 passed in 191.42s)
- **Failures / Blockers**: None.
- **Relevant Files**:
  - `omni_engine/contracts/routing.py` (extend `RouteDecision` with skill fields)
  - `omni_engine/routing/router.py` (integrate `SkillRegistry` and intent pattern matching)
  - `tests/test_l6b_skill_routing.py` (to create: comprehensive evaluation suite)
- **Hard Stopping Boundary**:
  - STOP BEFORE L8. Do NOT implement Argument Resolver (L8), Policy Engine (L9), Quest runtime (L10), Planner (L12), or DAG Executor (L14).
