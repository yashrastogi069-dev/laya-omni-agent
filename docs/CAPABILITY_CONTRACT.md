# CAPABILITY_CONTRACT.md — Canonical Capability Specification

## 1. Prime Directive for Capabilities
A tool or capability in the LAYA system is NOT a raw Python function accepting arbitrary text.
Every capability MUST expose a canonical `CapabilitySpec` defining:
1. Strict schema validation for inputs and outputs via Pydantic (`extra="forbid"`).
2. Explicit action classification and policy requirements (`minimum_autonomy_profile`, `confirmation_policy`).
3. Idempotency class (`IdempotencyClass`) and retry policy (`RetryPolicy`).
4. Deterministic outcome verifiers and evidence receipts.
5. Standardized result envelopes (`ToolResult`) with structured error envelopes (`ToolError`).

---

## 2. CapabilitySpec Schema

```python
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import Field
from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import (
    ActionClass,
    AutonomyProfile,
    ConfirmationPolicy,
    RetryPolicy,
    IdempotencyClass,
)

class CapabilitySpec(BaseContractModel):
    id: str = Field(..., description="Unique capability identifier, e.g. 'os.system_diagnostics'")
    version: str = Field(default="1.0.0", description="Semantic version of capability contract")
    schema_version: str = Field(default="1.0.0", description="Version of contract schema definition")
    name: str = Field(..., description="Human-readable name")
    domain: str = Field(..., description="Capability domain: web, browser, os, dev, data")
    description: str = Field(..., description="Clear description used for routing and documentation")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for arguments")
    output_schema: Dict[str, Any] = Field(default_factory=dict, description="JSON Schema for output data")
    action_class: ActionClass = Field(default=ActionClass.READ_ONLY)
    side_effects: bool = Field(default=False)
    minimum_autonomy_profile: AutonomyProfile = Field(default=AutonomyProfile.SAFE_ASSISTANT)
    confirmation_policy: ConfirmationPolicy = Field(default=ConfirmationPolicy.POLICY_CONTROLLED)
    retry_policy: RetryPolicy = Field(default=RetryPolicy.NEVER)
    idempotency_class: IdempotencyClass = Field(default=IdempotencyClass.READ_ONLY)
    timeout_seconds: float = Field(default=15.0, ge=0.1)
```

---

## 3. Standard Result Envelope (`ToolResult`)

Every capability MUST return a structured result envelope. Routine errors must never raise unhandled exceptions.

### Schema:
```python
class ToolResult(BaseContractModel):
    outcome: ToolOutcome = Field(default=ToolOutcome.SUCCESS)
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[ToolError] = None
    receipt: Optional[ExecutionReceipt] = None
    verification: Optional[VerificationResult] = None
```

### Outcome Invariants:
- `outcome == SUCCESS`: Requires `success=True`, `error=None`, and `data` present.
- `outcome == FAILURE`: Requires `success=False` and `error` present.
- `outcome == PARTIAL`: Requires `success=False`, `error` present (detailing failure), and allows partial `data`.

---

## 4. Canonical 19-Member Error Taxonomy (`ErrorCode`)

| Error Code | Category | Meaning | Retryable? |
| :--- | :--- | :--- | :--- |
| `UNKNOWN` | Validation | Unclassified or unexpected error | No |
| `INVALID_ARGUMENT` | Validation | Arguments failed validation or boundary bounds | No |
| `SCHEMA_VIOLATION` | Validation | Payload violates JSON/Pydantic schema contract | No |
| `UNCONFIGURED` | Configuration | Required environment variable or credential missing | No |
| `AUTH_REQUIRED` | Configuration | Authentication required or expired | No |
| `PERMISSION_DENIED` | Policy/OS | OS, filesystem, or remote endpoint rejected valid action | No |
| `UNAUTHORIZED_ACTION` | Policy/Internal | LAYA internal policy or autonomy profile refused action | No |
| `CONFIRMATION_REJECTED` | Policy/Human | User explicitly declined interactive confirmation gate | No |
| `NOT_FOUND` | Resource State | Specified file, process, URL, or resource missing | No |
| `ALREADY_EXISTS` | Resource State | Target file, directory, or entity already exists | No |
| `CONFLICT` | Resource State | Resource locked or concurrent conflict detected | No |
| `RATE_LIMITED` | Transient/Network | Downstream provider or rate limiter throttled request | Yes |
| `TIMEOUT` | Transient/Network | Execution exceeded allocated timeout budget | Yes |
| `NETWORK_ERROR` | Transient/Network | Connection failed, socket error, or DNS glitch | Yes |
| `SERVICE_UNAVAILABLE` | Transient/Network | Downstream API returned 503 or transient outage | Yes |
| `PROCESS_FAILED` | Execution | Executed subprocess exited with non-zero code | Contextual |
| `CANCELLED` | Execution | Execution cancelled by deadline manager or user | No |
| `UNKNOWN_COMMIT` | Critical | Mutation state uncertain; manual audit required | **NO (NEVER blind retry)** |
| `INTERNAL_ERROR` | Critical | Engine invariant breach or unhandled runtime bug | No |

### Crucial Semantic Invariant:
- `PERMISSION_DENIED` represents **external rejection** (OS permission, filesystem `EACCES`, remote HTTP 403).
- `UNAUTHORIZED_ACTION` represents **internal LAYA refusal** (autonomy profile gate or safety policy refusal).

---

## 5. Authoritative 23-Tool Source Registry

| Domain | Tool ID | Implementation Function | Blast Radius |
| :--- | :--- | :--- | :--- |
| **web** | `web_search` | `tool_web_search` | `READ_ONLY` |
| **web** | `scrape_url` | `tool_scrape_url_content` | `EXTERNAL_READ` |
| **web** | `http_api` | `tool_http_api_request` | `EXTERNAL_CREATE` / `READ` |
| **web** | `download_file` | `tool_download_file` | `LOCAL_CREATE` |
| **browser** | `visual_browse` | `tool_visual_browse` | `EXTERNAL_READ` / `SYSTEM` |
| **browser** | `browser_screenshot` | `tool_browser_screenshot` | `LOCAL_CREATE` |
| **os** | `system_diagnostics` | `tool_system_diagnostics` | `READ_ONLY` |
| **os** | `list_processes` | `tool_list_processes` | `READ_ONLY` |
| **os** | `kill_process` | `tool_kill_process` | `SYSTEM_ACTION` |
| **os** | `launch_app` | `tool_launch_app` | `SYSTEM_ACTION` |
| **os** | `desktop_screenshot` | `tool_desktop_screenshot` | `LOCAL_CREATE` |
| **os** | `clipboard` | `tool_clipboard` | `LOCAL_UPDATE` / `READ` |
| **os** | `powershell` | `tool_powershell` | `SYSTEM_ACTION` |
| **os** | `ping_test` | `tool_ping_test` | `EXTERNAL_READ` |
| **dev** | `file_read` | `tool_file_read` | `READ_ONLY` |
| **dev** | `file_write` | `tool_file_write` | `LOCAL_CREATE` / `UPDATE` |
| **dev** | `search_code` | `tool_search_code` | `READ_ONLY` |
| **dev** | `directory_tree` | `tool_directory_tree` | `READ_ONLY` |
| **dev** | `run_python` | `tool_run_python` | `SYSTEM_ACTION` |
| **dev** | `git_status` | `tool_git_status` | `READ_ONLY` |
| **data** | `sqlite_exec` | `tool_sqlite_exec` | `LOCAL_UPDATE` / `READ` |
| **data** | `inspect_data` | `tool_inspect_data` | `READ_ONLY` |
| **data** | `safe_math` | `tool_safe_math` | `READ_ONLY` |
