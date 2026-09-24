"""
omni_engine.capabilities.definitions
====================================
Canonical specifications and builders for all 23 source tools in the LAYA Omni Agent.

Binds the 23 source tools to canonical CapabilitySpecs and executable adapters,
enforcing 100% parity with omni_engine.tools.OMNI_TOOL_REGISTRY.
"""

from typing import Any, Dict, Optional

from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    IdempotencyClass,
    RetryPolicy,
)
from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.tools import OMNI_TOOL_REGISTRY

from .adapters import (
    make_adapter,
    make_clipboard_adapter,
    make_directory_tree_adapter,
    make_download_file_adapter,
    make_file_write_adapter,
    make_http_api_adapter,
    make_inspect_data_adapter,
    make_kill_process_adapter,
    make_list_processes_adapter,
    make_run_python_adapter,
    make_search_code_adapter,
    make_sqlite_exec_adapter,
    make_visual_browse_adapter,
)
from .registry import CapabilityRegistry


CANONICAL_SPECS: Dict[str, CapabilitySpec] = {
    # -----------------------------------------------------------------------
    # 1. Web Domain (4)
    # -----------------------------------------------------------------------
    "web_search": CapabilitySpec(
        id="web_search",
        version="1.0.0",
        name="Live Web Search",
        domain="web",
        description="Search the live internet for recent news, facts, current events, or topics using Tavily AI.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query keywords"},
                "max_results": {"type": "integer", "default": 6, "description": "Maximum search results"},
            },
            "required": ["query"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=20.0,
    ),
    "scrape_url": CapabilitySpec(
        id="scrape_url",
        version="1.0.0",
        name="Scrape Web URL",
        domain="web",
        description="Fetch and extract readable text content from any website URL.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Target web URL to fetch and scrape"},
            },
            "required": ["url"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=15.0,
    ),
    "http_api": CapabilitySpec(
        id="http_api",
        version="1.0.0",
        name="HTTP REST API",
        domain="web",
        description="Send GET, POST, PUT, or DELETE REST API requests to web endpoints.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Endpoint URL"},
                "method": {"type": "string", "default": "GET", "description": "HTTP method"},
                "body": {"type": "string", "description": "Optional request payload string"},
            },
            "required": ["url"],
        },
        action_class=ActionClass.EXTERNAL_CREATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=15.0,
    ),
    "download_file": CapabilitySpec(
        id="download_file",
        version="1.0.0",
        name="Download Web File",
        domain="web",
        description="Download images, datasets, or files from any URL to the local workspace.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Direct file URL to download"},
                "filename": {"type": "string", "description": "Local destination filename"},
            },
            "required": ["url"],
        },
        action_class=ActionClass.LOCAL_CREATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
        idempotency_class=IdempotencyClass.NATURAL,
        timeout_seconds=30.0,
    ),

    # -----------------------------------------------------------------------
    # 2. Browser Domain (2)
    # -----------------------------------------------------------------------
    "visual_browse": CapabilitySpec(
        id="visual_browse",
        version="1.0.0",
        name="Visual Edge Browser",
        domain="browser",
        description="Open Microsoft Edge to visually browse websites, click elements, and extract live data.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL or search query to browse in Edge"},
            },
            "required": ["url"],
        },
        action_class=ActionClass.SYSTEM_ACTION,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=45.0,
    ),
    "browser_screenshot": CapabilitySpec(
        id="browser_screenshot",
        version="1.0.0",
        name="Browser Screenshot",
        domain="browser",
        description="Capture a high-resolution screenshot of a live webpage in Microsoft Edge.",
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Webpage URL to capture"},
            },
            "required": ["url"],
        },
        action_class=ActionClass.LOCAL_CREATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
        idempotency_class=IdempotencyClass.NATURAL,
        timeout_seconds=30.0,
    ),

    # -----------------------------------------------------------------------
    # 3. OS & Desktop Domain (8)
    # -----------------------------------------------------------------------
    "system_diagnostics": CapabilitySpec(
        id="system_diagnostics",
        version="1.0.0",
        name="System Diagnostics",
        domain="os",
        description="Check real-time CPU, RAM, Disk space, network activity, and host uptime.",
        input_schema={"type": "object", "properties": {}},
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),
    "list_processes": CapabilitySpec(
        id="list_processes",
        version="1.0.0",
        name="List OS Processes",
        domain="os",
        description="Inspect running processes and identify CPU and memory consumption.",
        input_schema={
            "type": "object",
            "properties": {
                "filter_name": {"type": "string", "default": "", "description": "Optional substring filter"},
            },
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),
    "kill_process": CapabilitySpec(
        id="kill_process",
        version="1.0.0",
        name="Kill OS Process",
        domain="os",
        description="Terminate a running or hung process by PID or process name.",
        input_schema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "description": "Target PID or process executable name"},
            },
            "required": ["target"],
        },
        action_class=ActionClass.SYSTEM_ACTION,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.ALWAYS,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=10.0,
    ),
    "launch_app": CapabilitySpec(
        id="launch_app",
        version="1.0.0",
        name="Launch Desktop App",
        domain="os",
        description="Launch desktop applications such as Notepad, Calculator, VS Code, or Spotify.",
        input_schema={
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Application name or binary command"},
            },
            "required": ["app_name"],
        },
        action_class=ActionClass.SYSTEM_ACTION,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=10.0,
    ),
    "desktop_screenshot": CapabilitySpec(
        id="desktop_screenshot",
        version="1.0.0",
        name="Desktop Screenshot",
        domain="os",
        description="Take a full-resolution screenshot of the Windows desktop.",
        input_schema={"type": "object", "properties": {}},
        action_class=ActionClass.LOCAL_CREATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
        idempotency_class=IdempotencyClass.NATURAL,
        timeout_seconds=10.0,
    ),
    "clipboard": CapabilitySpec(
        id="clipboard",
        version="1.0.0",
        name="OS Clipboard",
        domain="os",
        description="Read or copy text to and from the system clipboard.",
        input_schema={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["read", "copy"], "default": "read"},
                "text": {"type": "string", "default": "", "description": "Text to copy if action is 'copy'"},
            },
        },
        action_class=ActionClass.LOCAL_UPDATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NATURAL,
        timeout_seconds=5.0,
    ),
    "powershell": CapabilitySpec(
        id="powershell",
        version="1.0.0",
        name="PowerShell Execution",
        domain="os",
        description="Execute commands, inspect environment, or manage files via Windows PowerShell.",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "PowerShell command or script string"},
            },
            "required": ["command"],
        },
        action_class=ActionClass.SYSTEM_ACTION,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
        confirmation_policy=ConfirmationPolicy.ALWAYS,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=30.0,
    ),
    "ping_test": CapabilitySpec(
        id="ping_test",
        version="1.0.0",
        name="Network Ping Test",
        domain="os",
        description="Check network connectivity and latency to an IP address or domain.",
        input_schema={
            "type": "object",
            "properties": {
                "host": {"type": "string", "default": "8.8.8.8", "description": "Host or IP to ping"},
            },
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),

    # -----------------------------------------------------------------------
    # 4. Dev & Code Domain (6)
    # -----------------------------------------------------------------------
    "file_read": CapabilitySpec(
        id="file_read",
        version="1.0.0",
        name="Read Local File",
        domain="dev",
        description="Read UTF-8 content from any local source file, document, or config.",
        input_schema={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to file to read"},
            },
            "required": ["filepath"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),
    "file_write": CapabilitySpec(
        id="file_write",
        version="1.0.0",
        name="Write Local File",
        domain="dev",
        description="Create or overwrite a file with specified UTF-8 content.",
        input_schema={
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Target destination file path"},
                "content": {"type": "string", "description": "Content to write into the file"},
            },
            "required": ["filepath", "content"],
        },
        action_class=ActionClass.LOCAL_CREATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
        idempotency_class=IdempotencyClass.NATURAL,
        timeout_seconds=15.0,
    ),
    "search_code": CapabilitySpec(
        id="search_code",
        version="1.0.0",
        name="Search Codebase",
        domain="dev",
        description="Search for regex patterns, functions, classes, or keywords across source files.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keyword or pattern"},
                "path": {"type": "string", "default": ".", "description": "Directory root to search"},
            },
            "required": ["query"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=15.0,
    ),
    "directory_tree": CapabilitySpec(
        id="directory_tree",
        version="1.0.0",
        name="Directory Tree",
        domain="dev",
        description="Inspect folder hierarchy, subdirectories, and files up to specified depth.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": ".", "description": "Root path to map"},
                "max_depth": {"type": "integer", "default": 3, "description": "Max hierarchy depth"},
            },
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),
    "run_python": CapabilitySpec(
        id="run_python",
        version="1.0.0",
        name="Run Python Code",
        domain="dev",
        description="Execute a Python script or code snippet in a sandboxed subprocess.",
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python source code string to execute"},
            },
            "required": ["code"],
        },
        action_class=ActionClass.SYSTEM_ACTION,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.ALWAYS,
        retry_policy=RetryPolicy.NEVER,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=20.0,
    ),
    "git_status": CapabilitySpec(
        id="git_status",
        version="1.0.0",
        name="Git Status",
        domain="dev",
        description="Inspect git repository status, staged changes, and active branch.",
        input_schema={"type": "object", "properties": {}},
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=10.0,
    ),

    # -----------------------------------------------------------------------
    # 5. Data & Analysis Domain (3)
    # -----------------------------------------------------------------------
    "sqlite_exec": CapabilitySpec(
        id="sqlite_exec",
        version="1.0.0",
        name="SQLite Database Query",
        domain="data",
        description="Query, create tables, or update local SQLite database files.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SQL query string"},
                "db_path": {"type": "string", "default": "omni_agent.db", "description": "SQLite database path"},
            },
            "required": ["query"],
        },
        action_class=ActionClass.LOCAL_UPDATE,
        side_effects=True,
        minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
        confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
        retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
        idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
        timeout_seconds=15.0,
    ),
    "inspect_data": CapabilitySpec(
        id="inspect_data",
        version="1.0.0",
        name="Inspect Dataset",
        domain="data",
        description="Analyze structure, schema, rows, and summary of CSV, JSON, or text files.",
        input_schema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Data file path to inspect"},
            },
            "required": ["file_path"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=15.0,
    ),
    "safe_math": CapabilitySpec(
        id="safe_math",
        version="1.0.0",
        name="Safe Mathematical Evaluator",
        domain="data",
        description="Safely evaluate complex mathematical expressions with strict AST whitelist and resource bounds.",
        input_schema={
            "type": "object",
            "properties": {
                "expression": {"type": "string", "description": "Mathematical formula to evaluate"},
            },
            "required": ["expression"],
        },
        action_class=ActionClass.READ_ONLY,
        side_effects=False,
        minimum_autonomy_profile=AutonomyProfile.ADVISOR,
        confirmation_policy=ConfirmationPolicy.NEVER,
        retry_policy=RetryPolicy.SAFE_READ_RETRY,
        idempotency_class=IdempotencyClass.READ_ONLY,
        timeout_seconds=5.0,
    ),
}


def build_canonical_registry() -> CapabilityRegistry:
    """Constructs and populates a CapabilityRegistry with all 23 source tools.
    
    Binds typed adapters and implementations for each tool.
    Guarantees 1:1 parity with OMNI_TOOL_REGISTRY.
    """
    registry = CapabilityRegistry()

    # Specialized adapter mappings ensuring valid schema kwargs work seamlessly
    adapter_factory = {
        "file_write": make_file_write_adapter,
        "http_api": make_http_api_adapter,
        "download_file": make_download_file_adapter,
        "clipboard": make_clipboard_adapter,
        "inspect_data": make_inspect_data_adapter,
        "visual_browse": make_visual_browse_adapter,
        "list_processes": make_list_processes_adapter,
        "kill_process": make_kill_process_adapter,
        "search_code": make_search_code_adapter,
        "directory_tree": make_directory_tree_adapter,
        "run_python": make_run_python_adapter,
        "sqlite_exec": make_sqlite_exec_adapter,
    }

    for cap_id, spec in CANONICAL_SPECS.items():
        if cap_id not in OMNI_TOOL_REGISTRY:
            raise KeyError(f"Capability '{cap_id}' defined in CANONICAL_SPECS missing from source OMNI_TOOL_REGISTRY.")

        raw_func = OMNI_TOOL_REGISTRY[cap_id]["func"]

        if cap_id in adapter_factory:
            impl = adapter_factory[cap_id](raw_func, cap_id)
        else:
            impl = make_adapter(raw_func, cap_id)

        registry.register(spec=spec, implementation=impl)

    return registry


# -----------------------------------------------------------------------
# Real Capability Engines (R1 -> R5)
# -----------------------------------------------------------------------

DEEP_RESEARCH_SPEC = CapabilitySpec(
    id="deep_research",
    version="1.0.0",
    name="Deep Evidence-Grounded Research",
    domain="web",
    description="Conduct multi-source deep research, crawling, evidence ledger extraction, and verified citation synthesis.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Research topic or question to investigate"},
            "breadth": {"type": "integer", "default": 5, "description": "Maximum candidate search queries/URLs"},
            "depth": {"type": "integer", "default": 1, "description": "Maximum crawl depth hops (0 or 1)"},
            "max_pages": {"type": "integer", "default": 10, "description": "Maximum total web pages to fetch"},
        },
        "required": ["query"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=60.0,
)

REAL_CAPABILITY_SPECS: Dict[str, CapabilitySpec] = {
    "deep_research": DEEP_RESEARCH_SPEC,
}


def make_deep_research_adapter(engine: Any = None):
    """Creates a typed adapter wrapping DeepResearchEngine."""
    def adapter(**kwargs) -> Dict[str, Any]:
        from omni_engine.contracts.research import ResearchBudget
        from omni_engine.research.engine import DeepResearchEngine
        nonlocal engine
        if engine is None:
            engine = DeepResearchEngine()

        query = kwargs.get("query", "")
        breadth = int(kwargs.get("breadth", 5))
        depth = int(kwargs.get("depth", 1))
        max_pages = int(kwargs.get("max_pages", 10))

        budget = ResearchBudget(
            max_search_queries=min(breadth, 10),
            max_crawl_depth=min(depth, 1),
            max_total_pages=min(max_pages, 20),
        )
        dossier = engine.execute(query=query, budget=budget)
        return {
            "query": dossier.query,
            "summary": dossier.summary,
            "claims": [c.model_dump() for c in dossier.claims],
            "evidence_count": len(dossier.evidence_ledger),
            "telemetry": dossier.telemetry.model_dump(),
        }

    return adapter


def register_deep_research_capability(
    registry: CapabilityRegistry,
    engine: Any = None,
) -> None:
    """Registers deep_research and alias research.deep on a CapabilityRegistry."""
    adapter = make_deep_research_adapter(engine)

    # Register primary ID
    registry.register(spec=DEEP_RESEARCH_SPEC, implementation=adapter)

    # Register dotted alias
    alias_spec = DEEP_RESEARCH_SPEC.model_copy(update={"id": "research.deep"})
    registry.register(spec=alias_spec, implementation=adapter)


def build_real_capability_registry(
    base_registry: Optional[CapabilityRegistry] = None,
    research_engine: Any = None,
) -> CapabilityRegistry:
    """Builds a CapabilityRegistry containing the canonical 23 tools PLUS real capability engines."""
    reg = base_registry or build_canonical_registry()
    register_deep_research_capability(reg, engine=research_engine)
    return reg

