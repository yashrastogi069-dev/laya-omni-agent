# ACTIVE_PLAN.md — Checkpoint L4: Provider Foundations (ACTIVE)

## 1. Summary of Completed Checkpoint L3 (Canonical Capability Substrate)
- **Status**: **COMPLETED & VERIFIED**
- **Artifacts Created**:
  - `omni_engine/capabilities/registry.py`: Thread-safe `CapabilityRegistry` with fine-grained lock scoping, exception normalization, and automatic `ExecutionReceipt` telemetry.
  - `omni_engine/capabilities/adapters.py`: Argument normalization adapters and prefix-anchored error interceptors for all 23 source tools (zero false-positives on content-bearing tools).
  - `omni_engine/capabilities/definitions.py`: Canonical `CapabilitySpec` definitions for all 23 source tools and `build_canonical_registry()` builder.
  - `omni_engine/capabilities/__init__.py`: Clean public interface for capability substrate.
  - `tests/test_l3_capabilities.py`: 25 unit tests (and 23 subtests) covering registration, 1:1 parity, read-only result boundaries, process-control exception propagation, all-23 capability argument execution without `TypeError`, and non-switching boundary preservation.
- **Test Suite Results**: **80/80 passed** (53 feature acceptance + 2 known defect reproduction + 25 L3 capability tests).

---

## 2. Checkpoint L4: Provider Foundations (ACTIVE)

### 2.1 Objectives
Build vendor-independent provider abstractions for both System 1 (fast reflexive decisions) and Generative (System 2 synthesis/planning) models, decoupling LAYA from specific vendors:
1. `SystemOneProvider` abstract base contract:
   - Methods: `classify()`, `score()`, `predict_signals()`, `health_check()`.
   - Implement `LayaProvider` wrapping local ModernBERT-large (`laya.Router()`).
   - Implement optional `JevProvider` wrapping TypeSafe cloud API (fails gracefully when unconfigured without crashing).
   - Telemetry: Record `provider_id`, `model_id`, inference `latency_ms`, calibrated probabilities where available, failure states. Never fabricate high confidence on model failure.
2. `GenerativeProvider` abstract base contract:
   - Methods: `generate_text()`, `generate_structured()`, `health_check()`.
   - Minimal interface needed by future Argument Resolver (L8) and Planner (L12).
   - Implement `OpenRouterProvider` wrapping current OpenRouter LLaMA 3.3 70B client (`omni_engine/system2.py`).
   - Decouple from vendor-specific libraries.
3. Resource Bounds & Latency Profiling:
   - Low host RAM protection (no preloading multiple heavyweight models).
   - Cold vs warm latency measurement.
   - Zero secrets committed to git.
4. Non-Switching Boundary:
   - Existing legacy `System1Router` and `System2Engine` remain intact for legacy agent callers.

---

## 3. Targeted Test Suite (`tests/test_l4_providers.py`)
1. `TestSystemOneProvider`: Abstract contract adherence, `LayaProvider` loading, latency measurement, output provenance.
2. `TestOptionalJevProvider`: Graceful failure with `ErrorCode.UNCONFIGURED` when API key missing.
3. `TestGenerativeProvider`: Abstract contract adherence, structured generation parsing, error normalization.
4. `TestProviderHealthAndTelemetry`: Health check APIs, cold vs warm latency tracking.

---

## 4. Acceptance Criteria
- [ ] Clean abstract provider interfaces (`SystemOneProvider`, `GenerativeProvider`) in `omni_engine/providers/`.
- [ ] `LayaProvider` functional with local ModernBERT.
- [ ] `OpenRouterProvider` functional behind `GenerativeProvider`.
- [ ] Optional `JevProvider` fails gracefully when unconfigured.
- [ ] No secrets committed.
- [ ] Latency telemetry preserved in decision metadata.
- [ ] Full regression test suite passes (>= 80 tests).
- [ ] Adversarial diff review passes.
