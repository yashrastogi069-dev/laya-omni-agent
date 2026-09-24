# ACTIVE_PLAN.md — Checkpoint L9: Deterministic Policy Engine & Persistent User Constraints (ACTIVE)

## 1. Summary of Completed Checkpoint L8 (Typed Argument Resolution & Extraction Engine)
- **Status**: **COMPLETED & VERIFIED**
- **Test Suite**: **26/26 unit tests passed in 0.010s; 207/207 full repository tests passed in 229s (100% pass rate)**.
- **Key Deliverables**:
  1. `omni_engine/contracts/arguments.py`: Strongly typed `ArgumentExtractionSource`, `ArgumentSlot`, and `ArgumentResolutionEnvelope` models.
  2. `omni_engine/arguments/extractors.py`: High-precision deterministic regex and syntactic AST extractors for file paths, URLs, PIDs, process names, app/service names, SQL queries, math expressions, PowerShell commands, and search queries.
  3. `omni_engine/arguments/resolver.py`: Master `ArgumentResolver` validating against `CapabilitySpec.input_schema`, implementing sub-1ms deterministic extraction (~0.118 ms benchmarked), schema defaults, context inheritance with `PARAM_ALIASES`, structured user clarification prompts (`CLARIFICATION_PROMPTS`), and zero-hallucination guarantees.
  4. `omni_engine/arguments/__init__.py`: Clean public interface exports.
  5. `tests/test_l8_arguments.py`: 26 comprehensive unit tests covering all 23 canonical tools and edge cases.
- **Adversarial Diff Review**: **PASS ✅** (Subagent `00527d05-183d-4711-be67-eeb080163dcc`).

---

## 2. Active Checkpoint L9: Deterministic Policy Engine & Persistent User Constraints

### Objective
Enforce the repository Prime Directive ("Deterministic Control, Probabilistic Reasoning") by implementing a high-throughput deterministic policy engine. The policy engine evaluates proposed capability invocations against action classes, autonomy tiers, confirmation policies, persistent user constraints, directory boundaries, and forbidden operations before any execution can take place.

### Architecture & Components

1. **Contracts (`omni_engine/contracts/policy.py`)**:
   - `PolicyEffect` (Enum: `ALLOW`, `REQUIRE_CONFIRMATION`, `DENY`, `QUARANTINE`)
   - `ActionAssessment`: Detailed risk analysis of proposed invocation (`action_class`, `autonomy_required`, `blast_radius`, `is_destructive`, `is_reversible`, `sensitive_targets`, `risk_score`).
   - `PolicyRule`: Declarative persistent rule contract (`rule_id`, `name`, `description`, `effect`, `match_criteria`, `priority`, `is_active`).
   - `PolicyDecision`: Output envelope (`allowed: bool`, `effect: PolicyEffect`, `matched_rules: List[str]`, `confirmation_prompt: Optional[str]`, `denial_reason: Optional[str]`, `latency_ms: float`, `metadata: Dict[str, Any]`).

2. **Persistent User Constraints & Rule Store (`omni_engine/policy/rules.py` & `store.py`)**:
   - Canonical system rules:
     - Forbidden operations (Invariant 3 in `AGENTS.md`): `git reset --hard`, `git clean -fd`, `rmdir /s /q C:\`, system-level drive formatting.
     - Protected path boundaries: Deny destructive or write operations targeting Windows system paths (`C:\Windows`, `System32`, `Program Files`, `.ssh`, `.env`, root drives).
     - Process protection: Deny termination of critical system processes (`csrss.exe`, `lsass.exe`, `smss.exe`, `services.exe`).
   - User-defined constraint persistence (JSON-backed store for custom allowed/denied paths, domains, and commands).

3. **Deterministic Policy Engine (`omni_engine/policy/engine.py`)**:
   - `PolicyEngine`:
     - Method `evaluate(spec: CapabilitySpec, arguments: Dict[str, Any], autonomy_profile: AutonomyProfile = AutonomyProfile.SAFE_ASSISTANT, user_confirmed: bool = False, session_context: Optional[Dict[str, Any]] = None) -> PolicyDecision`.
     - Sub-1ms deterministic evaluation:
       1. Rule-0: Hard Invariants and Forbidden Operations (instant `DENY`).
       2. Protected Resource Boundaries (instant `DENY`).
       3. Autonomy Profile Gating:
          - If `spec.minimum_autonomy_profile > autonomy_profile`:
            - If policy allows confirmation escalation -> `REQUIRE_CONFIRMATION`
            - Else -> `DENY`.
       4. Action Class & Confirmation Policy:
          - If `spec.confirmation_policy == ConfirmationPolicy.ALWAYS` and not `user_confirmed` -> `REQUIRE_CONFIRMATION`.
          - If `spec.confirmation_policy == ConfirmationPolicy.POLICY_CONTROLLED`:
            - If high-risk or destructive and not `user_confirmed` -> `REQUIRE_CONFIRMATION`.
       5. Custom User Constraint Evaluation (matching against pattern, target, domain).
       6. Telemetry & Shadow Mode (`LAYA_V2_MODE=off|shadow|active`).

4. **Integration & Parity**:
   - Seamlessly accepts `CapabilitySpec` and `arguments` from L8's `ArgumentResolutionEnvelope`.
   - Non-switching boundary preserved: `omni_agent.py` and `omni_engine/planner.py` untouched on legacy path.

5. **Test Suite (`tests/test_l9_policy.py`)**:
   - 25+ comprehensive tests covering all action classes, autonomy tiers, confirmation policies, protected paths, forbidden commands, custom constraints, and shadow mode.

---

## 3. Strict Goal Boundaries

- Active Goal Scope: `L7.5 (Complete) → L8 (Complete) → L9 (Active)`
- **HARD STOP AFTER L9**:
  Under NO circumstances implement:
  - SQLite Quest Persistence (L10)
  - Operation Ledger (L11)
  - Structured DAG Planner (L12)
  - Plan DAG Validator (L13)
  - Deterministic DAG Executor (L14)
