# ACTIVE_PLAN.md — Checkpoint R5: Developer Agent / Antigravity Engine (ACTIVE) & R1-R4 (COMPLETED)

## 1. Summary of Completed Checkpoint R4: n8n Automation Engine
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **25/25 unit and integration tests passed in 4.72s; 339/339 full repository tests (+ 47 subtests = 386 total) passed (100% pass rate)**.
- **Key Deliverables**:
  1. `docs/research/ADR_R4_N8N_AUTOMATION_ENGINE.md`: Technology audit adopting n8n v1 REST API, draft-test-validate lifecycle, and 7 blocking remediations. Status: **ACCEPTED**.
  2. `omni_engine/contracts/n8n.py`: Strongly typed contracts (`N8nTriggerType`, `N8nCredentialReference` with `extra="forbid"`, `N8nNode`, `N8nWorkflowSummary`, `N8nWorkflowDetail` with deterministic `compute_hash()`, `N8nWorkflowValidationResult`, `N8nExecutionReceipt`, `N8nActionResult`).
  3. `omni_engine/automation/scrubber.py`: `SecretScrubber` with compiled regexes for OpenAI (`sk-`), GitHub (`ghp_`), Bearer/Basic, AWS keys, n8n API keys, private keys, generic K-Vs, and header sanitization while preserving `$json.*` syntax.
  4. `omni_engine/automation/validator.py`: `N8nWorkflowValidator` parsing 3-level nested connections (`connections[src]["main"][idx] = [...]`), resolving name/ID bidirectionally, 3-color topological DFS cycle detector, in-degree constraints (`trigger in-degree == 0`, triggers >= 1), reachability analysis, and pre-flight parameter secret scan.
  5. `omni_engine/automation/transport.py`: Decoupled `N8nTransport` (ABC), `HttpN8nTransport` (production urllib + `ProxyHandler({})`), and `MockN8nTransport` (in-memory state machine for fast offline tests).
  6. `omni_engine/automation/client.py`: `N8nClient` enforcing draft mode (`active=False`) on creation, endpoints for activate/deactivate, execution trigger, and execution polling.
  7. `omni_engine/automation/engine.py`: `N8nAutomationEngine` implementing the Draft-Test-Validate lifecycle, Gate Triad enforcement for `activate_workflow` (1: Valid DAG, 2: Successful test run receipt for exact hash, 3: Zero secrets), bounded exponential backoff in `trigger_and_wait` with `"waiting"` state breakout.
  8. `omni_engine/automation/__init__.py`: Package exports.
  9. `omni_engine/policy/engine.py`: Mapped n8n high-risk node detection (`executeCommand`, `code`, `ssh`, `readWriteFile`) in `assess_action` and Stage 0 Rule-0 forbidden operations command scanner.
  10. `omni_engine/capabilities/definitions.py`: Registered 7 canonical n8n specs, adapters, and dotless aliases in `build_real_capability_registry()`, preserving 23-tool canonical registry.
  11. `omni_engine/capabilities/__init__.py`: Exported n8n capability specs and registration.
  12. `omni_engine/arguments/resolver.py`: Added n8n clarification prompts and slot extractors for `workflow_id`, `execution_id`, and `name`.
  13. `tests/test_r4_n8n.py`: 25 unit and integration tests passing in 4.72s.
- **Adversarial Reviews**:
  - Plan Review: Conditional Approval with 7 Blocking Requirements (`711073de-234c-46cc-8259-8bde4b647987`).
  - Diff Review: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)** (`901d60b3-003c-4854-9d3c-b76bed8c4f44`).
- **Non-Switching Principle**: `omni_agent.py` and `omni_engine/planner.py` remain 100% untouched (0 diffs).

---

## 2. Active Phase R5: Developer Agent / Antigravity Engine

### Objective
Build an official Developer Agent & Antigravity orchestration engine enabling LAYA to supervise and coordinate software engineering tasks:
1. **Antigravity CLI & Subagent Orchestration Adapter**:
   - Programmatic integration with Antigravity CLI (`agy`) and Google Antigravity SDK patterns.
   - Foreman-style supervisor architecture: LAYA acts as supervisor/orchestrator managing specialized developer subagents.
   - Execution isolation: workspace boundaries, scratch paths, isolated test sandboxes.
2. **Strongly Typed Developer Contracts (`omni_engine/contracts/developer.py`)**:
   - `DevTaskSpec`: repository root, task prompt, target files, test commands, timeout, max iterations.
   - `DevExecutionReceipt`: exit code, stdout/stderr, files modified, git diff summary, test results, duration.
   - `CodeVerificationReceipt`: deterministic verification of syntax, lint, type checks, and test pass/fail.
3. **Foreman / Developer Supervisor Engine (`omni_engine/developer/engine.py`)**:
   - Lifecycle: Plan → Inspect → Edit → Verify (Tests) → Review (Diff) → Commit/Report.
   - Deterministic process runner with bounded timeouts, output truncation guards, and zombie process cleanup.
4. **Safety & Policy Integration**:
   - Inviolable Rule-0 enforcement: Unconditionally deny `git reset --hard`, `git clean -fd`, `git push --force`, or destructive host commands.
   - Restrict dev operations to approved repository roots; prevent writing outside repository boundaries.
5. **Capability Registration**:
   - Register `developer.run_task`, `developer.run_tests`, `developer.git_diff`, `developer.inspect_code` in `CapabilityRegistry`, `PolicyEngine`, and `ArgumentResolver`.
   - Preserve 23-tool canonical registry invariant.
6. **Isolated Fixture Acceptance Test**:
   - End-to-end acceptance test in `tests/test_r5_developer.py` using a temporary isolated git fixture repository, executing code edits, running tests, capturing diffs, and verifying physical receipts 100% offline.

---

## 3. Strict Goal Boundaries
- Current Goal: `Foundation Gate (Complete) → R1 (Complete) → R2 (Complete) → R3 (Complete) → R4 (Complete) → R5 (Active)`
- **HARD STOP AFTER R5**:
  Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).

