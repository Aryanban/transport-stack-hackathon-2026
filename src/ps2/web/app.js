"use strict";

const byId = (id) => document.getElementById(id);
const form = byId("planner");
const status = byId("status");
const stopIds = {};
const timeFormat = new Intl.DateTimeFormat("en-IN", {
  timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
});
const clock = (value) => timeFormat.format(new Date(value));
const routeMap = new RouteMap(byId("map"), byId("map-vehicles"), byId("map-motion"));
let liveRequest = 0;
let liveTimer = null;

async function request(path, params, signal) {
  const query = params ? "?" + new URLSearchParams(params).toString() : "";
  const response = await fetch(path.replace(/^\//, "") + query, { signal });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Check your entries and try again.");
  return data;
}

function node(tag, content, className) {
  const item = document.createElement(tag);
  if (content !== undefined) item.textContent = content;
  if (className) item.className = className;
  return item;
}

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
        if (!suggestions.length) list.append(node("p", "No matching stops."));
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
        if (!signal.aborted) status.textContent = error.message;
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
    selected = selected < 0 && direction < 0 ? suggestions.length - 1
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

function pill(level) {
  const classes = { "Seats available": "low", "Standing room": "moderate", "Heavily crowded": "high" };
  return node("span", level === "Unknown" ? "Crowd estimate unavailable" : level, "pill " + (classes[level] || ""));
}

function journeyCard(option) {
  const card = node("article", undefined, "card");
  const top = node("div", undefined, "card-top");
  top.append(node("h3", option.label), pill(option.crowd.level));
  const bottom = node("div", undefined, "card-bottom");
  const transfer = option.transfers ? "1 transfer" : "Direct";
  bottom.append(node("span", clock(option.departure) + " → " + clock(option.arrival) + " · " + transfer));
  if (option.extraMinutes > 0) bottom.append(node("span", "+" + option.extraMinutes + " min"));
  const details = node("details");
  details.append(node("summary", "Bus and stop details"));
  details.append(node("p", "Initial wait " + option.waitMinutes + " min"
    + (option.transfers && option.crowd.busiestLeg ? " · Busiest leg " + option.crowd.busiestLeg.toLowerCase() : ""), "leg-note"));
  for (const leg of option.legs) {
    const row = node("div", undefined, "leg");
    const headline = node("div", undefined, "leg-top");
    headline.append(node("strong", "Bus " + leg.route), pill(leg.crowd.level));
    row.append(headline, node("p", clock(leg.departure) + " " + leg.from.name + " → "
      + clock(leg.arrival) + " " + leg.to.name));
    if (leg.crowd.days) {
      row.append(node("p", "About " + leg.crowd.modeledPassengers + " passengers · "
        + Math.round(leg.crowd.coverage * 100) + "% of ride modeled · "
        + leg.crowd.days + " sample days", "leg-note"));
      row.append(node("p", "Busiest modeled stretch · " + leg.crowd.busiestSegment, "leg-note"));
    }
    details.append(row);
  }
  const show = node("button", "Show on map");
  show.className = "show-route";
  show.setAttribute("aria-pressed", "false");
  show.type = "button";
  show.addEventListener("click", () => {
    for (const item of byId("options").children) {
      item.classList.toggle("selected", item === card);
      item.querySelector(".show-route").setAttribute("aria-pressed", String(item === card));
    }
    routeMap.setJourney(option);
    if (window.matchMedia("(max-width: 710px)").matches) byId("map-title").scrollIntoView({ block: "start" });
  });
  bottom.append(show);
  card.append(top, node("strong", option.minutes + " min", "minutes"), bottom, details);
  return card;
}

async function plan(event) {
  event?.preventDefault();
  const submit = form.querySelector("button[type=submit]");
  if (submit.disabled) return;
  if (!stopIds.origin || !stopIds.destination) {
    status.textContent = "Choose both stops from the search suggestions.";
    return;
  }
  submit.disabled = true;
  status.textContent = "Finding scheduled journeys…";
  byId("options").replaceChildren();
  routeMap.setJourney(null);
  try {
    const result = await request("/api/journeys", {
      origin: stopIds.origin, destination: stopIds.destination,
      departure: byId("departure").value, extra: byId("extra").value,
    });
    status.textContent = result.comfortReason || "";
    const cards = result.options.map(journeyCard);
    if (cards.length) {
      cards[0].classList.add("selected");
      cards[0].querySelector(".show-route").setAttribute("aria-pressed", "true");
    }
    byId("options").replaceChildren(...cards);
    routeMap.setJourney(result.options[0] || null);
  } catch (error) {
    status.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
}

async function refreshLive() {
  const requestId = ++liveRequest;
  try {
    const result = await request("/api/vehicles");
    if (liveTimer === null || requestId !== liveRequest) return;
    routeMap.setLive(result.positions);
    byId("live-status").textContent = result.status === "live"
      ? "Live positions as of " + clock(result.timestamp * 1000) + " IST"
      : "Live positions currently unavailable";
  } catch {
    if (liveTimer === null || requestId !== liveRequest) return;
    routeMap.setLive([]);
    byId("live-status").textContent = "Live positions currently unavailable";
  }
}

byId("live").addEventListener("click", () => {
  if (liveTimer !== null) {
    clearInterval(liveTimer);
    liveTimer = null;
    routeMap.setLive([]);
    byId("live").textContent = "Show live buses";
    byId("live-status").textContent = "Stop-to-stop schematic";
    return;
  }
  liveTimer = setInterval(refreshLive, 30000);
  byId("live").textContent = "Hide live buses";
  byId("live-status").textContent = "Loading live positions…";
  refreshLive();
});
byId("extra").addEventListener("input", () => {
  byId("extra-value").value = byId("extra").value + " min";
});
form.addEventListener("submit", plan);

async function initialize() {
  try {
    const config = await request("/api/config");
    byId("departure").value = config.defaultTime;
    byId("source").textContent = config.source === "unavailable" ? "Scheduled times · crowd data unavailable"
      : "Scheduled times · " + config.source;
    byId("live").hidden = !config.liveConfigured;
    if (config.sample) {
      byId("mode").textContent = "Generated ticket data";
      byId("mode").hidden = false;
    }
    if (config.origin && config.destination) {
      chooseOrigin(config.origin);
      chooseDestination(config.destination);
      await plan();
    }
  } catch (error) {
    status.textContent = error.message;
  }
}
initialize();

for (let hour = 0; hour < 24; hour += 1) {
  const option = node("option", String(hour).padStart(2, "0") + ":00");
  option.value = hour;
  byId("corridor-hour").append(option);
}
byId("corridor-hour").value = 18;

async function showSegments(event) {
  event?.preventDefault();
  const button = byId("corridor-form").querySelector("button");
  button.disabled = true;
  byId("corridor-status").textContent = "Loading segments…";
  byId("segments").replaceChildren();
  try {
    const data = await request("/api/crowding", {
      route: byId("corridor").value,
      hour: byId("corridor-hour").value,
      weekend: byId("corridor-day").value,
    });
    byId("corridor-status").textContent = data.segments.some((item) => item.days)
      ? "Stops below are in the ticket sample’s corridor order." : "No ticket sample for this hour and day type.";
    for (const segment of data.segments) {
      const row = node("tr");
      const crowd = node("td");
      crowd.append(pill(segment.level));
      row.append(node("td", segment.from + " → " + segment.to), crowd,
        node("td", segment.estimate === null ? "—" : segment.estimate.toFixed(1)),
        node("td", segment.days || "—"));
      byId("segments").append(row);
    }
  } catch (error) {
    byId("corridor-status").textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

byId("corridor-form").addEventListener("submit", showSegments);
request("/api/validation").then(async ({ audit, validation }) => {
  byId("validation").textContent = audit.modeled_ticket_rows.toLocaleString() + " generated tickets · "
    + validation.scored_segment_hour_cells + " held-out stretch/time combinations · average error "
    + validation.holdout_mae + " modeled passengers";
  for (const route of audit.sample_routes) {
    const option = node("option", route);
    option.value = route;
    byId("corridor").append(option);
  }
  byId("corridor").value = "502UP";
  await showSegments();
}).catch((error) => { byId("validation").textContent = error.message; });
