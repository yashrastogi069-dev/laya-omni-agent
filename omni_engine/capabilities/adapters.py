"""
omni_engine.capabilities.adapters
=================================
Typed argument adapters and prefix-anchored error interceptors for all 23 source tools.

Bridges strongly typed argument dictionaries conforming to CapabilitySpec.input_schema
to legacy tool implementations (normalizing parameter names and formats), and intercepts
legacy error strings without false-positive masking on content-bearing tools (like file_read
or search_code).
"""

from typing import Any, Callable, Dict, Optional, Tuple

from omni_engine.contracts.enums import ErrorCode
from omni_engine.contracts.capability import ToolError


def build_error(
    code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    retryable: bool = False,
    fix_action: Optional[str] = None,
) -> ToolError:
    return ToolError(
        code=code,
        message=message,
        details=details or {},
        retryable=retryable,
        fix_action=fix_action,
    )


# ---------------------------------------------------------------------------
# Error String Interceptors (Prefix-Anchored & Capability-Scoped)
# ---------------------------------------------------------------------------

def intercept_legacy_error_string(raw: str, capability_id: str) -> Optional[ToolError]:
    """Inspects raw string output from legacy tools for known failure signatures.
    
    Uses prefix-anchored checks to eliminate false positives on tools returning arbitrary
    text (e.g. file_read, search_code, powershell).
    """
    if not isinstance(raw, str):
        return None

    raw_clean = raw.strip()

    # 1. File Read & Inspect Data: Not Found
    if raw_clean.startswith("❌ File not found:") or (raw_clean.startswith("File '") and "does not exist." in raw_clean):
        return build_error(
            ErrorCode.NOT_FOUND,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Verify target path existence using 'dev.directory_tree'.",
        )

    # 2. Directory Tree: Path not found
    if raw_clean.startswith("Path '") and "does not exist." in raw_clean:
        return build_error(
            ErrorCode.NOT_FOUND,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Verify parent path or create folder.",
        )

    # 3. Kill Process Failures
    if raw_clean.startswith("Failed to terminate process:"):
        if "process PID not found" in raw_clean or "No process named" in raw_clean or "no longer exists" in raw_clean:
            return build_error(
                ErrorCode.NOT_FOUND,
                raw_clean,
                {"capability_id": capability_id, "raw_output": raw_clean},
                retryable=False,
                fix_action="Verify active processes using 'os.list_processes'.",
            )
        if "[Errno 13] Access is denied" in raw_clean or "Access is denied" in raw_clean:
            return build_error(
                ErrorCode.PERMISSION_DENIED,
                raw_clean,
                {"capability_id": capability_id, "raw_output": raw_clean},
                retryable=False,
                fix_action="Elevation or administrative OS permissions required to terminate this process.",
            )
        return build_error(
            ErrorCode.PROCESS_FAILED,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Check process state or target identifier.",
        )

    # 4. Web Search / API: Unconfigured Credentials
    if raw_clean.startswith("TAVILY_API_KEY is not configured"):
        return build_error(
            ErrorCode.UNCONFIGURED,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Set TAVILY_API_KEY environment variable.",
        )

    # 5. Invalid Arguments & Math Errors
    if raw_clean.startswith("❌ Format error:") or raw_clean.startswith("Please specify URL to download"):
        return build_error(
            ErrorCode.INVALID_ARGUMENT,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Provide required arguments conforming to schema.",
        )
    if raw_clean.startswith("Math calculation error:"):
        return build_error(
            ErrorCode.INVALID_ARGUMENT,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Check mathematical syntax, division by zero, or exponent bounds.",
        )
    if raw_clean.startswith("Unsupported format for inspector"):
        return build_error(
            ErrorCode.INVALID_ARGUMENT,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Target file must be a .csv or .json dataset.",
        )

    # 6. Network / Connectivity Failures
    if (
        raw_clean.startswith("Failed to scrape")
        or raw_clean.startswith("Download error:")
        or raw_clean.startswith("HTTP request failed:")
        or raw_clean.startswith("Ping test error:")
        or raw_clean.startswith("Ping failed:")
        or raw_clean.startswith("Web search error:")
    ):
        return build_error(
            ErrorCode.NETWORK_ERROR,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=True,
            fix_action="Check internet connectivity or target endpoint availability.",
        )

    # 7. Subprocess / OS Execution Failures
    if (
        raw_clean.startswith("PowerShell error:")
        or raw_clean.startswith("Python execution error:")
        or raw_clean.startswith("Failed to launch")
        or raw_clean.startswith("Failed to take screenshot")
        or raw_clean.startswith("Screenshot error:")
        or raw_clean.startswith("Edge visual browsing error:")
        or raw_clean.startswith("SQLite error:")
        or raw_clean.startswith("Search error:")
        or raw_clean.startswith("Error reading directory:")
        or raw_clean.startswith("Data inspection error:")
        or raw_clean.startswith("Clipboard error:")
        or raw_clean.startswith("Error reading file:")
        or raw_clean.startswith("Write error:")
        or raw_clean.startswith("Error writing file:")
        or raw_clean.startswith("Git error:")
        or raw_clean.startswith("⚠️ Desktop grab unavailable")
    ):
        return build_error(
            ErrorCode.PROCESS_FAILED,
            raw_clean,
            {"capability_id": capability_id, "raw_output": raw_clean},
            retryable=False,
            fix_action="Inspect parameters, local environment, or error message details.",
        )

    return None


# ---------------------------------------------------------------------------
# Specialized Tool Adapters (Normalizing All Kwarg Discrepancies)
# ---------------------------------------------------------------------------

def make_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Generic adapter for tools where kwargs already match the underlying function."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        raw_output = raw_func(**kwargs)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output}
    return adapted_callable


def make_visual_browse_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'url' -> tool_visual_browse(url_or_query)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        url = kwargs.get("url") or kwargs.get("url_or_query") or ""
        raw_output = raw_func(url_or_query=url)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "url": url}
    return adapted_callable


def make_list_processes_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'filter_name' -> tool_list_processes(filter_query)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        filter_query = kwargs.get("filter_name") or kwargs.get("filter_query") or ""
        raw_output = raw_func(filter_query=filter_query)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "filter_name": filter_query}
    return adapted_callable


def make_kill_process_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'target' -> tool_kill_process(pid_or_name)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        target = kwargs.get("target") or kwargs.get("pid_or_name") or ""
        if not target:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'target' is required.")
        raw_output = raw_func(pid_or_name=str(target))
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "target": target}
    return adapted_callable


def make_search_code_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'query' (and optional 'path') -> tool_search_code(query)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        query = kwargs.get("query") or ""
        if not query:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'query' is required.")
        raw_output = raw_func(query=query)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "query": query}
    return adapted_callable


def make_directory_tree_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'path' -> tool_directory_tree(folder)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        folder = kwargs.get("path") or kwargs.get("folder") or ""
        raw_output = raw_func(folder=folder)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "path": folder}
    return adapted_callable


def make_run_python_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'code' -> tool_run_python(code_snippet)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        code = kwargs.get("code") or kwargs.get("code_snippet") or ""
        if not code:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'code' is required.")
        raw_output = raw_func(code_snippet=code)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output}
    return adapted_callable


def make_sqlite_exec_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'query' -> tool_sqlite_exec(sql_query)."""
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        sql_query = kwargs.get("query") or kwargs.get("sql_query") or ""
        if not sql_query:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'query' is required.")
        raw_output = raw_func(sql_query=sql_query)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "query": sql_query}
    return adapted_callable


def make_file_write_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        filepath = kwargs.get("filepath") or kwargs.get("path")
        content = kwargs.get("content", "")
        if not filepath:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'filepath' is required.")
        payload = f"{filepath} ::: {content}"
        raw_output = raw_func(payload)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "filepath": filepath, "bytes_written": len(content.encode("utf-8"))}
    return adapted_callable


def make_http_api_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        url = kwargs.get("url")
        if not url:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'url' is required.")
        method = kwargs.get("method", "GET").upper()
        body = kwargs.get("body")
        payload = f"{method} {url}"
        if body:
            payload += f" {body}"
        raw_output = raw_func(payload)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "method": method, "url": url}
    return adapted_callable


def make_download_file_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        url = kwargs.get("url")
        if not url:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'url' is required.")
        filename = kwargs.get("filename")
        payload = f"{url} {filename}" if filename else url
        raw_output = raw_func(payload)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "url": url}
    return adapted_callable


def make_clipboard_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        action = kwargs.get("action", "read").lower()
        text = kwargs.get("text", "")
        payload = f"copy {text}" if action == "copy" else ""
        raw_output = raw_func(payload)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "action": action}
    return adapted_callable


def make_inspect_data_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        file_path = kwargs.get("file_path") or kwargs.get("filepath")
        if not file_path:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'file_path' is required.")
        raw_output = raw_func(file_path=file_path)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        return True, {"output": raw_output, "file_path": file_path}
    return adapted_callable


def make_safe_math_adapter(raw_func: Callable[..., Any], capability_id: str) -> Callable[..., Tuple[bool, Any]]:
    """Maps schema 'expression' -> tool_safe_math(expression) and extracts numeric result."""
    import re

    def adapted_callable(**kwargs: Any) -> Tuple[bool, Any]:
        expr = kwargs.get("expression") or ""
        if not expr:
            return False, build_error(ErrorCode.INVALID_ARGUMENT, "Parameter 'expression' is required.")
        raw_output = raw_func(expression=expr)
        err = intercept_legacy_error_string(raw_output, capability_id)
        if err is not None:
            return False, err
        result = None
        m = re.search(r"\*\*(.+?)\*\*", raw_output)
        if m:
            val_str = m.group(1).strip()
            try:
                if "." in val_str:
                    result = float(val_str)
                else:
                    result = int(val_str)
            except ValueError:
                result = val_str
        return True, {"output": raw_output, "result": result, "expression": expr}
    return adapted_callable
