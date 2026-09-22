"""
Comparative Test Suite: Laya (Local Open-Source) vs Jev (TypeSafe Cloud API)
System 1 Decision Engine Benchmark
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

TEST_PROMPTS = [
    "Search flights from New York to London for next week",
    "Open Calculator for me",
    "Open YouTube to listen to music",
    "Refactor my authentication middleware and fix the memory leak",
    "Adjust system volume to 50%",
]

def test_laya(prompts):
    print("\n" + "=" * 65)
    print("🧠 Testing LAYA (Local Open-Source System 1)")
    print("=" * 65)
    try:
        import laya
    except ImportError:
        print("❌ Laya is not installed. Run: pip install laya")
        return

    print("Loading Laya router...")
    t_start_load = time.perf_counter()
    router = laya.Router()
    load_time = (time.perf_counter() - t_start_load) * 1000
    print(f"✅ Laya loaded in {load_time:.1f}ms\n")

    questions = {
        "action_type": {
            "type": "choice",
            "instructions": "What primary category of action does the user want to perform on their Windows PC?",
            "criteria": {
                "browser_travel": "Searching, booking flights, hotels, or travel",
                "browser_web": "Opening websites, browsing YouTube, GitHub, web search",
                "desktop_app": "Opening desktop software (VS Code, Spotify, Notepad, Calculator, Explorer)",
                "complex_coding": "Writing code, debugging, refactoring, or complex reasoning",
                "system_control": "Windows settings, volume, terminal commands, or file system",
            },
        },
        "needs_antigravity": {
            "type": "noul",
            "instructions": "Does this request require deep multi-step planning, coding, or heavy reasoning from Antigravity?",
        },
    }

    for p in prompts:
        t0 = time.perf_counter()
        res = router.predict({"prompt": p}, questions)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        action = res["answers"]["action_type"]["choice"]
        conf = res["answers"]["action_type"]["confidence"]
        needs_ag = res["answers"]["needs_antigravity"]["noul"] > 0.65

        print(f"Prompt: \"{p}\"")
        print(f"  -> Decision: {action} (Confidence: {conf:.2f})")
        print(f"  -> Escalation (System 2): {needs_ag}")
        print(f"  -> Latency: {elapsed_ms:.2f}ms\n")

def test_jev(prompts):
    print("\n" + "=" * 65)
    print("⚡ Testing JEV (TypeSafe Cloud API System 1)")
    print("=" * 65)

    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        print("⚠️  TYPESAFE_API_KEY environment variable is not set.")
        print("💡 To test Jev live:")
        print("   1. Obtain an API key from https://console.typesafe.ai")
        print("   2. Run in PowerShell: $env:TYPESAFE_API_KEY=\"your_key_here\"")
        print("   3. Re-run: python test_models.py --jev\n")
        return

    try:
        from typesafe_sdk import TypeSafeClient, Choice, Noul
    except ImportError:
        print("❌ typesafe-sdk is not installed. Run: pip install typesafe-sdk")
        return

    client = TypeSafeClient(api_key=api_key)
    print("Connected to TypeSafe Jev API.\n")

    questions = {
        "action_type": Choice(
            instructions="What primary category of action does the user want to perform on their Windows PC?",
            criteria={
                "browser_travel": "Searching, booking flights, hotels, or travel",
                "browser_web": "Opening websites, browsing YouTube, GitHub, web search",
                "desktop_app": "Opening desktop software (VS Code, Spotify, Notepad, Calculator, Explorer)",
                "complex_coding": "Writing code, debugging, refactoring, or complex reasoning",
                "system_control": "Windows settings, volume, terminal commands, or file system",
            },
        ),
        "needs_antigravity": Noul(
            instructions="Does this request require deep multi-step planning, coding, or heavy reasoning from Antigravity?"
        ),
    }

    for p in prompts:
        t0 = time.perf_counter()
        try:
            res = client.system_one(
                state={"prompt": p},
                questions=questions,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000

            action = res.answers["action_type"].choice
            conf = getattr(res.answers["action_type"], "confidence", 1.0)
            needs_ag = getattr(res.answers["needs_antigravity"], "noul", False)

            print(f"Prompt: \"{p}\"")
            print(f"  -> Decision: {action} (Confidence: {conf:.2f})")
            print(f"  -> Escalation (System 2): {needs_ag}")
            print(f"  -> Latency: {elapsed_ms:.2f}ms\n")
        except Exception as e:
            print(f"Prompt: \"{p}\" -> ❌ Jev Error: {e}\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Laya and Jev System 1 models")
    parser.add_argument("--laya", action="store_true", help="Run only Laya test")
    parser.add_argument("--jev", action="store_true", help="Run only Jev test")
    parser.add_argument("--all", action="store_true", help="Run both Laya and Jev tests")
    args = parser.parse_args()

    if args.laya:
        test_laya(TEST_PROMPTS)
    elif args.jev:
        test_jev(TEST_PROMPTS)
    else:
        # Default to running comparison / all
        test_laya(TEST_PROMPTS)
        test_jev(TEST_PROMPTS)
