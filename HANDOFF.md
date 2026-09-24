# HANDOFF.md — Operational Continuation Guide (Real Capability Engines R1–R5 ALL COMPLETED)

## What We Have Built (Current State)
A **trustworthy pre-execution control plane, provider broker, and five complete real capability execution engines** powered by:
- **Phase R5: Developer Agent & Antigravity Orchestration Substrate**:
  - `DeveloperSupervisorEngine`: Foreman 5-stage bounded supervision lifecycle (Setup/Baseline -> Mutation -> AST Syntax Gate -> Test -> Convergence/Reversion).
  - Deterministic Thrashing & Oscillation Detection: Composite SHA-256 state fingerprinting over working tree `git diff`, sorted modified file names, and raw binary file contents.
  - `DeterministicSubprocessRunner`: Windows `CREATE_NEW_PROCESS_GROUP`, `communicate(timeout=...)` deadlock defense, `taskkill /F /T /PID` process-tree termination, quote-stripping argument parser, and 50k character output truncation.
  - `WorkspaceConfiner`: Validates `.git` presence, blocks protected OS roots (`is_protected_path`), verifies path containment (`is_relative_to` & `commonpath`), anti-tampering on test suites (`allow_test_edits=False`), and safe file-by-file revert (`git checkout -- <file>`, `os.remove` for untracked files) strictly avoiding destructive `git reset --hard` or `git clean -fd`.
  - Decoupled `AgyRunner` ABC (`SubprocessAgyRunner` for local `agy.exe`, `MockAgyRunner` for offline simulation).
  - Capability Substrate: Registered `developer.run_task`, `developer.run_tests`, `developer.git_diff`, `developer.inspect_code`.
  - Unit test suite `tests/test_r5_developer.py` (25/25 passed in 17.33s).
  - Adversarial Review: **PASS (100% compliant with all 7 blocking requirements and repository operating invariants)** (`fb7ba688-2887-47fa-811d-d25dbe922f53`).
- **Phase R4: n8n Automation Engine**:
  - `N8nClient`: Programmatic integration with n8n v1 REST API (`/workflows`, `/executions`), strictly enforcing draft mode (`active=False`) on creation.
  - `N8nWorkflowValidator`: Acyclic DAG verification with 3-color topological DFS cycle detector, 3-level nested schema parsing (`connections[src]["main"][idx] = [...]`), bidirectional node ID/name resolution, trigger node in-degree constraints (`in-degree == 0`, trigger count >= 1), and pre-flight parameter secret scan.
  - `SecretScrubber`: Multi-pattern secret scrubber detecting and scrubbing OpenAI, GitHub, AWS, Bearer/Basic, n8n API keys, private keys, generic tokens, and headers while safely preserving `$json.*` and `={{ ... }}` expressions.
  - `N8nAutomationEngine`: Enforces Draft-Test-Validate Gate Triad for `activate_workflow` (1: Valid DAG, 2: Successful test run receipt for exact hash, 3: Zero secrets), bounded exponential backoff in `trigger_and_wait` with `"waiting"` state breakout.
  - Policy & RCE Defense: Detection of high-risk node types (`executeCommand`, `code`, `ssh`) with blast radius escalation to `LOCAL_SYSTEM` / `SECURITY_CRITICAL` and composite risk >= 0.70. Rule-0 embedded command scanning on `executeCommand` parameters to block forbidden operations.
  - Decoupled `N8nTransport` (ABC), `HttpN8nTransport`, and `MockN8nTransport` running 100% offline in <5s.
  - Capability Substrate Integration: Registered 7 canonical n8n capabilities (`n8n.list_workflows`, `n8n.get_workflow`, `n8n.validate_workflow`, `n8n.create_workflow`, `n8n.activate_workflow`, `n8n.trigger_workflow`, `n8n.get_execution_status`).
  - Unit test suite `tests/test_r4_n8n.py` (25/25 passed in 4.72s).
- **Phase R3: Windows Desktop, App & Local Service Engine**:
  - `Win32Backend` & `AppWindowManager`: Safe activation without `AttachThreadInput`, `ctypes.windll.user32.IsHungAppWindow` pre-check, simulated menu key event (`VK_MENU`) for legitimate foreground rights, non-blocking `ShowWindowAsync(SW_RESTORE)` for minimized windows (`IsIconic`), and async activation polling.
  - Process Trampoline Resolution: Pre-launch baseline HWND diffing (`current_hwnds - baseline_hwnds`) combined with recursive child-tree traversal (`psutil.Process.children(recursive=True)`), returning strongly typed physical receipts (`launcher_pid`, `active_pid`, `hwnd`, `bounds`).
  - `LocalServiceProber`: Loopback dual-stack cascade (`127.0.0.1` -> `::1`), `SO_LINGER` to prevent `TIME_WAIT` socket buildup, isolated `ProxyHandler({})` opener to bypass host proxy environment traps, bounded 4KB HTTP reads, and strict timeouts (<=500ms socket, <=1500ms HTTP).
  - Rule-0 Process Safety Defense: Dual-layer enforcement in `PolicyEngine` Stage 0 and `AppWindowManager` pre-flight checks blocking critical OS processes (`csrss`, `lsass`, `smss`, `services`, `wininit`, `winlogon`, `system`, PID 0, PID 4), strictly ignoring human confirmation.
  - `WindowsInputDriver`: Pre-focus verification and non-intrusive `WM_CHAR` character dispatch.
  - Offline test suite `tests/test_r3_desktop.py` (21/21 passed in 0.953s).
- **Phase R2: Real Persistent Browser Engine**:
  - `BrowserSession`: Persistent isolated profile context (`~/.laya/browser_profile`), stale singleton lock recovery, single page invariant (`max_pages=1`), `atexit` cleanup, and 9 low-memory launch flags.
  - `DOMActionIndexer`: Dynamic indexed action space (`@1..@N`), semantic fingerprints, pre-action staleness verification.
  - `BrowserDriver`: Primitive action execution, financial safety gate, and evidence-based post-action verification (`dom_mutated`, `url_changed`, physical `input_value`).
  - Offline test fixture and test suite `tests/test_r2_browser.py` (15/15 passed).
- **Phase R1: Deep Evidence-Grounded Research Engine**:
  - `DeepResearchEngine`: Deterministic query decomposition, bounded discovery and crawl loop (depth <= 1), 3-gram Jaccard deduplication, sequential relevance scoring, mathematical saturation yield stopping, and cryptographic citation verification.
  - Offline test suite `tests/test_r1_research.py` (18/18 passed).
- **Foundation Gate: System 1 Provider Broker**:
  - User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), Hierarchical Two-Level Locking, strict English-only invariant, and debounced Windows RAM protection.
  - Offline test suite `tests/test_foundation_broker.py` (27/27 passed).
- **Pre-Execution Control Plane (L0–L9)**:
  - System 1 Decision Fabric (L7.5), Hierarchical Capability Routing (L6A/L6B), Skills Layer (L7), Typed Argument Resolution Engine (L8), and Deterministic Policy Engine (L9).
- **Strongly Typed Capability Contracts**: Clean interface boundaries throughout (`DevExecutionReceipt`, `CodeVerificationReceipt`, `N8nWorkflowDetail`, `N8nExecutionReceipt`, `AppLaunchResult`, `BrowserActionResult`, `ResearchDossier`, `ToolResult`, `PolicyDecision`, `ArgumentResolutionEnvelope`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Milestone Goal: **Real Capability Engines: Foundation Gate (COMPLETE) → Phase R1 (COMPLETE) → Phase R2 (COMPLETE) → Phase R3 (COMPLETE) → Phase R4 (COMPLETE) → Phase R5 (COMPLETE) — MILESTONE COMPLETED**.
- Full Test Suite: **364/364 tests passing (+ 47 subtests = 411 total, 100% pass rate)** in 233.91s across 19 test modules:
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
  - `tests/test_l9_policy.py` (26 tests)
  - `tests/test_foundation_broker.py` (27 tests)
  - `tests/test_r1_research.py` (18 tests)
  - `tests/test_r2_browser.py` (15 tests)
  - `tests/test_r3_desktop.py` (21 tests)
  - `tests/test_r4_n8n.py` (25 tests)
  - `tests/test_r5_developer.py` (25 tests)
- Governance: All canonical documents synchronized with verified implementation truth.
- Non-Switching Boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.

---

## Operational Boundary & Next Phase
- **Current Milestone**: Real Capability Engines (R1–R5) are **100% COMPLETE**.
- **Hard Stop Boundary**: **STRICTLY ENFORCED**. 0 diffs in `omni_agent.py` and `omni_engine/planner.py`. Zero advance implementation of L10–L14.
- **Next Milestone**: **Phase IV — Persistent Quest Engine & Structured DAG Planning (Checkpoints L10–L16)**.
  - L10: Persisted SQLite Quest Engine (`Quest`, `QuestStep`, `OperationExecution`).
  - L11: Operation Ledger & Logical Idempotency (`questId:stepId:capabilityId`).
  - L12: Structured DAG Planner.
  - L13: Plan Validator.
  - L14: Deterministic DAG Executor.

