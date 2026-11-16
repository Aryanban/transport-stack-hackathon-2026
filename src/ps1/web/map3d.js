/**
 * Delhi Transit Multimodal Map Engine
 * Powered by MapLibre GL 3D, OpenFreeMap Vector Basemap & DMRC Metro Integration.
 * Google Maps / Apple Maps Minimalist Standard.
 * Authentic 3D Bus & Metro Train Models (Zero Green Dots).
 */
"use strict";

function drawRoundRect(ctx, x, y, w, h, r) {
  if (ctx.roundRect) {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  if (w < 2 * r) r = w / 2;
  if (h < 2 * r) r = h / 2;
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/**
 * Generates an authentic 3D DTC Electric Low-Floor Bus sprite
 * Dimensions: 64x120px (retina @2x = 32x60px map display)
 * Heading 0 = North (Front points UP towards -Y)
 */
function create3DBusImage(color = "#00A389") {
  const w = 64, h = 120;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");

  // 1. Soft Ambient Underbody Drop Shadow (Provides 3D clearance above road)
  ctx.save();
  ctx.fillStyle = "rgba(15, 23, 42, 0.32)";
  drawRoundRect(ctx, 15, 23, 34, 82, 8);
  ctx.fill();
  ctx.restore();

  // 2. Main Bus Chassis (DTC Electric Emerald Teal / Metallic Cyan)
  const bx = 16, by = 20, bw = 32, bh = 78, r = 8;
  const bodyGrad = ctx.createLinearGradient(bx, 0, bx + bw, 0);
  bodyGrad.addColorStop(0, "#008771");
  bodyGrad.addColorStop(0.2, color);
  bodyGrad.addColorStop(0.7, "#059669");
  bodyGrad.addColorStop(1, "#047857");
  ctx.fillStyle = bodyGrad;
  drawRoundRect(ctx, bx, by, bw, bh, r);
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = "#044E43";
  ctx.stroke();

  // 3. Side Aerodynamic Wheels (Black rubber with metallic rims)
  ctx.fillStyle = "#1E293B";
  ctx.fillRect(bx - 2.5, by + 16, 3, 10);
  ctx.fillRect(bx + bw - 0.5, by + 16, 3, 10);
  ctx.fillRect(bx - 2.5, by + 54, 3, 12);
  ctx.fillRect(bx + bw - 0.5, by + 54, 3, 12);

  // 4. Panoramic Tinted Glass Windshield & Window Ribbons
  ctx.fillStyle = "#0F172A";
  drawRoundRect(ctx, bx + 3, by + 4, bw - 6, 12, 4);
  ctx.fill();

  // Glass Specular Sheen (Curved glare reflection)
  const glassGlare = ctx.createLinearGradient(bx + 4, by + 4, bx + bw - 4, by + 14);
  glassGlare.addColorStop(0, "rgba(255, 255, 255, 0.60)");
  glassGlare.addColorStop(0.5, "rgba(56, 189, 248, 0.30)");
  glassGlare.addColorStop(1, "rgba(255, 255, 255, 0.05)");
  ctx.fillStyle = glassGlare;
  drawRoundRect(ctx, bx + 4, by + 5, bw - 8, 5, 2);
  ctx.fill();

  // Side Passenger Windows
  ctx.fillStyle = "#1E293B";
  ctx.fillRect(bx + 2, by + 20, 3, 44);
  ctx.fillRect(bx + bw - 5, by + 20, 3, 44);
  // Window divider pillars
  ctx.fillStyle = "#047857";
  for (let y = by + 28; y <= by + 56; y += 9) {
    ctx.fillRect(bx + 2, y, 3, 1.5);
    ctx.fillRect(bx + bw - 5, y, 3, 1.5);
  }

  // 5. Glossy Porcelain White Roof with Dual HVAC & Battery Pods
  const rx = bx + 5, ry = by + 18, rw = bw - 10, rh = 48;
  const roofGrad = ctx.createLinearGradient(rx, 0, rx + rw, 0);
  roofGrad.addColorStop(0, "#15994a");
  roofGrad.addColorStop(0.5, "#22b85f");
  roofGrad.addColorStop(1, "#128a42");
  ctx.fillStyle = roofGrad;
  drawRoundRect(ctx, rx, ry, rw, rh, 4);
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#0b6b31";
  ctx.stroke();

  // Dual AC Unit on Roof with ventilation grilles
  ctx.fillStyle = "#0b6b31";
  drawRoundRect(ctx, rx + 2, ry + 6, rw - 4, 13, 2);
  ctx.fill();
  ctx.fillStyle = "#095a29";
  for (let gy = ry + 8; gy <= ry + 16; gy += 3) {
    ctx.fillRect(rx + 4, gy, rw - 8, 1);
  }

  // Rear Battery Pod
  ctx.fillStyle = "#0b6b31";
  drawRoundRect(ctx, rx + 2, ry + 28, rw - 4, 14, 2);
  ctx.fill();

  // 6. Front Amber Destination LED Matrix Display Board
  ctx.fillStyle = "#F59E0B";
  drawRoundRect(ctx, bx + 7, by + 1, bw - 14, 3, 1);
  ctx.fill();

  // 7. Twin High-Beam Headlights
  ctx.fillStyle = "#FEF08A";
  ctx.fillRect(bx + 3, by, 4, 2.5);
  ctx.fillRect(bx + bw - 7, by, 4, 2.5);

  // 8. Dual Aerodynamic Side Mirrors extending forward
  ctx.fillStyle = "#0F766E";
  ctx.fillRect(bx - 3.5, by + 4, 3.5, 2);
  ctx.fillRect(bx + bw, by + 4, 3.5, 2);

  // 9. Rear Red Taillight Clusters
  ctx.fillStyle = "#EF4444";
  ctx.fillRect(bx + 3, by + bh - 2, 5, 2);
  ctx.fillRect(bx + bw - 8, by + bh - 2, 5, 2);

  return ctx.getImageData(0, 0, w, h);
}

/**
 * Generates an authentic 3D DMRC Metro Train Car sprite
 * Dimensions: 48x130px (retina @2x = 24x65px map display)
 */
function create3DMetroImage(lineColor = "#F59E0B") {
  const w = 48, h = 130;
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");

  // 1. Ballast Track Shadow
  ctx.save();
  ctx.fillStyle = "rgba(15, 23, 42, 0.35)";
  drawRoundRect(ctx, 13, 12, 22, 108, 6);
  ctx.fill();
  ctx.restore();

  // 2. Streamlined Stainless Steel Carriage Body
  const mx = 14, my = 10, mw = 20, mh = 104, mr = 6;
  const steelGrad = ctx.createLinearGradient(mx, 0, mx + mw, 0);
  steelGrad.addColorStop(0, "#CBD5E1");
  steelGrad.addColorStop(0.3, "#F8FAFC");
  steelGrad.addColorStop(0.7, "#E2E8F0");
  steelGrad.addColorStop(1, "#94A3B8");

  ctx.fillStyle = steelGrad;
  drawRoundRect(ctx, mx, my, mw, mh, mr);
  ctx.fill();
  ctx.lineWidth = 1;
  ctx.strokeStyle = "#64748B";
  ctx.stroke();

  // 3. DMRC Line Color Beltline Stripe
  ctx.fillStyle = lineColor;
  ctx.fillRect(mx + 1, my + 12, 2.5, mh - 18);
  ctx.fillRect(mx + mw - 3.5, my + 12, 2.5, mh - 18);

  // 4. Front Aerodynamic Cab Windshield
  ctx.fillStyle = "#0F172A";
  drawRoundRect(ctx, mx + 2.5, my + 2, mw - 5, 9, 3);
  ctx.fill();
  // Windshield glare
  ctx.fillStyle = "rgba(255, 255, 255, 0.5)";
  ctx.fillRect(mx + 4, my + 3, mw - 8, 2.5);

  // 5. Articulated Gangway Bellows (Accordion Joint dividing train cars)
  const midY = my + mh / 2;
  ctx.fillStyle = "#1E293B";
  ctx.fillRect(mx + 1, midY - 2.5, mw - 2, 5);
  ctx.fillStyle = "#475569";
  for (let gy = midY - 2; gy <= midY + 2; gy += 1.5) {
    ctx.fillRect(mx + 2, gy, mw - 4, 0.8);
  }

  // 6. Roof HVAC Units & Pantograph Current Collector
  ctx.fillStyle = "#94A3B8";
  drawRoundRect(ctx, mx + 4, my + 16, mw - 8, 14, 2);
  ctx.fill();
  drawRoundRect(ctx, mx + 4, my + mh - 30, mw - 8, 14, 2);
  ctx.fill();

  // Roof Pantograph
  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(mx + 5, my + 23);
  ctx.lineTo(mx + mw / 2, my + 18);
  ctx.lineTo(mx + mw - 5, my + 23);
  ctx.stroke();

  // 7. Twin High-Intensity Xenon Headlights
  ctx.fillStyle = "#FFFFFF";
  ctx.fillRect(mx + 2, my, 3, 2);
  ctx.fillRect(mx + mw - 5, my, 3, 2);

  // 8. Rear Red Marker Lights
  ctx.fillStyle = "#DC2626";
  ctx.fillRect(mx + 2, my + mh - 1.5, 3, 1.5);
  ctx.fillRect(mx + mw - 5, my + mh - 1.5, 3, 1.5);

  return ctx.getImageData(0, 0, w, h);
}

function getHeading(fromCoord, toCoord) {
  const dLon = (toCoord[0] - fromCoord[0]) * Math.PI / 180;
  const lat1 = fromCoord[1] * Math.PI / 180;
  const lat2 = toCoord[1] * Math.PI / 180;
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}


// Cumulative metres along a [lon, lat] path.
function pathLengths(coords) {
  const out = [0];
  for (let i = 1; i < coords.length; i++) {
    const [lo0, la0] = coords[i - 1], [lo1, la1] = coords[i];
    const kx = 111320 * Math.cos(((la0 + la1) / 2) * Math.PI / 180);
    out.push(out[i - 1] + Math.hypot((lo1 - lo0) * kx, (la1 - la0) * 110574));
  }
  return out;
}
function pointAt(coords, cum, metres) {
  let i = 1;
  while (i < cum.length - 1 && cum[i] < metres) i++;
  const f = Math.max(0, Math.min(1, (metres - cum[i - 1]) / ((cum[i] - cum[i - 1]) || 1)));
  return [coords[i - 1][0] + (coords[i][0] - coords[i - 1][0]) * f, coords[i - 1][1] + (coords[i][1] - coords[i - 1][1]) * f];
}
function slicePath(coords, cum, metres) {
  const out = [coords[0]];
  let i = 1;
  while (i < coords.length && cum[i] <= metres) out.push(coords[i++]);
  if (i < coords.length) out.push(pointAt(coords, cum, metres));
  return out;
}

class TransitMapEngine {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.options = Object.assign({
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: [77.21, 28.62],
      zoom: 11.2,
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
    this.metroTrainTimer = null;
    this.metroLines = [];
    this.currentTheme = "day"; // Pure daylight modern UI
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
      style: {
        version: 8,
        sources: {},
        layers: [{
          id: "background",
          type: "background",
          paint: { "background-color": "#f1f5f9" }
        }]
      },
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
      this._registerSprites();
      this._setupLayers();
      this._setupInteractions();
      this.loadBasemap(); // draws any journey that arrived early once the street style is in
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

  _registerSprites() {
    if (!this.map) return;
    if (!this.map.hasImage("bus-3d-model")) {
      this.map.addImage("bus-3d-model", create3DBusImage("#0f8a3c"), { pixelRatio: 2 });
    }
    if (!this.map.hasImage("metro-3d-model")) {
      this.map.addImage("metro-3d-model", create3DMetroImage("#F59E0B"), { pixelRatio: 2 });
    }
  }

  _setupLayers() {
    const map = this.map;
    this._registerSprites();

    // 1. Google Maps Daylight Architectural Buildings (Clean light palette - Zero black polygons)
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
        minzoom: 13,
        filter: [">", ["to-number", ["get", "render_height"], 0], 0],
        paint: {
          // Taller buildings read a little cooler and darker, so the skyline has depth.
          "fill-extrusion-color": ["interpolate", ["linear"], ["to-number", ["get", "render_height"], 0],
            0, "#eef1f5", 25, "#dfe5ec", 80, "#c9d3df"],
          "fill-extrusion-height": ["interpolate", ["linear"], ["zoom"], 13, 0, 14.2, ["to-number", ["get", "render_height"], 10]],
          "fill-extrusion-base": ["to-number", ["get", "render_min_height"], 0],
          "fill-extrusion-opacity": 0.88,
          "fill-extrusion-vertical-gradient": true
        }
      }, labelLayerId);
    }
    try {
      map.setLight({ anchor: "viewport", color: "#ffffff", intensity: 0.5, position: [1.15, 210, 30] });
      map.setSky({
        "sky-color": "#a9cdf5", "horizon-color": "#e8f1fb", "fog-color": "#f4f7fb",
        "sky-horizon-blend": 0.55, "horizon-fog-blend": 0.6, "fog-ground-blend": 0.75, "atmosphere-blend": 0.6
      });
    } catch (_) { /* older engines: flat background is fine */ }

    // Sanitize any existing 2D building layers to ensure clean Google Maps daylight tones
    const styleLayers = map.getStyle().layers || [];
    styleLayers.forEach((l) => {
      if (l.id && l.id.toLowerCase().includes("building") && l.type === "fill") {
        try {
          map.setPaintProperty(l.id, "fill-color", "#E8EDF2");
          map.setPaintProperty(l.id, "fill-outline-color", "#CBD5E1");
          map.setPaintProperty(l.id, "fill-opacity", 0.70);
        } catch (_) {}
      }
    });

    // 2. Delhi Metro (DMRC) Network Layers
    if (!map.getSource("delhi-metro-source")) {
      map.addSource("delhi-metro-source", {
        type: "geojson",
        data: "/metro/network"
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
          "line-width": 8,
          "line-opacity": 0.35,
          "line-blur": 3
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
          "line-color": "#FFFFFF",
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
        minzoom: 12.0,
        filter: ["==", ["get", "type"], "station"],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            12.0, 2.5,
            14.0, ["case", ["get", "interchange"], 5.5, 4.0],
            16.0, ["case", ["get", "interchange"], 7.5, 5.5]
          ],
          "circle-color": "#FFFFFF",
          "circle-stroke-width": [
            "interpolate", ["linear"], ["zoom"],
            12.0, 1.2,
            14.0, 1.8,
            16.0, 2.4
          ],
          "circle-stroke-color": ["case", ["get", "interchange"], "#F59E0B", "#2563EB"]
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
        filter: ["==", ["get", "mode"], "bus"],
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": ["coalesce", ["get", "crowdColor"], "#1A73E8"],
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 9, 15, 18],
          "line-opacity": 0.25,
          "line-blur": 6
        }
      });
    }

    if (!map.getLayer("route-casing")) {
      map.addLayer({
        id: "route-casing",
        type: "line",
        source: "active-route-source",
        filter: ["==", ["get", "mode"], "bus"],
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#FFFFFF",
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 6.5, 15, 12],
          "line-opacity": 0.95
        }
      });
    }

    if (!map.getLayer("active-route-line")) {
      map.addLayer({
        id: "active-route-line",
        type: "line",
        source: "active-route-source",
        filter: ["==", ["get", "mode"], "bus"],
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": ["coalesce", ["get", "crowdColor"], "#1A73E8"],
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 4, 15, 8],
          "line-opacity": 1.0
        }
      });
    }

    if (!map.getLayer("route-walk")) {
      map.addLayer({
        id: "route-walk",
        type: "line",
        source: "active-route-source",
        filter: ["==", ["get", "mode"], "walk"],
        layout: { "line-join": "round", "line-cap": "round" },
        paint: { "line-color": "#5f6368", "line-width": 3, "line-dasharray": [0.6, 1.6] }
      });
    }

    // Intermediate Waypoint Stop Dots
    if (!map.getSource("route-stops-source")) {
      map.addSource("route-stops-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
    }

    if (!map.getLayer("route-stops-circles")) {
      map.addLayer({
        id: "route-stops-circles",
        type: "circle",
        source: "route-stops-source",
        minzoom: 12.5,
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            10, 2.5,
            13, 3.5,
            16, 5.0
          ],
          "circle-color": "#FFFFFF",
          "circle-stroke-width": 1.8,
          "circle-stroke-color": "#1E3A8A"
        }
      });
    }

    // 4. Forward Headlight Illumination
    if (!map.getSource("preview-headlights")) {
      map.addSource("preview-headlights", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "preview-headlight-throw",
        type: "fill",
        source: "preview-headlights",
        paint: {
          "fill-color": "#c5e7ff",
          "fill-opacity": ["get", "opacity"],
          "fill-antialias": false
        },
      });
    }

    // 5. Live Fleet Streaming Across Delhi (3D Models - Zero Green Dots)
    if (!map.getSource("live-fleet-source")) {
      map.addSource("live-fleet-source", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] }
      });
    }

    if (!map.getLayer("live-fleet-layer")) {
      map.addLayer({
        id: "live-fleet-layer",
        type: "symbol",
        source: "live-fleet-source",
        layout: {
          "visibility": this.liveFleetVisible ? "visible" : "none",
          "icon-image": ["case", ["==", ["get", "mode"], "metro"], "metro-3d-model", "bus-3d-model"],
          "icon-size": [
            "interpolate", ["linear"], ["zoom"],
            10, 0.28,
            12, 0.38,
            14, 0.55,
            16, 0.85
          ],
          "icon-rotate": ["get", "bearing"],
          "icon-rotation-alignment": "map",
          "icon-pitch-alignment": "map",
          "icon-allow-overlap": ["step", ["zoom"], false, 13, true],
          "icon-ignore-placement": false,
          "icon-padding": 2
        }
      });
    }

    // 6. Active Trip Moving 3D Vehicle Marker (DTC Electric Bus with 3D Chassis)
    if (!this.vehicleMarker) {
      const el = document.createElement("div");
      el.className = "transit-vehicle-marker";
      el.innerHTML = `
        <div class="vehicle-hud-speed">Preview</div>
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

      this.vehicleMarker = new maplibregl.Marker({ element: el, anchor: "center", offset: [0, -30] });

      // Origin Marker (Google Blue Circle)
      const startEl = document.createElement("div");
      startEl.className = "gmaps-origin-marker";
      startEl.innerHTML = `<div class="origin-inner-dot"></div>`;
      this.startMarker = new maplibregl.Marker({ element: startEl, anchor: "center" });

      // Destination Marker (Reference 1 Orange Teardrop Pin with ETA)
      const destEl = document.createElement("div");
      destEl.className = "gmaps-dest-marker";
      destEl.innerHTML = `
        <div class="dest-pin-ripple"></div>
        <div class="dest-eta-pin">
          <span class="dest-pin-time" id="dest-pin-time">11</span>
          <span class="dest-pin-unit">MIN</span>
        </div>
        <div class="dest-pin-tail"></div>
      `;
      this.endMarker = new maplibregl.Marker({ element: destEl, anchor: "bottom" });
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
        button.className = "popup-btn" + (field === "destination" ? " primary" : "");
        button.textContent = label;
        button.addEventListener("click", () => {
          window.setPlannerStop?.(field, stopName, coords);
          popup.remove();
        });
        actions.append(button);
      }
      content.append(actions);
    };

    map.on("click", "metro-stations-halo", ({ features }) => {
      if (!features || !features.length) return;
      const p = features[0].properties;
      showPopup(features[0].geometry.coordinates.slice(), p.name, [
        p.interchange === "true" || p.interchange === true ? "Metro interchange" : "Metro station",
        (() => { try { const l = JSON.parse(p.lines || "[]"); return l.length ? l.join(", ") : "Delhi Metro"; } catch { return "Delhi Metro"; } })(),
      ], p.name);
    });

    const fleetPopup = ({ features }) => {
      if (!features || !features.length) return;
      const p = features[0].properties;
      showPopup(features[0].geometry.coordinates.slice(), `Bus ${p.vehicle_id}`, [
        `Route ${p.route}`,
        `GPS reported ${p.age} s ago`,
      ]);
    };
    map.on("click", "route-stops-circles", ({ features }) => {
      if (!features || !features.length) return;
      showPopup(features[0].geometry.coordinates.slice(), features[0].properties.name || "Stop", ["A stop on your bus"]);
    });
    map.on("click", "live-fleet-layer", fleetPopup);
    map.on("click", "live-fleet-hit", fleetPopup);

    ["metro-stations-halo", "live-fleet-layer", "live-fleet-hit", "route-stops-circles"].forEach((layerId) => {
      map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
    });
  }

  setJourney(journey) {
    if (!this.isLoaded) {
      this._pendingJourney = journey;
      return;
    }
    this._clearRoute();
    if (!journey || !journey.legs || !journey.legs.length) return;

    this.currentJourney = journey;
    const allCoords = [];
    const stopFeatures = [];

    journey.legs.forEach((leg, legIdx) => {
      const isLegMetro = leg.mode === "metro";
      const pts = leg.points || [];
      const legCoords = pts.map((p) => [parseFloat(p.lon), parseFloat(p.lat)]);
      allCoords.push(...legCoords);

      const stops = leg.stops || [];
      stops.forEach((p, pIdx) => {
        const isStart = legIdx === 0 && pIdx === 0;
        const isEnd = legIdx === journey.legs.length - 1 && pIdx === stops.length - 1;
        if (!isStart && !isEnd) {
          stopFeatures.push({
            type: "Feature",
            properties: { id: p.id, name: p.name },
            geometry: { type: "Point", coordinates: [parseFloat(p.lon), parseFloat(p.lat)] }
          });
        }
      });
    });

    if (!allCoords.length) return;
    this.routeCoords = allCoords;

    const routeFeatures = journey.legs.filter((leg) => (leg.points || []).length > 1).map((leg) => ({
      type: "Feature",
      properties: { mode: leg.mode },
      geometry: { type: "LineString", coordinates: leg.points.map((p) => [+p.lon, +p.lat]) }
    }));
    this._revealRoute(routeFeatures);
    this.busCoords = journey.legs.filter((leg) => leg.mode === "bus")
      .flatMap((leg) => leg.points.map((p) => [+p.lon, +p.lat]));

    this.map.getSource("route-stops-source").setData({
      type: "FeatureCollection",
      features: stopFeatures
    });

    const startCoord = this.routeCoords[0];
    const endCoord = this.routeCoords[this.routeCoords.length - 1];

    this.startMarker.setLngLat(startCoord).addTo(this.map);
    this.endMarker.setLngLat(endCoord).addTo(this.map);

    // Labelled pins where you board, change and get off.
    this._keyMarkers = (journey.keyStops || []).map((k) => {
      const pin = document.createElement("div");
      pin.className = "key-stop-pin " + k.kind;
      const label = document.createElement("span");
      label.textContent = k.label;
      pin.append(label);
      const side = k.kind === "alight"; // sits left of the stop so it never covers the destination pin
      return new maplibregl.Marker({ element: pin, anchor: side ? "right" : "bottom", offset: side ? [-16, 0] : [0, -6] })
        .setLngLat([+k.lon, +k.lat]).addTo(this.map);
    });

    const pinTime = document.getElementById("dest-pin-time");
    if (pinTime) pinTime.textContent = Math.round(journey.minutes || 10);

    const navBanner = document.getElementById("hud-nav-banner");
    if (navBanner) navBanner.hidden = false;
    if (journey.banner) {
      document.getElementById("hud-next-stop").textContent = journey.banner.title;
      document.getElementById("hud-subtext").textContent = journey.banner.sub;
    }

    const bottomEta = document.getElementById("hud-bottom-eta");
    if (bottomEta) {
      bottomEta.hidden = false;
      const etaMin = document.getElementById("hud-eta-min");
      const etaDist = document.getElementById("hud-eta-dist");
      const etaArr = document.getElementById("hud-eta-arrival");
      const etaCrowd = document.getElementById("hud-eta-crowd");
      if (etaMin) etaMin.textContent = Math.round(journey.minutes || 10);
      if (etaDist) etaDist.textContent = `${(journey.km ?? 0).toFixed(1)} km`;
      if (etaArr) {
        const arrDate = new Date(journey.arrival);
        etaArr.textContent = isNaN(arrDate) ? "--:--" : arrDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: true });
      }
      if (etaCrowd) etaCrowd.textContent = journey.badge || "";
    }

    const btnRecenter = document.getElementById("btn-recenter");
    if (btnRecenter) btnRecenter.hidden = false;

    const bounds = this.routeCoords.reduce(
      (b, coord) => b.extend(coord),
      new maplibregl.LngLatBounds(startCoord, startCoord)
    );

    const narrow = this.map.getContainer().clientWidth < 700;
    this.map.fitBounds(bounds, {
      padding: narrow ? { top: 90, bottom: 110, left: 30, right: 30 } : { top: 90, bottom: 90, left: 420, right: 80 },
      pitch: this.is3D ? 52 : 0,
      duration: 1200,
      maxZoom: 15.5
    });

    this.animProgress = 0;
    this._startVehicleAnimation();
  }

  // Draw the route on from start to end (one short sweep; instant with reduced motion).
  _revealRoute(features) {
    const source = this.map.getSource("active-route-source");
    cancelAnimationFrame(this._revealId);
    const lengths = features.map((f) => pathLengths(f.geometry.coordinates));
    const total = lengths.reduce((s, l) => s + l[l.length - 1], 0);
    const show = (fraction) => {
      let budget = fraction * total;
      source.setData({ type: "FeatureCollection", features: features.map((f, i) => {
        const cum = lengths[i], len = cum[cum.length - 1];
        const coords = budget >= len ? f.geometry.coordinates : slicePath(f.geometry.coordinates, cum, Math.max(0, budget));
        budget -= len;
        return { ...f, geometry: { type: "LineString", coordinates: coords } };
      }).filter((f) => f.geometry.coordinates.length > 1) });
    };
    if (this.reducedMotion.matches || !total) return show(1);
    const start = performance.now(), dur = 900;
    const step = (now) => {
      const t = Math.min(1, (now - start) / dur);
      show(1 - Math.pow(1 - t, 3));
      if (t < 1) this._revealId = requestAnimationFrame(step);
    };
    this._revealId = requestAnimationFrame(step);
  }

  _clearRoute() {
    (this._keyMarkers || []).forEach((m) => m.remove());
    this._keyMarkers = [];
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
    this.routeCoords = [];
    this.busCoords = [];
    this.preview = null;
    cancelAnimationFrame(this._revealId);
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
    if (this.animId) {
      cancelAnimationFrame(this.animId);
      this.animId = null;
    }
    const path = this.busCoords && this.busCoords.length > 1 ? this.busCoords : null;
    if (!path) { this.vehicleMarker?.remove(); return; }

    const cum = pathLengths(path);
    const total = cum[cum.length - 1];
    // A short, readable sweep: about 2.2 s per km, between 14 s and 45 s for the whole ride.
    const durationMs = Math.min(45000, Math.max(14000, total / 1000 * 2200));
    let last = performance.now();
    let heading = null;
    this.vehicleMarker.setLngLat(path[0]).addTo(this.map);

    const render = (now) => {
      const dt = Math.min(0.1, (now - last) / 1000);
      last = now;
      if (!this.previewPaused && !this.reducedMotion.matches) this.animProgress += (dt * 1000) / durationMs;
      if (this.animProgress >= 1) this.animProgress = 0;

      const at = this.animProgress * total;
      let i = 1;
      while (i < cum.length - 1 && cum[i] < at) i++;
      const seg = cum[i] - cum[i - 1] || 1;
      const f = Math.max(0, Math.min(1, (at - cum[i - 1]) / seg));
      const p0 = path[i - 1], p1 = path[i];
      const coord = [p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f];
      // Look a little ahead so the bus turns smoothly instead of snapping at each shape point.
      const ahead = pointAt(path, cum, Math.min(total, at + 25));
      const target = (ahead[0] === coord[0] && ahead[1] === coord[1]) ? getHeading(p0, p1) : getHeading(coord, ahead);
      heading = heading === null ? target : heading + (((target - heading + 540) % 360) - 180) * Math.min(1, dt * 6);
      heading = (heading + 360) % 360;
      this._previewHeading = heading;
      this.preview = { coord, heading };

      this.vehicleMarker.setLngLat(coord);
      if (!this.fleet3D) {
        const body = this.vehicleMarker.getElement().querySelector(".vehicle-3d-wrapper");
        if (body) body.style.transform = `rotate(${heading - this.map.getBearing()}deg) perspective(140px) rotateX(${Math.round(this.map.getPitch() * 0.75)}deg)`;
      }
      this._paintHeadlights(coord, heading);
      if (this.followMode) this._followVehicle(coord, heading, dt);
      this.map.triggerRepaint();
      this.animId = requestAnimationFrame(render);
    };
    this.animId = requestAnimationFrame(render);
  }

  _paintHeadlights([lng, lat], heading) {
    const source = this.map.getSource("preview-headlights");
    if (!source) return;
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
      for (const [back, opacity] of [[12, .18], [23, .10], [36, .05], [50, .02]]) {
        const ring = [lamp(front, -1), lamp(back, -1), lamp(back, 1), lamp(front, 1)];
        ring.push(ring[0]);
        features.push({
          type: "Feature",
          properties: { opacity },
          geometry: { type: "Polygon", coordinates: [ring] }
        });
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
    const target = [
      position[0] + Math.sin(angle) * offset / Math.cos(position[1] * Math.PI / 180),
      position[1] + Math.cos(angle) * offset
    ];
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
    const fleetLayer = this.fleet3D ? "live-fleet-hit" : "live-fleet-layer";
    if (this.map?.getLayer(fleetLayer)) this.map.setLayoutProperty(fleetLayer, "visibility", visibility);
    this.map?.triggerRepaint();
    if (this.liveFleetVisible) {
      await this.refreshLiveFleet();
      if (!this.liveFleetTimer) {
        this.liveFleetTimer = setInterval(() => this.refreshLiveFleet(), 15000);
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
      const res = await fetch("/live/vehicles");
      const vehicleList = res.ok ? await res.json() : [];
      if (!this.liveFleetVisible) return;

      if (this.map && this.map.getSource("live-fleet-source")) {
        this.prevVehicleCoords = this.prevVehicleCoords || new Map();
        const nowS = Date.now() / 1000;
        const features = vehicleList.map((p) => {
          // Heading comes from the bus's own last GPS points; a bus not seen moving keeps its last heading.
          const bearing = p.heading ?? this.prevVehicleCoords.get(p.id) ?? 0;
          this.prevVehicleCoords.set(p.id, bearing);

          return {
            type: "Feature",
            properties: {
              vehicle_id: p.id,
              route: p.route,
              age: Math.max(0, Math.round(nowS - p.ts)),
              bearing: Math.round(bearing),
              mode: "bus"
            },
            geometry: {
              type: "Point",
              coordinates: [p.lon, p.lat]
            }
          };
        });

        this.map.getSource("live-fleet-source").setData({
          type: "FeatureCollection",
          features
        });
        this.onFleet?.(vehicleList);

        const pillText = document.getElementById("fleet-count-text");
        if (pillText) {
          pillText.textContent = `${features.length.toLocaleString("en-IN")} buses live`;
        }
      }
    } catch (e) {
      console.warn("Live fleet poll failed:", e);
    }
  }

  // Called by buses3d.js once three.js draws the fleet: keep an invisible layer for taps and hide the 2D icons.
  use3DFleet() {
    const map = this.map;
    this.fleet3D = true;
    if (map.getLayer("live-fleet-layer")) map.setLayoutProperty("live-fleet-layer", "visibility", "none");
    if (!map.getLayer("live-fleet-hit")) {
      map.addLayer({
        id: "live-fleet-hit", type: "circle", source: "live-fleet-source",
        layout: { visibility: this.liveFleetVisible ? "visible" : "none" },
        paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 5, 16, 14], "circle-opacity": 0 }
      });
    }
  }

  toggle3D() {
    this.is3D = !this.is3D;
    this.map.easeTo({
      pitch: this.is3D ? 52 : 0,
      bearing: this.is3D ? -16 : 0,
      duration: 1000
    });
    return this.is3D;
  }

  toggleFollow() {
    if (!this.followMode && this.vehicleMarker) {
      const { lng, lat } = this.vehicleMarker.getLngLat();
      this.map.stop();
      this._followVehicle([lng, lat], this._previewHeading ?? this.map.getBearing(), 0, true);
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

  setSpeeds(geojson) {
    const map = this.map;
    this._speeds = geojson;
    if (!map || !this.isLoaded) return;
    if (!map.getSource("speeds-source")) {
      map.addSource("speeds-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "speeds-layer", type: "line", source: "speeds-source",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 2, 14, 5],
          "line-color": ["step", ["get", "kmh"], "#d93025", 12, "#f9ab00", 20, "#7d8fa3"],
          "line-opacity": 0.9
        }
      }, map.getLayer("route-glow") ? "route-glow" : undefined);
    }
    map.getSource("speeds-source").setData(geojson || { type: "FeatureCollection", features: [] });
  }

  clearJourney() {
    this._clearRoute();
  }

  async loadBasemap() {
    this._styleRequest?.abort();
    const request = new AbortController();
    this._styleRequest = request;
    let style;
    try {
      const response = await fetch("https://tiles.openfreemap.org/styles/liberty", { signal: request.signal });
      if (!response.ok) throw new Error("Basemap unavailable");
      style = await response.json();
      if (style.sources && style.sources.openmaptiles) {
        const metadata = await fetch(style.sources.openmaptiles.url, { signal: request.signal });
        if (!metadata.ok) throw new Error("Basemap unavailable");
        const { url, ...source } = style.sources.openmaptiles;
        style.sources.openmaptiles = { ...await metadata.json(), ...source };
      }
    } catch {
      if (request.signal.aborted) return;
      const statusEl = document.getElementById("map-source-status");
      if (statusEl) statusEl.textContent = "Street basemap unavailable";
      style = {
        version: 8,
        sources: {},
        layers: [{
          id: "background",
          type: "background",
          paint: { "background-color": "#e7eeeb" }
        }]
      };
    }
    if (request.signal.aborted) return;
    if (style.sources && style.sources.openmaptiles) {
      const statusEl = document.getElementById("map-source-status");
      if (statusEl) statusEl.textContent = "";
    }
    if (this._styleLoaded) this.map.off("style.load", this._styleLoaded);
    this._styleLoaded = () => {
      if (request.signal.aborted) return;
      this._registerSprites();
      this._setupLayers();
      this.isLoaded = true;
      const journey = this._pendingJourney || this.currentJourney;
      this._pendingJourney = null;
      if (journey) this.setJourney(journey);
      if (this.liveFleetVisible) this.refreshLiveFleet();
      if (this._speeds) this.setSpeeds(this._speeds);
      (this.styleHooks || []).forEach((hook) => hook(this.map));
    };
    this.map.once("style.load", this._styleLoaded);
    this.map.setStyle(style, { diff: false });
  }

  async setTheme(theme) {
    // Pure Daylight Mode is permanent.
    this.currentTheme = "day";
    await this.loadBasemap();
  }
}
