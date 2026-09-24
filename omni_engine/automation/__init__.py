"""n8n Automation Subsystem for LAYA.

Exposes secret scrubbing, workflow graph validation, transport abstractions,
REST API client, and the high-level automation engine.
"""

from .scrubber import SecretScrubber, SENSITIVE_HEADERS
from .validator import N8nWorkflowValidator
from .transport import N8nTransport, HttpN8nTransport, MockN8nTransport
from .client import N8nClient
from .engine import N8nAutomationEngine

__all__ = [
    "SecretScrubber",
    "SENSITIVE_HEADERS",
    "N8nWorkflowValidator",
    "N8nTransport",
    "HttpN8nTransport",
    "MockN8nTransport",
    "N8nClient",
    "N8nAutomationEngine",
]
