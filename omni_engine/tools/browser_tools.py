"""
Visual Browser Automation Toolset (Microsoft Edge + Playwright)
- Launches real Edge browser in full screen with live glowing HUD
- Form filling, clicking, and visual highlighting
- Web page screenshot capture
- Evaluates DOM elements with Laya System 1
"""

import time
import os
from playwright.sync_api import sync_playwright

def inject_hud(page, title="⚡ LAYA OMNI-AGENT REAL-TIME BROWSER"):
    try:
        page.evaluate(f"""() => {{
            if (document.getElementById('omni-hud')) return;
            const hud = document.createElement('div');
            hud.id = 'omni-hud';
            hud.innerHTML = `
                <div style="font-weight:900; letter-spacing:1px; color:#00ff88; font-size:15px; margin-bottom:4px;">
                    {title}
                </div>
                <div id="omni-status" style="font-size:13px; color:#f1f5f9;">
                    🤖 Autonomous Navigation Active
                </div>
            `;
            hud.style.position = 'fixed';
            hud.style.top = '14px';
            hud.style.left = '50%';
            hud.style.transform = 'translateX(-50%)';
            hud.style.zIndex = '2147483647';
            hud.style.background = 'rgba(15, 23, 42, 0.95)';
            hud.style.border = '2px solid #00ff88';
            hud.style.borderRadius = '12px';
            hud.style.padding = '10px 22px';
            hud.style.minWidth = '480px';
            hud.style.boxShadow = '0 10px 30px rgba(0,255,136,0.3)';
            hud.style.fontFamily = 'Segoe UI, sans-serif';
            hud.style.textAlign = 'center';
            hud.style.pointerEvents = 'none';
            document.body.appendChild(hud);
        }}""")
    except Exception:
        pass


def update_hud(page, text: str):
    try:
        page.evaluate(f"""() => {{
            const el = document.getElementById('omni-status');
            if (el) el.innerHTML = `{text}`;
        }}""")
    except Exception:
        pass


def tool_visual_browse(url_or_query: str) -> str:
    """Launches full-screen Microsoft Edge, navigates to target URL or search, scrolls and scrapes content."""
    query = url_or_query.strip()
    target_url = query if query.startswith("http") else f"https://www.google.com/search?q={query.replace(' ', '+')}"

    extracted_content = ""
    title = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="msedge",
            headless=False,
            slow_mo=60,
            args=["--start-maximized"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto(target_url, timeout=18000, wait_until="domcontentloaded")
        time.sleep(1.0)
        title = page.title()
        inject_hud(page, f"⚡ LAYA BROWSER: {title[:40]}")

        # Smooth scrolling
        update_hud(page, "📜 <b>Deep Extraction:</b> Scanning page sections & data...")
        for _ in range(3):
            page.evaluate("window.scrollBy({top: 400, behavior: 'smooth'});")
            time.sleep(0.7)

        # Extract paragraphs and links
        paras = page.locator("p, h1, h2, h3, article, main, table").all_inner_texts()
        clean = [p.strip() for p in paras if len(p.strip()) > 35]
        extracted_content = "\n\n".join(clean[:15])

        update_hud(page, "✅ <b>Extraction Complete!</b> Browser will remain open for 5 seconds.")
        time.sleep(5.0)
        browser.close()

    return f"### Visual Browser Results for `{target_url}` (Title: '{title}'):\n\n{extracted_content[:2500]}"


def tool_browser_screenshot(url: str, output_path: str = "web_screenshot.png") -> str:
    """Visits any URL in Microsoft Edge and captures a clean webpage screenshot."""
    clean_url = url.strip()
    if not clean_url.startswith("http"):
        clean_url = "https://" + clean_url

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
        page.goto(clean_url, timeout=15000, wait_until="domcontentloaded")
        time.sleep(1.5)
        page.screenshot(path=output_path, full_page=False)
        browser.close()

    return f"✅ Webpage screenshot captured and saved to: `{output_path}`"
