"""
OMNI-AGENT: THE ULTIMATE MULTI-TOOL AUTONOMOUS AGENT (v2.0)
Architecture:
- System 1: Laya (Local ModernBERT-large) / Jev (TypeSafe Cloud API) for sub-35ms routing
- System 2: Cloud API (LLaMA 3.3 70B / Gemini via OpenRouter) + Antigravity System 2 Bridge
- Omni-Tool Arsenal: 20+ Real-World Tools across Web, Browser, OS, Dev, and Data
- Multi-Step Goal Planner: Decomposes complex objectives into automated phases
- Continuous Memory & Experience Cache: Learns and delivers better results every time!
"""

import sys
import os
import time

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from omni_engine import System1Router, System2Engine, OmniMemory, AutonomousPlanner, OMNI_TOOL_REGISTRY

class OmniAgent:
    def __init__(self, engine="laya"):
        print("=" * 80)
        print("🌟 INITIALIZING OMNI-AGENT: THE ULTIMATE MULTI-TOOL AUTONOMOUS AGENT (v2.0)")
        print("=" * 80)
        self.memory = OmniMemory()
        self.sys1 = System1Router(engine=engine)
        self.sys2 = System2Engine()
        self.planner = AutonomousPlanner(self.sys1, self.sys2, self.memory)
        print(f"🛠️  Loaded {len(OMNI_TOOL_REGISTRY)} Real-World Tools across Web, Browser, OS, Dev & Data!")
        print(f"🧠 Memory System Active: {self.memory.data.get('total_missions', 0)} missions recorded.\n")

    def run(self, user_prompt: str):
        prompt = user_prompt.strip()
        if not prompt:
            return

        # Special commands
        if prompt.lower() in ("memory stats", "stats", "memory"):
            print("\n" + "=" * 80)
            print(self.memory.get_stats())
            print("=" * 80 + "\n")
            return

        print("\n" + "=" * 80)
        print(f"📢 USER MISSION: \"{prompt}\"")
        print("=" * 80)

        t_start = time.perf_counter()
        result = self.planner.plan_and_execute(prompt)
        elapsed = time.perf_counter() - t_start

        print("\n" + "=" * 80)
        print(f"📊 EXECUTION OUTPUT (Completed in {elapsed:.2f}s)")
        print("=" * 80 + "\n")
        print(result)
        print("\n" + "=" * 80)
        print("✅ Mission Logged to Continuous Memory (Self-Improvement Active)!")
        print("=" * 80 + "\n")


def interactive_cli():
    import argparse
    parser = argparse.ArgumentParser(description="Omni-Agent: Ultimate Multi-Tool Autonomous Agent")
    parser.add_argument("query", nargs="*", help="Mission or command to execute")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya", help="System 1 engine (default: laya)")
    args = parser.parse_args()

    agent = OmniAgent(engine=args.engine)

    if args.query:
        query_str = " ".join(args.query)
        agent.run(query_str)
    else:
        print("=" * 80)
        print("💡 YOU ARE IN FULL CONTROL! 100+ CAPABILITIES ACROSS 5 TOOL DOMAINS:")
        print("   🌐 1. Live Web:       \"search web for latest AI news 2026\", \"scrape https://example.com\"")
        print("   🖥️  2. Real Browser:   \"open edge and explore github.com/trending\"")
        print("   💻 3. Windows OS:     \"check system diagnostics\", \"list top memory processes\", \"screenshot\"")
        print("   📂 4. Code & Files:    \"view directory tree\", \"search code for Router\", \"run python code\"")
        print("   📊 5. Deep Research:  \"create an intelligence dossier on neuromorphic computing\"")
        print("   🧠 6. Memory Stats:   \"memory stats\"")
        print("   🚪 7. Exit:           \"exit\"")
        print("===========================================================================")

        while True:
            try:
                cmd = input("\nOmniAgent > ").strip()
                if not cmd:
                    continue
                if cmd.lower() in ("exit", "quit", "q"):
                    print("👋 Exiting Omni-Agent.")
                    break
                agent.run(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Exiting.")
                break


if __name__ == "__main__":
    interactive_cli()
