# ADR-016: Deterministic Plan Validator Firewall

- **Status**: ACCEPTED & IMPLEMENTED
- **Date**: 2026-09-25
- **Author**: Antigravity / LAYA Autonomous Core Team
- **Milestone**: Checkpoint L13 (LAYA Autonomous V2)
- **Supersedes**: N/A
- **Related ADRs**:
  - `docs/research/ADR_L10_QUEST_RUNTIME.md` (ADR-013: Persisted SQLite Quest Runtime)
  - `docs/research/ADR_L11_OPERATION_LEDGER.md` (ADR-014: Exactly-Once Mutation Semantics)
  - `docs/research/ADR_L12_STRUCTURED_DAG_PLANNER.md` (ADR-015: Structured DAG Planner)

---

## 1. Context & Problem Statement

In autonomous multi-step execution, plans produced by generative models or instantiated from templates may contain structural flaws, invalid arguments, circular dependencies, policy violations, or unauthorized actions.
Allowing an unvalidated or partially-validated plan to enter execution violates:
1. **Invariant 1 (Deterministic Control)**: Models may propose or plan; deterministic runtime code must strictly validate, gate, and verify all operations before execution.
2. **Invariant 4 (Strongly Typed Contracts)**: Plans and step arguments must strictly adhere to schemas.
3. **Hard Policy Inviolability**: Destructive or forbidden commands (`git reset --hard`, protected system paths) must be rejected prior to execution.

---

## 2. The 10-Pass Deterministic Plan Validator Firewall

The `DeterministicPlanValidator` implements an in-memory verification firewall executing 10 deterministic passes:

| Pass # | Pass Name | Objective & Invariant Enforced |
| :--- | :--- | :--- |
| **Pass 1** | `DAG_ACYCLICITY` | 3-color DFS cycle detection; self-dependency rejection; duplicate step ID detection. |
| **Pass 2** | `DEPENDENCY_EXISTENCE` | Zero dangling dependencies: every dependency ID must exist within `plan.steps`. |
| **Pass 3** | `CAPABILITY_REGISTRATION` | Every step's `capability_id` must exist in `CapabilityRegistry` (including real engines). |
| **Pass 4** | `SCHEMA_CONFORMANCE` | Two-phase validation: Phase A verifies causal dependencies for `$steps.<id>` references; Phase B masks dynamic expressions with type-compliant dummy values for JSON schema verification. |
| **Pass 5** | `POLICY_FEASIBILITY` | Pre-flight `PolicyEngine.evaluate()` check. Blocks hard `DENY` commands/paths while masking dynamic placeholders to prevent false-positive path/extension denials. |
| **Pass 6** | `AUTONOMY_COMPLIANCE` | Enforces autonomy rank floor (`AUTONOMY_RANK`). Strictly disallows mutating actions under `ADVISOR` autonomy. |
| **Pass 7** | `STEP_COUNT_BOUNDS` | Enforces `1 <= len(plan.steps) <= max_steps` (default max 20). Rejects empty plans. |
| **Pass 8** | `GRAPH_DEPTH_BOUNDS` | Enforces `1 <= depth <= max_depth` (default max 6). Guards against cycles to prevent crashes. |
| **Pass 9** | `MUTATION_SAFETY` | Verifies that `NON_IDEMPOTENT` capabilities with `RetryPolicy.NEVER` declare `max_attempts <= 1`. |
| **Pass 10** | `RESOURCE_BUDGET` | Verifies positive wall-clock budget `<= max_timeout_budget_s` (3600s), and `step.timeout_s <= plan.timeout_budget_s`. |

---

## 3. Key Architectural Innovations & Defenses

1. **Two-Phase Schema Conformance (BLK-02)**:
   - Dynamic reference tokens like `$steps.step_1.output.id` are string expressions that would naively fail JSON schema validation on integer or array properties.
   - The validator identifies all `$steps.<ref_id>` tokens, proves `<ref_id>` is declared in `step.dependencies` (causal dependency requirement), and masks the token with a compliant dummy value for schema validation.
2. **False-Positive Policy Denial Prevention (BLK-03)**:
   - Dynamic path placeholders like `filepath="$steps.step_1.output.key"` could trigger `is_protected_path(".key")` inappropriately.
   - The validator masks dynamic string references during pre-flight policy evaluation, records a warning that dynamic evaluation is deferred to L14 execution runtime, while strictly intercepting literal violations (e.g. `git reset --hard` or `C:\Windows\System32`).
3. **Cumulative Diagnostic Reporting**:
   - Rather than failing fast on the first error, all 10 passes are evaluated and reported in `PlanValidationReport.passes`, giving planners complete diagnostics in a single evaluation round.

---

## 4. Test Verification Evidence

All 29/29 tests in `tests/test_l13_validator.py` passed in 6.81s:
- Contracts tested: `ValidationPassName`, `ValidationPassResult`, `PlanValidationReport` (`extra="forbid"`).
- Pass 1: Acyclic DAGs pass; self-loops, 2-node cycles, and duplicate IDs fail with `ErrorCode.CONFLICT`.
- Pass 2: Dangling step dependencies fail with `ErrorCode.INVALID_ARGUMENT`.
- Pass 3: Hallucinated/unregistered capabilities fail with `ErrorCode.NOT_FOUND`.
- Pass 4: Missing required fields, invalid argument types, missing causal dependencies, and phantom step references fail with `ErrorCode.SCHEMA_VIOLATION`. Dynamic arguments with causal dependencies pass.
- Pass 5: `git reset --hard` and System32 modifications fail with `ErrorCode.PERMISSION_DENIED`. Dynamic paths pass without false positives.
- Pass 6: Mutating steps under `ADVISOR` fail with `ErrorCode.UNAUTHORIZED_ACTION`. Insufficient autonomy fails.
- Pass 7: Empty plans (0 steps) and oversized plans fail with `ErrorCode.INVALID_ARGUMENT`.
- Pass 8: Deep chains exceeding `max_depth` fail. Cyclical plans do not crash.
- Pass 9: Excess attempts on non-idempotent capabilities fail with `ErrorCode.INVALID_ARGUMENT`.
- Pass 10: Negative budgets, excessive budgets, and step timeouts exceeding plan budget fail with `ErrorCode.TIMEOUT`.
- Golden multi-step diamond DAG: passes all 10 checks in <10ms.
- Non-switching boundary: `omni_agent.py` and `omni_engine/planner.py` have 0 diffs.

---

## 5. Decision Outcome

- **ADOPT**: Deterministic Plan Validator Firewall, 10 deterministic passes, two-phase schema conformance, dynamic placeholder causal dependency verification, and cumulative diagnostic reporting.
