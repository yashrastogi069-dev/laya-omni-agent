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
    make_safe_math_adapter,
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
        "safe_math": make_safe_math_adapter,
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

BROWSER_INTERACT_SPEC = CapabilitySpec(
    id="browser_interact",
    version="1.0.0",
    name="Interactive Persistent Browser Automation",
    domain="browser",
    description="Perform verified interactive browser actions (navigate, click, type, press key, select option, scroll, snapshot, screenshot) with dynamic indexed action space and financial safety gating.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["navigate", "click", "type", "press_key", "select_option", "scroll", "snapshot", "screenshot", "confirm_purchase"],
                "description": "Primitive browser action to execute",
            },
            "url": {"type": "string", "description": "Target web page URL to navigate to"},
            "target": {"type": "string", "description": "Target element index (@1..@N) or selector to interact with"},
            "text": {"type": "string", "description": "Text value to fill into targeted input element"},
            "key": {"type": "string", "description": "Keyboard key to press (Enter, Tab, Escape)"},
            "value": {"type": "string", "description": "Dropdown option value to select"},
            "scroll_direction": {"type": "string", "enum": ["up", "down", "top", "bottom"], "default": "down"},
            "scroll_amount": {"type": "integer", "default": 400},
            "output_path": {"type": "string", "description": "Destination file path for captured screenshot"},
            "user_confirmed": {"type": "boolean", "default": False, "description": "Human confirmation for financial/payment actions"},
        },
        "required": ["action"],
    },
    action_class=ActionClass.EXTERNAL_UPDATE,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=30.0,
)



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


def make_browser_interact_adapter(driver: Any = None):
    """Creates a typed adapter wrapping BrowserDriver."""
    def adapter(**kwargs) -> Dict[str, Any]:
        from omni_engine.contracts.browser import BrowserActionRequest, BrowserActionType
        from omni_engine.browser.driver import BrowserDriver
        nonlocal driver
        if driver is None:
            driver = BrowserDriver()

        action_str = kwargs.get("action", "snapshot")
        action_type = BrowserActionType(action_str)

        req = BrowserActionRequest(
            action_type=action_type,
            url=kwargs.get("url"),
            target=kwargs.get("target"),
            text=kwargs.get("text"),
            key=kwargs.get("key"),
            value=kwargs.get("value"),
            scroll_direction=kwargs.get("scroll_direction", "down"),
            scroll_amount=int(kwargs.get("scroll_amount", 400)),
            user_confirmed=bool(kwargs.get("user_confirmed", False)),
            output_path=kwargs.get("output_path"),
        )
        result = driver.execute(req)
        return result.model_dump()

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


def register_browser_capability(
    registry: CapabilityRegistry,
    driver: Any = None,
) -> None:
    """Registers browser_interact and alias browser.interact on a CapabilityRegistry."""
    adapter = make_browser_interact_adapter(driver)

    # Register primary ID
    registry.register(spec=BROWSER_INTERACT_SPEC, implementation=adapter)

    # Register dotted alias
    alias_spec = BROWSER_INTERACT_SPEC.model_copy(update={"id": "browser.interact"})
    registry.register(spec=alias_spec, implementation=adapter)


# -----------------------------------------------------------------------
# Phase R3: Desktop & Local Service Capabilities
# -----------------------------------------------------------------------

DESKTOP_LAUNCH_APP_SPEC = CapabilitySpec(
    id="desktop.launch_app",
    version="1.0.0",
    name="Desktop Application Launcher",
    domain="os",
    description="Launches Windows desktop applications with process trampoline resolution, PID tracking, and window verification.",
    input_schema={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Application name or executable (e.g. 'calc', 'notepad', 'code')"},
            "args": {"type": "array", "items": {"type": "string"}, "description": "Optional command line arguments"},
            "timeout": {"type": "number", "default": 3.0, "description": "Startup and window appearance timeout in seconds"},
        },
        "required": ["app_name"],
    },
    action_class=ActionClass.SYSTEM_ACTION,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=10.0,
)

DESKTOP_LIST_WINDOWS_SPEC = CapabilitySpec(
    id="desktop.list_windows",
    version="1.0.0",
    name="Desktop Window Inspector",
    domain="os",
    description="Enumerates open visible top-level desktop windows with titles, process IDs, and bounding coordinates.",
    input_schema={
        "type": "object",
        "properties": {
            "filter_title": {"type": "string", "description": "Optional substring to filter window titles"},
            "visible_only": {"type": "boolean", "default": True, "description": "Whether to return only visible windows"},
        },
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.ADVISOR,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=5.0,
)

DESKTOP_FOCUS_WINDOW_SPEC = CapabilitySpec(
    id="desktop.focus_window",
    version="1.0.0",
    name="Desktop Window Focus Controller",
    domain="os",
    description="Brings a desktop window to the foreground with hung-app detection and unminimize-only protection.",
    input_schema={
        "type": "object",
        "properties": {
            "target": {"type": ["integer", "string"], "description": "Window HWND or window title substring"},
            "timeout": {"type": "number", "default": 0.5, "description": "Focus verification timeout in seconds"},
        },
        "required": ["target"],
    },
    action_class=ActionClass.LOCAL_UPDATE,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=5.0,
)

DESKTOP_CLOSE_WINDOW_SPEC = CapabilitySpec(
    id="desktop.close_window",
    version="1.0.0",
    name="Desktop Window Closer",
    domain="os",
    description="Gracefully closes a desktop window via WM_CLOSE with Rule-0 protected process defenses.",
    input_schema={
        "type": "object",
        "properties": {
            "target": {"type": ["integer", "string"], "description": "Window HWND or window title substring"},
            "timeout": {"type": "number", "default": 1.0, "description": "Closure verification timeout in seconds"},
        },
        "required": ["target"],
    },
    action_class=ActionClass.SYSTEM_ACTION,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=5.0,
)

DESKTOP_SERVICE_HEALTH_SPEC = CapabilitySpec(
    id="desktop.service_health",
    version="1.0.0",
    name="Local Service & Port Health Prober",
    domain="os",
    description="Probes TCP socket listening status and HTTP endpoint health for local services (e.g. n8n on port 5678, Ollama on 11434).",
    input_schema={
        "type": "object",
        "properties": {
            "service_name": {"type": "string", "description": "Service name (e.g. 'n8n', 'ollama', 'dev_server') or port"},
            "host": {"type": "string", "default": "127.0.0.1", "description": "Network host (defaults to loopback)"},
            "port": {"type": "integer", "description": "Explicit port number"},
            "http_path": {"type": "string", "description": "Optional HTTP health check path (e.g. '/healthz')"},
        },
        "required": ["service_name"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.ADVISOR,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=5.0,
)

DESKTOP_SEND_KEYS_SPEC = CapabilitySpec(
    id="desktop.send_keys",
    version="1.0.0",
    name="Desktop Keystroke Dispatcher",
    domain="os",
    description="Sends keystrokes to a designated window after verifying foreground focus.",
    input_schema={
        "type": "object",
        "properties": {
            "target": {"type": ["integer", "string"], "description": "Window HWND or title"},
            "text": {"type": "string", "description": "Text or character sequence to send"},
            "press_enter": {"type": "boolean", "default": False, "description": "Whether to send Enter key after text"},
        },
        "required": ["target", "text"],
    },
    action_class=ActionClass.SYSTEM_ACTION,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.TRUSTED_OPERATOR,
    confirmation_policy=ConfirmationPolicy.ALWAYS,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=10.0,
)


def make_desktop_launch_app_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        app_name = str(kwargs.get("app_name") or kwargs.get("app") or "")
        args = kwargs.get("args")
        timeout = float(kwargs.get("timeout", 3.0))
        result = driver.launch_app(app_name=app_name, args=args, timeout=timeout)
        return result.model_dump()
    return adapter


def make_desktop_list_windows_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        filter_title = kwargs.get("filter_title")
        visible_only = bool(kwargs.get("visible_only", True))
        windows = driver.list_windows(filter_title=filter_title, visible_only=visible_only)
        return {"windows": [w.model_dump() for w in windows], "count": len(windows)}
    return adapter


def make_desktop_focus_window_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        target = kwargs.get("target") or kwargs.get("hwnd") or kwargs.get("window_target") or ""
        timeout = float(kwargs.get("timeout", 0.5))
        result = driver.focus_window(target=target, timeout=timeout)
        return result.model_dump()
    return adapter


def make_desktop_close_window_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        target = kwargs.get("target") or kwargs.get("hwnd") or kwargs.get("window_target") or ""
        timeout = float(kwargs.get("timeout", 1.0))
        result = driver.close_window(target=target, timeout=timeout)
        return result.model_dump()
    return adapter


def make_desktop_service_health_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        service_name = str(kwargs.get("service_name") or kwargs.get("service") or "n8n")
        host = kwargs.get("host")
        port = int(kwargs["port"]) if kwargs.get("port") is not None else None
        http_path = kwargs.get("http_path")
        result = driver.check_service(service_name=service_name, host=host, port=port, http_path=http_path)
        return result.model_dump()
    return adapter


def make_desktop_send_keys_adapter(driver: Any = None):
    def adapter(**kwargs: Any) -> Dict[str, Any]:
        nonlocal driver
        if driver is None:
            from omni_engine.desktop.engine import ComputerUseDriver
            driver = ComputerUseDriver()
        target = kwargs.get("target") or kwargs.get("hwnd") or kwargs.get("window_target") or ""
        text = str(kwargs.get("text") or kwargs.get("keys") or "")
        press_enter = bool(kwargs.get("press_enter", False))
        result = driver.send_keys(target=target, text=text, press_enter=press_enter)
        return result.model_dump()
    return adapter


def register_desktop_capabilities(
    registry: CapabilityRegistry,
    driver: Any = None,
) -> None:
    """Registers desktop and local service capabilities on a CapabilityRegistry."""
    # 1. launch_app
    launch_adapter = make_desktop_launch_app_adapter(driver)
    registry.register(spec=DESKTOP_LAUNCH_APP_SPEC, implementation=launch_adapter)
    registry.register(
        spec=DESKTOP_LAUNCH_APP_SPEC.model_copy(update={"id": "desktop_launch_app"}),
        implementation=launch_adapter,
    )

    # 2. list_windows
    list_adapter = make_desktop_list_windows_adapter(driver)
    registry.register(spec=DESKTOP_LIST_WINDOWS_SPEC, implementation=list_adapter)
    registry.register(
        spec=DESKTOP_LIST_WINDOWS_SPEC.model_copy(update={"id": "desktop_list_windows"}),
        implementation=list_adapter,
    )

    # 3. focus_window
    focus_adapter = make_desktop_focus_window_adapter(driver)
    registry.register(spec=DESKTOP_FOCUS_WINDOW_SPEC, implementation=focus_adapter)
    registry.register(
        spec=DESKTOP_FOCUS_WINDOW_SPEC.model_copy(update={"id": "desktop_focus_window"}),
        implementation=focus_adapter,
    )

    # 4. close_window
    close_adapter = make_desktop_close_window_adapter(driver)
    registry.register(spec=DESKTOP_CLOSE_WINDOW_SPEC, implementation=close_adapter)
    registry.register(
        spec=DESKTOP_CLOSE_WINDOW_SPEC.model_copy(update={"id": "desktop_close_window"}),
        implementation=close_adapter,
    )

    # 5. service_health
    health_adapter = make_desktop_service_health_adapter(driver)
    registry.register(spec=DESKTOP_SERVICE_HEALTH_SPEC, implementation=health_adapter)
    registry.register(
        spec=DESKTOP_SERVICE_HEALTH_SPEC.model_copy(update={"id": "desktop_service_health"}),
        implementation=health_adapter,
    )

    # 6. send_keys
    keys_adapter = make_desktop_send_keys_adapter(driver)
    registry.register(spec=DESKTOP_SEND_KEYS_SPEC, implementation=keys_adapter)
    registry.register(
        spec=DESKTOP_SEND_KEYS_SPEC.model_copy(update={"id": "desktop_send_keys"}),
        implementation=keys_adapter,
    )


# -----------------------------------------------------------------------
# Phase R4: n8n Automation Engine Specs & Adapters
# -----------------------------------------------------------------------

N8N_LIST_WORKFLOWS_SPEC = CapabilitySpec(
    id="n8n.list_workflows",
    version="1.0.0",
    name="List n8n Workflows",
    domain="automation",
    description="List all workflows available on the n8n automation server.",
    input_schema={
        "type": "object",
        "properties": {},
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=10.0,
)

N8N_GET_WORKFLOW_SPEC = CapabilitySpec(
    id="n8n.get_workflow",
    version="1.0.0",
    name="Get n8n Workflow Detail",
    domain="automation",
    description="Fetch full workflow configuration, nodes, and connections by workflow ID.",
    input_schema={
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string", "description": "Workflow identifier"},
        },
        "required": ["workflow_id"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=10.0,
)

N8N_VALIDATE_WORKFLOW_SPEC = CapabilitySpec(
    id="n8n.validate_workflow",
    version="1.0.0",
    name="Validate n8n Workflow",
    domain="automation",
    description="Validate workflow graph for acyclicity, valid triggers, reachability, and parameter security.",
    input_schema={
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string", "description": "Optional workflow ID to validate"},
            "workflow_data": {"type": "object", "description": "Optional workflow definition JSON dict to validate"},
        },
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=5.0,
)

N8N_CREATE_WORKFLOW_SPEC = CapabilitySpec(
    id="n8n.create_workflow",
    version="1.0.0",
    name="Create n8n Workflow Draft",
    domain="automation",
    description="Create a new workflow strictly in inactive draft mode (active=False) with pre-flight graph validation.",
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Workflow display title"},
            "nodes": {"type": "array", "description": "List of node definition objects"},
            "connections": {"type": "object", "description": "3-level nested node connections mapping"},
            "settings": {"type": "object", "description": "Optional execution settings"},
        },
        "required": ["name", "nodes", "connections"],
    },
    action_class=ActionClass.LOCAL_UPDATE,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=15.0,
)

N8N_ACTIVATE_WORKFLOW_SPEC = CapabilitySpec(
    id="n8n.activate_workflow",
    version="1.0.0",
    name="Activate n8n Workflow",
    domain="automation",
    description="Activate an n8n workflow under the Gate Triad (valid DAG, tested execution receipt, zero secrets).",
    input_schema={
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string", "description": "Workflow ID to activate"},
        },
        "required": ["workflow_id"],
    },
    action_class=ActionClass.EXTERNAL_UPDATE,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.VERIFY_BEFORE_RETRY,
    idempotency_class=IdempotencyClass.NATURAL,
    timeout_seconds=15.0,
)

N8N_TRIGGER_WORKFLOW_SPEC = CapabilitySpec(
    id="n8n.trigger_workflow",
    version="1.0.0",
    name="Trigger n8n Workflow",
    domain="automation",
    description="Trigger execution of an active n8n workflow and poll for physical execution receipt.",
    input_schema={
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string", "description": "Workflow ID to trigger"},
            "payload": {"type": "object", "description": "Optional input data payload"},
            "wait_for_completion": {"type": "boolean", "default": True, "description": "Whether to poll until completion"},
            "timeout_seconds": {"type": "number", "default": 30.0, "description": "Maximum seconds to wait for execution"},
        },
        "required": ["workflow_id"],
    },
    action_class=ActionClass.SYSTEM_ACTION,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=45.0,
)

N8N_GET_EXECUTION_STATUS_SPEC = CapabilitySpec(
    id="n8n.get_execution_status",
    version="1.0.0",
    name="Get n8n Execution Status",
    domain="automation",
    description="Poll execution state, duration, and output data for an n8n execution ID.",
    input_schema={
        "type": "object",
        "properties": {
            "execution_id": {"type": "string", "description": "n8n execution identifier"},
        },
        "required": ["execution_id"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=10.0,
)


def make_n8n_list_workflows_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        res = eng.list_workflows()
        return res.model_dump()
    return adapter


def make_n8n_get_workflow_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        wf_id = str(kwargs.get("workflow_id") or kwargs.get("id") or "")
        res = eng.get_workflow(wf_id)
        return res.model_dump()
    return adapter


def make_n8n_validate_workflow_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        wf_target = kwargs.get("workflow_data") or kwargs.get("workflow_id") or kwargs.get("id") or ""
        val = eng.validate_workflow(wf_target)
        return val.model_dump()
    return adapter


def make_n8n_create_workflow_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        name = str(kwargs.get("name") or "New Workflow")
        nodes = kwargs.get("nodes") or []
        conns = kwargs.get("connections") or {}
        settings = kwargs.get("settings")
        res = eng.create_workflow(name=name, nodes=nodes, connections=conns, settings=settings)
        return res.model_dump()
    return adapter


def make_n8n_activate_workflow_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        wf_id = str(kwargs.get("workflow_id") or kwargs.get("id") or "")
        res = eng.activate_workflow(wf_id)
        return res.model_dump()
    return adapter


def make_n8n_trigger_workflow_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        wf_id = str(kwargs.get("workflow_id") or kwargs.get("id") or "")
        payload = kwargs.get("payload")
        wait = bool(kwargs.get("wait_for_completion", True))
        timeout = float(kwargs.get("timeout_seconds", 30.0))
        res = eng.trigger_workflow(wf_id, payload=payload, wait_for_completion=wait, timeout_seconds=timeout)
        return res.model_dump()
    return adapter


def make_n8n_get_execution_status_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.automation.engine import N8nAutomationEngine
            from omni_engine.automation.client import N8nClient
            from omni_engine.automation.transport import HttpN8nTransport
            eng = N8nAutomationEngine(client=N8nClient(transport=HttpN8nTransport()))
        exec_id = str(kwargs.get("execution_id") or kwargs.get("id") or "")
        success, receipt, err = eng.client.get_execution(exec_id)
        if not success or not receipt:
            return {"success": False, "error": err or f"Execution {exec_id} not found"}
        return receipt.model_dump()
    return adapter


def register_n8n_capabilities(registry: CapabilityRegistry, engine: Any = None) -> None:
    """Registers all n8n automation capabilities and dotless aliases."""
    # 1. list_workflows
    list_ad = make_n8n_list_workflows_adapter(engine)
    registry.register(spec=N8N_LIST_WORKFLOWS_SPEC, implementation=list_ad)
    registry.register(
        spec=N8N_LIST_WORKFLOWS_SPEC.model_copy(update={"id": "n8n_list_workflows"}),
        implementation=list_ad,
    )

    # 2. get_workflow
    get_ad = make_n8n_get_workflow_adapter(engine)
    registry.register(spec=N8N_GET_WORKFLOW_SPEC, implementation=get_ad)
    registry.register(
        spec=N8N_GET_WORKFLOW_SPEC.model_copy(update={"id": "n8n_get_workflow"}),
        implementation=get_ad,
    )

    # 3. validate_workflow
    val_ad = make_n8n_validate_workflow_adapter(engine)
    registry.register(spec=N8N_VALIDATE_WORKFLOW_SPEC, implementation=val_ad)
    registry.register(
        spec=N8N_VALIDATE_WORKFLOW_SPEC.model_copy(update={"id": "n8n_validate_workflow"}),
        implementation=val_ad,
    )

    # 4. create_workflow
    create_ad = make_n8n_create_workflow_adapter(engine)
    registry.register(spec=N8N_CREATE_WORKFLOW_SPEC, implementation=create_ad)
    registry.register(
        spec=N8N_CREATE_WORKFLOW_SPEC.model_copy(update={"id": "n8n_create_workflow"}),
        implementation=create_ad,
    )

    # 5. activate_workflow
    act_ad = make_n8n_activate_workflow_adapter(engine)
    registry.register(spec=N8N_ACTIVATE_WORKFLOW_SPEC, implementation=act_ad)
    registry.register(
        spec=N8N_ACTIVATE_WORKFLOW_SPEC.model_copy(update={"id": "n8n_activate_workflow"}),
        implementation=act_ad,
    )

    # 6. trigger_workflow
    trig_ad = make_n8n_trigger_workflow_adapter(engine)
    registry.register(spec=N8N_TRIGGER_WORKFLOW_SPEC, implementation=trig_ad)
    registry.register(
        spec=N8N_TRIGGER_WORKFLOW_SPEC.model_copy(update={"id": "n8n_trigger_workflow"}),
        implementation=trig_ad,
    )

    # 7. get_execution_status
    exec_ad = make_n8n_get_execution_status_adapter(engine)
    registry.register(spec=N8N_GET_EXECUTION_STATUS_SPEC, implementation=exec_ad)
    registry.register(
        spec=N8N_GET_EXECUTION_STATUS_SPEC.model_copy(update={"id": "n8n_get_execution_status"}),
        implementation=exec_ad,
    )


# -----------------------------------------------------------------------
# Developer Agent & Code Supervision Specs (Phase R5)
# -----------------------------------------------------------------------

DEVELOPER_RUN_TASK_SPEC = CapabilitySpec(
    id="developer.run_task",
    version="1.0.0",
    name="Supervised Developer Task Runner",
    domain="dev",
    description="Supervise an autonomous coding task with bounded iterations, pre-test AST syntax gating, physical test verification, and safe rollback.",
    input_schema={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Target git repository path"},
            "task_prompt": {"type": "string", "description": "Instructions or bug fix description"},
            "target_files": {"type": "array", "items": {"type": "string"}, "default": []},
            "test_commands": {"type": "array", "items": {"type": "string"}, "default": []},
            "allow_test_edits": {"type": "boolean", "default": False},
            "max_iterations": {"type": "integer", "default": 3, "minimum": 1, "maximum": 5},
            "timeout_seconds": {"type": "number", "default": 120.0},
        },
        "required": ["repo_path", "task_prompt"],
    },
    action_class=ActionClass.LOCAL_UPDATE,
    side_effects=True,
    minimum_autonomy_profile=AutonomyProfile.LOCAL_OPERATOR,
    confirmation_policy=ConfirmationPolicy.POLICY_CONTROLLED,
    retry_policy=RetryPolicy.NEVER,
    idempotency_class=IdempotencyClass.NON_IDEMPOTENT,
    timeout_seconds=120.0,
)

DEVELOPER_RUN_TESTS_SPEC = CapabilitySpec(
    id="developer.run_tests",
    version="1.0.0",
    name="Deterministic Developer Test Runner",
    domain="dev",
    description="Execute repository test commands in a bounded subprocess with Rule-0 scanning and physical exit code capture.",
    input_schema={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Target git repository path"},
            "test_commands": {"type": "array", "items": {"type": "string"}, "description": "Test command lines to execute"},
            "timeout_seconds": {"type": "number", "default": 30.0},
        },
        "required": ["repo_path", "test_commands"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.SAFE_ASSISTANT,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=30.0,
)

DEVELOPER_GIT_DIFF_SPEC = CapabilitySpec(
    id="developer.git_diff",
    version="1.0.0",
    name="Developer Git Diff Extraction",
    domain="dev",
    description="Extract working tree git diff for target repository and optional file filters.",
    input_schema={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Target git repository path"},
            "target_files": {"type": "array", "items": {"type": "string"}, "default": []},
        },
        "required": ["repo_path"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.ADVISOR,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=10.0,
)

DEVELOPER_INSPECT_CODE_SPEC = CapabilitySpec(
    id="developer.inspect_code",
    version="1.0.0",
    name="Developer Workspace Code Inspection",
    domain="dev",
    description="Inspect file content within target repository with strict sandbox containment.",
    input_schema={
        "type": "object",
        "properties": {
            "repo_path": {"type": "string", "description": "Target git repository path"},
            "file_path": {"type": "string", "description": "Relative file path within repository"},
        },
        "required": ["repo_path", "file_path"],
    },
    action_class=ActionClass.READ_ONLY,
    side_effects=False,
    minimum_autonomy_profile=AutonomyProfile.ADVISOR,
    confirmation_policy=ConfirmationPolicy.NEVER,
    retry_policy=RetryPolicy.SAFE_READ_RETRY,
    idempotency_class=IdempotencyClass.READ_ONLY,
    timeout_seconds=5.0,
)


def make_developer_run_task_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.developer.engine import DeveloperSupervisorEngine
            eng = DeveloperSupervisorEngine()
        from omni_engine.contracts.developer import DevTaskSpec
        import uuid
        spec = DevTaskSpec(
            task_id=str(kwargs.get("task_id") or f"task_{uuid.uuid4().hex[:8]}"),
            repo_path=str(kwargs.get("repo_path") or ""),
            task_prompt=str(kwargs.get("task_prompt") or kwargs.get("prompt") or ""),
            target_files=list(kwargs.get("target_files") or []),
            test_commands=list(kwargs.get("test_commands") or []),
            allow_test_edits=bool(kwargs.get("allow_test_edits", False)),
            max_iterations=int(kwargs.get("max_iterations", 3)),
            timeout_seconds=float(kwargs.get("timeout_seconds", 120.0)),
        )
        receipt = eng.execute_task(spec)
        return receipt.model_dump()
    return adapter


def make_developer_run_tests_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.developer.engine import DeveloperSupervisorEngine
            eng = DeveloperSupervisorEngine()
        repo_path = str(kwargs.get("repo_path") or "")
        test_commands = list(kwargs.get("test_commands") or [])
        timeout = float(kwargs.get("timeout_seconds", 30.0))
        receipt = eng.run_tests(repo_path, test_commands, timeout_seconds=timeout)
        return receipt.model_dump()
    return adapter


def make_developer_git_diff_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.developer.engine import DeveloperSupervisorEngine
            eng = DeveloperSupervisorEngine()
        repo_path = str(kwargs.get("repo_path") or "")
        target_files = list(kwargs.get("target_files") or []) or None
        diff = eng.get_diff(repo_path, target_files)
        return {"diff": diff, "repo_path": repo_path}
    return adapter


def make_developer_inspect_code_adapter(engine_instance: Any = None):
    def adapter(**kwargs) -> Dict[str, Any]:
        eng = engine_instance
        if eng is None:
            from omni_engine.developer.engine import DeveloperSupervisorEngine
            eng = DeveloperSupervisorEngine()
        repo_path = str(kwargs.get("repo_path") or "")
        file_path = str(kwargs.get("file_path") or "")
        return eng.inspect_file(repo_path, file_path)
    return adapter


def register_developer_capabilities(registry: CapabilityRegistry, engine: Any = None) -> None:
    """Registers all developer capabilities and dotless aliases."""
    # 1. run_task
    task_ad = make_developer_run_task_adapter(engine)
    registry.register(spec=DEVELOPER_RUN_TASK_SPEC, implementation=task_ad)
    registry.register(
        spec=DEVELOPER_RUN_TASK_SPEC.model_copy(update={"id": "developer_run_task"}),
        implementation=task_ad,
    )

    # 2. run_tests
    test_ad = make_developer_run_tests_adapter(engine)
    registry.register(spec=DEVELOPER_RUN_TESTS_SPEC, implementation=test_ad)
    registry.register(
        spec=DEVELOPER_RUN_TESTS_SPEC.model_copy(update={"id": "developer_run_tests"}),
        implementation=test_ad,
    )

    # 3. git_diff
    diff_ad = make_developer_git_diff_adapter(engine)
    registry.register(spec=DEVELOPER_GIT_DIFF_SPEC, implementation=diff_ad)
    registry.register(
        spec=DEVELOPER_GIT_DIFF_SPEC.model_copy(update={"id": "developer_git_diff"}),
        implementation=diff_ad,
    )

    # 4. inspect_code
    inspect_ad = make_developer_inspect_code_adapter(engine)
    registry.register(spec=DEVELOPER_INSPECT_CODE_SPEC, implementation=inspect_ad)
    registry.register(
        spec=DEVELOPER_INSPECT_CODE_SPEC.model_copy(update={"id": "developer_inspect_code"}),
        implementation=inspect_ad,
    )


REAL_CAPABILITY_SPECS: Dict[str, CapabilitySpec] = {
    "deep_research": DEEP_RESEARCH_SPEC,
    "browser_interact": BROWSER_INTERACT_SPEC,
    "desktop.launch_app": DESKTOP_LAUNCH_APP_SPEC,
    "desktop.list_windows": DESKTOP_LIST_WINDOWS_SPEC,
    "desktop.focus_window": DESKTOP_FOCUS_WINDOW_SPEC,
    "desktop.close_window": DESKTOP_CLOSE_WINDOW_SPEC,
    "desktop.service_health": DESKTOP_SERVICE_HEALTH_SPEC,
    "desktop.send_keys": DESKTOP_SEND_KEYS_SPEC,
    "n8n.list_workflows": N8N_LIST_WORKFLOWS_SPEC,
    "n8n.get_workflow": N8N_GET_WORKFLOW_SPEC,
    "n8n.validate_workflow": N8N_VALIDATE_WORKFLOW_SPEC,
    "n8n.create_workflow": N8N_CREATE_WORKFLOW_SPEC,
    "n8n.activate_workflow": N8N_ACTIVATE_WORKFLOW_SPEC,
    "n8n.trigger_workflow": N8N_TRIGGER_WORKFLOW_SPEC,
    "n8n.get_execution_status": N8N_GET_EXECUTION_STATUS_SPEC,
    "developer.run_task": DEVELOPER_RUN_TASK_SPEC,
    "developer.run_tests": DEVELOPER_RUN_TESTS_SPEC,
    "developer.git_diff": DEVELOPER_GIT_DIFF_SPEC,
    "developer.inspect_code": DEVELOPER_INSPECT_CODE_SPEC,
}


def build_real_capability_registry(
    base_registry: Optional[CapabilityRegistry] = None,
    research_engine: Any = None,
    browser_driver: Any = None,
    desktop_driver: Any = None,
    n8n_engine: Any = None,
    developer_engine: Any = None,
) -> CapabilityRegistry:
    """Builds a CapabilityRegistry containing the canonical 23 tools PLUS real capability engines."""
    reg = base_registry or build_canonical_registry()
    register_deep_research_capability(reg, engine=research_engine)
    register_browser_capability(reg, driver=browser_driver)
    register_desktop_capabilities(reg, driver=desktop_driver)
    register_n8n_capabilities(reg, engine=n8n_engine)
    register_developer_capabilities(reg, engine=developer_engine)
    return reg




