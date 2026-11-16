"""Static GTFS network for PS1: one stop pattern and one road shape per route.

Each route's stops are placed at a distance along the route shape (linear
referencing). GPS points are later projected onto the same shape, so a bus's
progress and each stop's position share one coordinate.
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
GTFS = ROOT / "data" / "delhi_buses_gtfs"
CACHE = ROOT / "data" / "ps1" / "network.pkl"
EARTH_M = 6_371_000.0
REF_LAT = 28.62  # local equirectangular projection centred on Delhi
KX = math.radians(1) * EARTH_M * math.cos(math.radians(REF_LAT))
KY = math.radians(1) * EARTH_M


def to_xy(lat, lon):
    return np.asarray(lon, float) * KX, np.asarray(lat, float) * KY


def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_M * np.arcsin(np.sqrt(a))


@dataclass
class Route:
    id: str
    name: str
    desc: str
    stops: tuple                 # stop_ids in travel order
    stop_dist: np.ndarray        # metres along shape for each stop
    sched_offset: np.ndarray     # median scheduled seconds from first stop
    shape_xy: np.ndarray         # (n, 2) polyline in local metres
    shape_cum: np.ndarray        # cumulative metres at each vertex
    shape_latlon: np.ndarray     # (n, 2) for drawing
    departures: np.ndarray = field(default_factory=lambda: np.zeros(0, int))  # first-stop departures, s after midnight

    def project(self, x, y, lo=None, hi=None):
        """Project points onto the shape. Returns (dist_along_m, offset_m).

        lo/hi restrict the search to a window of shape distance, which stops a
        point on a looping route from snapping to the wrong pass.
        """
        a, b = self.shape_xy[:-1], self.shape_xy[1:]
        seg = b - a
        seg_len2 = np.maximum((seg ** 2).sum(1), 1e-9)
        px = np.stack([np.atleast_1d(x), np.atleast_1d(y)], 1)[:, None, :]
        t = np.clip(((px - a) * seg).sum(2) / seg_len2, 0, 1)
        proj = a + t[..., None] * seg
        off = np.sqrt(((px - proj) ** 2).sum(2))
        along = self.shape_cum[:-1] + t * np.sqrt(seg_len2)
        if lo is not None:
            bad = (along < np.atleast_1d(lo)[:, None]) | (along > np.atleast_1d(hi)[:, None])
            off = np.where(bad, np.inf, off)
        k = off.argmin(1)
        rows = np.arange(len(k))
        return along[rows, k], off[rows, k]


@dataclass
class Network:
    stops: dict                  # stop_id -> (name, lat, lon)
    routes: dict                 # route_id -> Route
    stop_routes: dict            # stop_id -> list[(route_id, index)]

    def stop_xy(self, stop_id):
        _, lat, lon = self.stops[stop_id]
        return to_xy(lat, lon)


def _secs(v):
    h, m, s = v.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


def build(gtfs=GTFS) -> Network:
    stops_df = pd.read_csv(gtfs / "stops.txt", dtype={"stop_id": str})
    stops = {r.stop_id: (r.stop_name, float(r.stop_lat), float(r.stop_lon)) for r in stops_df.itertuples()}
    routes_df = pd.read_csv(gtfs / "routes.txt", dtype=str).set_index("route_id")
    trips = pd.read_csv(gtfs / "trips.txt", dtype=str)
    st = pd.read_csv(gtfs / "stop_times.txt", usecols=["trip_id", "departure_time", "stop_id", "stop_sequence"],
                     dtype={"trip_id": str, "stop_id": str})
    st = st.sort_values(["trip_id", "stop_sequence"])
    st["sec"] = st["departure_time"].map(_secs)
    st["off"] = st["sec"] - st.groupby("trip_id")["sec"].transform("first")
    st["idx"] = st.groupby("trip_id").cumcount()
    st = st.merge(trips[["trip_id", "route_id", "shape_id"]], on="trip_id")
    first = st[st.idx == 0].groupby("route_id")["sec"].apply(lambda s: np.sort(s.to_numpy()))
    offsets = st.groupby(["route_id", "idx"])["off"].median()
    seqs = st.groupby("route_id").apply(lambda g: tuple(g[g.trip_id == g.trip_id.iloc[0]].stop_id), include_groups=False)
    shape_of = trips.groupby("route_id")["shape_id"].first()

    shapes = pd.read_csv(gtfs / "shapes.txt", dtype={"shape_id": str}).sort_values(["shape_id", "shape_pt_sequence"])
    shape_pts = {sid: g[["shape_pt_lat", "shape_pt_lon"]].to_numpy() for sid, g in shapes.groupby("shape_id")}

    routes, stop_routes = {}, {}
    for rid, seq in seqs.items():
        seq = tuple(s for s in seq if s in stops)
        if len(seq) < 2:
            continue
        stop_ll = np.array([stops[s][1:] for s in seq])
        pts = shape_pts.get(shape_of.get(rid))
        r = _make_route(rid, routes_df, seq, stop_ll, pts, offsets.loc[rid].to_numpy(float)[:len(seq)],
                        first.get(rid, np.zeros(0, int)))
        if r is None:
            continue
        routes[rid] = r
        for i, s in enumerate(seq):
            stop_routes.setdefault(s, []).append((rid, i))
    return Network(stops, routes, stop_routes)


def _polyline(latlon):
    x, y = to_xy(latlon[:, 0], latlon[:, 1])
    xy = np.stack([x, y], 1)
    cum = np.concatenate([[0], np.cumsum(np.sqrt((np.diff(xy, axis=0) ** 2).sum(1)))])
    return xy, cum


def _make_route(rid, routes_df, seq, stop_ll, pts, sched, departures):
    meta = routes_df.loc[rid] if rid in routes_df.index else None
    name = (meta.route_short_name if meta is not None else rid) or rid
    desc = (meta.route_desc if meta is not None and isinstance(meta.route_desc, str) else "")
    for source in (pts, stop_ll):
        if source is None or len(source) < 2:
            continue
        xy, cum = _polyline(source)
        r = Route(rid, name, desc, seq, np.zeros(len(seq)), sched, xy, cum, source, departures)
        sx, sy = to_xy(stop_ll[:, 0], stop_ll[:, 1])
        # place stops in order: each stop searched forward from the previous one
        dist, prev = [], 0.0
        ok = True
        for x, y in zip(sx, sy):
            d, off = r.project(x, y, lo=prev - 50, hi=prev + 20_000)
            if not np.isfinite(off[0]) or off[0] > 250:
                ok = False
                break
            prev = max(prev, float(d[0]))
            dist.append(prev)
        if ok:
            r.stop_dist = np.array(dist)
            return r
    return None


def load(rebuild=False) -> Network:
    if CACHE.exists() and not rebuild:
        with open(CACHE, "rb") as fh:
            return pickle.load(fh)
    net = build()
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE, "wb") as fh:
        pickle.dump(net, fh, protocol=pickle.HIGHEST_PROTOCOL)
    return net


if __name__ == "__main__":
    import time
    from src.ps1.network import load as _load  # pickle classes under their import path, not __main__
    t = time.time()
    net = _load(rebuild=True)
    lens = [r.stop_dist[-1] / 1000 for r in net.routes.values()]
    print(f"{len(net.routes)} routes, {len(net.stops)} stops in {time.time() - t:.1f}s; "
          f"median route length {np.median(lens):.1f} km")
