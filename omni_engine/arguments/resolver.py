"""
omni_engine.arguments.resolver
==============================
Master Capability Argument Resolver and Schema Validator.

Adheres to Prime Directive & Repository Invariants:
- Invariant 1: Deterministic Control — Arguments must strictly conform to CapabilitySpec.input_schema.
- Invariant 3: Minimize Generative Invocations — Deterministic extractors (<1ms) resolve routine requests.
- Invariant 4: Strongly Typed Contracts — Emits structured ArgumentResolutionEnvelope.
- Invariant 6: Evidence-Based — Missing required slots trigger user clarification, never hallucinatory defaults.
"""

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from omni_engine.contracts.arguments import (
    ArgumentExtractionSource,
    ArgumentResolutionEnvelope,
    ArgumentSlot,
)
from omni_engine.contracts.capability import CapabilitySpec
from omni_engine.providers.base import GenerativeProvider

from .extractors import (
    extract_app_name,
    extract_clipboard_data,
    extract_file_path,
    extract_math_expression,
    extract_pid,
    extract_ping_host,
    extract_powershell_script,
    extract_process_name,
    extract_python_code,
    extract_search_query,
    extract_sql_query,
    extract_url,
)


CLARIFICATION_PROMPTS: Dict[str, str] = {
    "file_read": "Which file path would you like to read?",
    "file_write": "Which file path and content would you like to write?",
    "kill_process": "Which process ID (PID) or process name would you like to terminate?",
    "launch_app": "Which application or service would you like to launch?",
    "scrape_url": "Which webpage URL would you like to scrape?",
    "visual_browse": "Which webpage URL would you like to navigate to?",
    "download_file": "Which URL and destination filename should be used for the download?",
    "http_api": "Which HTTP URL endpoint and method should be requested?",
    "ping_test": "Which host or IP address would you like to ping?",
    "sqlite_exec": "Which SQL query statement would you like to execute?",
    "safe_math": "Which mathematical expression would you like to calculate?",
    "search_code": "Which code search pattern or keyword are you looking for?",
    "inspect_data": "Which CSV or data file path would you like to inspect?",
    "deep_research": "What research topic or question would you like to investigate?",
    "research.deep": "What research topic or question would you like to investigate?",
}

PARAM_ALIASES: Dict[str, List[str]] = {
    "filepath": ["file_path", "path", "file"],
    "file_path": ["filepath", "path", "file"],
    "target": ["pid", "process_name", "app_name"],
    "query": ["pattern", "search_term", "sql"],
    "filename": ["save_path", "filepath", "file_path"],
    "save_path": ["filename", "filepath", "path"],
}


class ArgumentResolver:
    """Resolves and validates capability arguments against CapabilitySpec.input_schema."""

    def __init__(self, generative_provider: Optional[GenerativeProvider] = None) -> None:
        self.generative_provider = generative_provider

    def _extract_deterministic_slots(
        self,
        capability_id: str,
        prompt: str,
    ) -> Dict[str, ArgumentSlot]:
        """Runs specialized deterministic extractors matching canonical capability schemas."""
        slots: Dict[str, ArgumentSlot] = {}

        def _slot(name: str, val: Any, src: ArgumentExtractionSource, conf: float = 1.0) -> ArgumentSlot:
            return ArgumentSlot(
                name=name,
                value=val,
                is_resolved=val is not None,
                source=src,
                confidence=conf,
                raw_text=str(val) if val is not None else None,
            )

        # 1. Dev domain tools
        if capability_id == "file_read":
            path = extract_file_path(prompt)
            if path:
                slots["filepath"] = _slot("filepath", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)
                slots["file_path"] = _slot("file_path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "file_write":
            path = extract_file_path(prompt)
            if path:
                slots["filepath"] = _slot("filepath", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)
                slots["file_path"] = _slot("file_path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            # Content extraction: check quoted text or python code block
            code = extract_python_code(prompt)
            if code:
                slots["content"] = _slot("content", code, ArgumentExtractionSource.SYNTACTIC_AST)
            else:
                # Look for content: '...' or following content keyword
                import re
                c_match = re.search(r"""(?:content|text|with)\s*[:=]?\s*['"](.*?)['"]""", prompt, re.DOTALL | re.IGNORECASE)
                if c_match:
                    slots["content"] = _slot("content", c_match.group(1), ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "search_code":
            pat = extract_search_query(prompt)
            if pat:
                slots["query"] = _slot("query", pat, ArgumentExtractionSource.DETERMINISTIC_REGEX)
                slots["pattern"] = _slot("pattern", pat, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            path = extract_file_path(prompt)
            if path:
                slots["path"] = _slot("path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "directory_tree":
            path = extract_file_path(prompt)
            if path and path not in [".", "tree", "status", "info", "hierarchy", "structure"]:
                slots["path"] = _slot("path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            else:
                slots["path"] = _slot("path", ".", ArgumentExtractionSource.SCHEMA_DEFAULT)

        elif capability_id == "git_status":
            path = extract_file_path(prompt)
            slots["repo_path"] = _slot("repo_path", path or ".", ArgumentExtractionSource.DETERMINISTIC_REGEX if path else ArgumentExtractionSource.SCHEMA_DEFAULT)

        elif capability_id == "run_python":
            code = extract_python_code(prompt)
            if code:
                slots["code"] = _slot("code", code, ArgumentExtractionSource.SYNTACTIC_AST)

        # 2. Web domain tools
        elif capability_id in ("web_search", "deep_research", "research.deep"):
            q = extract_search_query(prompt) or prompt.strip()
            if q:
                slots["query"] = _slot("query", q, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "scrape_url":
            url = extract_url(prompt)
            if url:
                slots["url"] = _slot("url", url, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "http_api":
            url = extract_url(prompt)
            if url:
                slots["url"] = _slot("url", url, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            method = "GET"
            if "post" in prompt.lower():
                method = "POST"
            elif "put" in prompt.lower():
                method = "PUT"
            elif "delete" in prompt.lower():
                method = "DELETE"
            slots["method"] = _slot("method", method, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "download_file":
            url = extract_url(prompt)
            if url:
                slots["url"] = _slot("url", url, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            path = extract_file_path(prompt)
            if path:
                slots["filename"] = _slot("filename", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)
                slots["save_path"] = _slot("save_path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        # 3. Browser domain tools
        elif capability_id == "visual_browse":
            url = extract_url(prompt)
            if url:
                slots["url"] = _slot("url", url, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "browser_screenshot":
            url = extract_url(prompt)
            if url:
                slots["url"] = _slot("url", url, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        # 4. OS domain tools
        elif capability_id == "kill_process":
            pid = extract_pid(prompt)
            proc = extract_process_name(prompt)
            target_val = str(pid) if pid is not None else proc
            if target_val:
                slots["target"] = _slot("target", target_val, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            if pid is not None:
                slots["pid"] = _slot("pid", pid, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "launch_app":
            app = extract_app_name(prompt)
            if app:
                slots["app_name"] = _slot("app_name", app, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "list_processes":
            proc = extract_process_name(prompt)
            if proc:
                slots["filter_name"] = _slot("filter_name", proc, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "powershell":
            cmd = extract_powershell_script(prompt)
            if cmd:
                slots["command"] = _slot("command", cmd, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "ping_test":
            host = extract_ping_host(prompt)
            if host:
                slots["host"] = _slot("host", host, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "clipboard":
            action, text = extract_clipboard_data(prompt)
            slots["action"] = _slot("action", action, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            if text:
                slots["text"] = _slot("text", text, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "desktop_screenshot":
            path = extract_file_path(prompt)
            if path:
                slots["save_path"] = _slot("save_path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        # 5. Data domain tools
        elif capability_id == "sqlite_exec":
            sql = extract_sql_query(prompt)
            if sql:
                slots["query"] = _slot("query", sql, ArgumentExtractionSource.DETERMINISTIC_REGEX)
            db = extract_file_path(prompt)
            if db:
                slots["db_path"] = _slot("db_path", db, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "inspect_data":
            path = extract_file_path(prompt)
            if path:
                slots["file_path"] = _slot("file_path", path, ArgumentExtractionSource.DETERMINISTIC_REGEX)

        elif capability_id == "safe_math":
            expr = extract_math_expression(prompt)
            if expr:
                slots["expression"] = _slot("expression", expr, ArgumentExtractionSource.SYNTACTIC_AST)

        return slots

    def resolve(
        self,
        capability: Any,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> ArgumentResolutionEnvelope:
        """Resolves, normalizes, and validates capability arguments.
        
        Args:
            capability: Target CapabilitySpec or ExecutableCapability contract.
            prompt: User natural language instruction.
            context: Optional contextual parameters (e.g. active file, previous step output).
            request_id: Correlation request ID.
            
        Returns:
            ArgumentResolutionEnvelope containing arguments, slots, and validation status.
        """
        t0 = time.perf_counter()
        spec: CapabilitySpec = getattr(capability, "spec", capability)
        req_id = request_id or f"arg_{uuid.uuid4().hex[:8]}"
        schema = spec.input_schema or {}
        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        # 1. Deterministic Extraction Pass
        resolved_slots = self._extract_deterministic_slots(spec.id, prompt)

        # 2. Ingest parameters from explicit context if slot wasn't resolved by prompt
        if context:
            for prop_name in properties:
                if prop_name not in resolved_slots or not resolved_slots[prop_name].is_resolved:
                    candidates = [prop_name] + PARAM_ALIASES.get(prop_name, [])
                    for cand in candidates:
                        if cand in context and context[cand] is not None:
                            val = context[cand]
                            resolved_slots[prop_name] = ArgumentSlot(
                                name=prop_name,
                                value=val,
                                is_resolved=True,
                                source=ArgumentExtractionSource.CONTEXT_INHERITED,
                                confidence=1.0,
                                raw_text=str(val),
                            )
                            break

        # 3. Ingest schema defaults for optional unpopulated properties
        for prop_name, prop_meta in properties.items():
            if prop_name not in resolved_slots and "default" in prop_meta:
                resolved_slots[prop_name] = ArgumentSlot(
                    name=prop_name,
                    value=prop_meta["default"],
                    is_resolved=True,
                    source=ArgumentExtractionSource.SCHEMA_DEFAULT,
                    confidence=1.0,
                )

        # 4. Check for missing required slots
        missing_slots = [
            req_field for req_field in required_fields
            if req_field not in resolved_slots or not resolved_slots[req_field].is_resolved
        ]

        # 5. Generative Synthesis Fallback (if configured and required slots are missing)
        if missing_slots and self.generative_provider is not None:
            try:
                gen_prompt = (
                    f"Extract JSON arguments for capability '{spec.name}' from user request: '{prompt}'.\n"
                    f"Required JSON Schema properties: {json.dumps(properties)}"
                )
                from omni_engine.providers.generative import extract_json_from_text
                gen_result = self.generative_provider.generate_text(
                    prompt=gen_prompt,
                    temperature=0.0,
                    max_tokens=500,
                )
                cleaned = extract_json_from_text(gen_result.text)
                gen_res = json.loads(cleaned)
                if isinstance(gen_res, dict):
                    for k, v in gen_res.items():
                        target_prop = k if k in properties else None
                        if not target_prop:
                            for p in properties:
                                if k in PARAM_ALIASES.get(p, []):
                                    target_prop = p
                                    break
                        if target_prop and v is not None and target_prop not in resolved_slots:
                            resolved_slots[target_prop] = ArgumentSlot(
                                name=target_prop,
                                value=v,
                                is_resolved=True,
                                source=ArgumentExtractionSource.GENERATIVE_SYNTHESIS,
                                confidence=0.85,
                            )
                    # Re-compute missing slots after generative pass
                    missing_slots = [
                        req_field for req_field in required_fields
                        if req_field not in resolved_slots or not resolved_slots[req_field].is_resolved
                    ]
            except Exception:
                pass

        # 6. Build final arguments dictionary and validate
        arguments = {k: slot.value for k, slot in resolved_slots.items() if slot.is_resolved and k in properties}
        validation_errors: List[str] = []

        for req_field in missing_slots:
            validation_errors.append(f"Missing required argument '{req_field}' for capability '{spec.id}'")

        is_valid = len(missing_slots) == 0
        clarification_needed = not is_valid
        clarification_prompt = CLARIFICATION_PROMPTS.get(spec.id) if clarification_needed else None

        if clarification_needed and clarification_prompt is None:
            missing_names = ", ".join(missing_slots)
            clarification_prompt = f"Please specify the required parameter(s) ({missing_names}) for {spec.name}."

        t1 = time.perf_counter()
        latency_ms = round((t1 - t0) * 1000, 3)

        return ArgumentResolutionEnvelope(
            schema_version="1.0.0",
            request_id=req_id,
            capability_id=spec.id,
            arguments=arguments,
            resolved_slots=resolved_slots,
            is_valid=is_valid,
            validation_errors=validation_errors,
            clarification_needed=clarification_needed,
            clarification_prompt=clarification_prompt,
            missing_slots=missing_slots,
            latency_ms=latency_ms,
            metadata={
                "deterministic_path": all(
                    s.source in [ArgumentExtractionSource.DETERMINISTIC_REGEX, ArgumentExtractionSource.SYNTACTIC_AST, ArgumentExtractionSource.SCHEMA_DEFAULT]
                    for s in resolved_slots.values()
                ),
                "resolved_count": len(arguments),
                "required_count": len(required_fields),
            },
        )
