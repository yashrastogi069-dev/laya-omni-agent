# HANDOFF.md — Operational Continuation Guide (Checkpoint L5 Complete)

## What We Are Building
A **complete standalone autonomous operating agent** powered by:
- **System 1 Decision Fabric**: Sub-35ms bounded structured decisions via local ModernBERT-large (`laya.Router()`).
- **Deterministic Control**: The runtime strictly owns state transitions, permissions, operation identity, idempotency, and DAG execution.
- **Generative Models**: Invoked strictly for novel planning, structured argument extraction, code generation, and complex synthesis.
- **Strongly Typed Capability Contracts**: Clean interface boundaries (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `ExecutionReceipt`, `VerificationResult`, `DecisionFrame`, `AgentRequest`, `AgentResponse`, `AgentEvent`, `TraceContext`) without external runtime dependencies.

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Checkpoint: **L5 COMPLETED**; **L6A ACTIVE (Hierarchical Routing Foundation)**.
- Test Suite: **111/111 tests passing** (+ 23 subtests passed) across `test_l0_baselines.py`, `test_l1_repairs.py`, `test_l2_contracts.py`, `test_l2_1_reconciliation.py`, `test_l3_capabilities.py`, `test_l4_providers.py`, and `test_l5_decision_fabric.py`.
- Governance: All canonical documents synchronized with verified implementation truth.

---

## Last Changes (Checkpoint L5 Executed)
1. **Decision Fabric Engine (`omni_engine/decision/fabric.py`)**:
   - `DecisionFabric` producing fully typed, validated `DecisionFrame` packets.
   - Evaluates 15 canonical decision questions simultaneously in a single batched tensor pass via `LayaProvider.predict_signals()`.
   - Deterministic fast-path (<1ms) for empty, whitespace, and punctuation-only prompts returning immediate clarification frame without invoking neural model.
   - Sliding-window head-tail truncation for prompts exceeding 3,000 characters.
   - High-risk safety floor pre-emption (`DEFAULT_HIGH_RISK_PATTERNS`) clamping risk to `high_risk_system`, reversibility to `irreversible` (Invariant 7), and forcing `escalation_required=True`.
   - Ambiguity and low-confidence triggers setting `needs_clarification=True` and `needs_generative_reasoning=True`.
   - Conversational disambiguation: informational/chat queries without tools force `requires_action=False`, `needs_plan=False`, `needs_tools=False`, and `model_tier="system_1"`.
   - Domain contract trap mitigation: maps domain probabilities to `candidate_domains: List[str]` without passing illegal extra `domain` field to `DecisionFrame` (`extra="forbid"`).
   - Graceful fallback: provider errors produce an escalated fallback `DecisionFrame` with `escalation_required=True`, `needs_generative_reasoning=True`, `model_tier="pro"`.
2. **Benchmark Evaluation Corpus & Runner (`omni_engine/decision/corpus.py`)**:
   - Standardized 10-prompt benchmark dataset (`BENCHMARK_CORPUS`) covering conversational, file read, file write, process kill, powershell, git, sqlite, math, ambiguous, multi-step.
   - Evaluation runner `evaluate_decision_corpus()` measuring latency (min, max, avg, p95) and reporting signal distributions.
3. **Console Encoding Hardening (`omni_engine/system1.py`)**:
   - Replaced Unicode emojis (`🤖`, `⚡`) with ASCII `[System 1]` to prevent Windows `cp1252` `UnicodeEncodeError`.
4. **Router Preload Fix (`omni_engine/providers/system1.py`)**:
   - Passed `["english"]` explicitly to `_SHARED_ROUTER.preload()` to prevent multi-gigabyte downloads of unused multilingual models.
5. **Comprehensive Unit & Integration Test Suite (`tests/test_l5_decision_fabric.py`)**:
   - 12 comprehensive unit and integration tests covering contract completeness, empty prompt fast-paths, truncation, safety overrides, ambiguity triggers, conversational disambiguation, fallback, candidate domain ranking, benchmark evaluation, and live ModernBERT forward pass.
6. **Regression Verification**:
   - Full repository test suite passed: **111 passed in 160.07s (100% pass rate)**.
   - Adversarial diff review passed with all invariants confirmed.

---

## Files to Read Next
1. `tasks/ACTIVE_PLAN.md` — Target plan for Checkpoint L6A (Hierarchical Routing Foundation).
2. `tasks/MASTER_PLAN.md` — Full strategic roadmap (L0–L25).
3. `omni_engine/decision/fabric.py` — Completed System 1 Decision Fabric.
4. `omni_engine/capabilities/registry.py` — Canonical 23-tool CapabilityRegistry.

---

## Tests to Run
```powershell
python -m unittest discover tests -v
```

---

## Rules to Enforce During L6A
1. **Dynamic Candidate Pruning**: Never use flat `[:12]` catalog slicing; rank candidates by domain and relevance.
2. **Fail-Open Fallback**: Broaden candidate set across adjacent domains when uncertainty is high.
3. **Non-Switching Principle**: Main agent dispatch (`omni_agent.py`) remains on the legacy path.
4. **End-to-End Log**: Always update `END_TO_END_EXECUTION_LOG.md` with complete evidence.
