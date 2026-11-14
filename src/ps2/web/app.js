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
  legsContainer.style.paddingTop = "8px";

  option.legs.forEach((leg) => {
    const legRow = document.createElement("div");
    legRow.style.marginBottom = "6px";
    legRow.style.lineHeight = "1.4";

    const legTitle = document.createElement("div");
    legTitle.style.fontWeight = "600";
    legTitle.style.color = "var(--g-text)";
    legTitle.textContent = leg.route + " · " + Math.round(leg.rideMinutes) + " min";

    const legPath = document.createElement("div");
    legPath.textContent = clock(leg.departure) + " " + leg.from.name + " → " + clock(leg.arrival) + " " + leg.to.name;

    legRow.appendChild(legTitle);
    legRow.appendChild(legPath);

    if (leg.crowd?.modeledPassengers) {
      const stats = document.createElement("div");
      stats.style.fontSize = "0.72rem";
      stats.style.color = "var(--g-subtext)";
      stats.textContent = "Modeled occupancy: ~" + Math.round(leg.crowd.modeledPassengers) + " passengers (" + leg.crowd.days + " day sample)";
      legRow.appendChild(stats);
    }

    legsContainer.appendChild(legRow);
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

// 7. Floating 3D and Follow Camera Controls
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

// 8. Quick Corridor Shortcuts
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", async () => {
    document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active-chip"));
    chip.classList.add("active-chip");

    const fromId = chip.dataset.from;
    const fromName = chip.dataset.fromName;
    const toId = chip.dataset.to;
    const toName = chip.dataset.toName;

    chooseOrigin({ id: fromId, name: fromName });
    chooseDestination({ id: toId, name: toName });
    await plan();
  });
});

// 9. Initial Configuration & Boot
async function initialize() {
  try {
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
