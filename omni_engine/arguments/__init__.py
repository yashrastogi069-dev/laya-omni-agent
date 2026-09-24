"""
omni_engine.arguments
=====================
Capability argument resolution, extraction sources, and schema validation.
"""

from .resolver import ArgumentResolver, CLARIFICATION_PROMPTS
from .extractors import (
    extract_app_name,
    extract_clipboard_data,
    extract_file_path,
    extract_math_expression,
    extract_pid,
    extract_ping_host,
    extract_powershell_script,
    extract_process_name,
    extract_python_code,
    extract_search_query,
    extract_sql_query,
    extract_url,
)

__all__ = [
    "ArgumentResolver",
    "CLARIFICATION_PROMPTS",
    "extract_app_name",
    "extract_clipboard_data",
    "extract_file_path",
    "extract_math_expression",
    "extract_pid",
    "extract_ping_host",
    "extract_powershell_script",
    "extract_process_name",
    "extract_python_code",
    "extract_search_query",
    "extract_sql_query",
    "extract_url",
]
