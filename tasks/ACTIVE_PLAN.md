# ACTIVE_PLAN.md — Checkpoint L6B: Final Skill-Aware Hierarchical Router (COMPLETED)

## 1. Summary of Completed Checkpoint L6B (Final Skill-Aware Hierarchical Router)
- **Status**: **COMPLETED & VERIFIED**
- **Artifacts Created / Hardened**:
  - `omni_engine/contracts/routing.py`:
    - Strongly typed `RouteDecision` extended with skill awareness:
      - `selected_skill: Optional[str]`: Canonical identifier of primary matching skill, if selected.
      - `candidate_skills: List[str]`: Ranked list of candidate skill IDs evaluated.
      - `skill_workflow_template: Optional[List[SkillStepTemplate]]`: Predefined deterministic DAG step template attached to the selected skill.
      - `skill_confirmation_policy: Optional[ConfirmationPolicy]`: Interactive human confirmation requirement declared by the skill.
    - Model Validators:
      - Enforces that if `selected_skill is None`, `skill_workflow_template` and `skill_confirmation_policy` must strictly be `None`.
      - Enforces that if `selected_skill is not None`, it cannot be empty/whitespace and is guaranteed to be present in `candidate_skills`.
      - Clean relative imports avoiding circular import deadlocks.
  - `omni_engine/routing/router.py`:
    - `HierarchicalRouter`: Upgraded to full multi-tier Skill-Aware Hierarchical Capability Router:
      `Request → DecisionFrame → Domain Routing → Skill Routing → Small Candidate Set → Capability`
    - Injected `skill_registry: Optional[SkillRegistry] = None`, defaulting to `build_canonical_skill_registry(self.registry)`.
    - **Blocking-1 (Dynamic Floor Expansion)**: Mandatory capabilities (`pinned_caps ∪ skill.required_capabilities`) are unconditionally included. If `len(mandatory_caps) > max_candidates`, candidate budget dynamically expands (`effective_max = max(max_candidates, len(mandatory_caps))`) and records `metadata["budget_expanded"] = True`.
    - **Blocking-2 (Cross-Domain Spec Backfill)**: Unconditionally backfills `domain_specs` for all constituent capabilities of the selected skill from `CapabilityRegistry`, preventing tool-dropping across domains.
    - **Blocking-3 (Dual-Threshold Gating & Anti-Locking Defenses)**:
      - Destructive Verb Conflict Gate: Detects destructive verbs (`delete`, `remove`, `kill`, `drop`, `purge`, `terminate`) and zeroes match score for non-destructive skills, preventing dangerous false-positive skill locking.
      - Generic Single Token Gate: Generic tokens (`file`, `run`, `status`, `data`, `system`, `check`, `test`, `web`, `code`, `repo`, `python`) cannot trigger skill selection on their own.
      - Description Score Ceiling: Description token overlaps are capped at 0.50, ensuring only high-confidence intent pattern matches (>=0.75) can trigger skill selection.
      - Morphological Stemmer: Word suffix and root alignment (`_stem_token`) aligns verb inflections without external dependencies.
    - **Unified Deduplication & Multi-Rationale Merging**: If a capability is both pinned and skill-required, score is pinned at 1.0 with composite rationale `"explicit_keyword_pinned+skill_required"`.
    - **Budget-Conscious Optional Capability Ingestion**: Optional tools receive score 0.75 with rationale `"skill_optional"` and do not cause budget expansion.
    - **Fast-Paths & Latency SLA**: Empty prompts and conversational non-tool queries return in <5ms. Warm neural routing executes in <35ms.
  - `tests/test_l6b_skill_routing.py`:
    - 16 comprehensive unit and integration tests covering:
      1. `test_route_decision_contract_skill_fields_and_validation`
      2. `test_fastpath_empty_and_conversational`
      3. `test_canonical_skill_matching_web_research`
      4. `test_canonical_skill_matching_diagnose_system`
      5. `test_canonical_skill_matching_inspect_repository`
      6. `test_canonical_skill_matching_analyze_data`
      7. `test_canonical_skill_matching_browser_task`
      8. `test_canonical_skill_matching_git_inspection`
      9. `test_blocking_1_dynamic_floor_expansion`
      10. `test_blocking_2_cross_domain_spec_backfill`
      11. `test_blocking_3_destructive_verb_prevents_false_positive_lock`
      12. `test_blocking_3_generic_single_token_prevents_skill_lock`
      13. `test_deduplication_and_multi_rationale_merging`
      14. `test_optional_capabilities_ingestion_and_scoring`
      15. `test_legacy_non_switching_boundary`
      16. `test_live_modernbert_skill_routing`
- **Test Suite Results**:
  - `tests/test_l6b_skill_routing.py`: **16/16 passed in 83.82s (100% pass rate)**.
  - Full repository test suite (`python -m unittest discover tests -v`): **165/165 passed in 148.33s (100% pass rate)**.
- **Adversarial Diff Review**: **PASS ✅ (All 5 blocking recommendations verified, zero regressions, strict non-switching boundary)**.

---

## 2. Long-Horizon Engineering Goal (L3 – L7/L6B) Status: COMPLETE

With Checkpoints L3, L4, L5, L6A, L7, and L6B implemented, verified, and passing 100% across 165 tests, the capability substrate, provider foundations, System 1 decision fabric, skills layer, and hierarchical router are fully realized.

### Hard Stopping Boundary:
**STOP BEFORE L8**.
Do **NOT** implement:
- Argument Resolver (L8)
- Policy Engine & Autonomy Profiles (L9)
- Persisted SQLite Quest Engine (L10)
- Operation Ledger & Idempotency (L11)
- Structured DAG Planner (L12)
- Plan Validator (L13)
- Deterministic DAG Executor (L14)
The current goal is complete. Next actions will be determined by the user.
