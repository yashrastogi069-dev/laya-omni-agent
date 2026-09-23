"""
omni_engine.skills.definitions
==============================
Canonical Skill definitions and registry builder for the standalone LAYA Omni Agent.

Defines 7 evidence-driven, reusable skills backed 100% by the 23 verified capabilities:
1. web_research (web)
2. inspect_repository (dev)
3. diagnose_system (os)
4. file_transform (dev)
5. analyze_data (data)
6. browser_information_task (browser)
7. perform_git_inspection (dev)
"""

from typing import Dict, Optional

from omni_engine.capabilities.registry import CapabilityRegistry
from omni_engine.contracts.enums import ActionClass, AutonomyProfile, ConfirmationPolicy
from omni_engine.contracts.skill import SkillManifest, SkillStepTemplate
from .registry import SkillRegistry


CANONICAL_SKILLS: Dict[str, SkillManifest] = {
    # -----------------------------------------------------------------------
    # 1. Web Domain: web_research
    # -----------------------------------------------------------------------
    "web_research": SkillManifest(
        skill_id="web_research",
        version="1.0.0",
        domain="web",
        name="Web Research & Online Intelligence",
        description="Conduct live internet search, scrape page contents, and gather intelligence from online sources.",
        intent_patterns=[
            "web research",
            "research topic online",
            "search the internet for",
            "gather web intelligence",
            "find documentation online",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Research topic or query"},
            },
            "required": ["query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Synthesized research findings"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
        },
        required_capabilities=["web_search", "scrape_url"],
        optional_capabilities=[],
        action_classes=[ActionClass.READ_ONLY],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_search",
                capability_id="web_search",
                description="Search the web for target keywords",
                arg_mappings={"query": "$inputs.query"},
            ),
            SkillStepTemplate(
                step_id="step_2_scrape",
                capability_id="scrape_url",
                description="Scrape content from relevant page",
                depends_on=["step_1_search"],
                arg_mappings={"url": "$steps.step_1_search.top_url"},
            ),
        ],
        planning_required=False,
        verification_strategy="deterministic_receipt",
        applicable_autonomy=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.NEVER,
        escalation_conditions=["network_failure", "anti_bot_captcha_detected"],
    ),

    # -----------------------------------------------------------------------
    # 2. Dev Domain: inspect_repository
    # -----------------------------------------------------------------------
    "inspect_repository": SkillManifest(
        skill_id="inspect_repository",
        version="1.0.0",
        domain="dev",
        name="Inspect Repository & Codebase",
        description="Inspect directory structure, search codebase for symbols or patterns, and read source files.",
        intent_patterns=[
            "inspect codebase",
            "find function in codebase",
            "repository directory tree",
            "codebase structure",
            "search repository for symbol",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern or symbol"},
            },
            "required": ["pattern"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "matched_files": {"type": "array", "items": {"type": "string"}},
                "file_contents": {"type": "string"},
            },
        },
        required_capabilities=["directory_tree", "search_code", "file_read"],
        optional_capabilities=["git_status"],
        action_classes=[ActionClass.READ_ONLY],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_tree",
                capability_id="directory_tree",
                description="Inspect workspace directory structure",
            ),
            SkillStepTemplate(
                step_id="step_2_search",
                capability_id="search_code",
                description="Search codebase for pattern",
                depends_on=["step_1_tree"],
                arg_mappings={"pattern": "$inputs.pattern"},
            ),
            SkillStepTemplate(
                step_id="step_3_read",
                capability_id="file_read",
                description="Read matched source file",
                depends_on=["step_2_search"],
                arg_mappings={"file_path": "$steps.step_2_search.target_file"},
            ),
        ],
        planning_required=False,
        verification_strategy="file_existence_and_content",
        applicable_autonomy=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        escalation_conditions=["permission_denied_on_source_file"],
    ),

    # -----------------------------------------------------------------------
    # 3. OS Domain: diagnose_system
    # -----------------------------------------------------------------------
    "diagnose_system": SkillManifest(
        skill_id="diagnose_system",
        version="1.0.0",
        domain="os",
        name="Diagnose System Health & Processes",
        description="Inspect hardware telemetry, CPU load, memory usage, and list running processes.",
        intent_patterns=[
            "system health",
            "diagnose system",
            "check cpu load",
            "check memory usage",
            "inspect running processes",
        ],
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "diagnostics": {"type": "string"},
                "process_count": {"type": "integer"},
            },
        },
        required_capabilities=["system_diagnostics", "list_processes"],
        optional_capabilities=["ping_test"],
        action_classes=[ActionClass.READ_ONLY],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_diagnostics",
                capability_id="system_diagnostics",
                description="Capture CPU and memory telemetry",
            ),
            SkillStepTemplate(
                step_id="step_2_processes",
                capability_id="list_processes",
                description="Inspect active running processes",
                depends_on=["step_1_diagnostics"],
            ),
        ],
        planning_required=False,
        verification_strategy="deterministic_receipt",
        applicable_autonomy=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        escalation_conditions=["system_metrics_unreadable"],
    ),

    # -----------------------------------------------------------------------
    # 4. Dev Domain: file_transform
    # -----------------------------------------------------------------------
    "file_transform": SkillManifest(
        skill_id="file_transform",
        version="1.0.0",
        domain="dev",
        name="Read, Transform and Write File",
        description="Read existing file content, apply modifications, and write changes safely back to disk.",
        intent_patterns=[
            "modify file",
            "transform file content",
            "update file",
            "edit file",
            "overwrite file content",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Target file path"},
                "content": {"type": "string", "description": "New content to write"},
            },
            "required": ["file_path", "content"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "bytes_written": {"type": "integer"},
                "verified": {"type": "boolean"},
            },
        },
        required_capabilities=["file_read", "file_write"],
        optional_capabilities=[],
        action_classes=[ActionClass.READ_ONLY, ActionClass.LOCAL_CREATE],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_read",
                capability_id="file_read",
                description="Read original file content before editing",
                arg_mappings={"file_path": "$inputs.file_path"},
            ),
            SkillStepTemplate(
                step_id="step_2_write",
                capability_id="file_write",
                description="Write modified content to file",
                depends_on=["step_1_read"],
                arg_mappings={"file_path": "$inputs.file_path", "content": "$inputs.content"},
            ),
        ],
        planning_required=False,
        verification_strategy="file_size_and_mtime",
        applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        escalation_conditions=["write_permission_denied", "target_file_locked"],
    ),

    # -----------------------------------------------------------------------
    # 5. Data Domain: analyze_data
    # -----------------------------------------------------------------------
    "analyze_data": SkillManifest(
        skill_id="analyze_data",
        version="1.0.0",
        domain="data",
        name="Query Database and Inspect Data",
        description="Execute SQL queries against SQLite database files and inspect structured tables or CSVs.",
        intent_patterns=[
            "query database",
            "execute sql on database",
            "inspect data table",
            "analyze dataset",
            "inspect sqlite records",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "db_path": {"type": "string", "description": "SQLite database path"},
                "query": {"type": "string", "description": "SQL query to execute"},
            },
            "required": ["db_path", "query"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "rows": {"type": "array"},
                "row_count": {"type": "integer"},
            },
        },
        required_capabilities=["sqlite_exec", "inspect_data"],
        optional_capabilities=["safe_math"],
        action_classes=[ActionClass.READ_ONLY, ActionClass.LOCAL_UPDATE],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_query",
                capability_id="sqlite_exec",
                description="Execute SQL query against database",
                arg_mappings={"db_path": "$inputs.db_path", "query": "$inputs.query"},
            ),
            SkillStepTemplate(
                step_id="step_2_inspect",
                capability_id="inspect_data",
                description="Inspect query result dataset or table",
                depends_on=["step_1_query"],
                arg_mappings={"file_path": "$inputs.db_path"},
            ),
        ],
        planning_required=False,
        verification_strategy="deterministic_receipt",
        applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        escalation_conditions=["database_locked", "corrupt_database_schema"],
    ),

    # -----------------------------------------------------------------------
    # 6. Browser Domain: browser_information_task
    # -----------------------------------------------------------------------
    "browser_information_task": SkillManifest(
        skill_id="browser_information_task",
        version="1.0.0",
        domain="browser",
        name="Visual Browser Information Gathering",
        description="Navigate browser to webpage, inspect visual DOM elements, and capture browser screenshot.",
        intent_patterns=[
            "browse website",
            "navigate to webpage",
            "open browser and view page",
            "capture browser screenshot of site",
            "visual browse page",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Webpage URL to navigate to"},
            },
            "required": ["url"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "page_title": {"type": "string"},
                "screenshot_path": {"type": "string"},
            },
        },
        required_capabilities=["visual_browse", "browser_screenshot"],
        optional_capabilities=[],
        action_classes=[ActionClass.READ_ONLY, ActionClass.SYSTEM_ACTION, ActionClass.LOCAL_CREATE],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_navigate",
                capability_id="visual_browse",
                description="Navigate browser to target URL",
                arg_mappings={"url": "$inputs.url"},
            ),
            SkillStepTemplate(
                step_id="step_2_screenshot",
                capability_id="browser_screenshot",
                description="Capture browser screenshot for visual receipt",
                depends_on=["step_1_navigate"],
            ),
        ],
        planning_required=False,
        verification_strategy="screenshot_receipt_and_dom",
        applicable_autonomy=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        escalation_conditions=["browser_launch_failure", "page_crash"],
    ),

    # -----------------------------------------------------------------------
    # 7. Dev Domain: perform_git_inspection
    # -----------------------------------------------------------------------
    "perform_git_inspection": SkillManifest(
        skill_id="perform_git_inspection",
        version="1.0.0",
        domain="dev",
        name="Perform Git Version Control Inspection",
        description="Inspect git repository status, branch history, and search for uncommitted modifications.",
        intent_patterns=[
            "git status",
            "git diff",
            "check git branch",
            "git commit history",
            "uncommitted changes in repo",
        ],
        input_schema={"type": "object", "properties": {}},
        output_schema={
            "type": "object",
            "properties": {
                "branch": {"type": "string"},
                "status_output": {"type": "string"},
            },
        },
        required_capabilities=["git_status", "search_code"],
        optional_capabilities=["file_read"],
        action_classes=[ActionClass.READ_ONLY],
        workflow_template=[
            SkillStepTemplate(
                step_id="step_1_git_status",
                capability_id="git_status",
                description="Check repository git status and active branch",
            ),
            SkillStepTemplate(
                step_id="step_2_search_changes",
                capability_id="search_code",
                description="Search modified files for target markers",
                depends_on=["step_1_git_status"],
            ),
        ],
        planning_required=False,
        verification_strategy="exit_code_and_stdout",
        applicable_autonomy=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        escalation_conditions=["git_binary_not_found", "not_a_git_repository"],
    ),
}


def build_canonical_skill_registry(
    capability_registry: Optional[CapabilityRegistry] = None,
) -> SkillRegistry:
    """Builds and populates a SkillRegistry with all 7 canonical skills."""
    registry = SkillRegistry(capability_registry=capability_registry)
    for skill in CANONICAL_SKILLS.values():
        registry.register(skill)
    return registry
