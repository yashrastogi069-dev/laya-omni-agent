# ACTIVE_PLAN.md — Checkpoint R2: Real Browser Engine (ACTIVE) & R1: Deep Research Engine (COMPLETED)

## 1. Summary of Completed Checkpoint R1: Deep Research Engine
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **18/18 unit tests passed in 0.012s; 277/277 full repository tests (+ 47 subtests = 324 total) passed (100% pass rate)**.
- **Key Deliverables**:
  1. `docs/research/ADR_R1_DEEP_RESEARCH.md`: Technology audit adopting Scrapling (0.4.9), adapting Tavily & Citation Verifier, rejecting Crawl4AI (~3GB RAM footprint).
  2. `omni_engine/contracts/research.py`: Typed contracts for `EvidenceItem` (SHA-256 passage hash, deterministic `ev_<hash[:10]>`), `ResearchClaim`, `ResearchBudget`, `ResearchTelemetry`, `ResearchDossier`, `EvidenceStance`, `ClaimVerificationStatus`, `FetchMethod`.
  3. `omni_engine/research/sanitizer.py`: NFKC unicode normalization, zero-width / control character stripping, XML tag escaping, instruction override neutralization, and `<untrusted_external_data origin="..." hash="...">` framing.
  4. `omni_engine/research/fetcher.py`: URL canonicalization (stripping tracking query parameters and fragments), domain extraction, and `PageFetcher` multi-tier fallback (Scrapling -> BS4 -> Mock fixtures).
  5. `omni_engine/research/engine.py`: Master `DeepResearchEngine`:
     - Deterministic facet query decomposition (System 1 text generation strictly forbidden under REQ-B1).
     - Bounded discovery and crawl loop with explicit `(url, depth)` tuple queuing ensuring depth <= 1 enforcement.
     - Word 3-gram Jaccard deduplication ($J \ge 0.70$).
     - Sequential System 1 relevance scoring ($r \ge 0.45$) and stance classification.
     - Mathematical saturation yield stopping ($Y_k \le 0.15$ for 2 rounds).
     - Dossier synthesis with cryptographic citation verification quarantining unverified citations to `[UNVERIFIED_CITATION: <id>]`.
  6. `omni_engine/capabilities/definitions.py`: Canonical `DEEP_RESEARCH_SPEC` and `build_real_capability_registry()` preserving 23 source tools on canonical registry.
  7. `omni_engine/policy/engine.py` & `omni_engine/arguments/resolver.py`: Gated under `SAFE_ASSISTANT` with `ActionClass.READ_ONLY` and deterministic slot extraction.
  8. `tests/test_r1_research.py`: 18 comprehensive tests with 100% pass rate.
- **Adversarial Reviews**:
  - Plan Review: Conditional Approval with 5 Blocking Requirements (`e22ca329-86dd-4263-a208-d69ae9cb8471`).
  - Diff Review: **PASS (APPROVED FOR CHECKPOINT R1)** (`e5f6870e-ea3f-4969-83b9-1e169887f9d4`).
- **Non-Switching Principle**: `omni_agent.py` and `omni_engine/planner.py` remain 100% untouched.

---

## 2. Active Phase R2: Real Browser Engine

### Objective
Build a persistent, verified browser engine using Playwright (installed) supporting:
1. Persistent user browser session / profile context (retaining logins, cookies, state).
2. Dynamic indexed interactive action space (elements labeled `@1`, `@2`, `@3` with bounding boxes, tag, role, text).
3. Strongly typed browser interaction primitives: `navigate`, `click`, `type`, `select`, `scroll`, `extract_text`, `screenshot`.
4. Evidence-based post-action verification (DOM mutation confirmation, URL navigation confirmation, visual assertion).
5. Purchase and high-risk action confirmation gating (strict `POLICY_CONTROLLED` / `ALWAYS` confirmation before checkout, payments, or destructive account settings).

### Technology Audit & Candidates (`docs/research/ADR_R2_BROWSER_ENGINE.md`)
Evaluate candidates:
- Playwright (Installed: `playwright 1.54.4`)
- Chromium / Edge Persistent Context
- DOM Tree Accessibility Tree vs HTML Scraping
- Action Space Labeling (Numeric overlay vs Ref IDs)
- Anti-Detection / Bot Stealth Tactics
Formally record ADOPT, ADAPT, REFERENCE ONLY, REJECT decisions.

### Architecture & Pipeline Components
1. **Contracts (`omni_engine/contracts/browser.py`)**:
   - `BrowserActionType`: `NAVIGATE`, `CLICK`, `TYPE`, `PRESS_KEY`, `SELECT_OPTION`, `SCROLL`, `WAIT`, `EXTRACT_DOM`, `SCREENSHOT`, `CONFIRM_PURCHASE`.
   - `BrowserElement`: `element_id` (`@1`, `@2`), `tag_name`, `role`, `text`, `href`, `is_visible`, `is_interactive`, `bounding_box`.
   - `BrowserSnapshot`: `url`, `title`, `elements: List[BrowserElement]`, `interactive_count`, `screenshot_path`, `timestamp`.
   - `BrowserActionRequest`: `action_type`, `target_element_id`, `text_value`, `key_value`, `scroll_delta`, `expected_outcome`.
   - `BrowserActionResult`: `success`, `action_type`, `previous_url`, `current_url`, `dom_mutated`, `verification_status`, `error`.
2. **Session & Process Lifecycle (`omni_engine/browser/session.py`)**:
   - Manages Playwright process lifecycle, headless vs headed execution, persistent profile directory, and automatic cleanup.
   - Resource-safe: enforces single active browser instance and memory caps to respect host 8GB RAM.
3. **DOM Action Indexer (`omni_engine/browser/indexer.py`)**:
   - Deterministic extraction of interactive elements (buttons, inputs, links, selects, textareas).
   - Generates compact, structured action index `@1..@N` avoiding context bloating.
4. **Driver & Action Executor (`omni_engine/browser/driver.py`)**:
   - Executes primitive actions and verifies physical state transitions (DOM change, URL change, network idle).
   - Enforces human confirmation before checkout / purchase / financial actions (`ActionClass.FINANCIAL`).
5. **Capability Registration (`omni_engine/capabilities/definitions.py`)**:
   - High-level capability: `browser.perform_task` or `browser.interact`
   - Bounded execution with deterministic verification.
6. **Test Suite (`tests/test_r2_browser.py`)**:
   - Offline mock / fixture tests for element indexing, action validation, purchase confirmation gating, and error handling.
   - Live integration test for local HTML files.

---

## 3. Strict Goal Boundaries
- Current Goal: `Foundation Gate (Complete) → R1 (Complete) → R2 (Active) → R3 → R4 → R5`
- **HARD STOP AFTER R5**:
  Under NO circumstances implement Quest runtime (L10), Operation Ledger (L11), Planner (L12), DAG Validator (L13), or DAG Executor (L14).
