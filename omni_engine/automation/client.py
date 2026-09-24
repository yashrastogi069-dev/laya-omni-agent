"""n8n REST API Client for LAYA Automation Subsystem.

Wraps n8n's Public REST API endpoints with strongly typed Pydantic models,
secret scrubbing, and strict draft enforcement (REQ-BLOCK-1).
"""

from typing import Any, Dict, List, Optional, Tuple

from omni_engine.contracts.enums import VerificationStatus
from omni_engine.contracts.n8n import (
    N8nWorkflowSummary,
    N8nWorkflowDetail,
    N8nNode,
    N8nCredentialReference,
    N8nExecutionReceipt,
)
from omni_engine.automation.transport import N8nTransport
from omni_engine.automation.scrubber import SecretScrubber


class N8nClient:
    """Strongly typed, secure client for n8n v1 REST API."""

    def __init__(self, transport: N8nTransport):
        self.transport = transport

    def list_workflows(self) -> Tuple[bool, List[N8nWorkflowSummary], Optional[str]]:
        """Lists all workflows present on the n8n server."""
        status_code, body = self.transport.request("GET", "/api/v1/workflows")
        if status_code != 200:
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or "Failed to list workflows"))
            return False, [], err

        items = body.get("data") or body.get("workflows") or []
        summaries: List[N8nWorkflowSummary] = []
        for item in items:
            try:
                summaries.append(
                    N8nWorkflowSummary(
                        workflow_id=str(item.get("id")),
                        name=str(item.get("name", "Untitled")),
                        active=bool(item.get("active", False)),
                        created_at=item.get("createdAt"),
                        updated_at=item.get("updatedAt"),
                        tags=[str(t) if isinstance(t, str) else str(t.get("name", "")) for t in item.get("tags", [])],
                    )
                )
            except Exception as parse_err:
                continue

        return True, summaries, None

    def get_workflow(self, workflow_id: str) -> Tuple[bool, Optional[N8nWorkflowDetail], Optional[str]]:
        """Fetches full workflow details by workflow ID."""
        status_code, body = self.transport.request("GET", f"/api/v1/workflows/{workflow_id}")
        if status_code != 200:
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or f"Workflow {workflow_id} not found"))
            return False, None, err

        try:
            nodes_raw = body.get("nodes") or []
            nodes: List[N8nNode] = []
            for nr in nodes_raw:
                creds = None
                if nr.get("credentials"):
                    creds = {}
                    for ctype, cval in nr["credentials"].items():
                        if isinstance(cval, dict):
                            creds[ctype] = N8nCredentialReference(
                                id=str(cval.get("id", "")),
                                name=cval.get("name"),
                            )

                nodes.append(
                    N8nNode(
                        id=str(nr.get("id", "")),
                        name=str(nr.get("name", "")),
                        type=str(nr.get("type", "")),
                        type_version=float(nr.get("typeVersion", 1.0)),
                        position=nr.get("position", [0.0, 0.0]),
                        parameters=nr.get("parameters", {}),
                        credentials=creds,
                    )
                )

            detail = N8nWorkflowDetail(
                workflow_id=str(body.get("id", workflow_id)),
                name=str(body.get("name", "Untitled")),
                active=bool(body.get("active", False)),
                nodes=nodes,
                connections=body.get("connections", {}),
                settings=body.get("settings", {}),
                version_id=body.get("versionId"),
            )
            return True, detail, None
        except Exception as exc:
            return False, None, SecretScrubber.scrub_text(f"Schema parsing error: {exc}")

    def create_workflow_draft(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        connections: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[N8nWorkflowDetail], Optional[str]]:
        """Creates a new workflow strictly as an inactive draft.
        
        REQ-BLOCK-1: Unconditionally forces active=False.
        """
        payload = {
            "name": name,
            "nodes": nodes,
            "connections": connections,
            "settings": settings or {},
            "active": False,  # Mandatory draft mode
        }

        status_code, body = self.transport.request("POST", "/api/v1/workflows", body=payload)
        if status_code not in (200, 201):
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or "Failed to create workflow draft"))
            return False, None, err

        wf_id = str(body.get("id", ""))
        return self.get_workflow(wf_id)

    def activate_workflow_endpoint(self, workflow_id: str) -> Tuple[bool, Optional[str]]:
        """Invokes the server activation endpoint for a workflow."""
        status_code, body = self.transport.request("POST", f"/api/v1/workflows/{workflow_id}/activate")
        if status_code != 200:
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or f"Activation failed for {workflow_id}"))
            return False, err
        return True, None

    def deactivate_workflow_endpoint(self, workflow_id: str) -> Tuple[bool, Optional[str]]:
        """Invokes the server deactivation endpoint for a workflow."""
        status_code, body = self.transport.request("POST", f"/api/v1/workflows/{workflow_id}/deactivate")
        if status_code != 200:
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or f"Deactivation failed for {workflow_id}"))
            return False, err
        return True, None

    def trigger_workflow_execution(
        self,
        workflow_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Triggers execution of an active workflow, returning (success, execution_id, error)."""
        body = {"workflowId": workflow_id}
        if payload:
            body["data"] = payload

        status_code, resp = self.transport.request("POST", "/api/v1/executions", body=body)
        if status_code not in (200, 201):
            err = SecretScrubber.scrub_text(str(resp.get("message") or resp.get("error") or "Failed to trigger workflow execution"))
            return False, None, err

        exec_id = str(resp.get("id") or resp.get("executionId") or "")
        if not exec_id:
            return False, None, "n8n response omitted execution ID"

        return True, exec_id, None

    def get_execution(self, execution_id: str) -> Tuple[bool, Optional[N8nExecutionReceipt], Optional[str]]:
        """Fetches execution state and output data from n8n."""
        status_code, body = self.transport.request("GET", f"/api/v1/executions/{execution_id}")
        if status_code != 200:
            err = SecretScrubber.scrub_text(str(body.get("message") or body.get("error") or f"Execution {execution_id} not found"))
            return False, None, err

        try:
            status_raw = str(body.get("status", "unknown")).lower()
            if status_raw not in ("success", "error", "running", "waiting", "timeout"):
                status_raw = "unknown"

            started_at = body.get("startedAt")
            stopped_at = body.get("stoppedAt")
            duration_ms = None
            # Extract node terminal statuses and output data if available
            node_status: Dict[str, str] = {}
            output_data: Optional[Dict[str, Any]] = None

            result_data = body.get("data", {}).get("resultData", {})
            run_data = result_data.get("runData", {})
            for n_name, runs in run_data.items():
                if isinstance(runs, list) and runs:
                    last_run = runs[-1]
                    err_info = last_run.get("error")
                    if err_info:
                        node_status[n_name] = "error"
                    else:
                        node_status[n_name] = "success"
                        # Extract output data if present
                        main_out = last_run.get("data", {}).get("main")
                        if main_out and isinstance(main_out, list) and main_out[0]:
                            output_data = main_out[0][0].get("json")

            error_msg = None
            if status_raw == "error":
                raw_err = result_data.get("error", {})
                error_msg = SecretScrubber.scrub_text(str(raw_err.get("message") or body.get("error") or "Execution failed"))

            receipt = N8nExecutionReceipt(
                execution_id=execution_id,
                workflow_id=str(body.get("workflowId", "")),
                status=status_raw,  # type: ignore
                started_at=started_at,
                stopped_at=stopped_at,
                duration_ms=duration_ms,
                node_status=node_status,
                error_message=error_msg,
                output_data=SecretScrubber.scrub_dict(output_data) if output_data else None,
                verification_status=VerificationStatus.VERIFIED_SUCCESS if status_raw == "success" else (
                    VerificationStatus.VERIFIED_FAILURE if status_raw == "error" else VerificationStatus.UNVERIFIED
                ),
            )
            return True, receipt, None
        except Exception as exc:
            return False, None, SecretScrubber.scrub_text(f"Error parsing execution receipt: {exc}")
