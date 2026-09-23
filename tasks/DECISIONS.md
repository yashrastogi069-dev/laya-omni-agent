# DECISIONS.md — Architecture Decision Records (ADRs)

## ADR-001: Dual-System Architecture (Local System 1 + Cloud System 2)
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Running large generative LLMs (7B+ parameters) locally exhausts RAM and freezes older host machines (8GB RAM, 4 CPU cores). Conversely, relying purely on cloud LLMs for every micro-decision introduces prohibitive latency (500ms - 2000ms) and monetary cost.
- **Options**:
  1. Heavy local generative model (Ollama / llama.cpp 7B/8B).
  2. Pure cloud generative model for all actions.
  3. Dual-system: Local lightweight encoder/classifier (Laya ModernBERT-large, ~400MB RAM, <35ms) for high-frequency System 1 decisions + Cloud APIs (OpenRouter / Gemini) for System 2 deep reasoning.
- **Decision**: Adopt Option 3.
- **Reasons**: Guarantees sub-35ms routing on local CPU without freezing system memory; invokes cloud generative power only when genuinely required for novel planning or synthesis.
- **Trade-offs**: Requires disciplined separation between decision tasks and generative tasks.
- **Reconsideration Trigger**: If local machine hardware is upgraded to dedicated GPU with 16GB+ VRAM capable of running local quantized frontier models at <30ms latency.

---

## ADR-002: Deterministic DAG Planning vs Unconstrained ReAct Tool Loops
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Unconstrained ReAct loops ("think-act-observe" in a free-form while loop) frequently wander, repeat destructive operations, hallucinate tool completion, and suffer from prompt-injection vulnerabilities.
- **Options**:
  1. Unconstrained ReAct loop.
  2. Hardcoded finite state machine per task.
  3. Validated Directed Acyclic Graph (DAG) Plan + Deterministic Executor.
- **Decision**: Adopt Option 3.
- **Reasons**: Planning is separated from execution. The planner generates a structured DAG; a deterministic runtime validates the graph, executes ready nodes, manages dependencies, enforces policies, and verifies real-world side effects.
- **Trade-offs**: Slightly higher upfront structure required for simple tasks (mitigated by fast-path single-step execution).
- **Reconsideration Trigger**: If tasks exhibit dynamic runtime branching that cannot be expressed as conditional nodes or controlled replanning.

---

## ADR-003: SQLite as Canonical Local Storage for Quests and State
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Agent state and memory must survive process crashes, client disconnects, and provider timeouts without data loss or corruption.
- **Options**:
  1. Plain JSON files on disk.
  2. SQLite embedded database.
  3. External database (PostgreSQL / Redis).
- **Decision**: Adopt Option 2 (SQLite) for Quests, step states, operation ledger, and automation rules.
- **Reasons**: Zero setup, zero background daemon overhead, ACID transactions, atomic updates, and proven reliability for local-first software.
- **Trade-offs**: Requires defining relational schemas and migration helpers.
- **Reconsideration Trigger**: If multi-node distributed concurrency is explicitly required.

---

## ADR-004: Evidence-First Outcome Verification
- **Date**: 2026-09-23
- **Status**: ACCEPTED
- **Problem**: Language models frequently report tasks as complete when actions failed or were never actually executed.
- **Options**:
  1. Trust LLM text generation ("I have created the file").
  2. Deterministic outcome checks first (file existence, process checks, DOM state, exit codes) followed by cheap semantic checks.
- **Decision**: Adopt Option 2.
- **Reasons**: Prevents hallucinated task success. No operation is marked completed without observable physical receipts.
- **Trade-offs**: Each capability must define an associated verifier strategy.
- **Reconsideration Trigger**: None. This is a permanent core safety invariant.
