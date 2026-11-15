/**
 * Delhi Transit 3D God's Eye Visualizer
 * Inspired by Bilawal Sidhu, Apple Keynote, and Waymo/Google Maps 3D Navigation.
 * Standards: Hallmark Anti-Slop, Emil Kowalski Craft, 60 FPS WebGL Engine.
 */
"use strict";

class GodsEye3D {
  constructor(container, options = {}) {
    this.container = container;
    this.options = Object.assign({
      mode: "overview", // "overview" (God's Eye) | "chase" (Follow Bus)
      speedMultiplier: 1.0,
      autoPlay: true,
      timeOfDay: "day",
    }, options);

    this.isSupported = this._checkWebGL();
    if (!this.isSupported) {
      console.warn("WebGL not supported; falling back to 2D view.");
      return;
    }

    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.controls = null;
    this.busMesh = null;
    this.pinMesh = null;
    this.originRing = null;
    this.routeLine = null;
    this.routeTexture = null;
    this.roadMesh = null;
    this.stopMarkersGroup = null;
    this.cityGroup = null;
    this.liveVehiclesGroup = null;

    this.journey = null;
    this.curve = null;
    this.routeLength = 0;
    this.progress = 0; // 0.0 to 1.0 along route
    this.isPlaying = true;
    this.stopsWithT = [];
    this.currentStopIndex = -1;

    this.centerLat = 28.6139;
    this.centerLon = 77.2090;
    this.scaleFactor = 5000; // Calibrated dynamically per journey

    this.reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.animId = null;
    this.lastTime = performance.now();

    this._initScene();
    this._setupEvents();
  }

  _checkWebGL() {
    try {
      const canvas = document.createElement("canvas");
      return !!(window.WebGLRenderingContext && (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")));
    } catch (e) {
      return false;
    }
  }

  _initScene() {
    const width = this.container.clientWidth || 600;
    const height = this.container.clientHeight || 450;

    // 1. Scene & Atmospheric Fog
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xF4F0EA);
    this.scene.fog = new THREE.FogExp2(0xF4F0EA, 0.0014);

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 4000);
    this.camera.position.set(0, 110, 120);

    // 3. Renderer with high performance & soft shadow maps
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.domElement.className = "gods-eye-canvas";
    this.container.appendChild(this.renderer.domElement);

    // 4. OrbitControls
    if (typeof THREE.OrbitControls !== "undefined") {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.06;
      this.controls.maxPolarAngle = Math.PI / 2 - 0.06;
      this.controls.minDistance = 15;
      this.controls.maxDistance = 500;
    }

    // 5. Lighting System (Warm Keynote daylight)
    this.ambientLight = new THREE.AmbientLight(0xFFFFFF, 0.78);
    this.scene.add(this.ambientLight);

    this.sunLight = new THREE.DirectionalLight(0xFFF7ED, 0.88);
    this.sunLight.position.set(90, 180, 110);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.sunLight.shadow.camera.near = 10;
    this.sunLight.shadow.camera.far = 500;
    const d = 120;
    this.sunLight.shadow.camera.left = -d;
    this.sunLight.shadow.camera.right = d;
    this.sunLight.shadow.camera.top = d;
    this.sunLight.shadow.camera.bottom = -d;
    this.sunLight.shadow.bias = -0.0004;
    this.scene.add(this.sunLight);

    this.hemiLight = new THREE.HemisphereLight(0xE0F2FE, 0xE2E8F0, 0.38);
    this.scene.add(this.hemiLight);

    // 6. Groups
    this.cityGroup = new THREE.Group();
    this.scene.add(this.cityGroup);
    this._buildStylizedEnvironment();

    this.stopMarkersGroup = new THREE.Group();
    this.scene.add(this.stopMarkersGroup);

    this.busMesh = this._createProceduralBus();
    this.busMesh.visible = false;
    this.scene.add(this.busMesh);

    this.pinMesh = this._createDestinationPin("4 MIN");
    this.pinMesh.visible = false;
    this.scene.add(this.pinMesh);

    this.originRing = this._createOriginBeacon();
    this.originRing.visible = false;
    this.scene.add(this.originRing);

    this.liveVehiclesGroup = new THREE.Group();
    this.scene.add(this.liveVehiclesGroup);

    // Start render loop
    this._animate = this._animate.bind(this);
    this.animId = requestAnimationFrame(this._animate);
  }

  _setupEvents() {
    this._resizeHandler = () => {
      if (!this.container || !this.renderer) return;
      const width = this.container.clientWidth;
      const height = this.container.clientHeight;
      if (!width || !height) return;
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(width, height);
    };
    window.addEventListener("resize", this._resizeHandler);

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) {
        this.isPlaying = false;
      } else {
        this.isPlaying = true;
        this.lastTime = performance.now();
      }
    });
  }

  // --- STYLIZED PROCEDURAL ENVIRONMENT (Reference 1 & 3) ---
  _buildStylizedEnvironment() {
    this.cityGroup.clear();

    // 1. Vast Base Ground (Eggshell canvas tone)
    const groundGeo = new THREE.PlaneGeometry(2400, 2400);
    const groundMat = new THREE.MeshLambertMaterial({ color: 0xF4F0EA });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.1;
    ground.receiveShadow = true;
    this.cityGroup.add(ground);

    // 2. Subtle Coordinate Grid Lines
    const gridHelper = new THREE.GridHelper(1200, 120, 0xE4DFD6, 0xEDE8E1);
    gridHelper.position.y = 0;
    this.cityGroup.add(gridHelper);

    // 3. Yamuna River Ribbon (Teal-cyan waterway, Reference 1)
    const riverCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(120, 0.05, -300),
      new THREE.Vector3(90, 0.05, -150),
      new THREE.Vector3(75, 0.05, 0),
      new THREE.Vector3(105, 0.05, 160),
      new THREE.Vector3(130, 0.05, 320),
    ]);
    const riverGeo = new THREE.TubeGeometry(riverCurve, 64, 16, 4, false);
    riverGeo.scale(1, 0.02, 1);
    const riverMat = new THREE.MeshLambertMaterial({
      color: 0x4EA8B6,
      transparent: true,
      opacity: 0.94,
    });
    const river = new THREE.Mesh(riverGeo, riverMat);
    river.position.y = 0.06;
    river.receiveShadow = true;
    this.cityGroup.add(river);

    // 4. Stylized Sage Green Park Parcels (Reference 1)
    const parkMat = new THREE.MeshLambertMaterial({ color: 0xCDE4B8 });
    const parkConfigs = [
      { x: -55, z: -60, w: 65, h: 50, r: 8 },
      { x: 35, z: -110, w: 55, h: 40, r: 6 },
      { x: -80, z: 75, w: 70, h: 60, r: 10 },
      { x: 25, z: 120, w: 60, h: 48, r: 7 },
    ];
    for (const p of parkConfigs) {
      const parkShape = new THREE.Shape();
      const hw = p.w / 2;
      const hh = p.h / 2;
      parkShape.moveTo(-hw + p.r, -hh);
      parkShape.lineTo(hw - p.r, -hh);
      parkShape.quadraticCurveTo(hw, -hh, hw, -hh + p.r);
      parkShape.lineTo(hw, hh - p.r);
      parkShape.quadraticCurveTo(hw, hh, hw - p.r, hh);
      parkShape.lineTo(-hw + p.r, hh);
      parkShape.quadraticCurveTo(-hw, hh, -hw, hh - p.r);
      parkShape.lineTo(-hw, -hh + p.r);
      parkShape.quadraticCurveTo(-hw, -hh, -hw + p.r, -hh);

      const parkGeo = new THREE.ShapeGeometry(parkShape);
      const parkMesh = new THREE.Mesh(parkGeo, parkMat);
      parkMesh.rotation.x = -Math.PI / 2;
      parkMesh.position.set(p.x, 0.02, p.z);
      parkMesh.receiveShadow = true;
      this.cityGroup.add(parkMesh);
    }

    // 5. Stylized Low-Poly City Blocks (Porcelain-tinted 3D buildings)
    const blockMat = new THREE.MeshLambertMaterial({ color: 0xFDFBF7 });
    const blockEdgeMat = new THREE.LineBasicMaterial({ color: 0xE2DDD4 });
    const blockCoords = [
      { x: -38, z: -25, w: 24, l: 32, h: 10 },
      { x: -70, z: -20, w: 20, l: 26, h: 16 },
      { x: -28, z: 35, w: 30, l: 24, h: 12 },
      { x: 52, z: -30, w: 22, l: 26, h: 14 },
      { x: 45, z: 45, w: 26, l: 30, h: 18 },
      { x: -60, z: 135, w: 32, l: 26, h: 9 },
    ];
    for (const b of blockCoords) {
      const bGeo = new THREE.BoxGeometry(b.w, b.h, b.l);
      const bMesh = new THREE.Mesh(bGeo, blockMat);
      bMesh.position.set(b.x, b.h / 2, b.z);
      bMesh.castShadow = true;
      bMesh.receiveShadow = true;
      this.cityGroup.add(bMesh);

      const edges = new THREE.EdgesGeometry(bGeo);
      const wireframe = new THREE.LineSegments(edges, blockEdgeMat);
      wireframe.position.copy(bMesh.position);
      this.cityGroup.add(wireframe);
    }

    // 6. Miniature Low-Poly Street Trees (Bilawal Sidhu / Keynote detail)
    const trunkMat = new THREE.MeshLambertMaterial({ color: 0x8C7862 });
    const foliageMat = new THREE.MeshLambertMaterial({ color: 0x86D472 });
    const trunkGeo = new THREE.CylinderGeometry(0.3, 0.4, 2.2, 6);
    const foliageGeo = new THREE.DodecahedronGeometry(1.4, 0);

    const treePositions = [
      [-48, -48], [-42, -52], [-36, -56],
      [28, -98], [32, -102], [36, -106],
      [-72, 62], [-66, 68], [-60, 74],
      [18, 108], [24, 114], [30, 118],
    ];
    for (const [tx, tz] of treePositions) {
      const tree = new THREE.Group();
      tree.position.set(tx, 0, tz);

      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.position.y = 1.1;
      trunk.castShadow = true;
      tree.add(trunk);

      const foliage = new THREE.Mesh(foliageGeo, foliageMat);
      foliage.position.y = 2.8;
      foliage.castShadow = true;
      tree.add(foliage);

      this.cityGroup.add(tree);
    }
  }

  // --- PROCEDURAL 3D DTC ELECTRIC BUS MODEL (Reference 1 & 2) ---
  // Convention: +Z is FRONT (heading angle = atan2(dx, dz)), -Z is REAR
  _createProceduralBus() {
    const bus = new THREE.Group();
    bus.rotation.order = "YXZ"; // Yaw first, then Pitch, then Roll

    // 1. Lower Body (Teal / DTC Electric Green)
    const bodyGeo = new THREE.BoxGeometry(3.2, 1.4, 7.5);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x00A389,
      roughness: 0.35,
      metalness: 0.15,
    });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 1.1;
    body.castShadow = true;
    body.receiveShadow = true;
    bus.add(body);

    // 2. Glossy Porcelain Roof with mini AC pod
    const roofGeo = new THREE.BoxGeometry(3.1, 0.5, 7.3);
    const roofMat = new THREE.MeshStandardMaterial({ color: 0xFCFBF8, roughness: 0.2 });
    const roof = new THREE.Mesh(roofGeo, roofMat);
    roof.position.y = 2.1;
    roof.castShadow = true;
    bus.add(roof);

    const acPodGeo = new THREE.BoxGeometry(1.8, 0.35, 2.8);
    const acPod = new THREE.Mesh(acPodGeo, roofMat);
    acPod.position.set(0, 2.5, -0.4); // Towards rear
    bus.add(acPod);

    // 3. Tinted Panoramic Glass Band
    const glassGeo = new THREE.BoxGeometry(3.24, 0.8, 6.9);
    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x1E293B,
      roughness: 0.1,
      metalness: 0.8,
      transparent: true,
      opacity: 0.88,
    });
    const glass = new THREE.Mesh(glassGeo, glassMat);
    glass.position.y = 1.7;
    bus.add(glass);

    // 4. Glowing Front Destination Board (+Z is FRONT)
    const signGeo = new THREE.PlaneGeometry(2.0, 0.4);
    const signMat = new THREE.MeshBasicMaterial({ color: 0xFDE047 });
    const sign = new THREE.Mesh(signGeo, signMat);
    sign.position.set(0, 2.05, 3.77);
    bus.add(sign);

    // 5. Headlights & Forward Volumetric Beam Cones (+Z is FRONT)
    const lampMat = new THREE.MeshBasicMaterial({ color: 0xFFFBEB });
    for (const side of [-1.1, 1.1]) {
      const lampGeo = new THREE.BoxGeometry(0.35, 0.25, 0.1);
      const lamp = new THREE.Mesh(lampGeo, lampMat);
      lamp.position.set(side, 0.9, 3.77);
      bus.add(lamp);

      // Light beam cone onto asphalt ahead
      const beamGeo = new THREE.ConeGeometry(1.6, 7.0, 16, 1, true);
      const beamMat = new THREE.MeshBasicMaterial({
        color: 0xFEF08A,
        transparent: true,
        opacity: 0.24,
        side: THREE.DoubleSide,
      });
      const beam = new THREE.Mesh(beamGeo, beamMat);
      beam.rotation.x = Math.PI / 2 - 0.12;
      beam.position.set(side, 0.7, 7.2);
      bus.add(beam);
    }

    // 6. Red Taillights (-Z is REAR)
    const tailMat = new THREE.MeshBasicMaterial({ color: 0xEF4444 });
    for (const side of [-1.1, 1.1]) {
      const tail = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.28, 0.1), tailMat);
      tail.position.set(side, 1.0, -3.77);
      bus.add(tail);
    }

    // 7. Rotating Rubber Wheels
    this.wheels = [];
    const wheelGeo = new THREE.CylinderGeometry(0.65, 0.65, 0.4, 16);
    const wheelMat = new THREE.MeshLambertMaterial({ color: 0x1E293B });
    const hubMat = new THREE.MeshBasicMaterial({ color: 0x94A3B8 });
    const wheelPositions = [
      [-1.5, 0.65, 2.4],  // Front left
      [1.5, 0.65, 2.4],   // Front right
      [-1.5, 0.65, -2.4], // Rear left
      [1.5, 0.65, -2.4],  // Rear right
    ];
    for (const [wx, wy, wz] of wheelPositions) {
      const wheelGroup = new THREE.Group();
      wheelGroup.position.set(wx, wy, wz);

      const tire = new THREE.Mesh(wheelGeo, wheelMat);
      tire.rotation.z = Math.PI / 2;
      tire.castShadow = true;
      wheelGroup.add(tire);

      const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 0.42, 8), hubMat);
      hub.rotation.z = Math.PI / 2;
      wheelGroup.add(hub);

      bus.add(wheelGroup);
      this.wheels.push(tire);
    }

    // 8. Interior Cabin Glow (Crowdedness Indicator)
    this.cabinLight = new THREE.PointLight(0x10B981, 1.3, 14);
    this.cabinLight.position.set(0, 1.6, 0);
    bus.add(this.cabinLight);

    // Drop shadow decal under vehicle
    const shadowGeo = new THREE.PlaneGeometry(3.8, 8.5);
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x000000,
      transparent: true,
      opacity: 0.28,
    });
    const dropShadow = new THREE.Mesh(shadowGeo, shadowMat);
    dropShadow.rotation.x = -Math.PI / 2;
    dropShadow.position.y = 0.04;
    bus.add(dropShadow);

    // Radar Ping Locator Beacon
    const pingGeo = new THREE.RingGeometry(2.4, 4.0, 32);
    const pingMat = new THREE.MeshBasicMaterial({
      color: 0x2DD4BF,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
    });
    this.busPing = new THREE.Mesh(pingGeo, pingMat);
    this.busPing.rotation.x = -Math.PI / 2;
    this.busPing.position.y = 0.06;
    bus.add(this.busPing);

    return bus;
  }

  // --- FLOATING "4 MIN" DESTINATION PIN (Reference 1 & 3) ---
  _createDestinationPin(label = "4 MIN") {
    const group = new THREE.Group();

    // 1. Vertical Anchor Stem
    const stemGeo = new THREE.CylinderGeometry(0.22, 0.22, 10, 8);
    const stemMat = new THREE.MeshBasicMaterial({ color: 0xE05A2B });
    const stem = new THREE.Mesh(stemGeo, stemMat);
    stem.position.y = 5.0;
    group.add(stem);

    // 2. High-Res Canvas Badge Texture (Circular Orange Bubble)
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    ctx.beginPath();
    ctx.arc(256, 256, 232, 0, Math.PI * 2);
    ctx.fillStyle = "#FF5722";
    ctx.fill();
    ctx.lineWidth = 26;
    ctx.strokeStyle = "#FFFFFF";
    ctx.stroke();

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#FFFFFF";
    ctx.font = "900 170px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    ctx.fillText("4", 256, 192);
    ctx.font = "800 80px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
    ctx.fillText("MIN", 256, 336);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const pinGeo = new THREE.PlaneGeometry(11, 11);
    const pinMat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, side: THREE.DoubleSide });

    this.pinBadge = new THREE.Mesh(pinGeo, pinMat);
    this.pinBadge.position.y = 13.5;
    group.add(this.pinBadge);

    // 3. Drop Shadow Decal on Road Surface
    const shadowGeo = new THREE.CircleGeometry(4.0, 32);
    const shadowMat = new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.24 });
    this.pinShadow = new THREE.Mesh(shadowGeo, shadowMat);
    this.pinShadow.rotation.x = -Math.PI / 2;
    this.pinShadow.position.y = 0.05;
    group.add(this.pinShadow);

    return group;
  }

  // --- ORIGIN DEPARTURE BEACON ---
  _createOriginBeacon() {
    const group = new THREE.Group();

    const ringGeo = new THREE.RingGeometry(2.4, 4.0, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x10B981, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.08;
    group.add(ring);

    const dotGeo = new THREE.CircleGeometry(1.8, 24);
    const dotMat = new THREE.MeshBasicMaterial({ color: 0x059669 });
    const dot = new THREE.Mesh(dotGeo, dotMat);
    dot.rotation.x = -Math.PI / 2;
    dot.position.y = 0.09;
    group.add(dot);

    return group;
  }

  // --- DIRECTIONAL CHEVRON ROUTE TEXTURE (Reference 3) ---
  _createChevronTexture() {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 32;
    const ctx = canvas.getContext("2d");

    // Coral base
    ctx.fillStyle = "#FF5722";
    ctx.fillRect(0, 0, 128, 32);

    // White directional chevrons >>
    ctx.fillStyle = "rgba(255, 255, 255, 0.90)";

    // Chevron 1
    ctx.beginPath();
    ctx.moveTo(25, 4);
    ctx.lineTo(55, 16);
    ctx.lineTo(25, 28);
    ctx.lineTo(38, 28);
    ctx.lineTo(68, 16);
    ctx.lineTo(38, 4);
    ctx.closePath();
    ctx.fill();

    // Chevron 2
    ctx.beginPath();
    ctx.moveTo(70, 4);
    ctx.lineTo(100, 16);
    ctx.lineTo(70, 28);
    ctx.lineTo(83, 28);
    ctx.lineTo(113, 16);
    ctx.lineTo(83, 4);
    ctx.closePath();
    ctx.fill();

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }

  // --- GPS TO THREE.JS COORDINATE TRANSFORMATION ---
  _project(lat, lon) {
    const cosLat = Math.cos((this.centerLat * Math.PI) / 180);
    const x = (lon - this.centerLon) * cosLat * this.scaleFactor;
    const z = -(lat - this.centerLat) * this.scaleFactor;
    return new THREE.Vector3(x, 0, z);
  }

  // --- SET ACTIVE JOURNEY (Builds 3D Road, Spline & Waypoints) ---
  setJourney(journey) {
    this.journey = journey;
    this.progress = 0;
    this.currentStopIndex = -1;

    // Clean previous route meshes & stops
    if (this.routeLine) {
      this.scene.remove(this.routeLine);
      this.routeLine.geometry.dispose();
      this.routeLine = null;
    }
    if (this.roadMesh) {
      this.scene.remove(this.roadMesh);
      this.roadMesh.geometry.dispose();
      this.roadMesh = null;
    }
    this.stopMarkersGroup.clear();

    if (!journey || !journey.legs || !journey.legs.length) {
      this.busMesh.visible = false;
      this.pinMesh.visible = false;
      this.originRing.visible = false;
      return;
    }

    // 1. Gather all stop points
    const allPoints = journey.legs.flatMap((l) => l.points || [l.from, l.to]);
    if (allPoints.length < 2) return;

    // Recenter projection around the journey midpoint and calibrate scale
    const lats = allPoints.map((p) => p.lat);
    const lons = allPoints.map((p) => p.lon);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLon = Math.min(...lons), maxLon = Math.max(...lons);
    this.centerLat = (minLat + maxLat) / 2;
    this.centerLon = (minLon + maxLon) / 2;

    const cosLat = Math.cos((this.centerLat * Math.PI) / 180);
    const latSpan = maxLat - minLat;
    const lonSpan = (maxLon - minLon) * cosLat;
    const geoSpan = Math.max(latSpan, lonSpan, 0.008); // Min ~800m
    const targetWorldSpan = 140; // Three.js units for canonical scale
    this.scaleFactor = targetWorldSpan / geoSpan;

    const vectors = allPoints.map((p) => this._project(p.lat, p.lon));

    // 2. Build Smooth 3D Spline Curve
    this.curve = new THREE.CatmullRomCurve3(vectors);
    this.curve.curveType = "catmullrom";
    this.curve.tension = 0.35;
    this.routeLength = this.curve.getLength();

    // Map stop waypoints along spline progress (t: 0.0 to 1.0)
    this.stopsWithT = allPoints.map((pt, idx) => ({
      name: pt.name,
      lat: pt.lat,
      lon: pt.lon,
      vec: vectors[idx],
      t: idx / (allPoints.length - 1),
    }));

    // 3. Build Road Surface Ribbon (Porcelain white asphalt, Reference 1)
    const numSubdivisions = Math.max(80, Math.round(this.routeLength * 2));
    const roadGeo = new THREE.TubeGeometry(this.curve, numSubdivisions, 3.2, 4, false);
    roadGeo.scale(1, 0.02, 1); // Flatten into 6.4-unit wide road ribbon
    const roadMat = new THREE.MeshLambertMaterial({ color: 0xFFFFFF });
    this.roadMesh = new THREE.Mesh(roadGeo, roadMat);
    this.roadMesh.position.y = 0.12;
    this.roadMesh.receiveShadow = true;
    this.scene.add(this.roadMesh);

    // 4. Build Animated Route Coral Ribbon with Chevrons (Reference 1 & 3)
    this.routeTexture = this._createChevronTexture();
    this.routeTexture.repeat.set(Math.max(6, Math.round(this.routeLength / 3.5)), 1);

    const lineGeo = new THREE.TubeGeometry(this.curve, numSubdivisions, 1.1, 8, false);
    const lineMat = new THREE.MeshBasicMaterial({
      map: this.routeTexture,
      transparent: true,
      side: THREE.DoubleSide,
    });
    this.routeLine = new THREE.Mesh(lineGeo, lineMat);
    this.routeLine.position.y = 0.22;
    this.scene.add(this.routeLine);

    // 5. Build Intermediate Bus Stop Nodes along Route
    const stopPlateGeo = new THREE.CylinderGeometry(2.0, 2.0, 0.15, 24);
    const stopPlateMat = new THREE.MeshLambertMaterial({ color: 0xFFFFFF });
    const stopRingMat = new THREE.MeshBasicMaterial({ color: 0x00A389, side: THREE.DoubleSide });

    for (let i = 1; i < vectors.length - 1; i++) {
      const v = vectors[i];
      const stopNode = new THREE.Group();
      stopNode.position.set(v.x, 0.14, v.z);

      const plate = new THREE.Mesh(stopPlateGeo, stopPlateMat);
      plate.receiveShadow = true;
      stopNode.add(plate);

      const ring = new THREE.Mesh(new THREE.RingGeometry(1.2, 1.8, 24), stopRingMat);
      ring.rotation.x = -Math.PI / 2;
      ring.position.y = 0.1;
      stopNode.add(ring);

      this.stopMarkersGroup.add(stopNode);
    }

    // 6. Position Origin Beacon & Destination 4-MIN Pin
    const startPos = vectors[0];
    const endPos = vectors[vectors.length - 1];

    this.originRing.position.set(startPos.x, 0, startPos.z);
    this.originRing.visible = true;

    this.pinMesh.position.set(endPos.x, 0, endPos.z);
    this.pinMesh.visible = true;

    // Update pin text texture with actual journey duration
    this._updatePinLabel(Math.round(journey.minutes) + " MIN");

    // 7. Set initial bus state
    this.busMesh.position.copy(startPos);
    this.busMesh.visible = true;

    // Set cabin light color according to journey crowdedness tier
    const crowdLevel = journey.crowd?.level || "Seats available";
    if (crowdLevel === "Standing room") {
      this.cabinLight.color.setHex(0xF59E0B);
    } else if (crowdLevel === "Heavily crowded") {
      this.cabinLight.color.setHex(0xEF4444);
    } else {
      this.cabinLight.color.setHex(0x10B981);
    }

    // 8. Initial Camera Framing (God's Eye Overview)
    if (this.options.mode === "overview") {
      this._frameOverview(vectors);
    }
  }

  _updatePinLabel(text) {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext("2d");

    ctx.beginPath();
    ctx.arc(256, 256, 232, 0, Math.PI * 2);
    ctx.fillStyle = "#FF5722";
    ctx.fill();
    ctx.lineWidth = 26;
    ctx.strokeStyle = "#FFFFFF";
    ctx.stroke();

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#FFFFFF";
    const parts = text.split(" ");
    if (parts.length >= 2) {
      ctx.font = "900 170px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx.fillText(parts[0], 256, 192);
      ctx.font = "800 80px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx.fillText(parts[1], 256, 336);
    } else {
      ctx.font = "900 110px -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
      ctx.fillText(text, 256, 256);
    }

    if (this.pinBadge.material.map) {
      this.pinBadge.material.map.dispose();
    }
    this.pinBadge.material.map = new THREE.CanvasTexture(canvas);
    this.pinBadge.material.needsUpdate = true;
  }

  _frameOverview(points) {
    if (!points.length) return;
    const box = new THREE.Box3();
    points.forEach((p) => box.expandByPoint(p));
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.z, 70);

    const targetPos = new THREE.Vector3(
      center.x,
      center.y + maxDim * 0.95,
      center.z + maxDim * 0.95
    );

    if (this.controls) {
      this.controls.enabled = true;
      this.controls.target.copy(center);
      this.camera.position.copy(targetPos);
      this.controls.update();
    } else {
      this.camera.position.copy(targetPos);
      this.camera.lookAt(center);
    }
  }

  // --- LIVE FLEET INTEGRATION ---
  setLiveVehicles(vehicles) {
    this.liveVehiclesGroup.clear();
    if (!vehicles || !vehicles.length) return;

    const markerMat = new THREE.MeshBasicMaterial({ color: 0x0284C7 });
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x38BDF8, side: THREE.DoubleSide });

    for (const v of vehicles) {
      if (typeof v.lat !== "number" || typeof v.lon !== "number") continue;
      const pos = this._project(v.lat, v.lon);

      const busMarker = new THREE.Group();
      busMarker.position.set(pos.x, 0.2, pos.z);

      const dot = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 0.9, 16), markerMat);
      dot.position.y = 0.45;
      busMarker.add(dot);

      const ring = new THREE.Mesh(new THREE.RingGeometry(1.6, 2.4, 16), ringMat);
      ring.rotation.x = -Math.PI / 2;
      busMarker.add(ring);

      this.liveVehiclesGroup.add(busMarker);
    }
  }

  // --- CAMERA MODE SWITCHER ---
  setCameraMode(mode) {
    this.options.mode = mode;
    if (mode === "overview") {
      if (this.controls) this.controls.enabled = true;
      if (this.journey) {
        const allPoints = this.journey.legs.flatMap((l) => l.points || [l.from, l.to]);
        const vectors = allPoints.map((p) => this._project(p.lat, p.lon));
        this._frameOverview(vectors);
      }
    } else if (mode === "chase") {
      if (this.controls) this.controls.enabled = false;
      if (this.curve && this.busMesh) {
        const currentPos = this.curve.getPointAt(this.progress);
        const tangent = this.curve.getTangentAt(this.progress).normalize();
        const chasePos = new THREE.Vector3()
          .copy(currentPos)
          .sub(tangent.clone().multiplyScalar(22))
          .add(new THREE.Vector3(0, 8.5, 0));
        const lookTarget = new THREE.Vector3()
          .copy(currentPos)
          .add(tangent.clone().multiplyScalar(12))
          .add(new THREE.Vector3(0, 2.0, 0));
        this.camera.position.copy(chasePos);
        this.camera.lookAt(lookTarget);
      }
    }
  }

  // --- RENDER & ANIMATION LOOP (60 FPS) ---
  _animate(time) {
    this.animId = requestAnimationFrame(this._animate);
    const dt = Math.min((time - this.lastTime) / 1000, 0.1);
    this.lastTime = time;

    // 1. Floating Destination Pin Harmonic Bob (Reference 1 & 3)
    if (this.pinMesh && this.pinMesh.visible) {
      const bob = Math.sin(time * 0.003) * 0.65;
      this.pinBadge.position.y = 13.5 + bob;
      this.pinBadge.quaternion.copy(this.camera.quaternion); // Always face camera
      if (this.pinShadow) {
        const s = 1.0 - bob * 0.18;
        this.pinShadow.scale.set(s, s, 1);
      }
    }

    // 2. Animated Flowing Directional Chevrons (Reference 3)
    if (this.routeTexture && this.isPlaying) {
      this.routeTexture.offset.x -= dt * 0.5 * this.options.speedMultiplier;
    }

    // 3. Drive Bus Along Spline Curve (Reference 2)
    if (this.curve && this.busMesh && this.busMesh.visible && this.isPlaying) {
      const step = (dt * 0.05 * this.options.speedMultiplier) / Math.max(1, this.routeLength / 70);
      this.progress = (this.progress + step) % 1.0;

      const currentPos = this.curve.getPointAt(this.progress);
      const tangent1 = this.curve.getTangentAt(this.progress).normalize();

      this.busMesh.position.set(currentPos.x, 0, currentPos.z);
      this.busMesh.rotation.y = Math.atan2(tangent1.x, tangent1.z);
      this.busMesh.rotation.x = 0;

      // Spin wheels proportionally to motion
      if (this.wheels) {
        for (const w of this.wheels) {
          w.rotation.x += dt * 14 * this.options.speedMultiplier;
        }
      }

      // Radar pulse ring under bus
      if (this.busPing) {
        const pPhase = (time * 0.0025) % 1.0;
        const pScale = 0.8 + pPhase * 0.8;
        this.busPing.scale.set(pScale, pScale, 1);
        this.busPing.material.opacity = 0.45 * (1.0 - pPhase);
      }

      // Kinematic Turn Banking (Chassis leans smoothly into curves)
      if (!this.reducedMotion) {
        const tangent2 = this.curve.getTangentAt(Math.min(1.0, this.progress + 0.02)).normalize();
        const angleDelta = Math.atan2(tangent2.x, tangent2.z) - Math.atan2(tangent1.x, tangent1.z);
        this.busMesh.rotation.z = -Math.max(-0.12, Math.min(0.12, angleDelta * 3.5));
      }

      // 4. Update Turn-by-Turn HUD dynamically as bus advances
      if (this.stopsWithT && this.stopsWithT.length) {
        const nextStop = this.stopsWithT.find((s) => s.t >= this.progress) || this.stopsWithT[this.stopsWithT.length - 1];
        const nextIdx = this.stopsWithT.indexOf(nextStop);
        if (nextIdx !== this.currentStopIndex) {
          this.currentStopIndex = nextIdx;
          const hudNext = document.getElementById("hud-next-stop");
          const hudSub = document.getElementById("hud-subtext");
          if (hudNext && nextStop) {
            hudNext.textContent = "Next: " + nextStop.name;
          }
          if (hudSub && this.journey) {
            const remMin = Math.max(1, Math.round((1 - this.progress) * this.journey.minutes));
            const routeName = this.journey.legs[0]?.route || "502";
            hudSub.textContent = "Bus " + routeName + " · " + remMin + " min arrival";
          }
        }
      }

      // 5. Drone Chase Camera Mode (Reference 2 Waymo / Google Maps style)
      if (this.options.mode === "chase") {
        const chasePos = new THREE.Vector3()
          .copy(currentPos)
          .sub(tangent1.clone().multiplyScalar(22)) // 22 units behind
          .add(new THREE.Vector3(0, 8.5, 0));       // 8.5 units above

        const lookTarget = new THREE.Vector3()
          .copy(currentPos)
          .add(tangent1.clone().multiplyScalar(12))  // Look 12 units ahead
          .add(new THREE.Vector3(0, 2.0, 0));

        this.camera.position.lerp(chasePos, 0.1);
        this.camera.lookAt(lookTarget);
      }
    }

    if (this.controls && this.options.mode === "overview") {
      this.controls.update();
    }

    this.renderer.render(this.scene, this.camera);
  }

  destroy() {
    cancelAnimationFrame(this.animId);
    window.removeEventListener("resize", this._resizeHandler);
    if (this.renderer && this.renderer.domElement) {
      this.renderer.domElement.remove();
      this.renderer.dispose();
    }
  }
}
