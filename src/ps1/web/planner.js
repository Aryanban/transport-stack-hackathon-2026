"use strict";
// Planner screen on the 3D map. Times come from /journeys (GPS-learned model + live layer).
// Plain JS, no build step. The trip lives in the URL so it can be shared.

const byId = (id) => document.getElementById(id);
const form = byId("planner");
const statusEl = byId("status");
const optionsEl = byId("options");
const chosen = {}; // field id -> "stop_id" or "lat,lon" picked from a suggestion or the map
const clock = (iso) => new Date(iso).toLocaleTimeString("en-IN",
  { hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZone: "Asia/Kolkata" });
const istNow = () => new Date(Date.now() + 5.5 * 3600e3).toISOString().slice(0, 16);
const reduced = matchMedia("(prefers-reduced-motion: reduce)");

const transitMap = typeof TransitMapEngine !== "undefined" ? new TransitMapEngine("map-container") : null;
window.transitMap = transitMap; // buses3d.js (a module) attaches its 3D layer to it
let lastPlan = null;

async function getJSON(path, params, signal) {
  const q = params ? "?" + new URLSearchParams(params) : "";
  const r = await fetch(path + q, { signal });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof data.detail === "string" ? data.detail : "The planner could not answer. Try again.");
  return data;
}

function el(tag, text, className) {
  const n = document.createElement(tag);
  if (text !== undefined && text !== null) n.textContent = text;
  if (className) n.className = className;
  return n;
}

// ---------- live status ----------
async function pollLive() {
  const live = byId("live");
  clearTimeout(pollLive.timer);
  pollLive.timer = setTimeout(pollLive, live.dataset.state === "on" ? 30000 : 8000);
  try {
    const s = await getJSON("/live/status");
    if (s.fresh) {
      live.dataset.state = "on";
      live.textContent = `Live: ${s.vehicles.toLocaleString("en-IN")} buses reporting`;
    } else {
      live.dataset.state = "off";
      live.textContent = s.enabled ? "Live feed warming up, typical times for now" : "Live feed off, typical times for the hour";
    }
  } catch { live.dataset.state = "off"; live.textContent = "Live feed unavailable"; }
}
pollLive();

// ---------- accuracy figure ----------
getJSON("/validation").then((rep) => {
  const m = rep.estimators?.model, t = rep.estimators?.timetable;
  if (!m || !t) return;
  byId("proof-figure").textContent = `±${m.mae_min.toFixed(1)} min`;
  byId("proof-text").textContent = `Average error on ${rep.test_subtrips.toLocaleString("en-IN")} real bus trips we held back. `
    + `The timetable is off by ${t.mae_min.toFixed(1)} min. See the report`;
}).catch(() => { /* the link works without the figure */ });

// ---------- stop search ----------
function bindStop(id) {
  const field = byId(id);
  const list = byId(id + "-results");
  let timer, controller, found = [], active = -1;

  const hide = () => {
    clearTimeout(timer); controller?.abort();
    list.hidden = true; active = -1;
    field.setAttribute("aria-expanded", "false");
    field.removeAttribute("aria-activedescendant");
  };
  const choose = (stop) => { chosen[id] = stop.id; field.value = stop.name; hide(); };

  field.addEventListener("input", () => {
    delete chosen[id];
    hide();
    const term = field.value.trim();
    if (term.length < 2 || /^-?\d+(\.\d+)?\s*,/.test(term)) return;
    timer = setTimeout(async () => {
      controller = new AbortController();
      try {
        found = await getJSON("/stops", { q: term }, controller.signal);
        if (document.activeElement !== field) return;
        list.replaceChildren();
        if (!found.length) list.append(el("p", "No stop by that name. Try part of it, or lat,lon."));
        const seen = new Map();
        found.forEach(({ name }) => seen.set(name, (seen.get(name) || 0) + 1));
        found.forEach((stop, i) => {
          const b = el("button", seen.get(stop.name) > 1 ? `${stop.name} (stop ${stop.id})` : stop.name);
          if (stop.routes) b.append(el("small", `${stop.routes} route${stop.routes === 1 ? "" : "s"}`, "sugg-meta"));
          b.type = "button"; b.tabIndex = -1; b.id = `${id}-opt-${i}`;
          b.setAttribute("role", "option"); b.setAttribute("aria-selected", "false");
          b.addEventListener("pointerdown", (e) => e.preventDefault());
          b.addEventListener("click", () => choose(stop));
          list.append(b);
        });
        list.hidden = false;
        field.setAttribute("aria-expanded", "true");
      } catch (err) { if (err.name !== "AbortError") statusEl.textContent = err.message; }
    }, 160);
  });
  field.addEventListener("blur", hide);
  field.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "Escape") return hide();
    if (!found.length) return;
    if (e.key === "Enter" && active >= 0) { e.preventDefault(); return choose(found[active]); }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    active = (active + (e.key === "ArrowDown" ? 1 : -1) + found.length) % found.length;
    [...list.children].forEach((o, i) => o.setAttribute("aria-selected", String(i === active)));
    field.setAttribute("aria-activedescendant", list.children[active].id);
    list.children[active].scrollIntoView({ block: "nearest" });
  });
}
bindStop("origin");
bindStop("destination");

// Map popups ("Directions from / to") hand over a place with its coordinates.
window.setPlannerStop = (field, name, coords) => {
  byId(field).value = name;
  if (coords) chosen[field] = `${coords[1].toFixed(6)},${coords[0].toFixed(6)}`;
  if (byId("origin").value && byId("destination").value) plan();
};

const place = (id) => chosen[id] || byId(id).value.trim();

// ---------- planning ----------
function syncUrl(p) {
  const u = new URL(location.href);
  u.searchParams.set("from", p.from); u.searchParams.set("to", p.to); u.searchParams.set("depart", p.depart);
  if (byId("origin").value !== p.from) u.searchParams.set("from_label", byId("origin").value); else u.searchParams.delete("from_label");
  if (byId("destination").value !== p.to) u.searchParams.set("to_label", byId("destination").value); else u.searchParams.delete("to_label");
  history.replaceState(null, "", u);
}

async function plan(event, { withDay = true } = {}) {
  event?.preventDefault();
  const submit = form.querySelector("[type=submit]");
  if (submit.disabled) return;
  const p = { from: place("origin"), to: place("destination"), depart: byId("departure").value || istNow() };
  if (!p.from || !p.to) { statusEl.textContent = "Enter where you start and where you are going."; return; }
  syncUrl(p);
  submit.disabled = true; submit.setAttribute("aria-busy", "true");
  statusEl.textContent = "Timing the buses";
  optionsEl.replaceChildren(el("div", null, "skel"), el("div", null, "skel"));
  const ticket = plan.ticket = (plan.ticket || 0) + 1;
  try {
    const data = await getJSON("/journeys", p);
    if (ticket !== plan.ticket) return;
    lastPlan = data;
    render(data);
    if (withDay) loadDay(p); else markHour(p.depart);
    if (byId("btn-toggle-speeds").getAttribute("aria-pressed") === "true") loadSpeeds();
  } catch (err) {
    statusEl.textContent = err.message;
    optionsEl.replaceChildren();
    transitMap?.clearJourney();
  } finally { submit.disabled = false; submit.removeAttribute("aria-busy"); }
}
form.addEventListener("submit", plan);

function render(data) {
  if (!data.options.length) {
    statusEl.textContent = `${data.message || "No bus fits."} Try a later time, or a bigger stop nearby.`;
    optionsEl.replaceChildren();
    transitMap?.clearJourney();
    return;
  }
  statusEl.textContent = `${data.origin.label} to ${data.destination.label}, leaving ${clock(data.depart)}`;
  byId("source").textContent = data.options.some((o) => o.legs.some((l) => l.bus_source === "live"))
    ? "Times from bus GPS, with live buses" : "Times from bus GPS";
  optionsEl.replaceChildren(...data.options.map((o, i) => {
    const c = card(o, i, data);
    c.style.setProperty("--i", i); // stagger the entrance
    return c;
  }));
  select(0);
}

const busSvg = '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>';
const walkSvg = '<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true"><path d="M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7"/></svg>';

function badge(leg) {
  const b = el("span", null, "route-badge " + leg.mode);
  b.innerHTML = leg.mode === "bus" ? busSvg : walkSvg;
  b.append(el("span", leg.mode === "bus" ? leg.route : `${Math.round(leg.minutes)} min`));
  return b;
}

// One line for a collapsed card: which bus, where, and where to change.
function summaryLine(o) {
  const buses = o.legs.filter((l) => l.mode === "bus");
  if (!buses.length) return `Walk the whole way, ${Math.round(o.total_min)} min.`;
  const [a, b] = buses;
  let text = `Board ${a.route} at ${a.from.name}, ${clock(a.board)}.`;
  if (b) text += ` Change at ${a.to.name} to ${b.route}.`;
  return text;
}

function step(kind, time, title, lines = []) {
  const li = el("li", null, "it-step " + kind);
  li.append(el("span", time || "", "it-time"), el("span", null, "it-node"));
  const body = el("div", null, "it-body");
  if (title instanceof Node) body.append(title); else body.append(el("p", title, "it-title"));
  for (const line of lines) if (line) body.append(line instanceof Node ? line : el("p", line, "it-line"));
  li.append(body);
  return li;
}

// Step-by-step directions: where to walk, which bus and which way, when it comes, where to get off.
function itinerary(o, origin, destination) {
  const ol = el("ol", null, "itinerary");
  ol.setAttribute("aria-label", "Directions");
  const legs = o.legs;
  ol.append(step("start", clock(o.depart), `Leave ${origin}`));
  legs.forEach((l, k) => {
    const prevBus = legs.slice(0, k).some((x) => x.mode === "bus");
    if (l.mode === "walk") {
      const mins = Math.max(1, Math.round(l.minutes));
      const nextBus = legs.slice(k + 1).find((x) => x.mode === "bus");
      const title = k === legs.length - 1 ? `Walk ${mins} min to ${destination}`
        : prevBus && nextBus ? `Change buses: walk ${mins} min to ${l.to.name}`
        : `Walk ${mins} min to ${l.to.name}`;
      ol.append(step("walk", l.start ? clock(l.start) : "", title));
      return;
    }
    if (prevBus && legs[k - 1].mode === "bus") ol.append(step("walk", "", `Change buses at ${l.from.name}`));
    const head = el("div", null, "it-bus-head");
    const badgeEl = badge(l);
    badgeEl.classList.add("big");
    head.append(badgeEl, el("span", `towards ${l.towards || l.headsign}`, "it-towards"));
    const wait = Math.round(l.wait_min);
    const due = l.bus_source === "live"
      ? `A tracked bus reaches the stop at ${clock(l.board)}${wait ? `, ${wait} min wait` : ""}.`
      : `Next bus due ${clock(l.board)} by the timetable${wait ? `, ${wait} min wait` : ""}.`;
    const between = (l.stop_points || []).slice(1, -1);
    let list = null;
    if (between.length) {
      list = el("details", null, "it-stops");
      list.append(el("summary", `${between.length} stop${between.length === 1 ? "" : "s"} in between`));
      const names = el("ol", null, "it-stop-list");
      between.forEach((sp) => names.append(el("li", sp.name)));
      list.append(names);
    }
    ol.append(step("bus", clock(l.board), head, [
      `Board at ${l.from.name}. ${due}`,
      `Ride ${l.stops} stop${l.stops === 1 ? "" : "s"}, about ${Math.round(l.ride_min)} min.`,
      list,
    ]));
    const last = k === legs.length - 1;
    ol.append(step(last ? "end" : "alight", clock(l.alight), last ? `Get off at ${l.to.name}. You have arrived.` : `Get off at ${l.to.name}`));
  });
  if (legs[legs.length - 1].mode === "walk") ol.append(step("end", clock(o.arrive), `Arrive at ${destination}`));
  return ol;
}

function card(o, i, data) {
  const buses = o.legs.filter((l) => l.mode === "bus");
  const article = el("article", null, "transit-card");
  article.tabIndex = 0;
  article.setAttribute("role", "button");
  article.setAttribute("aria-pressed", "false");
  article.setAttribute("aria-label", `Option ${i + 1}: ${Math.round(o.total_min)} minutes, arrive ${clock(o.arrive)}. ${summaryLine(o)}`);

  const top = el("div", null, "transit-card-top");
  const row = el("div", null, "badge-row");
  o.legs.forEach((l, k) => { if (k) row.append(el("span", "›", "leg-sep")); row.append(badge(l)); });
  top.append(row);
  const firstBus = buses[0];
  if (firstBus) {
    const live = firstBus.bus_source === "live";
    top.append(el("span", live ? "Bus on its way now" : "Timetable departure", "source-pill" + (live ? " live" : "")));
  }

  const main = el("div", null, "transit-card-main");
  const dur = el("div", null, "duration-box");
  dur.append(el("span", `${Math.round(o.total_min)} min`, "duration-text"));
  const changes = !buses.length ? "no bus needed" : o.transfers ? `${o.transfers} change${o.transfers > 1 ? "s" : ""}` : "direct";
  main.append(dur, el("span", `${clock(o.depart)} to ${clock(o.arrive)}, ${changes}`, "time-window"));
  article.append(top, main, el("p", summaryLine(o), "card-summary"));

  const open = el("div", null, "card-open");
  open.append(itinerary(o, data.origin.label, data.destination.label));
  if (buses.length) {
    const dl = el("dl", null, "compare");
    for (const [dt, dd] of [["On the bus, our estimate", `${Math.round(o.ride_min)} min`], ["Timetable says", `${Math.round(o.timetable_ride_min)} min`]]) {
      const d = el("div"); d.append(el("dt", dt), el("dd", dd)); dl.append(d);
    }
    open.append(dl, el("p", `${Math.round(o.observed_share * 100)}% of this ride is on stretches where we have logged real buses. `
      + "The rest follows the city-wide pattern." + (o.hour_basis ? ` ${o.hour_basis[0].toUpperCase()}${o.hour_basis.slice(1)}.` : ""), "trust"));
  }
  article.append(open);

  const pick = (e) => { if (e.target.closest("summary, .it-stops")) return; select(i); };
  article.addEventListener("click", pick);
  article.addEventListener("keydown", (e) => {
    if (e.target !== article) return; // keys inside the stop list stay there
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(i); }
  });
  return article;
}

const km = (pts) => pts.reduce((s, p, k) => {
  if (!k) return 0;
  const q = pts[k - 1], r = Math.PI / 180;
  const a = Math.sin((p.lat - q.lat) * r / 2) ** 2 + Math.cos(q.lat * r) * Math.cos(p.lat * r) * Math.sin((p.lon - q.lon) * r / 2) ** 2;
  return s + 12742 * Math.asin(Math.sqrt(a));
}, 0);

function toMapJourney(o) {
  const legs = o.legs.map((l) => ({
    mode: l.mode,
    points: l.mode === "bus" ? l.path.map(([lat, lon]) => ({ lat, lon })) : [l.from, l.to].map(({ lat, lon }) => ({ lat, lon })),
    stops: l.mode === "bus" ? (l.stop_points || [l.from, l.to]) : [],
  }));
  const firstBus = o.legs.find((l) => l.mode === "bus");
  const later = o.legs.filter((l) => l.mode === "bus").slice(1).map((l) => l.route);
  const buses = o.legs.filter((l) => l.mode === "bus");
  const keyStops = buses.flatMap((l, k) => {
    const pins = [{ ...l.from, kind: k ? "change" : "board", label: k ? `Change to ${l.route}` : `Board ${l.route}` }];
    if (k === buses.length - 1) pins.push({ ...l.to, kind: "alight", label: "Get off" });
    return pins;
  });
  return {
    legs, minutes: o.total_min, arrival: o.arrive, keyStops,
    banner: firstBus
      ? { title: `Board ${firstBus.route} at ${firstBus.from.name}, ${clock(firstBus.board)}`,
          sub: (later.length ? `Then ${later.join(", ")}. ` : "") + "The moving bus is a preview, not a live position" }
      : { title: `Walk ${Math.round(o.total_min)} min`, sub: "No bus needed for this trip" },
    km: legs.reduce((s, l) => s + km(l.points), 0),
    badge: !firstBus ? "Walk" : firstBus.bus_source === "live" ? "Tracked bus on its way" : "Timetable departure",
  };
}

function select(i) {
  [...optionsEl.children].forEach((c, k) => {
    c.classList.toggle("selected", k === i);
    c.setAttribute("aria-pressed", String(k === i));
  });
  transitMap?.setJourney(toMapJourney(lastPlan.options[i]));
}

// ---------- same trip, every hour ----------
async function loadDay(p) {
  const day = byId("day"), hours = byId("hours");
  const ticket = loadDay.ticket = (loadDay.ticket || 0) + 1; // a newer plan wins over a slower old answer
  day.hidden = false;
  hours.replaceChildren();
  try {
    const data = await getJSON("/journeys/day", { from: p.from, to: p.to, date: p.depart.slice(0, 10) });
    if (ticket !== loadDay.ticket) return;
    const max = Math.max(1, ...data.hours.map((h) => h.total_min ?? 0));
    for (const h of data.hours) {
      const li = el("li");
      const b = el("button");
      b.type = "button";
      b.dataset.h = h.hour;
      b.disabled = h.total_min == null;
      b.setAttribute("aria-pressed", "false");
      b.setAttribute("aria-label", `${h.hour}:00, ${h.total_min == null ? "no bus" : Math.round(h.total_min) + " minutes"}`);
      const bar = el("span", null, "bar");
      const fill = el("i");
      fill.style.transform = `scaleY(${h.total_min == null ? 0 : (h.total_min / max).toFixed(3)})`;
      bar.append(fill);
      b.append(bar, el("span", h.total_min == null ? "-" : String(Math.round(h.total_min)), "m"), el("span", String(h.hour), "h"));
      b.addEventListener("click", () => {
        byId("departure").value = `${byId("departure").value.slice(0, 10) || istNow().slice(0, 10)}T${String(h.hour).padStart(2, "0")}:00`;
        plan(null, { withDay: false });
      });
      li.append(b);
      hours.append(li);
    }
    markHour(p.depart);
  } catch { if (ticket === loadDay.ticket) day.hidden = true; }
}
function markHour(depart) {
  const h = +depart.slice(11, 13);
  byId("hours").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(+b.dataset.h === h)));
}

// ---------- map controls ----------
function pressed(btn, on) { btn.classList.toggle("active", on); btn.setAttribute("aria-pressed", String(on)); }

byId("btn-toggle-3d").addEventListener("click", (e) => transitMap && pressed(e.currentTarget, transitMap.toggle3D()));
byId("btn-follow-vehicle").addEventListener("click", (e) => transitMap && pressed(e.currentTarget, transitMap.toggleFollow()));
byId("btn-toggle-live-fleet").addEventListener("click", async (e) => {
  if (!transitMap) return;
  const btn = e.currentTarget;
  const on = await transitMap.toggleLiveFleet();
  pressed(btn, on);
  byId("fleet-live-pill").hidden = !on;
});
async function loadSpeeds() {
  const v = byId("departure").value || istNow();
  const wd = new Date(Date.UTC(+v.slice(0, 4), +v.slice(5, 7) - 1, +v.slice(8, 10))).getUTCDay();
  try {
    transitMap?.setSpeeds(await getJSON("/traffic/stretches", { hour: +v.slice(11, 13), daytype: wd === 0 || wd === 6 ? "weekend" : "weekday" }));
  } catch { /* keep the previous layer */ }
}
byId("btn-toggle-speeds").addEventListener("click", (e) => {
  const on = e.currentTarget.getAttribute("aria-pressed") !== "true";
  pressed(e.currentTarget, on);
  byId("speed-legend").hidden = !on;
  if (on) loadSpeeds(); else transitMap?.setSpeeds(null);
});
byId("btn-recenter").addEventListener("click", () => transitMap?.recenter());
byId("btn-cancel-route").addEventListener("click", () => {
  transitMap?.clearJourney();
  [...optionsEl.children].forEach((c) => { c.classList.remove("selected"); c.setAttribute("aria-pressed", "false"); });
});
const previewToggle = byId("hud-sound-toggle");
previewToggle.addEventListener("click", () => {
  if (!transitMap || reduced.matches) return;
  transitMap.previewPaused = !transitMap.previewPaused;
  const label = transitMap.previewPaused ? "Resume route preview" : "Pause route preview";
  previewToggle.setAttribute("aria-label", label);
  previewToggle.setAttribute("aria-pressed", String(transitMap.previewPaused));
  previewToggle.querySelector("path").setAttribute("d", transitMap.previewPaused ? "M8 5v14l11-7z" : "M6 5h4v14H6zm8 0h4v14h-4z");
});

byId("btn-swap-stops").addEventListener("click", () => {
  const o = byId("origin"), d = byId("destination");
  [o.value, d.value] = [d.value, o.value];
  [chosen.origin, chosen.destination] = [chosen.destination, chosen.origin];
  for (const k of ["origin", "destination"]) if (!chosen[k]) delete chosen[k];
  if (o.value && d.value) plan();
});

document.querySelectorAll(".time-chip").forEach((chip) => chip.addEventListener("click", () => {
  document.querySelectorAll(".time-chip").forEach((c) => c.classList.toggle("active-time", c === chip));
  const now = istNow();
  const date = byId("departure").value.slice(0, 10) || now.slice(0, 10);
  byId("departure").value = chip.dataset.time === "now" ? now : `${date}T${chip.dataset.time}`;
  if (byId("origin").value && byId("destination").value) plan();
}));

// ---------- start ----------
const q = new URLSearchParams(location.search);
byId("departure").value = q.get("depart") || istNow();
if (q.get("from") && q.get("to")) {
  for (const [field, key] of [["origin", "from"], ["destination", "to"]]) {
    byId(field).value = q.get(`${key}_label`) || q.get(key);
    if (q.get(`${key}_label`)) chosen[field] = q.get(key);
  }
} else {
  byId("origin").value = "Kashmere Gate";
  byId("destination").value = "Nehru Place";
}
plan();
