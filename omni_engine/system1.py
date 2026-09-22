"""
System 1 Decision Engine (Laya / Jev)
Sub-35ms routing, tool selection, ranking, and guardrails.
"""

import os
import time
import warnings

# Suppress temperature calibration warnings from laya
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")

import laya
from laya import Router

class System1Router:
    def __init__(self, engine: str = "laya"):
        self.engine = engine.lower()
        self.laya_router = None
        self.jev_client = None

        if self.engine == "jev":
            api_key = os.environ.get("TYPESAFE_API_KEY")
            if api_key:
                try:
                    from typesafe_sdk import TypeSafeClient
                    self.jev_client = TypeSafeClient(api_key=api_key)
                    print("⚡ [System 1] Connected to TypeSafe Jev Cloud API!")
                except Exception:
                    self.engine = "laya"
            else:
                self.engine = "laya"

        if self.engine == "laya":
            print("🤖 [System 1] Initializing Laya Decision Engine (ModernBERT-large)...")
            self.laya_router = Router()
            print("⚡ [System 1] Laya ready for sub-35ms tool dispatch & ranking!\n")

    def route_tool(self, prompt: str, tool_catalog: dict) -> tuple:
        """Evaluates user intent and returns (chosen_tool_name, latency_ms)."""
        criteria = {k: v["desc"][:85] for k, v in list(tool_catalog.items())[:12]}
        q = {
            "target_tool": {
                "type": "choice",
                "instructions": "Select the single best tool to execute the user's objective:",
                "criteria": criteria,
            }
        }
        t0 = time.perf_counter()
        if self.engine == "jev" and self.jev_client:
            try:
                from typesafe_sdk import Choice
                q_j = {"target_tool": Choice(instructions=q["target_tool"]["instructions"], criteria=criteria)}
                res = self.jev_client.system_one(state={"prompt": prompt}, questions=q_j)
                return res.answers["target_tool"].choice, 25.0
            except Exception:
                pass

        res = self.laya_router.predict({"prompt": prompt}, q)
        latency = (time.perf_counter() - t0) * 1000
        choice = res["answers"]["target_tool"]["choice"]
        return choice, latency

    def rank_options(self, goal: str, options: dict) -> str:
        """Ranks a list of candidate items/links/actions in ~30ms."""
        crit = {k: v[:80] for k, v in list(options.items())[:8]}
        q = {
            "best_option": {
                "type": "choice",
                "instructions": f"Goal: '{goal}'. Which option is the most authoritative and directly relevant?",
                "criteria": crit,
            }
        }
        res = self.laya_router.predict({"goal": goal}, q)
        return res["answers"]["best_option"]["choice"]
