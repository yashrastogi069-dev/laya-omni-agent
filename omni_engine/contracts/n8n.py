"""n8n Automation Engine Contracts for LAYA Omni Agent.

Defines strongly typed Pydantic models for n8n workflows, nodes,
graph validation, execution receipts, and action envelopes under Invariants 4 & 6.
"""

from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Literal, Optional
from pydantic import Field, ConfigDict

from omni_engine.contracts.base import BaseContractModel
from omni_engine.contracts.enums import VerificationStatus


class N8nTriggerType(str, Enum):
    """Canonical n8n trigger node types."""
    WEBHOOK = "n8n-nodes-base.webhook"
    SCHEDULE = "n8n-nodes-base.scheduleTrigger"
    MANUAL = "n8n-nodes-base.manualTrigger"
    EVENT = "n8n-nodes-base.eventTrigger"
    CRON = "n8n-nodes-base.cron"
    OTHER = "other"


class N8nCredentialReference(BaseContractModel):
    """Opaque credential reference in n8n nodes.
    
    REQ-BLOCK-3: Forbids extra fields like token, apiKey, password,
    strictly preventing inline plaintext credentials.
    """
    id: str = Field(..., description="Opaque credential ID in n8n vault")
    name: Optional[str] = Field(default=None, description="Optional human-readable label")


class N8nNode(BaseContractModel):
    """Typed representation of an n8n workflow node."""
    id: str = Field(..., description="Unique node ID (UUID or string)")
    name: str = Field(..., description="Unique node display name used in connections")
    type: str = Field(..., description="Node type identifier, e.g. 'n8n-nodes-base.httpRequest'")
    type_version: float = Field(default=1.0, description="Version of the node definition")
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0], description="Canvas coordinates [x, y]")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Node configuration parameters")
    credentials: Optional[Dict[str, N8nCredentialReference]] = Field(
        default=None, description="Vault credential references keyed by credential type"
    )


class N8nWorkflowSummary(BaseContractModel):
    """Brief metadata summary of an n8n workflow."""
    workflow_id: str = Field(..., description="n8n workflow identifier")
    name: str = Field(..., description="Workflow title")
    active: bool = Field(default=False, description="Whether the workflow is actively listening")
    created_at: Optional[str] = Field(default=None, description="ISO timestamp of creation")
    updated_at: Optional[str] = Field(default=None, description="ISO timestamp of last update")
    tags: List[str] = Field(default_factory=list, description="Workflow tags")


class N8nWorkflowDetail(BaseContractModel):
    """Comprehensive representation of an n8n workflow definition."""
    workflow_id: str = Field(..., description="n8n workflow identifier")
    name: str = Field(..., description="Workflow title")
    active: bool = Field(default=False, description="Active status on n8n server")
    nodes: List[N8nNode] = Field(default_factory=list, description="Ordered list of workflow nodes")
    connections: Dict[str, Any] = Field(
        default_factory=dict,
        description="n8n 3-level nested connection map: connections[src]['main'][output_idx] = [...]"
    )
    settings: Dict[str, Any] = Field(default_factory=dict, description="Execution settings")
    version_id: Optional[str] = Field(default=None, description="Workflow version UUID")

    def compute_hash(self) -> str:
        """Computes a deterministic SHA-256 hash of the workflow topology and configuration."""
        normalized = {
            "name": self.name,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type,
                    "type_version": n.type_version,
                    "parameters": n.parameters,
                    "credentials": {k: v.model_dump() for k, v in (n.credentials or {}).items()},
                }
                for n in sorted(self.nodes, key=lambda x: x.name)
            ],
            "connections": self.connections,
        }
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:16]


class N8nWorkflowValidationResult(BaseContractModel):
    """Result of static DAG and schema validation on an n8n workflow."""
    is_valid: bool = Field(..., description="True if workflow satisfies all structural invariants")
    workflow_hash: str = Field(default="", description="Hash of the validated workflow definition")
    errors: List[str] = Field(default_factory=list, description="Blocking validation errors")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking structural warnings")
    trigger_nodes: List[str] = Field(default_factory=list, description="Names of identified entry trigger nodes")
    node_count: int = Field(default=0, description="Total nodes in the workflow")
    has_cycles: bool = Field(default=False, description="True if circular dependency detected")


class N8nExecutionReceipt(BaseContractModel):
    """Physical outcome receipt of an n8n workflow execution (Invariant 6)."""
    execution_id: str = Field(..., description="Unique n8n execution identifier")
    workflow_id: str = Field(..., description="Workflow ID that was executed")
    workflow_hash: str = Field(default="", description="Hash of workflow at execution time")
    status: Literal["success", "error", "running", "waiting", "timeout", "unknown"] = Field(
        ..., description="Terminal or active execution state"
    )
    started_at: Optional[str] = Field(default=None, description="Start ISO timestamp")
    stopped_at: Optional[str] = Field(default=None, description="End ISO timestamp")
    duration_ms: Optional[float] = Field(default=None, description="Total elapsed runtime in ms")
    node_status: Dict[str, str] = Field(
        default_factory=dict, description="Terminal state per node (e.g. {'Webhook': 'success'})"
    )
    error_message: Optional[str] = Field(default=None, description="Failure details if status == 'error'")
    output_data: Optional[Dict[str, Any]] = Field(
        default=None, description="Extracted final node output payload"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED, description="Physical receipt verification status"
    )


class N8nActionResult(BaseContractModel):
    """Standardized result envelope for all n8n capability operations."""
    action: str = Field(..., description="Action name, e.g. 'list_workflows', 'trigger_workflow'")
    workflow_id: Optional[str] = Field(default=None, description="Workflow ID involved")
    execution_id: Optional[str] = Field(default=None, description="Execution ID if triggered")
    success: bool = Field(..., description="True if action succeeded")
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED, description="Verification outcome"
    )
    data: Optional[Dict[str, Any]] = Field(default=None, description="Action-specific output payload")
    error: Optional[str] = Field(default=None, description="Sanitized error description on failure")
    sanitized: bool = Field(default=True, description="True if payload has passed through SecretScrubber")
