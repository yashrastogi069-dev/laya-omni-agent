"""
omni_engine.policy.rules
========================
Canonical safety rules, path canonicalization, protected resource boundaries,
and embedded command scanners for the deterministic policy engine.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Safety checks execute via pure code before LLMs or tools.
- Invariant 3 in AGENTS.md: Forbidden Operations — git reset --hard, git clean -fd, force push, root wiping are strictly blocked.
- Sub-1ms Latency SLA: Fast static string and regex matching without expensive OS process enumeration.
"""

import os
import pathlib
import re
from typing import Any, List, Optional, Tuple

from omni_engine.contracts.enums import ActionClass
from omni_engine.contracts.policy import PolicyEffect, PolicyRule


# ---------------------------------------------------------------------------
# 1. Path Canonicalization & Protection
# ---------------------------------------------------------------------------

# Static protected path substrings / prefixes (canonicalized lower case)
PROTECTED_PATH_SUBSTRINGS = [
    r"\windows\system32",
    r"\windows\syswow64",
    r"\windows\system",
    r"\windows\regedit.exe",
    r"\windows",
    r"\program files",
    r"\program files (x86)",
    r"\.ssh",
    r"\.env",
    r"\id_rsa",
    r"\id_ed25519",
    r"\known_hosts",
    "/etc",
    "/usr",
    "/boot",
    "/bin",
    "/sbin",
]

SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    "known_hosts",
    "authorized_keys",
    "credentials.json",
    "service_account.json",
    "secret.key",
    "private.key",
    "server.key",
}

SENSITIVE_EXTENSIONS = {".pem", ".key", ".pfx", ".p12"}


def canonicalize_path(raw_path: str, base_dir: Optional[str] = None) -> str:
    """Deterministically normalizes, expands, and canonicalizes any file/dir path on Windows.
    
    Guarantees elimination of \\?\\ prefixes, 8.3 aliases, traversal (..),
    environment variables, user tilde, and casing discrepancies.
    """
    if not raw_path or not isinstance(raw_path, str):
        return ""

    # 1. Strip surrounding quotes and whitespace
    clean = raw_path.strip().strip('"').strip("'")
    if not clean:
        return ""

    # 2. Strip Windows extended length device prefixes (\\?\, \\.\, \\?\UNC\) EARLY
    # to ensure downstream pattern matchers work and prevent network SMB hangs during resolution
    if clean.startswith("\\\\?\\UNC\\") or clean.startswith("//?/UNC/"):
        clean = "\\\\" + clean[8:]
    elif clean.startswith("\\\\?\\") or clean.startswith("//?/"):
        clean = clean[4:]
    elif clean.startswith("\\\\.\\") or clean.startswith("//./"):
        clean = clean[4:]

    # 3. Expand user home (~) and environment variables (%WINDIR%, %SYSTEMROOT%, etc.)
    expanded = os.path.expandvars(os.path.expanduser(clean))

    # 4. Handle Localhost UNC admin share conversion:
    # \\localhost\admin$ -> %SystemRoot% (C:\Windows)
    # \\localhost\c$ -> C:\
    unc_admin_share = re.match(r"^\\\\(?:localhost|127\.0\.0\.1)\\admin\$(?:\\(.*))?$", expanded, re.IGNORECASE)
    if unc_admin_share:
        sub = unc_admin_share.group(1) or ""
        sys_root = os.environ.get("SystemRoot", "C:\\Windows")
        expanded = os.path.join(sys_root, sub) if sub else sys_root
    else:
        unc_drive_share = re.match(r"^\\\\(?:localhost|127\.0\.0\.1)\\([a-zA-Z])\$(?:\\(.*))?$", expanded, re.IGNORECASE)
        if unc_drive_share:
            drive_letter = unc_drive_share.group(1)
            sub = unc_drive_share.group(2) or ""
            expanded = f"{drive_letter}:\\{sub}" if sub else f"{drive_letter}:\\"

    # 5. Resolve path through pathlib or static normpath
    # Critical: Do NOT call pathlib.Path.resolve() on network UNC paths (\\host\share)
    # because it attempts SMB host discovery and can block the thread for 30+ seconds!
    if expanded.startswith("\\\\") or expanded.startswith("//"):
        resolved = os.path.normpath(expanded)
    else:
        try:
            p = pathlib.Path(expanded)
            if not p.is_absolute() and base_dir:
                p = pathlib.Path(base_dir) / p
            resolved = str(p.resolve())
        except Exception:
            resolved = os.path.abspath(expanded)

    # 6. Normalize separators and casefold for Windows case-insensitivity
    # Strip any lingering extended prefix if pathlib.resolve() re-added it
    if resolved.startswith("\\\\?\\UNC\\"):
        resolved = "\\\\" + resolved[8:]
    elif resolved.startswith("\\\\?\\") or resolved.startswith("\\\\.\\"):
        resolved = resolved[4:]

    return os.path.normpath(resolved).lower()


def is_protected_path(path_str: str) -> Tuple[bool, Optional[str]]:
    """Checks whether a target path violates system protected path boundaries."""
    if not path_str:
        return False, None

    canon = canonicalize_path(path_str)
    if not canon:
        return False, None

    # Check root filesystem direct targets (e.g. "c:\", "c:", "/")
    if re.match(r"^[a-zA-Z]:\\?$", canon) or canon == "/":
        return True, f"Targeting root drive '{path_str}' is strictly forbidden."

    # Check protected path substrings
    for prot in PROTECTED_PATH_SUBSTRINGS:
        if prot in canon or canon.startswith(prot):
            return True, f"Target path '{path_str}' is within protected system directory '{prot}'."

    # Check sensitive filename patterns
    basename = os.path.basename(canon)
    if basename in SENSITIVE_FILE_NAMES:
        return True, f"Target file '{path_str}' matches sensitive credential/key pattern '{basename}'."

    _, ext = os.path.splitext(basename)
    if ext in SENSITIVE_EXTENSIONS:
        return True, f"Target file '{path_str}' has sensitive certificate/key extension '{ext}'."

    return False, None


# ---------------------------------------------------------------------------
# 2. Static Protected OS Processes
# ---------------------------------------------------------------------------

PROTECTED_PIDS = {0, 4, "0", "4"}

PROTECTED_PROCESS_NAMES = {
    "csrss",
    "csrss.exe",
    "lsass",
    "lsass.exe",
    "smss",
    "smss.exe",
    "services",
    "services.exe",
    "wininit",
    "wininit.exe",
    "winlogon",
    "winlogon.exe",
    "system",
    "system idle process",
}


def is_protected_process(target: Any) -> Tuple[bool, Optional[str]]:
    """Checks whether a target PID or process name is a critical system process."""
    if target is None:
        return False, None

    target_str = str(target).strip().lower()

    if target in PROTECTED_PIDS or target_str in PROTECTED_PIDS:
        return True, f"Process ID '{target}' is a critical OS kernel process and cannot be terminated."

    clean_name = target_str.rstrip(".exe")
    if clean_name in PROTECTED_PROCESS_NAMES or target_str in PROTECTED_PROCESS_NAMES:
        return True, f"Process '{target}' is a critical Windows system service and cannot be terminated."

    return False, None


# ---------------------------------------------------------------------------
# 3. Embedded Command Scanners (Regex)
# ---------------------------------------------------------------------------

RE_FORBIDDEN_GIT_COMMANDS = [
    # git reset --hard or git reset <ref> --hard
    re.compile(r"""\bgit\s+reset\b[^;\n]*\s+--hard\b""", re.IGNORECASE),
    # git clean with -f and -d (combined like -fd, -df, -xdf, -dxf, or separated -f -d, -d -f)
    re.compile(r"""\bgit\s+clean\b[^;\n]*-(?:[a-zA-Z]*f[a-zA-Z]*d|[a-zA-Z]*d[a-zA-Z]*f)\b""", re.IGNORECASE),
    re.compile(r"""\bgit\s+clean\b[^;\n]*-[a-zA-Z]*f\b[^;\n]*-[a-zA-Z]*d\b""", re.IGNORECASE),
    re.compile(r"""\bgit\s+clean\b[^;\n]*-[a-zA-Z]*d\b[^;\n]*-[a-zA-Z]*f\b""", re.IGNORECASE),
    # git push force (--force, --force-with-lease, -f, --delete, or +refspec)
    re.compile(r"""\bgit\s+push\b[^;\n]*(?:--(?:force|delete)\b|-(?:[a-zA-Z]*f|[a-zA-Z]*d)\b|\+[a-zA-Z0-9_/-]+)""", re.IGNORECASE),
]

RE_DESTRUCTIVE_SYSTEM_COMMANDS = [
    re.compile(r"""\brmdir\s+(?:/[sS]\s+/[qQ]|/[qQ]\s+/[sS])\s+[a-zA-Z]:\\?""", re.IGNORECASE),
    re.compile(r"""\bformat(?:-volume)?\s+[a-zA-Z]:""", re.IGNORECASE),
    re.compile(r"""\brm\s+-(?:rf|fr)\s+/(?:\s|$|[\*])""", re.IGNORECASE),
    re.compile(r"""\bdel\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\?""", re.IGNORECASE),
    re.compile(r"""\b(?:Remove-Item|ri|rm)\s+[^;\n]*-(?:Recurse|r)\b[^;\n]*[a-zA-Z]:\\?""", re.IGNORECASE),
    re.compile(r"""\bStop-Process\s+-(?:Name\s+)?(?:csrss|lsass|smss|services)\b""", re.IGNORECASE),
]


def scan_embedded_commands(text: str) -> Tuple[bool, Optional[str]]:
    """Scans command strings, python code, or shell one-liners for hard-forbidden operations."""
    if not text or not isinstance(text, str):
        return False, None

    for pattern in RE_FORBIDDEN_GIT_COMMANDS:
        if pattern.search(text):
            return True, f"Forbidden git command (git reset --hard, git clean -fd, or force push) detected (violates Invariant 3 in AGENTS.md): '{pattern.pattern}'"

    for pattern in RE_DESTRUCTIVE_SYSTEM_COMMANDS:
        if pattern.search(text):
            return True, f"Destructive system command detected (violates system safety policy): '{pattern.pattern}'"

    return False, None


# ---------------------------------------------------------------------------
# 4. Canonical System Hard Invariant Rules (Tier 0)
# ---------------------------------------------------------------------------

SYSTEM_HARD_RULES: List[PolicyRule] = [
    PolicyRule(
        rule_id="RULE_0_FORBIDDEN_GIT_MUTATIONS",
        name="Forbidden Destructive Git Operations",
        description="Strictly blocks git reset --hard, git clean -fd, and force-push over remote branches.",
        effect=PolicyEffect.DENY,
        action_classes=[ActionClass.SYSTEM_ACTION, ActionClass.LOCAL_DELETE],
        forbidden_patterns=[
            r"\bgit\s+reset\b[^;\n]*\s+--hard\b",
            r"\bgit\s+clean\b[^;\n]*-(?:[a-zA-Z]*f[a-zA-Z]*d|[a-zA-Z]*d[a-zA-Z]*f)\b",
            r"\bgit\s+clean\b[^;\n]*-[a-zA-Z]*f\b[^;\n]*-[a-zA-Z]*d\b",
            r"\bgit\s+clean\b[^;\n]*-[a-zA-Z]*d\b[^;\n]*-[a-zA-Z]*f\b",
            r"\bgit\s+push\b[^;\n]*(?:--(?:force|delete)\b|-(?:[a-zA-Z]*f|[a-zA-Z]*d)\b|\+[a-zA-Z0-9_/-]+)",
        ],
        priority=0,
        is_active=True,
    ),
    PolicyRule(
        rule_id="RULE_0_PROTECTED_SYSTEM_PATHS",
        name="Protected System Paths Boundary",
        description="Blocks modification, writing, or deletion targeting Windows system folders or root drives.",
        effect=PolicyEffect.DENY,
        action_classes=[ActionClass.LOCAL_CREATE, ActionClass.LOCAL_UPDATE, ActionClass.LOCAL_DELETE, ActionClass.SYSTEM_ACTION],
        target_paths=PROTECTED_PATH_SUBSTRINGS,
        priority=1,
        is_active=True,
    ),
    PolicyRule(
        rule_id="RULE_0_PROTECTED_SYSTEM_PROCESSES",
        name="Critical System Process Protection",
        description="Blocks terminating essential OS processes (csrss, lsass, smss, services, PID 0/4).",
        effect=PolicyEffect.DENY,
        action_classes=[ActionClass.SYSTEM_ACTION],
        priority=2,
        is_active=True,
    ),
]
