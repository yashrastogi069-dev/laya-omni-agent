# ADR_R2_BROWSER_ENGINE: Real Persistent Browser Engine Architecture

**Status**: PROPOSED & AUDITED  
**Date**: 2026-09-24  
**Scope**: Phase R2 (Real Capability Engines: R1 → R5)  
**Authors**: LAYA Autonomous Architecture Team

---

## 1. Context & Problem Statement

The legacy LAYA browser implementation (`omni_engine/tools/browser_tools.py`) consists of two single-shot, ephemeral functions:
- `tool_visual_browse(url_or_query)`: Launches a fresh Edge window, sleeps 1s, extracts paragraphs, sleeps 5s, closes browser.
- `tool_browser_screenshot(url, output_path)`: Launches a fresh Edge window, sleeps 1.5s, screenshots, closes browser.

This design suffers from critical architectural limitations:
1. **Zero Session Persistence**: Every invocation launches a fresh browser, discarding session cookies, authenticated logins, shopping cart state, and local storage.
2. **No Interactive Action Space**: The agent cannot perform multi-step web interactions (e.g. click next page, fill login form, select dropdown, submit query) because it cannot address specific page elements.
3. **No Outcome Verification**: There is no verification that a click or form submission produced the intended real-world state transition.
4. **No Financial Confirmation Gating**: Autonomous purchasing or payment submission lacks a deterministic policy boundary.
5. **Context Window Exhaustion**: Dumping raw HTML (which can easily exceed 50,000 tokens) causes severe context bloat and hallucinated selectors.

---

## 2. Technology Audit & Candidate Evaluation

| Technology | Evaluation | Decision | Rationale |
| :--- | :--- | :--- | :--- |
| **Playwright Python (1.54.4)** | Pre-installed, native Chromium (`chrome.exe`) and Edge support, robust async/sync API, built-in locators and network listeners. | **ADOPT** | High reliability, active maintenance, supports persistent contexts out of the box. |
| **Selenium WebDriver** | Heavyweight external driver binaries, slower startup, fragile element staleness. | **REJECT** | Unnecessary duplicate dependency; Playwright is already installed and faster. |
| **Persistent User Context** | Stores user profile in dedicated directory (`~/.laya/browser_profile`), retaining logins, cookies, and local storage across turns. | **ADOPT** | Essential for real-world agent workflows requiring authenticated sessions. |
| **Raw HTML Dumps** | Dumps raw HTML string into LLM context. | **REJECT** | Causes context bloat (20k–100k tokens), token costs, and selector hallucinations. |
| **Indexed Action Space (`@1..@N`)** | Extracts interactive elements (buttons, inputs, links, selects, textareas) and maps them to clean integer indices `@1`, `@2`, `@3` with accessible names and bounding boxes. | **ADOPT** | Compact representation (~500 tokens), unambiguous deterministic addressing, zero LLM XPath/CSS hallucination. |
| **Pure Vision Coordinates (VLM click x,y)** | Requires continuous high-resolution VLM vision inference per step. | **REJECT (LOCAL)** | Host machine lacks CUDA GPU and has 8GB RAM; vision coordinate estimation is too slow on CPU. |
| **Evidence-Based Action Verification** | Computes pre/post DOM hash, URL change, network idle state, and returns physical execution receipts. | **ADOPT** | Adheres to Invariant 6 (Evidence-Based Completion); never assumes a click succeeded without proof. |
| **Financial / Purchase Confirmation Gate** | Scans target elements and URLs for financial keywords (`checkout`, `pay`, `buy`, `order`, `card`, `cvv`) and requires explicit human confirmation. | **ADOPT** | Adheres to Invariant 1 and `docs/SECURITY_AND_POLICY.md` (`ActionClass.FINANCIAL`). |

---

## 3. Architecture Specification

### 3.1 Session & Process Lifecycle (`omni_engine/browser/session.py`)
- `BrowserSession`: Singleton manager holding active `BrowserContext` and `Page`.
- Supports configurable profile directory (defaults to `~/.laya/browser_profile`).
- Dual execution mode:
  - **Headless mode** (`headless=True`): Fast, low-memory background execution for automated tasks and tests.
  - **Headed mode** (`headless=False`): Interactive visual execution with HUD when user monitoring is requested.
- Resource guard: Only 1 persistent context active simultaneously to prevent host RAM exhaustion. Automatic idle timeout and cleanup.

### 3.2 Dynamic Indexed Action Space (`omni_engine/browser/indexer.py`)
- Evaluates accessibility tree and DOM to query all visible, enabled interactive elements:
  - `button`, `a[href]`, `input`, `select`, `textarea`, `[role=button]`, `[role=link]`, `[role=checkbox]`, `[role=menuitem]`, `[role=tab]`.
- Assigns indexed label `@1`, `@2`, ... `@N`.
- For each element, captures:
  - `index`: `@1`
  - `tag_name`: `button`
  - `role`: `button`
  - `text`: Accessible name or visible text (e.g. "Add to Cart")
  - `value`: Current value for inputs
  - `href`: Destination URL for links
  - `bounding_box`: `{x, y, width, height}`
  - `is_interactive`: `True`
- Emits structured `BrowserSnapshot` envelope.

### 3.3 Strongly Typed Action Primitives (`omni_engine/browser/driver.py`)
- Supported actions:
  - `NAVIGATE`: `goto(url)` with timeout and DOM wait.
  - `CLICK`: click element by `@N` or CSS selector with automatic scroll-into-view.
  - `TYPE`: fill text into input element by `@N`.
  - `PRESS_KEY`: send keyboard event (e.g. `Enter`, `Tab`, `Escape`).
  - `SELECT_OPTION`: select dropdown value by `@N`.
  - `SCROLL`: scroll page vertically/horizontally.
  - `EXTRACT_DOM`: capture current snapshot of indexed interactive elements.
  - `SCREENSHOT`: capture page screenshot to disk.
- Returns structured `BrowserActionResult` with `dom_mutated: bool`, `url_changed: bool`, `previous_url: str`, `current_url: str`, `verification_status: VerificationStatus`.

### 3.4 Safety & Financial Confirmation Gate
- Pre-execution check: If action targets an element or URL with financial markers:
  - Keywords: `pay`, `checkout`, `buy now`, `place order`, `purchase`, `credit card`, `cvv`, `billing`
  - Or `action_type == BrowserActionType.CONFIRM_PURCHASE`
- Action is classified as `ActionClass.FINANCIAL`.
- `PolicyEngine` enforces `ConfirmationPolicy.ALWAYS`. Execution is strictly blocked unless `user_confirmed=True`.

---

## 4. Invariant Compliance Checklist

- [x] **Deterministic Control**: Action resolution, element indexing, and confirmation checks are deterministic rules.
- [x] **Evidence-Based Outcome**: Actions verify physical state changes (URL, DOM mutation, element presence).
- [x] **Host Safety & RAM Protection**: Single browser instance; headless default; bounded element extraction (capped at 100 elements).
- [x] **Non-Switching Boundary**: Existing `tool_visual_browse` in `browser_tools.py` remains intact; new engine lives in `omni_engine/browser/`.
