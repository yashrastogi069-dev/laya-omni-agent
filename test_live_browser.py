from playwright.sync_api import sync_playwright
import time

print("Opening live browser...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto("https://www.google.com")
    
    # Check for cookie dialog
    for name in ["Accept all", "I agree", "Stay signed out"]:
        try:
            page.get_by_role("button", name=name).click(timeout=1500)
            break
        except Exception:
            pass
            
    search_box = page.locator("textarea[name='q'], input[name='q']").first
    search_box.click()
    search_box.fill("Laya AI Decision Engine")
    page.keyboard.press("Enter")
    page.wait_for_timeout(3000)
    print("Page Title:", page.title())
    browser.close()

print("Browser test complete!")
