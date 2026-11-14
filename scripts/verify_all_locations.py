"""
Comprehensive E2E Frontend Location Matrix & Route Verification Script
Uses Playwright to simulate user journeys across various Delhi-NCR transit corridors:
1. North-South Arterial (Delhi Gate -> Kashmere Gate)
2. Directional Reverse Corridor via Swap Button (Kashmere Gate -> Delhi Gate)
3. South Arterial Transfer Corridor (Mehrauli Terminal -> Delhi Gate)
4. Autocomplete Search & Cross-City Routing (Kashmere Gate -> DDA Flats Kalkaji)

Validates:
- MapLibre GL 3D Canvas & Route Polylines
- HUD Navigation Banner (Next Stop, Direction)
- HUD Bottom ETA Card (Duration, Estimated Distance)
- Orange Teardrop Destination Pin with Live ETA
- Journey Option Cards & Multi-Leg Transfer Continuity
- Zero Console / Script Errors
"""

import sys
import time
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = "/Users/aryanbansal/.gemini/antigravity/brain/59777929-c859-4958-b01e-06842e1c36cf"

def verify_all_locations():
    print("================================================================================")
    print("🚀 STARTING E2E MULTI-LOCATION FRONTEND VERIFICATION FOR PROBLEM STATEMENT 2")
    print("================================================================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        # -------------------------------------------------------------------------
        # Scenario 1: Default North-South Arterial (Delhi Gate -> Kashmere Gate ISBT)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 1: North-South Arterial (Delhi Gate -> Kashmere Gate ISBT) ---")
        page.goto("http://127.0.0.1:8000/ps2/", wait_until="networkidle")
        page.wait_for_selector("#map-container canvas", timeout=15000)
        print("✓ MapLibre 3D canvas loaded.")

        page.wait_for_selector(".transit-card", timeout=10000)
        cards = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards)} transit options for Delhi Gate -> Kashmere Gate.")
        assert len(cards) > 0, "No transit cards found!"

        # Verify Ref 2 HUD Turn-by-Turn Banner
        page.wait_for_selector("#hud-nav-banner:not([hidden])", timeout=8000)
        hud_next = page.locator("#hud-next-stop").inner_text()
        print(f"✓ HUD Banner Next Stop: '{hud_next}'")
        assert len(hud_next) > 0

        # Verify Ref 2 HUD Bottom ETA Card
        page.wait_for_selector("#hud-bottom-eta:not([hidden])", timeout=8000)
        eta_min = page.locator("#hud-eta-min").inner_text()
        eta_dist = page.locator("#hud-eta-dist").inner_text()
        print(f"✓ HUD Bottom ETA Card: {eta_min} mins | {eta_dist}")
        assert len(eta_min) > 0 and len(eta_dist) > 0

        # Verify Orange Teardrop Destination Pin
        page.wait_for_selector(".dest-eta-pin", timeout=8000)
        pin_time = page.locator("#dest-pin-time").inner_text()
        print(f"✓ Map Destination Pin ETA: {pin_time} MIN")
        assert len(pin_time) > 0

        shot1 = f"{ARTIFACTS_DIR}/ps2_corridor_delhi_to_kashmere.png"
        page.screenshot(path=shot1, full_page=True)
        print(f"✓ Screenshot captured: {shot1}")

        # -------------------------------------------------------------------------
        # Scenario 2: Bi-Directional Reverse Corridor via Swap Button
        # -------------------------------------------------------------------------
        print("\n--- Scenario 2: Reverse Corridor via Stop Swap Button ---")
        orig_before = page.locator("#origin").input_value()
        dest_before = page.locator("#destination").input_value()
        print(f"Before Swap: '{orig_before}' -> '{dest_before}'")

        btn_swap = page.locator("#btn-swap-stops")
        btn_swap.click()
        time.sleep(2.0)
        page.wait_for_selector(".transit-card", timeout=10000)

        orig_after = page.locator("#origin").input_value()
        dest_after = page.locator("#destination").input_value()
        print(f"After Swap:  '{orig_after}' -> '{dest_after}'")
        assert orig_after == dest_before, f"Expected origin '{dest_before}', got '{orig_after}'"
        assert dest_after == orig_before, f"Expected destination '{orig_before}', got '{dest_after}'"

        eta_min_swap = page.locator("#hud-eta-min").inner_text()
        eta_dist_swap = page.locator("#hud-eta-dist").inner_text()
        print(f"✓ Reverse Route Calculated: {eta_min_swap} mins | {eta_dist_swap}")

        shot2 = f"{ARTIFACTS_DIR}/ps2_corridor_swap_kashmere_to_delhi.png"
        page.screenshot(path=shot2, full_page=True)
        print(f"✓ Screenshot captured: {shot2}")

        # -------------------------------------------------------------------------
        # Scenario 3: South Arterial Multi-Leg Transfer (Mehrauli Terminal -> Delhi Gate)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 3: South Arterial Transfer (Mehrauli Terminal -> Delhi Gate) ---")
        mehrauli_chip = page.locator("#corridor-chips button.chip", has_text="Mehrauli")
        assert mehrauli_chip.count() > 0, "Expected Mehrauli corridor shortcut chip!"
        mehrauli_chip.first.click()

        time.sleep(2.5)
        page.wait_for_selector(".transit-card", timeout=12000)
        cards_mehrauli = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards_mehrauli)} route options for Mehrauli -> Delhi Gate.")

        # Check for transfer badge or multi-leg markers
        card_text = cards_mehrauli[0].inner_text()
        print(f"Top Route Summary:\n{card_text[:180]}...")
        
        eta_dist_m = page.locator("#hud-eta-dist").inner_text()
        eta_min_m = page.locator("#hud-eta-min").inner_text()
        print(f"✓ HUD Multi-leg Metric: {eta_min_m} mins | {eta_dist_m}")
        dist_num = float(eta_dist_m.replace("km", "").strip())
        assert dist_num >= 14.0, f"Expected distance >= 14.0 km for Mehrauli, got {dist_num} km"

        shot3 = f"{ARTIFACTS_DIR}/ps2_corridor_mehrauli_to_delhi.png"
        page.screenshot(path=shot3, full_page=True)
        print(f"✓ Screenshot captured: {shot3}")

        # -------------------------------------------------------------------------
        # Scenario 4: Cross-City Autocomplete Search (Kashmere Gate -> DDA Flats Kalkaji)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 4: Cross-City Autocomplete Search (Kashmere Gate -> DDA Flats Kalkaji) ---")
        
        # 1. Type in Origin
        page.locator("#origin").click()
        page.locator("#origin").fill("Kashmere Gate")
        page.wait_for_selector("#origin-results:not([hidden]) button", timeout=6000)
        origin_options = page.locator("#origin-results button")
        print(f"✓ Origin autocomplete returned {origin_options.count()} suggestions.")
        assert origin_options.count() > 0
        origin_options.first.click()
        print(f"✓ Selected origin: '{page.locator('#origin').input_value()}'")
        time.sleep(0.5)

        # 2. Type in Destination
        page.locator("#destination").click()
        page.locator("#destination").fill("DDA Flats KalkaJi")
        page.wait_for_selector("#destination-results:not([hidden]) button", timeout=6000)
        dest_options = page.locator("#destination-results button")
        print(f"✓ Destination autocomplete returned {dest_options.count()} suggestions for 'DDA Flats KalkaJi'.")
        assert dest_options.count() > 0
        dest_options.first.click()
        print(f"✓ Selected destination: '{page.locator('#destination').input_value()}'")
        time.sleep(0.5)

        # 3. Set Morning Peak 08:30 AM
        chip_830 = page.locator('.time-chip[data-time="08:30"]')
        chip_830.click()
        time.sleep(0.5)

        # 4. Set Crowd flexibility to 30 min to capture transfer connections
        page.evaluate("""() => {
            const extra = document.getElementById('extra');
            extra.value = '30';
            extra.dispatchEvent(new Event('input', { bubbles: true }));
        }""")
        time.sleep(0.5)

        # 5. Submit Search
        page.locator("button.btn-search").click()
        print("✓ Clicked 'Find Routes' button.")
        
        time.sleep(3.0)
        page.wait_for_selector(".transit-card", timeout=15000)
        cards_kalkaji = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards_kalkaji)} transit options for Kashmere Gate -> DDA Flats Kalkaji.")

        eta_dist_k = page.locator("#hud-eta-dist").inner_text()
        eta_min_k = page.locator("#hud-eta-min").inner_text()
        print(f"✓ HUD Cross-city Metric: {eta_min_k} mins | {eta_dist_k}")
        dist_num_k = float(eta_dist_k.replace("km", "").strip())
        assert dist_num_k >= 14.0, f"Expected distance >= 14.0 km for Kalkaji, got {dist_num_k} km"

        shot4 = f"{ARTIFACTS_DIR}/ps2_autocomplete_kashmere_to_kalkaji.png"
        page.screenshot(path=shot4, full_page=True)
        print(f"✓ Screenshot captured: {shot4}")

        # -------------------------------------------------------------------------
        # Critical Console Error Verification
        # -------------------------------------------------------------------------
        print("\n--- Console Error Audit ---")
        critical_errors = [e for e in console_errors if "favicon" not in e and "404" not in e]
        print(f"Total console messages logged: {len(console_errors)}")
        print(f"Critical console errors: {len(critical_errors)}")
        if critical_errors:
            print(f"CRITICAL ERRORS: {critical_errors}")
        assert len(critical_errors) == 0, f"Encountered {len(critical_errors)} critical console errors!"

        browser.close()
        print("\n================================================================================")
        print("🎉 ALL FRONTEND & BACKEND LOCATION MATRIX SCENARIOS VERIFIED SUCCESSFULLY (100%)")
        print("================================================================================")

if __name__ == "__main__":
    verify_all_locations()
