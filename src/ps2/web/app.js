"use strict";

const byId = (id) => document.getElementById(id);
const form = byId("planner");
const statusEl = byId("status");
const stopIds = {};
const timeFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const clock = (value) => timeFormat.format(new Date(value));

// 1. Initialize MapLibre GL 3D Transit Engine
const transitMap = typeof TransitMapEngine !== "undefined" ? new TransitMapEngine("map-container") : null;
window.transitMap = transitMap;

let currentActiveOption = null;

async function request(path, params, signal) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  const response = await fetch(path.replace(/^\//, "") + query, { signal });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(typeof data.detail === "string" ? data.detail : "Check your entries and try again.");
  }
  return data;
}

function node(tag, content, className) {
  const item = document.createElement(tag);
  if (content !== undefined) item.textContent = content;
  if (className) item.className = className;
  return item;
}

// 2. Stop Autocomplete Controller
function bindStop(id) {
  const field = byId(id);
  const list = byId(id + "-results");
  let timer;
  let controller;
  let suggestions = [];
  let selected = -1;

  function hide() {
    clearTimeout(timer);
    controller?.abort();
    list.hidden = true;
    field.setAttribute("aria-expanded", "false");
    field.removeAttribute("aria-activedescendant");
    selected = -1;
  }

  function choose(stop) {
    stopIds[id] = stop.id;
    field.value = stop.name;
    hide();
  }

  field.addEventListener("input", () => {
    delete stopIds[id];
    hide();
    const term = field.value.trim();
    if (!term) return;

    timer = setTimeout(async () => {
      controller = new AbortController();
      const signal = controller.signal;
      try {
        const found = await request("/api/stops", { q: term }, signal);
        if (signal.aborted || document.activeElement !== field) return;
        suggestions = found;
        list.replaceChildren();
        if (!suggestions.length) {
          list.append(node("p", "No matching stops."));
        }
        const counts = new Map();
        suggestions.forEach(({ name }) => counts.set(name, (counts.get(name) || 0) + 1));
        suggestions.forEach((stop, index) => {
          const name = counts.get(stop.name) > 1 ? stop.name + " · " + stop.id : stop.name;
          const button = node("button", name);
          button.type = "button";
          button.tabIndex = -1;
          button.id = id + "-suggestion-" + index;
          button.setAttribute("role", "option");
          button.setAttribute("aria-selected", "false");
          button.addEventListener("pointerdown", (event) => event.preventDefault());
          button.addEventListener("click", () => choose(stop));
          list.append(button);
        });
        list.hidden = false;
        field.setAttribute("aria-expanded", "true");
      } catch (error) {
        if (!signal.aborted && statusEl) statusEl.textContent = error.message;
      }
    }, 160);
  });

  field.addEventListener("blur", hide);
  field.addEventListener("keydown", (event) => {
    if (list.hidden) return;
    if (event.key === "Escape") {
      hide();
      return;
    }
    if (!suggestions.length) return;
    if (event.key === "Enter" && selected >= 0) {
      event.preventDefault();
      choose(suggestions[selected]);
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const direction = event.key === "ArrowDown" ? 1 : -1;
    selected = selected < 0 && direction < 0
      ? suggestions.length - 1
      : (selected + direction + suggestions.length) % suggestions.length;
    [...list.children].forEach((option, index) => option.setAttribute("aria-selected", String(index === selected)));
    const option = list.children[selected];
    field.setAttribute("aria-activedescendant", option.id);
    option.scrollIntoView({ block: "nearest" });
  });

  return choose;
}

const chooseOrigin = bindStop("origin");
const chooseDestination = bindStop("destination");

window.setPlannerStop = async (fieldId, stopName) => {
  try {
    const hits = await request("/api/stops", { q: stopName });
    if (hits && hits.length) {
      if (fieldId === "origin") chooseOrigin(hits[0]);
      else chooseDestination(hits[0]);
      if (stopIds.origin && stopIds.destination) {
        await plan();
      }
    }
  } catch (e) {
    console.warn("Could not set stop from popup:", e);
  }
};

// 3. Crowding Status Pill Generator (Google Maps Style)
function makeCrowdBadge(level) {
  const container = document.createElement("span");
  container.className = "crowd-pill";
  const dot = document.createElement("span");
  dot.className = "dot";
  container.appendChild(dot);

  const textNode = document.createElement("span");
  if (level === "Seats available") {
    container.classList.add("low");
    textNode.textContent = "Seats available";
  } else if (level === "Standing room") {
    container.classList.add("moderate");
    textNode.textContent = "Standing room";
  } else if (level === "Heavily crowded") {
    container.classList.add("high");
    textNode.textContent = "Crowded";
  } else {
    textNode.textContent = "Normal load";
  }
  container.appendChild(textNode);
  return container;
}

// 4. Update Visualizers & Floating HUD Navigation Banner
function updateVisualizers(option) {
  currentActiveOption = option;
  if (transitMap) {
    transitMap.setJourney(option);
  }

  const navBanner = byId("hud-nav-banner");
  if (navBanner && option && option.legs && option.legs.length) {
    const firstLeg = option.legs[0];
    const points = firstLeg.points || [];
    const nextStopName = points.length > 1 ? points[1].name : firstLeg.to.name;
    const isMetro = String(firstLeg.route).toLowerCase().includes("line") || String(firstLeg.route).toLowerCase().includes("metro");
    const routePrefix = isMetro ? "Metro " : "Bus ";

    const hudNext = byId("hud-next-stop");
    const hudSub = byId("hud-subtext");
    if (hudNext) hudNext.textContent = "Next: " + nextStopName;
    if (hudSub) hudSub.textContent = routePrefix + firstLeg.route + " · " + Math.round(option.minutes) + " min duration";
    navBanner.hidden = false;
  } else if (navBanner) {
    navBanner.hidden = true;
  }
}

// 5. Google Maps / Apple Maps Style Transit Option Card
function journeyCard(option, isFirst = false) {
  const card = document.createElement("article");
  card.className = "transit-card" + (isFirst ? " selected" : "");
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-pressed", String(isFirst));

  // Top Row: Badges & Crowding Level
  const top = document.createElement("div");
  top.className = "transit-card-top";

  const badgeRow = document.createElement("div");
  badgeRow.className = "badge-row";

  // Build badges for each leg
  option.legs.forEach((leg, i) => {
    if (i > 0) {
      const arrow = document.createElement("span");
      arrow.textContent = "›";
      arrow.style.color = "var(--g-subtext)";
      arrow.style.fontWeight = "bold";
      badgeRow.appendChild(arrow);
    }
    const badge = document.createElement("span");
    const isMetro = String(leg.route).toLowerCase().includes("line");
    badge.className = "route-badge " + (isMetro ? "metro" : "bus");

    // Clean SVG icon for bus or metro
    const svgIcon = isMetro
      ? `<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M12 2c-4.42 0-8 .5-8 4v10c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4zm0 2c3.5 0 6 .4 6 2v2H6V6c0-1.6 2.5-2 6-2zm-5 13c-.83 0-1.5-.67-1.5-1.5S6.17 14 7 14s1.5.67 1.5 1.5S7.83 17 7 17zm10 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5z"/></svg>`
      : `<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/></svg>`;

    badge.innerHTML = `${svgIcon}<span>${leg.route}</span>`;
    badgeRow.appendChild(badge);
  });

  // Estimated Transit Fare Pill (DTC & DMRC Tariff Ground Truth)
  const isMulti = (option.transfers || 0) > 0;
  const farePill = document.createElement("span");
  farePill.className = "fare-pill";
  farePill.textContent = isMulti ? "₹25 Fare" : "₹15 AC";
  badgeRow.appendChild(farePill);

  top.appendChild(badgeRow);
  top.appendChild(makeCrowdBadge(option.crowd?.level));

  // Main Row: Large Duration & Time Range
  const main = document.createElement("div");
  main.className = "transit-card-main";

  const duration = document.createElement("span");
  duration.className = "duration-text";
  duration.textContent = Math.round(option.minutes) + " min";

  const timeWindow = document.createElement("span");
  timeWindow.className = "time-window";
  const transferText = option.transfers ? option.transfers + " transfer" : "Direct";
  timeWindow.textContent = clock(option.departure) + " – " + clock(option.arrival) + " · " + transferText;

  main.appendChild(duration);
  main.appendChild(timeWindow);

  // Collapsible Legs Details
  const details = document.createElement("details");
  details.className = "transit-card-details";
  const summary = document.createElement("summary");
  summary.textContent = "Route details and stops";
  details.appendChild(summary);

  const legsContainer = document.createElement("div");
  legsContainer.style.paddingTop = "4px";

  option.legs.forEach((leg, legIdx) => {
    const isLastLeg = legIdx === option.legs.length - 1;
    const track = document.createElement("div");
    track.className = "timeline-track";

    // Boarding Stop Node
    const startStep = document.createElement("div");
    startStep.className = "timeline-step";
    startStep.innerHTML = `
      <div class="timeline-node origin"></div>
      <div class="timeline-content">
        <div class="timeline-stop-name">${leg.from.name}</div>
        <div class="timeline-stop-time">Depart ${clock(leg.departure)} · Board ${leg.route}</div>
      </div>
    `;
    track.appendChild(startStep);

    // Intermediate Stretch Note with Crowding
    const pointsCount = (leg.points || []).length;
    if (pointsCount > 2) {
      const midStep = document.createElement("div");
      midStep.className = "timeline-step";
      midStep.style.margin = "6px 0";
      const modeledInfo = leg.crowd?.modeledPassengers
        ? ` · ~${Math.round(leg.crowd.modeledPassengers)} passengers (${leg.crowd.level})`
        : "";
      midStep.innerHTML = `
        <div class="timeline-content" style="color:var(--g-subtext); font-size:0.72rem;">
          Ride ${pointsCount - 1} stops (${Math.round(leg.rideMinutes)} min)${modeledInfo}
        </div>
      `;
      track.appendChild(midStep);
    }

    // Alighting Stop Node
    const endStep = document.createElement("div");
    endStep.className = "timeline-step";
    endStep.innerHTML = `
      <div class="timeline-node ${isLastLeg ? 'dest' : ''}"></div>
      <div class="timeline-content">
        <div class="timeline-stop-name">${leg.to.name}</div>
        <div class="timeline-stop-time">Arrive ${clock(leg.arrival)} ${isLastLeg ? '· Destination reached' : '· Transfer connection'}</div>
      </div>
    `;
    track.appendChild(endStep);

    legsContainer.appendChild(track);
  });

  details.appendChild(legsContainer);

  card.appendChild(top);
  card.appendChild(main);
  card.appendChild(details);

  // Click & Keyboard Selection
  const selectThisOption = () => {
    const allCards = byId("options").children;
    for (const c of allCards) {
      c.classList.remove("selected");
      c.setAttribute("aria-pressed", "false");
    }
    card.classList.add("selected");
    card.setAttribute("aria-pressed", "true");
    updateVisualizers(option);
  };

  card.addEventListener("click", (e) => {
    // Prevent toggling details from triggering map zoom change if user clicked summary
    if (e.target.tagName.toLowerCase() === "summary") return;
    selectThisOption();
  });

  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      selectThisOption();
    }
  });

  return card;
}

// 6. Journey Planner Form Submission
async function plan(event) {
  event?.preventDefault();
  const submit = form?.querySelector("button[type=submit]");
  if (submit?.disabled) return;

  if (!stopIds.origin || !stopIds.destination) {
    if (statusEl) statusEl.textContent = "Choose both stops from the search suggestions.";
    return;
  }

  if (submit) submit.disabled = true;
  if (statusEl) statusEl.textContent = "Finding scheduled journeys…";
  byId("options").replaceChildren();
  updateVisualizers(null);

  try {
    const result = await request("/api/journeys", {
      origin: stopIds.origin,
      destination: stopIds.destination,
      departure: byId("departure").value,
      extra: byId("extra").value,
    });

    if (statusEl) {
      statusEl.textContent = result.comfortReason || "";
    }

    const cards = result.options.map((opt, idx) => journeyCard(opt, idx === 0));
    byId("options").replaceChildren(...cards);
    updateVisualizers(result.options[0] || null);
  } catch (error) {
    if (statusEl) statusEl.textContent = error.message;
  } finally {
    if (submit) submit.disabled = false;
  }
}

if (form) form.addEventListener("submit", plan);

const extraInput = byId("extra");
if (extraInput) {
  extraInput.addEventListener("input", () => {
    const val = byId("extra-value");
    if (val) val.value = extraInput.value + " min";
  });
}

// 7. Interactive Controls & Buttons
const btnSwap = byId("btn-swap-stops");
if (btnSwap) {
  btnSwap.addEventListener("click", async () => {
    const originInput = byId("origin");
    const destInput = byId("destination");
    if (!originInput || !destInput) return;

    const tempName = originInput.value;
    originInput.value = destInput.value;
    destInput.value = tempName;

    // Resolve matching stop IDs for the reverse direction
    try {
      const origHits = await request("/api/stops", { q: originInput.value });
      const destHits = await request("/api/stops", { q: destInput.value });
      if (origHits && origHits.length) stopIds.origin = origHits[0].id;
      if (destHits && destHits.length) stopIds.destination = destHits[0].id;
    } catch (e) {
      console.warn("Could not resolve swapped stop IDs:", e);
    }

    if (stopIds.origin && stopIds.destination) {
      await plan();
    }
  });
}

// Quick Departure Time Chips
document.querySelectorAll(".time-chip").forEach((chip) => {
  chip.addEventListener("click", async () => {
    document.querySelectorAll(".time-chip").forEach((c) => c.classList.remove("active-time"));
    chip.classList.add("active-time");
    const tVal = chip.dataset.time;
    const depInput = byId("departure");
    if (!depInput) return;

    // Preserve the valid scheduled GTFS date
    let baseDate = "2026-11-11";
    if (depInput.value && depInput.value.includes("T")) {
      baseDate = depInput.value.split("T")[0];
    }

    if (tVal === "now") {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, "0");
      const min = String(now.getMinutes()).padStart(2, "0");
      depInput.value = `${baseDate}T${hh}:${min}`;
    } else {
      depInput.value = `${baseDate}T${tVal}`;
    }

    if (stopIds.origin && stopIds.destination) {
      await plan();
    }
  });
});

const btnToggle3D = byId("btn-toggle-3d");
if (btnToggle3D) {
  btnToggle3D.addEventListener("click", () => {
    if (transitMap) {
      const is3D = transitMap.toggle3D();
      btnToggle3D.classList.toggle("active", is3D);
    }
  });
}

const btnFollowVehicle = byId("btn-follow-vehicle");
if (btnFollowVehicle) {
  btnFollowVehicle.addEventListener("click", () => {
    if (transitMap) {
      const isFollow = transitMap.toggleFollow();
      btnFollowVehicle.classList.toggle("active", isFollow);
    }
  });
}

const btnLiveFleet = byId("btn-toggle-live-fleet");
if (btnLiveFleet) {
  btnLiveFleet.addEventListener("click", async () => {
    if (transitMap) {
      const isVisible = await transitMap.toggleLiveFleet();
      btnLiveFleet.classList.toggle("active", isVisible);
    }
  });
}

const btnTheme = byId("btn-toggle-theme");
if (btnTheme) {
  btnTheme.addEventListener("click", () => {
    const isNight = document.body.classList.toggle("theme-night");
    btnTheme.classList.toggle("active", isNight);
    if (transitMap) {
      transitMap.setTheme(isNight ? "night" : "day");
    }
  });
}

const btnRecenter = byId("btn-recenter");
if (btnRecenter) {
  btnRecenter.addEventListener("click", () => {
    if (transitMap) {
      transitMap.recenter();
    }
  });
}

const btnCancelRoute = byId("btn-cancel-route");
if (btnCancelRoute) {
  btnCancelRoute.addEventListener("click", () => {
    if (transitMap) {
      transitMap.clearJourney();
    }
    const allCards = byId("options")?.children || [];
    for (const c of allCards) {
      c.classList.remove("selected");
      c.setAttribute("aria-pressed", "false");
    }
  });
}

const btnSound = byId("hud-sound-toggle");
if (btnSound) {
  let isMuted = false;
  btnSound.addEventListener("click", () => {
    isMuted = !isMuted;
    btnSound.style.opacity = isMuted ? "0.5" : "1.0";
    btnSound.title = isMuted ? "Sound muted" : "Audio guidance active";
  });
}

// 8. Dynamic Benchmark Corridor Shortcuts from Dataset
async function loadCorridors() {
  const container = byId("corridor-chips");
  if (!container) return;
  try {
    const res = await request("/api/corridors");
    if (!res.corridors || !res.corridors.length) return;
    container.replaceChildren();

    res.corridors.forEach((corr, index) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip" + (index === 0 ? " active-chip" : "");
      chip.textContent = corr.label;
      chip.dataset.from = corr.from.id;
      chip.dataset.fromName = corr.from.name;
      chip.dataset.to = corr.to.id;
      chip.dataset.toName = corr.to.name;

      chip.addEventListener("click", async () => {
        container.querySelectorAll(".chip").forEach((c) => c.classList.remove("active-chip"));
        chip.classList.add("active-chip");
        chooseOrigin(corr.from);
        chooseDestination(corr.to);
        await plan();
      });

      container.appendChild(chip);
    });
  } catch (e) {
    console.warn("Could not load dynamic corridors:", e);
  }
}

// 9. Initial Configuration & Boot
async function initialize() {
  try {
    await loadCorridors();

    const config = await request("/api/config");
    const departureEl = byId("departure");
    if (departureEl && config.defaultTime) {
      departureEl.value = config.defaultTime;
    }
    const sourceEl = byId("source");
    if (sourceEl) {
      sourceEl.textContent = config.source === "unavailable"
        ? "Scheduled times · crowd data unavailable"
        : "Scheduled times · " + config.source;
    }

    if (config.origin && config.destination) {
      chooseOrigin(config.origin);
      chooseDestination(config.destination);
      await plan();
    }
  } catch (error) {
    if (statusEl) statusEl.textContent = error.message;
  }
}
initialize();

// 10. Corridor Audit Table
const corridorHour = byId("corridor-hour");
if (corridorHour) {
  for (let hour = 0; hour < 24; hour += 1) {
    const opt = node("option", String(hour).padStart(2, "0") + ":00");
    opt.value = hour;
    corridorHour.append(opt);
  }
  corridorHour.value = 18;
}

async function showSegments(event) {
  event?.preventDefault();
  const corridorForm = byId("corridor-form");
  const button = corridorForm?.querySelector("button");
  if (button) button.disabled = true;
  const corridorStatus = byId("corridor-status");
  if (corridorStatus) corridorStatus.textContent = "Loading segments…";
  byId("segments").replaceChildren();

  try {
    const data = await request("/api/crowding", {
      route: byId("corridor").value,
      hour: byId("corridor-hour").value,
      weekend: byId("corridor-day").value,
    });
    if (corridorStatus) {
      corridorStatus.textContent = data.segments.some((item) => item.days)
        ? "Stops below are in corridor sequence."
        : "No ticket sample for this hour and day type.";
    }
    for (const segment of data.segments) {
      const row = node("tr");
      const crowd = node("td");
      crowd.append(makeCrowdBadge(segment.level));
      row.append(
        node("td", segment.from + " → " + segment.to),
        crowd,
        node("td", segment.estimate === null ? "—" : segment.estimate.toFixed(1)),
        node("td", segment.days || "—")
      );
      byId("segments").append(row);
    }
  } catch (error) {
    if (corridorStatus) corridorStatus.textContent = error.message;
  } finally {
    if (button) button.disabled = false;
  }
}

const corridorForm = byId("corridor-form");
if (corridorForm) {
  corridorForm.addEventListener("submit", showSegments);
  request("/api/validation").then(async ({ audit, validation }) => {
    const valEl = byId("validation");
    if (valEl) {
      valEl.textContent = audit.modeled_ticket_rows.toLocaleString() + " generated tickets · "
        + validation.scored_segment_hour_cells + " held-out stretch/time combinations · average error "
        + validation.holdout_mae + " modeled passengers";
    }
    const corridorSelect = byId("corridor");
    if (corridorSelect) {
      for (const route of audit.sample_routes) {
        const option = node("option", route);
        option.value = route;
        corridorSelect.append(option);
      }
      corridorSelect.value = "502UP";
    }
    await showSegments();
  }).catch((error) => {
    const valEl = byId("validation");
    if (valEl) valEl.textContent = error.message;
  });
}
