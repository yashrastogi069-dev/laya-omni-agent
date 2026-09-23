# AGENTS.md — Repository Operating Rules for AI Coding Agents

## 1. Prime Directive & Core Invariants

You are working on the **LAYA Omni Agent** repository.
The mission is not to make the repository "look agentic," but to make it **reliably agentic**.

Every AI coding agent operating in this repository MUST adhere strictly to the following invariants:

1. **Deterministic Control, Probabilistic Reasoning**:
   - Models may classify, rank, estimate, propose, plan, generate, or summarize.
   - Models must **NEVER** independently own persistent state transitions, dependency execution, confirmation enforcement, permissions, idempotency, mutation identity, retries, timeout budgets, policy, or completion state.
   - The deterministic runtime owns those.

2. **System 1 (LAYA) is a Fast Decision Nervous System, NOT a General LLM**:
   - Use LAYA aggressively for bounded, structured, low-latency decisions (<35ms): intent, task class, domain routing, skill selection, urgency, importance, risk, ambiguity, need-for-planning, need-for-tools, semantic verification, and model tier selection.
   - Never force LAYA to generate arbitrary prose, write arbitrary code, or produce long novel plans.

3. **Minimize Generative Model Invocations**:
   - Before invoking an expensive or slower generative LLM, verify whether deterministic code, a known Skill template, or a System 1 decision can solve the problem.
   - Generative calls are reserved strictly for: novel multi-step planning (when no template applies), schema-conforming argument synthesis (when deterministic parsing fails), code generation, and complex synthesis.

4. **Strongly Typed Capability Contracts**:
   - Every tool must be registered with a canonical `CapabilitySpec` defining input schema, output schema, action class, risk, idempotency, side effects, timeout, and verification strategy.
   - Never pass raw user natural language directly into tool functions unless the tool explicitly takes free-form text.
   - All tool executions must return a standardized structured envelope (`ToolResult`). Routine failures must never throw unhandled exceptions.

5. **Persisted Quest + Validated DAG Execution**:
   - Multi-step work must execute via a persisted Quest entity (backed by SQLite) and a validated DAG plan.
   - Planners produce plans; planners do **not** execute.
   - Executors execute plans step-by-step, checking preconditions, policies, operation idempotency, and verifiers.

6. **Evidence-Based Completion**:
   - Never report a task as completed without verifying the real-world outcome (file existence, exit code, process state, DOM state, database query).
   - Never confuse a plausible generated sentence with a real completed action.

7. **Signals are First-Class**:
   - Urgency, importance, risk, reversibility, ambiguity, and confidence are distinct, explicit signals. Never equate raw model confidence with urgency or truth.

---

## 2. Engineering Workflow & Phased Checkpoints

Follow the disciplined phased workflow:
`RECON → INTERROGATE → PLAN → ADVERSARIAL PLAN REVIEW → IMPLEMENT → VERIFY → ADVERSARIAL DIFF REVIEW → REPAIR → DOCUMENT EVIDENCE → CHECKPOINT`

- **Small Checkpoints**: Follow checkpoints L0 through L25 sequentially as laid out in `tasks/MASTER_PLAN.md`.
- **Active Plan**: Only ONE checkpoint is active at any time, documented in `tasks/ACTIVE_PLAN.md`.
- **Permanent Scope-Control Rule**: If an idea or feature is not required for the current active checkpoint, record it in `tasks/DEFERRED.md`. Do not implement deferred items prematurely.
- **Red/Green/Refactor**: For every confirmed defect:
  1. Reproduce with a targeted test.
  2. Prove the test fails (Red).
  3. Implement the smallest root-cause fix.
  4. Prove the test passes (Green).
  5. Run adjacent regression tests.
  6. Update `tasks/KNOWN_ISSUES.md`.

---

## 3. Forbidden Operations

1. **NO Destructive Git Commands**:
   - Never run `git reset --hard`, `git clean -fd`, or force-push over remote branches without explicit user consent.
   - Never delete prototype code or user files during exploratory phases.
2. **NO Unconfirmed High-Risk Actions**:
   - Any action falling into action classes `LOCAL_DELETE`, `EXTERNAL_DELETE`, `EXTERNAL_SEND`, `SYSTEM_ACTION`, `SECURITY_SENSITIVE`, or `FINANCIAL` must strictly pass through policy checks and confirmation gates.
3. **NO Recursive Agent Invocation**:
   - Subagents must not recursively invoke each other in unbounded cycles. Use read-only subagents for adversarial reviews and plan validation.

---

## 4. Documentation Synchronization Rules

The following canonical documentation files MUST be maintained in exact synchronization with repository truth:

| Document | Purpose |
| :--- | :--- |
| `AGENTS.md` | Operating rules, invariants, and conventions (this file). |
| `LAYA_BUILD_STATE.md` | Single source of ground truth: working components, defects, blockers, last passed test suite. |
| `HANDOFF.md` | Operational continuation guide for the next agent session. |
| `tasks/MASTER_PLAN.md` | Strategic migration roadmap covering checkpoints L0 through L25. |
| `tasks/ACTIVE_PLAN.md` | Single active checkpoint execution plan with acceptance criteria. |
| `tasks/DECISIONS.md` | Architectural Decision Records (ADRs). |
| `tasks/KNOWN_ISSUES.md` | Tracking confirmed defects, severity, reproductions, and status. |
| `tasks/DEFERRED.md` | Valuable out-of-scope work intentionally postponed. |
| `tasks/lessons.md` | Durable engineering lessons discovered during development. |
| `docs/ARCHITECTURE.md` | Current executable architecture vs Target architecture. |
| `docs/CAPABILITY_CONTRACT.md` | Canonical specification for capability schemas, inputs, outputs, and safety. |
| `docs/AUTOMATION_MODEL.md` | Triggers, scheduled automations, conditions, and Quest dispatch rules. |
| `docs/SECURITY_AND_POLICY.md` | Action classification, autonomy tiers, approvals, and injection defenses. |
| `LAYA_CORE_IMPLEMENTATION_REPORT.md` | Long-form evidence report with benchmark data and defect analyses. |

---

## 5. Review & Subagent Guidelines

- **Adversarial Review**: Before implementing architectural changes, use a secondary model or read-only subagent to critically assess the plan for race conditions, schema mismatches, policy bypasses, and missing edge cases.
- **Independent Validation**: The author of a substantial architecture change must never be its sole reviewer.
