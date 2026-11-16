// Real 3D buses on the map: a three.js custom layer drawn into MapLibre's own WebGL context.
// - The preview bus for the chosen trip, following map3d.js's route preview.
// - Every live bus from /live/vehicles, one instanced draw call, gliding to each new GPS report.
// The bus model is built from boxes and cylinders here, so no model files are downloaded.
// If three.js cannot load, map3d.js keeps its 2D bus icons and CSS preview bus.

const THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js";
const MAX_FLEET = 9000;
const GLIDE_MS = 2500;   // time a live bus takes to slide to its newest reported position
const POP_MS = 300;      // time a newly seen bus takes to grow in

const mercX = (lon) => (lon + 180) / 360;
const mercY = (lat) => (1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2;
const easeOut = (t) => 1 - Math.pow(1 - t, 3);
const turn = (a, b, t) => a + ((((b - a) % 360) + 540) % 360 - 180) * t;

function busGeometry(THREE, livery) {
  // Local frame in metres: x right, y forward, z up. A 12 m low-floor city bus.
  const parts = [];
  const box = (w, l, h, x, y, z, color) => {
    const g = new THREE.BoxGeometry(w, l, h).toNonIndexed();
    g.translate(x, y, z);
    parts.push([g, new THREE.Color(color)]);
  };
  const wheel = (x, y) => {
    const g = new THREE.CylinderGeometry(0.5, 0.5, 0.32, 14).toNonIndexed();
    g.rotateZ(Math.PI / 2);
    g.translate(x, y, 0.5);
    parts.push([g, new THREE.Color("#1f2328")]);
  };
  box(2.55, 12.0, 1.15, 0, 0, 0.95, livery);           // lower body
  box(2.56, 11.1, 0.95, 0, -0.2, 2.05, "#20303f");      // window band, dark glass
  box(2.55, 12.0, 0.35, 0, 0, 2.7, "#f4f6f8");          // roof line
  box(1.9, 3.6, 0.38, 0, -1.2, 3.06, "#d9dee4");        // roof AC pod
  box(2.3, 0.08, 1.5, 0, 6.01, 1.95, "#14212d");        // windscreen
  box(0.42, 0.06, 0.2, -0.85, 6.03, 0.75, "#fff6d6");   // headlights
  box(0.42, 0.06, 0.2, 0.85, 6.03, 0.75, "#fff6d6");
  box(0.42, 0.06, 0.2, -0.85, -6.03, 0.8, "#e5484d");   // tail lights
  box(0.42, 0.06, 0.2, 0.85, -6.03, 0.8, "#e5484d");
  box(2.57, 1.2, 0.18, 0, 4.2, 1.45, "#ffffff");        // livery stripe
  wheel(-1.12, 3.9); wheel(1.12, 3.9); wheel(-1.12, -3.6); wheel(1.12, -3.6);

  let count = 0;
  for (const [g] of parts) count += g.attributes.position.count;
  const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), col = new Float32Array(count * 3);
  let o = 0;
  for (const [g, c] of parts) {
    pos.set(g.attributes.position.array, o * 3);
    nor.set(g.attributes.normal.array, o * 3);
    for (let i = 0; i < g.attributes.position.count; i++) col.set([c.r, c.g, c.b], (o + i) * 3);
    o += g.attributes.position.count;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  geo.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return geo;
}

function shadowTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = c.height = 64;
  const ctx = c.getContext("2d");
  const g = ctx.createRadialGradient(32, 32, 4, 32, 32, 32);
  g.addColorStop(0, "rgba(15,23,42,0.45)");
  g.addColorStop(1, "rgba(15,23,42,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

function makeLayer(THREE, engine) {
  const map = engine.map;
  const fleet = new Map(); // id -> {fx, fy, fh, tx, ty, th, t0, born, route}
  let renderer, scene, camera, hero, heroShadow, ring, fleetMesh;
  const m4 = new THREE.Matrix4(), scaleM = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), sc = new THREE.Vector3();
  const up = new THREE.Vector3(0, 0, 1);
  // Mercator y grows southward. Meshes are placed in east-north-up metres and flipped by FLIP,
  // a negative-determinant matrix three.js sees, so it keeps face winding and lighting right.
  const FLIP = new THREE.Matrix4().makeScale(1, -1, 1);
  const place = (mesh, x, y, z, headingDeg, sx, sy, sz) => {
    q.setFromAxisAngle(up, (-headingDeg * Math.PI) / 180); // compass degrees, clockwise from north
    mesh.matrix.compose(v.set(x, y, z), q, sc.set(sx, sy, sz)).premultiply(FLIP);
    mesh.matrixWorld.copy(mesh.matrix);
  };

  // Metres per CSS pixel at the map centre, and a size boost so buses stay readable when zoomed out.
  const metresPerPixel = () => 40075016.7 * Math.cos((map.getCenter().lat * Math.PI) / 180) / (512 * Math.pow(2, map.getZoom()));
  const boost = (pixels) => Math.max(1, (pixels * metresPerPixel()) / 12);

  engine.onFleet = (list) => {
    const now = performance.now();
    const seen = new Set();
    for (const b of list) {
      seen.add(b.id);
      const x = mercX(b.lon), y = mercY(b.lat);
      const cur = fleet.get(b.id);
      if (!cur) {
        const h = b.heading ?? 0;
        fleet.set(b.id, { fx: x, fy: y, fh: h, tx: x, ty: y, th: h, t0: now, born: now });
        continue;
      }
      const k = easeOut(Math.min(1, (now - cur.t0) / GLIDE_MS));
      cur.fx = cur.fx + (cur.tx - cur.fx) * k;
      cur.fy = cur.fy + (cur.ty - cur.fy) * k;
      cur.fh = turn(cur.fh, cur.th, k);
      cur.tx = x; cur.ty = y; cur.th = b.heading ?? cur.th; cur.t0 = now;
    }
    for (const id of fleet.keys()) if (!seen.has(id)) fleet.delete(id);
    map.triggerRepaint();
  };
  engine.fleetCleared = () => { fleet.clear(); map.triggerRepaint(); };

  return {
    id: "buses-3d",
    type: "custom",
    renderingMode: "3d",
    onAdd(_, gl) {
      camera = new THREE.Camera();
      scene = new THREE.Scene();
      const sky = new THREE.HemisphereLight(0xffffff, 0xb8c2cc, 2.4);
      sky.position.set(0, 0, 1);
      scene.add(sky);
      const sun = new THREE.DirectionalLight(0xfff4e0, 1.5);
      sun.position.set(-0.6, -0.4, 1).normalize();
      scene.add(sun);

      const heroMat = new THREE.MeshLambertMaterial({ vertexColors: true });
      hero = new THREE.Mesh(busGeometry(THREE, "#1a73e8"), heroMat);
      hero.matrixAutoUpdate = false;
      hero.matrixWorldAutoUpdate = false;
      heroShadow = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 15), new THREE.MeshBasicMaterial({ map: shadowTexture(THREE), transparent: true, depthWrite: false }));
      heroShadow.matrixAutoUpdate = false;
      ring = new THREE.Mesh(new THREE.RingGeometry(9, 10.5, 48), new THREE.MeshBasicMaterial({ color: 0x1a73e8, transparent: true, depthWrite: false }));
      ring.matrixAutoUpdate = false;
      scene.add(heroShadow, ring, hero);

      const fleetMat = new THREE.MeshLambertMaterial({ vertexColors: true });
      fleetMesh = new THREE.InstancedMesh(busGeometry(THREE, "#14b8a6"), fleetMat, MAX_FLEET);
      fleetMesh.frustumCulled = false;
      fleetMesh.count = 0;
      fleetMesh.matrixAutoUpdate = false;
      fleetMesh.matrix.copy(FLIP);
      scene.add(fleetMesh);

      renderer = new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl, antialias: true });
      renderer.autoClear = false;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      document.body.classList.add("has-3d");
    },
    render(gl, matrix) {
      const now = performance.now();
      const c = map.getCenter();
      const cx = mercX(c.lng), cy = mercY(c.lat);
      const unit = maplibregl.MercatorCoordinate.fromLngLat(c, 0).meterInMercatorCoordinateUnits();
      const toLocal = (mx, my) => [(mx - cx) / unit, -(my - cy) / unit]; // east, north metres from centre
      // World = translate(map centre) * scale(metres -> mercator units). Re-centring every frame keeps precision.
      camera.projectionMatrix.fromArray(matrix).multiply(m4.makeTranslation(cx, cy, 0)).multiply(scaleM.makeScale(unit, unit, unit));

      let animating = false;
      // Preview bus for the chosen trip.
      const p = engine.preview;
      hero.visible = heroShadow.visible = ring.visible = !!p;
      if (p) {
        const [x, y] = toLocal(mercX(p.coord[0]), mercY(p.coord[1]));
        const s = boost(34);
        place(hero, x, y, 0, p.heading, s, s, s);
        place(heroShadow, x, y, 0.05 * s, p.heading, s, s, 1);
        const pulse = (now % 1800) / 1800;
        const rs = s * (0.6 + pulse * 0.9);
        place(ring, x, y, 0.08 * s, 0, rs, rs, 1);
        const still = engine.reducedMotion.matches || engine.previewPaused;
        ring.material.opacity = still ? 0 : 0.45 * (1 - pulse);
        animating = !still;
      }

      // Live fleet.
      let n = 0;
      if (engine.liveFleetVisible && fleet.size) {
        const z = map.getZoom();
        const s = boost(z < 11.5 ? 6 : z < 13.5 ? 9 : 15); // small when the whole city is in view
        const bounds = map.getBounds();
        const pad = 0.02;
        for (const b of fleet.values()) {
          if (n >= MAX_FLEET) break;
          const k = engine.reducedMotion.matches ? 1 : easeOut(Math.min(1, (now - b.t0) / GLIDE_MS));
          if (k < 1) animating = true;
          const mx = b.fx + (b.tx - b.fx) * k, my = b.fy + (b.ty - b.fy) * k;
          const lon = mx * 360 - 180;
          if (lon < bounds.getWest() - pad || lon > bounds.getEast() + pad) continue;
          const grow = engine.reducedMotion.matches ? 1 : easeOut(Math.min(1, (now - b.born) / POP_MS));
          if (grow < 1) animating = true;
          const [x, y] = toLocal(mx, my);
          q.setFromAxisAngle(up, (-turn(b.fh, b.th, k) * Math.PI) / 180);
          // Instances live inside the mesh's FLIP, so they are composed in plain east-north-up.
          fleetMesh.setMatrixAt(n++, m4.compose(v.set(x, y, 0), q, sc.set(s * grow, s * grow, s * grow)));
        }
      }
      fleetMesh.count = n;
      fleetMesh.instanceMatrix.needsUpdate = true;

      renderer.resetState();
      renderer.render(scene, camera);
      if (animating) map.triggerRepaint();
    },
  };
}

(async () => {
  const engine = window.transitMap;
  if (!engine || !engine.map) return;
  let THREE;
  try {
    THREE = await import(THREE_URL);
  } catch (err) {
    console.warn("3D buses unavailable, keeping 2D icons:", err);
    return;
  }
  const add = (map) => {
    if (map.getLayer("buses-3d")) return;
    map.addLayer(makeLayer(THREE, engine)); // on top, so buses stand on the route line
    engine.use3DFleet?.();
  };
  engine.styleHooks = [...(engine.styleHooks || []), add];
  if (engine.isLoaded) add(engine.map);
})();
