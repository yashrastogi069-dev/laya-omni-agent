# DECISIONS.md — Architecture Decision Records (ADRs)

## ADR-001: Local-First Cognitive Dual-System (System 1 Local ModernBERT + System 2 Cloud/Antigravity)
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Running large generative LLMs (7B+ parameters) locally exhausts RAM and freezes older host machines (8GB RAM, 4 CPU cores). Conversely, relying purely on cloud LLMs for every micro-decision introduces prohibitive latency (500ms - 2000ms) and monetary cost.
- **Decision**: Adopt local lightweight ModernBERT-large (Laya, ~400MB RAM, <35ms) for high-frequency System 1 decisions, backed by cloud APIs for heavy generative reasoning.
- **Reasons**: Guarantees sub-35ms routing on local CPU without freezing system memory.

---

## ADR-002: Deterministic DAG Planning vs Unconstrained ReAct Tool Loops
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Unconstrained ReAct loops ("think-act-observe" in a free-form while loop) frequently wander, repeat destructive operations, hallucinate tool completion, and suffer from prompt-injection vulnerabilities.
- **Decision**: Adopt Validated Directed Acyclic Graph (DAG) Plan + Deterministic Executor for multi-step work.
- **Reasons**: Planning is separated from execution. The planner generates a structured DAG; a deterministic runtime validates the graph, executes ready nodes, manages dependencies, enforces policies, and verifies real-world side effects.

---

## ADR-003: SQLite as Canonical Local Storage for Quests and State
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Agent state and memory must survive process crashes, client disconnects, and provider timeouts without data loss or corruption.
- **Decision**: Adopt SQLite embedded database for Quests, step states, operation ledger, and automation rules.
- **Reasons**: Zero setup, zero background daemon overhead, ACID transactions, atomic updates, and proven reliability for local-first software.

---

## ADR-004: Evidence-First Outcome Verification
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Language models frequently report tasks as complete when actions failed or were never actually executed.
- **Decision**: Actions must be verified with physical receipts (file diffs, process tables, DOM state, exit codes) before being reported as completed.

---

## ADR-005: Standalone Autonomous Agent with Clean Interface Boundaries
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: LAYA must function as a complete, fully autonomous standalone agent without depending on external runtimes. At the same time, future multi-agent coordination must remain possible without rewriting internal engines.
- **Decision**: Build LAYA as a complete standalone autonomous agent with its own Quest runtime, DAG executor, action policy, capability contracts, and memory. Expose all external boundaries via clean, standardized interface types: `AgentRequest`, `AgentResponse`, `DecisionFrame`, `Quest`, `CapabilitySpec`, `ToolResult`, `ExecutionReceipt`, `VerificationResult`, and `AgentEvent`.
- **Reasons**: Decouples LAYA completely from external runtimes while preserving modularity.

---

## ADR-006: Hierarchical Capability Routing Over Flat Tool Catalog Dumps
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: The legacy `[:12]` slice in `system1.py` excluded 11 tools. However, simply removing the slice and dumping all 23+ tool descriptions into a flat choice prompt exceeds context constraints, degrades classification accuracy, and fails to scale to 50–100 tools.
- **Decision**: Reject the flat 23-tool dump. Implement hierarchical capability routing in Checkpoint L6: `Request → Domain → Skill → Small Candidate Set → Capability`, with fail-open fallback.
