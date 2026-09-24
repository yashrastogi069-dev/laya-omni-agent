"""Secret Scrubber for LAYA Automation Subsystem.

REQ-BLOCK-3: Provides deterministic detection and redaction of plaintext API keys,
bearer tokens, passwords, private keys, and authorization headers from strings,
dictionaries, and error messages before logging or returning ToolResult envelopes.
"""

import copy
import re
from typing import Any, Dict, List, Set, Union


# Compiled secret patterns
SECRET_PATTERNS = [
    # OpenAI API Keys
    re.compile(r"\bsk-(?:proj-|live-)?[A-Za-z0-9_-]{20,}\b"),
    # GitHub Personal Access Tokens
    re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"),
    # Bearer / Basic Auth Tokens
    re.compile(r"(?i)\b(?:Bearer|Basic)\s+[A-Za-z0-9\-._~+/]+=*"),
    # AWS Access Key ID
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    # n8n API Key
    re.compile(r"(?i)\b(?:x-n8n-api-key|n8n[-_]api[-_]key)\s*[:=]\s*[\"']?([A-Za-z0-9\-_]{16,})[\"']?"),
    # Generic Secret / Token assignments (quoted values >= 8 chars)
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|secret_key|private_key|password)\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']"),
    # SSH / RSA / EC Private Keys
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"),
    # Sensitive URL Query Parameters
    re.compile(r"(?i)(?:token|api[-_]?key|key|secret|password)=([A-Za-z0-9\-._~+/]{8,})"),
]

# Sensitive HTTP headers
SENSITIVE_HEADERS: Set[str] = {
    "authorization",
    "x-n8n-api-key",
    "x-api-key",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}


class SecretScrubber:
    """Deterministic sanitizer for secrets and credentials."""

    @staticmethod
    def scrub_text(text: str) -> str:
        """Redacts sensitive tokens from a plain text or error string."""
        if not text or not isinstance(text, str):
            return text

        scrubbed = text

        # Check SSH keys first (multiline)
        for pattern in SECRET_PATTERNS:
            def _replace_match(m: re.Match) -> str:
                matched_str = m.group(0)
                # Avoid redacting n8n expression references like {{$json.token}}
                if "$json" in matched_str or "$node" in matched_str or "$parameter" in matched_str:
                    return matched_str
                # If pattern has capturing group for value, redact just the value part
                if m.lastindex and m.lastindex >= 1:
                    val = m.group(1)
                    return matched_str.replace(val, "[REDACTED_SECRET]")
                return "[REDACTED_SECRET]"

            scrubbed = pattern.sub(_replace_match, scrubbed)

        return scrubbed

    @classmethod
    def scrub_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Redacts sensitive HTTP authorization headers."""
        if not headers or not isinstance(headers, dict):
            return {}

        sanitized: Dict[str, str] = {}
        for k, v in headers.items():
            if str(k).lower() in SENSITIVE_HEADERS:
                sanitized[k] = "[REDACTED_HEADER]"
            else:
                sanitized[k] = cls.scrub_text(str(v))
        return sanitized

    @classmethod
    def scrub_dict(cls, data: Union[Dict[str, Any], List[Any], Any]) -> Any:
        """Recursively sanitizes nested dictionaries, lists, and strings.
        
        Returns a deep-copied, sanitized structure without mutating the input.
        """
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                lower_k = str(k).lower()
                # If key itself denotes a secret and value is a raw string/number
                if any(sec in lower_k for sec in ("password", "secret", "token", "apikey", "api_key")) and isinstance(v, (str, int, float)):
                    # Protect n8n expressions
                    if isinstance(v, str) and (v.startswith("={{") or "$json" in v):
                        new_dict[k] = v
                    else:
                        new_dict[k] = "[REDACTED_SECRET]"
                else:
                    new_dict[k] = cls.scrub_dict(v)
            return new_dict

        elif isinstance(data, list):
            return [cls.scrub_dict(item) for item in data]

        elif isinstance(data, str):
            return cls.scrub_text(data)

        else:
            return data

    @classmethod
    def contains_secret(cls, data: Any) -> bool:
        """Checks if a string, dict, or list contains unredacted secrets."""
        if isinstance(data, str):
            for pattern in SECRET_PATTERNS:
                m = pattern.search(data)
                if m:
                    matched_str = m.group(0)
                    if not ("$json" in matched_str or "$node" in matched_str or "$parameter" in matched_str):
                        return True
            return False

        elif isinstance(data, dict):
            for k, v in data.items():
                lower_k = str(k).lower()
                if any(sec in lower_k for sec in ("password", "secret", "token", "apikey", "api_key")):
                    if isinstance(v, str) and not (v.startswith("={{") or "$json" in v or v == "[REDACTED_SECRET]"):
                        return True
                if cls.contains_secret(v):
                    return True
            return False

        elif isinstance(data, list):
            return any(cls.contains_secret(item) for item in data)

        return False
