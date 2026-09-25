# ADR-015: Structured DAG Planner & Template-First Precedence

- **Status**: ACCEPTED & IMPLEMENTED
- **Date**: 2026-09-25
- **Author**: Antigravity / LAYA Autonomous Core Team
- **Milestone**: Checkpoint L12 (LAYA Autonomous V2)
- **Supersedes**: N/A
- **Related ADRs**:
  - `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013: Persisted SQLite Quest Runtime)
  - `docs/research/ADR_L11_OPERATION_LEDGER.md` (ADR-014: Operation Ledger & Exactly-Once Mutation Semantics)
  - `docs/research/ADR_R5_DEVELOPER_AGENT.md` (Foreman Supervision & Bounded Convergence)

---

## 1. Context & Problem Statement

In autonomous multi-step execution, objectives can vary from well-understood routine workflows (e.g. Git feature branching, workspace setup, web research synthesis) to novel, open-ended requests.
Allowing general generative LLMs to produce unconstrained, arbitrary prose plans violates:
1. **Invariant 1 (Deterministic Control)**: Models must propose or plan, but DAG validation, dependency checking, and execution orchestration must be deterministic.
2. **Invariant 3 (Minimize Generative Invocations)**: Known Skill workflow templates must be prioritized before calling slow, costly generative LLMs.
3. **Invariant 5 (Persisted Quest + Validated DAG Execution)**: Plans must be strongly typed DAG structures attached to a persisted `Quest` entity with strict acyclicity and topological dependency ordering.

---

## 2. Prime Directive & Core Invariants

1. **Deterministic Control, Probabilistic Reasoning (Invariant 1)**:
   - The structured planner produces typed `Plan` and `PlanStep` instances.
   - All step IDs, dependency references, argument bindings, and cycle checks are strictly evaluated by deterministic algorithms (3-color DFS, Kahn's algorithm).
2. **Template-First Precedence (Invariant 3)**:
   - When a requested goal matches a registered canonical Skill with an existing `workflow_template`, the planner instantiates the plan from the template in `<1ms` without calling any generative LLM.
   - Dynamic parameter substitution supports `$inputs.<param>` resolution from extracted user arguments.
3. **Generative Fallback with Strict Schema Conformance**:
   - For novel objectives where no template applies, generative synthesis is bounded by strict JSON schema instructions.
   - Markdown code fences (` ```json ... ``` `) are automatically stripped, and any referenced capability must exist in the canonical `CapabilityRegistry`.
4. **Plan Bounds Enforcement**:
   - Total steps must not exceed `max_steps` (default 20).
   - Plan DAG depth must not exceed `max_depth` (default 6).
5. **Non-Switching Boundary**:
   - Legacy files `omni_agent.py` and `omni_engine/planner.py` remain completely untouched (0 diffs). New planning components reside in `omni_engine/planning/`.

---

## 3. Architecture & Components

```
                       User Objective / Request
                                  │
                                  ▼
                     StructuredDAGPlanner (engine.py)
                                  │
                   ┌──────────────┴──────────────┐
                   │ Skill has workflow_template?│
                   └──────────────┬──────────────┘
                         YES      │      NO
          ┌───────────────────────┘      └────────────────────────┐
          ▼                                                       ▼
SkillTemplatePlanner (<1ms)                            GenerativePlanner (LLM Fallback)
  - Instantiates SkillStepTemplates                      - Strict JSON Schema
  - Dynamic $inputs.<arg> substitution                   - Strips Markdown fences
  - Preserves declared dependencies                      - Validates against CapabilityRegistry
          │                                                       │
          └───────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
                         DAGTopology (dag.py)
                           - 3-Color DFS Cycle Detection
                           - Kahn's Algorithm Topological Sort
                           - In-degree & Ready Steps
                           - Plan Depth Calculation
                                  │
                                  ▼
                         Plan Bounds Verification
                           - steps <= max_steps (20)
                           - depth <= max_depth (6)
                                  │
                                  ▼
                           attach_to_quest()
                           - Transforms PlanStep -> QuestStep
                           - Maps CapabilitySpec.action_class
                           - Transitions Quest: CREATED -> PLANNED
```

---

## 4. Test Verification Evidence

All 20/20 unit tests in `tests/test_l12_planner.py` passed:
- `test_plan_contract_valid_and_forbids_extra`: Strict Pydantic contracts with `extra="forbid"`.
- `test_plan_rejects_duplicate_step_ids`: Prevents duplicate step identifiers.
- `test_plan_rejects_self_dependency`: Disallows self-referential steps.
- `test_plan_rejects_unknown_dependency`: Disallows dangling dependency IDs.
- `test_detect_cycle_2_nodes` / `test_detect_cycle_3_nodes`: 3-color DFS cycle detector proves acyclicity.
- `test_topological_sort_diamond_dag`: Correct topological order for diamond dependencies.
- `test_in_degrees_and_ready_steps`: Correct in-degree computation and initial root step identification.
- `test_compute_plan_depth`: Verifies accurate DAG critical path depth.
- `test_plan_from_skill_workflow_template`: Instant `<1ms` deterministic plan generation with `$inputs` substitution.
- `test_synthesize_plan_with_clean_json` / `test_synthesize_plan_strips_markdown_code_fences`: Robust parsing.
- `test_synthesize_plan_rejects_unknown_capability`: Prevents LLM hallucinations of unregistered tools.
- `test_synthesize_plan_rejects_cycles`: Generative outputs with cycles are intercepted and rejected.
- `test_template_first_precedence_for_canonical_skill`: Proves Invariant 3 template precedence.
- `test_plan_bounds_enforcement`: Rejects plans exceeding step or depth limits.
- `test_legacy_files_remain_untouched`: Non-switching boundary verification.

---

## 5. Decision Outcome

- **ADOPT**: Structured DAG planning engine, template-first precedence, strict schema bounds, and persisted Quest plan attachment.
