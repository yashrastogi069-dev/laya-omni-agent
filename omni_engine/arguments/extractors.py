"""
omni_engine.arguments.extractors
================================
High-precision deterministic extractors for capability arguments using regex,
syntactic parsing, and string normalization.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Fast deterministic extraction (<1ms) precedes generative LLMs.
- Invariant 3: Minimize Generative Model Invocations — Solves routine cases without LLM inference.
- Canonical Schema Parity: Tailored to all 23 source tools in omni_engine.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


# Regex patterns for paths (Windows and POSIX, quoted and unquoted)
RE_QUOTED_STRING = re.compile(r"""['"]([^'"]+)['"]""")
RE_WINDOWS_DRIVE_PATH = re.compile(r"""\b([A-Za-z]:[\\/][^'"><|:\*\?]+?)(?=\s|$|['"])""")
RE_RELATIVE_PATH = re.compile(
    r"""(?:\b|['"])([\w\-\.]+/(?:[\w\-\.]+/)*[\w\-\.]+\.\w+)(?:['"]|\b)"""
)
RE_LOCAL_FILENAME_WITH_EXT = re.compile(
    r"""\b([\w\-]+\.(?:py|json|txt|csv|md|log|db|sqlite|html|js|ts|tar|gz|zip|sh|png|jpg|pdf|xml|yml|yaml))\b""",
    re.IGNORECASE,
)

# Regex patterns for URLs and endpoints
RE_HTTP_URL = re.compile(r"""\b(https?://[^\s"'<>]+)""", re.IGNORECASE)
RE_LOCALHOST_PORT = re.compile(r"""\b(localhost:\d+)\b""", re.IGNORECASE)

# Regex patterns for process identification
RE_PID = re.compile(
    r"""(?:pid|process\s*id|process)\s*[:=]?\s*(\d{1,7})\b""", re.IGNORECASE
)
RE_KILL_COMMAND_PID = re.compile(
    r"""\b(?:kill|terminate|stop)\s+(?:process\s+)?(\d{1,7})\b""", re.IGNORECASE
)
RE_PROCESS_NAME = re.compile(
    r"""\b([\w\-]+\.exe)\b""", re.IGNORECASE
)
KNOWN_PROCESS_NAMES = [
    "node", "python", "python3", "n8n", "chrome", "edge", "firefox",
    "notepad", "calc", "calculator", "powershell", "pwsh", "cmd", "explorer"
]

# Regex patterns for database SQL
RE_SQL_QUERY = re.compile(
    r"""\b(SELECT\s+.+?|INSERT\s+INTO\s+.+?|UPDATE\s+.+?|DELETE\s+FROM\s+.+?|CREATE\s+TABLE\s+.+?|DROP\s+TABLE\s+.+?)(?:;|\s*$|['"])""",
    re.IGNORECASE | re.DOTALL,
)

# Regex patterns for math expressions
RE_MATH_EXPRESSION = re.compile(
    r"""(?:calculate|compute|eval|math(?:\s+expression)?)\s*[:=]?\s*['"]?([0-9\.\s\+\-\*\/\^\(\)\%]{3,})['"]?""",
    re.IGNORECASE,
)
RE_BARE_MATH = re.compile(
    r"""\b(\d+(?:\.\d+)?\s*(?:[\+\-\*\/\^]|\*\*)\s*[\(\)\d\s\+\-\*\/\^\.]+)\b"""
)

# Regex patterns for hosts and IPs
RE_IPV4 = re.compile(r"""\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b""")
RE_DOMAIN_HOST = re.compile(
    r"""\b([a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*(?:\.com|\.org|\.net|\.io|\.dev|\.edu|\.gov|\.ai))\b""",
    re.IGNORECASE,
)


def extract_file_path(text: str) -> Optional[str]:
    """Extracts a file or directory path from natural language text."""
    if not text:
        return None

    # 1. Quoted paths (e.g. 'data/config.json' or "C:\Users\file.txt")
    for match in RE_QUOTED_STRING.finditer(text):
        val = match.group(1).strip()
        if (
            "\\" in val
            or "/" in val
            or RE_LOCAL_FILENAME_WITH_EXT.search(val)
        ):
            return val

    # 2. Windows drive paths (e.g. C:\project\src\main.py)
    win_match = RE_WINDOWS_DRIVE_PATH.search(text)
    if win_match:
        return win_match.group(1).strip()

    # 3. Relative unix-like paths (e.g. src/components/button.tsx)
    rel_match = RE_RELATIVE_PATH.search(text)
    if rel_match:
        return rel_match.group(1).strip()

    # 4. Local filename with known extension (e.g. summary.csv)
    file_match = RE_LOCAL_FILENAME_WITH_EXT.search(text)
    if file_match:
        return file_match.group(1).strip()

    # 5. Look for target after "file" or "path" keyword
    kw_match = re.search(r"""(?:file|path|directory|folder)\s+([^\s,;]+)""", text, re.IGNORECASE)
    if kw_match:
        candidate = kw_match.group(1).strip("'\"")
        if candidate and candidate.lower() not in ["and", "to", "from", "the", "a", "an", "tree", "structure", "hierarchy", "contents", "info", "status"]:
            return candidate

    return None


def extract_url(text: str) -> Optional[str]:
    """Extracts an HTTP/HTTPS URL or localhost endpoint from text."""
    if not text:
        return None

    http_match = RE_HTTP_URL.search(text)
    if http_match:
        url = http_match.group(1).rstrip(".,;'\"")
        return url

    lh_match = RE_LOCALHOST_PORT.search(text)
    if lh_match:
        return f"http://{lh_match.group(1)}"

    return None


def extract_pid(text: str) -> Optional[int]:
    """Extracts numeric process ID (PID) from text."""
    if not text:
        return None

    match = RE_PID.search(text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass

    kill_match = RE_KILL_COMMAND_PID.search(text)
    if kill_match:
        try:
            return int(kill_match.group(1))
        except ValueError:
            pass

    return None


def extract_process_name(text: str) -> Optional[str]:
    """Extracts process executable name or process filter from text."""
    if not text:
        return None

    exe_match = RE_PROCESS_NAME.search(text)
    if exe_match:
        return exe_match.group(1)

    text_lower = text.lower()
    for proc in KNOWN_PROCESS_NAMES:
        if re.search(r"\b" + re.escape(proc) + r"\b", text_lower):
            return proc

    # Look for "process <name>"
    proc_kw = re.search(r"""process\s+([a-zA-Z0-9_\-]+)""", text, re.IGNORECASE)
    if proc_kw:
        cand = proc_kw.group(1).strip()
        if cand.lower() not in ["id", "pid", "named", "called", "the", "a"]:
            return cand

    return None


def extract_app_name(text: str) -> Optional[str]:
    """Extracts desktop application or service name for launch_app."""
    if not text:
        return None

    # Explicit app launch patterns: "launch calc", "open notepad", "start n8n"
    match = re.search(
        r"""(?:launch|open|start|run)\s+(?:app|application|program|service)?\s*['"]?([a-zA-Z0-9_\-\.]+)['"]?""",
        text,
        re.IGNORECASE,
    )
    if match:
        cand = match.group(1).strip()
        if cand.lower() not in ["the", "a", "an", "browser", "file", "url", "code"]:
            return cand

    text_lower = text.lower()
    for app in ["calculator", "calc", "notepad", "n8n", "powershell", "cmd", "terminal", "paint"]:
        if re.search(r"\b" + re.escape(app) + r"\b", text_lower):
            return app

    return None


def extract_sql_query(text: str) -> Optional[str]:
    """Extracts SQL query string from text."""
    if not text:
        return None

    # Check for quoted query: "SELECT * FROM users"
    for match in RE_QUOTED_STRING.finditer(text):
        val = match.group(1).strip()
        if re.match(r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|PRAGMA)\b", val, re.IGNORECASE):
            return val

    # Direct SQL pattern in unquoted prompt
    sql_match = RE_SQL_QUERY.search(text)
    if sql_match:
        return sql_match.group(1).strip()

    return None


def extract_math_expression(text: str) -> Optional[str]:
    """Extracts mathematical arithmetic expression for safe_math."""
    if not text:
        return None

    # Explicit calculate/compute prefix
    match = RE_MATH_EXPRESSION.search(text)
    if match:
        expr = match.group(1).strip().rstrip(".,;?'\"")
        return expr

    # Bare math pattern (e.g. 2 ** 32 / (1024 * 1024))
    bare_match = RE_BARE_MATH.search(text)
    if bare_match:
        expr = bare_match.group(1).strip().rstrip(".,;?'\"")
        return expr

    return None


def extract_powershell_script(text: str) -> Optional[str]:
    """Extracts PowerShell command or script string."""
    if not text:
        return None

    # Quoted script after powershell: powershell 'Get-Process'
    match = re.search(
        r"""(?:powershell|pwsh|shell|run\s+command)\s*[:=]?\s*['"]([^'"]+)['"]""",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    # Unquoted command following powershell keyword: "run powershell Get-Service"
    kw_match = re.search(
        r"""(?:powershell|pwsh)\s+(.+)""",
        text,
        re.IGNORECASE,
    )
    if kw_match:
        return kw_match.group(1).strip()

    return None


def extract_python_code(text: str) -> Optional[str]:
    """Extracts Python code string for run_python."""
    if not text:
        return None

    # Markdown fenced code block ```python ... ```
    fence_match = re.search(r"""```(?:python)?\s*\n(.*?)\n```""", text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()

    # Quoted code string: run_python 'print("hello")'
    match = re.search(r"""(?:run_python|python(?:\s+code)?)\s*[:=]?\s*['"]([^'"]+)['"]""", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Look for inline python print or expression
    inline_match = re.search(r"""\b(print\s*\(.*?\))""", text)
    if inline_match:
        return inline_match.group(1)

    return None


def extract_search_query(text: str) -> Optional[str]:
    """Extracts search keywords for web search or code search."""
    if not text:
        return None

    # Quoted query: search for "ModernBERT large"
    for match in RE_QUOTED_STRING.finditer(text):
        cand = match.group(1).strip()
        if len(cand) >= 2:
            return cand

    # Pattern: search [the web] for <query>
    match = re.search(
        r"""(?:search(?:\s+the\s+web|\s+tavily|\s+code|\s+google)?\s+for|google\s+for|find\s+pattern)\s+(.+)""",
        text,
        re.IGNORECASE,
    )
    if match:
        query = match.group(1).strip().rstrip(".,;?'\"")
        return query

    return None


def extract_ping_host(text: str) -> Optional[str]:
    """Extracts target host or IP for ping_test."""
    if not text:
        return None

    ip_match = RE_IPV4.search(text)
    if ip_match:
        return ip_match.group(1)

    domain_match = RE_DOMAIN_HOST.search(text)
    if domain_match:
        return domain_match.group(1)

    # Look for "ping <host>"
    match = re.search(r"""\bping\s+([a-zA-Z0-9_\-\.]+)""", text, re.IGNORECASE)
    if match:
        cand = match.group(1).strip()
        if cand.lower() not in ["test", "host", "the", "a"]:
            return cand

    return None


def extract_clipboard_data(text: str) -> Tuple[str, Optional[str]]:
    """Determines clipboard action ('read' vs 'write') and text payload."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["read", "view", "paste", "get", "show"]):
        return "read", None

    # Write action: extract text to write
    quoted = RE_QUOTED_STRING.search(text)
    if quoted:
        return "write", quoted.group(1).strip()

    match = re.search(r"""(?:copy|write|set\s+clipboard)\s+(?:text\s+)?(.+)""", text, re.IGNORECASE)
    if match:
        return "write", match.group(1).strip().rstrip(".,;?'\"")

    return "read", None
