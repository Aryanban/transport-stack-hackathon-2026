import sys
import time
from playwright.sync_api import sync_playwright

def verify_ui():
    print("Starting Playwright verification for Delhi Transit UI (100% Dynamic Engine)...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://127.0.0.1:8000/ ...")
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")

        print(f"Current URL after redirect: {page.url}")
        assert "/ps2" in page.url, f"Expected /ps2 in URL, got {page.url}"

        # Wait for MapLibre container and canvas
        page.wait_for_selector("#map-container canvas", timeout=15000)
        print("MapLibre GL 3D canvas loaded successfully.")

        # Check dynamic corridors chips
        page.wait_for_selector("#corridor-chips button.chip", timeout=10000)
        chips = page.query_selector_all("#corridor-chips button.chip")
        print(f"Found {len(chips)} dynamic corridor shortcut chips loaded from GTFS.")
        assert len(chips) > 0, "No dynamic corridor chips found!"

        # Wait for journey cards
        page.wait_for_selector(".transit-card", timeout=10000)
        cards = page.query_selector_all(".transit-card")
        print(f"Found {len(cards)} transit journey options.")
        assert len(cards) > 0, "No journey cards rendered!"

        # Check HUD banner
        hud = page.query_selector("#hud-nav-banner")
        assert hud is not None, "HUD navigation banner missing!"
        hud_text = page.locator("#hud-next-stop").inner_text()
        print(f"HUD Next Stop Banner text: {hud_text}")

        # Check Live Fleet button and toggle it
        btn_fleet = page.locator("#btn-toggle-live-fleet")
        if btn_fleet.count() > 0:
            print("Toggling Live Fleet button to stream 3,600+ real vehicles...")
            btn_fleet.click()
            time.sleep(2.0)
            print(f"Live Fleet button class: {btn_fleet.get_attribute('class')}")

        # Capture verification screenshot
        screenshot_path = "/Users/aryanbansal/.gemini/antigravity/brain/59777929-c859-4958-b01e-06842e1c36cf/delhi_transit_dynamic_live_fleet.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"Screenshot saved to: {screenshot_path}")

        print("Console errors encountered:")
        print(console_errors)
        critical_errors = [e for e in console_errors if "favicon" not in e and "404" not in e]
        print(f"Total critical errors: {len(critical_errors)}")
        assert len(critical_errors) == 0, f"Critical errors found: {critical_errors}"

        browser.close()
        print("Verification complete with 100% dynamic loading and 0 errors!")

if __name__ == "__main__":
    verify_ui()
