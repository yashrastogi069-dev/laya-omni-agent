"""
Persistent Continuous Memory & Self-Improving Experience Cache
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

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "version": "2.0",
            "total_missions": 0,
            "missions": [],
            "tool_success_counts": {},
            "learned_insights": {},
        }

    def save(self):
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Memory save error: {e}")

    def recall(self, query: str) -> list:
        """Finds past relevant missions to improve current execution."""
        words = [w.lower() for w in query.split() if len(w) > 3]
        matches = []
        for m in self.data.get("missions", []):
            if any(w in m.get("query", "").lower() for w in words):
                matches.append(m)
        return matches[-3:]

    def record_mission(self, query: str, tool: str, summary: str):
        self.data["total_missions"] += 1
        self.data["missions"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "tool": tool,
            "summary": summary[:300],
        })
        self.data["tool_success_counts"][tool] = self.data["tool_success_counts"].get(tool, 0) + 1
        self.data["missions"] = self.data["missions"][-150:]
        self.save()

    def get_stats(self) -> str:
        counts = self.data.get("tool_success_counts", {})
        top_tools = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
        stats = f"### Continuous Memory Statistics\n- **Total Missions Completed**: {self.data.get('total_missions', 0)}\n- **Top Executed Tools**:\n"
        for t, cnt in top_tools:
            stats += f"  - `{t}`: {cnt} executions\n"
        return stats
