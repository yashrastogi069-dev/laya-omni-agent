"""
LAYA UNIFIED AGENT: THE COMPLETE SYSTEM 1 + SYSTEM 2 AUTONOMOUS AGENT
======================================================================
Architecture:
- System 1 (Fast Reflex): Laya (Local ModernBERT-large) / Jev (TypeSafe Cloud) in sub-35ms
- System 2 (Deep Reasoning): Cloud API (LLaMA 3.3 70B via OpenRouter) + Antigravity Live Bridge
- Tool Arsenal: 23+ Real-World Tools across Web, Browser, OS, Dev, and Data
- Multi-Step Goal Planner: Automatically decomposes complex goals into sequential phases
- Continuous Memory Engine: Persistent experience cache that learns from every run
- Visual Interface: Rich terminal UI + Microsoft Edge full-screen browser with live glowing HUD
"""

import os
import sys
import time
import warnings

# Suppress temperature calibration warnings from laya
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")

# Ensure UTF-8 console output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from omni_engine import (
    System1Router,
    System2Engine,
    OmniMemory,
    AutonomousPlanner,
    OMNI_TOOL_REGISTRY,
)

console = Console()

class LayaUnifiedAgent:
    def __init__(self, engine: str = "laya"):
        self.engine_name = engine.lower()
        self.memory = OmniMemory()
        self.sys1 = System1Router(engine=self.engine_name)
        self.sys2 = System2Engine()
        self.planner = AutonomousPlanner(self.sys1, self.sys2, self.memory)

    def print_banner(self):
        missions_count = self.memory.data.get("total_missions", 0)
        tools_count = len(OMNI_TOOL_REGISTRY)

        banner_text = f"""[bold green]⚡ LAYA UNIFIED AUTONOMOUS AGENT (v2.5)[/bold green]
[cyan]Architecture:[/cyan] [bold]System 1 Reflexes (Laya/Jev)[/bold] + [bold]System 2 (Antigravity & Cloud)[/bold]
[cyan]Tool Arsenal:[/cyan] [bold green]{tools_count} Production Tools[/bold green] (Web, Edge Browser, OS, Code, Data)
[cyan]Continuous Memory:[/cyan] [bold yellow]{missions_count} Missions Learned[/bold yellow] (Self-Improving Cache Active)
[cyan]Active Engine:[/cyan] [bold magenta]{self.engine_name.upper()}[/bold magenta] (Sub-35ms Decision Speed)"""

        console.print(Panel(banner_text, border_style="bright_green", title="🤖 ALL-IN-ONE AGENT", subtitle="Ready for any mission"))

    def show_tools_table(self):
        table = Table(title="🛠️ Omni-Tool Arsenal (Categorized by Domain)", border_style="cyan")
        table.add_column("Category", style="bold cyan", width=16)
        table.add_column("Tool Name", style="bold green", width=22)
        table.add_column("Capabilities & Description", style="white")

        categories = {
            "web": "🌐 Live Web",
            "browser": "🖥️  Visual Browser",
            "os": "💻 Windows OS",
            "dev": "📂 Code & Files",
            "data": "📊 Data Science",
        }

        for cat_key, cat_label in categories.items():
            cat_tools = [k for k, v in OMNI_TOOL_REGISTRY.items() if v.get("category") == cat_key]
            for i, t_name in enumerate(cat_tools):
                desc = OMNI_TOOL_REGISTRY[t_name]["desc"]
                table.add_row(cat_label if i == 0 else "", t_name, desc)

        console.print(table)

    def show_memory_stats(self):
        stats = self.memory.get_stats()
        console.print(Panel(Markdown(stats), border_style="yellow", title="🧠 Continuous Learning Memory"))

    def execute(self, user_mission: str):
        mission = user_mission.strip()
        if not mission:
            return

        # Built-in quick navigation commands
        lower = mission.lower()
        if lower in ("help", "tools", "?"):
            self.show_tools_table()
            return
        elif lower in ("stats", "memory"):
            self.show_memory_stats()
            return
        elif lower.startswith("engine "):
            new_eng = lower.split()[1]
            if new_eng in ("laya", "jev"):
                self.engine_name = new_eng
                self.sys1 = System1Router(engine=new_eng)
                self.planner.sys1 = self.sys1
                console.print(f"[bold green]✅ Switched System 1 engine to: {new_eng.upper()}[/bold green]")
            else:
                console.print("[yellow]Usage: engine laya  OR  engine jev[/yellow]")
            return
        elif lower == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            self.print_banner()
            return

        console.print(f"\n[bold bright_blue]📢 MISSION:[/bold bright_blue] [white]\"{mission}\"[/white]")

        t0 = time.perf_counter()
        with console.status("[bold green]Agent orchestrating System 1 reflexes and tools...", spinner="dots"):
            result = self.planner.plan_and_execute(mission)
        elapsed = time.perf_counter() - t0

        console.print(Panel(
            Markdown(result) if "#" in result or "**" in result else result,
            border_style="green",
            title=f"📊 EXECUTION RESULT (Completed in {elapsed:.2f}s)",
            subtitle="Logged to Continuous Memory"
        ))


def interactive_loop():
    import argparse
    parser = argparse.ArgumentParser(description="Laya Unified Autonomous Agent")
    parser.add_argument("query", nargs="*", help="Direct mission command to run")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya", help="System 1 engine (default: laya)")
    parser.add_argument("--tools", action="store_true", help="List all available tools and exit")
    args = parser.parse_args()

    agent = LayaUnifiedAgent(engine=args.engine)

    if args.tools:
        agent.show_tools_table()
        return

    if args.query:
        agent.execute(" ".join(args.query))
        return

    agent.print_banner()
    console.print("\n[bold]💡 Tip:[/bold] Type [bold green]tools[/bold green] for tool catalog, [bold yellow]memory[/bold yellow] for stats, or type [bold cyan]ANY[/bold cyan] task you want to execute.")
    console.print("[dim]Type 'exit' or 'quit' to close.[/dim]\n")

    while True:
        try:
            cmd = console.input("[bold bright_green]LayaAgent > [/bold bright_green]").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit", "q"):
                console.print("[bold yellow]👋 Exiting Laya Unified Agent. Your learned memories are safely saved![/bold yellow]")
                break
            agent.execute(cmd)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold yellow]👋 Exiting.[/bold yellow]")
            break


if __name__ == "__main__":
    interactive_loop()
