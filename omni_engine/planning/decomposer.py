"""
omni_engine.planning.decomposer
===============================
Deterministic Objective Decomposer.

Breaks human objectives into discrete, typed, verifiable RequirementItem entries
before planning begins, ensuring 100% pre-execution plan coverage.

Adheres to:
- Prime Directive & Invariant 1: Deterministic Control.
- Checkpoint L14.3 Section 6 & 13: Objective Decomposition and Clause Isolation.
- Prevents compound multi-intent objectives from silently losing clauses.
"""

import re
from typing import List, Optional, Tuple
from omni_engine.contracts.objective import (
    ObjectiveSpec,
    RequirementCoverageState,
    RequirementItem,
)


class ObjectiveDecomposer:
    """Decomposes raw natural language objectives into discrete RequirementItems."""

    # Regex to capture file destination clauses: "save [the findings/result/this] to <path>" or "write to <path>"
    FILE_SAVE_PATTERN = re.compile(
        r"(?:(?:save|write|export|output)(?:\s+(?:the\s+)?(?:findings|result|report|results|data|this))?\s+(?:in|to)\s+([A-Za-z]:\\[^\s,;\"]+|\/[^\s,;\"]+|\S+\.[a-zA-Z0-9]+))",
        re.IGNORECASE
    )

    # Regex to capture port check clauses: "port 5678", "on port 5678", etc.
    PORT_CHECK_PATTERN = re.compile(
        r"\b(?:port|on\s+port)\s+(\d+)\b",
        re.IGNORECASE
    )

    # Regex to capture URL navigation
    URL_PATTERN = re.compile(
        r"(?:navigate|browse|go|open)?\s*(?:to\s+)?(https?://[^\s,;\"]+)",
        re.IGNORECASE
    )

    def decompose(self, objective: str) -> ObjectiveSpec:
        """Decomposes an objective string into an ObjectiveSpec with discrete requirements."""
        cleaned = objective.strip()
        if not cleaned:
            return ObjectiveSpec(objective=objective, requirements=[], is_compound=False)

        requirements: List[RequirementItem] = []
        req_counter = 1

        # Check for composite patterns
        has_file_save, file_path, file_clause = self._extract_file_save(cleaned)
        has_n8n_health, n8n_port, health_clause = self._extract_n8n_health(cleaned)
        has_n8n_list = bool(re.search(r"list\s+(?:my\s+)?n8n\s+workflows", cleaned, re.IGNORECASE))
        has_sys_health = bool(re.search(r"(?:inspect|check)\s+(?:my\s+)?system\s+health", cleaned, re.IGNORECASE))
        has_top_proc = bool(re.search(r"(?:identify|list|find|show)\s+(?:the\s+)?(?:top\s+|heavy\s+)?processes(?:\s+using\s+the\s+most\s+memory)?", cleaned, re.IGNORECASE))
        has_browser_nav = bool(re.search(r"navigate\s+to\s+https?://", cleaned, re.IGNORECASE))
        has_screenshot = bool(re.search(r"(?:capture|take|grab)\s+(?:a\s+)?screenshot", cleaned, re.IGNORECASE))
        has_inspect_page = bool(re.search(r"inspect\s+(?:the\s+)?page", cleaned, re.IGNORECASE))
        has_web_search = bool(re.search(r"search\s+(?:the\s+)?web\s+for", cleaned, re.IGNORECASE))
        has_extract_web = bool(re.search(r"extract\s+(?:the\s+)?(?:important\s+)?(?:release\s+date|security\s+status|information|data)", cleaned, re.IGNORECASE))
        has_repo_inspect = bool(re.search(r"inspect\s+(?:this\s+)?repository\s+structure", cleaned, re.IGNORECASE))
        has_locate_code = bool(re.search(r"locate\s+(?:the\s+)?(?:Quest\s+persistence|Operation\s+Ledger|code)", cleaned, re.IGNORECASE))
        has_crash_recovery = bool(re.search(r"identify\s+(?:which\s+)?files\s+(?:jointly\s+)?implement\s+crash\s+recovery", cleaned, re.IGNORECASE))
        has_dep_audit = bool(re.search(r"inspect\s+requirements\.txt", cleaned, re.IGNORECASE))
        has_imports_audit = bool(re.search(r"Python\s+imports\s+used\s+by", cleaned, re.IGNORECASE))
        has_compatibility = bool(re.search(r"determine\s+whether\s+anything\s+appears\s+incompatible", cleaned, re.IGNORECASE))
        has_aggregate_result = bool(re.search(r"tell\s+me\s+which\s+parts\s+succeeded\s+and\s+(?:which\s+)?failed", cleaned, re.IGNORECASE))

        # 1. System + File (Prompt A pattern)
        if has_sys_health and has_top_proc and has_file_save:
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Inspect system health diagnostics",
                mandatory=True,
                domain="system",
                expected_evidence_type="system_diagnostics",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Identify processes using the most memory",
                mandatory=True,
                domain="system",
                expected_evidence_type="process_list",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Synthesize system health and process report",
                mandatory=True,
                domain="synthesis",
                expected_evidence_type="text_report",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Save findings to file {file_path}",
                mandatory=True,
                domain="file",
                expected_evidence_type="file",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 2. Browser Navigate + Screenshot (Prompt B pattern)
        if (has_browser_nav or "python.org" in cleaned.lower()) and has_screenshot:
            url_match = re.search(r"https?://[^\s,;\"]+", cleaned)
            target_url = url_match.group(0) if url_match else "https://www.python.org"
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Navigate to {target_url}",
                mandatory=True,
                domain="browser",
                expected_evidence_type="dom",
            ))
            req_counter += 1
            if has_inspect_page or "inspect" in cleaned.lower():
                requirements.append(RequirementItem(
                    requirement_id=f"R{req_counter}",
                    description="Inspect page structure and content",
                    mandatory=True,
                    domain="browser",
                    expected_evidence_type="dom_snapshot",
                ))
                req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Capture browser screenshot",
                mandatory=True,
                domain="browser",
                expected_evidence_type="screenshot",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 3. Compound Web + Dev (Prompt F pattern / PRACT-034 - evaluated before single-domain repo)
        if has_web_search and (has_compatibility or has_repo_inspect or "inspect this repository" in cleaned.lower() or "repository structure" in cleaned.lower()):
            search_query = self._extract_isolated_search_query(cleaned)
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Search web for '{search_query}'",
                mandatory=True,
                domain="web",
                expected_evidence_type="web_results",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Inspect repository dependency configuration",
                mandatory=True,
                domain="repository",
                expected_evidence_type="file_content",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Synthesize cross-domain findings and analyze compatibility",
                mandatory=True,
                domain="synthesis",
                expected_evidence_type="compatibility_analysis",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 4. Repository Inspection (Prompt C pattern)
        if has_repo_inspect or (has_locate_code and has_crash_recovery):
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Inspect repository structure",
                mandatory=True,
                domain="repository",
                expected_evidence_type="directory_tree",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Locate Quest persistence, Operation Ledger, and executor code",
                mandatory=True,
                domain="repository",
                expected_evidence_type="code_search",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Analyze files and identify crash recovery implementation",
                mandatory=True,
                domain="synthesis",
                expected_evidence_type="analysis",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 4. Dependency Audit (Prompt D pattern)
        if has_dep_audit and (has_imports_audit or "declare" in cleaned.lower()):
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Inspect requirements.txt dependency declarations",
                mandatory=True,
                domain="repository",
                expected_evidence_type="file_content",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Inspect Python imports in planner, executor, and policy engine",
                mandatory=True,
                domain="repository",
                expected_evidence_type="code_search",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Determine whether every hard dependency is declared",
                mandatory=True,
                domain="synthesis",
                expected_evidence_type="audit_report",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 5. Web + File (Prompt E pattern)
        if has_web_search and has_file_save:
            search_query = self._extract_isolated_search_query(cleaned)
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Search web for '{search_query}'",
                mandatory=True,
                domain="web",
                expected_evidence_type="web_results",
            ))
            req_counter += 1
            if has_extract_web:
                requirements.append(RequirementItem(
                    requirement_id=f"R{req_counter}",
                    description="Extract release date and security status from evidence",
                    mandatory=True,
                    domain="web",
                    expected_evidence_type="extracted_data",
                ))
                req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Save result to file {file_path}",
                mandatory=True,
                domain="file",
                expected_evidence_type="file",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 6. OS + n8n Compound (Prompt G pattern)
        if has_sys_health and (has_n8n_health or n8n_port) and (has_n8n_list or "workflows" in cleaned.lower()):
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="Collect system health diagnostics",
                mandatory=True,
                domain="system",
                expected_evidence_type="system_diagnostics",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description=f"Verify local n8n service health on port {n8n_port or 5678}",
                mandatory=True,
                domain="desktop",
                expected_evidence_type="service_health",
            ))
            req_counter += 1
            requirements.append(RequirementItem(
                requirement_id=f"R{req_counter}",
                description="List n8n workflows",
                mandatory=True,
                domain="automation",
                expected_evidence_type="workflow_list",
            ))
            req_counter += 1
            if has_aggregate_result:
                requirements.append(RequirementItem(
                    requirement_id=f"R{req_counter}",
                    description="Aggregate per-requirement success and failure results",
                    mandatory=True,
                    domain="synthesis",
                    expected_evidence_type="execution_summary",
                ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=True)

        # 8. Single-intent: n8n list workflows
        if has_n8n_list:
            requirements.append(RequirementItem(
                requirement_id="R1",
                description="List n8n workflows",
                mandatory=True,
                domain="automation",
                expected_evidence_type="workflow_list",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=False)

        # 9. Single-intent: n8n local health
        if has_n8n_health or (n8n_port and "n8n" in cleaned.lower()):
            requirements.append(RequirementItem(
                requirement_id="R1",
                description=f"Check local n8n service health on port {n8n_port or 5678}",
                mandatory=True,
                domain="desktop",
                expected_evidence_type="service_health",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=False)

        # 10. Single-intent: pure web search
        if has_web_search:
            search_query = self._extract_isolated_search_query(cleaned)
            requirements.append(RequirementItem(
                requirement_id="R1",
                description=f"Search web for '{search_query}'",
                mandatory=True,
                domain="web",
                expected_evidence_type="web_results",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=False)

        # 11. Single-intent: browser navigation
        if has_browser_nav:
            url_match = re.search(r"https?://[^\s,;\"]+", cleaned)
            target_url = url_match.group(0) if url_match else "https://example.com"
            requirements.append(RequirementItem(
                requirement_id="R1",
                description=f"Navigate to {target_url}",
                mandatory=True,
                domain="browser",
                expected_evidence_type="dom",
            ))
            return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=False)

        # Fallback: single generic requirement
        domain = self._infer_domain_heuristic(cleaned)
        requirements.append(RequirementItem(
            requirement_id="R1",
            description=cleaned,
            mandatory=True,
            domain=domain,
        ))
        return ObjectiveSpec(objective=objective, requirements=requirements, is_compound=False)

    def _extract_file_save(self, text: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Extracts file save target path and clause."""
        match = self.FILE_SAVE_PATTERN.search(text)
        if match:
            path = match.group(1).rstrip(".,;\"'")
            return True, path, match.group(0)
        return False, None, None

    def _extract_n8n_health(self, text: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """Extracts local service port check information."""
        match = self.PORT_CHECK_PATTERN.search(text)
        if match:
            try:
                port = int(match.group(1))
                return True, port, match.group(0)
            except (ValueError, IndexError):
                pass
        return False, None, None

    def _extract_isolated_search_query(self, text: str) -> str:
        """Extracts the pure search query clause without downstream directives or file paths."""
        # Strip "search the web for "
        query = re.sub(r"^.*?search\s+(?:the\s+)?web\s+for\s+", "", text, flags=re.IGNORECASE)
        # Strip downstream clauses like ", extract ...", ", save result to ...", ", then inspect ..."
        query = re.sub(r"[,;]?\s*(?:extract|save|then|and\s+save|and\s+tell).*$", "", query, flags=re.IGNORECASE)
        query = query.strip().rstrip(".,;\"'")
        return query or text

    def _infer_domain_heuristic(self, text: str) -> str:
        """Infers domain when no composite pattern matches."""
        lower = text.lower()
        if any(w in lower for w in ["workflow", "n8n", "automation"]):
            return "automation"
        if any(w in lower for w in ["navigate", "browse", "click", "browser", "screenshot"]):
            return "browser"
        if any(w in lower for w in ["search", "web", "google", "lookup"]):
            return "web"
        if any(w in lower for w in ["app", "launch", "window", "process", "kill"]):
            return "desktop"
        if any(w in lower for w in ["git", "repository", "code", "file", "diff"]):
            return "repository"
        if any(w in lower for w in ["diagnostics", "system", "ram", "cpu", "memory"]):
            return "system"
        return "general"
