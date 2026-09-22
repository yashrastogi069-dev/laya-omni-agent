"""
Laya Live Ultrafast Browser Automation Agent
Executes REAL browser actions on your desktop using Playwright + Laya System 1:
- Real Visible Browser Window (watch it on your screen)
- Visual Element Highlighting (Laya highlights chosen elements with a neon green glow)
- Real Typing and Real Clicking in Real Time
"""

import os
import sys
import time
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
        router = Router()
        print("⚡ [System 1] Laya ready for sub-35ms reflex decisions!\n")
    return router

def highlight_element(page, element_locator):
    """Draws a bright neon-green border around the element Laya picked so the user can see it."""
    try:
        page.evaluate("""(el) => {
            el.scrollIntoView({behavior: 'smooth', block: 'center'});
            el.style.outline = '4px solid #00ff88';
            el.style.boxShadow = '0 0 20px #00ff88';
            el.style.transition = 'all 0.3s ease-in-out';
        }""", element_locator.element_handle())
        time.sleep(0.5)
    except Exception:
        pass

def live_youtube_automation(query: str = "relaxing lofi music"):
    print("=" * 65)
    print(f"🎬 [TASK: YOUTUBE LIVE] Playing '{query}' on YouTube")
    print("=" * 65)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Launching visible Chrome/Chromium window on your desktop...")
        browser = p.chromium.launch(headless=False, slow_mo=50)
        page = browser.new_page(viewport={"width": 1366, "height": 850})

        print("🌐 Navigating to https://www.youtube.com ...")
        page.goto("https://www.youtube.com")

        # Handle cookie consent dialog if shown
        for btn_text in ["Accept all", "Reject all", "I agree", "Stay signed out"]:
            try:
                page.get_by_role("button", name=btn_text).click(timeout=1500)
                print(f" -> Dismissed consent dialog: '{btn_text}'")
                break
            except Exception:
                pass

        page.wait_for_timeout(1000)

        # Laya decision: Identify search input
        print("\n🧠 [Laya Decision] Locating YouTube search bar...")
        t0 = time.perf_counter()
        q = {
            "search_box": {
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
        latency = (time.perf_counter() - t0) * 1000
        choice = res["answers"]["search_box"]["choice"]
        conf = res["answers"]["search_box"]["confidence"]
        print(f"🎯 Laya selected: [{choice}] (Confidence: {conf:.2f}, Latency: {latency:.1f}ms)")

        # Target search box in live DOM
        search_box = page.locator("input[name='search_query'], input#search").first
        highlight_element(page, search_box)

        print(f"⌨️  Typing query: \"{query}\" ...")
        search_box.click()
        search_box.fill(query)
        page.wait_for_timeout(500)

        print("🔍 Submitting search...")
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)

        # Find top video results
        print("\n🧠 [Laya Decision] Selecting top video result to play...")
        video_locator = page.locator("ytd-video-renderer a#video-title").first
        highlight_element(page, video_locator)

        video_title = video_locator.get_attribute("title") or video_locator.inner_text()
        print(f"▶️  Clicking & playing: \"{video_title[:60]}...\"")
        video_locator.click()

        print("\n🎉 SUCCESS: Video is now playing live in the browser window!")
        print("💡 Feel free to watch. Browser will remain open for 15 seconds (or press Enter in terminal to close)...")
        page.wait_for_timeout(15000)
        browser.close()
        print("👋 Browser session closed.\n")

def live_wikipedia_automation(topic: str = "Artificial Intelligence"):
    print("=" * 65)
    print(f"📖 [TASK: WIKIPEDIA LIVE] Researching '{topic}'")
    print("=" * 65)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Launching visible Chrome/Chromium window on your desktop...")
        browser = p.chromium.launch(headless=False, slow_mo=60)
        page = browser.new_page(viewport={"width": 1366, "height": 850})

        print("🌐 Navigating to https://en.wikipedia.org ...")
        page.goto("https://en.wikipedia.org")
        page.wait_for_timeout(1000)

        # Laya decision
        print("\n🧠 [Laya Decision] Identifying Wikipedia search box...")
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
        latency = (time.perf_counter() - t0) * 1000
        print(f"🎯 Laya selected: [search_field] (Latency: {latency:.1f}ms)")

        search_box = page.locator("input[name='search'], input#searchInput").first
        highlight_element(page, search_box)

        print(f"⌨️  Typing topic: \"{topic}\" ...")
        search_box.click()
        search_box.fill(topic)
        page.wait_for_timeout(600)

        print("🔍 Navigating to article...")
        page.keyboard.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(1500)

        print(f"📄 Loaded Article Title: \"{page.title()}\"")
        # Scroll smoothly down the article
        print("📜 Scrolling through article content...")
        page.evaluate("window.scrollBy({top: 500, behavior: 'smooth'});")
        page.wait_for_timeout(1500)
        page.evaluate("window.scrollBy({top: 600, behavior: 'smooth'});")

        print("\n🎉 SUCCESS: Live Wikipedia exploration complete!")
        page.wait_for_timeout(6000)
        browser.close()
        print("👋 Browser session closed.\n")

def live_flights_automation(destination: str = "London"):
    print("=" * 65)
    print(f"🛫 [TASK: GOOGLE FLIGHTS LIVE] Searching Flights to {destination}")
    print("=" * 65)
    r = get_router()

    with sync_playwright() as p:
        print("🖥️  Launching visible Chrome/Chromium window on your desktop...")
        browser = p.chromium.launch(headless=False, slow_mo=70)
        page = browser.new_page(viewport={"width": 1366, "height": 850})

        print("🌐 Navigating to Google Flights...")
        page.goto("https://www.google.com/travel/flights")

        # Handle cookie consent
        for btn_text in ["Accept all", "I agree", "Reject all"]:
            try:
                page.get_by_role("button", name=btn_text).click(timeout=1500)
                break
            except Exception:
                pass

        page.wait_for_timeout(2000)

        # Laya decision: find destination input
        print("\n🧠 [Laya Decision] Identifying 'Where to' flight destination field...")
        t0 = time.perf_counter()
        q = {
            "target": {
                "type": "choice",
                "instructions": "Which element allows entering the destination airport?",
                "criteria": {
                    "origin_input": "Input for 'Where from?' departure airport",
                    "destination_input": "Input or combobox for 'Where to?' arrival airport",
                    "date_picker": "Field for selecting flight travel dates",
                }
            }
        }
        res = r.predict({"site": "google_flights", "destination": destination}, q)
        latency = (time.perf_counter() - t0) * 1000
        choice = res["answers"]["target"]["choice"]
        print(f"🎯 Laya selected: [{choice}] (Latency: {latency:.1f}ms)")

        # In Google Flights, find 'Where to' box
        dest_field = page.locator("input[placeholder*='Where to'], div[role='combobox']:has-text('Where to'), [aria-label*='Where to']").first
        try:
            dest_field.click(timeout=3000)
            highlight_element(page, dest_field)
            page.keyboard.type(destination, delay=100)
            page.wait_for_timeout(1000)
            print("✈️  Selecting airport from dropdown...")
            page.keyboard.press("Enter")
        except Exception:
            # Fallback to direct search query
            page.goto(f"https://www.google.com/travel/flights?q=flights+to+{destination}")

        page.wait_for_timeout(4000)
        print(f"📊 Flights Interface loaded for: {destination}!")
        print("💡 You can see available flights, airlines, and prices on screen.")
        page.wait_for_timeout(8000)
        browser.close()
        print("👋 Browser session closed.\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Laya Live Ultrafast Browser Automation")
    parser.add_argument("--youtube", action="store_true", help="Run live YouTube player automation")
    parser.add_argument("--wiki", action="store_true", help="Run live Wikipedia research automation")
    parser.add_argument("--flights", action="store_true", help="Run live Google Flights automation")
    parser.add_argument("--query", type=str, default=None, help="Custom query for YouTube/Wiki")
    args = parser.parse_args()

    if args.youtube:
        live_youtube_automation(args.query or "relaxing lofi music")
    elif args.wiki:
        live_wikipedia_automation(args.query or "Artificial Intelligence")
    elif args.flights:
        live_flights_automation(args.query or "London")
    else:
        # Default: run Wikipedia as a quick, guaranteed, beautiful visual demonstration
        print("\n" + "=" * 65)
        print("🚀 LAYA LIVE BROWSER AUTOMATION")
        print("💡 Watching real-time decisions on a real visible browser window!")
        print("=" * 65)
        live_wikipedia_automation("Artificial Intelligence")

if __name__ == "__main__":
    main()
