"""
tests.test_l7_skills
====================
Comprehensive test suite for Checkpoint L7: Skills Substrate & Workflow Manifests.

Verifies:
1. SkillStepTemplate and SkillManifest contract schema validation and invariants.
2. SkillRegistry capability parity validation (zero dangling capabilities).
3. Autonomy policy floor enforcement (skill autonomy >= constituent capability autonomy).
4. Workflow template DAG integrity and duplicate step ID rejection.
5. High-risk confirmation policy enforcement (cannot be NEVER).
6. Canonical skill registry parity across all 7 evidence-driven skills.
7. Intent-based skill search and ranking.
8. Legacy prototype non-switching boundary preservation.
"""

import unittest
from unittest.mock import MagicMock
from pydantic import ValidationError

from omni_engine.capabilities.definitions import build_canonical_registry
from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, ConfirmationPolicy
from omni_engine.contracts.skill import SkillManifest, SkillStepTemplate
from omni_engine.skills.definitions import CANONICAL_SKILLS, build_canonical_skill_registry
from omni_engine.skills.registry import SkillRegistry


class TestSkillContracts(unittest.TestCase):
    """Test suite validating SkillStepTemplate and SkillManifest data contracts."""

    def test_step_template_valid_and_non_blank(self) -> None:
        """Valid step template instantiates and validates required non-blank fields."""
        step = SkillStepTemplate(
            step_id="step_1",
            capability_id="web_search",
            description="Perform web search",
            depends_on=[],
            arg_mappings={"query": "$inputs.query"},
        )
        self.assertEqual(step.step_id, "step_1")
        self.assertEqual(step.capability_id, "web_search")

        # Blank step_id or capability_id rejected
        with self.assertRaises(ValidationError):
            SkillStepTemplate(step_id="", capability_id="web_search", description="desc")
        with self.assertRaises(ValidationError):
            SkillStepTemplate(step_id="step_1", capability_id="   ", description="desc")

    def test_manifest_forbids_extra_fields(self) -> None:
        """SkillManifest enforces extra='forbid'."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(step_id="s1", capability_id="web_search", description="desc")
                ],
                planning_required=False,
                applicable_autonomy=AutonomyProfile.SAFE_ASSISTANT,
                bogus_extra_field="illegal", # type: ignore
            )

    def test_manifest_rejects_invalid_domain(self) -> None:
        """SkillManifest rejects domain outside valid canonical set."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="invalid_domain",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                planning_required=True,
            )

    def test_manifest_rejects_empty_required_capabilities(self) -> None:
        """SkillManifest rejects empty required_capabilities."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=[], # Illegal
                action_classes=[ActionClass.READ_ONLY],
                planning_required=True,
            )

    def test_manifest_rejects_duplicate_required_capabilities(self) -> None:
        """SkillManifest rejects duplicates within required_capabilities."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search", "web_search"], # Duplicate
                action_classes=[ActionClass.READ_ONLY],
                planning_required=True,
            )

    def test_manifest_rejects_overlap_between_required_and_optional(self) -> None:
        """Capabilities cannot be both required and optional."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                optional_capabilities=["web_search"], # Overlap
                action_classes=[ActionClass.READ_ONLY],
                planning_required=True,
            )

    def test_manifest_cross_validates_planning_required_and_template(self) -> None:
        """Skills with planning_required=False MUST provide a non-empty workflow_template."""
        # 1. planning_required=False with None workflow_template -> FAILS
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=None,
                planning_required=False,
            )

        # 2. planning_required=False with empty list -> FAILS
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[],
                planning_required=False,
            )

        # 3. planning_required=True with empty list -> OK
        manifest = SkillManifest(
            skill_id="test_skill",
            domain="web",
            name="Test",
            description="Test skill",
            intent_patterns=["test"],
            required_capabilities=["web_search"],
            action_classes=[ActionClass.READ_ONLY],
            workflow_template=None,
            planning_required=True,
        )
        self.assertTrue(manifest.planning_required)

    def test_manifest_workflow_template_step_validation(self) -> None:
        """Workflow template rejects duplicate step IDs, undeclared capabilities, and self-dependencies."""
        # Duplicate step_id
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(step_id="dup_step", capability_id="web_search", description="d1"),
                    SkillStepTemplate(step_id="dup_step", capability_id="web_search", description="d2"),
                ],
                planning_required=False,
            )

        # Undeclared capability in step
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(step_id="s1", capability_id="undeclared_cap", description="d1"),
                ],
                planning_required=False,
            )

        # Self-dependency
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(
                        step_id="s1",
                        capability_id="web_search",
                        description="d1",
                        depends_on=["s1"], # Self-dependency
                    ),
                ],
                planning_required=False,
            )

        # Phantom / undeclared dependency (Defect 1)
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(
                        step_id="s1",
                        capability_id="web_search",
                        description="d1",
                        depends_on=["phantom_step_xyz"], # Undeclared dependency
                    ),
                ],
                planning_required=False,
            )

        # Circular dependency cycle (Defect 2)
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="test_skill",
                domain="web",
                name="Test",
                description="Test skill",
                intent_patterns=["test"],
                required_capabilities=["web_search"],
                action_classes=[ActionClass.READ_ONLY],
                workflow_template=[
                    SkillStepTemplate(step_id="s1", capability_id="web_search", description="d1", depends_on=["s2"]),
                    SkillStepTemplate(step_id="s2", capability_id="web_search", description="d2", depends_on=["s1"]),
                ],
                planning_required=False,
            )

    def test_manifest_rejects_never_confirmation_on_high_risk_actions(self) -> None:
        """High-risk action classes cannot declare confirmation_policy=NEVER."""
        with self.assertRaises(ValidationError):
            SkillManifest(
                skill_id="high_risk_skill",
                domain="os",
                name="Kill Processes Skill",
                description="Kill system processes",
                intent_patterns=["kill process"],
                required_capabilities=["kill_process"],
                action_classes=[ActionClass.SYSTEM_ACTION],
                workflow_template=[
                    SkillStepTemplate(step_id="s1", capability_id="kill_process", description="kill"),
                ],
                planning_required=False,
                confirmation_policy=ConfirmationPolicy.NEVER, # ILLEGAL on SYSTEM_ACTION
            )

    def test_manifest_json_serialization_roundtrip(self) -> None:
        """SkillManifest cleanly serializes to dict and reconstructs identically."""
        canonical_web = CANONICAL_SKILLS["web_research"]
        dumped = canonical_web.model_dump()
        reconstructed = SkillManifest.model_validate(dumped)
        self.assertEqual(canonical_web.skill_id, reconstructed.skill_id)
        self.assertEqual(len(canonical_web.workflow_template or []), len(reconstructed.workflow_template or []))


class TestSkillRegistry(unittest.TestCase):
    """Test suite validating SkillRegistry operations and integrity enforcement."""

    def setUp(self) -> None:
        self.cap_registry = build_canonical_registry()
        self.registry = SkillRegistry(capability_registry=self.cap_registry)

    def test_register_and_retrieve_skill(self) -> None:
        """Registering a canonical skill allows clean retrieval by ID."""
        manifest = CANONICAL_SKILLS["web_research"]
        self.registry.register(manifest)

        self.assertTrue(self.registry.has("web_research"))
        retrieved = self.registry.get("web_research")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.skill_id, "web_research")
        self.assertEqual(self.registry.count(), 1)
        self.assertEqual(self.registry.list_all(), ["web_research"])

    def test_duplicate_registration_rejected(self) -> None:
        """Registering duplicate skill_id raises ValueError."""
        manifest = CANONICAL_SKILLS["web_research"]
        self.registry.register(manifest)

        with self.assertRaises(ValueError):
            self.registry.register(manifest)

    def test_dangling_required_capability_rejected(self) -> None:
        """Registering a skill requiring a non-existent capability raises ValueError."""
        dangling_manifest = SkillManifest(
            skill_id="dangling_skill",
            domain="web",
            name="Dangling Skill",
            description="Requires imaginary tool",
            intent_patterns=["imaginary"],
            required_capabilities=["non_existent_capability_xyz"],
            action_classes=[ActionClass.READ_ONLY],
            planning_required=True,
        )

        with self.assertRaises(ValueError) as cm:
            self.registry.register(dangling_manifest)
        self.assertIn("non_existent_capability_xyz", str(cm.exception))

    def test_dangling_optional_capability_rejected(self) -> None:
        """Registering a skill referencing non-existent optional capability raises ValueError."""
        dangling_manifest = SkillManifest(
            skill_id="dangling_skill",
            domain="web",
            name="Dangling Skill",
            description="Optional imaginary tool",
            intent_patterns=["imaginary"],
            required_capabilities=["web_search"],
            optional_capabilities=["non_existent_optional_xyz"],
            action_classes=[ActionClass.READ_ONLY],
            planning_required=True,
        )

        with self.assertRaises(ValueError) as cm:
            self.registry.register(dangling_manifest)
        self.assertIn("non_existent_optional_xyz", str(cm.exception))

    def test_weaker_autonomy_profile_rejected_by_policy_floor(self) -> None:
        """A skill cannot declare an autonomy profile weaker than its required tools."""
        # file_write requires AutonomyProfile.LOCAL_OPERATOR (rank 3)
        # Declaring AutonomyProfile.ADVISOR (rank 1) must be rejected
        weak_manifest = SkillManifest(
            skill_id="weak_autonomy_skill",
            domain="dev",
            name="Weak Skill",
            description="Writes file but claims advisor",
            intent_patterns=["write file"],
            required_capabilities=["file_write"],
            action_classes=[ActionClass.LOCAL_CREATE],
            workflow_template=[
                SkillStepTemplate(step_id="s1", capability_id="file_write", description="write"),
            ],
            planning_required=False,
            applicable_autonomy=AutonomyProfile.ADVISOR, # WEAKER than LOCAL_OPERATOR
            confirmation_policy=ConfirmationPolicy.ALWAYS,
        )

        with self.assertRaises(ValueError) as cm:
            self.registry.register(weak_manifest)
        self.assertIn("weaker than required capability", str(cm.exception))

    def test_registry_rejects_missing_constituent_action_class(self) -> None:
        """Registering a skill missing an action class of a constituent capability raises ValueError."""
        missing_ac_manifest = SkillManifest(
            skill_id="missing_ac_skill",
            domain="dev",
            name="Missing Action Class Skill",
            description="Uses file_write but only declares READ_ONLY",
            intent_patterns=["write file"],
            required_capabilities=["file_write"], # LOCAL_CREATE
            action_classes=[ActionClass.READ_ONLY], # Missing LOCAL_CREATE!
            workflow_template=[
                SkillStepTemplate(step_id="s1", capability_id="file_write", description="write"),
            ],
            planning_required=False,
            applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
            confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        )

        with self.assertRaises(ValueError) as cm:
            self.registry.register(missing_ac_manifest)
        self.assertIn("missing from the skill's declared action_classes", str(cm.exception))

    def test_registry_rejects_action_class_spoofing_confirmation_bypass(self) -> None:
        """Registering a high-risk tool with confirmation=NEVER via action class spoofing is rejected."""
        # 1. Pydantic validator blocks setting confirmation_policy=NEVER when high-risk action class is declared
        manifest_with_high_risk = SkillManifest(
            skill_id="spoofed_skill_1",
            domain="os",
            name="Spoofed Kill Process 1",
            description="Kills process",
            intent_patterns=["kill"],
            required_capabilities=["kill_process"],
            action_classes=[ActionClass.READ_ONLY, ActionClass.SYSTEM_ACTION],
            workflow_template=[
                SkillStepTemplate(step_id="s1", capability_id="kill_process", description="kill"),
            ],
            planning_required=False,
            applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
            confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        )
        with self.assertRaises(ValidationError):
            manifest_with_high_risk.confirmation_policy = ConfirmationPolicy.NEVER

        # 2. If action_classes omits SYSTEM_ACTION to spoof/bypass Pydantic, SkillRegistry catches the missing action class
        spoofed_manifest = SkillManifest(
            skill_id="spoofed_skill_2",
            domain="os",
            name="Spoofed Kill Process 2",
            description="Kills process spoofing read-only",
            intent_patterns=["kill"],
            required_capabilities=["kill_process"],
            action_classes=[ActionClass.READ_ONLY],  # Spoofed!
            workflow_template=[
                SkillStepTemplate(step_id="s1", capability_id="kill_process", description="kill"),
            ],
            planning_required=False,
            applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
            confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        )
        with self.assertRaises(ValueError) as cm:
            self.registry.register(spoofed_manifest)
        self.assertIn("missing from the skill's declared action_classes", str(cm.exception))

    def test_unregister_skill(self) -> None:
        """unregister() removes skill and returns correct boolean."""
        self.registry.register(CANONICAL_SKILLS["web_research"])
        self.assertTrue(self.registry.has("web_research"))

        self.assertTrue(self.registry.unregister("web_research"))
        self.assertFalse(self.registry.has("web_research"))
        self.assertFalse(self.registry.unregister("web_research"))

    def test_mutation_isolation(self) -> None:
        """Mutating a retrieved manifest does not modify internal registry state."""
        self.registry.register(CANONICAL_SKILLS["web_research"])
        retrieved = self.registry.get("web_research")
        retrieved.name = "Mutated Name"

        fresh = self.registry.get("web_research")
        self.assertNotEqual(fresh.name, "Mutated Name")
        self.assertEqual(fresh.name, CANONICAL_SKILLS["web_research"].name)

    def test_list_by_domain(self) -> None:
        """list_by_domain() filters skills correctly."""
        for skill in CANONICAL_SKILLS.values():
            self.registry.register(skill)

        dev_skills = self.registry.list_by_domain("dev")
        dev_ids = [s.skill_id for s in dev_skills]
        self.assertIn("inspect_repository", dev_ids)
        self.assertIn("file_transform", dev_ids)
        self.assertIn("perform_git_inspection", dev_ids)
        self.assertNotIn("web_research", dev_ids)

    def test_find_by_intent(self) -> None:
        """find_by_intent() finds relevant skills based on intent patterns."""
        for skill in CANONICAL_SKILLS.values():
            self.registry.register(skill)

        # 1. Web research query
        matches = self.registry.find_by_intent("I want to do web research on quantum computing")
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0][1].skill_id, "web_research")

        # 2. Git query
        git_matches = self.registry.find_by_intent("check git status and active branch")
        self.assertGreater(len(git_matches), 0)
        self.assertEqual(git_matches[0][1].skill_id, "perform_git_inspection")

        # 3. System diagnosis query
        sys_matches = self.registry.find_by_intent("diagnose system health and memory usage")
        self.assertGreater(len(sys_matches), 0)
        self.assertEqual(sys_matches[0][1].skill_id, "diagnose_system")

        # 4. Empty query returns empty list
        self.assertEqual(self.registry.find_by_intent(""), [])

    def test_export_manifests(self) -> None:
        """export_manifests() exports JSON-serializable dictionaries."""
        self.registry.register(CANONICAL_SKILLS["web_research"])
        exported = self.registry.export_manifests()
        self.assertEqual(len(exported), 1)
        self.assertEqual(exported[0]["skill_id"], "web_research")
        self.assertEqual(exported[0]["domain"], "web")


class TestCanonicalSkillsParity(unittest.TestCase):
    """Test suite verifying all 7 canonical skills register with 100% capability parity."""

    def test_build_canonical_skill_registry_succeeds(self) -> None:
        """build_canonical_skill_registry() builds registry with 7 skills and 0 dangling tools."""
        cap_reg = build_canonical_registry()
        skill_reg = build_canonical_skill_registry(capability_registry=cap_reg)

        self.assertEqual(skill_reg.count(), 7)
        expected_skills = {
            "web_research",
            "inspect_repository",
            "diagnose_system",
            "file_transform",
            "analyze_data",
            "browser_information_task",
            "perform_git_inspection",
        }
        self.assertEqual(set(skill_reg.list_all()), expected_skills)

    def test_all_canonical_skills_have_valid_capabilities(self) -> None:
        """Every capability referenced across all 7 canonical skills exists in CapabilityRegistry."""
        cap_reg = build_canonical_registry()
        for skill_id, manifest in CANONICAL_SKILLS.items():
            with self.subTest(skill=skill_id):
                for req_cap in manifest.required_capabilities:
                    self.assertTrue(
                        cap_reg.has(req_cap),
                        f"Skill '{skill_id}' requires missing capability '{req_cap}'",
                    )
                for opt_cap in manifest.optional_capabilities:
                    self.assertTrue(
                        cap_reg.has(opt_cap),
                        f"Skill '{skill_id}' references missing optional capability '{opt_cap}'",
                    )

    def test_all_canonical_skills_encompass_constituent_action_classes(self) -> None:
        """Every canonical skill strictly declares the action classes of its constituent tools."""
        cap_reg = build_canonical_registry()
        for skill_id, manifest in CANONICAL_SKILLS.items():
            with self.subTest(skill=skill_id):
                all_caps = set(manifest.required_capabilities) | set(manifest.optional_capabilities)
                for cap_id in all_caps:
                    spec = cap_reg.get_spec(cap_id)
                    self.assertIsNotNone(spec)
                    self.assertIn(
                        spec.action_class,
                        manifest.action_classes,
                        f"Skill '{skill_id}' is missing action class '{spec.action_class.value}' "
                        f"required by constituent tool '{cap_id}'.",
                    )


class TestLegacyNonSwitchingBoundary(unittest.TestCase):
    """Confirms omni_engine.planner and omni_engine.system1 preserve their legacy dispatch."""

    def test_legacy_dispatch_unaffected(self) -> None:
        from omni_engine.planner import AutonomousPlanner
        from omni_engine.system1 import System1Router

        s1 = System1Router()
        self.assertTrue(hasattr(s1, "route_tool"))
        planner = AutonomousPlanner(
            sys1_engine=s1,
            sys2_engine=MagicMock(),
            memory_engine=MagicMock(),
        )
        self.assertIsNotNone(planner.sys1)


if __name__ == "__main__":
    unittest.main()
