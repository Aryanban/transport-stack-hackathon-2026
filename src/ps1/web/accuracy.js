// Accuracy page: renders /validation as figures, two scatter panels, hourly bars and tables.
(() => {
  const $ = (id) => document.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (v, d = 1) => (v == null ? "-" : Number(v).toFixed(d));
  const tip = $("tip");

  function el(name, attrs = {}, parent) {
    const n = document.createElementNS(NS, name);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    if (parent) parent.appendChild(n);
    return n;
  }
  function showTip(html, evt) {
    tip.innerHTML = html; tip.hidden = false;
    const r = tip.getBoundingClientRect();
    const x = Math.min(window.innerWidth - r.width - 8, (evt.clientX ?? 0) + 14);
    const y = Math.max(8, (evt.clientY ?? 0) - r.height - 10);
    tip.style.transform = `translate(${x}px, ${y}px)`;
    tip.style.left = "0"; tip.style.top = "0";
  }
  const hideTip = () => { tip.hidden = true; };
  function focusTip(node, html) {
    const b = node.getBoundingClientRect();
    showTip(html, { clientX: b.right, clientY: b.top });
  }
  // round axis steps (1, 2, 2.5, 5 x 10^k) so every tick is a value people say out loud
  const niceStep = (v) => {
    const raw = v / 4, p = 10 ** Math.floor(Math.log10(raw));
    return [1, 2, 2.5, 5, 10].map((k) => k * p).find((s) => s >= raw);
  };
  const niceMax = (v) => { const st = niceStep(v); return Math.ceil(v / st) * st; };
  const ticks = (max) => { const st = niceStep(max), out = []; for (let t = 0; t <= max + 1e-9; t += st) out.push(+t.toFixed(2)); return out; };

  // ---------- figures ----------
  function stats(rep) {
    const e = rep.estimators;
    const card = (key, label, lead) => {
      const m = e[key];
      return `<div class="stat ${lead ? "stat--lead" : ""}"><span class="label">${label}</span>
        <span class="figure">${fmt(m.mae_min, 2)} <small>min</small></span>
        <span class="sub">${fmt(m.mape_pct)}% off on average. ${fmt(m.within_20pct, 0)}% of trips within 20%.</span></div>`;
    };
    $("stats").innerHTML = card("model", "Our model", true) + card("timetable", "Delhi bus timetable") + card("flat", "One speed for the whole city");
  }

  // ---------- predicted vs observed ----------
  function scatter(rep) {
    const pts = rep.points || [];
    const host = $("scatter");
    if (!pts.length) { host.innerHTML = `<div class="empty"><p>No held-back trips yet. Run the validation after the logger has collected data.</p></div>`; return; }
    const max = niceMax(Math.max(...pts.flatMap((p) => [p.observed_min, p.model_min, p.timetable_min])));
    host.innerHTML = "";
    for (const [key, title, cls] of [["model_min", "Our model", "dot--model"], ["timetable_min", "Timetable", "dot--base"]]) {
      const panel = document.createElement("figure");
      panel.className = "panel"; panel.style.margin = "0";
      panel.innerHTML = `<h3>${title}</h3>`;
      const W = 420, H = 360, m = { l: 44, r: 12, t: 8, b: 40 };
      const sx = (v) => m.l + (v / max) * (W - m.l - m.r), sy = (v) => H - m.b - (v / max) * (H - m.t - m.b);
      const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${title}: predicted against observed minutes for ${pts.length} trips` }, panel);
      const g = el("g", { class: "grid" }, svg), ax = el("g", { class: "axis" }, svg);
      for (const t of ticks(max)) {
        el("line", { x1: m.l, x2: W - m.r, y1: sy(t), y2: sy(t) }, g);
        el("text", { x: m.l - 6, y: sy(t) + 4, "text-anchor": "end" }, ax).textContent = t;
        el("text", { x: sx(t), y: H - m.b + 16, "text-anchor": "middle" }, ax).textContent = t;
      }
      el("text", { x: (W + m.l) / 2, y: H - 6, "text-anchor": "middle" }, ax).textContent = "Real trip, minutes";
      el("text", { x: 12, y: (H - m.b) / 2, "text-anchor": "middle", transform: `rotate(-90 12 ${(H - m.b) / 2})` }, ax).textContent = "Predicted, minutes";
      el("line", { class: "diag", x1: sx(0), y1: sy(0), x2: sx(max), y2: sy(max) }, svg);
      for (const p of pts) {
        const cx = sx(p.observed_min), cy = sy(p[key]);
        const html = `<b>${title}</b><br>Real trip ${fmt(p.observed_min)} min<br>Predicted ${fmt(p[key])} min<br>Left at ${p.hour}:00`;
        const hit = el("circle", { class: "hit", cx, cy, r: 8 }, svg);
        const dot = el("circle", { class: `dot ${cls}`, cx, cy, r: 4 }, svg);
        hit.addEventListener("pointerenter", (e) => { dot.classList.add("on"); showTip(html, e); });
        hit.addEventListener("pointermove", (e) => showTip(html, e));
        hit.addEventListener("pointerleave", () => { dot.classList.remove("on"); hideTip(); });
      }
      host.appendChild(panel);
    }
  }

  // ---------- by hour ----------
  function hours(rep) {
    const rows = rep.by_hour || [];
    const tbody = $("hour-table").querySelector("tbody");
    tbody.innerHTML = rows.map((r) => `<tr><td>${r.hour}:00</td><td class="num">${r.n}</td><td class="num">${fmt(r.model_mae_min, 2)}</td><td class="num">${fmt(r.timetable_mae_min, 2)}</td></tr>`).join("");
    if (!rows.length) { $("hours").innerHTML = `<div class="empty"><p>No hours yet.</p></div>`; return; }
    if (rows.length < 6) $("hour-note").textContent = `Only ${rows.length === 1 ? "one hour has" : rows.length + " hours have"} held-back trips so far. More bars appear as the logger covers the day.`;
    const W = 900, H = 260, m = { l: 44, r: 8, t: 18, b: 32 };
    const max = niceMax(Math.max(...rows.flatMap((r) => [r.model_mae_min, r.timetable_mae_min])));
    const band = (W - m.l - m.r) / 24, bw = Math.min(14, band / 2 - 3);
    const sy = (v) => H - m.b - (v / max) * (H - m.t - m.b);
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Average error in minutes by hour, model against timetable" });
    const g = el("g", { class: "grid" }, svg), ax = el("g", { class: "axis" }, svg);
    for (const t of ticks(max)) {
      el("line", { x1: m.l, x2: W - m.r, y1: sy(t), y2: sy(t) }, g);
      el("text", { x: m.l - 6, y: sy(t) + 4, "text-anchor": "end" }, ax).textContent = t;
    }
    for (let h = 0; h < 24; h += 3) el("text", { x: m.l + band * (h + 0.5), y: H - m.b + 18, "text-anchor": "middle" }, ax).textContent = `${h}:00`;
    const bar = (x, v, cls, label) => {
      const y = sy(v), h = Math.max(1, H - m.b - y), r = Math.min(4, h, bw / 2);
      // rounded data end, square at the baseline
      el("path", { class: cls, d: `M${x},${H - m.b} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${H - m.b} Z` }, svg);
      const hit = el("rect", { class: "hit", x: x - 2, y: m.t, width: bw + 4, height: H - m.t - m.b, tabindex: 0, role: "img", "aria-label": label }, svg);
      hit.addEventListener("pointerenter", (e) => showTip(label, e));
      hit.addEventListener("pointermove", (e) => showTip(label, e));
      hit.addEventListener("pointerleave", hideTip);
      hit.addEventListener("focus", () => focusTip(hit, label));
      hit.addEventListener("blur", hideTip);
    };
    for (const r of rows) {
      const x0 = m.l + band * r.hour + band / 2 - bw - 1;
      bar(x0, r.model_mae_min, "barm--model", `${r.hour}:00, our model: ${fmt(r.model_mae_min, 2)} min average error, ${r.n} trips`);
      bar(x0 + bw + 2, r.timetable_mae_min, "barm--base", `${r.hour}:00, timetable: ${fmt(r.timetable_mae_min, 2)} min average error, ${r.n} trips`);
    }
    $("hours").replaceChildren(svg);
  }

  // ---------- Google ----------
  function google(rep) {
    const g = rep.google || {};
    if (!g.pairs) {
      $("google").innerHTML = `<div class="empty"><p>Not checked yet. Copy <code>data/ps1/google_benchmark_template.csv</code> to <code>data/ps1/google_benchmark.csv</code>, fill in the bus-only time Google Maps shows for each trip, then run <code>python -m src.ps1.validation</code>.</p></div>`;
      return;
    }
    const head = g.n ? `<p class="note">${g.n} trips. Our door-to-door time is ${fmt(g.mae_min)} min from Google's on average, ${fmt(g.mape_pct)}% off, with ${fmt(g.within_20pct, 0)}% within 20%.</p>` : "";
    $("google").innerHTML = head + `<table><thead><tr><th scope="col">From</th><th scope="col">To</th><th scope="col">Leave</th><th scope="col" class="num">Google, min</th><th scope="col" class="num">Ours, min</th></tr></thead><tbody>` +
      g.pairs.map((p) => `<tr><td>${esc(p.origin)}</td><td>${esc(p.destination)}</td><td>${esc(p.depart.replace("T", " "))}</td><td class="num">${fmt(p.google_min)}</td><td class="num">${fmt(p.ours_min)}</td></tr>`).join("") + `</tbody></table>`;
  }

  // ---------- coverage ----------
  function facts(rep) {
    const c = rep.coverage || {};
    const t = (s) => (s ? s.replace("T", " ").slice(0, 16) : "-");
    const items = [
      ...(c.sources || []).map((s) => [s.source === "archive" ? "Organisers' GPS archive" : "Our live GTFS-RT log",
        `${s.first_day} to ${s.last_day}, ${s.days} days, ${s.observations.toLocaleString("en-IN")} stretch observations`]),
      ["Days of bus GPS", (rep.days_logged || []).length],
      ["Stretch observations", (c.observations ?? 0).toLocaleString("en-IN")],
      ["Buses seen", (c.vehicles ?? 0).toLocaleString("en-IN")],
      ["Routes seen", `${c.routes ?? 0} of ${c.routes_total ?? 0}`],
      ["Stretches with 3+ trips", `${(c.stretches_3plus ?? 0).toLocaleString("en-IN")} of ${(c.stretches ?? 0).toLocaleString("en-IN")}`],
      ["Hours with their own data", (c.hours_with_data || []).map((h) => `${h}:00`).join(", ") || "none yet"],
      ["Held-back trips", rep.test_subtrips],
    ];
    $("facts").innerHTML = items.map(([k, v]) => `<div><dt>${k}</dt><dd>${esc(v)}</dd></div>`).join("");
    $("split").textContent = `Held back from training: ${rep.split}. Report made ${t(rep.generated)}.`;
  }

  async function load() {
    try {
      const r = await fetch("/validation");
      if (!r.ok) throw new Error((await r.json()).detail || "No report yet.");
      const rep = await r.json();
      const m = rep.estimators.model, tt = rep.estimators.timetable;
      $("lead").textContent = rep.test_subtrips
        ? `Checked on ${rep.test_subtrips} real bus trips kept out of training. Our model is off by ${fmt(m.mae_min, 2)} minutes on average, the timetable by ${fmt(tt.mae_min, 2)}.`
        : "No held-back trips yet.";
      stats(rep); scatter(rep); hours(rep); google(rep); facts(rep);
    } catch (err) {
      $("lead").textContent = "";
      $("stats").outerHTML = `<div class="error" role="alert"><p>${esc(err.message)} Build it with <code>python -m src.ps1.validation</code>, then reload.</p></div>`;
    } finally { $("page").setAttribute("aria-busy", "false"); }
  }
  load();
})();
