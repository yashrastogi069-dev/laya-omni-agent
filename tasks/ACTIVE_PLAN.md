# ACTIVE_PLAN.md — Checkpoint L6B: Final Skill-Aware Hierarchical Router (ACTIVE)

## 1. Summary of Completed Checkpoint L7 (Skills Substrate & Workflow Manifests)
- **Status**: **COMPLETED & VERIFIED**
- **Artifacts Created / Hardened**:
  - `omni_engine/contracts/skill.py`:
    - `SkillStepTemplate`: Declarative workflow step model with `step_id`, `capability_id`, `description`, `depends_on`, `default_args`, `arg_mappings`, `verification_rule`, and `can_fail_silently`.
    - `SkillManifest`: Strongly typed skill contract defining `skill_id`, `version`, `domain`, `name`, `description`, `intent_patterns`, `input_schema`, `output_schema`, `required_capabilities`, `optional_capabilities`, `action_classes`, `workflow_template`, `planning_required`, `verification_strategy`, `applicable_autonomy`, `confirmation_policy`, and `escalation_conditions`.
    - Invariants & Safety Floors:
      - Overlap rejection: Capabilities cannot appear in both `required_capabilities` and `optional_capabilities`.
      - Non-empty template enforcement: If `planning_required=False`, `workflow_template` must not be empty.
      - Step capability membership: All step `capability_id` values must belong to required or optional sets.
      - Phantom dependency rejection: `depends_on` entries must reference valid prior step IDs within the template.
      - Cycle detection: Three-color DFS cycle detector strictly forbids circular dependencies (`s1 -> s2 -> s1`).
      - High-risk confirmation floor: Skills containing high-risk action classes (`LOCAL_DELETE`, `EXTERNAL_DELETE`, `EXTERNAL_SEND`, `SYSTEM_ACTION`, `SECURITY_SENSITIVE`, `FINANCIAL`) cannot declare `confirmation_policy=NEVER`.
  - `omni_engine/skills/registry.py`:
    - `SkillRegistry`: Thread-safe registry (`RLock`) enforcing:
      - Zero dangling capabilities: Every required, optional, and step capability must exist in `CapabilityRegistry`.
      - Action class encompassment: A skill cannot reference a capability whose action class is not declared in `manifest.action_classes` (blocks action-class omission spoofing).
      - High-risk confirmation floor: Registry independently verifies that constituent high-risk capabilities forbid `confirmation_policy=NEVER`.
      - Autonomy profile floor: A skill cannot declare an autonomy tier weaker than the minimum autonomy required by its constituent capabilities.
      - Mutation isolation: Deep copy returns prevent internal registry state corruption.
      - Methods: `register`, `unregister`, `has`, `get`, `list_all`, `list_manifests`, `list_by_domain`, `find_by_intent`, `export_manifests`, `count`.
  - `omni_engine/skills/definitions.py`:
    - 7 canonical skills backed 100% by the 23 verified tools:
      1. `web_research` (web_search, scrape_url, http_api, download_file)
      2. `inspect_repository` (directory_tree, search_code, file_read, git_status)
      3. `diagnose_system` (system_diagnostics, list_processes, ping_test)
      4. `file_transform` (file_read, file_write, run_python)
      5. `analyze_data` (sqlite_exec, inspect_data, safe_math)
      6. `browser_information_task` (visual_browse, browser_screenshot)
      7. `perform_git_inspection` (git_status, search_code, file_read)
    - `build_canonical_skill_registry()` helper for instant canonical instantiation.
  - `omni_engine/skills/__init__.py`: Clean public API export.
  - `tests/test_l7_skills.py`: 26 comprehensive unit and integration tests (contract invariants, cycle detection, phantom dependency rejection, policy floors, spoofing defenses, thread safety, canonical parity, and non-switching boundary).
- **Test Suite Results**:
  - `tests/test_l7_skills.py`: **26/26 passed in 0.025s (100% pass rate)**.
  - Full repository test suite (`python -m unittest discover tests -v`): **149/149 passed in 191.42s (100% pass rate)**.
- **Adversarial Diff Review**: **PASS (All 5 repairs verified: phantom deps, DAG cycle DFS, action-class spoofing gate, canonical parity, thread safety)**.

---

## 2. Checkpoint L6B: Final Skill-Aware Hierarchical Router (ACTIVE)

### 2.1 Objectives & Scope
Now that Checkpoints L3 (Capability Registry), L4 (Providers), L5 (DecisionFabric), L6A (Hierarchical Router Foundation), and L7 (Skills Substrate) are in place, integrate them into the final hierarchical routing pipeline:
`User Request → DecisionFrame → Domain Router → Skill Router → Skill Manifest → Capability Candidate Set → Capability Router`

Key components:
1. **Extend `RouteDecision` Contract** (`omni_engine/contracts/routing.py`):
   - Add `selected_skill: Optional[str] = None`
   - Add `candidate_skills: List[str] = Field(default_factory=list)`
   - Add `skill_workflow_template: Optional[List[Dict[str, Any]]] = None`
   - Add `skill_confirmation_policy: Optional[ConfirmationPolicy] = None`
2. **Upgrade `HierarchicalRouter`** (`omni_engine/routing/router.py`):
   - Accept `skill_registry: Optional[SkillRegistry] = None` (defaults to `build_canonical_skill_registry()`).
   - If `needs_tools=False` and `requires_action=False`, fast-path exits early as conversational (0 skills, 0 capabilities).
   - Domain resolution matches active domains (with fail-open pooling and keyword pinning as in L6A).
   - Skill routing:
     - Queries `skill_registry.list_manifests(domain=domain)` and `skill_registry.find_by_intent(prompt, domain=domain)`.
     - Matches prompt intent against `skill.intent_patterns` and description.
     - If a high-confidence matching skill is identified:
       - Skill required capabilities are automatically guaranteed top priority in candidate set.
       - Optional capabilities are added if candidate budget permits.
       - Attaches `selected_skill`, `candidate_skills`, `skill_workflow_template`, and `skill_confirmation_policy` to `RouteDecision`.
     - If no skill matches with sufficient confidence, router falls back gracefully to raw domain capability routing (fail-open capability routing from L6A).
   - Maintains sub-35ms warm latency budget (<5ms for deterministic paths).
3. **Comprehensive Evaluation Corpus & Test Suite** (`tests/test_l6b_skill_routing.py`):
   - Test 1: Conversational query bypasses both skills and tools.
   - Test 2: Exact skill match (`"research quantum computing papers" -> web_research`).
   - Test 3: System diagnostic skill match (`"diagnose cpu usage and high memory" -> diagnose_system`).
   - Test 4: Repository inspection skill match (`"search the codebase for auth tokens" -> inspect_repository`).
   - Test 5: Fallback to capability routing when prompt does not cleanly match any predefined skill.
   - Test 6: Multi-step cross-domain query retains required capabilities from multiple domains/skills.
   - Test 7: Latency telemetry verifies System 1 performance envelope.
   - Test 8: Non-switching boundary confirms `omni_agent.py` and `omni_engine/planner.py` remain untouched on legacy dispatch.
4. **Hard Stopping Boundary**:
   - STOP BEFORE L8. Do NOT implement Argument Resolver (L8), Policy Engine (L9), Quest runtime (L10), Planner (L12), or DAG Executor (L14).

---

## 3. Acceptance Criteria
- [ ] `RouteDecision` contract updated with optional skill fields (`selected_skill`, `candidate_skills`, `skill_workflow_template`, `skill_confirmation_policy`).
- [ ] `HierarchicalRouter` updated to incorporate `SkillRegistry` with intent pattern matching and capability prioritization.
- [ ] Dedicated test suite `tests/test_l6b_skill_routing.py` implemented and 100% passing.
- [ ] Full repository test suite passes with 0 regressions.
- [ ] Adversarial plan & diff reviews completed and verified.
- [ ] Canonical documentation updated: `tasks/ACTIVE_PLAN.md`, `tasks/MASTER_PLAN.md`, `LAYA_BUILD_STATE.md`, `HANDOFF.md`, and `END_TO_END_EXECUTION_LOG.md`.
- [ ] Git commit and push to `laya-autonomous-v2`.
- [ ] Consolidated Long-Run Goal Report (L3-L7/L6B) delivered.
