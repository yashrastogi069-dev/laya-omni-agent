"""
Persistent Continuous Memory & Self-Improving Experience Cache
- Schema normalization & backward compatibility
- Atomic persistence to avoid zero-byte crash corruption
- Verified outcome tracking (distinguishing execution from verified success)
"""

import os
import json
import time

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_PATH = os.path.join(WORKSPACE_ROOT, "memory", "omni_memory.json")
os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)

class OmniMemory:
    def __init__(self, filepath=MEMORY_PATH):
        self.filepath = filepath
        self.data = self._load()

    def _load(self) -> dict:
        """Loads memory from JSON with backward-compatible key migration and corruption resilience."""
        defaults = {
            "version": "2.5",
            "total_missions": 0,
            "missions": [],
            "tool_invocations": {},
            "tool_success_counts": {},
            "learned_insights": {},
        }

        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            # Backward-compatible key migration
                            if "tool_effectiveness" in data and "tool_success_counts" not in data:
                                data["tool_success_counts"] = data.pop("tool_effectiveness", {})
                            if "learned_facts" in data and "learned_insights" not in data:
                                data["learned_insights"] = data.pop("learned_facts", {})

                            # Ensure all expected keys exist
                            for k, v in defaults.items():
                                data.setdefault(k, v)
                            return data
            except Exception as e:
                print(f"⚠️ Memory load notice (corrupted or unreadable file, resetting to defaults): {e}")

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

    def record_mission(self, query: str, tool: str, summary: str, verified_success: bool = True):
        """Records mission execution telemetry and verified success status."""
        self.data["total_missions"] += 1

        # Track overall tool invocations
        invocations = self.data.setdefault("tool_invocations", {})
        invocations[tool] = invocations.get(tool, 0) + 1

        # Track verified successful outcomes separately
        successes = self.data.setdefault("tool_success_counts", {})
        if verified_success:
            successes[tool] = successes.get(tool, 0) + 1

        self.data["missions"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "tool": tool,
            "summary": summary[:300],
            "verified_success": verified_success,
        })
        self.data["missions"] = self.data["missions"][-150:]
        self.save()

    def get_stats(self) -> str:
        invocations = self.data.get("tool_invocations", {})
        successes = self.data.get("tool_success_counts", {})
        top_tools = sorted(invocations.items(), key=lambda x: x[1], reverse=True)[:5]

        stats = f"### Continuous Memory Statistics\n- **Total Missions Logged**: {self.data.get('total_missions', 0)}\n- **Top Executed Tools**:\n"
        for t, total in top_tools:
            succ = successes.get(t, 0)
            rate = (succ / total * 100) if total > 0 else 0
            stats += f"  - `{t}`: {total} runs ({succ} verified successes, {rate:.0f}% success rate)\n"
        if not top_tools:
            stats += "  *(No tools executed yet)*\n"
        return stats
