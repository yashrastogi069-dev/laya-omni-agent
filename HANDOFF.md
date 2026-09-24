# HANDOFF.md — Operational Continuation Guide (Checkpoint R1 COMPLETED; Phase R2 ACTIVE)

## What We Have Built (Current State)
A **trustworthy pre-execution control plane, provider broker, and real capability execution engines** powered by:
- **Phase R1: Deep Evidence-Grounded Research Engine**:
  - `DeepResearchEngine`: Deterministic facet query decomposition (System 1 generation strictly forbidden), bounded discovery and crawl loop with explicit `(url, depth)` tuple queuing ensuring depth <= 1 enforcement, 3-gram Jaccard deduplication ($J \ge 0.70$), sequential System 1 relevance scoring and stance classification, mathematical saturation yield stopping ($Y_k \le 0.15$ for 2 rounds), and cryptographic citation verification quarantining unverified citations.
  - `sanitizer.py`: Untrusted external data isolation, NFKC normalization, zero-width / control character stripping, XML tag escaping, and `<untrusted_external_data origin="..." hash="...">` containment framing.
  - `fetcher.py`: URL canonicalization (stripping tracking query parameters and fragments), domain extraction, and `PageFetcher` multi-tier fallback (Scrapling -> BS4 -> Mock fixtures).
  - Canonical `DEEP_RESEARCH_SPEC` and `build_real_capability_registry()` preserving 23 source tools on canonical registry.
- **Foundation Gate: System 1 Provider Broker**:
  - Fast provider routing under ironclad User Model Sovereignty (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`), allowlist enforcement, and task overrides.
  - Hierarchical Two-Level Locking: Level 1 (`_MODEL_LIFECYCLE_LOCK`, RLock) outer, Level 2 (`_INFERENCE_SEMAPHORE`, Semaphore) inner, with exclusive permit draining on swaps/evictions.
  - Strict English-Only Invariant: Prohibits multilingual checkpoints and language detection routines (`VALID_LOCAL_MODELS = ("english", "typed-decisions")`).
  - Debounced Windows RAM Protection: Telemetry via `psutil` with Windows `ctypes.windll.kernel32.GlobalMemoryStatusEx` fallback; requires 3 consecutive breaches over >=5s before idle eviction.
  - Empirical Concurrency Benchmark: Cold start is ~47.4s / 1.67 GB RAM; warm inference is ~712ms (concurrency 2: 2.79 req/s).
  - Deterministic Stratified Calibration: 70/30 stratified partition (72 dev / 31 test) and 10-bin Expected Calibration Error (ECE) metric evaluation harness.
- **Pre-Execution Control Plane (L0–L9)**:
  - System 1 Decision Fabric (L7.5) with ModernBERT-large and two-stage adaptive triage.
  - Hierarchical Capability Routing (L6A/L6B) with multi-tier tool catalog reduction.
  - Skills Layer (L7) with workflow manifests and safety floors.
  - Typed Argument Resolution Engine (L8) with sub-millisecond extraction (0.118 ms).
  - Deterministic Policy Engine (L9) with sub-millisecond evaluation (~0.15ms warm) enforcing Inviolable Rule-0 Invariants.
- **Strongly Typed Capability Contracts**: Clean interface boundaries throughout (`CapabilityInvocation`, `CapabilitySpec`, `ToolResult`, `EvidenceItem`, `ResearchClaim`, `ResearchBudget`, `ResearchTelemetry`, `ResearchDossier`, `PolicyDecision`, `ArgumentResolutionEnvelope`).

---

## Current Architecture & State
- Repository: Public GitHub `https://github.com/yashrastogi069-dev/laya-omni-agent` on branch `laya-autonomous-v2`.
- Active Milestone Goal: **Real Capability Engines: Foundation Gate (COMPLETE) → Phase R1 (COMPLETE & VERIFIED) → Phase R2: Real Browser Engine (ACTIVE)**.
- Full Test Suite: **277/277 tests passing (+ 47 subtests = 324 total, 100% pass rate)** in 161.40s across 15 test modules:
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
  - `tests/test_l9_policy.py` (25 tests)
  - `tests/test_foundation_broker.py` (27 tests)
  - `tests/test_r1_research.py` (18 tests)
- Governance: All canonical documents synchronized with verified implementation truth.
- Non-Switching Boundary: `omni_agent.py` and `omni_engine/planner.py` have **0 diffs**.

---

## Deliverables Summary for Phase R1
1. **Contracts (`omni_engine/contracts/research.py`)**:
   - `EvidenceItem` with passage-level SHA-256 hash and deterministic `ev_<hash[:10]>` ID.
   - `ResearchClaim`, `ResearchBudget`, `ResearchTelemetry`, `ResearchDossier`, `EvidenceStance`, `ClaimVerificationStatus`, `FetchMethod`.
2. **Untrusted Content Sanitizer (`omni_engine/research/sanitizer.py`)**:
   - NFKC normalization, zero-width character stripping, control character removal, XML escaping, instruction override neutralization, and `<untrusted_external_data>` framing.
3. **Page Fetcher (`omni_engine/research/fetcher.py`)**:
   - URL canonicalization (stripping tracking parameters and fragments), domain extraction, and `PageFetcher` fallback chain.
4. **Research Engine (`omni_engine/research/engine.py`)**:
   - Multi-source discovery, bounded crawl loop with `(url, depth)` tuple queuing, 3-gram Jaccard deduplication, System 1 relevance & stance evaluation, saturation yield stopping, dossier synthesis, and cryptographic citation verification.
5. **Substrate Registration**:
   - Canonical `DEEP_RESEARCH_SPEC` in `omni_engine/capabilities/definitions.py`, `build_real_capability_registry()`, `PolicyEngine` registration, and `ArgumentResolver` extraction.
6. **Independent Adversarial Review**: **PASS (APPROVED FOR CHECKPOINT R1)** (`e5f6870e-ea3f-4969-83b9-1e169887f9d4`).

---

## Operational Boundary & Next Phase
- **Active Phase**: **Phase R2 — Real Browser Engine**.
- **Core Next Steps for R2**:
  1. Produce technology audit & ADR in `docs/research/ADR_R2_BROWSER_ENGINE.md`.
  2. Implement Playwright browser session lifecycle with persistent context.
  3. Implement DOM action space indexer (`@1..@N` interactive element overlay).
  4. Implement browser interaction driver (click, type, navigate, scroll, extract, screenshot).
  5. Implement evidence-based action verification (DOM mutation confirmation, URL change verification).
  6. Enforce purchase and financial action confirmation gates.
  7. Test in `tests/test_r2_browser.py`, run adversarial reviews, commit.
- **Hard Stop Boundary**: Stop cleanly after R5. Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
