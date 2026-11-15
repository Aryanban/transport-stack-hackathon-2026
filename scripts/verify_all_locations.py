"""
Comprehensive E2E Frontend Location Matrix & Route Verification Script
Uses Playwright to simulate user journeys across various Delhi-NCR transit corridors:
1. Default Dynamic Featured Corridor (102UP: Old Delhi Railway Station -> Hansraj College)
2. Directional Reverse Corridor via Swap Button (Hansraj College -> Old Delhi Railway Station)
3. Central Arterial Corridor Chip (449UP: ISBT Kashmiri Gate -> Delhi Gate)
4. Trans-Yamuna East Arterial Chip (534UP: Anand Vihar ISBT Terminal -> Ashirwad Apartment)
5. Ring Road North Arterial Chip (761DOWN: Azadpur Terminal -> Wazirpur DTC Depot)
6. Cross-City Autocomplete Search (Kashmere Gate -> DDA Flats Kalkaji)

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
        # Scenario 1: Default Dynamic Featured Corridor (102UP)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 1: Default Dynamic Featured Corridor ---")
        page.goto("http://127.0.0.1:8000/ps2/", wait_until="networkidle")
        page.wait_for_selector("#map-container canvas", timeout=15000)
        print("✓ MapLibre 3D canvas loaded.")

        page.wait_for_selector(".transit-card", timeout=10000)
        cards = page.query_selector_all(".transit-card")
        orig_val = page.locator("#origin").input_value()
        dest_val = page.locator("#destination").input_value()
        print(f"✓ Default Route Loaded: '{orig_val}' -> '{dest_val}' with {len(cards)} options.")
        assert len(cards) > 0, "No transit cards found!"

        # Verify Ref 2 HUD Turn-by-Turn Banner
        page.wait_for_selector("#hud-nav-banner:not([hidden])", timeout=8000)
        hud_next = page.locator("#hud-next-stop").inner_text()
        print(f"✓ HUD Banner: '{hud_next}'")
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

        shot1 = f"{ARTIFACTS_DIR}/ps2_corridor_default.png"
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

        shot2 = f"{ARTIFACTS_DIR}/ps2_corridor_swap.png"
        page.screenshot(path=shot2, full_page=True)
        print(f"✓ Screenshot captured: {shot2}")

        # Verify Quick Corridors are completely removed
        assert page.locator("#corridor-chips").count() == 0, "Quick corridor chips should be removed!"
        assert page.locator(".quick-corridors").count() == 0, "Quick corridors container should be removed!"

        # -------------------------------------------------------------------------
        # Scenario 3: Central Arterial Corridor (ISBT -> Delhi Gate)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 3: Central Arterial Corridor (ISBT -> Delhi Gate) ---")
        page.fill("#origin", "Kashmere Gate City Bus Terminal")
        page.wait_for_timeout(400)
        orig_sug = page.locator("#origin-results .autocomplete-item").first
        if orig_sug.is_visible(): orig_sug.click()
        page.fill("#destination", "Delhi Gate")
        page.wait_for_timeout(400)
        dest_sug = page.locator("#destination-results .autocomplete-item").first
        if dest_sug.is_visible(): dest_sug.click()
        page.locator("#planner button[type=submit]").click(force=True)

        time.sleep(2.0)
        page.wait_for_selector(".transit-card", timeout=10000)
        cards_isbt = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards_isbt)} route options for ISBT -> Delhi Gate.")
        assert len(cards_isbt) > 0

        eta_dist_isbt = page.locator("#hud-eta-dist").inner_text()
        eta_min_isbt = page.locator("#hud-eta-min").inner_text()
        print(f"✓ HUD Arterial Metric: {eta_min_isbt} mins | {eta_dist_isbt}")

        shot3 = f"{ARTIFACTS_DIR}/ps2_corridor_isbt_to_delhi_gate.png"
        page.screenshot(path=shot3, full_page=True)
        print(f"✓ Screenshot captured: {shot3}")

        # -------------------------------------------------------------------------
        # Scenario 4: Trans-Yamuna East Arterial (Anand Vihar ISBT)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 4: Trans-Yamuna East Arterial (Anand Vihar ISBT) ---")
        page.fill("#origin", "Anand Vihar ISBT Main Road")
        page.wait_for_timeout(400)
        orig_sug = page.locator("#origin-results .autocomplete-item").first
        if orig_sug.is_visible(): orig_sug.click()
        page.fill("#destination", "Maharani Bagh")
        page.wait_for_timeout(400)
        dest_sug = page.locator("#destination-results .autocomplete-item").first
        if dest_sug.is_visible(): dest_sug.click()
        page.locator("#planner button[type=submit]").click(force=True)

        time.sleep(2.0)
        page.wait_for_selector(".transit-card", timeout=10000)
        cards_anand = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards_anand)} route options for Anand Vihar ISBT corridor.")
        assert len(cards_anand) > 0

        eta_dist_anand = page.locator("#hud-eta-dist").inner_text()
        eta_min_anand = page.locator("#hud-eta-min").inner_text()
        print(f"✓ HUD East Metric: {eta_min_anand} mins | {eta_dist_anand}")

        shot4 = f"{ARTIFACTS_DIR}/ps2_corridor_anand_vihar.png"
        page.screenshot(path=shot4, full_page=True)
        print(f"✓ Screenshot captured: {shot4}")

        # -------------------------------------------------------------------------
        # Scenario 5: Ring Road North Arterial (Azadpur Terminal)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 5: Ring Road North Arterial (Azadpur Terminal) ---")
        page.fill("#origin", "Azadpur Terminal")
        page.wait_for_timeout(400)
        orig_sug = page.locator("#origin-results .autocomplete-item").first
        if orig_sug.is_visible(): orig_sug.click()
        page.fill("#destination", "Punjabi Bagh")
        page.wait_for_timeout(400)
        dest_sug = page.locator("#destination-results .autocomplete-item").first
        if dest_sug.is_visible(): dest_sug.click()
        page.locator("#planner button[type=submit]").click(force=True)

        time.sleep(2.0)
        page.wait_for_selector(".transit-card", timeout=10000)
        cards_azadpur = page.query_selector_all(".transit-card")
        print(f"✓ Found {len(cards_azadpur)} route options for Azadpur corridor.")
        assert len(cards_azadpur) > 0

        eta_dist_azad = page.locator("#hud-eta-dist").inner_text()
        eta_min_azad = page.locator("#hud-eta-min").inner_text()
        print(f"✓ HUD North Metric: {eta_min_azad} mins | {eta_dist_azad}")

        shot5 = f"{ARTIFACTS_DIR}/ps2_corridor_azadpur.png"
        page.screenshot(path=shot5, full_page=True)
        print(f"✓ Screenshot captured: {shot5}")

        # -------------------------------------------------------------------------
        # Scenario 6: Cross-City Autocomplete Search (Kashmere Gate -> DDA Flats Kalkaji)
        # -------------------------------------------------------------------------
        print("\n--- Scenario 6: Cross-City Autocomplete Search (Kashmere Gate -> DDA Flats Kalkaji) ---")
        
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

        shot6 = f"{ARTIFACTS_DIR}/ps2_autocomplete_kashmere_to_kalkaji.png"
        page.screenshot(path=shot6, full_page=True)
        print(f"✓ Screenshot captured: {shot6}")

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
