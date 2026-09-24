"""Transport Abstraction for n8n API.

REQ-BLOCK-7: Decouples HTTP networking from business logic, allowing 100% offline
mock testing without requiring a live n8n instance.
"""

from abc import ABC, abstractmethod
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request
import urllib.error

from omni_engine.automation.scrubber import SecretScrubber


class N8nTransport(ABC):
    """Abstract interface for sending requests to n8n."""

    @abstractmethod
    def request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> Tuple[int, Dict[str, Any]]:
        """Sends an HTTP request to n8n and returns (status_code, json_dict)."""
        pass


class HttpN8nTransport(N8nTransport):
    """Production HTTP transport communicating with an n8n instance via urllib."""

    def __init__(self, base_url: str = "http://127.0.0.1:5678", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        # Dedicated opener with empty proxy dict to bypass host proxy traps for loopback
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> Tuple[int, Dict[str, Any]]:
        full_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{full_path}"
        if query_params:
            url = f"{url}?{urllib.parse.urlencode(query_params)}"

        req_headers = {
            "Accept": "application/json",
            "User-Agent": "LAYA-Omni-Agent/2.0",
        }
        if self.api_key:
            req_headers["X-N8N-API-KEY"] = self.api_key

        if headers:
            req_headers.update(headers)

        encoded_data = None
        if body is not None:
            req_headers["Content-Type"] = "application/json"
            encoded_data = json.dumps(body).encode("utf-8")

        req = urllib.request.Request(
            url=url,
            data=encoded_data,
            headers=req_headers,
            method=method.upper(),
        )

        try:
            with self._opener.open(req, timeout=timeout) as response:
                status_code = response.getcode()
                raw_bytes = response.read(524288)  # Read up to 512KB
                try:
                    payload = json.loads(raw_bytes.decode("utf-8")) if raw_bytes else {}
                except Exception:
                    payload = {"raw": raw_bytes.decode("utf-8", errors="replace")}
                return status_code, payload
        except urllib.error.HTTPError as exc:
            err_bytes = exc.read(65536)
            try:
                err_payload = json.loads(err_bytes.decode("utf-8")) if err_bytes else {}
            except Exception:
                err_payload = {"error": SecretScrubber.scrub_text(str(exc))}
            return exc.code, err_payload
        except Exception as exc:
            return 500, {"error": SecretScrubber.scrub_text(str(exc))}


class MockN8nTransport(N8nTransport):
    """In-memory mock n8n transport for fast, offline unit and integration testing."""

    def __init__(self):
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.executions: Dict[str, Dict[str, Any]] = {}
        self._next_wf_id = 1
        self._next_exec_id = 100
        # Simulation hooks
        self.force_status_code: Optional[int] = None
        self.force_error_payload: Optional[Dict[str, Any]] = None
        self.execution_state_sequence: Dict[str, List[str]] = {}

    def add_mock_workflow(self, workflow_dict: Dict[str, Any]) -> str:
        wf_id = str(workflow_dict.get("id") or f"wf_{self._next_wf_id}")
        self._next_wf_id += 1
        workflow_dict["id"] = wf_id
        if "active" not in workflow_dict:
            workflow_dict["active"] = False
        self.workflows[wf_id] = workflow_dict
        return wf_id

    def request(
        self,
        method: str,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 15.0,
    ) -> Tuple[int, Dict[str, Any]]:
        if self.force_status_code is not None:
            return self.force_status_code, (self.force_error_payload or {"error": "Forced mock error"})

        m = method.upper()
        norm_path = path.strip("/")

        # 1. GET /api/v1/workflows
        if m == "GET" and norm_path == "api/v1/workflows":
            wf_list = [
                {
                    "id": k,
                    "name": v.get("name", "Untitled"),
                    "active": v.get("active", False),
                    "createdAt": v.get("createdAt", "2026-09-24T12:00:00Z"),
                    "updatedAt": v.get("updatedAt", "2026-09-24T12:00:00Z"),
                    "tags": v.get("tags", []),
                }
                for k, v in self.workflows.items()
            ]
            return 200, {"data": wf_list}

        # 2. POST /api/v1/workflows (Create)
        if m == "POST" and norm_path == "api/v1/workflows":
            wf_id = f"wf_{self._next_wf_id}"
            self._next_wf_id += 1
            wf_data = body.copy() if body else {}
            wf_data["id"] = wf_id
            wf_data["createdAt"] = "2026-09-24T12:00:00Z"
            wf_data["updatedAt"] = "2026-09-24T12:00:00Z"
            # Server defaults to inactive if not specified
            if "active" not in wf_data:
                wf_data["active"] = False
            self.workflows[wf_id] = wf_data
            return 201, wf_data

        # 3. GET /api/v1/workflows/{id}
        if m == "GET" and norm_path.startswith("api/v1/workflows/"):
            parts = norm_path.split("/")
            if len(parts) == 4:
                wf_id = parts[3]
                if wf_id in self.workflows:
                    return 200, self.workflows[wf_id]
                return 404, {"message": f"Workflow {wf_id} not found."}

        # 4. PUT/PATCH /api/v1/workflows/{id}
        if m in ("PUT", "PATCH") and norm_path.startswith("api/v1/workflows/"):
            parts = norm_path.split("/")
            if len(parts) == 4:
                wf_id = parts[3]
                if wf_id in self.workflows:
                    if body:
                        self.workflows[wf_id].update(body)
                    return 200, self.workflows[wf_id]
                return 404, {"message": f"Workflow {wf_id} not found."}

        # 5. POST /api/v1/workflows/{id}/activate
        if m == "POST" and norm_path.startswith("api/v1/workflows/") and norm_path.endswith("/activate"):
            parts = norm_path.split("/")
            wf_id = parts[3]
            if wf_id in self.workflows:
                self.workflows[wf_id]["active"] = True
                return 200, self.workflows[wf_id]
            return 404, {"message": f"Workflow {wf_id} not found."}

        # 6. POST /api/v1/workflows/{id}/deactivate
        if m == "POST" and norm_path.startswith("api/v1/workflows/") and norm_path.endswith("/deactivate"):
            parts = norm_path.split("/")
            wf_id = parts[3]
            if wf_id in self.workflows:
                self.workflows[wf_id]["active"] = False
                return 200, self.workflows[wf_id]
            return 404, {"message": f"Workflow {wf_id} not found."}

        # 7. POST /api/v1/executions (Trigger)
        if m == "POST" and norm_path == "api/v1/executions":
            exec_id = f"exec_{self._next_exec_id}"
            self._next_exec_id += 1
            wf_id = (body or {}).get("workflowId", "wf_1")
            exec_obj = {
                "id": exec_id,
                "workflowId": wf_id,
                "status": "success",
                "startedAt": "2026-09-24T12:00:00Z",
                "stoppedAt": "2026-09-24T12:00:01Z",
                "data": {
                    "resultData": {
                        "runData": {
                            "Webhook": [{"status": "success"}],
                            "OutputNode": [{"data": {"main": [[{"json": {"ok": True}}]]}}],
                        }
                    }
                },
            }
            self.executions[exec_id] = exec_obj
            return 200, {"id": exec_id, "status": "success"}

        # 8. GET /api/v1/executions/{id}
        if m == "GET" and norm_path.startswith("api/v1/executions/"):
            parts = norm_path.split("/")
            if len(parts) == 4:
                exec_id = parts[3]
                if exec_id in self.executions:
                    exec_record = self.executions[exec_id]
                    # Check if there's a dynamic status transition sequence
                    if exec_id in self.execution_state_sequence and self.execution_state_sequence[exec_id]:
                        next_status = self.execution_state_sequence[exec_id].pop(0)
                        exec_record["status"] = next_status
                    return 200, exec_record
                return 404, {"message": f"Execution {exec_id} not found."}

        return 404, {"message": f"Endpoint {method} /{norm_path} not found in mock."}
