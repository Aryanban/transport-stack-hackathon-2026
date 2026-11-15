"""Exercise the PS2 app: 3D bus/metro fleet rendering, pure daylight theme, camera controls."""
import argparse
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def verify_ui(args):
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.chromium,
            args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"]
            + (["--single-process", "--no-zygote", "--disable-dev-shm-usage"] if args.single_process else []),
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        provider_failures = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: errors.append(msg.text)
                if msg.type == "error" and not msg.location.get("url", "").startswith(
                    "https://tiles.openfreemap.org/") else None)
        page.on("requestfailed", lambda request: provider_failures.append(request.url)
                if request.url.startswith("https://tiles.openfreemap.org/") else None)
        if args.offline_basemap:
            # Abort at the app boundary by returning a valid, source-free style.
            # This leaves the real GTFS and the actual WebGL renderer in use.
            page.route("https://tiles.openfreemap.org/styles/*", lambda route: route.fulfill(json={
                "version": 8, "sources": {}, "layers": [{"id": "background",
                "type": "background", "paint": {"background-color": "#e7eeeb"}}]}))

        page.goto(args.url, wait_until="domcontentloaded")
        assert "/ps2/" in page.url
        expect(page.locator(".transit-card").first).to_be_visible(timeout=45_000)
        expect(page.locator("#btn-recenter")).to_be_visible()
        expect(page.locator("#hud-bottom-eta")).to_be_visible()
        expect(page.locator(".dest-eta-pin")).to_be_visible()
        expect(page.locator("#hud-subtext")).to_contain_text("Scheduled route preview")
        expect(page.locator("#hud-eta-dist")).to_contain_text("km")
        expect(page.locator("#vehicle-floating-speed")).to_have_text("Preview")
        # Quick corridors should be completely removed
        expect(page.locator("#corridor-chips")).to_have_count(0)
        expect(page.locator(".quick-corridors")).to_have_count(0)

        # Theme toggle button should be completely removed
        expect(page.locator("#btn-toggle-theme")).to_have_count(0)
        expect(page.locator("body")).not_to_have_class(re.compile(r"\btheme-night\b"))

        pause = page.locator("#hud-sound-toggle")
        pause.click()
        expect(pause).to_have_attribute("aria-pressed", "true")
        pause.click()
        origin, destination = (page.locator("#" + field).input_value()
                               for field in ("origin", "destination"))
        page.locator("#btn-swap-stops").click()
        expect(page.locator("#origin")).to_have_value(destination)
        expect(page.locator("#destination")).to_have_value(origin)
        expect(page.locator("#planner button[type=submit]")).to_be_enabled(timeout=20_000)
        page.locator("#btn-swap-stops").click()
        expect(page.locator("#origin")).to_have_value(origin)
        expect(page.locator("#destination")).to_have_value(destination)
        expect(page.locator("#hud-bottom-eta")).to_be_visible()
        page.locator("#btn-toggle-live-fleet").click()
        expect(page.locator("#fleet-count-text")).to_have_text(
            re.compile(r"(3d buses live|live buses|not configured|no fresh gps positions)", re.I), timeout=25_000)
        expect(page.locator("#hud-subtext")).to_contain_text("Scheduled route preview")
        page.screenshot(path=args.output / "day.png")

        # Verify 3D Bus and Metro Sprite Models are loaded in MapLibre
        page.wait_for_function(
            "Boolean(window.transitMap && window.transitMap.map && window.transitMap.map.hasImage('bus-3d-model') && window.transitMap.map.hasImage('metro-3d-model'))",
            timeout=15_000
        )
        assert page.evaluate("transitMap.map.getLayer('live-fleet-layer').type === 'symbol'")
        assert page.evaluate("transitMap.map.getLayer('metro-trains-layer').type === 'symbol'")
        assert page.evaluate("transitMap.map.getLayer('live-fleet-glow') === undefined")

        # Verify Camera Tilt & Recenter Controls
        page.locator("#btn-follow-vehicle").click()
        expect(page.locator("#btn-follow-vehicle")).to_have_attribute("aria-pressed", "true")
        page.wait_for_function("transitMap.map.getPitch() > 63", timeout=10_000)
        page.locator("#btn-recenter").click()
        assert abs(page.evaluate("transitMap.map.getPitch()") - 64) < 0.1
        assert abs(page.evaluate("transitMap.map.getZoom()") - 16.6) < 0.1
        assert page.evaluate('transitMap.map.getLayer("preview-headlight-throw") !== undefined')
        page.screenshot(path=args.output / "fleet-3d.png")

        # Responsive Mobile Viewport
        page.set_viewport_size({"width": 390, "height": 844})
        page.emulate_media(reduced_motion="reduce")
        before = page.evaluate("transitMap.animProgress")
        page.wait_for_timeout(200)
        assert page.evaluate("transitMap.animProgress") == before
        page.screenshot(path=args.output / "mobile.png")
        page.locator("#btn-cancel-route").click()
        expect(page.locator("#hud-bottom-eta")).to_be_hidden()
        assert not errors, errors
        print(f"Browser checks passed. Provider request failures: {len(provider_failures)}")
        if args.offline_basemap:
            print("Verified with a source-free basemap. Street tiles and building extrusions were not exercised.")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/")
    parser.add_argument("--output", type=Path, default=Path("artifacts/transit"))
    parser.add_argument("--chromium", help="Optional installed Chromium executable")
    parser.add_argument("--single-process", action="store_true", help="Use a single-process headless shell")
    parser.add_argument("--offline-basemap", action="store_true", help="Exercise the map without an external tile provider")
    verify_ui(parser.parse_args())
