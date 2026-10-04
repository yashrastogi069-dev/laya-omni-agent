# PRACTICAL_FINDINGS.md — Real Manual & Practical Integration Findings

This document is the canonical repository record of practical integration and runtime findings discovered during real manual testing and practical execution of the LAYA Omni Agent (Checkpoints L10 through L14.3).

All findings are permanently preserved with reproduction prompts, observed results, root causes, affected components, planned fixes, and resolution statuses.

---

## Index of Practical Findings

| ID | Title | Severity | Status | Affected Files |
| :--- | :--- | :--- | :--- | :--- |
| **PRACT-001** | Local System One routing is unacceptably slow on 8 GB Windows host | Medium (Performance) | RESOLVED | `omni_engine/providers/broker.py`, `omni_engine/routing/router.py` |
| **PRACT-002** | Fail-open routing successfully rescues some wrong domain classifications | Low (Reliability) | DOCUMENTED & PRESERVED | `omni_engine/routing/router.py` |
| **PRACT-003** | Local domain routing misclassified obvious desktop requests | Medium (Routing) | RESOLVED | `omni_engine/routing/router.py` |
| **PRACT-004** | Generic adapter execution-context leakage passes `idempotency_key` into legacy tools | High (Runtime Crash) | RESOLVED | `omni_engine/capabilities/adapters.py` |
| **PRACT-005** | Older/legacy capabilities can outrank newer R-series implementations | Medium (Quality) | RESOLVED | `omni_engine/routing/router.py`, `omni_engine/capabilities/registry.py` |
| **PRACT-006** | Capability aliases consume candidate slots as if they were independent capabilities | Medium (Routing) | RESOLVED | `omni_engine/routing/router.py` |
| **PRACT-007** | `perform_git_inspection` contains an invalid template (`search_code` missing `query`) | High (DAG Validation Failure) | RESOLVED | `omni_engine/skills/definitions.py` |
| **PRACT-008** | Plan firewall correctly rejects malformed template DAGs before execution | Low (Safety) | VERIFIED & PRESERVED | `omni_engine/planning/validator.py`, `omni_engine/execution/executor.py` |
| **PRACT-009** | Contextual create-vs-overwrite confirmation for file writes works correctly | Low (Safety) | VERIFIED & PRESERVED | `omni_engine/policy/engine.py` |
| **PRACT-010** | Successfully resumed steps remain `COMPLETED` while retaining stale confirmation in `error` | Medium (State Hygiene) | RESOLVED | `omni_engine/execution/executor.py` |
| **PRACT-011** | Missing-input clarification does not continue the same user intention/Quest | High (Session Continuity) | RESOLVED | `omni_engine/session/manager.py`, `laya_v2_cli.py` |
| **PRACT-012** | Previous PowerShell Rule-0 test was blocked for the wrong reason | Medium (Safety Precision) | RESOLVED | `omni_engine/policy/rules.py` |
| **PRACT-013** | Explicit imperative capability requests can be hijacked by an incompatible skill | Medium (Routing) | RESOLVED | `omni_engine/routing/router.py` |
| **PRACT-014** | Critical-process Rule-0 protection works end-to-end | Low (Safety) | VERIFIED & PRESERVED | `omni_engine/policy/engine.py`, `omni_engine/policy/rules.py` |
| **PRACT-015** | Successful execution receipts contain no completion verification yet, ending at `AWAITING_VERIFICATION` | Invariant (L15 Gate) | ENFORCED & VERIFIED | `omni_engine/execution/executor.py` |
| **PRACT-016** | Manual practical benchmarks must become permanent regression gates | Medium (Testing) | RESOLVED | `tests/test_l14_3_practical.py` |
| **PRACT-017** | Tavily/search exceptions are swallowed and converted into empty result arrays | Medium (Observability) | RESOLVED | `omni_engine/tools/web_tools.py`, `omni_engine/research/engine.py` |
| **PRACT-018** | Research fetch failure telemetry can report misleading fetch-method information | Low (Telemetry) | RESOLVED | `omni_engine/research/engine.py` |
| **PRACT-019** | Environment-variable precedence masked a malformed/misnamed secrets file | Medium (Configuration) | RESOLVED | `.gitignore`, `omni_engine/config.py`, `laya_v2_cli.py` |
| **PRACT-020** | Actual local secrets file is `keys.env`, not `keys` | High (Security) | RESOLVED | `.gitignore` |
| **PRACT-021** | Research acquisition quality differs significantly by fetch path/site | Low (Reliability) | RESOLVED | `omni_engine/research/engine.py`, `omni_engine/research/fetcher.py` |
| **PRACT-022** | Template-first planning can silently drop uncovered clauses of multi-intent objectives | High (Planning Correctness) | RESOLVED | `omni_engine/contracts/objective.py`, `omni_engine/planning/engine.py` |
| **PRACT-023** | Failed research page fetches consume page budget and prevent backfilling | Medium (Research Efficiency) | RESOLVED | `omni_engine/research/engine.py` |
| **PRACT-024** | Final fetch failure can incorrectly report `SCRAPLING` even after fallback cascade | Low (Telemetry) | RESOLVED | `omni_engine/research/engine.py` |
| **PRACT-025** | Semantically malformed URLs such as `https://https://...` pass argument validation | High (Input Safety) | RESOLVED | `omni_engine/arguments/validator.py`, `omni_engine/arguments/resolver.py` |
| **PRACT-026** | n8n/automation capabilities exist below router but automation is not a first-class routing domain | High (Routing) | RESOLVED | `omni_engine/routing/router.py` |
| **PRACT-027** | Unrelated clauses of compound objectives contaminate capability-specific arguments | High (Argument Quality) | RESOLVED | `omni_engine/arguments/resolver.py`, `omni_engine/planning/decomposer.py` |
| **PRACT-028** | Interactive runtime lacks conversational continuation and referent binding (`this`, etc.) | High (Usability) | RESOLVED | `omni_engine/session/manager.py`, `laya_v2_cli.py` |
| **PRACT-029** | Temporary `v2_cli_test.py` bypasses StructuredDAGPlanner for skills with required inputs | Medium (Integration) | RESOLVED | `laya_v2_cli.py` |
| **PRACT-030** | Secret-bearing files require stronger read-side protection/redaction | High (Security) | RESOLVED | `omni_engine/policy/rules.py`, `omni_engine/policy/engine.py` |
| **PRACT-031** | Ordinary browser navigation is over-classified as a high-risk `SYSTEM_ACTION` | High (Operator Policy) | RESOLVED | `omni_engine/policy/engine.py`, `omni_engine/contracts/policy.py` |
| **PRACT-032** | Browser Navigate + Screenshot objectives collapse into Navigate only | High (Plan Coverage) | RESOLVED | `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py` |
| **PRACT-033** | Complex repository inspection collapses into `directory_tree` only | High (Plan Coverage) | RESOLVED | `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py` |
| **PRACT-034** | Mixed web + repository objectives collapse into one capability/domain | High (Plan Coverage) | RESOLVED | `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py` |
| **PRACT-035** | OS + n8n compound objectives drop automation requirements | High (Plan Coverage) | RESOLVED | `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py` |
| **PRACT-036** | Selecting a skill is incorrectly treated as evidence that skill covers complete user goal | Critical (Planning Invariant) | RESOLVED | `omni_engine/contracts/objective.py`, `omni_engine/planning/engine.py` |

---

## Detailed Records

### PRACT-001 — Local System One Routing Latency on 8 GB Host
- **Reproduction**: Run 15-question `DecisionFrame` or single question inference using `LayaProvider` (ModernBERT-large on CPU).
- **Observed Result**: Single question inference: ~749ms. Full 15-question frame: ~15.4s. Host RAM usage: ~1.2 GB model footprint.
- **Root Cause**: ModernBERT-large (395M parameters) executes on host CPU without AVX-512/CUDA acceleration.
- **Affected Source**: `omni_engine/providers/system1.py`, `omni_engine/providers/broker.py`.
- **Planned Fix**: Provide `SystemOneBroker` with user-selectable provider policies (`USER_LOCKED`, `USER_PREFERRED`, `AUTO`). Enable Jev provider (`LAYA_SYSTEM1_PROVIDER=jev`) for sub-35ms remote inference when configured, while preserving deterministic local fallback.
- **Tests Added**: `tests/test_foundation_broker.py`, `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-002 — Fail-Open Routing Rescues Misclassified Domains
- **Reproduction**: Prompt with ambiguous domain keywords where System 1 predicts wrong domain.
- **Observed Result**: Fail-open capability search across all domains matches target capability by name/embedding even when domain prediction is wrong.
- **Root Cause**: `Router.route()` includes secondary fallback to global capability registry when domain-specific filter yields no match.
- **Affected Source**: `omni_engine/routing/router.py`.
- **Planned Fix**: Retain fail-open design; document as intentional reliability invariant.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: VERIFIED & PRESERVED.

### PRACT-003 — Local Domain Routing Misclassifies Obvious Desktop Requests
- **Reproduction**: Prompt: `"Launch Notepad"` or `"Open Calculator"`.
- **Observed Result**: Misclassified to `system` or `generic` domain rather than `desktop`.
- **Root Cause**: Missing direct domain keyword pins for common desktop applications.
- **Affected Source**: `omni_engine/routing/router.py`.
- **Planned Fix**: Add desktop application keywords and pinned intent mappings to `CAPABILITY_PIN_MAP` in `router.py`.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-004 — Generic Adapter Execution-Context Leakage
- **Reproduction**: Execute legacy tool (e.g. `tool_launch_app` via capability `launch_app`) through `DeterministicDAGExecutor`.
- **Observed Result**: `TypeError: tool_launch_app() got an unexpected keyword argument 'idempotency_key'`.
- **Root Cause**: `make_adapter` in `omni_engine/capabilities/adapters.py` passed all execution metadata (`idempotency_key`, `quest_id`, `step_id`, `operation_id`, `attempt_id`) directly to the underlying callable via `**kwargs`.
- **Affected Source**: `omni_engine/capabilities/adapters.py`.
- **Planned Fix**: Filter kwargs against `spec.input_schema["properties"]`. Strip infrastructure metadata unless explicitly declared by capability spec or callable signature.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-005 — Legacy Capabilities Outranking Modern R-Series Implementations
- **Reproduction**: Route `"Launch Notepad"` or `"Research Python 3.12"`.
- **Observed Result**: Older `launch_app` outranked `desktop.launch_app`; basic `web_search` outranked `research.deep`.
- **Root Cause**: Capability ranking used simple alphabetical or insertion order without tier weighting for modern implementations.
- **Affected Source**: `omni_engine/routing/router.py`, `omni_engine/capabilities/registry.py`.
- **Planned Fix**: Assign canonical preference to R-series capabilities (`desktop.*`, `research.deep`, `browser.*`, `n8n.*`).
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-006 — Capability Aliases Consuming Multiple Candidate Slots
- **Reproduction**: Inspect candidate list returned by router for `"launch app"`.
- **Observed Result**: Both `launch_app` and `desktop.launch_app` occupied top candidate slots, pushing other relevant capabilities out.
- **Root Cause**: Aliases registered as distinct registry entries without family deduplication in ranking.
- **Affected Source**: `omni_engine/routing/router.py`.
- **Planned Fix**: Deduplicate capabilities by canonical family before ranking so one family occupies exactly one candidate slot.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-007 — `perform_git_inspection` Invalid Template
- **Reproduction**: Instantiate skill `perform_git_inspection` and validate generated Plan.
- **Observed Result**: Validation fails: step 2 (`search_code`) missing mandatory argument `query`.
- **Root Cause**: In `omni_engine/skills/definitions.py`, `perform_git_inspection` mapped `path` but omitted `query`.
- **Affected Source**: `omni_engine/skills/definitions.py`.
- **Planned Fix**: Add `query` parameter to `SkillManifest.input_schema` and map `query: "$inputs.query"` in step 2.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-008 — Plan Firewall Rejects Malformed DAGs Before Execution
- **Reproduction**: Attempt to execute plan with missing arguments or cycles.
- **Observed Result**: `DeterministicPlanValidator` rejects plan during Pass 4 (SCHEMA_CONFORMANCE) or Pass 1 (DAG_ACYCLICITY) with zero physical capability dispatches.
- **Root Cause**: Deterministic plan validation firewall correctly placed before execution.
- **Affected Source**: `omni_engine/planning/validator.py`, `omni_engine/execution/executor.py`.
- **Planned Fix**: Retain and strengthen.
- **Tests Added**: `tests/test_l13_validator.py`.
- **Final Status**: VERIFIED & PRESERVED.

### PRACT-009 — Contextual Create vs Overwrite Confirmation
- **Reproduction**: Execute `file_write` to new file vs existing file.
- **Observed Result**: Creating new file in workspace allows execution under `LOCAL_OPERATOR`; overwriting existing file requires confirmation.
- **Root Cause**: `PolicyEngine` checks destination file existence dynamically.
- **Affected Source**: `omni_engine/policy/engine.py`.
- **Planned Fix**: Retain and verify.
- **Tests Added**: `tests/test_l9_policy.py`.
- **Final Status**: VERIFIED & PRESERVED.

### PRACT-010 — Resumed Steps Retain Stale Confirmation Error
- **Reproduction**: Pause a step for confirmation (`PAUSED_FOR_CONFIRMATION`), confirm, resume, and inspect completed step.
- **Observed Result**: `step.status == COMPLETED` while `step.error == "Confirmation required: ..."` persisted.
- **Root Cause**: `executor.py` set `step.error` on pause but did not clear it upon successful completion.
- **Affected Source**: `omni_engine/execution/executor.py`.
- **Planned Fix**: Clear `step.error` on successful resumption or store confirmation prompt in `metadata["confirmation_prompt"]`.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-011 — Missing Input Clarification Breaks Session Continuation
- **Reproduction**: Issue prompt missing required argument (e.g. `"Run Python code:"`), respond with code in next turn.
- **Observed Result**: Second turn created a brand new Quest instead of resuming the paused Quest.
- **Root Cause**: Interactive runner lacked session state tracking for `active_quest_id` and did not route follow-ups to `resume_quest()`.
- **Affected Source**: `omni_engine/session/manager.py`, `laya_v2_cli.py`.
- **Planned Fix**: Track active paused Quest; resume same Quest upon input receipt.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-012 — PowerShell Rule-0 Test Blocked for Wrong Reason
- **Reproduction**: Test PowerShell command `Remove-Item -Recurse -Force C:\`.
- **Observed Result**: Blocked by path check rather than explicit command scanner.
- **Root Cause**: Protected path scan ran before command syntax scanner in Stage 0.
- **Affected Source**: `omni_engine/policy/rules.py`.
- **Planned Fix**: Ensure explicit command regex matches before generic path containment.
- **Tests Added**: `tests/test_l9_policy.py`.
- **Final Status**: RESOLVED.

### PRACT-013 — Imperative Capability Requests Hijacked by Incompatible Skill
- **Reproduction**: Prompt: `"Check local n8n service health on port 5678"`.
- **Observed Result**: Incompatible skill or web search hijacked intent.
- **Root Cause**: Skill matching score exceeded single capability pin score.
- **Affected Source**: `omni_engine/routing/router.py`.
- **Planned Fix**: Direct intent pins in `CAPABILITY_PIN_MAP` take absolute precedence over skill heuristic search.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-014 — Critical Process Rule-0 Protection Works End-to-End
- **Reproduction**: Attempt `kill_process(target="csrss.exe")` or `desktop.close_window(pid=4)`.
- **Observed Result**: Hard `DENY` with `SECURITY_SENSITIVE` error. Even `user_confirmed=True` cannot override.
- **Root Cause**: Stage 0 invariant rule in `PolicyEngine`.
- **Affected Source**: `omni_engine/policy/engine.py`.
- **Planned Fix**: Retain and preserve.
- **Tests Added**: `tests/test_l9_policy.py`.
- **Final Status**: VERIFIED & PRESERVED.

### PRACT-015 — Receipts End at AWAITING_VERIFICATION (L15 Gate)
- **Reproduction**: Execute multi-step Quest to completion.
- **Observed Result**: Quest transitions strictly from `RUNNING` to `AWAITING_VERIFICATION`. Never marks itself `COMPLETED`.
- **Root Cause**: Invariant 6 adherence.
- **Affected Source**: `omni_engine/execution/executor.py`.
- **Planned Fix**: Retain invariant.
- **Tests Added**: `tests/test_l14_executor.py`.
- **Final Status**: ENFORCED & VERIFIED.

### PRACT-016 — Practical Benchmarks as Permanent Regression Gates
- **Reproduction**: Code modifications can silently break composite workflows without failing narrow unit tests.
- **Observed Result**: Unit tests passed while real CLI flows failed.
- **Root Cause**: Lack of automated integration test suite running full practical prompts A through L.
- **Affected Source**: `tests/test_l14_3_practical.py`.
- **Planned Fix**: Implement `tests/test_l14_3_practical.py` with tests A through L.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-017 — Tavily Exceptions Swallowed into Empty Arrays
- **Reproduction**: Invoke `web_search` with invalid or expired API key.
- **Observed Result**: Returned `[]` with no indication of network/auth failure.
- **Root Cause**: Broad `except Exception: return []` in web tools.
- **Affected Source**: `omni_engine/tools/web_tools.py`, `omni_engine/research/engine.py`.
- **Planned Fix**: Return structured `ToolResult` with `ToolOutcome.FAILURE` and specific `ErrorCode`.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-018 — Misleading Research Fetch Telemetry
- **Reproduction**: Research engine attempts Scrapling, fails, falls back to BS4, fails.
- **Observed Result**: Telemetry reported `method=SCRAPLING`.
- **Root Cause**: `method` attribute initialized to first attempted method and not updated upon fallback.
- **Affected Source**: `omni_engine/research/engine.py`.
- **Planned Fix**: Track `attempted_methods: List[str]`, `successful_method: Optional[str]`, and `errors_by_method: Dict[str, str]`.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-019 — Environment Variable Precedence Masking Secret Files
- **Reproduction**: Set `OPENROUTER_API_KEY` in environment while having different key in `keys.env`.
- **Observed Result**: Process environment took precedence without logging which configuration source was active.
- **Root Cause**: Standard `os.environ.get()` lookup without source provenance.
- **Affected Source**: `laya_v2_cli.py`.
- **Planned Fix**: Log configuration source provenance (e.g. `[Config] Loaded OPENROUTER_API_KEY from keys.env`) without printing secret values.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-020 — Local Secrets File Name Discrepancy (`keys.env`)
- **Reproduction**: Check `.gitignore` for secrets.
- **Observed Result**: `.gitignore` contained `keys` but not `keys.env` or `*.env`.
- **Root Cause**: Incomplete `.gitignore` patterns.
- **Affected Source**: `.gitignore`.
- **Planned Fix**: Add `keys`, `.env`, `*.env`, `keys.env` to `.gitignore`.
- **Tests Added**: Working tree inspection.
- **Final Status**: RESOLVED.

### PRACT-021 — Research Acquisition Quality Varies by Fetch Path
- **Reproduction**: Scrape complex JS-rendered site vs static HTML site.
- **Observed Result**: Static BS4 fails on JS hydration; headless browser succeeds.
- **Root Cause**: Heterogeneous web targets require tiered acquisition cascade.
- **Affected Source**: `omni_engine/research/fetcher.py`.
- **Planned Fix**: Tiered cascade: Scrapling / Playwright -> Requests/BS4 -> Readability extractor.
- **Tests Added**: `tests/test_r1_research.py`.
- **Final Status**: RESOLVED.

### PRACT-022 — Template-First Planning Silently Drops Uncovered Clauses
- **Reproduction**: Prompt: `"Diagnose system health, list top processes, and save to C:\report.txt"`.
- **Observed Result**: Matched skill `diagnose_system` generated a 2-step plan, completely dropping the `"save to report.txt"` requirement.
- **Root Cause**: Planner returned template immediately without verifying that all mandatory clauses of the objective were satisfied.
- **Affected Source**: `omni_engine/planning/engine.py`, `omni_engine/contracts/objective.py`.
- **Planned Fix**: Decompose objective into `RequirementItem`s; treat template as a building block; augment plan with missing steps (e.g. `file_write`); enforce 100% mandatory requirement coverage before execution.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-023 — Failed Fetches Exhaust Research Page Budget
- **Reproduction**: 2 out of 5 search results return 403/404; research terminates with 0 evidence.
- **Observed Result**: Budget of 2 pages exhausted by the 2 failed fetches.
- **Root Cause**: `max_pages` bounded total attempts rather than successful acquisitions.
- **Affected Source**: `omni_engine/research/engine.py`.
- **Planned Fix**: Separate `max_fetch_attempts` (e.g. 6) from `max_successful_pages` (e.g. 2); backfill from remaining candidates.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-024 — Final Fetch Failure Reporting `SCRAPLING`
- **Reproduction**: Fallback fetch failure where all tiers fail.
- **Observed Result**: Error envelope reported `SCRAPLING_FAILED` even though BS4 and urllib also failed.
- **Root Cause**: Final error message string interpolation used initial method name.
- **Affected Source**: `omni_engine/research/engine.py`.
- **Planned Fix**: Aggregate error across all attempted tiers (`"All acquisition tiers failed: Scrapling (timeout), BS4 (403)"`).
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-025 — Semantically Malformed URLs Passing Validation
- **Reproduction**: Pass URL `"https://https://hydrahd.ws.com"` or `"ftp://invalid"`.
- **Observed Result**: Schema validation passed because string type matched schema.
- **Root Cause**: Lack of semantic URL validation in argument resolver and plan validator.
- **Affected Source**: `omni_engine/arguments/validator.py`, `omni_engine/arguments/resolver.py`.
- **Planned Fix**: Implement `SemanticArgumentValidator.validate_url()`: single scheme, HTTP/HTTPS only, valid hostname.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-026 — Missing First-Class Automation/n8n Routing
- **Reproduction**: Prompt: `"List my n8n workflows"`.
- **Observed Result**: Routed to `web_search` or `system` domain because `automation` was not in `DOMAIN_KEYWORD_MAP`.
- **Root Cause**: n8n capabilities implemented in R4 were registered in `CapabilityRegistry` but missing domain keyword mapping and direct intent pins in `router.py`.
- **Affected Source**: `omni_engine/routing/router.py`.
- **Planned Fix**: Add `automation` domain with keywords (`n8n`, `workflow`, `workflows`) and direct pins for `list_workflows`, `get_workflow`, `validate_workflow`, and local health.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-027 — Compound Objective Clauses Contaminating Arguments
- **Reproduction**: Prompt: `"Search web for Python 3.12 release date and save to C:\foo.txt"`.
- **Observed Result**: Search tool invoked with query `"Search web for Python 3.12 release date and save to C:\foo.txt"`.
- **Root Cause**: Argument resolver used full raw objective string instead of isolated requirement clause.
- **Affected Source**: `omni_engine/arguments/resolver.py`, `omni_engine/planning/decomposer.py`.
- **Planned Fix**: Decomposer extracts clause boundaries; argument resolver maps requirement-specific clause to capability arguments.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-028 — Lack of Conversational Continuation & Referent Binding
- **Reproduction**: Turn 1: `"Search web for Python 3.12"`. Turn 2: `"Save this to C:\report.txt"`.
- **Observed Result**: Turn 2 failed or created unrelated code execution Quest because `this` could not be resolved.
- **Root Cause**: Interactive runner lacked session state tracking for `last_tool_result`.
- **Affected Source**: `omni_engine/session/manager.py`, `laya_v2_cli.py`.
- **Planned Fix**: Implement `SessionManager` maintaining `last_tool_result` and dynamic `$session.last_result` binding.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-029 — Temporary CLI Bypassing StructuredDAGPlanner
- **Reproduction**: Run `v2_cli_test.py` with multi-step prompt.
- **Observed Result**: Shortcut code constructed single-step plan directly from top candidate capability.
- **Root Cause**: Prototype shortcut in `v2_cli_test.py`.
- **Affected Source**: `laya_v2_cli.py`.
- **Planned Fix**: Replace prototype shortcut with full runtime pipeline in production `laya_v2_cli.py`.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-030 — Secret-Bearing File Protection
- **Reproduction**: Tool execution: `file_read(path=".env")` or `file_read(path="keys.env")`.
- **Observed Result**: Allowed because `file_read` has `ActionClass.READ_ONLY`.
- **Root Cause**: Policy engine only checked destructive mutations, not sensitive read targets.
- **Affected Source**: `omni_engine/policy/rules.py`, `omni_engine/policy/engine.py`.
- **Planned Fix**: Hard Rule-0 block on reading `.env`, `keys.env`, private keys (`id_rsa`, `*.pem`), credentials files.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-031 — Ordinary Browser Navigation Over-Classified as SYSTEM_ACTION
- **Reproduction**: Navigate to `https://www.python.org`.
- **Observed Result**: Policy risk calculated as `0.90` (`SYSTEM_ACTION`), forcing confirmation prompt.
- **Root Cause**: Coarse capability classification assigned `SYSTEM_ACTION` to all browser operations.
- **Affected Source**: `omni_engine/capabilities/definitions.py`, `omni_engine/policy/engine.py`.
- **Planned Fix**: Classify browser read actions (`navigate`, `snapshot`, `screenshot`, `extract`) as `READ_ONLY` / low-risk `EXTERNAL_NETWORK` (risk <= 0.20). Reserve high risk for interactive mutations (`click`, `type`) and financial gating.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-032 — Browser Navigate + Screenshot Collapsing to Navigate Only
- **Reproduction**: Prompt: `"Navigate to https://www.python.org, inspect the page, and capture a screenshot"`.
- **Observed Result**: Plan contained only 1 step (navigate); screenshot step was omitted.
- **Root Cause**: Template-first planning selected `browse_web` which only navigates.
- **Affected Source**: `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py`.
- **Planned Fix**: Objective decomposer identifies separate screenshot requirement; planner augments plan with `browser_screenshot` step.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-033 — Complex Repository Inspection Collapsing to Directory Tree
- **Reproduction**: Prompt: `"Inspect repository structure, locate Quest persistence, Operation Ledger, and identify crash recovery files"`.
- **Observed Result**: Plan contained only `tool_directory_tree`.
- **Root Cause**: Single candidate selection collapsed multi-part inspection.
- **Affected Source**: `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py`.
- **Planned Fix**: Decompose into structure inspection, search/locate code, and content inspection steps.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-034 — Mixed Web + Repository Objectives Collapsing to Single Domain
- **Reproduction**: Prompt: `"Search web for Python 3.12 lifecycle, inspect repository dependencies, determine compatibility"`.
- **Observed Result**: Router selected either web search or repository inspection, completely ignoring the other domain.
- **Root Cause**: Single domain routing unable to handle multi-domain compound objectives.
- **Affected Source**: `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py`.
- **Planned Fix**: Compound objective decomposition produces multi-domain requirement list; generative planner or composite template composes multi-domain DAG.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-035 — OS + n8n Compound Objectives Dropping Automation Requirements
- **Reproduction**: Prompt: `"Check system health, check n8n port 5678, list n8n workflows, aggregate results"`.
- **Observed Result**: OS diagnostics executed; n8n workflow listing dropped.
- **Root Cause**: Template-first planning terminated on `diagnose_system`.
- **Affected Source**: `omni_engine/planning/decomposer.py`, `omni_engine/planning/engine.py`.
- **Planned Fix**: Requirement coverage check prevents plan finalization until OS and n8n requirements are both covered.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.

### PRACT-036 — Skill Selection Incorrectly Equated with Complete Goal Coverage
- **Reproduction**: Any prompt combining a skill domain with an additional action (e.g. `perform_git_inspection` + `save report`).
- **Observed Result**: Plan only executed skill steps; file save was omitted.
- **Root Cause**: Fundamental architectural gap: treating skill selection as terminal planning rather than a reusable building block.
- **Affected Source**: `omni_engine/contracts/objective.py`, `omni_engine/planning/engine.py`.
- **Planned Fix**: Invariant enforcement: Planner must map skill steps against `ObjectiveSpec.requirements`, identify uncovered requirements, and augment the DAG.
- **Tests Added**: `tests/test_l14_3_practical.py`.
- **Final Status**: RESOLVED.
