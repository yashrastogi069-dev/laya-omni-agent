"""
Dual System 2 Engine: Cloud API + Antigravity Bridge
- Mode A: Cloud API (OpenRouter LLaMA 3.3 70B / Gemini) - 0 MB local RAM usage
- Mode B: Antigravity CLI Bridge (`agy.exe` at C:\\Users\\win 10\\AppData\\Local\\agy\\bin\\agy.EXE)
- Mode C: Chat Escalation Protocol (logs pending escalations to escalations/pending_task.json)
"""

import os
import json
import time
import shutil
import subprocess

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESCALATION_DIR = os.path.join(WORKSPACE_ROOT, "escalations")
os.makedirs(ESCALATION_DIR, exist_ok=True)

class System2Engine:
    def __init__(self):
        self.openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        self.agy_path = shutil.which("agy") or "C:\\Users\\win 10\\AppData\\Local\\agy\\bin\\agy.EXE"
        self.has_agy = os.path.exists(self.agy_path) if self.agy_path else False

    def synthesize_dossier(self, mission: str, raw_context: str) -> str:
        """Synthesizes raw web or tool outputs into an executive intelligence dossier."""
        if self.openrouter_key:
            try:
                from openai import OpenAI
                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.openrouter_key)
                prompt = (
                    f"Mission: \"{mission}\"\n\nGathered Multi-Tool Context:\n{raw_context[:8000]}\n\n"
                    "Provide a MASTER-CLASS Intelligence Dossier structured with:\n"
                    "1. Executive Summary & Foundational Core\n"
                    "2. Deep Analysis & Cross-Referenced Findings\n"
                    "3. Actionable Protocols & Step-by-Step Implementation\n"
                    "4. Critical Nuances, Pitfalls & Counter-Perspectives\n"
                    "5. Source Index & Data Attribution\n"
                    "Format cleanly with markdown callouts and bullet points."
                )
                resp = client.chat.completions.create(
                    model="meta-llama/llama-3.3-70b-instruct",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=3000,
                )
                return resp.choices[0].message.content
            except Exception as e:
                print(f"⚠️ Cloud synthesis notice: {e}")

        # Native high-value structured summary
        return f"""# Master Intelligence Dossier: {mission.title()}
*Synthesized by Omni-Agent System 2*

---

## 1. Executive Summary
This document compiles and synthesizes multi-source data gathered for the objective: **{mission}**.

## 2. Key Gathered Intelligence
{raw_context[:3000]}

## 3. Actionable Protocols
- Review operational parameters and calibrate execution.
- Maintain systematic verification of all data points.
"""

    def escalate_to_antigravity(self, complex_goal: str, context: dict = None) -> str:
        """Escalates complex code refactoring, debugging, or deep architecture to Antigravity."""
        escalation_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "goal": complex_goal,
            "context": context or {},
            "status": "pending_antigravity_resolution",
        }
        task_file = os.path.join(ESCALATION_DIR, "pending_task.json")
        with open(task_file, "w", encoding="utf-8") as f:
            json.dump(escalation_data, f, indent=2)

        # If agy CLI is present, run prompt via agy
        if self.has_agy:
            try:
                print(f"🧠 [Antigravity System 2] Invoking Antigravity CLI ({self.agy_path})...")
                res = subprocess.run([self.agy_path, "--print", complex_goal], capture_output=True, text=True, timeout=30)
                out = res.stdout.strip() or res.stderr.strip()
                if out:
                    return f"### Antigravity System 2 Resolution:\n\n{out}"
            except Exception as e:
                print(f"⚠️ Antigravity CLI notice: {e}")

        return (
            f"🧠 **[Escalated to Antigravity System 2]**\n"
            f"- Task logged to: `{os.path.relpath(task_file, WORKSPACE_ROOT)}`\n"
            f"- Mission: *\"{complex_goal}\"*\n"
            f"- Antigravity is ready in your active chat session to complete this refactoring/reasoning task!"
        )
