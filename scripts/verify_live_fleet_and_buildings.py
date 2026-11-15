import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = Path("/Users/aryanbansal/.gemini/antigravity/brain/59777929-c859-4958-b01e-06842e1c36cf")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def test_fleet_and_buildings():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        print("1. Opening http://127.0.0.1:8000/ps2/ ...")
        page.goto("http://127.0.0.1:8000/ps2/", wait_until="networkidle")
        page.wait_for_timeout(2000)
        
        # Click Live Fleet button
        print("2. Toggling Live Fleet...")
        page.locator("#btn-toggle-live-fleet").click()
        page.wait_for_timeout(2500)
        
        # Fly to the exact location from the user's screenshot (Old Delhi / Karol Bagh / Civil Lines)
        # Lat: 28.66, Lon: 77.21, Zoom: 13.5
        print("3. Flying camera to Old Delhi / Karol Bagh area...")
        page.evaluate("""() => {
            if (window.transitMap && window.transitMap.map) {
                window.transitMap.map.flyTo({
                    center: [77.21, 28.66],
                    zoom: 13.5,
                    pitch: 25,
                    duration: 1000
                });
            }
        }""")
        page.wait_for_timeout(2500)
        
        out_path = ARTIFACTS_DIR / "ps2_live_fleet_decluttered_daylight.png"
        page.screenshot(path=str(out_path))
        print(f"4. Screenshot saved to {out_path}")
        browser.close()

if __name__ == "__main__":
    test_fleet_and_buildings()
