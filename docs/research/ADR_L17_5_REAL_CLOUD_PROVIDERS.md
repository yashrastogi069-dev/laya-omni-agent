# ADR-023: Real Cloud Provider Integration (L17.5)

- **Date**: 2026-10-05
- **Status**: ACCEPTED
- **Authors**: LAYA Core Autonomous Architecture Team
- **Checkpoint**: L17.5 (Real Cloud Provider Integration)

---

## 1. Context & Problem Statement

In Checkpoint L17, we established the `GenerativeRouter`, enabling role-aware model selection across 5 functional agent roles (`ARGUMENT_WRITER`, `PLANNER`, `REPLANNER`, `FINALIZER`, `CODING`), performance tier calibration (`FAST`, `BALANCED`, `CAPABLE`), deterministic user sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), and cascading fallbacks.

Prior to L17.5, the only real external provider was `OpenRouterProvider`, which routes all generative calls through a third-party proxy aggregator (OpenRouter). While convenient, relying exclusively on a single proxy aggregator introduces several structural vulnerabilities:
1. **Single Point of Failure (SPOF)**: Outages or billing issues with the proxy service halt all autonomous execution across all models.
2. **Proxy Latency Overhead**: Proxy routing introduces additional round-trip network hops and rate limits.
3. **Vendor-Specific Capabilities**: Direct endpoints offer native features:
   - Anthropic: Native Claude Messages API, prompt caching headers, and strict system message segregation.
   - OpenAI: Native strict JSON schema enforcement (`response_format={"type": "json_schema"}`), function calling, and seed determinism.
   - DeepSeek: Extremely cost-effective frontier coding intelligence (`deepseek-chat` / `deepseek-reasoner`) via direct OpenAI-compatible endpoint (`https://api.deepseek.com`).

We require **direct, production-grade cloud provider adapters** for Anthropic, OpenAI, and DeepSeek that:
- Inherit from `GenerativeProvider(ABC)`, returning standardized `GenerationResult` and validated Pydantic models.
- Support invocation-local `model` and `timeout` overrides (preserving thread safety).
- Enforce strict secret hygiene: credentials resolved safely from environment variables; zero token leakage in logs, exceptions, or telemetry.
- Degrade gracefully when unconfigured (`is_configured=False`, raising `ProviderError(ErrorCode.UNCONFIGURED)`).
- Provide decoupled transport interfaces for 100% offline, deterministic testing.
- Integrate seamlessly into `GenerativeRouter` via provider URI schemes (`openai:<model>`, `anthropic:<model>`, `deepseek:<model>`).

---

## 2. Decision & Architectural Invariants

### 2.1 Provider Architecture & Transport Strategy

| Provider | Default Model | Transport Protocol | Base Endpoint | Supported Credentials |
| :--- | :--- | :--- | :--- | :--- |
| `DirectOpenAIProvider` | `gpt-4o` | `openai.OpenAI` SDK | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| `AnthropicProvider` | `claude-3-5-sonnet-20241022` | HTTP Messages API (`urllib.request` / optional `anthropic`) | `https://api.anthropic.com/v1/messages` | `ANTHROPIC_API_KEY` |
| `DeepSeekProvider` | `deepseek-chat` | `openai.OpenAI` SDK | `https://api.deepseek.com` | `DEEPSEEK_API_KEY` |

### 2.2 Dependency Minimization Invariant
To prevent repository bloat and ensure reliability across heterogeneous Windows/Linux environments:
1. `openai` is already installed and verified in the environment. Both `DirectOpenAIProvider` and `DeepSeekProvider` use `openai.OpenAI` directly.
2. The `anthropic` SDK is not installed in the host environment. `AnthropicProvider` is implemented using Python's built-in `urllib.request` with optional dynamic import if `anthropic` is present. This eliminates heavyweight external dependencies while providing 100% compliant Anthropic Messages API support.

### 2.3 Secret Hygiene & Telemetry Defense (docs/SECURITY_AND_POLICY.md)
1. **Zero Secret Persistence**: API keys are passed to underlying client instances or request headers; they are never stored in `RouterTelemetry`, `GenerationResult.metadata`, or exception messages.
2. **Error Redaction**: All raw exception messages from network clients are filtered through regex redaction to strip any embedded authorization headers or API key patterns (`sk-`, `ant-`, `Bearer `).

### 2.4 Test Isolation & Offline Determinism
Every cloud provider adapter accepts an optional transport/client factory or mock HTTP handler:
- `AnthropicProvider(transport_fn=...)`
- `DirectOpenAIProvider(client=...)`
- `DeepSeekProvider(client=...)`
This guarantees that all unit and integration tests run 100% offline, with 0 external network requests, in <1 second.

---

## 3. Technology Evaluation (ADOPT / ADAPT / REJECT)

1. **Direct OpenAI SDK (`openai.OpenAI`)**:
   - *Audit*: Official SDK already installed; thread-safe client with native timeout and error handling.
   - *Decision*: **ADOPT**. Use for `DirectOpenAIProvider` and `DeepSeekProvider`.
2. **Direct Anthropic REST Messages API**:
   - *Audit*: Anthropic Messages API v1 is stable and well-specified (`/v1/messages`, `x-api-key`, `anthropic-version: 2023-06-01`).
   - *Decision*: **ADOPT (Lightweight REST Adapter)**. Implement via standard library `urllib.request` with JSON serialization, avoiding extra dependencies while delivering full Claude capability.
3. **DeepSeek Direct API**:
   - *Audit*: DeepSeek exposes an OpenAI-compatible API at `https://api.deepseek.com`.
   - *Decision*: **ADOPT**. Subclass or wrap `DirectOpenAIProvider` with default base URL `https://api.deepseek.com` and `DEEPSEEK_API_KEY`.

---

## 4. Consequences & Verification

- **Positive**:
  - Eliminates OpenRouter as a single point of failure.
  - Enables direct access to Claude 3.5 Sonnet, GPT-4o, and DeepSeek V3 with lowest possible latency.
  - Enables sovereign routing directly to first-party cloud endpoints.
- **Negative / Trade-offs**:
  - Requires operators to manage separate API keys if choosing direct routing over OpenRouter.
- **Verification Strategy**:
  - 100% offline unit tests in `tests/test_l17_5_cloud_providers.py`.
  - Verification of URI routing in `GenerativeRouter` (`openai:gpt-4o`, `anthropic:claude-3.5-sonnet`, `deepseek:deepseek-chat`).
  - Full repository regression suite (585+ tests).
  - Legacy non-switching boundary check (`omni_agent.py` and `omni_engine/planner.py` maintain 0 diffs).
