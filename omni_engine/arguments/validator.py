"""
omni_engine.arguments.validator
===============================
Deterministic Semantic Argument Validator for LAYA Omni Agent.

Enforces deep semantic validation on capability arguments before policy checks,
operation ledger recording, or physical execution.

Adheres to:
- Prime Directive & Invariant 1: Deterministic Control.
- Invariant 4: Strongly Typed Contracts.
- Checkpoint L14.3 Section 14: Semantic Argument Validation.
"""

import os
import re
from typing import Any, Dict, Optional
import urllib.parse

from omni_engine.contracts.enums import ErrorCode


class SemanticValidationError(ValueError):
    """Raised when an argument fails semantic validation beyond schema type checks."""
    def __init__(self, message: str, field: Optional[str] = None, code: ErrorCode = ErrorCode.INVALID_ARGUMENT):
        super().__init__(message)
        self.message = message
        self.field = field
        self.code = code


class SemanticArgumentValidator:
    """Validates and normalizes semantic types: URLs, Ports, Paths, Process targets, and Workflow IDs."""

    # Regex detecting malformed nested schemes like https://https://, http://http://, https:http:, etc.
    NESTED_SCHEME_PATTERN = re.compile(r"^(?:https?[:/]+){2,}", re.IGNORECASE)

    @classmethod
    def validate_url(cls, url: Any, allow_file_scheme: bool = True) -> str:
        """Validates that a URL has exactly one valid scheme, a valid host, and no nested schemes.
        
        Raises:
            SemanticValidationError: On nested schemes, invalid characters, or missing host.
        """
        if not isinstance(url, str) or not url.strip():
            raise SemanticValidationError("URL must be a non-empty string.", field="url")

        clean_url = url.strip()

        # Reject malformed nested / double schemes (PRACT-025)
        if cls.NESTED_SCHEME_PATTERN.match(clean_url):
            raise SemanticValidationError(
                f"Malformed URL '{url}': Multiple or nested protocol schemes detected (e.g. 'https://https://').",
                field="url"
            )

        # Parse with urllib
        try:
            parsed = urllib.parse.urlparse(clean_url)
        except Exception as e:
            raise SemanticValidationError(f"Malformed URL '{url}': {str(e)}", field="url") from e

        allowed_schemes = ("http", "https")
        if allow_file_scheme:
            allowed_schemes = ("http", "https", "file")

        if parsed.scheme.lower() not in allowed_schemes:
            raise SemanticValidationError(
                f"Malformed URL '{url}': Scheme '{parsed.scheme}' is unsupported. Allowed schemes: {allowed_schemes}.",
                field="url"
            )

        # For HTTP/HTTPS, require netloc / hostname
        if parsed.scheme.lower() in ("http", "https"):
            if not parsed.netloc or not parsed.hostname:
                raise SemanticValidationError(
                    f"Malformed URL '{url}': Missing valid host name or authority.",
                    field="url"
                )
            # Check for illegal double colon in scheme/host
            if "::" in clean_url and not clean_url.startswith("http://[") and not clean_url.startswith("https://["):
                raise SemanticValidationError(
                    f"Malformed URL '{url}': Illegal nested punctuation in URL structure.",
                    field="url"
                )

        return clean_url

    @classmethod
    def validate_port(cls, port: Any) -> int:
        """Validates that port is an integer in the valid TCP/UDP range [1, 65535]."""
        try:
            int_port = int(port)
        except (ValueError, TypeError) as e:
            raise SemanticValidationError(f"Invalid port value '{port}': Port must be an integer.", field="port") from e

        if not (1 <= int_port <= 65535):
            raise SemanticValidationError(
                f"Invalid port '{int_port}': Port must be in the range 1 to 65535.",
                field="port"
            )
        return int_port

    @classmethod
    def validate_path(cls, path: Any) -> str:
        """Normalizes and canonicalizes filesystem paths."""
        if not isinstance(path, str) or not path.strip():
            raise SemanticValidationError("File path must be a non-empty string.", field="path")

        clean_path = path.strip().strip("\"'")
        # Normalize slashes and redundant components
        normalized = os.path.normpath(clean_path)
        if "/" in clean_path and "\\" not in clean_path:
            normalized = normalized.replace("\\", "/")
        return normalized

    @classmethod
    def validate_process_target(cls, target: Any) -> str:
        """Validates and normalizes process targets (PID or executable name)."""
        if target is None:
            raise SemanticValidationError("Process target cannot be None.", field="target")

        target_str = str(target).strip()
        if not target_str:
            raise SemanticValidationError("Process target cannot be empty.", field="target")

        # If numeric PID, ensure positive integer
        if target_str.isdigit():
            pid_int = int(target_str)
            if pid_int < 0:
                raise SemanticValidationError(f"Invalid PID '{pid_int}': PID must be non-negative.", field="target")
            return str(pid_int)

        return target_str

    @classmethod
    def validate_workflow_id(cls, workflow_id: Any) -> str:
        """Validates that a workflow/execution ID is non-empty and syntactically acceptable."""
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise SemanticValidationError("Workflow ID must be a non-empty string.", field="workflow_id")

        clean_id = workflow_id.strip()
        # Disallow control characters or path traversal markers
        if any(c in clean_id for c in ["\x00", "\n", "\r", "..", "/", "\\"]):
            raise SemanticValidationError(f"Invalid workflow ID '{workflow_id}': Contains illegal characters.", field="workflow_id")
        return clean_id

    @classmethod
    def validate_arguments(cls, capability_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and normalizes arguments for a capability invocation.
        
        Performs targeted semantic checks based on argument names and capability domain.
        """
        validated = dict(arguments)

        for key, val in list(validated.items()):
            # Dynamic references ($steps, $inputs) cannot be semantically validated until resolved
            if isinstance(val, str) and (val.startswith("$steps.") or val.startswith("$inputs.")):
                continue

            # URL validation
            if key in ("url", "target_url", "start_url") and val is not None:
                validated[key] = cls.validate_url(val)

            # Port validation
            elif (key == "port" or key.endswith("_port")) and val is not None:
                validated[key] = cls.validate_port(val)

            # Path validation
            elif key in ("path", "filepath", "file_path", "db_path", "destination") and val is not None:
                validated[key] = cls.validate_path(val)

            # Process target validation
            elif key in ("target", "pid_or_name") and "process" in capability_id and val is not None:
                validated[key] = cls.validate_process_target(val)

            # Workflow / execution ID validation
            elif key in ("workflow_id", "execution_id") and val is not None:
                validated[key] = cls.validate_workflow_id(val)

        return validated
