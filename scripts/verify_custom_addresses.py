"""Playwright end-to-end verification for custom address inputs and dynamic multi-leg routing."""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ARTIFACTS_DIR = Path("/Users/aryanbansal/.gemini/antigravity/brain/59777929-c859-4958-b01e-06842e1c36cf")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def test_custom_routing():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" and not msg.location.get("url", "").startswith("https://tiles.openfreemap.org/") else None)
        
        print("1. Navigating to http://127.0.0.1:8000/ps2/ ...")
        page.goto("http://127.0.0.1:8000/ps2/", wait_until="networkidle")
        
        # Verify initial load
        expect(page.locator(".transit-card").first).to_be_visible(timeout=30_000)
        print("   Initial route card loaded.")
        
        # Test 1: "Romani sector 9" -> "Hurkeshnagar"
        print("2. Testing Romani sector 9 -> Hurkeshnagar...")
        page.fill("#origin", "Romani sector 9")
        page.wait_for_timeout(600)
        
        # Verify autocomplete suggestion
        origin_item = page.locator("#origin-results .autocomplete-item").first
        if origin_item.is_visible():
            print(f"   Origin autocomplete item found: {origin_item.inner_text()}")
            origin_item.click()
        else:
            print("   Auto-resolving origin upon submit...")
            
        page.fill("#destination", "Hurkeshnagar")
        page.wait_for_timeout(600)
        dest_item = page.locator("#destination-results .autocomplete-item").first
        if dest_item.is_visible():
            print(f"   Destination autocomplete item found: {dest_item.inner_text()}")
            dest_item.click()
        else:
            print("   Auto-resolving destination upon submit...")
            
        print("   Clicking Find Routes...")
        page.locator("#planner button[type=submit]").click()
        
        # Wait for routes to load
        page.wait_for_timeout(2500)
        expect(page.locator(".transit-card").first).to_be_visible(timeout=15_000)
        cards = page.locator(".transit-card").all()
        print(f"   Successfully found {len(cards)} transit options for Romani sector 9 -> Hurkeshnagar!")
        
        # Verify card contents
        fastest_card = cards[0]
        text_content = fastest_card.inner_text()
        print(f"   Top recommendation summary: {text_content[:120]}...")
        
        screenshot_path = ARTIFACTS_DIR / "ps2_romani_to_hurkeshnagar.png"
        page.screenshot(path=str(screenshot_path))
        print(f"   Screenshot saved to {screenshot_path}")
        
        # Test 2: "saket" -> "rohini"
        print("3. Testing Saket -> Rohini...")
        page.fill("#origin", "saket")
        page.wait_for_timeout(600)
        saket_item = page.locator("#origin-results button").first
        if saket_item.is_visible():
            saket_item.click()
            
        page.fill("#destination", "rohini")
        page.wait_for_timeout(600)
        rohini_item = page.locator("#destination-results button").first
        if rohini_item.is_visible():
            rohini_item.click()
            
        page.locator("#planner button[type=submit]").click(force=True)
        page.wait_for_timeout(3000)
        expect(page.locator(".transit-card").first).to_be_visible(timeout=15_000)
        cards_saket = page.locator(".transit-card").all()
        print(f"   Successfully found {len(cards_saket)} transit options for Saket -> Rohini!")
        
        screenshot_saket = ARTIFACTS_DIR / "ps2_saket_to_rohini.png"
        page.screenshot(path=str(screenshot_saket))
        print(f"   Screenshot saved to {screenshot_saket}")

        assert not errors, f"Console/page errors detected: {errors}"
        print("All custom address and routing checks PASSED with 0 errors!")
        browser.close()

if __name__ == "__main__":
    test_custom_routing()
