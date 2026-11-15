/**
 * Delhi Transit Multimodal Map Engine
 * Powered by MapLibre GL 3D, OpenFreeMap Vector Basemap & DMRC Metro Integration.
 * Google Maps / Apple Maps Minimalist Standard. Zero generic icons.
 */
"use strict";

class TransitMapEngine {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = Object.assign({
      style: "https://tiles.openfreemap.org/styles/liberty",
      zoom: 13.5,
      pitch: 52,
      bearing: -16,
    }, options);

    this.map = null;
    this.isLoaded = false;
    this.is3D = true;
    this.followMode = false;
    this.currentJourney = null;
    this.routeCoords = [];
    this.animProgress = 0;
    this.animId = null;
    this.vehicleMarker = null;
    this.liveFleetVisible = false;
    this.liveFleetTimer = null;
    this.reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

    this._initMap();
  }

  _initMap() {
    if (typeof maplibregl === "undefined") {
      console.warn("MapLibre GL not loaded.");
      return;
    }

    this.map = new maplibregl.Map({
      container: this.containerId,
      style: { version: 8, sources: {}, layers: [{ id: "background", type: "background",
        paint: { "background-color": "#e7eeeb" } }] },
      center: this.options.center,
      zoom: this.options.zoom,
      pitch: this.options.pitch,
      maxPitch: 70,
      bearing: this.options.bearing,
      antialias: true,
      attributionControl: false,
    });

    this.map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    this.map.on("load", () => {
      this.isLoaded = true;
      this._setupLayers();
      this._setupInteractions();
      this.setTheme(this.currentTheme || "day");
      if (this._pendingJourney) {
        this.setJourney(this._pendingJourney);
        this._pendingJourney = null;
      }
    });

    this.map.on("dragstart", () => {
      if (this.followMode) {
        this.followMode = false;
        const btn = document.getElementById("btn-follow-vehicle");
        if (btn) {
          btn.classList.remove("active");
          btn.setAttribute("aria-pressed", "false");
        }
      }
    });
  }

  _setupLayers() {
    const map = this.map;
    const isNight = (this.currentTheme === "night");

    // 1. 3D Extruded Buildings (Real OpenStreetMap Building Heights across Delhi)
    if (map.getSource("openmaptiles") && !map.getLayer("3d-buildings")) {
      const layers = map.getStyle().layers || [];
      let labelLayerId;
      for (const layer of layers) {
        if (layer.type === "symbol" && layer.layout && layer.layout["text-field"]) {
          labelLayerId = layer.id;
          break;
        }
      }

      map.addLayer({
        id: "3d-buildings",
        source: "openmaptiles",
        "source-layer": "building",
        type: "fill-extrusion",
        minzoom: 12.5,
        paint: {
          "fill-extrusion-color": isNight
            ? [
                "interpolate", ["linear"], ["get", "render_height"],
                0, "#172033",
                20, "#222F47",
                60, "#31405a"
              ]
            : [
                "interpolate", ["linear"], ["get", "render_height"],
                0, "#F2EFE9",
                20, "#EAE5DC",
                60, "#DDD6CA"
              ],
          "fill-extrusion-height": [
            "interpolate", ["linear"], ["zoom"],
            12.5, 0,
            14.5, ["get", "render_height"]
          ],
          "fill-extrusion-base": [
            "interpolate", ["linear"], ["zoom"],
            12.5, 0,
            14.5, ["get", "render_min_height"]
          ],
          "fill-extrusion-opacity": isNight ? 0.92 : 0.82
        }
      }, labelLayerId);
    }

    // 2. Delhi Metro (DMRC) Network Layers
    if (!map.getSource("delhi-metro-source")) {
      map.addSource("delhi-metro-source", {
        type: "geojson",
        data: "api/metro/network"
      });
    }

    if (!map.getLayer("metro-rail-glow")) {
      map.addLayer({
        id: "metro-rail-glow",
        type: "line",
        source: "delhi-metro-source",
        filter: ["==", ["get", "type"], "metro"],
        paint: {
          "line-color": ["get", "color"],
          "line-width": isNight ? 10 : 8,
          "line-opacity": isNight ? 0.6 : 0.35,
          "line-blur": isNight ? 5 : 3
        }
      });
    }

    if (!map.getLayer("metro-rail-line")) {
      map.addLayer({
        id: "metro-rail-line",
        type: "line",
        source: "delhi-metro-source",
        filter: ["==", ["get", "type"], "metro"],
        paint: {
          "line-color": ["get", "color"],
          "line-width": 4.5,
          "line-opacity": 0.95
        }
      });
    }

    if (!map.getLayer("metro-rail-ties")) {
      map.addLayer({
        id: "metro-rail-ties",
        type: "line",
        source: "delhi-metro-source",
        filter: ["==", ["get", "type"], "metro"],
        paint: {
          "line-color": isNight ? "#E2E8F0" : "#FFFFFF",
          "line-width": 2.5,
          "line-dasharray": [1.5, 2.5],
          "line-opacity": 0.8
        }
      });
    }

    if (!map.getLayer("metro-stations-halo")) {
      map.addLayer({
        id: "metro-stations-halo",
        type: "circle",
        source: "delhi-metro-source",
        filter: ["==", ["get", "type"], "station"],
        paint: {
          "circle-radius": ["case", ["get", "interchange"], 7.5, 5],
          "circle-color": isNight ? "#0F172A" : "#FFFFFF",
          "circle-stroke-width": 2.5,
          "circle-stroke-color": ["case", ["get", "interchange"], "#F59E0B", isNight ? "#38BDF8" : "#2563EB"]
        }
      });
    }

    // 3. Active Journey Route Polyline
    if (!map.getSource("active-route-source")) {
      map.addSource("active-route-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
    }

    if (!map.getLayer("route-glow")) {
      map.addLayer({
        id: "route-glow",
        type: "line",
        source: "active-route-source",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": ["coalesce", ["get", "crowdColor"], isNight ? "#00E5FF" : "#1A73E8"],
          "line-width": isNight ? 14 : 10,
          "line-opacity": isNight ? 0.45 : 0.25,
          "line-blur": 6
        }
      });
    }

    if (!map.getLayer("route-casing")) {
      map.addLayer({
        id: "route-casing",
        type: "line",
        source: "active-route-source",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": isNight ? "#0B0F19" : "#FFFFFF",
          "line-width": 8.5,
          "line-opacity": 0.95
        }
      });
    }

    if (!map.getLayer("route-core")) {
      map.addLayer({
        id: "route-core",
        type: "line",
        source: "active-route-source",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": ["coalesce", ["get", "crowdColor"], isNight ? "#00D2FF" : "#1A73E8"],
          "line-width": 6,
          "line-opacity": 1.0
        }
      });
    }

    if (!map.getLayer("route-chevrons")) {
      map.addLayer({
        id: "route-chevrons",
        type: "line",
        source: "active-route-source",
        paint: {
          "line-color": "#FFFFFF",
          "line-width": 2.2,
          "line-dasharray": [1.4, 2.4],
          "line-opacity": 0.9
        }
      });
    }

    if (!map.getSource("route-stops-source")) {
      map.addSource("route-stops-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
    }

    if (!map.getLayer("route-stops")) {
      map.addLayer({
        id: "route-stops",
        type: "circle",
        source: "route-stops-source",
        paint: {
          "circle-radius": 4.5,
          "circle-color": isNight ? "#0B0F19" : "#FFFFFF",
          "circle-stroke-width": 2.0,
          "circle-stroke-color": isNight ? "#38BDF8" : "#374151"
        }
      });
    }

    if (!map.getSource("preview-headlights")) {
      map.addSource("preview-headlights", {
        type: "geojson", data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "preview-headlight-throw", type: "fill", source: "preview-headlights",
        paint: { "fill-color": "#c5e7ff", "fill-opacity": ["get", "opacity"],
          "fill-antialias": false },
      });
    }

    // 4. Live Fleet Streaming Across Delhi
    if (!map.getSource("live-fleet-source")) {
      map.addSource("live-fleet-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
    }

    if (!map.getLayer("live-fleet-glow")) {
      map.addLayer({
        id: "live-fleet-glow",
        type: "circle",
        source: "live-fleet-source",
        layout: { visibility: this.liveFleetVisible ? "visible" : "none" },
        paint: {
          "circle-radius": isNight ? 7 : 5,
          "circle-color": isNight ? "#00E5FF" : "#0F9D58",
          "circle-opacity": isNight ? 0.5 : 0.3,
          "circle-blur": 1.5
        }
      });
    }

    if (!map.getLayer("live-fleet-layer")) {
      map.addLayer({
        id: "live-fleet-layer",
        type: "circle",
        source: "live-fleet-source",
        layout: { visibility: this.liveFleetVisible ? "visible" : "none" },
        paint: {
          "circle-radius": isNight ? 3.8 : 4,
          "circle-color": isNight ? "#00E676" : "#0F9D58",
          "circle-stroke-width": 1.5,
          "circle-stroke-color": isNight ? "#042F2E" : "#FFFFFF",
          "circle-opacity": 0.95
        }
      });
    }

    // 5. Moving Vehicle Marker Element (Active Trip - 3D Animated Motion Graphics Model)
    if (!this.vehicleMarker) {
      const el = document.createElement("div");
      el.className = "transit-vehicle-marker";
      el.innerHTML = `
        <div class="vehicle-hud-speed" id="vehicle-floating-speed">Preview</div>
        <div class="vehicle-3d-wrapper">
          <div class="vehicle-underglow"></div>
          <div class="vehicle-chassis">
            <div class="windshield-front"></div>
            <div class="chassis-roof"></div>
            <div class="chassis-side chassis-side-left" aria-hidden="true"></div>
            <div class="chassis-side chassis-side-right" aria-hidden="true"></div>
            <div class="front-led-dots">
              <span class="headlight-dot left"></span>
              <span class="headlight-dot right"></span>
            </div>
            <div class="taillight-leds">
              <span class="tail-dot"></span>
              <span class="tail-dot"></span>
            </div>
          </div>
        </div>
      `;

      this.vehicleMarker = new maplibregl.Marker({ element: el, anchor: "center" });

      // Origin Marker (Google Blue Circle)
      const startEl = document.createElement("div");
      startEl.className = "gmaps-origin-marker";
      this.startMarker = new maplibregl.Marker({ element: startEl, anchor: "center" });

      // Destination Marker (Reference 1: Orange Teardrop with Travel Time & Pulse)
      const endEl = document.createElement("div");
      endEl.className = "dest-eta-pin";
      endEl.innerHTML = `
        <div class="dest-pin-ripple"></div>
        <div class="dest-pin-badge">
          <span class="dest-pin-time" id="dest-pin-time">--</span>
          <span class="dest-pin-unit">MIN</span>
        </div>
        <div class="dest-pin-tail"></div>
        <div class="dest-pin-anchor"></div>
      `;
      this.endMarker = new maplibregl.Marker({ element: endEl, anchor: "bottom" });
    }
  }

  _setupInteractions() {
    const map = this.map;
    if (this._interactionsSetup) return;
    this._interactionsSetup = true;

    const showPopup = (coords, title, lines, stopName) => {
      const content = document.createElement("div");
      content.className = "transit-popup-card";
      const name = document.createElement("strong");
      name.textContent = title;
      content.append(name);
      for (const line of lines) {
        const row = document.createElement("div");
        row.className = "popup-meta";
        row.textContent = line;
        content.append(row);
      }
      const popup = new maplibregl.Popup({ offset: 12, closeButton: true })
        .setLngLat(coords).setDOMContent(content).addTo(map);
      if (!stopName) return;
      const actions = document.createElement("div");
      actions.className = "popup-actions";
      for (const [field, label] of [["origin", "Directions from"], ["destination", "Directions to"]]) {
        const button = document.createElement("button");
        button.className = "popup-btn";
        button.textContent = label;
        button.addEventListener("click", () => {
          window.setPlannerStop(field, stopName);
          popup.remove();
        });
        actions.append(button);
      }
      content.append(actions);
    };
    map.on("click", "metro-stations-halo", ({ features }) => {
      if (!features?.length) return;
      const { geometry, properties: p } = features[0];
      showPopup(geometry.coordinates, p.name,
        [p.lines_str || p.line, p.gate_count ? p.gate_count + " mapped gate records" : "GTFS station"].filter(Boolean), p.name);
    });
    map.on("click", "live-fleet-layer", ({ features }) => {
      if (!features?.length) return;
      const { geometry, properties: p } = features[0];
      const speed = p.speed == null ? "Speed unavailable" : p.speed + " km/h";
      showPopup(geometry.coordinates, p.vehicle_id, ["Live GPS", p.route, speed].filter(Boolean));
    });

    // Pointer cursor on clickable transit features
    ["metro-stations-halo", "live-fleet-layer"].forEach((layerId) => {
      map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
    });
  }

  setJourney(journey) {
    if (!this.isLoaded || !this.map.getSource("active-route-source")) {
      this._pendingJourney = journey;
      return;
    }

    this.currentJourney = journey;

    this._cameraBearing = undefined;

    if (!journey || !journey.legs || !journey.legs.length) {
      this._clearRoute();
      return;
    }

    const allPoints = journey.legs.flatMap((l) => l.points || [l.from, l.to]);
    if (allPoints.length < 2) return;

    this.routeCoords = allPoints.map((p) => [p.lon, p.lat]);
    this.routeSegments = [];
    this.routeLength = 0;
    this.routeCoords.slice(1).forEach((end, i) => {
      const start = this.routeCoords[i];
      const north = end[1] - start[1];
      const east = (end[0] - start[0]) * Math.cos((start[1] + end[1]) * Math.PI / 360);
      const length = Math.hypot(north, east) * 111.195;
      if (!length) return;
      this.routeLength += length;
      this.routeSegments.push({ start, end, length, cumulative: this.routeLength,
        bearing: Math.atan2(east, north) * 180 / Math.PI, next: allPoints[i + 1] });
    });

    // Determine crowd color for route polyline
    const crowdLevel = journey.crowd?.level || "Seats available";
    let crowdColor = crowdLevel === "Seats available" ? "#34D399" : "#00E5FF";
    if (crowdLevel === "Standing room") {
      crowdColor = "#FBBF24"; // Standing Room (Amber)
    } else if (crowdLevel === "Heavily crowded") {
      crowdColor = "#FB7185"; // Crowded (Red)
    }

    // Update active route GeoJSON
    const routeFeature = {
      type: "Feature",
      properties: { crowdColor },
      geometry: {
        type: "LineString",
        coordinates: this.routeCoords
      }
    };
    this.map.getSource("active-route-source").setData({
      type: "FeatureCollection",
      features: [routeFeature]
    });

    // Update intermediate stops GeoJSON
    const intermediateStops = allPoints.slice(1, -1).map((p) => ({
      type: "Feature",
      properties: { name: p.name },
      geometry: {
        type: "Point",
        coordinates: [p.lon, p.lat]
      }
    }));
    this.map.getSource("route-stops-source").setData({
      type: "FeatureCollection",
      features: intermediateStops
    });

    // Position Start & End Markers
    const startCoord = this.routeCoords[0];
    const endCoord = this.routeCoords[this.routeCoords.length - 1];

    this.startMarker.setLngLat(startCoord).addTo(this.map);
    this.endMarker.setLngLat(endCoord).addTo(this.map);

    const pinTime = this.endMarker.getElement().querySelector("#dest-pin-time");
    if (pinTime) {
      pinTime.textContent = Math.round(journey.minutes);
    }

    // Show HUD Navigation and Bottom ETA Bar
    const navBanner = document.getElementById("hud-nav-banner");
    if (navBanner) navBanner.hidden = false;

    const bottomEta = document.getElementById("hud-bottom-eta");
    if (bottomEta) {
      bottomEta.hidden = false;
      const etaMin = document.getElementById("hud-eta-min");
      const etaDist = document.getElementById("hud-eta-dist");
      const etaArr = document.getElementById("hud-eta-arrival");
      const etaCrowd = document.getElementById("hud-eta-crowd");
      if (etaMin) etaMin.textContent = Math.round(journey.minutes);
      if (etaDist) etaDist.textContent = `${this.routeLength.toFixed(1)} km`;
      if (etaArr) {
        const arrDate = new Date(journey.arrival);
        etaArr.textContent = isNaN(arrDate) ? "--:--" : arrDate.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: true });
      }
      if (etaCrowd) {
        const firstLeg = journey.legs?.[0];
        const lvl = journey.crowd?.level || firstLeg?.crowd?.level || "Unknown";
        etaCrowd.className = "hud-crowd-chip " + (lvl === "Standing room" ? "crowd-med" : lvl === "Heavily crowded" ? "crowd-high" : lvl === "Seats available" ? "crowd-low" : "crowd-unknown");
        etaCrowd.textContent = `● ${lvl}`;
      }
    }

    const btnRecenter = document.getElementById("btn-recenter");
    if (btnRecenter) btnRecenter.hidden = false;

    // Frame the journey with smooth easing
    const bounds = this.routeCoords.reduce(
      (b, coord) => b.extend(coord),
      new maplibregl.LngLatBounds(startCoord, startCoord)
    );

    this.map.fitBounds(bounds, {
      padding: { top: 84, bottom: 105, left: 38, right: 38 },
      pitch: this.is3D ? 52 : 0,
      duration: this.reducedMotion.matches ? 0 : 760,
      maxZoom: 15.5
    });

    // Start Vehicle Animation
    this.vehicleMarker.setLngLat(startCoord).addTo(this.map);
    this.animProgress = 0;
    this._startVehicleAnimation();
  }

  _clearRoute() {
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
    this.currentJourney = null;
    this._pendingJourney = null;
    this.followMode = false;
    const follow = document.getElementById("btn-follow-vehicle");
    follow?.classList.remove("active");
    follow?.setAttribute("aria-pressed", "false");
    this.routeCoords = [];
    this.map?.getSource("preview-headlights")?.setData({ type: "FeatureCollection", features: [] });
    if (this.map && this.map.getSource("active-route-source")) {
      this.map.getSource("active-route-source").setData({ type: "FeatureCollection", features: [] });
    }
    if (this.map && this.map.getSource("route-stops-source")) {
      this.map.getSource("route-stops-source").setData({ type: "FeatureCollection", features: [] });
    }
    this.startMarker?.remove();
    this.endMarker?.remove();
    this.vehicleMarker?.remove();

    const navBanner = document.getElementById("hud-nav-banner");
    if (navBanner) navBanner.hidden = true;
    const bottomEta = document.getElementById("hud-bottom-eta");
    if (bottomEta) bottomEta.hidden = true;
    const btnRecenter = document.getElementById("btn-recenter");
    if (btnRecenter) btnRecenter.hidden = true;
  }

  _startVehicleAnimation() {
    cancelAnimationFrame(this.animId);
    if (!this.routeSegments?.length) return;
    const body = this.vehicleMarker.getElement().querySelector(".vehicle-3d-wrapper");
    const hudNext = document.getElementById("hud-next-stop");
    const hudSub = document.getElementById("hud-subtext");
    const route = this.currentJourney.legs.map((leg) => leg.route).join(" / ");
    hudSub.textContent = route + " · Scheduled route preview";
    let lastTime = performance.now();
    let previousStop;
    let lastLightPaint = -Infinity;
    let heading = this.routeSegments[0].bearing;
    const render = (time) => {
      const dt = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;
      const still = this.reducedMotion.matches;
      if (!still && !this.previewPaused) this.animProgress = (this.animProgress + dt / 28) % 1;
      const distance = this.animProgress * this.routeLength;
      const seg = this.routeSegments.find((item) => item.cumulative > distance)
        || this.routeSegments.at(-1);
      const fraction = 1 - (seg.cumulative - distance) / seg.length;
      const position = seg.start.map((value, axis) => value + (seg.end[axis] - value) * fraction);
      this.vehicleMarker.setLngLat(position);
      body.style.setProperty("--model-tilt", Math.round(this.map.getPitch() * .46) + "deg");
      const shortest = ((seg.bearing - heading + 540) % 360) - 180;
      heading += still ? shortest : shortest * (1 - Math.exp(-9 * dt));
      body.style.transform = `rotate(${heading - this.map.getBearing()}deg)`;
      if (time - lastLightPaint >= 1000 / 24) {
        this._paintHeadlights(position, heading);
        lastLightPaint = time;
      }
      this._previewHeading = heading;
      if (seg.next !== previousStop) {
        hudNext.textContent = "Next: " + seg.next.name;
        previousStop = seg.next;
      }
      if (this.followMode && !still) this._followVehicle(position, heading, dt);
      this.animId = requestAnimationFrame(render);
    };
    this.animId = requestAnimationFrame(render);
  }

  _paintHeadlights([lng, lat], heading) {
    const source = this.map.getSource("preview-headlights");
    if (!source || this.currentTheme !== "night") return;
    const angle = heading * Math.PI / 180;
    const latitudeScale = 1 / 111195;
    const longitudeScale = latitudeScale / Math.cos(lat * Math.PI / 180);
    const point = (forward, lateral) => [
      lng + (Math.sin(angle) * forward + Math.cos(angle) * lateral) * longitudeScale,
      lat + (Math.cos(angle) * forward - Math.sin(angle) * lateral) * latitudeScale,
    ];
    const features = [];
    for (const side of [-1, 1]) {
      const lamp = (forward, edge) => point(forward, side * (1 + forward / 18) + edge * (0.3 + forward / 13));
      let front = 5;
      for (const [back, opacity] of [[12, .24], [23, .15], [36, .09], [50, .04], [68, .015]]) {
        const ring = [lamp(front, -1), lamp(back, -1), lamp(back, 1), lamp(front, 1)];
        ring.push(ring[0]);
        features.push({ type: "Feature", properties: { opacity },
          geometry: { type: "Polygon", coordinates: [ring] } });
        front = back;
      }
    }
    source.setData({ type: "FeatureCollection", features });
  }

  _followVehicle(position, heading, dt, immediate = false) {
    const camera = this.map.getCenter();
    const amount = immediate ? 1 : 1 - Math.exp(-5 * dt);
    const angle = heading * Math.PI / 180;
    const offset = this.is3D ? (this.map.getContainer().clientWidth < 500 ? 0.00055 : 0.00155) : 0;
    const target = [position[0] + Math.sin(angle) * offset / Math.cos(position[1] * Math.PI / 180),
      position[1] + Math.cos(angle) * offset];
    const bearing = this.map.getBearing();
    const turn = ((heading - bearing + 540) % 360) - 180;
    this.map.jumpTo({
      center: [camera.lng + (target[0] - camera.lng) * amount,
        camera.lat + (target[1] - camera.lat) * amount],
      bearing: bearing + turn * amount,
      pitch: this.map.getPitch() + ((this.is3D ? 64 : 0) - this.map.getPitch()) * amount,
      zoom: this.map.getZoom() + (16.6 - this.map.getZoom()) * amount,
    });
  }

  async toggleLiveFleet() {
    this.liveFleetVisible = !this.liveFleetVisible;
    const visibility = this.liveFleetVisible ? "visible" : "none";
    for (const layer of ["live-fleet-layer", "live-fleet-glow"]) {
      if (this.map?.getLayer(layer)) this.map.setLayoutProperty(layer, "visibility", visibility);
    }
    if (this.liveFleetVisible) {
      await this.refreshLiveFleet();
      if (!this.liveFleetTimer) {
        this.liveFleetTimer = setInterval(() => this.refreshLiveFleet(), 20000);
      }
    } else {
      if (this.liveFleetTimer) {
        clearInterval(this.liveFleetTimer);
        this.liveFleetTimer = null;
      }
    }
    return this.liveFleetVisible;
  }

  async refreshLiveFleet() {
    try {
      const res = await fetch("api/vehicles");
      const data = await res.json();
      if (!this.liveFleetVisible) return;
      if (data && data.positions && this.map && this.map.getSource("live-fleet-source")) {
        const features = data.positions.map((p) => ({
          type: "Feature",
          properties: {
            vehicle_id: p.vehicle_id,
            speed: p.speed_kmh,
            route: p.route_id
          },
          geometry: {
            type: "Point",
            coordinates: [p.lon, p.lat]
          }
        }));
        this.map.getSource("live-fleet-source").setData({
          type: "FeatureCollection",
          features
        });
        const pillText = document.getElementById("fleet-count-text");
        if (pillText) pillText.textContent = data.status === "live"
          ? data.total_live_fleet.toLocaleString() + " live buses"
          : data.status === "disabled" ? "Live feed not configured" : "No fresh GPS positions";
      }
    } catch (e) {
      console.warn("Live fleet poll failed:", e);
    }
  }

  toggle3D() {
    this.is3D = !this.is3D;
    this.map.easeTo({
      pitch: this.is3D ? 52 : 0,
      bearing: this.is3D ? -16 : 0,
      duration: this.reducedMotion.matches ? 0 : 600
    });
    return this.is3D;
  }

  toggleFollow() {
    if (!this.currentJourney) return false;
    if (!this.followMode) this.map.stop();
    if (!this.followMode && this.reducedMotion.matches) {
      this.recenter();
      return true;
    }
    this.followMode = !this.followMode;
    return this.followMode;
  }

  recenter() {
    if (!this.currentJourney || !this.vehicleMarker) return;
    this.followMode = true;
    const button = document.getElementById("btn-follow-vehicle");
    button?.classList.add("active");
    button?.setAttribute("aria-pressed", "true");
    const { lng, lat } = this.vehicleMarker.getLngLat();
    this.map.stop();
    this._followVehicle([lng, lat], this._previewHeading ?? this.map.getBearing(), 0, true);
  }

  clearJourney() {
    this._clearRoute();
  }

  async setTheme(theme) {
    this.currentTheme = theme;
    this._styleRequest?.abort();
    const request = new AbortController();
    this._styleRequest = request;
    const night = theme === "night";
    let style;
    try {
      const response = await fetch("https://tiles.openfreemap.org/styles/" + (night ? "dark" : "liberty"),
        { signal: request.signal });
      if (!response.ok) throw new Error("Basemap unavailable");
      style = await response.json();
      if (style.sources.openmaptiles) {
        const metadata = await fetch(style.sources.openmaptiles.url, { signal: request.signal });
        if (!metadata.ok) throw new Error("Basemap unavailable");
        const { url, ...source } = style.sources.openmaptiles;
        style.sources.openmaptiles = { ...await metadata.json(), ...source };
      }
    } catch {
      if (request.signal.aborted) return;
      document.getElementById("map-source-status").textContent = "Street basemap unavailable";
      style = { version: 8, sources: {}, layers: [{ id: "background", type: "background",
        paint: { "background-color": night ? "#0B0F19" : "#e7eeeb" } }] };
    }
    if (request.signal.aborted) return;
    if (style.sources.openmaptiles) document.getElementById("map-source-status").textContent = "";
    if (night) {
      const background = style.layers.find((layer) => layer.type === "background");
      if (background) background.paint["background-color"] = "#0B0F19";
      const palette = { "water": "#10283e", "road": "#25324a", "landcover": "#132032",
        "landuse": "#111e2d" };
      for (const layer of style.layers) {
        const key = layer["source-layer"];
        if (layer.type === "line" && key === "transportation") layer.paint["line-color"] = palette.road;
        if (layer.type === "fill" && palette[key]) layer.paint["fill-color"] = palette[key];
      }
      style.light = { anchor: "viewport", color: "#bccfff", intensity: .42, position: [1.5, 225, 48] };
      style.sky = { "sky-color": "#111c32", "horizon-color": "#334a69",
        "fog-color": "#152138", "fog-ground-blend": .62 };
    }
    if (this._styleLoaded) this.map.off("style.load", this._styleLoaded);
    this._styleLoaded = () => {
      if (request.signal.aborted) return;
      this._setupLayers();
      this.isLoaded = true;
      const journey = this._pendingJourney || this.currentJourney;
      this._pendingJourney = null;
      if (journey) this.setJourney(journey);
      if (this.liveFleetVisible) this.refreshLiveFleet();
    };
    this.map.once("style.load", this._styleLoaded);
    this.map.setStyle(style, { diff: false });
  }
}
