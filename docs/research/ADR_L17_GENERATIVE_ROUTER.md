# ADR-022: Role-Aware Generative Provider Router (L17)

- **Date**: 2026-10-05
- **Status**: ACCEPTED
- **Authors**: LAYA Core Autonomous Architecture Team
- **Checkpoint**: L17 (Role-Aware Generative Provider Router)

---

## 1. Context & Problem Statement

In the LAYA Omni Agent architecture, System 1 (`laya.Router()`) handles high-frequency structured classifications (<35ms on GPU, sub-second on CPU) across 15 canonical decision signals. Invariant 3 dictates that generative models are reserved strictly for tasks that deterministic code, skills, or System 1 cannot solve:
1. Structured argument synthesis (`ARGUMENT_WRITER`) when deterministic resolution fails.
2. Novel multi-step DAG planning (`PLANNER`) when no skill template matches.
3. Recovery sub-DAG synthesis (`REPLANNER`) upon recoverable step failures.
4. Deep research synthesis and executive dossier generation (`FINALIZER`).
5. Supervised code generation and bug remediation (`CODING`).

Historically:
- The codebase used a single monolithic `OpenRouterProvider` with a single global model string (e.g., `meta-llama/llama-3.3-70b-instruct`).
- Different agent roles have vastly differing requirements for latency, reasoning depth, token budgets, and schema conformity:
  - `ARGUMENT_WRITER` requires low latency and strict schema compliance, where a fast model (e.g. GPT-4o-mini or Claude 3.5 Haiku) is optimal.
  - `PLANNER` and `CODING` require deep topological reasoning and code understanding, where frontier models (e.g. Claude 3.5 Sonnet or DeepSeek V3) excel.
  - `FINALIZER` requires prose fluency and long-form synthesis.
- Furthermore, a single provider failure (e.g. OpenRouter rate limit or API key omission) would cause an unrecoverable crash, with zero model cascade or user sovereignty enforcement.

We require a **strongly typed, role-aware generative provider router** that:
- Defines distinct agent roles with calibrated default models, temperatures, token limits, and timeout budgets.
- Organizes models into performance tiers (`FAST`, `BALANCED`, `CAPABLE`).
- Enforces user sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), strictly prohibiting unauthorized fallbacks when locked.
- Implements deterministic cascading fallbacks across alternative models/providers upon network, timeout, or rate-limit failures.
- Captures granular routing telemetry on every generation.
- Decouples cleanly via `GenerativeProvider` ABC, providing a drop-in replacement across `omni_engine`.
- Provides an isolated `MockGenerativeProvider` for 100% offline, deterministic testing.

---

## 2. Decision & Architectural Invariants

### 2.1 Agent Role Taxonomy (`AgentRole`)
The system recognizes 5 explicit generative roles:

| Role | Purpose | Typical Tier | Default Temperature | Default Max Tokens | Example Models |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ARGUMENT_WRITER` | Fulfill capability input schemas | `FAST` | 0.1 | 1,000 | `gpt-4o-mini`, `claude-3-5-haiku`, `llama-3.3-70b` |
| `PLANNER` | Decompose novel multi-step goals into DAGs | `CAPABLE` | 0.2 | 3,000 | `claude-3-5-sonnet`, `gpt-4o`, `deepseek-r1` |
| `REPLANNER` | Blast radius diagnosis & replacement graft | `BALANCED` | 0.2 | 2,000 | `claude-3-5-sonnet`, `gpt-4o`, `llama-3.3-70b` |
| `FINALIZER` | Research dossiers & final quest summaries | `BALANCED` | 0.4 | 4,000 | `claude-3-5-sonnet`, `gpt-4o`, `llama-3.3-70b` |
| `CODING` | Code generation & syntax-guaranteed repair | `CAPABLE` | 0.1 | 3,000 | `claude-3-5-sonnet`, `deepseek-v3`, `qwen-2.5-coder-32b` |

### 2.2 Model Tiers (`ModelTier`)
1. `FAST`: Low latency, low token cost (<1s API latency, schema adherence priority).
2. `BALANCED`: General reasoning workhorse (balanced latency and synthesis quality).
3. `CAPABLE`: Frontier intelligence, complex logic, multi-hop reasoning, and code synthesis.

### 2.3 User Sovereignty Hierarchy
Model sovereignty follows the established LAYA pattern:
1. `USER_LOCKED`:
   - The user or operator explicitly pins a model or provider for a role.
   - **No fallback is permitted under any circumstance**. If the locked provider fails (unconfigured, rate-limited, timeout, network error), a `ProviderError` is raised immediately.
2. `USER_PREFERRED`:
   - The operator specifies a preferred model.
   - If the preferred model fails with a recoverable error (`RATE_LIMITED`, `TIMEOUT`, `NETWORK_ERROR`, `UNCONFIGURED`), the router may cascade to configured fallbacks.
   - The router records `was_fallback=True` and an explicit `FallbackReason`.
3. `AUTO`:
   - The router selects the optimal model from the role's default tier configuration and cascades through fallbacks seamlessly.

### 2.4 Cascading Fallback Lifecycle
When `generate_text_for_role` or `generate_structured_for_role` is invoked:
1. Look up `RoleRouteConfig` for the requested `AgentRole`.
2. Determine primary candidate model and provider (accounting for user pins).
3. Build the ordered candidate sequence: `[Primary] + FallbackCandidates`.
4. Iterate through candidates:
   - If candidate is healthy and configured: attempt generation.
   - If generation succeeds: return `GenerationResult` (or validated Pydantic model) with `RouterTelemetry`.
   - If generation fails:
     - If sovereignty is `USER_LOCKED`: abort immediately, raise exception.
     - If error is non-retryable (e.g. fatal validation error on client request): abort.
     - If error is transient/recoverable (`RATE_LIMITED`, `TIMEOUT`, `NETWORK_ERROR`, `SERVICE_UNAVAILABLE`, `UNCONFIGURED`): record attempt, log fallback diagnostic, advance to next candidate.
5. If all candidates are exhausted: raise `ProviderError(ErrorCode.PROCESS_FAILED, "All candidates exhausted")`.

### 2.5 Contract Drop-In Invariant
`GenerativeRouter` inherits directly from `GenerativeProvider(ABC)`:
- Existing callers calling `.generate_text(prompt)` or `.generate_structured(prompt, model)` continue to function transparently, defaulting to `AgentRole.PLANNER`.
- Callers requiring role awareness use `.generate_text_for_role(role, ...)` or `.generate_structured_for_role(role, ...)`.

---

## 3. Technology Evaluation (ADOPT / ADAPT / REJECT)

1. **LiteLLM / Instructor**:
   - *Audit*: Heavy external dependencies (hundreds of transitive packages, monkeypatching, non-deterministic logging).
   - *Decision*: **REJECT**. LAYA uses a lightweight, self-contained router built on pure standard library and Pydantic v2.
2. **OpenAI SDK / OpenRouter API**:
   - *Audit*: Standardized client already integrated in `OpenRouterProvider`.
   - *Decision*: **ADOPT & ENHANCE**. Use as underlying provider transport for remote cloud calls.
3. **MockGenerativeProvider**:
   - *Audit*: Needed for fast offline testability without external network calls or secrets.
   - *Decision*: **ADOPT**. Programmable in-memory provider supporting scripted text/structured returns and simulated error triggers.

---

## 4. Consequences & Verification

- **Positive**:
  - Eliminates single-point-of-failure on remote model outages.
  - Tailors intelligence density and cost to specific agent roles.
  - Guarantees zero local RAM bloat (pure network routing).
  - Respects user model sovereignty deterministically.
- **Negative / Trade-offs**:
  - Routing cascades introduce minor latency during provider failovers.
- **Verification Strategy**:
  - 100% offline unit and integration tests in `tests/test_l17_generative_router.py`.
  - Full repository regression suite (562+ tests).
  - Zero diffs on legacy non-switching boundary (`omni_agent.py` and `omni_engine/planner.py`).
