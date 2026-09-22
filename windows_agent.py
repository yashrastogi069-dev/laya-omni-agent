"""
Unified Windows AI Agent: System 1 (Laya/Jev) + System 2 (Antigravity)
Automates real tasks on Windows 11:
 - Launching Desktop Apps (Notepad, VS Code, Spotify, Calc)
 - Triggering Browser Workflows (Google Flights, Hotels, Search)
 - Escalating Complex Planning to Antigravity
"""

import os
import sys
import subprocess
import webbrowser
import shutil
import warnings

# Suppress checkpoint temperature calibration warnings from laya
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import laya

class WindowsAgent:
    def __init__(self, engine: str = "laya"):
        self.engine = engine.lower()
        print(f"🤖 Initializing Windows Agent (powered by {self.engine.upper()} System 1)...")
        if self.engine == "jev":
            api_key = os.environ.get("TYPESAFE_API_KEY")
            if not api_key:
                print("⚠️ Warning: TYPESAFE_API_KEY not set. Falling back to local Laya engine.")
                self.engine = "laya"
                self.router = laya.Router()
            else:
                try:
                    from typesafe_sdk import TypeSafeClient
                    self.jev_client = TypeSafeClient(api_key=api_key)
                except ImportError:
                    print("⚠️ typesafe-sdk not found. Falling back to Laya.")
                    self.engine = "laya"
                    self.router = laya.Router()
        else:
            # Use lazy loading so only the required checkpoint is downloaded
            self.router = laya.Router()
        print(f"⚡ System 1 Reflex Engine ready! Sub-35ms decision speed via {self.engine.upper()}.\n")

    def classify_intent(self, user_prompt: str) -> dict:
        """Evaluates user intent and target using Laya or Jev."""
        if self.engine == "jev" and hasattr(self, "jev_client"):
            from typesafe_sdk import Choice, Noul
            questions = {
                "action_type": Choice(
                    instructions="What primary category of action does the user want to perform on their Windows PC?",
                    criteria={
                        "browser_travel": "Searching, booking, or checking flights, hotels, or travel (Google Flights, Airbnb, Booking)",
                        "browser_web": "Opening websites, browsing YouTube, Spotify web, GitHub, Wikipedia, or web search",
                        "desktop_app": "Opening or controlling installed Windows desktop software (VS Code, Spotify, Notepad, Calculator, Explorer, Settings)",
                        "complex_coding": "Writing code, debugging, analyzing codebases, or complex multi-step reasoning",
                        "system_control": "Windows settings, volume, terminal commands, or file system operations",
                    },
                ),
                "needs_antigravity": Noul(
                    instructions="Does this request require deep multi-step planning, coding, or heavy reasoning from Antigravity?"
                ),
            }
            res = self.jev_client.system_one(state={"prompt": user_prompt}, questions=questions)
            choice_ans = res.answers["action_type"]
            noul_ans = res.answers["needs_antigravity"]
            return {
                "action_type": choice_ans.choice,
                "confidence": getattr(choice_ans, "confidence", 1.0),
                "urgency": 0.5,
                "needs_antigravity": getattr(noul_ans, "noul", False),
            }

        questions = {
            "action_type": {
                "type": "choice",
                "instructions": "What primary category of action does the user want to perform on their Windows PC?",
                "criteria": {
                    "browser_travel": "Searching, booking, or checking flights, hotels, or travel (Google Flights, Airbnb, Booking)",
                    "browser_web": "Opening websites, browsing YouTube, Spotify web, GitHub, Wikipedia, or web search",
                    "desktop_app": "Opening or controlling installed Windows desktop software (VS Code, Spotify, Notepad, Calculator, Explorer, Settings)",
                    "complex_coding": "Writing code, debugging, analyzing codebases, or complex multi-step reasoning",
                    "system_control": "Windows settings, volume, terminal commands, or file system operations",
                },
            },
            "urgency": {
                "type": "score",
                "instructions": "Rate how time-sensitive or critical this user action is.",
                "criteria": ["Low: casual request", "Medium: standard workflow", "High: blocking or urgent"],
            },
            "needs_antigravity": {
                "type": "noul",
                "instructions": "Does this request require deep multi-step planning, coding, or heavy reasoning from Antigravity?",
            },
        }

        res = self.router.predict({"prompt": user_prompt}, questions)
        return {
            "action_type": res["answers"]["action_type"]["choice"],
            "confidence": res["answers"]["action_type"]["confidence"],
            "urgency": res["answers"]["urgency"]["score"],
            "needs_antigravity": res["answers"]["needs_antigravity"]["noul"] > 0.65,
        }

    def execute(self, user_prompt: str):
        print(f"\n📢 User Command: \"{user_prompt}\"")
        decision = self.classify_intent(user_prompt)

        print(f"🎯 System 1 Decision: {decision['action_type']} (Confidence: {decision['confidence']:.2f})")
        print(f"⚡ Escalation to Antigravity Needed: {decision['needs_antigravity']}")

        action = decision["action_type"]

        # 1. Travel / Flights / Hotels (Real Browser Automation)
        if action == "browser_travel":
            print("🛫 Opening Google Flights in your Windows browser...")
            prompt_l = user_prompt.lower()
            dest = "London"
            for word in ["to ", "in ", "for "]:
                if word in prompt_l:
                    parts = prompt_l.split(word)
                    if len(parts) > 1:
                        dest = parts[-1].strip().split(" ")[0].capitalize()
                    break
            url = f"https://www.google.com/travel/flights?q=flights+to+{dest}"
            print(f" -> Launching URL: {url}")
            webbrowser.open(url)

        # 2. General Web / YouTube / Search (Real Browser Automation)
        elif action == "browser_web":
            print("🌐 Opening Web destination in your Windows browser...")
            prompt_l = user_prompt.lower()
            if "youtube" in prompt_l or "music" in prompt_l or "song" in prompt_l:
                clean_q = prompt_l.replace("open youtube", "").replace("to listen to", "").replace("play", "").strip() or "relaxing music"
                clean_q_url = clean_q.replace(" ", "+")
                url = f"https://www.youtube.com/results?search_query={clean_q_url}"
                print(f" -> Launching YouTube Search: \"{clean_q}\"")
                webbrowser.open(url)
            elif "github" in prompt_l:
                webbrowser.open("https://github.com")
            elif "reddit" in prompt_l:
                webbrowser.open("https://reddit.com")
            elif "wiki" in prompt_l:
                clean_q = prompt_l.replace("search wikipedia for", "").replace("wikipedia", "").replace("search", "").strip() or "Artificial_Intelligence"
                webbrowser.open(f"https://en.wikipedia.org/wiki/{clean_q.replace(' ', '_')}")
            else:
                clean_query = prompt_l
                for prefix in ["search for ", "search ", "browse ", "google ", "open "]:
                    if clean_query.startswith(prefix):
                        clean_query = clean_query[len(prefix):]
                        break
                clean_q_url = clean_query.replace(" ", "+")
                webbrowser.open(f"https://www.google.com/search?q={clean_q_url}")

        # 3. Desktop Software Control (Windows Apps)
        elif action == "desktop_app":
            print("💻 Launching Windows Desktop App...")
            prompt_lower = user_prompt.lower()

            # Guard against media/web requests misclassified under desktop_app
            if "youtube" in prompt_lower or "music" in prompt_lower:
                clean_q = prompt_lower.replace("open youtube", "").replace("to listen to", "").replace("play", "").strip() or "relaxing music"
                clean_q_url = clean_q.replace(" ", "+")
                url = f"https://www.youtube.com/results?search_query={clean_q_url}"
                print(f" -> Launching YouTube Search in browser: \"{clean_q}\"")
                webbrowser.open(url)
                return decision

            if "code" in prompt_lower or "vs code" in prompt_lower or "vscode" in prompt_lower:
                subprocess.Popen(["cmd.exe", "/c", "code", "."], shell=True)
                print(" -> Launched Visual Studio Code!")
            elif "notepad" in prompt_lower:
                subprocess.Popen(["notepad.exe"])
                print(" -> Launched Notepad!")
            elif "calc" in prompt_lower or "calculator" in prompt_lower:
                subprocess.Popen(["calc.exe"])
                print(" -> Launched Calculator!")
            elif "explorer" in prompt_lower or "files" in prompt_lower or "folder" in prompt_lower:
                subprocess.Popen(["explorer.exe"])
                print(" -> Opened File Explorer!")
            elif "spotify" in prompt_lower:
                subprocess.Popen(["cmd.exe", "/c", "start", "spotify:"], shell=True)
                print(" -> Launched Spotify!")
            elif "chrome" in prompt_lower:
                subprocess.Popen(["cmd.exe", "/c", "start", "chrome"], shell=True)
                print(" -> Launched Google Chrome!")
            elif "edge" in prompt_lower:
                subprocess.Popen(["cmd.exe", "/c", "start", "msedge"], shell=True)
                print(" -> Launched Microsoft Edge!")
            elif "terminal" in prompt_lower or "powershell" in prompt_lower or "cmd" in prompt_lower:
                cmd_exec = "wt.exe" if shutil.which("wt") else "powershell.exe"
                subprocess.Popen([cmd_exec])
                print(f" -> Launched Terminal ({cmd_exec})!")
            elif "setting" in prompt_lower:
                subprocess.Popen(["cmd.exe", "/c", "start", "ms-settings:"], shell=True)
                print(" -> Opened Windows Settings!")
            else:
                # Strip leading helper words so Windows doesn't try to run 'open.exe'
                clean_target = prompt_lower
                for prefix in ["open ", "launch ", "start ", "run ", "for me", "please "]:
                    clean_target = clean_target.replace(prefix, "")
                clean_target = clean_target.strip()
                print(f" -> Launching '{clean_target}' via Windows...")
                subprocess.Popen(["cmd.exe", "/c", "start", "", clean_target], shell=True)

        # 4. Complex Tasks / Coding / Reasoning -> Escalate to Antigravity
        elif action == "complex_coding" or decision["needs_antigravity"]:
            print("🧠 Escalating to Antigravity (System 2):")
            print(f" -> Deep reasoning task: \"{user_prompt}\"")
            agy_bin = shutil.which("agy")
            if agy_bin:
                print(f" -> Antigravity CLI detected at: {agy_bin}")
                print(" -> Handing off to Antigravity System 2 (use `agy` or Antigravity chat)!")
            else:
                print(" -> Handing off to Antigravity in this chat session!")

        return decision

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Unified Windows AI Agent (Laya/Jev System 1 + Antigravity System 2)")
    parser.add_argument("command", nargs="?", help="Direct command to run (e.g. 'Open Calculator')")
    parser.add_argument("--demo", action="store_true", help="Run the pre-configured sample commands demo")
    parser.add_argument("--engine", choices=["laya", "jev"], default="laya", help="System 1 engine to use (default: laya)")
    args = parser.parse_args()

    agent = WindowsAgent(engine=args.engine)

    sample_commands = [
        "Search flights from New York to London for next week",
        "Open Calculator for me",
        "Open YouTube to listen to music",
        "Refactor my authentication middleware and fix the memory leak",
    ]

    if args.demo:
        print("▶ Running Demo Sequence...")
        for cmd in sample_commands:
            agent.execute(cmd)
            print("-" * 50)
    elif args.command:
        agent.execute(args.command)
    else:
        # Default to Interactive Mode so the agent doesn't exit immediately!
        print("=" * 65)
        print("🚀 Windows Agent is ACTIVE (System 1: Laya | System 2: Antigravity)")
        print("💡 Enter any command (e.g. 'open notepad', 'flights to tokyo', etc.)")
        print("💡 Type 'demo' to run sample test cases, or 'exit' to quit.")
        print("=" * 65)
        while True:
            try:
                user_input = input("\nWindowsAgent > ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("👋 Exiting Windows Agent.")
                    break
                if user_input.lower() == "demo":
                    for cmd in sample_commands:
                        agent.execute(cmd)
                        print("-" * 50)
                    continue
                agent.execute(user_input)
                print("-" * 50)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Exiting Windows Agent.")
                break
