# CAPABILITY_CONTRACT.md — Canonical Capability Specification

## 1. Prime Directive for Capabilities
A tool or capability in the LAYA system is NOT a raw Python function accepting arbitrary text.
Every capability MUST expose a canonical `CapabilitySpec` defining:
1. Strict schema validation for inputs and outputs.
2. Explicit action classification and policy requirements.
3. Deterministic outcome verifier.
4. Idempotency and retry semantics.
5. Standardized result envelopes (`ToolResult`).

---

## 2. CapabilitySpec Schema

```python
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

class ActionClass(str, Enum):
    READ_ONLY = "READ_ONLY"
    LOCAL_CREATE = "LOCAL_CREATE"
    LOCAL_UPDATE = "LOCAL_UPDATE"
    LOCAL_DELETE = "LOCAL_DELETE"
    EXTERNAL_CREATE = "EXTERNAL_CREATE"
    EXTERNAL_UPDATE = "EXTERNAL_UPDATE"
    EXTERNAL_SEND = "EXTERNAL_SEND"
    EXTERNAL_DELETE = "EXTERNAL_DELETE"
    SYSTEM_ACTION = "SYSTEM_ACTION"
    SECURITY_SENSITIVE = "SECURITY_SENSITIVE"
    FINANCIAL = "FINANCIAL"

class CapabilitySpec(BaseModel):
    id: str = Field(..., description="Unique capability identifier, e.g. 'os.system_diagnostics'")
    version: str = Field(default="1.0.0")
    name: str = Field(..., description="Human-readable name")
    domain: str = Field(..., description="Capability domain: web, browser, os, dev, data")
    description: str = Field(..., description="Clear description used for routing and documentation")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema / Pydantic definition for arguments")
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    action_class: ActionClass = Field(default=ActionClass.READ_ONLY)
    side_effects: bool = Field(default=False)
    requires_confirmation: bool = Field(default=False)
    idempotent: bool = Field(default=True)
    retryable: bool = Field(default=False)
    timeout_seconds: float = Field(default=15.0)
    availability_check: Optional[Callable[[], bool]] = None
    verifier: Optional[Callable[[Dict[str, Any], "ToolResult"], bool]] = None
    implementation: Callable[..., Any]
```

---

## 3. Standard Result Envelope (`ToolResult`)

Every capability MUST return a structured result envelope. Routine errors must never raise unhandled exceptions.

### Success Envelope
```json
{
  "success": true,
  "data": {
    "output": "Extracted text or structured payload"
  },
  "error": null,
  "observations": [
    "Navigated to https://example.com",
    "Extracted 45 elements"
  ],
  "receipt": {
    "timestamp": 1727052000,
    "duration_ms": 142.5,
    "bytes_read": 4096
  }
}
```

### Error Envelope
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Target file 'config.json' does not exist in workspace.",
    "retryable": false,
    "fix_action": "Check directory tree with 'dev.directory_tree' or create file with 'dev.file_write'."
  },
  "observations": [],
  "receipt": {
    "timestamp": 1727052000,
    "duration_ms": 12.1
  }
}
```

---

## 4. Standard Error Codes

| Error Code | Meaning | Retryable? |
| :--- | :--- | :--- |
| `INVALID_ARGUMENT` | Arguments failed schema validation. | No |
| `NOT_FOUND` | Specified target (file, process, URL) does not exist. | No |
| `PERMISSION_DENIED` | Action blocked by policy, autonomy profile, or OS permissions. | No |
| `CONFIRMATION_REJECTED` | User explicitly declined confirmation prompt. | No |
| `TIMEOUT` | Capability execution exceeded timeout budget. | Yes |
| `NETWORK_ERROR` | Connection failed or DNS resolution failed. | Yes |
| `PROCESS_FAILED` | Executed subprocess returned non-zero exit code. | Contextual |
| `UNKNOWN_COMMIT` | Side-effect mutation state uncertain (e.g. timeout during HTTP POST). | NO (Manual audit required) |
