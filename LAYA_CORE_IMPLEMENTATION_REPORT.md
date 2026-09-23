# LAYA_CORE_IMPLEMENTATION_REPORT.md — Checkpoint L0 Ground Truth & Evidence Report

**Repository**: `LAYA Omni Agent`  
**Generated At**: 2026-09-23T06:18:00+05:30  
**Inspection Mode**: Strict Repository Truth & Verification Protocol (L0)  

---

## A. Repository / Git State
- **Root Directory**: `C:\Users\win 10\Desktop\LAYA`
- **Active Branch**: `main`
- **Remote Origin**: `https://github.com/yashrastogi069-dev/laya-omni-agent.git` (Public repository)
- **HEAD Commit**: `ced5b52` (*"feat: Initial release of LAYA Omni-Agent v2.5 (Dual-System Autonomous Operating Engine)"*)
- **Working Tree**: Clean, untracked canonical docs and test suite initialized.
- **Python Environment**: Python 3.12.10 (win32).
- **Installed Key Packages**: `laya` (0.3.5), `typesafe-sdk` (0.7.1), `playwright` (1.60.0), `tavily-python` (0.7.24), `psutil` (7.2.2), `pyperclip` (1.11.0), `pillow` (12.3.0), `openai` (2.44.0), `rich` (15.0.0), `pytest` (9.1.1).

---

## B. Actual Current Architecture
The current system runs through an interactive CLI loop (`laya_agent.py`):
1. **User Mission Input**: Sent to `AutonomousPlanner.plan_and_execute(mission_prompt)`.
2. **Keyword Workflow Branch**: String matching against `["dossier", "report", "deep research", "analyze", "explain in depth", "how to"]`. If triggered, it executes a hardcoded 3-phase sequence:
   - `tool_web_search(mission_prompt)` (Tavily search)
   - `tool_visual_browse(mission_prompt)` (Playwright Edge popup)
   - `sys2.synthesize_dossier(mission_prompt, combined_context)` (OpenRouter LLaMA 3.3 70B)
3. **Single Tool Dispatch Branch**: If keywords do not match, `System1Router.route_tool()` is invoked.
   - Slices `OMNI_TOOL_REGISTRY` to `[:12]` (truncating the registry from 23 tools to 12).
   - Calls local ModernBERT `laya_router.predict()` on a single `choice` question.
   - Returns chosen tool name and latency.
4. **Execution**: Directly calls `tool_func(mission_prompt)` without argument extraction or validation.
5. **Memory**: Logs the raw query, tool name, and first 250 characters of result to `memory/omni_memory.json`, incrementing execution count unconditionally.

---

## C. Intended Architecture Described by Documentation
The documentation (README) claimed:
- A fully unified dual-system autonomous personal agent.
- Sub-35ms routing across 23+ production tools.
- Real-time visual Edge automation with modular capabilities (`browser_navigate`, `browser_click_element`, `browser_type_text`, `browser_extract_text`).
- Autonomous multi-step goal planning and decomposition.
- Self-improving continuous memory that learns from every run.

---

## D. Differences Between Documentation and Reality
1. **Tool Catalog Visibility**: README claimed 23+ production tools are routable. Reality: `system1.py` lines 42-49 slice `list(tool_catalog.items())[:12]`, rendering 11 tools (`powershell`, `file_read`, `file_write`, `run_python`, `safe_math`, etc.) completely invisible to System 1.
2. **Browser Modularity**: README claimed modular Playwright primitives exist. Reality: `browser_tools.py` only implements two monolithic functions (`tool_visual_browse` and `tool_browser_screenshot`).
3. **Planning**: README claimed an autonomous multi-step planner. Reality: Planning is a 7-word keyword check that executes a hardcoded 3-step script; `is_complex_multi_step()` is dead code.
4. **Tool Arguments**: README implied natural interaction with tools. Reality: The raw user prompt is passed verbatim as the only argument, causing tools like `file_read`, `file_write`, and `powershell` to fail on normal queries.
5. **Continuous Memory**: README claimed experience-based learning. Reality: Memory is a JSON file that performs substring matching on words with `len > 3` and increments a counter upon execution, regardless of outcome.
6. **Defect in Safe Math**: README claimed safe arithmetic evaluation. Reality: `tool_safe_math` crashed on every call with `NameError: name 're' is not defined`.
7. **Antigravity Bridge**: README claimed active System 2 Antigravity escalation. Reality: `escalate_to_antigravity()` is defined but never invoked in any execution path.

---

## E. Production vs Prototype Map

| File Path | Classification | Role / Description |
| :--- | :--- | :--- |
| `laya_agent.py` | **PRODUCTION** | Primary Rich CLI entry point. |
| `omni_engine/__init__.py` | **PRODUCTION** | Package initialization. |
| `omni_engine/system1.py` | **PRODUCTION** | Local System 1 ModernBERT router (requires L1 refactor). |
| `omni_engine/system2.py` | **PRODUCTION** | Cloud API OpenRouter synthesis engine. |
| `omni_engine/planner.py` | **PRODUCTION** | Current goal planner (requires replacement with DAG engine). |
| `omni_engine/memory.py` | **PRODUCTION** | JSON memory persistence engine. |
| `omni_engine/tools/__init__.py` | **PRODUCTION** | Tool registry index (23 tools). |
| `omni_engine/tools/web_tools.py` | **PRODUCTION** | Web search, scraper, REST tester, file downloader. |
| `omni_engine/tools/browser_tools.py` | **PRODUCTION** | Playwright Edge browser automation. |
| `omni_engine/tools/os_tools.py` | **PRODUCTION** | Hardware stats, processes, clipboard, screenshot, powershell. |
| `omni_engine/tools/dev_tools.py` | **PRODUCTION** | File read/write, code grep, directory tree, python sandbox. |
| `omni_engine/tools/data_tools.py` | **PRODUCTION** | SQLite query runner, CSV/JSON inspector, math evaluator. |
| `START_LAYA_AGENT.bat` | **PRODUCTION** | One-click Windows desktop batch launcher. |
| `tests/test_l0_baselines.py` | **TEST** | Baseline unit test suite asserting ground truth. |
| `omni_agent.py` | **PROTOTYPE** | Predecessor CLI wrapper. |
| `ultimate_autonomous_agent.py` | **PROTOTYPE** | Monolithic 488-line predecessor script. |
| `realtime_laya_agent.py` | **PROTOTYPE** | Early Tavily + Edge experiment. |
| `laya_autonomous_agent.py` | **PROTOTYPE** | Early autonomous agent experiment. |
| `windows_agent.py` | **PROTOTYPE** | Early Windows desktop app experiment. |
| `laya_live_browser.py` | **PROTOTYPE** | Early Playwright experiment. |
| `laya_showcase.py` | **DEMO** | Showcase script for Laya classification benchmarks. |
| `test_laya.py` | **DEMO** | Single ticket classification script (no assertions). |
| `test_live_browser.py` | **DEMO** | Browser opening script (no assertions). |
| `test_models.py` | **DEMO** | Laya vs Jev 5-prompt benchmark script (no assertions). |
| `launch_*.bat`, `run_agent.bat` | **LEGACY** | Predecessor batch launch files. |

---

## F. System One / LAYA Audit
- **Underlying Checkpoint**: `ModernBERT-large` (421M parameters) fine-tuned classifier via `laya.Router()`.
- **Latency**: 15ms – 35ms on host CPU (warm); ~300ms (cold load).
- **RAM Footprint**: ~400MB RAM.
- **Current Query Schema**: Single `choice` question (`target_tool`) with criteria truncated to 85 characters.
- **Missing Signals**: No urgency score, no importance score, no risk class, no ambiguity flag, no need-for-planning flag, no confidence distribution.
- **Fallback**: TypeSafe Jev cloud API supported when `TYPESAFE_API_KEY` is present.

---

## G. Generative / System Two Audit
- **Provider**: OpenRouter API (`https://openrouter.ai/api/v1`).
- **Model**: `meta-llama/llama-3.3-70b-instruct`.
- **Purpose**: Generates markdown intelligence dossiers during keyword-triggered research workflows.
- **Timeout / Fallback**: 30-second timeout; falls back to static structured summary string if API key is absent or request fails.
- **Dead Code**: `escalate_to_antigravity()` generates `escalations/pending_task.json` and attempts `agy.exe --print`, but is never invoked by any runtime caller.

---

## H. Capability Inventory (All 23 Tools)

| Capability | Domain | Registered? | Routable? | Accepted Arguments | Side Effects | Risk Class | Timeout | Verification | Confirmed Defect |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `web_search` | web | YES | YES | `query: str` | None | READ_ONLY | 15s | None | None |
| `scrape_url` | web | YES | YES | `url: str` | None | READ_ONLY | 12s | None | Takes first word only |
| `http_api` | web | YES | YES | `payload: str` | HTTP request | EXTERNAL_CREATE | 10s | None | Natural language breaks parser |
| `download_file` | web | YES | YES | `payload: str` | Writes file to disk | LOCAL_CREATE | 15s | None | Natural language breaks parser |
| `visual_browse` | browser | YES | YES | `url_or_query: str`| Launches GUI Edge | READ_ONLY | 25s | None | Sleeps 5s, monolithic |
| `browser_screenshot`| browser | YES | YES | `url: str, output_path`| Writes image file | LOCAL_CREATE | 15s | None | Natural language breaks URL |
| `system_diagnostics`| os | YES | YES | `_: str = ""` | None | READ_ONLY | 5s | None | None (safe default arg) |
| `list_processes` | os | YES | YES | `filter_query: str`| None | READ_ONLY | 5s | None | Prompt breaks filter |
| `kill_process` | os | YES | YES | `pid_or_name: str` | Terminates process | SYSTEM_ACTION | 5s | None | Unconfirmed process kill |
| `launch_app` | os | YES | YES | `app_name: str` | Spawns GUI process | SYSTEM_ACTION | 5s | None | Keyword-only detection |
| `desktop_screenshot`| os | YES | YES | `filename: str` | Writes image file | LOCAL_CREATE | 5s | None | Prompt becomes filename |
| `clipboard` | os | YES | YES | `action_text: str` | Clipboard read/write | LOCAL_UPDATE | 3s | None | Keyword-only detection |
| `powershell` | os | YES | **NO** (sliced) | `command: str` | Executes command | SYSTEM_ACTION | 12s | None | Excluded from System 1 |
| `ping_test` | os | YES | **NO** (sliced) | `host: str` | Sends ICMP ping | READ_ONLY | 8s | None | Excluded from System 1 |
| `file_read` | dev | YES | **NO** (sliced) | `filepath: str` | Reads disk file | READ_ONLY | 5s | None | Excluded; prompt breaks path |
| `file_write` | dev | YES | **NO** (sliced) | `payload: str` | Writes disk file | LOCAL_CREATE | 5s | None | Excluded; prompt breaks format |
| `search_code` | dev | YES | **NO** (sliced) | `query: str` | None | READ_ONLY | 8s | None | Excluded from System 1 |
| `directory_tree` | dev | YES | **NO** (sliced) | `folder: str` | None | READ_ONLY | 5s | None | Excluded from System 1 |
| `run_python` | dev | YES | **NO** (sliced) | `code: str` | Executes script | LOCAL_CREATE | 10s | None | Excluded; prompt breaks syntax |
| `git_status` | dev | YES | **NO** (sliced) | `_: str = ""` | None | READ_ONLY | 5s | None | Excluded from System 1 |
| `sqlite_exec` | data | YES | **NO** (sliced) | `sql_query: str` | DB query / mutate | LOCAL_UPDATE | 8s | None | Excluded; prompt breaks SQL |
| `inspect_data` | data | YES | **NO** (sliced) | `file_path: str` | Reads dataset | READ_ONLY | 5s | None | Excluded; prompt breaks path |
| `safe_math` | data | YES | **NO** (sliced) | `expression: str` | None | READ_ONLY | 3s | None | **NameError: name 're' is not defined** |

---

## I. Argument Handling Audit
In `AutonomousPlanner.plan_and_execute()`, line 60 executes:
```python
result = tool_func(mission_prompt)
```
The raw user prompt is passed directly to the function. This breaks nearly all non-search tools when a user types natural instructions like *"read the file README.md"*, *"kill process 1234"*, or *"calculate 15 * 8"*. An explicit `ArgumentResolver` is required.

---

## J. Quest / Planning Audit
- Current planning is rudimentary keyword matching against 6 words.
- No task graph, no dependency resolution, no step state machine.
- `is_complex_multi_step()` in `planner.py` is defined but never invoked.
- Tasks do not persist; a crash or error during multi-step execution discards all progress.

---

## K. Browser Automation Audit
- `browser_tools.py` contains Playwright Edge automation with an injected CSS neon HUD.
- Lacks modularity: cannot navigate, click, type, or extract in separate steps.
- Closes the browser after every single call with a hardcoded `sleep(5.0)`, causing extreme latency.
- Must be rebuilt into persistent browser session primitives (`browser.navigate`, `browser.click`, `browser.type`, `browser.extract`, `browser.screenshot`).

---

## L. Memory Audit
- Storage: `memory/omni_memory.json`.
- Key Inconsistency: Loaded JSON had `tool_effectiveness` while code expected `tool_success_counts`.
- Invariant Flaw: Execution count is incremented blindly upon tool completion, even if the tool failed.
- Retrieval: Substring match on words with `len > 3` returns last 3 matches. Lacks true episodic recall or semantic search.

---

## M. Security & Action-Safety Audit
- Zero confirmation gates currently protect destructive operations (`kill_process`, `file_write`, `powershell`).
- Untrusted data (scraped web pages) is passed directly to generative prompts without isolation tags or sanitization.

---

## N. Test & Evaluation Audit
- Automated test assertions before L0: **0**.
- Automated test assertions after L0: **10** (all passing in `tests/test_l0_baselines.py`).
- Defect reproduction tests confirmed the `safe_math` NameError and System 1 `[:12]` truncation.

---

## O. Performance & Latency Risks
- System 1 inference on local ModernBERT takes 15ms – 35ms (acceptable).
- Memory footprint is ~400MB (safe on 8GB host machine).
- Unnecessary 5-second sleep in `tool_visual_browse` causes browser sluggishness.

---

## P. Confirmed Runtime Defects
1. **ISSUE-01**: `tool_safe_math` crashes with `NameError: name 're' is not defined`.
2. **ISSUE-02**: `System1Router.route_tool` slices catalog to `[:12]`, excluding 11 tools.
3. **ISSUE-03**: Raw prompt passed directly to tools instead of extracted typed arguments.
4. **ISSUE-04**: `OmniMemory` schema key mismatch (`tool_effectiveness` vs `tool_success_counts`).
5. **ISSUE-05**: Dead code: `is_complex_multi_step()` and `escalate_to_antigravity()` never called.
6. **ISSUE-06**: Discrepancy between README browser capabilities and implementation.

---

## Q. Healthy Components to Preserve
- Local Laya `ModernBERT-large` sub-35ms routing foundation.
- Baseline OS tools (`system_diagnostics`, `desktop_screenshot`, `clipboard`).
- Baseline Dev tools (`directory_tree`, `search_code`, `git_status`).
- Tavily web search integration.
- Playwright Edge neon HUD injection concept.
- Rich terminal console UI.

---

## R. Components Requiring Replacement
- `AutonomousPlanner` → Replace with Structured DAG Planner & Deterministic DAG Executor.
- Raw tool argument passing → Replace with Typed `ArgumentResolver`.
- Raw tool dictionary → Replace with `CapabilityRegistry` exposing `CapabilitySpec`.

---

## S. Components That Should Be Refactored Rather Than Replaced
- `System1Router` → Refactor into `LayaProvider` implementing `SystemOneProvider` and returning `DecisionFrame`.
- `tool_safe_math` → Refactor to add `import re` and robust arithmetic evaluation.
- `OmniMemory` → Refactor for schema backward-compatibility before Memory V2.
- `browser_tools.py` → Refactor into modular session-backed primitives.

---

## T. Proposed Target Architecture
Documented comprehensively in `docs/ARCHITECTURE.md`.

---

## U. L0 Tests and Commands Run
```powershell
python -m pip install pytest
python -m unittest tests/test_l0_baselines.py
python -m pytest tests/test_l0_baselines.py
```

---

## V. Exact Results
All 10 tests passed with 0 failures and 0 errors:
- `test_tool_registry_count`: PASS (23 tools)
- `test_tool_categories`: PASS (5 categories)
- `test_all_tools_have_required_fields`: PASS
- `test_defect_safe_math_missing_re_import`: PASS (reproduced NameError)
- `test_defect_system1_tool_catalog_truncation`: PASS (proved 11 tools hidden)
- `test_defect_prompt_passed_directly_as_file_read_arg`: PASS (proved prompt breakage)
- `test_system_diagnostics`: PASS
- `test_directory_tree`: PASS
- `test_git_status`: PASS
- `test_memory_load_and_keys`: PASS

---

## W. Open Risks
- Host RAM capacity (7.8GB total, ~83% currently in use). Do not load heavy local generative models.
- Interactive GUI context required for `Pillow ImageGrab` and full-screen Edge Playwright browser.

---

## X. Documentation Created / Updated
1. `AGENTS.md`
2. `LAYA_BUILD_STATE.md`
3. `HANDOFF.md`
4. `tasks/MASTER_PLAN.md`
5. `tasks/ACTIVE_PLAN.md`
6. `tasks/DECISIONS.md`
7. `tasks/KNOWN_ISSUES.md`
8. `tasks/DEFERRED.md`
9. `tasks/lessons.md`
10. `docs/ARCHITECTURE.md`
11. `docs/CAPABILITY_CONTRACT.md`
12. `docs/AUTOMATION_MODEL.md`
13. `docs/SECURITY_AND_POLICY.md`
14. `tests/test_l0_baselines.py`
15. `LAYA_CORE_IMPLEMENTATION_REPORT.md`

---

## Y. L1 Executed Scope & Results (COMPLETED)
1. **`tool_safe_math` Repair**: Added `import re` and implemented a strict `ast.NodeVisitor` arithmetic evaluator. Whitelisted safe operators (`+`, `-`, `*`, `/`, `//`, `%`, `**`), math functions (`sqrt`, `abs`, `round`, `sin`, `cos`), and constants (`pi`, `e`, `tau`). Defended against computational exhaustion (`**` capped at exponent 100) and sandbox escapes (`__import__`, attribute access).
2. **`OmniMemory` Schema Normalization & Atomic Persistence**: Implemented dynamic key migration (`tool_effectiveness` → `tool_success_counts`, `learned_facts` → `learned_insights`), atomic file persistence (`.tmp` write then `os.replace`), crash resilience for corrupted/empty files, and verified success tracking.
3. **Preserved Legacy Routing Defect**: Retained `[:12]` slice test as a documented legacy limitation; rejected flat 23-tool dump in favor of upcoming Checkpoint L6 (Hierarchical Capability Routing).
4. **Test Suite Verification**: Created `tests/test_l1_repairs.py` (12 tests). Ran full test suite (`tests/test_l0_baselines.py` + `tests/test_l1_repairs.py`): **22/22 tests passed via pytest in 5.06s (100% pass rate)**.

---

## Z. L1.1 Hardening Pass Scope & Results (COMPLETED)
1. **OmniMemory 3-State Outcome Tracking**:
   - Default outcome explicitly set to `UNVERIFIED` (`None`). Execution never automatically implies verified success.
   - Distinct tracking for `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, and `UNVERIFIED`.
   - Separate counters for `invocation_count`, `verified_success_count`, `verified_failure_count`, and `unverified_count`.
   - Automatic corrupted/malformed JSON quarantine to `<filepath>.corrupt.<timestamp>`, ensuring zero historical data loss and graceful default reinitialization.
2. **Deterministic Resource Bounds on `tool_safe_math`**:
   - Expression length capped at 256 characters.
   - AST node count capped at 40 nodes.
   - Numeric literal magnitude capped at `1e100`.
   - Factorial parameter bounded to integer `0 <= n <= 100`.
   - Exponent magnitude capped at `abs(exp) <= 100`, base capped at `abs(base) <= 1e6` if `abs(exp) > 10`.
3. **Branch Creation**:
   - Created and pushed architecture branch `laya-autonomous-v2`.

---

## AA. L2 Foundational Typed Contracts Scope & Results (COMPLETED)
1. **Canonical Package Structure (`omni_engine/contracts/`)**:
   - `base.py`: `BaseContractModel` enforcing `model_config = ConfigDict(extra="forbid", validate_assignment=True)`.
   - `enums.py`:
     - `ActionClass`: 11 levels (`READ_ONLY`, `LOCAL_CREATE`, `LOCAL_UPDATE`, `LOCAL_DELETE`, `EXTERNAL_CREATE`, `EXTERNAL_UPDATE`, `EXTERNAL_SEND`, `EXTERNAL_DELETE`, `SYSTEM_ACTION`, `SECURITY_SENSITIVE`, `FINANCIAL`).
     - `AutonomyProfile`: 5 tiers (`ADVISOR`, `SAFE_ASSISTANT`, `LOCAL_OPERATOR`, `TRUSTED_OPERATOR`, `WORKFLOW_AUTHORIZED`).
     - `ErrorCode`: 12 codes (`INVALID_ARGUMENT`, `NOT_FOUND`, `PERMISSION_DENIED`, `CONFIRMATION_REJECTED`, `TIMEOUT`, `NETWORK_ERROR`, `PROCESS_FAILED`, `RATE_LIMITED`, `SCHEMA_VIOLATION`, `UNAUTHORIZED_ACTION`, `UNKNOWN_COMMIT`, `UNKNOWN`).
     - `VerificationStatus`: 3 states (`VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `UNVERIFIED`).
     - `DecisionSignalType`: 12 types (`INTENT`, `TASK_CLASS`, `DOMAIN`, `SKILL`, `URGENCY`, `IMPORTANCE`, `RISK`, `REVERSIBILITY`, `AMBIGUITY`, `NEEDS_PLAN`, `NEEDS_TOOLS`, `MODEL_TIER`).
   - `decision.py`:
     - `DecisionSignal`: strictly bounded confidence in `[0.0, 1.0]`, NaN/Inf rejection, probability distribution validation, and latency tracking.
     - `DecisionFrame`: complete System 1 decision packet incorporating all 10 core signals (including Invariant 7 `reversibility`), candidate domains/skills, latency profiling, and provider ID.
   - `capability.py`:
     - `CapabilitySpec`: pure JSON-serializable specification separated from callables (`id`, `name`, `version`, `domain`, `description`, `action_class`, `autonomy_profile`, `idempotent`, `side_effects`, `requires_confirmation`, `retryable`, `timeout_seconds`, `input_schema`, `output_schema`, `verification_strategy`).
     - `ExecutableCapability`: Python-side runtime binding pairing a `CapabilitySpec` with executable callables and availability checks.
     - `ToolError`: canonical error envelope with `code`, `message`, `details`, `retryable`, and `fix_action`.
     - `ExecutionReceipt`: physical audit record of execution (`receipt_id`, `operation_id`, `capability_id`, timestamps, `duration_ms`, `exit_code`, bytes read/written, `raw_output_ref`).
     - `VerificationResult`: physical evidence verification record (`status`, `strategy`, `evidence`, `notes`, `verified_at`).
     - `ToolResult`: canonical envelope strictly enforcing:
       - `success == True` -> `error is None`.
       - `success == False` -> `error is not None` and `data is None`.
   - `agent.py`:
     - `TraceContext`: distributed tracing context (`trace_id`, `parent_id`, `session_id`).
     - `AgentRequest`: inbound user/system query envelope with context and tracing.
     - `AgentResponse`: structured terminal or intermediate agent output with decision frame, receipts, verifications, and timing.
     - `AgentEvent`: event envelope for internal asynchronous event bus.

2. **Automated Test Coverage**:
   - Created `tests/test_l2_contracts.py` with 18 comprehensive tests.
   - All 40 repository tests (`tests/test_l0_baselines.py`, `tests/test_l1_repairs.py`, `tests/test_l2_contracts.py`) passed in 6.11s with 100% pass rate.

---

## AB. Adversarial Reviews
- **Adversarial Plan Review**: Subagent reviewed proposed contract schemas against `docs/CAPABILITY_CONTRACT.md` and `AGENTS.md`. Identified `ActionClass` naming nuances, missing `UNKNOWN_COMMIT` and `CONFIRMATION_REJECTED` error codes, and the need to include `REVERSIBILITY` under Invariant 7. All incorporated before coding.
- **Adversarial Diff Review**: Subagent reviewed implementation diff for race conditions, contract leaks, and schema exclusivity. Status: **PASS** across all dimensions with zero premature runtime logic leaks.

---

## AC. Exact Next Engineering Action
Begin Checkpoint L3 (Canonical Capability Registry & ToolResult Envelopes):
- Wrap all 23 existing tools into `CapabilitySpec` contracts with typed schemas.
- Enforce standardized `ToolResult` return envelopes across all tools with zero uncaught exceptions.

