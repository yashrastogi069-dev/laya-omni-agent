"""
omni_engine.research.sanitizer
==============================
Prompt-Injection Defense and Untrusted Content Sanitizer for Web Research.

Adheres to Prime Directive & Repository Invariants:
- Prompt Injection Defenses (docs/SECURITY_AND_POLICY.md): External web pages are
  classified strictly as UNTRUSTED DATA.
- REQ-B4 Adversarial Plan Resolution:
  1. NFKC unicode normalization to neutralize homoglyph attacks.
  2. Complete removal of zero-width and invisible control characters.
  3. Strict XML tag escaping (&lt; and &gt;) preventing synthetic tag termination.
  4. Encapsulation inside rigid `<untrusted_external_data>` boundary framing.
"""

import hashlib
import re
import unicodedata
from typing import Tuple

# Zero-width and invisible formatting characters used for evasion
_ZERO_WIDTH_CHARS = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u202a-\u202e]")

# ASCII control codes (0x00 to 0x1F excluding \t, \n, \r)
_CONTROL_CODES = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Common prompt injection and instruction override patterns to neutralize
_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+(?:override|prompt|reset)\b", re.IGNORECASE),
    re.compile(r"\byou\s+are\s+now\s+(?:a|an|in)\s+(?:developer\s+mode|dan|unrestricted)\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:safety|guidelines|rules)\b", re.IGNORECASE),
    re.compile(r"\bprint\s+your\s+(?:initial\s+)?(?:system\s+)?prompt\b", re.IGNORECASE),
]


def clean_web_text(text: str) -> str:
    """Cleans, normalizes, and strips invisible evasion characters from raw web text."""
    if not text:
        return ""

    # 1. NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Strip zero-width characters
    stripped = _ZERO_WIDTH_CHARS.sub("", normalized)

    # 3. Strip non-printable ASCII control characters
    stripped = _CONTROL_CODES.sub(" ", stripped)

    # 4. Neutralize known overt prompt injection patterns with benign placeholder
    for pattern in _INJECTION_PATTERNS:
        stripped = pattern.sub("[FILTERED_INSTRUCTION_OVERRIDE]", stripped)

    return stripped.strip()


def sanitize_untrusted_web_content(
    raw_text: str,
    origin_url: str,
    escape_html_tags: bool = True,
) -> Tuple[str, str]:
    """Applies defense-in-depth sanitization and encapsulates content in sandboxed XML tags.

    Returns:
    - encapsulated_envelope: The fully framed text inside `<untrusted_external_data>` tags.
    - content_hash: SHA-256 hash of the cleaned text.
    """
    cleaned = clean_web_text(raw_text)

    # Escape literal XML characters to prevent synthetic closing tag attacks (REQ-B4)
    if escape_html_tags:
        escaped = (
            cleaned.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
    else:
        escaped = cleaned

    content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    safe_origin = origin_url.replace("<", "").replace(">", "").replace('"', "")

    envelope = (
        f'<untrusted_external_data origin="{safe_origin}" hash="{content_hash}">\n'
        f"{escaped}\n"
        f"</untrusted_external_data>"
    )

    return envelope, content_hash
