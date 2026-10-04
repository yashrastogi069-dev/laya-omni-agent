# ADR-021: Controlled Replanner, Sub-DAG Replacement, Blast-Radius Containment & Bounded Recovery Loop (L16)

- **Date**: 2026-10-05
- **Status**: ACCEPTED
- **Authors**: LAYA Core Autonomous Architecture Team
- **Checkpoint**: L16 (Controlled Replanner)

---

## 1. Context & Problem Statement

In Checkpoints L10–L14.3, LAYA developed a deterministic execution pipeline:
`Objective → Decomposer → Template/Generative Planner → Plan Validator → Quest Persistence → DAG Executor → Evidence Verifier`.

In the current runtime (`omni_engine/execution/executor.py`):
1. When any step encounters an execution error (`ToolResult.outcome == FAILURE` or unhandled tool exception), the coordinator halts execution and transitions the entire Quest to `QuestStatus.FAILED`.
2. All subsequent work is aborted, even when the failed step is non-critical, alternative capabilities could fulfill the requirement, or simple parameter/strategy adjustment could recover.
3. Conversely, unconstrained LLM agent loops ("ReAct retry loops") are notoriously prone to infinite looping, thrashing between mutually contradictory actions, and repeating already completed destructive mutations.
4. Furthermore, Pass 9 of `DeterministicPlanValidator` intentionally deferred `can_fail_silently=True` to Checkpoint L16.

We require a **deterministic, controlled replanning and recovery subsystem** that:
- Detects recoverable step and verification failures.
- Computes the exact "blast radius" (the failed step and its transitive downstream dependents).
- Preserves all already completed steps, their physical execution receipts, and their `OperationLedger` idempotency tokens (zero re-execution of committed mutations).
- Synthesizes a replacement sub-DAG to fulfill the remaining unfulfilled requirements.
- Strictly validates the spliced plan through the 10-pass `DeterministicPlanValidator` before execution.
- Enforces hard bounds on replanning attempts (`max_replans=3`) to prevent infinite recovery loops.
- Supports `can_fail_silently=True` for optional or non-critical steps.

---

## 2. Decision & Architectural Invariants

### 2.1 Separation of Concerns & Deterministic Sovereignty (Invariant 1)
- Generative models and planners may *propose* alternative steps or replacement sub-DAGs.
- Deterministic software strictly owns the replanning decision, blast-radius calculation, preservation of completed steps, cycle detection, budget tracking, and plan splicing.
- Generative models have zero authority to bypass replan budgets or erase executed mutation records.

### 2.2 Replanning Triggers (`ReplanTrigger`)
Replanning can be triggered by four explicit events:
1. `STEP_FAILURE`: An unrecoverable tool execution failure or tool exception occurs during step dispatch (and `can_fail_silently=False`).
2. `PRECONDITION_FAILED`: Dynamic argument resolution fails (e.g. prerequisite step output is missing an expected key or has an incompatible shape).
3. `TIMEOUT`: A step times out without mutation commit uncertainty.
4. `VERIFICATION_FAILED`: L15 evidence verification proves a physical artifact is missing or an assertion failed after execution, requiring targeted remediation.

### 2.3 Blast-Radius Containment & Preservation of Completed Work
When step $S_{fail}$ fails:
1. **Transitive Downstream Dependents**: Compute $Descendants(S_{fail})$ using topological graph traversal:
   $$Descendants(S_{fail}) = \{ s \in Steps \mid S_{fail} \in Ancestors(s) \}$$
2. **Blast Radius**:
   $$BlastRadius = \{ S_{fail} \} \cup Descendants(S_{fail})$$
3. **Preserved Step Set**:
   $$Preserved = Steps \setminus BlastRadius$$
4. **Preservation Invariant**:
   - All steps in $Preserved$ with status `StepStatus.COMPLETED` remain strictly `COMPLETED`. Their outputs and execution receipts are preserved in the execution context and made available as `$steps.<id>.output` references to new steps.
   - Any steps in $Preserved$ with status `PENDING` or `READY` (independent branches) remain untouched and ready for execution.
   - Mutating steps that committed side effects are NEVER re-executed (enforced by `OperationLedger` idempotency).

### 2.4 Replanning Scopes (`ReplanScope`)
The replanner operates under three hierarchical scopes:
1. `STEP_RETRY_WITH_VARIATION`: Replace only the failed step with an alternative capability or adjusted parameters (e.g. alternate web search tool or modified query).
2. `SUB_DAG_REPLACE`: Replace the failed step and its direct/indirect dependents with a new sub-DAG that fulfills the equivalent requirement.
3. `FULL_REPLAN`: If the blast radius invalidates all remaining plan steps, generate a fresh sub-plan covering the remaining unverified requirements using preserved step outputs as quest inputs.

### 2.5 Monotonic Plan Versioning & Provenance
When a replan succeeds:
1. `plan.plan_version` increments monotonically ($plan\_version \leftarrow plan\_version + 1$).
2. `plan.plan_type` is set to `PlanType.COMPOSITE` (or preserved).
3. A new canonical `plan.compute_hash()` is generated.
4. The revised plan is attached to the Quest in SQLite, and a `QuestEvent` with type `PLAN_ATTACHED` and `metadata={"replan_version": ..., "trigger": ..., "blast_radius": ...}` is appended.

### 2.6 Pre-Execution Validation Firewall on Spliced Plans
Every spliced or revised plan MUST pass through all 10 passes of `DeterministicPlanValidator`:
1. `DAG_ACYCLICITY`: Graph must be acyclic (no circular dependencies introduced by splicing).
2. `DEPENDENCY_EXISTENCE`: Every dependency must point to a valid preserved step or newly introduced step.
3. `CAPABILITY_REGISTRATION`: All capabilities must exist in `CapabilityRegistry`.
4. `SCHEMA_CONFORMANCE`: Argument schemas must conform.
5. `POLICY_FEASIBILITY`: Pre-flight policy checks (no forbidden commands or protected path violations).
6. `AUTONOMY_COMPLIANCE`: Must respect the granted autonomy profile.
7. `STEP_COUNT_BOUNDS`: Total steps $\le max\_steps$.
8. `GRAPH_DEPTH_BOUNDS`: Depth $\le max\_depth$.
9. `MUTATION_SAFETY`: Concurrency and idempotency safety.
10. `RESOURCE_BUDGET`: Timeout budget bounds.

If validation fails, the spliced plan is rejected immediately; the Quest transitions to `FAILED`.

### 2.7 Anti-Looping & Termination Bounds
To prevent infinite replanning:
1. **Replan Attempt Limit**: `max_replans = 3` per quest.
2. **Replan Depth Limit**: `max_replan_depth = 2`.
3. **Anti-Oscillation Gate**: If a proposed replacement step has the identical capability and argument fingerprint as a step that previously failed in the same quest, the replan is rejected.
4. When budget is exhausted, the Quest transitions to `QuestStatus.FAILED`.

### 2.8 Support for `can_fail_silently=True`
In Pass 9 (`MUTATION_SAFETY`), `can_fail_silently=True` is now supported:
- If a step has `can_fail_silently=True` and fails:
  - It does NOT trigger a replan or quest failure.
  - The step is transitioned to `StepStatus.SKIPPED` (or `COMPLETED` with error recorded).
  - Downstream steps that do not depend on its output continue executing normally.

---

## 3. Consequences

### Positive
- Robust recovery from transient network issues, unavailable tools, and bad argument formulations without restarting multi-step workflows from scratch.
- Preserves expensive completed work (e.g. web research dossiers, repository checkouts).
- Guaranteed protection against infinite loops and mutation re-execution.
- 100% adherence to repository prime directives and invariants.

### Negative / Trade-Offs
- Splicing and sub-DAG grafting adds DAG topology manipulation complexity.
- Requires careful dependency reference re-mapping.
