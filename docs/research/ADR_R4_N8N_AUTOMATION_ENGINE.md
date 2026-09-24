# ADR_R4_N8N_AUTOMATION_ENGINE.md — Programmatic n8n Automation Engine Architecture

## Status
**ACCEPTED (Post Adversarial Plan Review)**

## Context & Problem Statement
In Phase R4 of the LAYA Omni Agent roadmap, the agent requires a native, programmatic automation engine to interface with **n8n** (an open-source node-based workflow automation platform commonly running locally on port 5678 or remotely):
1. **Programmatic Workflow Lifecycle**:
   - Managing workflows via n8n's Public REST API (`/workflows`, `/executions`, `/credentials`, `/nodes`).
   - Preventing blind deployment of malformed or untested workflows via a deterministic **Draft → Validate → Test → Activate** lifecycle.
2. **Graph Validation & Safety**:
   - Validating workflow node graphs prior to deployment (acyclicity check, valid trigger presence, parameter verification, connection integrity).
   - Rejecting infinite loop topologies or orphaned, disconnected nodes.
3. **Zero Leaked Secrets Invariant**:
   - n8n workflows inherently process sensitive third-party credentials (API keys, webhook secrets, database credentials).
   - In accordance with repository safety rules, plaintext secrets must **never** be passed in prompt contexts, stored in workflow definition text, logged in console outputs, or returned in `ToolResult` envelopes. Credentials must strictly be referenced by opaque IDs (`credential_id`).
   - A deterministic `SecretScrubber` must scrub authorization headers and token patterns from all outgoing and incoming payloads.
4. **Evidence-Based Completion (Invariant 6)**:
   - Workflow execution must never be assumed. The agent must poll execution receipts (`execution_id`, `status: "success" | "error" | "running" | "waiting"`, node execution counts, duration, and output data).
5. **Local Service Discovery**:
   - Integrating with `LocalServiceProber` (developed in R3) to check localhost port 5678 readiness before dispatching API calls, with graceful diagnostic feedback if the n8n daemon is offline.

---

## Adversarial Plan Review Remediations (REQ-BLOCK-1 to REQ-BLOCK-7)

| ID | Requirement | Severity | Implementation Architecture |
| :--- | :--- | :--- | :--- |
| **REQ-BLOCK-1** | Lifecycle Gate Triad & Activation Guard | **BLOCKING** | `create_workflow` unconditionally forces `active=False`. Added explicit `n8n.activate_workflow`. Enforces triad before activation: (1) Graph validation passed (`is_valid=True`), (2) Successful execution receipt for current `workflow_hash` recorded, (3) Zero plaintext secrets found. |
| **REQ-BLOCK-2** | n8n 3-Level Connection Parser & Resolver | **BLOCKING** | Topological DFS parses 3-level nested `connections[src]["main"][idx] = [...]`. Resolves both `name` and `id` references; detects self-loops and multi-node cycles via 3-color DFS; flags orphaned unreachable nodes; verifies trigger node `in-degree == 0` and total triggers >= 1. |
| **REQ-BLOCK-3** | Credential Isolation & SecretScrubber | **BLOCKING** | `N8nCredentialReference` strictly requires `id: str` and `name: Optional[str]` with `extra="forbid"`. `SecretScrubber` strips OpenAI, GitHub, AWS, Bearer/Basic, n8n API key, private keys, and generic secrets from headers, dictionaries, and error messages without mangling `$json.*` syntax. Deep pre-flight parameter scan blocks deployment of inline secrets. |
| **REQ-BLOCK-4** | Bounded Polling & "Waiting" State Detection | **BLOCKING** | `trigger_and_wait()` implements exponential backoff (0.2s -> 2.0s cap), bounded timeout (default 30s), immediate exit on terminal states or `"waiting"` state (aborting wait-node stalls), emitting `ToolOutcome.PARTIAL` with `ErrorCode.TIMEOUT` on deadline expiry. |
| **REQ-BLOCK-5** | RCE Defense & Stage 0 Command Defense | **BLOCKING** | `PolicyEngine` Stage 0 and risk assessment inspect n8n node types: flags `executeCommand`, `code`, `ssh` as `LOCAL_SYSTEM` risk (0.85+), requiring confirmation. Runs `scan_embedded_commands()` on `executeCommand` parameters to block Rule-0 forbidden operations (`git reset --hard`, destructive drive wipes). |
| **REQ-BLOCK-6** | Dual Registration & Dotless Aliases | **BLOCKING** | Register canonical `n8n.*` and dotless aliases in `build_real_capability_registry()`. Wire clarification prompts and slot extractors in `resolver.py`. Preserve canonical 23-tool registry invariant. |
| **REQ-BLOCK-7** | Transport Abstraction & Offline Fast Suite | **BLOCKING** | Decouple HTTP networking via `N8nTransport` (ABC). Parameterize `poll_interval` and `sleep_fn`. `tests/test_r4_n8n.py` runs 100% offline via `MockN8nTransport` in <1.5s with zero live server dependencies. |

---

## Architectural Invariants & Safety Floor

| Rule ID | Principle | Specification |
| :--- | :--- | :--- |
| **INV-R4-1** | **Draft-Test-Validate Lifecycle** | Workflows are created in `active=False` draft mode. Promotion to active requires successful graph validation and test execution. |
| **INV-R4-2** | **Zero Plaintext Secrets** | Plaintext tokens (`sk-...`, `ghp_...`, `Bearer ...`) are strictly forbidden in workflow JSON. Node credentials must use vault ID references (`{"id": "..."}`). All API client headers and log outputs pass through `SecretScrubber`. |
| **INV-R4-3** | **Acyclic Graph Integrity** | Workflow node connections are verified via topological DFS cycle detection before registration or test runs. |
| **INV-R4-4** | **Physical Execution Receipts** | Triggering a workflow produces an `execution_id` that is polled until a terminal state (`success`, `error`, `crashed`). Output data and node timings are captured in `N8nExecutionReceipt`. |
| **INV-R4-5** | **Offline Test Isolation** | The engine decouples HTTP transport behind `N8nTransport` (ABC). `tests/test_r4_n8n.py` runs 100% offline in <1.5s via `MockN8nTransport` without requiring an active n8n instance. |
| **INV-R4-6** | **Non-Switching Boundary** | `omni_agent.py` and `omni_engine/planner.py` remain **100% untouched (0 diffs)**. |

---

## Technology Audit & Candidate Evaluation

| Technology | Evaluation | Verdict | Rationale |
| :--- | :--- | :--- | :--- |
| **n8n Public REST API (v1)** | Official programmatic REST API exposed by self-hosted n8n and n8n Cloud (`/api/v1/workflows`, `/api/v1/executions`, `/api/v1/credentials`). Clean JSON interface with standard HTTP verb semantics and API key authentication (`X-N8N-API-KEY`). | **ADOPT** | Universal, documented, native n8n control plane with zero third-party client dependencies. |
| **Standard Library `urllib.request` + `json`** | Python standard library networking with proxy-bypass opener (`ProxyHandler({})`), timeout enforcement, and memory-safe response parsing. | **ADOPT** | Lightweight, zero external package dependencies, easily mocked via abstract transport interface. |
| **`LocalServiceProber` (R3 Engine)** | Developed in R3: Dual-stack TCP loopback cascade (`127.0.0.1` -> `::1`) with `SO_LINGER` socket reset. | **ADOPT** | Provides sub-millisecond instance discovery and health verification for local n8n on port 5678. |
| **Community n8n Python SDKs (e.g. `n8n-python`, `pyn8n`)** | Unofficial community wrappers. | **REJECT** | Unmaintained, outdated API versions, lack pydantic v2 contracts, introduce dependency drift and insecure secret handling. |
| **Direct SQLite Database Mutation (`~/.n8n/database.sqlite`)** | Writing directly to n8n's internal database file. | **REJECT** | Dangerous: Bypasses n8n's in-memory state, encryption keys, and active trigger listeners; risks database corruption. |

---

## Proposed Component Architecture

```
omni_engine/
  contracts/
    n8n.py                 <-- Strongly typed Pydantic v2 contracts with extra="forbid"
  automation/
    __init__.py            <-- Package exports
    scrubber.py            <-- Deterministic SecretScrubber (headers, tokens, credentials)
    validator.py           <-- Workflow graph validator (DFS cycle check, trigger verification)
    transport.py           <-- N8nTransport ABC, HttpN8nTransport, MockN8nTransport
    client.py              <-- N8nClient (REST API endpoints with retry and error envelopes)
    engine.py              <-- N8nAutomationEngine (lifecycle management, local prober, execution polling)
  capabilities/
    definitions.py         <-- n8n.* capability specs, adapters, real registry registration
  arguments/
    resolver.py            <-- n8n slot extraction (workflow_id, workflow_name, payload)
  policy/
    engine.py              <-- ActionClass mapping (READ_ONLY, LOCAL_UPDATE, SYSTEM_ACTION)
```

---

## Contract Schemas (`omni_engine/contracts/n8n.py`)

```python
class N8nTriggerType(str, Enum):
    WEBHOOK = "n8n-nodes-base.webhook"
    SCHEDULE = "n8n-nodes-base.scheduleTrigger"
    MANUAL = "n8n-nodes-base.manualTrigger"
    EVENT = "n8n-nodes-base.eventTrigger"
    OTHER = "other"

class N8nWorkflowSummary(BaseContractModel):
    workflow_id: str
    name: str
    active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class N8nNode(BaseContractModel):
    id: str
    name: str
    type: str
    type_version: float = 1.0
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0])
    parameters: Dict[str, Any] = Field(default_factory=dict)
    credentials: Optional[Dict[str, Any]] = None

class N8nWorkflowDetail(BaseContractModel):
    workflow_id: str
    name: str
    active: bool
    nodes: List[N8nNode] = Field(default_factory=list)
    connections: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    version_id: Optional[str] = None

class N8nWorkflowValidationResult(BaseContractModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    trigger_nodes: List[str] = Field(default_factory=list)
    node_count: int = 0
    has_cycles: bool = False

class N8nExecutionReceipt(BaseContractModel):
    execution_id: str
    workflow_id: str
    status: Literal["success", "error", "running", "waiting", "unknown"]
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    duration_ms: Optional[float] = None
    node_status: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None

class N8nActionResult(BaseContractModel):
    action: str
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    success: bool
    verification_status: VerificationStatus
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    sanitized: bool = True
```
