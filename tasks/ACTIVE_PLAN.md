# ACTIVE_PLAN.md — Checkpoint R1: Deep Research Engine (ACTIVE) & Foundation Gate (COMPLETED)

## 1. Summary of Completed Foundation Gate: System One Broker, Concurrency Correction & Calibration Truth
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **27/27 unit tests passed in 0.047s; 259/259 full repository tests (+ 47 subtests = 306 total) passed (100% pass rate)**.
- **Key Deliverables**:
  1. `omni_engine/contracts/broker.py`: Strongly typed `ProviderSelectionMode` (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), `BrokerRoutingOutcome`, `FallbackReason`, `TaskProviderOverride`, `ProviderPolicyConfig`, `BrokerDecision`, and `CalibrationMetrics`.
  2. `omni_engine/providers/system1.py`:
     - **Two-Level Hierarchical Locking**: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner.
     - **Exclusive Drain Protocol**: `_drain_inference_permits()` drains all permits before model swaps or evictions, eliminating swap races and C++ access violations.
     - **Bounded Queue Wait**: `_INFERENCE_SEMAPHORE.acquire(timeout=5.0s)` prevents indefinite thread hangs.
     - **Strict English-Only Invariant**: `VALID_LOCAL_MODELS = ("english", "typed-decisions")`. All multilingual model loading unconditionally raises `ValueError` ("forbidden").
     - **Debounced Windows RAM Protection**: `get_available_ram_mb()` incorporates `psutil` with Windows `ctypes.windll.kernel32.GlobalMemoryStatusEx` fallback. `is_ram_pressure_critical()` requires 3 consecutive breaches over >= 5s before evicting a warm model when idle.
  3. `omni_engine/providers/broker.py`: Master `SystemOneBroker` implementing `SystemOneProvider` with ironclad User Model Sovereignty (`USER_LOCKED` prohibits silent fallback; `USER_PREFERRED` emits explanatory telemetry; `AUTO` optimizes within allowlist).
  4. `omni_engine/decision/concurrency_benchmark.py`: Empirical load testing harness measuring p50, p95, throughput, and RAM deltas for concurrency levels 1, 2, and 4 on CPU. Proven: cold start is ~47.4s / 1.67 GB RAM, warm inference is ~712ms (concurrency 2: 2.79 req/s).
  5. `omni_engine/decision/calibration_eval.py`: Deterministic 70/30 stratified corpus partition (72 dev / 31 test) and 10-bin Expected Calibration Error (ECE) metric calculator.
  6. `docs/research/ADR_SYSTEM_ONE_BROKER.md`: Architectural Decision Record for broker, sovereignty, and concurrency hierarchy.
  7. `tests/test_foundation_broker.py`: 27 comprehensive unit tests with 100% pass rate.
- **Adversarial Reviews**:
  - Plan Review: Conditional Approval with 4 Blocking Requirements (`7886b073-0966-4305-b637-72f242f498c0`).
  - Diff Review: **PASS (UNCONDITIONAL)** (`5e8a88cd-a846-4ef9-b639-22afb9b791c2`).

---

## 2. Active Phase R1: Deep Research Engine

### Objective
Build a real, evidence-first deep research engine capable of multi-source discovery, crawl, extraction, dynamic-page fallback, evidence normalization, relevance ranking, gap detection, evidence saturation stopping, generative synthesis, and claim-level verification with zero hallucination.

### Research Gate & Technology Audit (`docs/research/ADR_R1_DEEP_RESEARCH.md`)
Evaluate candidates:
- Tavily Search / Extract / Map / Crawl
- Crawl4AI
- Scrapling (Installed)
- Existing LAYA web tools (`web_search`, `scrape_url`)
- Citation Verifier architecture
Formally record ADOPT, ADAPT, REFERENCE ONLY, REJECT decisions.

### Architecture & Pipeline Components
1. **Contracts (`omni_engine/contracts/research.py`)**:
   - `ResearchSourceQuality` (Domain authority, TLS, freshness, reputation).
   - `EvidenceItem`: Canonical URL, title, publisher, retrieval timestamp, content hash, passage text, claim IDs, relevance score, support/contradiction state, confidence.
   - `ResearchClaim`: Claim text, verification status, cited evidence IDs.
   - `ResearchBudget`: `max_search_queries` (default 5), `max_urls` (default 20), `max_pages_per_domain` (default 3), `max_total_pages` (default 10), `max_wall_time_sec` (default 60.0), `evidence_saturation_threshold` (default 0.85).
   - `ResearchDossier`: User query, sub-queries, evidence ledger, synthesized summary, verified claims, citations, execution telemetry.
2. **Prompt-Injection Defense**:
   - All crawled/scraped content wrapped in `<untrusted_external_data origin="url">`.
   - Strips instruction override patterns and injection vectors before semantic ranking or synthesis.
3. **Research Engine (`omni_engine/research/engine.py`)**:
   - `DeepResearchEngine`:
     - Step 1: Sub-query decomposition via System One / Generative tier.
     - Step 2: Multi-source discovery (Tavily search / DuckDuckGo / web tools).
     - Step 3: URL canonicalization and deduplication.
     - Step 4: Source-quality screening and filtering.
     - Step 5: Page extraction with fallback (Scrapling / BeautifulSoup / text extractor).
     - Step 6: Evidence normalization and System One relevance scoring.
     - Step 7: Gap detection and saturation stop evaluation.
     - Step 8: Synthesis and claim-level citation verification.
4. **Capability Registration (`omni_engine/capabilities/definitions.py`)**:
   - High-level capability: `research.deep`
   - Bounded execution with strict `ResearchBudget`.
5. **Test Suite (`tests/test_r1_research.py`)**:
   - Offline fixture tests: multi-query research, conflicting-source handling, dynamic-page fallback, malicious prompt injection defense, saturation stop.
   - Opt-in live integration test behind marker.

---

## 3. Strict Goal Boundaries
- Current Goal: `Foundation Gate (Complete) → R1 (Active) → R2 → R3 → R4 → R5`
- **HARD STOP AFTER R5**:
  Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
