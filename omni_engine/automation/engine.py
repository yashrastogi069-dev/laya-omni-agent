"""High-Level n8n Automation Engine for LAYA.

Implements the Draft-Test-Validate workflow lifecycle (REQ-BLOCK-1),
bounded execution polling with backoff (REQ-BLOCK-4), local microservice discovery,
and secret-scrubbed action envelopes under Invariants 1, 4, and 6.
"""

from collections.abc import Callable
import time
from typing import Any, Dict, List, Optional, Union

from omni_engine.contracts.enums import VerificationStatus
from omni_engine.contracts.desktop import ServiceHealthStatus
from omni_engine.contracts.n8n import (
    N8nWorkflowSummary,
    N8nWorkflowDetail,
    N8nWorkflowValidationResult,
    N8nExecutionReceipt,
    N8nActionResult,
)
from omni_engine.automation.client import N8nClient
from omni_engine.automation.validator import N8nWorkflowValidator
from omni_engine.automation.scrubber import SecretScrubber
from omni_engine.desktop.service import LocalServiceProber


class N8nAutomationEngine:
    """Orchestrates n8n workflow management, validation, and verified execution."""

    def __init__(
        self,
        client: N8nClient,
        service_prober: Optional[LocalServiceProber] = None,
        poll_interval: float = 0.2,
        sleep_fn: Callable[[float], None] = time.sleep,
    ):
        self.client = client
        self.prober = service_prober or LocalServiceProber()
        self.poll_interval = poll_interval
        self.sleep_fn = sleep_fn
        # Gate Triad: Cache verified execution receipts by workflow_hash
        self._verified_receipts: Dict[str, N8nExecutionReceipt] = {}

    def check_local_instance(self, port: int = 5678) -> ServiceHealthStatus:
        """Probes the health of the local n8n daemon on localhost."""
        return self.prober.check_service(service_name="n8n", port=port, http_path="/healthz")

    def list_workflows(self) -> N8nActionResult:
        """Lists all workflows available on the n8n instance."""
        success, summaries, err = self.client.list_workflows()
        if not success:
            return N8nActionResult(
                action="list_workflows",
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        return N8nActionResult(
            action="list_workflows",
            success=True,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
            data={"workflows": [s.model_dump() for s in summaries], "count": len(summaries)},
        )

    def get_workflow(self, workflow_id: str) -> N8nActionResult:
        """Retrieves complete workflow structure and validates it."""
        success, detail, err = self.client.get_workflow(workflow_id)
        if not success or not detail:
            return N8nActionResult(
                action="get_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        validation = N8nWorkflowValidator.validate(detail)
        return N8nActionResult(
            action="get_workflow",
            workflow_id=workflow_id,
            success=True,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
            data={
                "workflow": detail.model_dump(),
                "validation": validation.model_dump(),
            },
        )

    def validate_workflow(
        self,
        workflow_id_or_data: Union[str, N8nWorkflowDetail, Dict[str, Any]],
    ) -> N8nWorkflowValidationResult:
        """Runs static graph validation and cycle detection without modifying state."""
        if isinstance(workflow_id_or_data, N8nWorkflowDetail):
            return N8nWorkflowValidator.validate(workflow_id_or_data)

        if isinstance(workflow_id_or_data, dict):
            # Parse dict into N8nWorkflowDetail
            try:
                wf = N8nWorkflowDetail(**workflow_id_or_data)
                return N8nWorkflowValidator.validate(wf)
            except Exception as exc:
                return N8nWorkflowValidationResult(
                    is_valid=False,
                    errors=[f"Invalid workflow structure: {exc}"],
                )

        # String workflow ID
        success, detail, err = self.client.get_workflow(str(workflow_id_or_data))
        if not success or not detail:
            return N8nWorkflowValidationResult(
                is_valid=False,
                errors=[err or f"Workflow {workflow_id_or_data} not found"],
            )

        return N8nWorkflowValidator.validate(detail)

    def create_workflow(
        self,
        name: str,
        nodes: List[Dict[str, Any]],
        connections: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> N8nActionResult:
        """Creates a new workflow in inactive draft mode after pre-flight validation.
        
        REQ-BLOCK-1: active is strictly False.
        """
        # 1. Pre-flight secret scan
        if SecretScrubber.contains_secret(nodes):
            return N8nActionResult(
                action="create_workflow",
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error="Node parameters contain plaintext secrets or tokens. Use credential IDs instead.",
            )

        # 2. Pre-flight structural validation
        temp_detail = N8nWorkflowDetail(
            workflow_id="temp_draft",
            name=name,
            active=False,
            nodes=[
                {
                    "id": str(n.get("id", f"node_{i}")),
                    "name": str(n.get("name", f"Node_{i}")),
                    "type": str(n.get("type", "")),
                    "type_version": float(n.get("typeVersion", 1.0)),
                    "position": n.get("position", [0.0, 0.0]),
                    "parameters": n.get("parameters", {}),
                }
                for i, n in enumerate(nodes)
            ],
            connections=connections,
            settings=settings or {},
        )

        validation = N8nWorkflowValidator.validate(temp_detail)
        if not validation.is_valid:
            return N8nActionResult(
                action="create_workflow",
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Pre-flight graph validation failed: {'; '.join(validation.errors)}",
                data={"validation": validation.model_dump()},
            )

        # 3. Create draft on n8n server
        success, created_wf, err = self.client.create_workflow_draft(
            name=name, nodes=nodes, connections=connections, settings=settings
        )
        if not success or not created_wf:
            return N8nActionResult(
                action="create_workflow",
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        return N8nActionResult(
            action="create_workflow",
            workflow_id=created_wf.workflow_id,
            success=True,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
            data={
                "workflow": created_wf.model_dump(),
                "workflow_hash": created_wf.compute_hash(),
                "validation": validation.model_dump(),
                "active": False,
                "message": "Workflow created in draft mode (active=False). Test and validate before activation.",
            },
        )

    def trigger_and_wait(
        self,
        workflow_id: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> N8nExecutionReceipt:
        """Triggers execution and polls with exponential backoff until completion (REQ-BLOCK-4)."""
        start_time = time.perf_counter()
        deadline = start_time + max(1.0, timeout_seconds)

        success, exec_id, err = self.client.trigger_workflow_execution(workflow_id, payload)
        if not success or not exec_id:
            return N8nExecutionReceipt(
                execution_id=exec_id or "unknown",
                workflow_id=workflow_id,
                status="error",
                error_message=err or "Trigger execution failed",
                verification_status=VerificationStatus.VERIFIED_FAILURE,
            )

        # Exponential backoff parameters
        current_interval = max(0.001, self.poll_interval)
        max_interval = 2.0
        backoff_factor = 1.5

        last_receipt: Optional[N8nExecutionReceipt] = None

        while time.perf_counter() < deadline:
            poll_success, receipt, poll_err = self.client.get_execution(exec_id)
            if poll_success and receipt:
                last_receipt = receipt
                # Terminal States
                if receipt.status in ("success", "error"):
                    receipt.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    return receipt

                # REQ-BLOCK-4: "waiting" state breakout (Wait node encountered)
                if receipt.status == "waiting":
                    receipt.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                    receipt.error_message = "Workflow entered waiting state (external event required)."
                    return receipt

            # Backoff and wait
            self.sleep_fn(current_interval)
            current_interval = min(current_interval * backoff_factor, max_interval)

        # Timeout reached
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return N8nExecutionReceipt(
            execution_id=exec_id,
            workflow_id=workflow_id,
            status="timeout",
            duration_ms=elapsed_ms,
            error_message=f"Execution timed out after {timeout_seconds}s.",
            verification_status=VerificationStatus.UNVERIFIED,
        )

    def test_workflow(
        self,
        workflow_id: str,
        test_payload: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> N8nActionResult:
        """Executes a test run of a workflow and caches successful receipt for gate triad."""
        # 1. Fetch current workflow and compute hash
        success, detail, err = self.client.get_workflow(workflow_id)
        if not success or not detail:
            return N8nActionResult(
                action="test_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        wf_hash = detail.compute_hash()

        # 2. Execute test run
        receipt = self.trigger_and_wait(workflow_id, test_payload, timeout_seconds=timeout_seconds)
        receipt.workflow_hash = wf_hash

        if receipt.status == "success":
            # Record in gate triad cache
            self._verified_receipts[wf_hash] = receipt
            return N8nActionResult(
                action="test_workflow",
                workflow_id=workflow_id,
                execution_id=receipt.execution_id,
                success=True,
                verification_status=VerificationStatus.VERIFIED_SUCCESS,
                data={
                    "receipt": receipt.model_dump(),
                    "workflow_hash": wf_hash,
                    "passed_test_gate": True,
                },
            )

        return N8nActionResult(
            action="test_workflow",
            workflow_id=workflow_id,
            execution_id=receipt.execution_id,
            success=False,
            verification_status=VerificationStatus.VERIFIED_FAILURE,
            error=receipt.error_message or f"Test execution ended with status '{receipt.status}'",
            data={"receipt": receipt.model_dump(), "workflow_hash": wf_hash},
        )

    def activate_workflow(self, workflow_id: str) -> N8nActionResult:
        """Promotes a workflow to active status under the Enforced Gate Triad (REQ-BLOCK-1).
        
        Triad Invariant:
        1. Structural Validation Pass (is_valid == True)
        2. Execution Receipt Pass (successful test run for current workflow_hash)
        3. Zero Plaintext Secrets Pass (clean parameters)
        """
        # 1. Fetch current workflow
        success, detail, err = self.client.get_workflow(workflow_id)
        if not success or not detail:
            return N8nActionResult(
                action="activate_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        current_hash = detail.compute_hash()

        # Gate 1: Structural Validation
        validation = N8nWorkflowValidator.validate(detail)
        if not validation.is_valid:
            return N8nActionResult(
                action="activate_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=f"Activation blocked by Gate 1 (Structural Validation): {'; '.join(validation.errors)}",
                data={"validation": validation.model_dump()},
            )

        # Gate 2: Evidence-Based Execution Receipt Pass
        cached_receipt = self._verified_receipts.get(current_hash)
        if not cached_receipt or cached_receipt.status != "success":
            return N8nActionResult(
                action="activate_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=(
                    f"Activation blocked by Gate 2 (Test Execution): No verified test receipt found for current "
                    f"workflow hash '{current_hash}'. You must execute 'test_workflow' successfully before activating."
                ),
                data={"current_hash": current_hash},
            )

        # Gate 3: Zero Plaintext Secrets Pass
        if SecretScrubber.contains_secret([n.parameters for n in detail.nodes]):
            return N8nActionResult(
                action="activate_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error="Activation blocked by Gate 3 (Secret Protection): Workflow parameters contain plaintext secrets.",
            )

        # All 3 gates satisfied -> Invoke activation
        act_success, act_err = self.client.activate_workflow_endpoint(workflow_id)
        if not act_success:
            return N8nActionResult(
                action="activate_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=act_err,
            )

        return N8nActionResult(
            action="activate_workflow",
            workflow_id=workflow_id,
            success=True,
            verification_status=VerificationStatus.VERIFIED_SUCCESS,
            data={
                "workflow_id": workflow_id,
                "workflow_hash": current_hash,
                "active": True,
                "test_execution_id": cached_receipt.execution_id,
                "message": "Workflow successfully validated, tested, and activated.",
            },
        )

    def trigger_workflow(
        self,
        workflow_id: str,
        payload: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True,
        timeout_seconds: float = 30.0,
    ) -> N8nActionResult:
        """Triggers an active workflow with structured parameters and captures physical receipts."""
        if wait_for_completion:
            receipt = self.trigger_and_wait(workflow_id, payload, timeout_seconds=timeout_seconds)
            return N8nActionResult(
                action="trigger_workflow",
                workflow_id=workflow_id,
                execution_id=receipt.execution_id,
                success=receipt.status == "success",
                verification_status=receipt.verification_status,
                data={"receipt": receipt.model_dump()},
                error=receipt.error_message,
            )

        # Fire and return execution ID
        success, exec_id, err = self.client.trigger_workflow_execution(workflow_id, payload)
        if not success:
            return N8nActionResult(
                action="trigger_workflow",
                workflow_id=workflow_id,
                success=False,
                verification_status=VerificationStatus.VERIFIED_FAILURE,
                error=err,
            )

        return N8nActionResult(
            action="trigger_workflow",
            workflow_id=workflow_id,
            execution_id=exec_id,
            success=True,
            verification_status=VerificationStatus.UNVERIFIED,
            data={"execution_id": exec_id, "status": "running"},
        )
