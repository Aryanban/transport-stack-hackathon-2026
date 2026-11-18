// Records the real planner (http://127.0.0.1:8020) in one session and logs when each action happens.
// Uses the global Playwright install. Output: public/clips/app.webm and public/clips/marks.json.
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { renameSync, writeFileSync, readdirSync, mkdirSync } from "node:fs";
const require = createRequire(execSync("npm root -g").toString().trim() + "/");
const { chromium } = require("playwright");

const W = 1440, H = 900, DIR = "public/clips/raw";
mkdirSync(DIR, { recursive: true });
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"] });
const ctx = await browser.newContext({ viewport: { width: W, height: H }, recordVideo: { dir: DIR, size: { width: W, height: H } } });
const page = await ctx.newPage();
const t0 = Date.now();
const marks = {};
const mark = (k) => { marks[k] = (Date.now() - t0) / 1000; console.log(k, marks[k].toFixed(1)); };
const wait = (s) => page.waitForTimeout(s * 1000);

await page.goto("http://127.0.0.1:8020/?from=Kashmere%20Gate%20ISBT&to=Nehru%20Place&depart=2026-11-24T18:00", { waitUntil: "domcontentloaded" });
await page.locator("#options li, #options .option, #options > *").first().waitFor({ timeout: 60000 });
await wait(4); // let the map finish drawing the route
mark("plan");
await wait(5);

await page.locator('#hours button[data-h="5"]').waitFor({ timeout: 30000 });
// scroll the results panel the way a person would, so the hour chart comes into view
await page.evaluate(() => {
  const day = document.getElementById("day");
  let el = day.parentElement;
  while (el && el.scrollHeight <= el.clientHeight + 4) el = el.parentElement;
  const top = day.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop - 120;
  el.scrollTo({ top, behavior: "smooth" });
});
await wait(1.5);
mark("hours");
await wait(1);
await page.locator('#hours button[data-h="5"]').click();
mark("hour5");
await wait(4.5);
await page.locator('#hours button[data-h="18"]').click();
mark("hour18");
await wait(4);

mark("speeds");
await page.locator("#btn-toggle-speeds").click();
await wait(5);
await page.locator("#btn-toggle-speeds").click();

mark("live");
await page.locator("#btn-toggle-live-fleet").click();
await wait(6);

// zoom in on the destination like a scroll-wheel zoom, then tap a stop on the route
await page.evaluate(() => {
  const m = window.transitMap.map;
  m.easeTo({ center: [77.2513, 28.5494], zoom: 15, pitch: 0, duration: 2000 });
});
await wait(3);
const pt = await page.evaluate(() => {
  const m = window.transitMap?.map;
  if (!m) return null;
  const layers = ["route-stops-circles", "all-stops-circles"].filter((l) => m.getLayer(l));
  const f = m.queryRenderedFeatures({ layers });
  if (!f.length) return null;
  const mid = m.project(m.getCenter());
  f.sort((a, b) => { const pa = m.project(a.geometry.coordinates), pb = m.project(b.geometry.coordinates); return Math.hypot(pa.x - mid.x, pa.y - mid.y) - Math.hypot(pb.x - mid.x, pb.y - mid.y); });
  const p = m.project(f[0].geometry.coordinates);
  const r = m.getCanvas().getBoundingClientRect();
  return { x: r.left + p.x, y: r.top + p.y, name: f[0].properties?.name ?? null };
});
console.log("stop", JSON.stringify(pt));
mark("stop");
if (pt) await page.mouse.click(pt.x, pt.y); else console.log("no stop found");
await wait(6);

await page.locator("#route-q").scrollIntoViewIfNeeded();
mark("route");
await page.locator("#route-q").pressSequentially("534", { delay: 120 });
await page.locator("#route-results button").first().waitFor({ timeout: 15000 });
await wait(0.6);
await page.locator("#route-results button").first().click();
await wait(6);
mark("end");

await ctx.close();
await browser.close();
const f = readdirSync(DIR).find((n) => n.endsWith(".webm"));
renameSync(`${DIR}/${f}`, "public/clips/app.webm");
writeFileSync("public/clips/marks.json", JSON.stringify({ ...marks, stopFound: !!pt }, null, 2));
