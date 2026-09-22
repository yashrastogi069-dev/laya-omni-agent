"""
OmniTool Registry: Unified index of all tools across Web, Browser, OS, Dev, and Data.
"""

from .web_tools import (
    tool_web_search,
    tool_scrape_url_content,
    tool_http_api_request,
    tool_download_file,
)
from .browser_tools import (
    tool_visual_browse,
    tool_browser_screenshot,
)
from .os_tools import (
    tool_system_diagnostics,
    tool_list_processes,
    tool_kill_process,
    tool_launch_app,
    tool_desktop_screenshot,
    tool_clipboard,
    tool_powershell,
    tool_ping_test,
)
from .dev_tools import (
    tool_file_read,
    tool_file_write,
    tool_search_code,
    tool_directory_tree,
    tool_run_python,
    tool_git_status,
)
from .data_tools import (
    tool_sqlite_exec,
    tool_inspect_data,
    tool_safe_math,
)

OMNI_TOOL_REGISTRY = {
    # 1. Live Web & Internet
    "web_search": {
        "func": tool_web_search,
        "desc": "Search the live internet for recent news, facts, current events, or topics",
        "category": "web"
    },
    "scrape_url": {
        "func": tool_scrape_url_content,
        "desc": "Fetch and extract text content from any website URL",
        "category": "web"
    },
    "http_api": {
        "func": tool_http_api_request,
        "desc": "Send GET or POST REST API requests to web endpoints",
        "category": "web"
    },
    "download_file": {
        "func": tool_download_file,
        "desc": "Download images, PDFs, datasets, or files from any URL",
        "category": "web"
    },

    # 2. Visual Browser Automation
    "visual_browse": {
        "func": tool_visual_browse,
        "desc": "Open Edge full-screen to visually browse websites, click, and extract live data",
        "category": "browser"
    },
    "browser_screenshot": {
        "func": tool_browser_screenshot,
        "desc": "Capture screenshot of a live webpage in Microsoft Edge",
        "category": "browser"
    },

    # 3. Windows OS & Desktop
    "system_diagnostics": {
        "func": tool_system_diagnostics,
        "desc": "Check real-time CPU, RAM, Disk space, network activity, and uptime",
        "category": "os"
    },
    "list_processes": {
        "func": tool_list_processes,
        "desc": "Inspect running Windows processes and identify memory/CPU usage",
        "category": "os"
    },
    "kill_process": {
        "func": tool_kill_process,
        "desc": "Terminate a hung or misbehaving process by PID or name",
        "category": "os"
    },
    "launch_app": {
        "func": tool_launch_app,
        "desc": "Launch desktop apps like Notepad, Calculator, VS Code, Spotify, Settings",
        "category": "os"
    },
    "desktop_screenshot": {
        "func": tool_desktop_screenshot,
        "desc": "Take a full-resolution screenshot of the Windows desktop",
        "category": "os"
    },
    "clipboard": {
        "func": tool_clipboard,
        "desc": "Read current clipboard content or copy text to Windows clipboard",
        "category": "os"
    },
    "powershell": {
        "func": tool_powershell,
        "desc": "Execute Windows PowerShell terminal commands or scripts",
        "category": "os"
    },
    "ping_test": {
        "func": tool_ping_test,
        "desc": "Test network latency and ping connectivity to remote host",
        "category": "os"
    },

    # 4. Developer & Code
    "file_read": {
        "func": tool_file_read,
        "desc": "Read content from local code, text files, or configurations",
        "category": "dev"
    },
    "file_write": {
        "func": tool_file_write,
        "desc": "Create, overwrite, or update code or text files on disk",
        "category": "dev"
    },
    "search_code": {
        "func": tool_search_code,
        "desc": "Search codebase for keywords, functions, or file names",
        "category": "dev"
    },
    "directory_tree": {
        "func": tool_directory_tree,
        "desc": "View hierarchical folder and directory structure",
        "category": "dev"
    },
    "run_python": {
        "func": tool_run_python,
        "desc": "Dynamically execute Python code for algorithms, calculations, or data tasks",
        "category": "dev"
    },
    "git_status": {
        "func": tool_git_status,
        "desc": "Inspect git version control status, changes, and active branch",
        "category": "dev"
    },

    # 5. Data Science & Database
    "sqlite_exec": {
        "func": tool_sqlite_exec,
        "desc": "Execute SQL queries on local SQLite database",
        "category": "data"
    },
    "inspect_data": {
        "func": tool_inspect_data,
        "desc": "Inspect CSV or JSON datasets, schemas, and preview records",
        "category": "data"
    },
    "safe_math": {
        "func": tool_safe_math,
        "desc": "Evaluate mathematical, arithmetic, and algebraic calculations",
        "category": "data"
    },
}
