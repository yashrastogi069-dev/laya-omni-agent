# ACTIVE_PLAN.md — Checkpoint L8: Typed Argument Resolution & Extraction Engine (ACTIVE)

## 1. Summary of Completed Checkpoint L7.5 (System One Truth, Calibration & Upstream Alignment)
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **181/181 passed in 48.60s (100% pass rate)**.
- **Key Deliverables**:
  1. `omni_engine/contracts/calibration.py`: `CalibratedModelThresholds`, `DeterministicPolicyThresholds`, and `CalibrationConfig`.
  2. `omni_engine/skills/registry.py`: Autonomy profile floor validator inspects `required_capabilities | optional_capabilities | step_capabilities`, preventing autonomy bypass via optional tools.
  3. `omni_engine/providers/system1.py`: Upstream alignment with `max_loaded=1`, pre-eviction unload/gc, process-wide thread lock (`_ROUTER_LOCK`), single-model preload guard (`names=[model_name]`), and configurable model routing (`english`, `multilingual`, `typed-decisions`).
  4. `omni_engine/decision/eval_corpus.py`: 103 reviewable ground-truth labeled evaluation cases across 6 domains, prompt injection, and automation workflows.
  5. `omni_engine/decision/benchmark.py`: Hardware-aware benchmark harness with batch scaling and adaptive triage telemetry.
  6. `omni_engine/decision/fabric.py`: Integrated calibrated thresholds and `evaluate_adaptive()` 4-question fast triage for conversational queries saving ~11.8s CPU latency.
  7. `omni_engine/routing/router.py`: Integrated calibrated scoring thresholds and shadow semantic skill routing telemetry.
  8. `tests/test_l7_5_calibration.py`: 16 unit tests covering all calibration requirements.
- **Adversarial Diff Review**: **PASS ✅** (Subagent `85316cc5-c0b3-4cca-a911-a0cda52da3c4`).

---

## 2. Active Checkpoint L8: Typed Argument Resolution & Extraction Engine

### Objective
Transform candidate capabilities selected by `HierarchicalRouter` into strongly-typed, schema-conforming `CapabilityInvocation` payloads. Deterministic extraction solves routine cases in <1ms; bounded generative synthesis resolves complex phrasing; missing arguments generate structured clarifications without hallucinatory defaults.

### Architecture & Components
1. **Contracts (`omni_engine/contracts/arguments.py`)**:
   - `ArgumentExtractionSource` (Enum: `DETERMINISTIC_EXTRACTOR`, `SYNTACTIC_AST`, `GENERATIVE_SYNTHESIS`, `SCHEMA_DEFAULT`)
   - `ArgumentSlot`: Represents a single argument slot with `name`, `value`, `is_resolved`, `source`, `confidence`, and `error`.
   - `ArgumentResolutionEnvelope`: Encapsulates resolution outcome:
     - `capability_id: str`
     - `arguments: Dict[str, Any]`
     - `resolved_slots: Dict[str, ArgumentSlot]`
     - `is_valid: bool`
     - `validation_errors: List[str]`
     - `clarification_needed: bool`
     - `clarification_prompt: Optional[str]`
     - `latency_ms: float`
     - `metadata: Dict[str, Any]`

2. **Deterministic Extractors (`omni_engine/arguments/extractors.py`)**:
   - High-precision regex and AST extractors matching all 23 canonical capabilities:
     - `extract_file_paths(text)`: Quoted paths, Windows paths (`C:\...`, `.\...`, `*.ext`), POSIX paths.
     - `extract_urls(text)`: HTTP/HTTPS URLs, domains, ports (e.g. `:5678`).
     - `extract_pids(text)`: Numeric process IDs with prefix matching (`pid 1234`, `process 456`).
     - `extract_process_names(text)`: Application names, `.exe` processes, script runtimes (`node`, `python`, `n8n`, `chrome`).
     - `extract_sql(text)`: SQL statements (`SELECT`, `INSERT`, `UPDATE`, `CREATE TABLE`).
     - `extract_math_expression(text)`: Mathematical equations and arithmetic expressions.
     - `extract_powershell_script(text)`: Command strings, shell one-liners.
     - `extract_search_query(text)`: Natural language queries for code search and web search.

3. **Argument Resolver (`omni_engine/arguments/resolver.py`)**:
   - `ArgumentResolver`:
     - Validates extracted arguments against `CapabilitySpec.input_schema`.
     - Fast deterministic path: When regex/AST extraction satisfies all required fields of `CapabilitySpec.input_schema`, returns valid envelope in <1ms.
     - Ambiguity & Missing Slot Detection: When required parameters are missing (e.g. user said "delete file" or "kill process" without specifying path or PID), sets `clarification_needed = True` with a clean clarification prompt.
     - Generative Fallback: When deterministic extraction is incomplete and an optional `GenerativeProvider` is available, requests structured JSON matching the schema.

4. **Integration & Parity**:
   - Mapped 1:1 against all 23 canonical tool input schemas.
   - Non-switching boundary preserved: `omni_agent.py` and `omni_engine/planner.py` untouched.

5. **Test Suite (`tests/test_l8_arguments.py`)**:
   - 25+ comprehensive unit tests covering all 23 tools, slot extraction, schema validation, and clarification generation.

---

## 3. Strict Goal Boundaries

- Active Goal Scope: `L7.5 (Complete) → L8 (Active) → L9 (Next)`
- **HARD STOP AFTER L9**:
  Do **NOT** implement:
  - SQLite Quest Persistence (L10)
  - Operation Ledger (L11)
  - Structured DAG Planner (L12)
  - Plan DAG Validator (L13)
  - Deterministic DAG Executor (L14)
