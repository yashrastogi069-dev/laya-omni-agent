# ACTIVE_PLAN.md — Checkpoint L5: System One Decision Fabric (ACTIVE)

## 1. Summary of Completed Checkpoint L4 (Provider Foundations)
- **Status**: **COMPLETED & VERIFIED**
- **Artifacts Created / Hardened**:
  - `omni_engine/providers/base.py`:
    - Abstract `SystemOneProvider(ABC)` declaring `classify()`, `score()`, `predict_signals()`, `health_check()`.
    - Abstract `GenerativeProvider(ABC)` declaring `generate_text()`, `generate_structured()`, `health_check()`.
    - Normalized contract envelopes `ProviderError` (strongly typed `ErrorCode`), `ProviderHealth` (latency and status code tracking), and `GenerationResult` (token counts and finish reason).
  - `omni_engine/providers/system1.py`:
    - `LayaProvider` wrapping local ModernBERT-large (`laya.Router()`) with global thread-safe `_ROUTER_LOCK` singleton to eliminate duplicate PyTorch allocations and protect host RAM.
    - Batched multi-question evaluation in a single forward pass (`predict_signals()`) satisfying the `<35ms` latency budget.
    - Numerical sanitization (`sanitize_float` clamping to `[0.0, 1.0]`, NaN/Inf replacement).
    - Defensive extraction helper `_extract_decision_data` handling both dicts and `RouteDecision` objects, `None` values, and uncalibrated distributions without `TypeError`.
    - Optional `JevProvider` implementing TypeSafe cloud API with non-crashing graceful degradation (`ErrorCode.UNCONFIGURED`) when unconfigured.
  - `omni_engine/providers/generative.py`:
    - `OpenRouterProvider` with configurable model, base URL, and explicit timeout budget (default 60s).
    - Deterministic markdown fence extraction (`extract_json_from_text`) stripping code fences and isolating JSON payloads.
    - Structured Pydantic object extraction and validation via `generate_structured()`.
    - Validation of non-empty completion choices and graceful degradation when unconfigured (`ErrorCode.UNCONFIGURED`).
    - Zero local RAM overhead (remote HTTP client only).
  - `omni_engine/memory.py`:
    - Repaired Windows console encoding flaw (`UnicodeEncodeError` under `cp1252`) by replacing raw Unicode emojis (`⚠️`) with ASCII `[WARNING]`.
  - `tests/test_l4_providers.py`:
    - 19 comprehensive unit tests covering all provider contracts, batched multi-signal forward passes, unconfigured graceful failure, empty choices guards, timeout parameters, defensive polymorphic parsing, and shared router RAM preservation.
- **Test Suite Results**:
  - `tests/test_l4_providers.py`: **19/19 passed in 92.49s (100% pass rate)**.
  - Full repository test suite (`python -m unittest discover tests -v`): **99 passed in 123.56s (100% pass rate)**.
- **Adversarial Diff Review**: **PASS (with all identified repairs incorporated)**.

---

## 2. Checkpoint L5: System One Decision Fabric (ACTIVE)

### 2.1 Objectives
Build the complete high-frequency typed `DecisionFrame` generation engine on top of `LayaProvider`, evaluating the full multi-dimensional decision state in a single low-latency forward pass:
1. `SystemOneEngine` / `DecisionFabric`:
   - Inputs: User request (`prompt`), conversation state, session context.
   - Evaluates all canonical `DecisionSignalType` members:
     - `INTENT`: Query / task intention category.
     - `TASK_CLASS`: Single-turn reflex, multi-step quest, deep research, code refactor, system admin.
     - `DOMAIN`: Target capability domain (`filesystem`, `code`, `system`, `web`, `data`).
     - `URGENCY`: Critical / immediate vs routine.
     - `IMPORTANCE`: High consequence vs low consequence.
     - `RISK`: Safe read-only vs mutating vs high-risk system action.
     - `REVERSIBILITY`: Reversible vs irreversible (Invariant 7).
     - `AMBIGUITY`: Unambiguous vs ambiguous.
     - `REQUIRES_CLARIFICATION`: True/False.
     - `REQUIRES_ACTION`: True/False.
     - `REQUIRES_TOOLS`: True/False.
     - `REQUIRES_PLAN`: Needs multi-step planning (DAG) vs direct execution.
     - `REQUIRES_GENERATIVE_REASONING`: Needs generative LLM vs deterministic/reflexive execution.
     - `MODEL_TIER`: System 1 reflex, light generative, or deep reasoning.
   - Outputs: Fully validated `DecisionFrame` adhering to `omni_engine/contracts/decision.py`.
2. Latency Budget & Evaluation Corpus:
   - Target forward-pass latency: `<35ms` for warm batched decision pass.
   - Construct a standardized evaluation corpus of test prompts representing diverse interaction categories.
   - Benchmark signal accuracy and report baseline metrics.
3. Fallback & Uncertainty Handling:
   - When decision confidence is low or ambiguity is high, escalate signals safely (`requires_clarification=True` or `requires_generative_reasoning=True`).
4. Non-Switching Principle:
   - Main agent dispatch (`omni_agent.py`) remains on the legacy path; L5 is tested via dedicated unit and integration tests.

---

## 3. Targeted Test Suite (`tests/test_l5_decision_fabric.py`)
1. `TestDecisionFrameGeneration`: Validates complete `DecisionFrame` generated with all required signals.
2. `TestMultiDimensionalBatchedPass`: Asserts all criteria are evaluated simultaneously in one forward pass.
3. `TestSignalThresholdsAndEscalation`: Validates ambiguity threshold triggers `requires_clarification`.
4. `TestHighRiskDetection`: Confirms destructive actions trigger high risk and low reversibility.
5. `TestEvaluationCorpusBenchmark`: Runs evaluation dataset and reports latency and signal distributions.

---

## 4. Acceptance Criteria
- [ ] `DecisionFabric` generates valid `DecisionFrame` with all canonical signals populated.
- [ ] Inference runs via single-pass batched `LayaProvider.predict_signals()` under the `<35ms` warm budget.
- [ ] Numerical confidences bounded in `[0.0, 1.0]`, provenance populated with provider and model ID.
- [ ] Ambiguity and risk safely escalate decisions.
- [ ] Evaluation corpus established and tested with benchmark evidence.
- [ ] Full regression test suite passes (>= 99 tests + new L5 tests).
- [ ] Adversarial diff review passes.
