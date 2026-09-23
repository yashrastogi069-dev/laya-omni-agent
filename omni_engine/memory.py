"""
Persistent Continuous Memory & Self-Improving Experience Cache
- Schema normalization & backward compatibility with explicit schema_version
- Atomic persistence to avoid zero-byte crash corruption
- Quarantining of corrupted files to preserve historical data
- Explicit three-state outcome tracking:
    * VERIFIED_SUCCESS (True)
    * VERIFIED_FAILURE (False)
    * UNVERIFIED (None) - Default state; execution NEVER automatically implies success.
"""

import os
import json
import time
import shutil

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_PATH = os.path.join(WORKSPACE_ROOT, "memory", "omni_memory.json")
os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
# Continuous memory storage format schema version (intentionally decoupled from application versioning)
SCHEMA_VERSION = "2.5.0"

class OmniMemory:
    def __init__(self, filepath=MEMORY_PATH):
        self.filepath = filepath
        self.schema_version = SCHEMA_VERSION
        self.data = self._load()

    def _load(self) -> dict:
        """Loads memory from JSON with backward-compatible key migration and corruption quarantining."""
        defaults = {
            "schema_version": self.schema_version,
            "version": self.schema_version,
            "total_missions": 0,
            "missions": [],
            "invocation_count": {},
            "verified_success_count": {},
            "verified_failure_count": {},
            "unverified_count": {},
            # Backward-compatible mirrors
            "tool_invocations": {},
            "tool_success_counts": {},
            "learned_insights": {},
        }

        if os.path.exists(self.filepath):
            content = ""
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    data = json.loads(content)
                    if isinstance(data, dict):
                        # Migrate legacy schema keys
                        if "tool_effectiveness" in data and "verified_success_count" not in data:
                            data["verified_success_count"] = data.pop("tool_effectiveness", {})
                        if "learned_facts" in data and "learned_insights" not in data:
                            data["learned_insights"] = data.pop("learned_facts", {})

                        # Synchronize backward-compatible mirrors
                        if "tool_success_counts" not in data:
                            data["tool_success_counts"] = dict(data.get("verified_success_count", {}))
                        if "tool_invocations" not in data:
                            data["tool_invocations"] = dict(data.get("invocation_count", {}))

                        # Ensure all expected keys exist
                        for k, v in defaults.items():
                            data.setdefault(k, v)
                        data["schema_version"] = self.schema_version
                        return data
            except Exception as e:
                # File exists and is non-empty, but failed to parse as valid JSON.
                # Quarantine the corrupted file to prevent permanent data loss!
                corrupt_backup = f"{self.filepath}.corrupt.{int(time.time())}"
                try:
                    shutil.copy2(self.filepath, corrupt_backup)
                    print(f"⚠️ Corrupted memory file preserved at: {corrupt_backup} (Error: {e})")
                except Exception as copy_err:
                    print(f"⚠️ Failed to quarantine corrupted memory file: {copy_err}")

        return defaults

    def save(self):
        """Atomically persists memory to disk using a temporary file and replace."""
        tmp_path = self.filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self.filepath)
        except Exception as e:
            print(f"⚠️ Memory save error: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def recall(self, query: str) -> list:
        """Finds past relevant missions to improve current execution."""
        words = [w.lower() for w in query.split() if len(w) > 3]
        matches = []
        for m in self.data.get("missions", []):
            if any(w in m.get("query", "").lower() for w in words):
                matches.append(m)
        return matches[-3:]

    def record_mission(self, query: str, tool: str, summary: str, verified_success: bool | None = None):
        """Records mission execution telemetry and explicit verification status.
        
        verified_success semantics:
          - True: VERIFIED_SUCCESS
          - False: VERIFIED_FAILURE
          - None: UNVERIFIED (Default; execution NEVER automatically implies success)
        """
        self.data["total_missions"] += 1

        # Track overall tool invocations
        inv_counts = self.data.setdefault("invocation_count", {})
        inv_counts[tool] = inv_counts.get(tool, 0) + 1
        self.data.setdefault("tool_invocations", {})[tool] = inv_counts[tool]

        # Resolve outcome status
        if verified_success is True:
            outcome_status = "VERIFIED_SUCCESS"
            succ_counts = self.data.setdefault("verified_success_count", {})
            succ_counts[tool] = succ_counts.get(tool, 0) + 1
            self.data.setdefault("tool_success_counts", {})[tool] = succ_counts[tool]
        elif verified_success is False:
            outcome_status = "VERIFIED_FAILURE"
            fail_counts = self.data.setdefault("verified_failure_count", {})
            fail_counts[tool] = fail_counts.get(tool, 0) + 1
        else:
            outcome_status = "UNVERIFIED"
            unver_counts = self.data.setdefault("unverified_count", {})
            unver_counts[tool] = unver_counts.get(tool, 0) + 1

        self.data["missions"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "tool": tool,
            "summary": summary[:300],
            "outcome_status": outcome_status,
            "verified_success": verified_success,
        })
        self.data["missions"] = self.data["missions"][-150:]
        self.save()

    def get_stats(self) -> str:
        invocations = self.data.get("invocation_count", {})
        successes = self.data.get("verified_success_count", {})
        failures = self.data.get("verified_failure_count", {})
        unverified = self.data.get("unverified_count", {})

        top_tools = sorted(invocations.items(), key=lambda x: x[1], reverse=True)[:5]

        stats = (
            f"### Continuous Memory Statistics (Schema v{self.data.get('schema_version', '2.5.0')})\n"
            f"- **Total Missions Logged**: {self.data.get('total_missions', 0)}\n"
            f"- **Top Executed Tools**:\n"
        )
        for t, total in top_tools:
            succ = successes.get(t, 0)
            fail = failures.get(t, 0)
            unv = unverified.get(t, 0)
            rate = (succ / total * 100) if total > 0 else 0
            stats += f"  - `{t}`: {total} runs (✅ {succ} verified, ❌ {fail} failed, ⏳ {unv} unverified | {rate:.0f}% verified success rate)\n"
        if not top_tools:
            stats += "  *(No tools executed yet)*\n"
        return stats
