"""
Autonomous Multi-Step Goal Planner & Execution Loop
Decomposes complex, multi-part objectives into sequential tool executions,
coordinates System 1 reflexes with System 2 synthesis.
"""

import time
from .tools import OMNI_TOOL_REGISTRY

class AutonomousPlanner:
    def __init__(self, sys1_engine, sys2_engine, memory_engine):
        self.sys1 = sys1_engine
        self.sys2 = sys2_engine
        self.memory = memory_engine

    def is_complex_multi_step(self, prompt: str) -> bool:
        """Determines if a task requires multiple tools chained together."""
        indicators = ["and then", "after that", "also check", "dossier", "report on", "audit and", "search and create"]
        return any(ind in prompt.lower() for ind in indicators) or len(prompt.split()) > 10

    def plan_and_execute(self, mission_prompt: str) -> str:
        print(f"\n🧠 [Autonomous Planner] Decomposing mission: \"{mission_prompt}\"...")

        # 1. Recall past insights
        past_missions = self.memory.recall(mission_prompt)
        context_str = ""
        if past_missions:
            print(f"💡 [Memory] Recalled {len(past_missions)} relevant past mission experiences.")
            context_str = f"Prior Knowledge: {past_missions[0].get('summary', '')[:200]}"

        # 2. If it's a deep research / dossier mission:
        p_lower = mission_prompt.lower()
        if any(w in p_lower for w in ["dossier", "report", "deep research", "analyze", "explain in depth", "how to"]):
            print("🚀 [Multi-Step Workflow: Deep Web Intelligence + Visual Scrape + System 2 Synthesis]")
            
            # Step A: Live Web Search across internet
            web_results = OMNI_TOOL_REGISTRY["web_search"]["func"](mission_prompt)
            print("  ✅ [Phase 1/3 Complete]: Live web search executed.")

            # Step B: Laya ranks options & Visual Edge Browse
            vis_results = OMNI_TOOL_REGISTRY["visual_browse"]["func"](mission_prompt)
            print("  ✅ [Phase 2/3 Complete]: Real Edge browser visual exploration complete.")

            # Step C: System 2 Master Synthesis
            combined_context = f"{web_results}\n\n{vis_results}\n\n{context_str}"
            final_report = self.sys2.synthesize_dossier(mission_prompt, combined_context)
            print("  ✅ [Phase 3/3 Complete]: Master Intelligence Dossier synthesized.")

            # Record in memory
            self.memory.record_mission(mission_prompt, "multi_step_deep_research", final_report[:250])
            return final_report

        # 3. Otherwise: Dynamic Laya System 1 Tool Dispatch
        tool_name, latency = self.sys1.route_tool(mission_prompt, OMNI_TOOL_REGISTRY)
        print(f"🎯 [System 1 Decision ({latency:.1f}ms)]: Selected Tool -> [{tool_name}]")
        print(f"💡 Tool: {OMNI_TOOL_REGISTRY[tool_name]['desc']}")

        tool_func = OMNI_TOOL_REGISTRY[tool_name]["func"]
        t0 = time.perf_counter()
        result = tool_func(mission_prompt)
        exec_time = time.perf_counter() - t0

        self.memory.record_mission(mission_prompt, tool_name, result[:250])
        return result
