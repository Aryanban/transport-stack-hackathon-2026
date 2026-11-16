"""Bus journey planner timed by the learned travel-time model.

The timetable is used only for which routes exist and when each trip leaves
its first stop. Everything after that is predicted: when the bus reaches
your stop, how long the ride takes, and when you arrive.
"""
from __future__ import annotations

import math
import re
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np

from .model import IST, TravelModel, day_type
from .network import Network, haversine_m

WALK_MS = 1.25            # 4.5 km/h
WALK_DETOUR = 1.3         # street distance vs straight line
ACCESS_M = 1000           # max walk to the first stop / from the last stop
TRANSFER_M = 300          # max walk between stops when changing bus
TRANSFER_BUFFER_S = 180   # time allowed to change bus
LATE_SLACK_S = 30 * 60    # options may arrive at most this much (or half the best trip) after the best
WALK_ONLY_MAX_S = 30 * 60 # offer walking the whole way when it takes at most this
HORIZON_S = 3 * 3600      # search window for a bus after you reach the stop
MAX_OPTIONS = 3


@dataclass
class Place:
    label: str
    lat: float
    lon: float


class Planner:
    def __init__(self, net: Network, model: TravelModel, live=None):
        self.net, self.model, self.live = net, model, live
        served = [s for s in net.stop_routes if s in net.stops]
        self.stop_ids = np.array(served)
        self.stop_lat = np.array([net.stops[s][1] for s in served])
        self.stop_lon = np.array([net.stops[s][2] for s in served])
        self._names = [(s, net.stops[s][0].lower()) for s in served]

    # ---------- places ----------
    def resolve(self, text: str) -> Place:
        text = text.strip()
        m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)", text)
        if m:
            return Place(f"{float(m[1]):.5f}, {float(m[2]):.5f}", float(m[1]), float(m[2]))
        if text in self.net.stops:
            name, lat, lon = self.net.stops[text]
            return Place(name, lat, lon)
        q = text.lower()
        scored = []
        for sid, name in self._names:
            if name == q:
                rank = 0
            elif name.startswith(q):
                rank = 1
            elif q in name:
                rank = 2
            elif all(w in name for w in q.split()):
                rank = 3
            else:
                continue
            scored.append((rank, len(name), sid))
        if not scored:
            raise LookupError(f"No stop matches '{text}'. Try a stop name or 'lat,lon'.")
        sid = min(scored)[2]
        name, lat, lon = self.net.stops[sid]
        return Place(name, lat, lon)

    def search_stops(self, text: str, limit=8):
        q = text.lower().strip()
        if len(q) < 2:
            return []
        hits = sorted((name.find(q) != 0, len(name), sid) for sid, name in self._names if q in name)
        return [{"id": sid, "name": self.net.stops[sid][0], "lat": self.net.stops[sid][1],
                 "lon": self.net.stops[sid][2]} for _, _, sid in hits[:limit]]

    def nearby(self, lat, lon, radius):
        d = haversine_m(lat, lon, self.stop_lat, self.stop_lon)
        idx = np.nonzero(d <= radius)[0]
        idx = idx[np.argsort(d[idx])][:15]
        return {self.stop_ids[i]: float(d[i]) * WALK_DETOUR / WALK_MS for i in idx}

    # ---------- timing ----------
    def segment_s(self, route, k, when: datetime, hour_override=None, use_live=True):
        f, t = route.stops[k], route.stops[k + 1]
        dist = float(route.stop_dist[k + 1] - route.stop_dist[k])
        hour = when.hour if hour_override is None else hour_override
        dtype = day_type(when)
        sec, n = self.model.predict(f, t, dist, hour, dtype)
        if use_live and self.live is not None and hour_override is None:
            sec *= self.live.factor(f, t, when)
        return sec, n

    def ride(self, route, i, j, start: datetime, **kw):
        """Predicted seconds from stop i to stop j leaving at start, and observed share."""
        t, covered, total = start, 0.0, 0.0
        for k in range(i, j):
            sec, n = self.segment_s(route, k, t, **kw)
            t += timedelta(seconds=sec)
            total += sec
            if n >= 3:
                covered += sec
        return total, (covered / total if total else 0.0)

    def next_bus(self, route, i, ready: datetime):
        """Earliest bus reaching stop i at or after `ready`. Returns (arrival_dt, source)."""
        if self.live is not None:
            eta = self.live.next_arrival(route, i, ready, self)
            if eta is not None:
                return eta, "live"
        deps = route.departures
        if not len(deps):
            return None, None
        # approximate time from the first stop to stop i at this hour, then refine
        approx, _ = self.ride(route, 0, i, ready - timedelta(seconds=float(route.sched_offset[i])))
        found = None
        for day_shift in (-1, 0, 1):  # GTFS times can run past 24:00
            midnight = datetime(ready.year, ready.month, ready.day, tzinfo=IST) + timedelta(days=day_shift)
            target = (ready - midnight).total_seconds() - approx - 600
            k = bisect_left(deps, target)
            for d in deps[k:k + 12]:
                dep = midnight + timedelta(seconds=int(d))
                to_i, _ = self.ride(route, 0, i, dep)
                at_i = dep + timedelta(seconds=to_i)
                if at_i >= ready:
                    if found is None or at_i < found:
                        found = at_i
                    break
        if found is None or (found - ready).total_seconds() > HORIZON_S:
            return None, None
        return found, "timetable"

    # ---------- search ----------
    def plan(self, origin: str, destination: str, depart: datetime):
        o, d = self.resolve(origin), self.resolve(destination)
        o_acc = self.nearby(o.lat, o.lon, ACCESS_M)
        d_acc = self.nearby(d.lat, d.lon, ACCESS_M)
        if not o_acc or not d_acc:
            return {"origin": o.__dict__, "destination": d.__dict__, "options": [],
                    "message": "No bus stop within 1 km of the origin or destination."}
        reach = {}  # stop -> list[(route_id, board_idx, alight_idx, walk_after_s)]
        for ds, w in d_acc.items():
            for rid, j in self.net.stop_routes.get(ds, ()):
                r = self.net.routes[rid]
                for i in range(j):
                    reach.setdefault(r.stops[i], []).append((rid, i, j, w))
        cands = []
        for os_, w0 in o_acc.items():
            for rid, i, j, w1 in reach.get(os_, ()):
                cands.append(((os_, w0, rid, i, j, w1),))
        cands += self._transfer_candidates(o_acc, reach)
        cands.sort(key=self._quick_cost)
        best = {}  # route sequence -> earliest-arriving timing of it
        for c in cands[:120]:
            opt = self._time(c, o, d, depart)
            if opt is None:
                continue
            key = tuple(leg["route"] for leg in opt["legs"] if leg["mode"] == "bus")
            if key not in best or opt["arrive"] < best[key]["arrive"]:
                best[key] = opt
        walk_only = self._walk_only(o, d, depart)
        if walk_only:
            best[("walk",)] = walk_only
        options = sorted(best.values(), key=lambda x: (x["arrive"], x["transfers"], x["walk_min"]))
        kept = []
        for opt in options:  # drop options another kept one beats on arrival, changes and walking
            if not any(k["arrive"] <= opt["arrive"] and k["transfers"] <= opt["transfers"]
                       and k["walk_min"] <= opt["walk_min"] for k in kept):
                kept.append(opt)
        if kept:  # an option arriving far later than the best one is not a real choice
            first = datetime.fromisoformat(kept[0]["arrive"])
            slack = timedelta(seconds=max(LATE_SLACK_S, 0.5 * kept[0]["total_min"] * 60))
            kept = [k for k in kept if datetime.fromisoformat(k["arrive"]) <= first + slack]
        options = kept[:MAX_OPTIONS]
        return {"origin": o.__dict__, "destination": d.__dict__, "depart": depart.isoformat(),
                "options": options, "message": None if options else "No bus journey found in the next 3 hours."}

    def _transfer_candidates(self, o_acc, reach):
        best, near_cache = {}, {}
        for os_, w0 in o_acc.items():
            for rid1, i in self.net.stop_routes.get(os_, ()):
                r1 = self.net.routes[rid1]
                for k in range(i + 1, len(r1.stops)):
                    x = r1.stops[k]
                    if x not in near_cache:
                        _, xl, xo = self.net.stops[x]
                        near_cache[x] = self.nearby(xl, xo, TRANSFER_M)
                    for x2, wx in near_cache[x].items():
                        for rid2, i2, j2, w1 in reach.get(x2, ()):
                            if rid2 == rid1:
                                continue
                            c = ((os_, w0, rid1, i, k, 0.0), (x2, wx, rid2, i2, j2, w1))
                            cost = self._quick_cost(c)
                            if cost < best.get((rid1, rid2), (math.inf,))[0]:
                                best[(rid1, rid2)] = (cost, c)
        return [c for _, c in sorted(best.values(), key=lambda v: v[0])[:60]]

    def _quick_cost(self, c):
        cost = 0.0
        for stop, w0, rid, i, j, w1 in c:
            r = self.net.routes[rid]
            cost += w0 + w1 + (r.stop_dist[j] - r.stop_dist[i]) / 5.0 + 600  # ~18 km/h + wait
        return cost

    def _time(self, cand, o: Place, d: Place, depart: datetime):
        legs, t = [], depart
        prev_place = o
        observed_s = ride_total = sched_total = quiet_total = 0.0
        for n, (stop, walk_before, rid, i, j, walk_after) in enumerate(cand):
            r = self.net.routes[rid]
            sname, slat, slon = self.net.stops[stop]
            if walk_before > 0:
                legs.append(self._walk(prev_place, Place(sname, slat, slon), t, walk_before))
                t += timedelta(seconds=walk_before)
            ready = t + (timedelta(seconds=TRANSFER_BUFFER_S) if n else timedelta(0))
            board, source = self.next_bus(r, i, ready)
            if board is None:
                return None
            ride_s, share = self.ride(r, i, j, board)
            hist_s, _ = self.ride(r, i, j, board, use_live=False)
            quiet_h = self.quiet_hour()
            quiet_s, _ = self.ride(r, i, j, board, hour_override=quiet_h)
            sched_s = float(r.sched_offset[j] - r.sched_offset[i])
            alight = board + timedelta(seconds=ride_s)
            aname, alat, alon = self.net.stops[r.stops[j]]
            legs.append({
                "mode": "bus", "route": r.name, "route_id": rid, "headsign": r.desc,
                "from": {"id": stop, "name": sname, "lat": slat, "lon": slon},
                "to": {"id": r.stops[j], "name": aname, "lat": alat, "lon": alon},
                "wait_min": round((board - t).total_seconds() / 60, 1),
                "board": board.isoformat(), "alight": alight.isoformat(),
                "stops": j - i, "ride_min": round(ride_s / 60, 1),
                "typical_min": round(hist_s / 60, 1), "quiet_min": round(quiet_s / 60, 1),
                "timetable_min": round(sched_s / 60, 1), "observed_share": round(share, 2),
                "bus_source": source, "hour_basis": self.hour_basis(board), "path": self._path(r, i, j),
                "stop_points": [{"id": k, "name": self.net.stops[k][0], "lat": self.net.stops[k][1],
                                 "lon": self.net.stops[k][2]} for k in r.stops[i:j + 1] if k in self.net.stops],
            })
            observed_s += share * ride_s
            ride_total += ride_s
            sched_total += sched_s
            quiet_total += quiet_s
            t = alight
            prev_place = Place(aname, alat, alon)
            if n == len(cand) - 1 and walk_after > 0:
                legs.append(self._walk(prev_place, d, t, walk_after))
                t += timedelta(seconds=walk_after)
        total = (t - depart).total_seconds()
        walk = sum(leg.get("minutes", 0) for leg in legs if leg["mode"] == "walk")
        fixed = total - ride_total  # walking and waiting do not change with traffic
        return {
            "depart": depart.isoformat(), "arrive": t.isoformat(), "total_min": round(total / 60, 1),
            "walk_min": round(walk, 1), "transfers": len(cand) - 1,
            "ride_min": round(ride_total / 60, 1),
            "quiet_total_min": round((fixed + quiet_total) / 60, 1), "quiet_hour": self.quiet_hour(),
            "timetable_ride_min": round(sched_total / 60, 1),
            "observed_share": round(observed_s / ride_total, 2) if ride_total else 0.0,
            "hour_basis": next((l["hour_basis"] for l in legs if l["mode"] == "bus"), ""),
            "legs": legs,
        }

    def _walk_only(self, o: Place, d: Place, depart):
        sec = float(haversine_m(o.lat, o.lon, d.lat, d.lon)) * WALK_DETOUR / WALK_MS
        if sec > WALK_ONLY_MAX_S:
            return None
        arrive = depart + timedelta(seconds=sec)
        return {"depart": depart.isoformat(), "arrive": arrive.isoformat(), "total_min": round(sec / 60, 1),
                "walk_min": round(sec / 60, 1), "transfers": 0, "ride_min": 0.0,
                "quiet_total_min": round(sec / 60, 1), "quiet_hour": self.quiet_hour(),
                "timetable_ride_min": 0.0, "observed_share": 0.0, "hour_basis": "walking only",
                "legs": [self._walk(o, d, depart, sec)]}

    def _walk(self, a: Place, b: Place, t, sec):
        return {"mode": "walk", "from": {"name": a.label, "lat": a.lat, "lon": a.lon},
                "to": {"name": b.label, "lat": b.lat, "lon": b.lon},
                "start": t.isoformat(), "minutes": round(sec / 60, 1)}

    def _path(self, r, i, j):
        lo, hi = r.stop_dist[i], r.stop_dist[j]
        k0 = max(0, int(np.searchsorted(r.shape_cum, lo)) - 1)
        k1 = min(len(r.shape_cum), int(np.searchsorted(r.shape_cum, hi)) + 1)
        pts = r.shape_latlon[k0:k1]
        step = max(1, len(pts) // 200)
        return [[round(float(a), 5), round(float(b), 5)] for a, b in pts[::step]]

    def hour_basis(self, when: datetime) -> str:
        """Where this hour's traffic factor comes from, in words a rider can read."""
        _, src = self.model.hour_factor(day_type(when), when.hour)
        if src.startswith("nearest:"):
            return f"no bus data logged at {when.hour}:00 yet, using {src.split(':')[1]}:00"
        if src.startswith("*:") and src != "*:*":
            return f"bus data at {when.hour}:00, weekdays and weekends pooled"
        if src == "*:*":
            return "no hourly bus data yet, using the all-day average"
        return f"bus data at {when.hour}:00 on {day_type(when)}s"

    def quiet_hour(self):
        """Least congested hour between 06:00 and 23:00 that has its own data."""
        best = None
        for h in range(6, 24):
            key = f"*:{h}"
            if key in self.model.R and (best is None or self.model.R[key] < self.model.R[f"*:{best}"]):
                best = h
        return best if best is not None else 22
