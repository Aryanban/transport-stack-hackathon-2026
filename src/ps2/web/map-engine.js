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
      center: [77.2285, 28.6500], // Delhi Gate - Central Delhi
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
    this.matchedLiveVehicle = null;

    this._initMap();
  }

  _initMap() {
    if (typeof maplibregl === "undefined") {
      console.warn("MapLibre GL not loaded.");
      return;
    }

    this.map = new maplibregl.Map({
      container: this.containerId,
      style: this.options.style,
      center: this.options.center,
      zoom: this.options.zoom,
      pitch: this.options.pitch,
      bearing: this.options.bearing,
      antialias: true,
      attributionControl: false,
    });

    this.map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    this.map.on("load", () => {
      this.isLoaded = true;
      this._setupLayers();
      if (this._pendingJourney) {
        this.setJourney(this._pendingJourney);
        this._pendingJourney = null;
      }
    });

    this.map.on("dragstart", () => {
      if (this.followMode) {
        this.followMode = false;
        const btn = document.getElementById("btn-follow-vehicle");
        if (btn) btn.classList.remove("active");
      }
    });
  }

  _setupLayers() {
    const map = this.map;

    // 1. 3D Extruded Buildings (Real OpenStreetMap Building Heights across Delhi)
    if (map.getSource("openmaptiles")) {
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
          "fill-extrusion-color": [
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
          "fill-extrusion-opacity": 0.82
        }
      }, labelLayerId);
    }

    // 2. Delhi Metro (DMRC) Network Layers (Dynamically loaded from backend)
    map.addSource("delhi-metro-source", {
      type: "geojson",
      data: "api/metro/network"
    });

    // Elevated Metro Track Glow / Casing
    map.addLayer({
      id: "metro-rail-glow",
      type: "line",
      source: "delhi-metro-source",
      filter: ["==", ["get", "type"], "metro"],
      paint: {
        "line-color": ["get", "color"],
        "line-width": 8,
        "line-opacity": 0.35,
        "line-blur": 3
      }
    });

    // Elevated Metro Rail Viaduct Line
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

    // Metro Rail Track Ties Pattern
    map.addLayer({
      id: "metro-rail-ties",
      type: "line",
      source: "delhi-metro-source",
      filter: ["==", ["get", "type"], "metro"],
      paint: {
        "line-color": "#FFFFFF",
        "line-width": 2.5,
        "line-dasharray": [1.5, 2.5],
        "line-opacity": 0.8
      }
    });

    // Metro Station Nodes
    map.addLayer({
      id: "metro-stations-halo",
      type: "circle",
      source: "delhi-metro-source",
      filter: ["==", ["get", "type"], "station"],
      paint: {
        "circle-radius": ["case", ["get", "interchange"], 7.5, 5],
        "circle-color": "#FFFFFF",
        "circle-stroke-width": 2.5,
        "circle-stroke-color": ["case", ["get", "interchange"], "#D97706", "#2563EB"]
      }
    });

    // 2b. Moving Metro Train Markers (Dynamic Headway Simulation along DMRC Tracks)
    map.addSource("metro-trains-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] }
    });

    map.addLayer({
      id: "metro-trains-glow",
      type: "circle",
      source: "metro-trains-source",
      paint: {
        "circle-radius": 9,
        "circle-color": ["get", "color"],
        "circle-opacity": 0.4,
        "circle-blur": 1
      }
    });

    map.addLayer({
      id: "metro-trains-body",
      type: "circle",
      source: "metro-trains-source",
      paint: {
        "circle-radius": 5,
        "circle-color": ["get", "color"],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#FFFFFF"
      }
    });

    // Fetch dynamic metro tracks for continuous train interpolation
    fetch("api/metro/network")
      .then((r) => r.json())
      .then((data) => {
        if (data && data.features) {
          this.metroLines = data.features.filter((f) => f.properties.type === "metro");
          this._startMetroTrainLoop();
        }
      })
      .catch((e) => console.warn("Could not load metro network for train loop:", e));

    // 3. Active Journey Route Polyline
    map.addSource("active-route-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] }
    });

    // Route Outer Casing
    map.addLayer({
      id: "route-casing",
      type: "line",
      source: "active-route-source",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": "#FFFFFF",
        "line-width": 9,
        "line-opacity": 0.95
      }
    });

    // Route Primary Line with Dynamic Crowding Color
    map.addLayer({
      id: "route-core",
      type: "line",
      source: "active-route-source",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: {
        "line-color": ["coalesce", ["get", "crowdColor"], "#1A73E8"],
        "line-width": 6,
        "line-opacity": 1.0
      }
    });

    // Route Directional Chevrons
    map.addLayer({
      id: "route-chevrons",
      type: "line",
      source: "active-route-source",
      paint: {
        "line-color": "#FFFFFF",
        "line-width": 2.0,
        "line-dasharray": [1.5, 2.5],
        "line-opacity": 0.85
      }
    });

    // Intermediate Stop Circles
    map.addSource("route-stops-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] }
    });

    map.addLayer({
      id: "route-stops",
      type: "circle",
      source: "route-stops-source",
      paint: {
        "circle-radius": 4.5,
        "circle-color": "#FFFFFF",
        "circle-stroke-width": 2.0,
        "circle-stroke-color": "#374151"
      }
    });

    // 4. Live Fleet Streaming Across Delhi (3,600+ real GTFS-RT vehicles)
    map.addSource("live-fleet-source", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] }
    });

    map.addLayer({
      id: "live-fleet-layer",
      type: "circle",
      source: "live-fleet-source",
      layout: { visibility: "none" },
      paint: {
        "circle-radius": 4,
        "circle-color": "#0F9D58",
        "circle-stroke-width": 1.5,
        "circle-stroke-color": "#FFFFFF",
        "circle-opacity": 0.9
      }
    });

    // 5. Moving Vehicle Marker Element (Active Trip)
    const el = document.createElement("div");
    el.className = "transit-vehicle-marker";
    el.innerHTML = `
      <div class="vehicle-pulse"></div>
      <div class="vehicle-body">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M4 16c0 .88.39 1.67 1 2.22V20c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h8v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1.78c.61-.55 1-1.34 1-2.22V6c0-3.5-3.58-4-8-4s-8 .5-8 4v10zm3.5 1c-.83 0-1.5-.67-1.5-1.5S6.67 14 7.5 14s1.5.67 1.5 1.5S8.33 17 7.5 17zm9 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zm1.5-6H6V6h12v5z"/>
        </svg>
      </div>
    `;

    this.vehicleMarker = new maplibregl.Marker({ element: el, anchor: "center" });

    // Origin Marker (Google Blue Circle)
    const startEl = document.createElement("div");
    startEl.className = "gmaps-origin-marker";
    this.startMarker = new maplibregl.Marker({ element: startEl, anchor: "center" });

    // Destination Marker (Google Red Pin)
    const endEl = document.createElement("div");
    endEl.className = "gmaps-dest-marker";
    endEl.innerHTML = `
      <svg viewBox="0 0 24 34" width="24" height="34">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 9 12 22 12 22s12-13 12-22c0-6.63-5.37-12-12-12zm0 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5z" fill="#EA4335"/>
      </svg>
    `;
    this.endMarker = new maplibregl.Marker({ element: endEl, anchor: "bottom" });
  }

  setJourney(journey) {
    if (!this.isLoaded) {
      this._pendingJourney = journey;
      return;
    }

    this.currentJourney = journey;
    this.matchedLiveVehicle = null;

    if (!journey || !journey.legs || !journey.legs.length) {
      this._clearRoute();
      return;
    }

    const firstLeg = journey.legs[0];
    const routeParam = firstLeg.routeId || firstLeg.route;
    if (routeParam) {
      this._checkLiveVehicle(routeParam);
    }

    const allPoints = journey.legs.flatMap((l) => l.points || [l.from, l.to]);
    if (allPoints.length < 2) return;

    this.routeCoords = allPoints.map((p) => [p.lon, p.lat]);

    // Determine crowd color for route polyline
    const crowdLevel = journey.crowd?.level || "Seats available";
    let crowdColor = "#00875A"; // Seats Available (Green)
    if (crowdLevel === "Standing room") {
      crowdColor = "#E65100"; // Standing Room (Amber)
    } else if (crowdLevel === "Heavily crowded") {
      crowdColor = "#D32F2F"; // Crowded (Red)
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

    // Frame the journey with smooth easing
    const bounds = this.routeCoords.reduce(
      (b, coord) => b.extend(coord),
      new maplibregl.LngLatBounds(startCoord, startCoord)
    );

    this.map.fitBounds(bounds, {
      padding: { top: 90, bottom: 90, left: 420, right: 80 },
      pitch: this.is3D ? 52 : 0,
      duration: 1200,
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
    this.routeCoords = [];
    if (this.map && this.map.getSource("active-route-source")) {
      this.map.getSource("active-route-source").setData({ type: "FeatureCollection", features: [] });
    }
    if (this.map && this.map.getSource("route-stops-source")) {
      this.map.getSource("route-stops-source").setData({ type: "FeatureCollection", features: [] });
    }
    this.startMarker?.remove();
    this.endMarker?.remove();
    this.vehicleMarker?.remove();
  }

  _startVehicleAnimation() {
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }

    if (!this.routeCoords || this.routeCoords.length < 2) return;

    let lastTime = performance.now();

    const animate = (time) => {
      if (!this.routeCoords || this.routeCoords.length < 2) {
        this.animId = null;
        return;
      }

      const coords = this.routeCoords;
      const totalSegments = coords.length - 1;
      if (totalSegments < 1) {
        this.animId = null;
        return;
      }

      const dt = Math.min((time - lastTime) / 1000, 0.1);
      lastTime = time;

      this.animProgress = (this.animProgress + dt * 0.04) % 1.0;

      // Calculate position along piecewise polyline
      const globalPos = this.animProgress * totalSegments;
      const segIndex = Math.max(0, Math.min(Math.floor(globalPos), totalSegments - 1));
      const segProgress = Math.max(0, Math.min(globalPos - segIndex, 1));

      const p1 = coords[segIndex];
      const p2 = coords[segIndex + 1];
      if (!p1 || !p2 || !p1[0] || !p2[0]) {
        this.animId = requestAnimationFrame(animate);
        return;
      }

      const currentLon = p1[0] + (p2[0] - p1[0]) * segProgress;
      const currentLat = p1[1] + (p2[1] - p1[1]) * segProgress;

      this.vehicleMarker.setLngLat([currentLon, currentLat]);

      // Calculate bearing
      const dLon = p2[0] - p1[0];
      const dLat = p2[1] - p1[1];
      const bearing = (Math.atan2(dLon, dLat) * 180) / Math.PI;

      const bodyEl = this.vehicleMarker.getElement().querySelector(".vehicle-body");
      if (bodyEl) {
        bodyEl.style.transform = `rotate(${bearing}deg)`;
      }

      // Update HUD banner with next stop info
      const nextStopIndex = Math.min(segIndex + 1, coords.length - 1);
      const points = this.currentJourney?.legs?.[0]?.points || [];
      const nextStop = points[nextStopIndex] || this.currentJourney?.legs?.[0]?.to;

      const hudNext = document.getElementById("hud-next-stop");
      const hudSub = document.getElementById("hud-subtext");
      if (hudNext && nextStop) {
        hudNext.textContent = "Next: " + nextStop.name;
      }
      if (hudSub && this.currentJourney) {
        const firstLeg = this.currentJourney.legs[0];
        if (this.matchedLiveVehicle) {
          const lv = this.matchedLiveVehicle;
          hudSub.textContent = "Live GPS: " + lv.vehicle_id + " · " + lv.speed_kmh + " km/h · " + Math.round(lv.age_seconds) + "s ago";
        } else {
          const remainingMin = Math.max(1, Math.round((1 - this.animProgress) * this.currentJourney.minutes));
          hudSub.textContent = "Bus " + (firstLeg?.route || "502") + " · " + remainingMin + " min remaining (Timetable run)";
        }
      }

      // Smooth camera follow in Follow Mode
      if (this.followMode) {
        this.map.easeTo({
          center: [currentLon, currentLat],
          bearing: bearing,
          pitch: 58,
          zoom: 16.2,
          duration: 200,
        });
      }

      this.animId = requestAnimationFrame(animate);
    };

    this.animId = requestAnimationFrame(animate);
  }

  async _checkLiveVehicle(routeId) {
    try {
      const clean = String(routeId).replace(/[^a-zA-Z0-9]/g, "");
      const res = await fetch("api/vehicles?route=" + encodeURIComponent(clean));
      const data = await res.json();
      if (data && data.positions && data.positions.length > 0) {
        this.matchedLiveVehicle = data.positions[0];
      } else {
        this.matchedLiveVehicle = null;
      }
    } catch {
      this.matchedLiveVehicle = null;
    }
  }

  async toggleLiveFleet() {
    this.liveFleetVisible = !this.liveFleetVisible;
    const visibility = this.liveFleetVisible ? "visible" : "none";
    if (this.map && this.map.getLayer("live-fleet-layer")) {
      this.map.setLayoutProperty("live-fleet-layer", "visibility", visibility);
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
        if (pillText && data.total_live_fleet) {
          pillText.textContent = data.total_live_fleet.toLocaleString() + " Live Buses";
        }
      }
    } catch (e) {
      console.warn("Live fleet poll failed:", e);
    }
  }

  _startMetroTrainLoop() {
    if (this._metroTrainInterval) clearInterval(this._metroTrainInterval);

    const updateTrains = () => {
      if (!this.map || !this.metroLines || !this.map.getSource("metro-trains-source")) return;

      const now = performance.now() / 1000;
      const trainFeatures = [];

      this.metroLines.forEach((line) => {
        const coords = line.geometry?.coordinates;
        if (!coords || coords.length < 2) return;

        const color = line.properties?.color || "#FFD700";
        const lineName = line.properties?.name || "Metro Line";
        const totalSegments = coords.length - 1;

        const trainsOnLine = Math.min(6, Math.max(2, Math.floor(coords.length / 5)));
        for (let i = 0; i < trainsOnLine; i++) {
          const phaseOffset = i / trainsOnLine;
          const progress = (now * 0.015 + phaseOffset) % 1.0;
          const globalPos = progress * totalSegments;
          const segIndex = Math.max(0, Math.min(Math.floor(globalPos), totalSegments - 1));
          const segProgress = Math.max(0, Math.min(globalPos - segIndex, 1));

          const p1 = coords[segIndex];
          const p2 = coords[segIndex + 1];
          if (!p1 || !p2 || !p1[0] || !p2[0]) continue;

          const lon = p1[0] + (p2[0] - p1[0]) * segProgress;
          const lat = p1[1] + (p2[1] - p1[1]) * segProgress;

          trainFeatures.push({
            type: "Feature",
            properties: {
              line: lineName,
              color: color,
              train_id: `${lineName.replace(/\s+/g, "")}-${i + 1}`
            },
            geometry: {
              type: "Point",
              coordinates: [lon, lat]
            }
          });
        }
      });

      this.map.getSource("metro-trains-source").setData({
        type: "FeatureCollection",
        features: trainFeatures
      });
    };

    updateTrains();
    this._metroTrainInterval = setInterval(updateTrains, 1000);
  }

  toggle3D() {
    this.is3D = !this.is3D;
    this.map.easeTo({
      pitch: this.is3D ? 52 : 0,
      bearing: this.is3D ? -16 : 0,
      duration: 800
    });
    return this.is3D;
  }

  toggleFollow() {
    this.followMode = !this.followMode;
    return this.followMode;
  }
}
