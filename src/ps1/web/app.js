// PS1 planner screen. Plain JS, no build step. State lives in the URL.
(() => {
  const $ = (id) => document.getElementById(id);
  // MapLibre cannot parse oklch(), so resolve each token to rgb through a canvas pixel.
  const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  const css = (name) => {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
    return `rgb(${r}, ${g}, ${b})`;
  };
  const form = $("plan"), results = $("results"), hoursEl = $("hours"), day = $("day");
  const fmtTime = (iso) => new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Kolkata" });
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const istNow = () => {
    const d = new Date(Date.now() + 5.5 * 3600e3);
    return d.toISOString().slice(0, 16);
  };
  let current = null, lastPlan = null;

  // ---------- map ----------
  const map = new maplibregl.Map({
    container: "map", style: "https://tiles.openfreemap.org/styles/positron",
    center: [77.21, 28.62], zoom: 10.4, attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
  const ready = new Promise((res) => map.on("load", res));
  ready.then(() => {
    const ink = css("--color-ink"), accent = css("--color-accent"), amber = css("--color-accent-2"), ink2 = css("--color-ink-2"), paper = css("--color-paper-3");
    map.addSource("traffic", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "traffic", type: "line", source: "traffic", layout: { visibility: "none", "line-cap": "round" },
      paint: { "line-width": 3, "line-color": ["step", ["get", "kmh"], amber, 12, ink2, 20, accent] } });
    map.addSource("route", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "route-walk", type: "line", source: "route", filter: ["==", ["get", "mode"], "walk"],
      paint: { "line-color": ink, "line-width": 2, "line-dasharray": [1, 1.5] } });
    map.addLayer({ id: "route-casing", type: "line", source: "route", filter: ["==", ["get", "mode"], "bus"],
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": paper, "line-width": 9 } });
    map.addLayer({ id: "route-bus", type: "line", source: "route", filter: ["==", ["get", "mode"], "bus"],
      layout: { "line-cap": "round", "line-join": "round" }, paint: { "line-color": ink, "line-width": 5 } });
    map.addSource("stops", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "stops", type: "circle", source: "stops",
      paint: { "circle-radius": 6, "circle-color": paper, "circle-stroke-color": ink, "circle-stroke-width": 2 } });
    map.addSource("buses", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({ id: "buses", type: "circle", source: "buses",
      paint: { "circle-radius": 4.5, "circle-color": accent, "circle-stroke-color": paper, "circle-stroke-width": 1.5 } });
  });

  // ---------- live status ----------
  async function pollLive() {
    try {
      const s = await (await fetch("/live/status")).json();
      const el = $("live");
      if (s.fresh) { el.dataset.state = "on"; el.textContent = `Live: ${s.vehicles.toLocaleString("en-IN")} buses`; }
      else { el.dataset.state = "off"; el.textContent = s.enabled ? "Live feed: warming up" : "Live feed off, typical times"; }
    } catch { $("live").textContent = "Live feed unavailable"; }
    if (lastPlan) drawBuses(lastPlan.options[current ?? 0]);
  }
  pollLive(); setInterval(pollLive, 30000);

  // ---------- accuracy link with the latest held-back result ----------
  (async () => {
    try {
      const r = await fetch("/validation");
      if (!r.ok) return;
      const rep = await r.json();
      const m = rep.estimators?.model, t = rep.estimators?.timetable;
      if (!m || !t) return;
      $("proof-figure").textContent = `±${m.mae_min.toFixed(1)} min`;
      $("proof-text").textContent = `Average error on ${rep.test_subtrips} real bus trips we held back. The timetable is off by ${t.mae_min.toFixed(1)} min. Open the accuracy report`;
    } catch { /* the link still works without the figure */ }
  })();

  // ---------- stop suggestions ----------
  for (const id of ["from", "to"]) {
    let t;
    $(id).addEventListener("input", (e) => {
      clearTimeout(t);
      const q = e.target.value.trim();
      if (q.length < 2 || /^-?\d/.test(q)) return;
      t = setTimeout(async () => {
        const list = await (await fetch(`/stops?q=${encodeURIComponent(q)}`)).json();
        $(`${id}-list`).innerHTML = list.map((s) => `<option value="${esc(s.name)}"></option>`).join("");
      }, 180);
    });
  }

  // ---------- planning ----------
  const params = () => ({ from: $("from").value.trim(), to: $("to").value.trim(), depart: $("depart").value });
  function syncUrl(p) {
    const u = new URL(location.href);
    Object.entries(p).forEach(([k, v]) => u.searchParams.set(k, v));
    history.replaceState(null, "", u);
  }

  async function plan(p, { withDay = true } = {}) {
    syncUrl(p);
    const submit = form.querySelector("[type=submit]");
    submit.setAttribute("aria-busy", "true"); submit.disabled = true;
    results.innerHTML = `<p class="summary">Timing buses from ${esc(p.from)}</p><div class="skel"></div><div class="skel"></div>`;
    try {
      const r = await fetch(`/journeys?from=${encodeURIComponent(p.from)}&to=${encodeURIComponent(p.to)}&depart=${encodeURIComponent(p.depart)}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail || "The planner could not answer.");
      lastPlan = data;
      render(data);
      if (withDay) loadDay(p);
      else markHour(p.depart);
    } catch (err) {
      results.innerHTML = `<div class="error" role="alert"><h2>No answer</h2><p>${esc(err.message)}</p><button class="btn" type="button" id="retry">Try again</button></div>`;
      $("retry").onclick = () => plan(p, { withDay });
    } finally { submit.removeAttribute("aria-busy"); submit.disabled = false; }
  }

  function render(data) {
    if (!data.options.length) {
      results.innerHTML = `<div class="empty"><h2>No bus fits</h2><p>${esc(data.message)} Try a later time, or a bigger stop nearby.</p></div>`;
      clearMap(); return;
    }
    const o0 = data.options[0];
    if ($("traffic").checked) loadTraffic();
    results.innerHTML = `<p class="summary">${esc(data.origin.label)} to ${esc(data.destination.label)}, leaving ${fmtTime(o0.depart)}</p>` +
      data.options.map((o, i) => card(o, i)).join("");
    results.querySelectorAll(".option .head").forEach((b) => b.addEventListener("click", () => select(+b.dataset.i)));
    select(0);
  }

  function card(o, i) {
    const buses = o.legs.filter((l) => l.mode === "bus").map((l) => l.route);
    if (!buses.length) {
      return `<article class="option" aria-current="${i === current}">
        <button class="head" type="button" data-i="${i}" aria-label="Show option ${i + 1} on the map">
          <span class="plate"><span class="figure">${Math.round(o.total_min)}</span><small>min</small></span>
          <span class="what"><b>Walk the whole way</b><span>Arrive ${fmtTime(o.arrive)}, no bus needed</span></span>
        </button></article>`;
    }
    const legs = o.legs.map((l) => l.mode === "walk"
      ? `<li><span class="t">${l.start ? fmtTime(l.start) : ""}</span><span>Walk ${l.minutes} min to ${esc(l.to.name)}</span></li>`
      : `<li><span class="t">${fmtTime(l.board)}</span><span>Board <span class="route">${esc(l.route)}</span> at ${esc(l.from.name)}, ride ${l.stops} stops, ${l.ride_min} min. Get off at ${esc(l.to.name)} ${fmtTime(l.alight)}.
         <br><span class="src" ${l.bus_source === "live" ? "data-live" : ""}>${l.bus_source === "live" ? "Bus is on its way now" : "Next bus from the timetable"}, ${l.wait_min} min wait</span></span></li>`).join("");
    const share = Math.round(o.observed_share * 100);
    return `<article class="option" aria-current="${i === current}">
      <button class="head" type="button" data-i="${i}" aria-label="Show option ${i + 1} on the map">
        <span class="plate"><span class="figure">${Math.round(o.total_min)}</span><small>min</small></span>
        <span class="what"><b>${buses.map(esc).join(" then ")}</b><span>Arrive ${fmtTime(o.arrive)}${o.transfers ? ", 1 change" : ", direct"}, ${o.walk_min} min walking</span></span>
      </button>
      <dl class="compare">
        <div><dt>Ride now</dt><dd>${o.ride_min} min</dd></div>
        <div><dt>Ride at ${o.quiet_hour}:00</dt><dd>${o.legs.filter((l) => l.mode === "bus").reduce((s, l) => s + l.quiet_min, 0).toFixed(1)} min</dd></div>
        <div><dt>Timetable says</dt><dd>${o.timetable_ride_min} min</dd></div>
      </dl>
      <ol class="legs">${legs}</ol>
      <p class="trust">${share}% of this ride is on stretches with observed bus data; the rest follows the city-wide pattern. Hour: ${esc(o.hour_basis)}.</p>
    </article>`;
  }

  function select(i) {
    current = i;
    results.querySelectorAll(".option").forEach((el, k) => el.setAttribute("aria-current", String(k === i)));
    draw(lastPlan.options[i]);
  }

  async function draw(o) {
    await ready;
    const feats = [], stops = [];
    const bounds = new maplibregl.LngLatBounds();
    for (const l of o.legs) {
      const coords = l.mode === "bus" ? l.path.map(([a, b]) => [b, a]) : [[l.from.lon, l.from.lat], [l.to.lon, l.to.lat]];
      coords.forEach((c) => bounds.extend(c));
      feats.push({ type: "Feature", properties: { mode: l.mode }, geometry: { type: "LineString", coordinates: coords } });
      if (l.mode === "bus") for (const s of [l.from, l.to]) stops.push({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [s.lon, s.lat] } });
    }
    map.getSource("route").setData({ type: "FeatureCollection", features: feats });
    map.getSource("stops").setData({ type: "FeatureCollection", features: stops });
    if (!bounds.isEmpty()) map.fitBounds(bounds, { padding: 60, duration: matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 400 });
    drawBuses(o);
  }

  async function drawBuses(o) {
    await ready;
    const routes = o ? o.legs.filter((l) => l.mode === "bus").map((l) => l.route_id) : [];
    const feats = [];
    for (const r of routes) {
      try {
        for (const v of await (await fetch(`/live/vehicles?route=${encodeURIComponent(r)}`)).json())
          feats.push({ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: [v.lon, v.lat] } });
      } catch { /* live layer is optional */ }
    }
    map.getSource("buses").setData({ type: "FeatureCollection", features: feats });
  }

  async function clearMap() {
    await ready;
    for (const s of ["route", "stops", "buses"]) map.getSource(s).setData({ type: "FeatureCollection", features: [] });
  }

  // ---------- signature: every hour ----------
  async function loadDay(p) {
    day.hidden = false;
    hoursEl.innerHTML = Array.from({ length: 19 }, (_, k) => `<li><button type="button" disabled><span class="h">${k + 5}</span><span class="m">..</span><span class="bar-fill"><i style="transform:scaleX(0)"></i></span></button></li>`).join("");
    try {
      const r = await fetch(`/journeys/day?from=${encodeURIComponent(p.from)}&to=${encodeURIComponent(p.to)}&date=${p.depart.slice(0, 10)}`);
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail);
      const vals = data.hours.map((h) => h.total_min).filter((v) => v != null);
      const max = Math.max(...vals, 1);
      hoursEl.innerHTML = data.hours.map((h) => `<li><button type="button" data-h="${h.hour}" ${h.total_min == null ? "disabled" : ""} aria-pressed="false"
          aria-label="${h.hour}:00, ${h.total_min == null ? "no bus" : Math.round(h.total_min) + " minutes"}">
          <span class="h">${h.hour}</span><span class="m">${h.total_min == null ? "-" : Math.round(h.total_min)}</span>
          <span class="bar-fill"><i style="transform:scaleX(${h.total_min == null ? 0 : (h.total_min / max).toFixed(3)})"></i></span></button></li>`).join("");
      hoursEl.querySelectorAll("button[data-h]").forEach((b) => b.addEventListener("click", () => {
        const hh = String(b.dataset.h).padStart(2, "0");
        $("depart").value = `${$("depart").value.slice(0, 10)}T${hh}:00`;
        plan(params(), { withDay: false });
      }));
      markHour(p.depart);
    } catch { day.hidden = true; }
  }
  function markHour(depart) {
    const h = +depart.slice(11, 13);
    hoursEl.querySelectorAll("button[data-h]").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.h === h)));
  }

  // ---------- traffic layer ----------
  async function loadTraffic() {
    await ready;
    const v = $("depart").value || istNow();
    const weekday = new Date(Date.UTC(+v.slice(0, 4), +v.slice(5, 7) - 1, +v.slice(8, 10))).getUTCDay();
    const daytype = weekday === 0 || weekday === 6 ? "weekend" : "weekday";
    try {
      map.getSource("traffic").setData(await (await fetch(`/traffic/stretches?hour=${+v.slice(11, 13)}&daytype=${daytype}`)).json());
    } catch { /* keep the previous layer */ }
  }
  $("traffic").addEventListener("change", async (e) => {
    await ready;
    const on = e.target.checked;
    $("legend").hidden = !on;
    map.setLayoutProperty("traffic", "visibility", on ? "visible" : "none");
    if (on) loadTraffic();
  });

  // ---------- wiring ----------
  form.addEventListener("submit", (e) => { e.preventDefault(); plan(params()); });
  $("now").addEventListener("click", () => { $("depart").value = istNow(); if ($("from").value && $("to").value) plan(params()); });
  $("swap").addEventListener("click", () => { const a = $("from").value; $("from").value = $("to").value; $("to").value = a; });
  $("example").addEventListener("click", () => {
    $("from").value = "Kashmere Gate"; $("to").value = "Nehru Place";
    $("depart").value = `${istNow().slice(0, 10)}T08:30`; plan(params());
  });

  const q = new URLSearchParams(location.search);
  $("depart").value = q.get("depart") || istNow();
  if (q.get("from") && q.get("to")) { $("from").value = q.get("from"); $("to").value = q.get("to"); plan(params()); }
})();
