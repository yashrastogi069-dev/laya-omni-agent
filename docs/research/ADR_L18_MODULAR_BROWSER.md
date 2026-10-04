# ADR-024: Checkpoint L18 — Modular Browser Capability Rebuild

**Status**: ACCEPTED  
**Date**: 2026-10-05  
**Author**: LAYA Omni Agent Architecture Team  
**Scope**: Checkpoint L18: Modular Browser Capability Rebuild  
**Related ADRs**:
- `ADR_R2_BROWSER_ENGINE.md` (Phase R2: Real Persistent Browser Engine)
- `ADR_SYSTEM_ONE_BROKER.md` (System 1 Broker & Resource Calibration)
- `ADR_L13_PLAN_VALIDATOR.md` (Deterministic Plan Validator)
- `ADR_L14_DETERMINISTIC_DAG_EXECUTOR.md` (Deterministic DAG Executor)
- `ADR_L15_COMPLETION_VERIFIER.md` (Evidence-Based Completion Engine)

---

## 1. Context & Motivation

In Phase R2, the LAYA Omni Agent implemented a persistent browser engine backed by Microsoft Playwright (`BrowserSession`, `DOMActionIndexer`, `BrowserDriver`), featuring an indexed action space (`@1..@N`), element staleness detection, and intrinsic financial action gating.

However, all browser capabilities were consolidated into a single multi-purpose tool `browser_interact` (aliased as `browser.interact`) accepting a mandatory `action` discriminator property (`navigate`, `click`, `type`, `press_key`, `select_option`, `scroll`, `snapshot`, `screenshot`, `confirm_purchase`).

This monolithic structure presented four major operational limitations:
1. **Planner & Decomposition Friction**: Planning models (`StructuredDAGPlanner`, `GenerativePlanner`) and syntactic objective decomposers (`ObjectiveDecomposer`) had to artificially synthesize complex nested arguments (`{"action": "navigate", "url": "..."}`) rather than emitting direct semantic capability invocations (`browser.navigate`).
2. **Coarse-Grained Policy Classification**: Because `browser_interact` accommodated mutating interactions (clicking buttons, submitting forms), its capability spec was classified uniformly as `ActionClass.EXTERNAL_UPDATE` under `AutonomyProfile.LOCAL_OPERATOR`. As a result, inherently harmless read-only actions (such as taking a DOM snapshot or extracting text) inherited elevated risk profiles.
3. **Absence of Dedicated In-Page Extraction**: Scraping text or attribute data required full DOM snapshot processing or downstream Python scripts, rather than an optimized in-page extraction primitive.
4. **Single-Tab Rigidity**: To protect the 8GB host RAM limit on Windows, `BrowserSession` strictly enforced `max_pages=1`, intercepting popups and forcing navigation in the primary tab. While safe, this completely prevented legitimate multi-tab workflows, comparative browsing, and controlled tab switching.

Checkpoint L18 resolves these limitations by **rebuilding browser capabilities into first-class atomic primitives** while preserving complete backward compatibility with the legacy `browser_interact` facade.

---

## 2. Invariants & Repository Invariants

1. **Deterministic Control (Invariant 1)**:
   - Models propose capability invocations and arguments; the deterministic runtime validates schemas, enforces autonomy tiers and confirmation policies, manages browser sessions, and executes actions.
2. **Strongly Typed Contracts (Invariant 4)**:
   - Every atomic browser capability is governed by a dedicated Pydantic v2 contract (`extra="forbid"`), defining typed request parameters and evidence outcome receipts.
3. **Evidence-Based Completion (Invariant 6)**:
   - Actions emit physical receipts verifying the real-world outcome (e.g. `url_changed`, `dom_mutated`, `input_value`, `extracted_count`, `screenshot_path`).
4. **Host Safety & 8GB RAM Protection**:
   - Chromium contexts run with low-memory launch flags (`--disable-dev-shm-usage`, `--no-sandbox`, `--disable-gpu`, `--disable-extensions`).
   - Multi-tab management strictly bounds active tabs to `max_tabs = 5`, preventing runaway memory consumption.
5. **Financial & High-Risk Safety Gate (REQ-B4)**:
   - Actions targeting checkout, payment, or purchase elements strictly require human confirmation (`user_confirmed=True`) regardless of whether invoked via `browser.click` or legacy `browser_interact`.
6. **Canonical 23-Tool Registry Invariant**:
   - `build_canonical_registry()` retains exactly the 23 base tools from L3. Atomic modular browser capabilities are registered in `build_real_capability_registry()`.
7. **Non-Switching Boundary**:
   - `omni_agent.py` and `omni_engine/planner.py` maintain **EXACTLY 0 DIFFS**.

---

## 3. Atomic Capability Architecture

Checkpoint L18 registers 7 discrete, first-class atomic browser capabilities:

| Capability ID | Dotted / Dotless Alias | Action Class | Autonomy Profile | Confirmation Policy | Idempotency Class | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `browser.navigate` | `browser_navigate` | `EXTERNAL_NETWORK` | `SAFE_ASSISTANT` | `NEVER` | `NATURAL` | Navigate active page to specified URL with DOM load verification. |
| `browser.snapshot` | `browser_snapshot` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `READ_ONLY` | Capture and index interactive action space (`@1..@N`) with financial detection. |
| `browser.click` | `browser_click` | `EXTERNAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NON_IDEMPOTENT` | Click interactive element (`@N` or selector) with DOM mutation verification and financial gating. |
| `browser.type` | `browser_type` | `EXTERNAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NON_IDEMPOTENT` | Type text into input field with physical `input_value` verification and enter-key submission. |
| `browser.extract` | `browser_extract` | `READ_ONLY` | `SAFE_ASSISTANT` | `NEVER` | `READ_ONLY` | Extract text or attributes from DOM elements matching a CSS selector. |
| `browser.screenshot` | `browser_screenshot_v2` | `LOCAL_CREATE` | `SAFE_ASSISTANT` | `NEVER` | `NATURAL` | Capture page or element screenshot to disk with file existence verification. |
| `browser.tabs` | `browser_tabs` | `LOCAL_UPDATE` | `LOCAL_OPERATOR` | `POLICY_CONTROLLED` | `NON_IDEMPOTENT` | Manage browser tabs (`list`, `new`, `switch`, `close`) with strict `max_tabs=5` bound. |

### Backward Compatibility Facade
The existing `browser_interact` (and alias `browser.interact`) capability remains registered in `build_real_capability_registry()` and delegates directly to `BrowserDriver`, ensuring existing plans, tests, and skills remain 100% operational without disruption.

---

## 4. Multi-Tab Lifecycle & Memory Safety

To support controlled multi-tab workflows while adhering to the 8GB RAM safety envelope:
1. **Tab Representation (`TabInfo`)**:
   - `tab_id`: Integer index (0-indexed).
   - `url`: Current page URL.
   - `title`: Current page title.
   - `is_active`: Boolean indicating whether this page is the current active foreground tab.
2. **Bounded Capacity (`max_tabs = 5`)**:
   - Attempting to open a tab beyond the limit raises `BrowserTabLimitExceededError` or returns `success=False` with a descriptive error.
3. **Tab Operations**:
   - `list`: Enumerates all open pages in the persistent context, updating title and URL.
   - `new`: Spawns a new page in the context (if under limit), optionally navigates to a URL, and sets it as the active page.
   - `switch`: Sets the active page reference to the target `tab_id` and brings it to the front.
   - `close`: Closes the target tab (or active tab if not specified). If the active tab was closed, sets the active page to the highest remaining tab index. At least one page is always preserved.

---

## 5. Technology Evaluation: ADOPT / ADAPT / REJECT

| Component / Pattern | Decision | Rationale |
| :--- | :--- | :--- |
| **Atomic Capability Separation** | **ADOPT** | Decouples monolithic `browser_interact` into 7 typed capabilities, improving planner ergonomics and fine-grained security policy. |
| **In-Page DOM Extraction (`browser.extract`)** | **ADOPT** | Fast `page.evaluate()` extraction avoids serializing large DOM trees across IPC boundaries, saving RAM and CPU cycles. |
| **Bounded Multi-Tab Management (`browser.tabs`)** | **ADOPT** | Replaces rigid `max_pages=1` with bounded `max_tabs=5` to support popups and multi-site workflows safely. |
| **Unified Facade Preservation (`browser_interact`)** | **ADOPT** | Retains existing tool spec for 100% backwards compatibility with R2 test suite and existing plans. |
| **Heavy External Browser Wrappers (Selenium, Puppeteer)** | **REJECT** | Playwright is already installed, reliable, and provides superior async/sync Chromium integration. |
| **Unbounded Tab Spawning** | **REJECT** | Spawning arbitrary numbers of tabs risks out-of-memory crashes on 8GB Windows host machines. |

---

## 6. Consequences & Verification Plan

### Positive Consequences
- Planners can compose natural multi-step plans (`browser.navigate -> browser.snapshot -> browser.click -> browser.extract`).
- Read-only capabilities (`browser.snapshot`, `browser.extract`) execute under `SAFE_ASSISTANT` without prompting operators.
- Tab management allows complex workflows without crashing or leaking memory.
- Evidence-based completion verifiers can independently verify each atomic outcome receipt.

### Verification Plan
- Authored dedicated unit test suite `tests/test_l18_modular_browser.py`:
  - 100% offline unit execution using mock Playwright page/context fixtures.
  - Contract validation with `extra="forbid"`.
  - Atomic capability dispatch for all 7 capabilities.
  - Multi-tab lifecycle: `list`, `new`, `switch`, `close`, and `max_tabs=5` boundary enforcement.
  - In-page extraction: text, attributes, multiple matches, selector fallbacks.
  - Financial safety gating on `browser.click` and `browser.type`.
  - Full repository regression suite (all 603+ tests passing).
