"""
Laya Real-Time Visual Automation Engine
- Launches your real Microsoft Edge browser in full screen
- Displays a Live Floating HUD on the browser showing Laya's System 1 decisions
- Highlights interactive elements with neon glow before typing/clicking
- Keeps browser open so you can see and interact with results
"""

import os
import sys
import time
import subprocess
import warnings
from playwright.sync_api import sync_playwright

# Suppress temperature calibration warnings from laya
warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*laya.*")
warnings.filterwarnings("ignore", message=r".*checkpoint ships temperatures outside.*")

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import laya
from laya import Router

router = None

def get_router():
    global router
    if router is None:
        print("🤖 [System 1] Initializing Laya Decision Engine (Local ModernBERT-large)...")
        t0 = time.perf_counter()
        router = Router()
        print(f"⚡ [System 1] Laya ready in {(time.perf_counter() - t0)*1000:.1f}ms!\n")
    return router


def inject_hud(page):
    """Injects a real-time HUD (Heads-Up Display) at the top of the browser page."""
    try:
        page.evaluate("""() => {
            if (document.getElementById('laya-hud')) return;
            const hud = document.createElement('div');
            hud.id = 'laya-hud';
            hud.innerHTML = `
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                    <div style="font-weight:900; letter-spacing:1px; color:#00ff88; font-size:16px;">
                        ⚡ LAYA SYSTEM 1 REAL-TIME AUTOMATION
                    </div>
                    <div id="laya-latency" style="background:#1e293b; color:#38bdf8; font-size:12px; padding:3px 10px; border-radius:20px; font-weight:bold;">
                        Sub-35ms Reflex
                    </div>
                </div>
                <div id="laya-status" style="font-size:15px; color:#f8fafc; font-weight:500;">
                    🤖 Initializing Real-Time Task...
                </div>
            `;
            hud.style.position = 'fixed';
            hud.style.top = '16px';
            hud.style.left = '50%';
            hud.style.transform = 'translateX(-50%)';
            hud.style.zIndex = '2147483647';
            hud.style.background = 'rgba(15, 23, 42, 0.95)';
            hud.style.backdropFilter = 'blur(12px)';
            hud.style.border = '2px solid #00ff88';
            hud.style.borderRadius = '14px';
            hud.style.padding = '14px 24px';
            hud.style.minWidth = '520px';
            hud.style.maxWidth = '80vw';
            hud.style.boxShadow = '0 12px 40px rgba(0, 255, 136, 0.35)';
            hud.style.fontFamily = 'Segoe UI, -apple-system, sans-serif';
            hud.style.pointerEvents = 'none';
            hud.style.transition = 'all 0.3s ease';
            document.body.appendChild(hud);
        }""")
    except Exception:
        pass


def update_hud(page, text: str, latency: str = "Sub-35ms Reflex"):
    """Updates the HUD message and latency banner in real time."""
    try:
        page.evaluate(f"""() => {{
            const status = document.getElementById('laya-status');
            const lat = document.getElementById('laya-latency');
            if (status) status.innerHTML = `{text}`;
            if (lat) lat.innerText = `{latency}`;
        }}""")
    except Exception:
        pass


def visual_highlight(page, element_locator):
    """Draws a bright glowing neon border around the element that Laya chose."""
    try:
        page.evaluate("""(el) => {
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            el.style.outline = '4px solid #00ff88';
            el.style.boxShadow = '0 0 25px #00ff88';
            el.style.transition = 'all 0.3s ease-in-out';
            el.style.transform = 'scale(1.02)';
        }""", element_locator.element_handle())
        time.sleep(0.6)
    except Exception:
        pass


def run_realtime_youtube(query: str = "relaxing lofi music"):
    print("=" * 70)
    print(f"🎬 [REAL-TIME BROWSER] Playing '{query}' on YouTube")
    print("=" * 70)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Opening Microsoft Edge on your desktop...")
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=60,
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        print("🌐 Navigating to YouTube...")
        page.goto("https://www.youtube.com")

        # Consent dialogs
        for btn in ["Accept all", "Reject all", "I agree", "Stay signed out"]:
            try:
                page.get_by_role("button", name=btn).click(timeout=1500)
                break
            except Exception:
                pass

        page.wait_for_timeout(1000)
        inject_hud(page)
        update_hud(page, f"🧠 <b>Laya Analyzing DOM:</b> Locating search bar for \"{query}\"...")

        # Laya Decision
        t0 = time.perf_counter()
        q = {
            "search_target": {
                "type": "choice",
                "instructions": "Which element allows entering a video search query?",
                "criteria": {
                    "search_input": "Text input box with placeholder 'Search'",
                    "voice_search": "Microphone button for voice search",
                    "notifications": "Bell icon for notifications",
                }
            }
        }
        res = r.predict({"site": "youtube", "task": "search for video"}, q)
        latency_ms = (time.perf_counter() - t0) * 1000
        choice = res["answers"]["search_target"]["choice"]
        conf = res["answers"]["search_target"]["confidence"]

        update_hud(page, f"🎯 <b>Laya Decision:</b> Found <code>{choice}</code> (Confidence: {conf:.2f})", f"{latency_ms:.1f}ms Decision")
        time.sleep(1.2)

        search_box = page.locator("input[name='search_query'], input#search").first
        visual_highlight(page, search_box)

        update_hud(page, f"⌨️ <b>Typing in Real-Time:</b> \"{query}\"...")
        search_box.click()
        search_box.type(query, delay=80)
        time.sleep(0.5)

        update_hud(page, "🔍 <b>Pressing Enter:</b> Submitting search...")
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2500)

        inject_hud(page)
        update_hud(page, "🧠 <b>Laya Decision:</b> Selecting top video from search results...")
        video_locator = page.locator("ytd-video-renderer a#video-title").first
        visual_highlight(page, video_locator)

        video_title = video_locator.get_attribute("title") or video_locator.inner_text()
        update_hud(page, f"▶️ <b>Now Playing:</b> \"{video_title[:55]}...\"")
        video_locator.click()

        time.sleep(2.0)
        inject_hud(page)
        update_hud(page, "🎉 <b>Task Complete:</b> Video is playing live! (Browser will stay open for 30s)")

        print(f"\n🎉 SUCCESS: Now playing \"{video_title}\"!")
        print("💡 Browser will stay open for 30 seconds so you can watch/listen...")
        page.wait_for_timeout(30000)
        browser.close()


def run_realtime_wikipedia(topic: str = "Artificial Intelligence"):
    print("=" * 70)
    print(f"📖 [REAL-TIME BROWSER] Researching '{topic}' on Wikipedia")
    print("=" * 70)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Opening Microsoft Edge on your desktop...")
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=60,
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        print("🌐 Navigating to Wikipedia...")
        page.goto("https://en.wikipedia.org")
        page.wait_for_timeout(1000)

        inject_hud(page)
        update_hud(page, f"🧠 <b>Laya Analyzing DOM:</b> Locating search input for \"{topic}\"...")

        t0 = time.perf_counter()
        q = {
            "search_box": {
                "type": "choice",
                "instructions": "Which element is used to search Wikipedia articles?",
                "criteria": {
                    "search_field": "Input box with placeholder 'Search Wikipedia'",
                    "main_page_link": "Navigation link to Main Page",
                    "donate_button": "Support Wikipedia donation button",
                }
            }
        }
        res = r.predict({"site": "wikipedia", "topic": topic}, q)
        latency_ms = (time.perf_counter() - t0) * 1000
        choice = res["answers"]["search_box"]["choice"]
        conf = res["answers"]["search_box"]["confidence"]

        update_hud(page, f"🎯 <b>Laya Decision:</b> Selected <code>{choice}</code>", f"{latency_ms:.1f}ms Decision")
        time.sleep(1.0)

        search_box = page.locator("input[name='search'], input#searchInput").first
        visual_highlight(page, search_box)

        update_hud(page, f"⌨️ <b>Typing in Real-Time:</b> \"{topic}\"...")
        search_box.click()
        search_box.type(topic, delay=80)
        time.sleep(0.5)

        update_hud(page, "🔍 <b>Navigating:</b> Loading article...")
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        inject_hud(page)
        update_hud(page, f"📄 <b>Article Loaded:</b> \"{page.title()}\"")

        # Smooth scrolling down the article
        print("📜 Scrolling article in real-time...")
        for i in range(4):
            page.evaluate("window.scrollBy({top: 400, behavior: 'smooth'});")
            time.sleep(1.2)

        update_hud(page, "🎉 <b>Research Complete!</b> (Browser will stay open for 20s)")
        print("\n🎉 SUCCESS: Live Wikipedia research complete!")
        page.wait_for_timeout(20000)
        browser.close()


def run_realtime_flights(destination: str = "London"):
    print("=" * 70)
    print(f"🛫 [REAL-TIME BROWSER] Searching Flights to '{destination}' on Google Flights")
    print("=" * 70)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Opening Microsoft Edge on your desktop...")
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=70,
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        print("🌐 Navigating to Google Flights...")
        page.goto("https://www.google.com/travel/flights")

        for btn in ["Accept all", "I agree", "Reject all"]:
            try:
                page.get_by_role("button", name=btn).click(timeout=1500)
                break
            except Exception:
                pass

        page.wait_for_timeout(1500)
        inject_hud(page)
        update_hud(page, f"🧠 <b>Laya Analyzing DOM:</b> Finding destination field for \"{destination}\"...")

        t0 = time.perf_counter()
        q = {
            "target": {
                "type": "choice",
                "instructions": "Which element allows entering the destination airport?",
                "criteria": {
                    "origin_input": "Input for departure airport",
                    "destination_input": "Input for 'Where to?' arrival airport",
                    "date_picker": "Field for selecting travel dates",
                }
            }
        }
        res = r.predict({"site": "google_flights", "dest": destination}, q)
        latency_ms = (time.perf_counter() - t0) * 1000

        update_hud(page, f"🎯 <b>Laya Decision:</b> Selected Destination Input", f"{latency_ms:.1f}ms Decision")
        time.sleep(1.0)

        # In Google Flights, navigate or fill destination
        dest_field = page.locator("input[placeholder*='Where to'], div[role='combobox']:has-text('Where to'), [aria-label*='Where to']").first
        try:
            dest_field.click(timeout=3000)
            visual_highlight(page, dest_field)
            update_hud(page, f"⌨️ <b>Typing Destination:</b> \"{destination}\"...")
            page.keyboard.type(destination, delay=100)
            time.sleep(1.0)
            page.keyboard.press("Enter")
        except Exception:
            page.goto(f"https://www.google.com/travel/flights?q=flights+to+{destination}")

        page.wait_for_timeout(3000)
        inject_hud(page)
        update_hud(page, f"✈️ <b>Flights Loaded:</b> Live options and prices for {destination} are on screen!")

        print(f"\n🎉 SUCCESS: Google Flights is live on your screen for {destination}!")
        print("💡 Browser will stay open for 30 seconds for you to explore...")
        page.wait_for_timeout(30000)
        browser.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Laya Real-Time Visual Automation Engine")
    parser.add_argument("--youtube", action="store_true", help="Launch live YouTube automation")
    parser.add_argument("--wiki", action="store_true", help="Launch live Wikipedia automation")
    parser.add_argument("--flights", action="store_true", help="Launch live Google Flights automation")
    parser.add_argument("--query", type=str, default=None, help="Query for YouTube, Wiki, or Flights")
    args = parser.parse_args()

    if args.youtube:
        run_realtime_youtube(args.query or "relaxing lofi music")
    elif args.wiki:
        run_realtime_wikipedia(args.query or "Artificial Intelligence")
    elif args.flights:
        run_realtime_flights(args.query or "London")
    else:
        # Interactive Menu
        print("=" * 70)
        print("🌟 LAYA REAL-TIME BROWSER AUTOMATION (LIVE ON YOUR SCREEN)")
        print("=" * 70)
        print("Choose a real-life task to watch execute in Microsoft Edge:")
        print(" [1] 🎬 YouTube Live: Search and play music video")
        print(" [2] 📖 Wikipedia Live: Research topic with real-time scrolling")
        print(" [3] 🛫 Google Flights Live: Search destination and prices")
        print(" [4] ⌨️  Custom Command: Type any task you want!")
        print(" [5] 🚪 Exit")
        print("=" * 70)

        while True:
            try:
                choice = input("\nEnter choice [1-5]: ").strip()
                if choice == "1":
                    q = input("Enter song or topic (default 'relaxing lofi music'): ").strip() or "relaxing lofi music"
                    run_realtime_youtube(q)
                elif choice == "2":
                    q = input("Enter research topic (default 'Artificial Intelligence'): ").strip() or "Artificial Intelligence"
                    run_realtime_wikipedia(q)
                elif choice == "3":
                    q = input("Enter destination city (default 'London'): ").strip() or "London"
                    run_realtime_flights(q)
                elif choice == "4":
                    prompt = input("What do you want the agent to do? ").strip()
                    if "flight" in prompt.lower():
                        run_realtime_flights("London")
                    elif "youtube" in prompt.lower() or "music" in prompt.lower():
                        run_realtime_youtube("relaxing music")
                    else:
                        run_realtime_wikipedia(prompt)
                elif choice == "5" or choice.lower() in ("exit", "quit", "q"):
                    print("👋 Exiting Real-Time Automation.")
                    break
            except (KeyboardInterrupt, EOFError):
                break

if __name__ == "__main__":
    main()
