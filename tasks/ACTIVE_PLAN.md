# ACTIVE_PLAN.md — Checkpoint L7: Skills Substrate & Workflow Manifests (ACTIVE)

## 1. Summary of Completed Checkpoint L6A (Hierarchical Routing Foundation)
- **Status**: **COMPLETED & VERIFIED**
- **Artifacts Created / Hardened**:
  - `omni_engine/contracts/routing.py`:
    - `CapabilityCandidate`: Strongly typed individual candidate model with `capability_id`, `domain`, `score` (bounded in [0.0, 1.0]), `rationale`, and `spec_summary`.
    - `RouteDecision`: Complete hierarchical routing decision envelope containing `selected_domain`, `candidate_domains`, ranked `candidates`, `is_fail_open`, `fallback_reason`, `catalog_reduction_ratio`, `total_registry_capabilities`, `latency_ms`, and `metadata`.
    - Strict validators: duplicate candidate rejection, fail-open reason consistency, candidate count <= total registry capabilities, finite bounded reduction ratio.
  - `omni_engine/contracts/__init__.py`: Exported `CapabilityCandidate` and `RouteDecision`.
  - `omni_engine/routing/router.py`:
    - `HierarchicalRouter`: Implements multi-tier catalog reduction pipeline (`Request → DecisionFrame → Domain Routing → Candidate Pruning → RouteDecision`).
    - Conversational Fast-Path: Deterministically bypasses tool scoring for empty/whitespace prompts (<5ms) and informational non-tool queries (`reduction_ratio=1.0`).
    - Automatic Cross-Domain Pooling (Rec-1): Always pools at least top-2 domains for multi-step tasks (`needs_plan=True` or `task_class in ["multi_step_quest", "code_refactor"]`).
    - Ambiguity & Low-Confidence Fail-Open (Rec-3): Pools adjacent domains when domain confidence <0.55 or ambiguity >0.65.
    - Explicit Keyword Capability Pinning (Rec-5): Declarative `CAPABILITY_PIN_MAP` regex scanning unconditionally pins named tools at score=1.0 with rationale `"explicit_keyword_pinned"`.
    - "General" Domain Technical Promotion (Rec-6): Promotes technical domains when `"general"` co-occurs with `needs_tools=True`.
    - Elimination of Sequential Latency Cliff (Rec-2): Zero-inference short circuit for single domains (count <= max_candidates) in <0.2ms; fast deterministic lexical token overlap scoring when pruning large sets in <1ms.
    - Elimination of Legacy Truncation Defect (ISSUE-02): Proved tools 13–23 (previously dropped by legacy `[:12]` slicing like `sqlite_exec`, `inspect_data`, `safe_math`, `powershell`, `ping_test`) are reliably accessible.
  - `omni_engine/routing/__init__.py`: Exported `DOMAIN_KEYWORD_MAP`, `CAPABILITY_PIN_MAP`, and `HierarchicalRouter`.
  - `omni_engine/decision/fabric.py`: Fixed ambiguity escalation condition to evaluate ambiguity probability/value rather than raw confidence.
  - `tests/test_l6a_routing.py`: 12 comprehensive unit and integration tests covering contract validation, empty prompts, conversational gating, single-domain filtering, bound pruning, cross-domain retention, fail-open pooling, keyword pinning, general domain promotion, legacy truncation elimination, non-switching boundary, and live ModernBERT neural routing.
- **Test Suite Results**:
  - `tests/test_l6a_routing.py`: **12/12 passed (100% pass rate)**.
  - Full repository test suite (`python -m unittest discover tests -v`): **123/123 passed in 244.52s (100% pass rate)**.
- **Adversarial Diff Review**: **PASS (All invariants and 6 recommendations verified)**.

---

## 2. Checkpoint L7: Skills Substrate & Workflow Manifests (ACTIVE)

### 2.1 Objectives & Scope
Create a first-class Skill system above raw capabilities:
A Skill is NOT simply a prompt. It is a structured, reusable workflow abstraction mapping common user objectives to constrained capability sets, workflow templates, and safety requirements:
1. `SkillManifest` Data Contract (`omni_engine/contracts/skill.py`):
   - `skill_id: str`: Unique canonical identifier (e.g. `web_research`, `codebase_audit`, `diagnose_system`).
   - `version: str`: Semantic version string (e.g. `1.0.0`).
   - `domain: str`: Primary capability domain (e.g. `web`, `dev`, `os`, `data`).
   - `description: str`: Human- and System-1-readable description of the skill's purpose.
   - `intent_patterns: List[str]`: Exemplar queries and trigger phrases for System 1 classification.
   - `input_requirements: Dict[str, Any]`: JSON-schema or argument requirements.
   - `required_capabilities: List[str]`: Canonical capability IDs strictly required for execution.
   - `optional_capabilities: List[str]`: Supporting capability IDs that may enhance execution.
   - `action_classes: List[ActionClass]`: Maximum risk and action types encompassed by the skill.
   - `workflow_template: Optional[List[Dict[str, Any]]]`: Deterministic sequence of steps if predefined.
   - `planning_required: bool`: Whether novel generative DAG planning is required for variations.
   - `verification_strategy: str`: Method for validating physical completion receipts.
   - `applicable_autonomy: AutonomyProfile`: Minimum autonomy profile required to execute.
   - `escalation_conditions: List[str]`: Explicit triggers mandating escalation to human or supervisor.
2. `SkillRegistry` Substrate (`omni_engine/skills/registry.py`):
   - Thread-safe registry for loading, querying, validating, and retrieving `SkillManifest` instances.
   - Validates that all `required_capabilities` exist in `CapabilityRegistry` (zero dangling capabilities).
3. Initial Canonical Skills (`omni_engine/skills/definitions.py`):
   - Evidence-driven, backed 100% by the 23 existing tools:
     - `web_research` (requires `web_search`, `scrape_url`, optional `http_api`, `download_file`)
     - `codebase_audit` (requires `directory_tree`, `search_code`, `file_read`, optional `git_status`)
     - `diagnose_system` (requires `system_diagnostics`, `list_processes`, optional `ping_test`)
     - `file_transform` (requires `file_read`, `file_write`, optional `run_python`)
     - `database_query` (requires `sqlite_exec`, optional `inspect_data`)
     - `network_probe` (requires `ping_test`, optional `http_api`)
4. Non-Switching Principle:
   - Preserves existing `omni_agent.py` and `omni_engine/planner.py` on the legacy dispatch path.
   - Dedicated unit tests in `tests/test_l7_skills.py`.

---

## 3. Targeted Test Suite (`tests/test_l7_skills.py`)
1. `TestSkillManifestValidation`: Asserts strict schema, type checking, duplicate detection, and extra="forbid".
2. `TestSkillRegistryParity`: Asserts all canonical skills register cleanly and verify that required capabilities exist in `CapabilityRegistry`.
3. `TestSkillLookupByDomain`: Asserts filtering skills by domain.
4. `TestDanglingCapabilityRejection`: Asserts registering a skill with a non-existent capability ID raises `ValueError`.
5. `TestSkillWorkflowTemplates`: Asserts deterministic workflow step structures validate schema contracts.
6. `TestSkillRegistryExport`: Asserts export to JSON-compatible dictionaries round-trips cleanly.

---

## 4. Acceptance Criteria
- [ ] `SkillManifest` contract implemented in `omni_engine/contracts/skill.py`.
- [ ] `SkillRegistry` implemented in `omni_engine/skills/registry.py`.
- [ ] Initial canonical skills defined in `omni_engine/skills/definitions.py`.
- [ ] Zero dangling capabilities: all required capabilities verified against `CapabilityRegistry`.
- [ ] Comprehensive unit test suite `tests/test_l7_skills.py` passes (100% pass rate).
- [ ] Full regression test suite passes (>= 123 tests).
- [ ] Adversarial diff review passes.
