"use strict";

class RouteMap {
  constructor(base, overlay, motionButton) {
    this.base = base;
    this.overlay = overlay;
    this.button = motionButton;
    this.surface = base.parentElement;
    this.preference = matchMedia("(prefers-reduced-motion: reduce)");
    this.paused = false;
    this.frame = 0;
    this.elapsed = 0;
    this.lastTime = null;
    this.live = [];
    motionButton.addEventListener("click", () => {
      this.paused = !this.paused;
      this.updateMotion();
    });
    this.preference.addEventListener("change", () => this.updateMotion());
    document.addEventListener("visibilitychange", () => this.updateMotion());
    new ResizeObserver(() => this.layout()).observe(this.surface);
  }

  setJourney(journey) {
    this.reveal?.cancel();
    this.journey = journey;
    this.elapsed = 0;
    this.layout();
    if (journey && !this.preference.matches && !this.paused) {
      this.reveal = this.base.animate([{ opacity: .45 }, { opacity: 1 }], {
        duration: 220, easing: "ease-out",
      });
    }
  }

  setLive(positions) {
    this.live = positions;
    this.paintVehicles();
  }

  layout() {
    const { width, height } = this.surface.getBoundingClientRect();
    if (!width || !height) return;
    this.width = width;
    this.height = height;
    this.scale = Math.min(2, devicePixelRatio || 1);
    for (const canvas of [this.base, this.overlay]) {
      canvas.width = Math.round(width * this.scale);
      canvas.height = Math.round(height * this.scale);
    }
    const points = this.journey ? this.journey.legs.flatMap((leg) => leg.points) : [];
    document.getElementById("map-empty").hidden = points.length > 0;
    document.getElementById("map-route").textContent = this.journey
      ? this.journey.legs.map((leg) => leg.route).join(" / ") : "Delhi bus network";
    this.paths = [];
    this.project = null;
    if (points.length) {
      const minX = Math.min(...points.map((p) => p.lon));
      const maxX = Math.max(...points.map((p) => p.lon));
      const minY = Math.min(...points.map((p) => p.lat));
      const maxY = Math.max(...points.map((p) => p.lat));
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      const longitudeScale = Math.cos(centerY * Math.PI / 180);
      const padding = Math.min(80, width * .2);
      const yTilt = .78;
      const unit = Math.min((width - 2 * padding) / Math.max(.002, (maxX - minX) * longitudeScale),
        (height - 104) / Math.max(.002, (maxY - minY) * yTilt));
      this.project = (p) => [width / 2 + (p.lon - centerX) * longitudeScale * unit,
        height / 2 - (p.lat - centerY) * yTilt * unit + 10];
      this.paths = this.journey.legs.map((leg, index) => {
        const coords = leg.points.map(this.project);
        const segments = [];
        let length = 0;
        for (let i = 1; i < coords.length; i += 1) {
          const [x, y] = coords[i - 1];
          const dx = coords[i][0] - x;
          const dy = coords[i][1] - y;
          const distance = Math.hypot(dx, dy / yTilt);
          if (!distance) continue;
          segments.push({ x, y, dx, dy, distance, start: length });
          length += distance;
        }
        return { coords, segments, length, index, duration: 4600 + Math.min(3400, length * 7) };
      });
    }
    this.paintBase(points);
    this.updateMotion();
  }

  context(canvas) {
    const ctx = canvas.getContext("2d");
    ctx.setTransform(this.scale, 0, 0, this.scale, 0, 0);
    return ctx;
  }

  paintBase(points) {
    const ctx = this.context(this.base);
    const { width, height } = this;
    ctx.fillStyle = "#dcece7";
    ctx.fillRect(0, 0, width, height);
    // A drafting grid provides spatial reference for the stop schematic.
    for (let x = -height; x < width + height; x += 25) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x + height * .65, height);
      ctx.strokeStyle = "#bfd7cf";
      ctx.lineWidth = .65;
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 19) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    ctx.strokeStyle = "#8daaa5";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(width - 30, 41);
    ctx.lineTo(width - 30, 22);
    ctx.lineTo(width - 34, 28);
    ctx.moveTo(width - 30, 22);
    ctx.lineTo(width - 26, 28);
    ctx.stroke();
    ctx.fillStyle = "#385b5d";
    ctx.font = "700 10px Segoe UI";
    ctx.fillText("N", width - 34, 17);

    for (const path of this.paths) {
      const color = path.index ? "#396b8a" : "#17634e";
      ctx.beginPath();
      path.coords.forEach(([x, y], index) => index ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      ctx.lineCap = ctx.lineJoin = "round";
      ctx.strokeStyle = "#8aaea5";
      ctx.lineWidth = 12;
      ctx.stroke();
      ctx.strokeStyle = "#f8fffb";
      ctx.lineWidth = 9;
      ctx.stroke();
      ctx.strokeStyle = color;
      ctx.lineWidth = 4;
      ctx.stroke();
      path.coords.forEach(([x, y], index) => {
        const terminal = index === 0 || index === path.coords.length - 1;
        ctx.beginPath();
        ctx.arc(x, y, terminal ? 6 : 3, 0, Math.PI * 2);
        ctx.fillStyle = terminal ? color : "#f0fff7";
        ctx.fill();
        ctx.strokeStyle = terminal ? "#fff" : color;
        ctx.lineWidth = terminal ? 2.5 : 1;
        ctx.stroke();
      });
    }
    if (points.length) {
      this.label(ctx, points[0], -25);
      this.label(ctx, points[points.length - 1], 26);
    }
  }

  label(ctx, point, offset) {
    const [x, y] = this.project(point);
    ctx.font = "700 12px Segoe UI";
    const textWidth = Math.min(ctx.measureText(point.name).width, this.width - 30);
    const left = Math.max(6, Math.min(this.width - textWidth - 16, x - textWidth / 2 - 6));
    const top = Math.max(3, Math.min(this.height - 26, y + offset - 10));
    ctx.beginPath();
    ctx.roundRect(left, top, textWidth + 14, 23, 5);
    ctx.fillStyle = "#f9fffc";
    ctx.fill();
    ctx.strokeStyle = "#9ab8b0";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.fillStyle = "#183c3b";
    ctx.fillText(point.name, left + 7, top + 15, textWidth);
  }

  // Change the heading gradually before and after a corner without moving
  // the bus off the currently selected stop-to-stop line.
  pose(path, fraction) {
    const distance = path.length * fraction;
    const segment = path.segments.find((item) => distance <= item.start + item.distance)
      || path.segments.at(-1);
    if (!segment) return null;
    const offset = (distance - segment.start) / segment.distance;
    const i = path.segments.indexOf(segment);
    const angle = (item) => Math.atan2(item.dy / .78, item.dx);
    const heading = angle(segment);
    const nearby = offset < .16 ? path.segments[i - 1]
      : offset > .84 ? path.segments[i + 1] : null;
    const delta = nearby ? angle(nearby) - heading : 0;
    const turn = Math.atan2(Math.sin(delta), Math.cos(delta));
    const blend = Math.max(0, (.16 - Math.min(offset, 1 - offset)) / .32);
    return [segment.x + segment.dx * offset, segment.y + segment.dy * offset, heading + turn * blend];
  }

  paintVehicles() {
    if (!this.width) return;
    const ctx = this.context(this.overlay);
    ctx.clearRect(0, 0, this.width, this.height);
    if (!this.project || !this.paths.length) return;
    ctx.fillStyle = "#713622";
    ctx.strokeStyle = "#fff9ed";
    ctx.lineWidth = 1.5;
    for (const point of this.live) {
      const [x, y] = this.project(point);
      if (x < 5 || x > this.width - 5 || y < 5 || y > this.height - 5) continue;
      ctx.beginPath();
      ctx.roundRect(x - 4, y - 4, 8, 8, 2);
      ctx.fill();
      ctx.stroke();
    }
    const total = this.paths.reduce((sum, path) => sum + path.duration, 0);
    let time = this.elapsed % total;
    for (const path of this.paths) {
      if (time > path.duration) {
        time -= path.duration;
        continue;
      }
      const fraction = this.preference.matches ? .54 : Math.max(.015, Math.min(.985, time / path.duration));
      const pose = this.pose(path, fraction);
      if (pose) {
        const fade = this.preference.matches || this.paused ? 1
          : Math.min(1, .4 + Math.min(time, path.duration - time) / 280);
        drawBus(ctx, ...pose, path.index, fade);
      }
      break;
    }
  }

  updateMotion() {
    if (this.preference.matches || this.paused) this.reveal?.cancel();
    cancelAnimationFrame(this.frame);
    this.frame = 0;
    this.lastTime = null;
    this.button.hidden = !this.journey || this.preference.matches;
    this.button.textContent = this.paused ? "Play preview" : "Pause preview";
    this.paintVehicles();
    if (this.journey && !this.paused && !this.preference.matches && !document.hidden) {
      this.frame = requestAnimationFrame((stamp) => this.tick(stamp));
    }
  }

  tick(stamp) {
    if (this.lastTime !== null) this.elapsed += Math.min(45, stamp - this.lastTime);
    this.lastTime = stamp;
    this.paintVehicles();
    this.frame = requestAnimationFrame((next) => this.tick(next));
  }
}

function drawBus(ctx, x, y, heading, secondLeg, alpha) {
  const cos = Math.cos(heading), sin = Math.sin(heading);
  // Project the same rectangular 3D model at every route heading.
  const project = ([u, v, z]) => [x + u * cos - v * sin, y + .78 * (u * sin + v * cos) - z];
  const polygon = (points, fill, stroke = "#173744") => {
    ctx.beginPath();
    points.map(project).forEach(([px, py], i) => i ? ctx.lineTo(px, py) : ctx.moveTo(px, py));
    ctx.closePath();
    ctx.fillStyle = fill;
    ctx.fill();
    if (stroke) {
      ctx.strokeStyle = stroke;
      ctx.lineWidth = .8;
      ctx.stroke();
    }
  };

  const half = 22, side = 8, roof = 16, floor = 3;
  const faces = [];
  const body = secondLeg ? "#4f83ab" : "#2c9970";
  const trim = secondLeg ? "#d8efff" : "#d1ffdf";
  ctx.save();
  ctx.globalAlpha = alpha * .3;
  ctx.fillStyle = "#153d38";
  ctx.beginPath();
  ctx.ellipse(x + 2, y + 3, 24, 6, Math.atan2(.78 * sin, cos), 0, 2 * Math.PI);
  ctx.fill();
  ctx.globalAlpha = alpha;

  const visibleSide = cos >= 0 ? side : -side;
  const visibleEnd = sin >= 0 ? half : -half;
  faces.push(() => {
    const v = visibleSide;
    for (const axle of [-13, 13]) {
      const [wx, wy] = project([axle, v, 2]);
      ctx.beginPath();
      ctx.arc(wx, wy, 3.7, 0, Math.PI * 2);
      ctx.fillStyle = "#14262f";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(wx, wy, 1.3, 0, Math.PI * 2);
      ctx.fillStyle = "#91b9b2";
      ctx.fill();
    }
    polygon([[-half, v, floor], [half, v, floor], [half, v, roof], [-half, v, roof]], body);
    for (let u = -18; u <= 12; u += 7.5) {
      polygon([[u, v, 9], [u + 5.5, v, 9], [u + 5.5, v, 14], [u, v, 14]], "#193a4a", null);
    }
    polygon([[-19, v, 5], [20, v, 5], [20, v, 6.3], [-19, v, 6.3]], trim, null);
  });
  faces.push(() => {
    const u = visibleEnd;
    polygon([[u, -side, floor], [u, side, floor], [u, side, roof], [u, -side, roof]], body);
    polygon([[u, -5.5, 9], [u, 5.5, 9], [u, 5.5, 14], [u, -5.5, 14]], "#163545", null);
    for (const v of [-5.6, 4.1]) {
      polygon([[u, v, 5.2], [u, v + 1.6, 5.2], [u, v + 1.6, 6.9], [u, v, 6.9]],
        u > 0 ? "#fff3b5" : "#ae3845", null);
    }
  });
  faces.forEach((face) => face());
  polygon([[-half, -side, roof], [half, -side, roof], [half, side, roof], [-half, side, roof]], trim);
  polygon([[-8, -3.5, roof], [7, -3.5, roof], [7, 3.5, roof], [-8, 3.5, roof]], "#accdc6", null);
  ctx.restore();
}
