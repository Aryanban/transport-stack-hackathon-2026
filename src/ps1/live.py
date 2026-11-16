"""Live layer: poll GTFS-RT, keep recent traces, and adjust predictions.

Two effects, both only for departures within LIVE_HORIZON of now:
- factor(f, t, when): ratio of live observed to historical predicted time on
  a stretch over the last 30 minutes, shrunk toward the city-wide live ratio,
  fading to 1 as the departure moves further into the future.
- next_arrival(route, i, ready): ETA of a real bus already on the route,
  from the last stop it passed plus the predicted remaining ride.
With no key or no fresh data, both fall back silently to the historical model.
"""
from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta

import numpy as np

from .matcher import match_run
from .model import IST, day_type
from .network import to_xy

POLL_S = 20
TRACE_S = 30 * 60          # keep this much history per vehicle (= live window)
LIVE_WINDOW_S = 30 * 60    # observations used for live factors
LIVE_HORIZON_S = 60 * 60   # live influence fades to zero over this horizon
W_LIVE = 3.0               # shrinkage weight for stretch-level live factor
STALE_S = 180              # vehicle positions older than this are ignored for ETAs


class LiveTracker:
    def __init__(self, net, model, client=None):
        self.net, self.model = net, model
        self.client = client
        self.traces = defaultdict(deque)  # (vehicle, trip, route) -> deque[(ts, x, y)]
        self.obs = deque()                # (t_end, f, t, ratio)
        self.pair_ratio = {}              # "f>t" -> (log_sum, n)
        self.city = (0.0, 0)
        self.last_poll = None
        self.vehicle_count = 0
        self.passes = {}                  # key -> list[(k, t)] most recent match
        self.positions = []
        self._lock = threading.Lock()
        self._thread = None

    # ---------- ingestion ----------
    def start(self):
        if self.client is None or self._thread:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while True:
            try:
                self.ingest(self.client.fetch_vehicle_positions(force_refresh=True))
            except Exception:
                pass
            time.sleep(POLL_S)

    def snapshot(self):
        """Current positions with headings, read under the lock the poll thread writes with."""
        with self._lock:
            return [dict(v, heading=self.heading((v["vehicle_id"], v.get("trip_id", ""), v["route_id"])))
                    for v in self.positions]

    def heading(self, key, min_move_m=15.0):
        """Compass heading from the vehicle's last two GPS points far enough apart, else None.
        Callers outside this class go through snapshot(), which holds the lock."""
        tr = self.traces.get(key)
        if not tr:
            return None
        _, x1, y1 = tr[-1]
        for _, x0, y0 in reversed(tr):
            dx, dy = x1 - x0, y1 - y0
            if math.hypot(dx, dy) >= min_move_m:
                return round(math.degrees(math.atan2(dx, dy)) % 360)
        return None

    def ingest(self, vehicles, now=None):
        now = now or time.time()
        live = [v for v in vehicles if v.get("source", "live") == "live" and v.get("route_id") in self.net.routes]
        with self._lock:
            for v in live:
                key = (v["vehicle_id"], v.get("trip_id", ""), v["route_id"])
                tr = self.traces[key]
                if tr and tr[-1][0] >= v["timestamp"]:
                    continue
                x, y = to_xy(v["latitude"], v["longitude"])
                tr.append((float(v["timestamp"]), float(x), float(y)))
                while tr and tr[0][0] < now - TRACE_S:
                    tr.popleft()
            for key in [k for k, tr in self.traces.items() if not tr]:
                del self.traces[key]
            self._rematch(now)
            self.positions = [v for v in live if now - v["timestamp"] <= STALE_S]
            self.vehicle_count = len(self.positions)
            self.last_poll = now

    def _rematch(self, now):
        seen = set()
        new_obs = []
        for key, tr in self.traces.items():
            if len(tr) < 3:
                continue
            route = self.net.routes[key[2]]
            arr = np.array(tr)
            passes = match_run(route, arr[:, 0], arr[:, 1], arr[:, 2])
            self.passes[key] = passes
            for (k1, t1), (k2, t2) in zip(passes, passes[1:]):
                if k2 != k1 + 1 or t2 <= t1 or t2 < now - LIVE_WINDOW_S:
                    continue
                okey = (key[0], key[2], k1)
                if okey in seen:
                    continue
                seen.add(okey)
                when = datetime.fromtimestamp(t1, IST)
                f, t = route.stops[k1], route.stops[k2]
                hist, _ = self.model.predict(f, t, route.stop_dist[k2] - route.stop_dist[k1], when.hour, day_type(when))
                new_obs.append((t2, f, t, math.log(max(1.0, t2 - t1) / hist)))
        self.passes = {k: v for k, v in self.passes.items() if k in self.traces}
        pair = defaultdict(lambda: [0.0, 0])
        for _, f, t, lr in new_obs:
            p = pair[f"{f}>{t}"]
            p[0] += max(-1.5, min(1.5, lr))
            p[1] += 1
        total = sum(p[0] for p in pair.values())
        n = sum(p[1] for p in pair.values())
        self.pair_ratio = dict(pair)
        self.city = (total / n if n else 0.0, n)

    # ---------- queries ----------
    def fresh(self, now=None):
        now = now or time.time()
        return self.last_poll is not None and now - self.last_poll < 3 * POLL_S and self.city[1] >= 20

    def factor(self, f, t, when: datetime) -> float:
        if not self.fresh():
            return 1.0
        ahead = (when.timestamp() - time.time())
        if ahead > LIVE_HORIZON_S or ahead < -LIVE_HORIZON_S:
            return 1.0
        fade = 1.0 - max(0.0, ahead) / LIVE_HORIZON_S
        city_log = self.city[0]
        s, n = self.pair_ratio.get(f"{f}>{t}", (0.0, 0))
        log_f = (s + W_LIVE * city_log) / (n + W_LIVE)
        return math.exp(fade * log_f)

    def next_arrival(self, route, i, ready: datetime, planner):
        if not self.fresh() or (ready.timestamp() - time.time()) > LIVE_HORIZON_S:
            return None
        best = None
        now = time.time()
        with self._lock:
            items = [(k, p) for k, p in self.passes.items() if k[2] == route.id and p]
        for key, passes in items:
            k, t_pass = passes[-1]
            if k >= i or now - t_pass > 15 * 60:
                continue
            ride, _ = planner.ride(route, k, i, datetime.fromtimestamp(t_pass, IST))
            eta = datetime.fromtimestamp(t_pass + ride, IST)
            if eta >= ready and (best is None or eta < best):
                best = eta
        return best

    def status(self):
        return {"enabled": self.client is not None, "fresh": self.fresh(),
                "vehicles": self.vehicle_count, "live_observations": self.city[1],
                "city_live_vs_typical": round(math.exp(self.city[0]), 3) if self.city[1] else None,
                "last_poll": datetime.fromtimestamp(self.last_poll, IST).isoformat() if self.last_poll else None}
