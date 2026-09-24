"""
omni_engine.desktop.service
===========================
Deterministic Local Service and Microservice Health Prober (Phase R3).

Adheres to:
- Invariant 1: Deterministic Control — bounded timeouts, strict error envelopes.
- Invariant 6: Evidence-Based Completion — physical TCP socket handshake & HTTP response receipts.
- REQ-R3-3: Dual-stack cascade (127.0.0.1 -> ::1), SO_LINGER TIME_WAIT prevention, proxy bypass, bounded 4KB reads.
"""

import json
import socket
import struct
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from omni_engine.contracts.desktop import ServiceHealthStatus


# Default registry of known local development and runtime services
KNOWN_SERVICES: Dict[str, Dict[str, Any]] = {
    "n8n": {
        "port": 5678,
        "http_path": "/healthz",
        "description": "n8n Workflow Automation Server",
    },
    "ollama": {
        "port": 11434,
        "http_path": "/api/tags",
        "description": "Ollama Local LLM Daemon",
    },
    "antigravity": {
        "port": 8000,
        "http_path": "/",
        "description": "Antigravity Local Agent/Dev Server",
    },
    "dev_server": {
        "port": 3000,
        "http_path": "/",
        "description": "Local Web Application / React / Next.js Server",
    },
    "dev_server_alt": {
        "port": 8080,
        "http_path": "/",
        "description": "Alternative Local Web Server (8080)",
    },
}


class LocalServiceProber:
    """High-reliability, low-overhead local port and HTTP service prober."""

    def __init__(
        self,
        default_socket_timeout: float = 0.5,
        default_http_timeout: float = 1.5,
    ) -> None:
        self.default_socket_timeout = default_socket_timeout
        self.default_http_timeout = default_http_timeout
        # REQ-R3-3: Build isolated opener bypassing host/system proxies for loopback calls
        self._proxy_bypass_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def probe_socket(
        self,
        host: str = "127.0.0.1",
        port: int = 5678,
        timeout: Optional[float] = None,
    ) -> Tuple[bool, float, Optional[str]]:
        """Probes TCP socket availability with dual-stack cascade and SO_LINGER hygiene.
        
        Returns:
            Tuple of (is_listening: bool, response_time_ms: float, error_message: Optional[str])
        """
        t_out = timeout or self.default_socket_timeout
        t0 = time.perf_counter()

        # REQ-R3-3: Candidate IP cascade for local loopback
        candidates = [host]
        if host in ("localhost", "127.0.0.1"):
            candidates = ["127.0.0.1", "::1"]

        last_error = None
        for cand in candidates:
            family = socket.AF_INET6 if ":" in cand else socket.AF_INET
            try:
                with socket.socket(family, socket.SOCK_STREAM) as s:
                    s.settimeout(t_out)
                    # REQ-R3-3: Prevent TIME_WAIT accumulation during rapid health checks
                    try:
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
                    except Exception:
                        pass
                    s.connect((cand, port))
                    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                    return True, latency_ms, None
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                last_error = str(e)
                continue

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return False, latency_ms, last_error

    def probe_http(
        self,
        url: str,
        expected_status: int = 200,
        timeout: Optional[float] = None,
    ) -> Tuple[bool, Optional[int], float, Dict[str, Any], Optional[str]]:
        """Dispatches an HTTP GET probe with proxy bypass and bounded response reads.
        
        Returns:
            Tuple of (success: bool, status_code: Optional[int], latency_ms: float, details: dict, error: Optional[str])
        """
        t_out = timeout or self.default_http_timeout
        t0 = time.perf_counter()

        req = urllib.request.Request(
            url=url,
            headers={"User-Agent": "LAYA-ServiceProber/1.0", "Accept": "application/json, text/plain, */*"},
            method="GET",
        )

        try:
            with self._proxy_bypass_opener.open(req, timeout=t_out) as resp:
                status_code = resp.getcode()
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
                # REQ-R3-3: Bounded 4KB read to prevent hanging on unbounded streams
                raw_bytes = resp.read(4096)
                body_text = raw_bytes.decode("utf-8", errors="replace")

                details: Dict[str, Any] = {"status_code": status_code}
                try:
                    details["json"] = json.loads(body_text)
                except Exception:
                    details["body_preview"] = body_text[:200]

                success = (status_code == expected_status) or (200 <= status_code < 400)
                return success, status_code, latency_ms, details, None

        except urllib.error.HTTPError as e:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return False, e.code, latency_ms, {"http_error": str(e)}, f"HTTP {e.code}: {e.reason}"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return False, None, latency_ms, {}, f"Network connection failed: {e}"

    def check_service(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        http_path: Optional[str] = None,
    ) -> ServiceHealthStatus:
        """Evaluates health of a named or custom service, emitting strongly typed receipts."""
        s_lower = service_name.lower().strip()
        catalog_entry = KNOWN_SERVICES.get(s_lower, {})

        target_host = host or "127.0.0.1"
        target_port = port or catalog_entry.get("port", 80)
        target_path = http_path or catalog_entry.get("http_path")

        # Step 1: TCP Port Probe
        is_listening, port_latency, socket_err = self.probe_socket(
            host=target_host,
            port=target_port,
        )

        if not is_listening:
            return ServiceHealthStatus(
                service_name=service_name,
                host=target_host,
                port=target_port,
                is_listening=False,
                http_status=None,
                response_time_ms=port_latency,
                details={"probe": "tcp_socket"},
                error=socket_err or f"Port {target_port} not listening on {target_host}",
            )

        # Step 2: HTTP Probe if path is defined
        if target_path:
            url = f"http://{target_host}:{target_port}{target_path}"
            http_success, http_code, http_latency, details, http_err = self.probe_http(url=url)
            total_latency = round(port_latency + http_latency, 2)
            details["url"] = url
            return ServiceHealthStatus(
                service_name=service_name,
                host=target_host,
                port=target_port,
                is_listening=True,
                http_status=http_code,
                response_time_ms=total_latency,
                details=details,
                error=http_err if not http_success else None,
            )

        # Pure socket service
        return ServiceHealthStatus(
            service_name=service_name,
            host=target_host,
            port=target_port,
            is_listening=True,
            http_status=None,
            response_time_ms=port_latency,
            details={"probe": "tcp_socket_only"},
            error=None,
        )
