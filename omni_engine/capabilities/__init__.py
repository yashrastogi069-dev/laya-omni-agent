"""
omni_engine.capabilities
========================
Canonical capability substrate package for LAYA Omni Agent.

Provides strongly typed CapabilityRegistry, pure CapabilitySpecs,
adapters, and execution boundaries for all 23 source capabilities.
"""

from .registry import CapabilityRegistry
from .definitions import (
    CANONICAL_SPECS,
    DEEP_RESEARCH_SPEC,
    BROWSER_INTERACT_SPEC,
    DESKTOP_LAUNCH_APP_SPEC,
    DESKTOP_LIST_WINDOWS_SPEC,
    DESKTOP_FOCUS_WINDOW_SPEC,
    DESKTOP_CLOSE_WINDOW_SPEC,
    DESKTOP_SERVICE_HEALTH_SPEC,
    DESKTOP_SEND_KEYS_SPEC,
    N8N_LIST_WORKFLOWS_SPEC,
    N8N_GET_WORKFLOW_SPEC,
    N8N_VALIDATE_WORKFLOW_SPEC,
    N8N_CREATE_WORKFLOW_SPEC,
    N8N_ACTIVATE_WORKFLOW_SPEC,
    N8N_TRIGGER_WORKFLOW_SPEC,
    N8N_GET_EXECUTION_STATUS_SPEC,
    DEVELOPER_RUN_TASK_SPEC,
    DEVELOPER_RUN_TESTS_SPEC,
    DEVELOPER_GIT_DIFF_SPEC,
    DEVELOPER_INSPECT_CODE_SPEC,
    REAL_CAPABILITY_SPECS,
    build_canonical_registry,
    build_real_capability_registry,
    make_deep_research_adapter,
    make_browser_interact_adapter,
    register_deep_research_capability,
    register_browser_capability,
    register_desktop_capabilities,
    register_n8n_capabilities,
    register_developer_capabilities,
)
from .adapters import (
    intercept_legacy_error_string,
    make_adapter,
    make_file_write_adapter,
    make_http_api_adapter,
    make_download_file_adapter,
    make_clipboard_adapter,
    make_inspect_data_adapter,
)

__all__ = [
    "CapabilityRegistry",
    "CANONICAL_SPECS",
    "DEEP_RESEARCH_SPEC",
    "BROWSER_INTERACT_SPEC",
    "DESKTOP_LAUNCH_APP_SPEC",
    "DESKTOP_LIST_WINDOWS_SPEC",
    "DESKTOP_FOCUS_WINDOW_SPEC",
    "DESKTOP_CLOSE_WINDOW_SPEC",
    "DESKTOP_SERVICE_HEALTH_SPEC",
    "DESKTOP_SEND_KEYS_SPEC",
    "N8N_LIST_WORKFLOWS_SPEC",
    "N8N_GET_WORKFLOW_SPEC",
    "N8N_VALIDATE_WORKFLOW_SPEC",
    "N8N_CREATE_WORKFLOW_SPEC",
    "N8N_ACTIVATE_WORKFLOW_SPEC",
    "N8N_TRIGGER_WORKFLOW_SPEC",
    "N8N_GET_EXECUTION_STATUS_SPEC",
    "DEVELOPER_RUN_TASK_SPEC",
    "DEVELOPER_RUN_TESTS_SPEC",
    "DEVELOPER_GIT_DIFF_SPEC",
    "DEVELOPER_INSPECT_CODE_SPEC",
    "REAL_CAPABILITY_SPECS",
    "build_canonical_registry",
    "build_real_capability_registry",
    "intercept_legacy_error_string",
    "make_adapter",
    "make_deep_research_adapter",
    "make_browser_interact_adapter",
    "register_deep_research_capability",
    "register_browser_capability",
    "register_desktop_capabilities",
    "register_n8n_capabilities",
    "register_developer_capabilities",
    "make_file_write_adapter",
    "make_http_api_adapter",
    "make_download_file_adapter",
    "make_clipboard_adapter",
    "make_inspect_data_adapter",
]


