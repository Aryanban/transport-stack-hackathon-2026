"""Turn raw GTFS-RT positions into observed stop-to-stop travel times.

For each vehicle run (vehicle_id + trip_id):
1. Project every GPS point onto its route's shape (distance along, offset).
2. Drop points more than OFFSET_M off the road and points that imply an
   impossible speed or move backwards beyond GPS jitter.
3. Interpolate the time the bus passed each stop, using the two GPS points
   either side of it, if they are at most MAX_GAP_S apart.
4. Each pair of consecutive passed stops gives one observation. Dwell at the
   stop and waiting at signals are inside the observation by design: a rider
   experiences them as part of the ride.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from .gpslog import read_file
from .network import Network, ROOT, to_xy

LOG_DIR = ROOT / "data" / "gps_log"
OBS_FILE = ROOT / "data" / "ps1" / "segment_obs.csv.gz"            # what the model fits on
LIVE_OBS_FILE = ROOT / "data" / "ps1" / "segment_obs_live.csv.gz"  # from our own GTFS-RT log
ARCHIVE_OBS_DIR = ROOT / "data" / "raw" / "obs"                    # from the October archive
OFFSET_M = 60          # max distance from the route shape
MAX_GAP_S = 150        # max gap between the two GPS points bracketing a stop
MAX_SPEED_MS = 25.0    # 90 km/h: faster implied moves are GPS jumps
BACKTRACK_M = 40       # jitter allowed backwards along the shape
SEARCH_AHEAD_M = 4000  # window ahead of the last good point when projecting
OBS_COLS = ["route_id", "from_stop", "to_stop", "idx", "t0", "travel_s", "dist_m", "vehicle_id"]


def read_logs(files) -> pd.DataFrame:
    """Read hourly logs; a cut-off write only loses its own partial rows."""
    frames = [read_file(f) for f in files]
    frames = [f for f in frames if len(f)]
    if not frames:
        return pd.DataFrame(columns=["ts", "vehicle_id", "route_id", "trip_id", "lat", "lon"])
    df = pd.concat([f.astype({"vehicle_id": str, "route_id": str, "trip_id": str}) for f in frames],
                   ignore_index=True)
    return df.drop_duplicates(["vehicle_id", "ts"])


def match_run(route, ts, x, y):
    """Return (stop_index, pass_time) pairs for one run, in order."""
    order = np.argsort(ts, kind="stable")
    ts, x, y = ts[order], x[order], y[order]
    # first pass: unconstrained projection to find a start, then walk forward
    d0, off0 = route.project(x[:1], y[:1])
    if off0[0] > OFFSET_M:
        good = np.nonzero(route.project(x, y)[1] <= OFFSET_M)[0]
        if not len(good):
            return []
        start = good[0]
        ts, x, y = ts[start:], x[start:], y[start:]
        d0, _ = route.project(x[:1], y[:1])
    keep_t, keep_d = [ts[0]], [float(d0[0])]
    for i in range(1, len(ts)):
        last = keep_d[-1]
        d, off = route.project(x[i:i + 1], y[i:i + 1], lo=last - BACKTRACK_M, hi=last + SEARCH_AHEAD_M)
        if not np.isfinite(off[0]) or off[0] > OFFSET_M:
            continue
        dt = ts[i] - keep_t[-1]
        if dt <= 0:
            continue
        step = float(d[0]) - last
        if step > MAX_SPEED_MS * dt:
            continue
        keep_t.append(ts[i])
        keep_d.append(max(last, float(d[0])))
    if len(keep_t) < 2:
        return []
    kt, kd = np.array(keep_t, float), np.array(keep_d)
    passes = []
    for k, sd in enumerate(route.stop_dist):
        j = np.searchsorted(kd, sd, side="right")  # first point beyond the stop
        if j == 0 or j >= len(kd):
            continue
        t1, t2, d1, d2 = kt[j - 1], kt[j], kd[j - 1], kd[j]
        if t2 - t1 > MAX_GAP_S or d2 <= d1:
            continue
        passes.append((k, t1 + (sd - d1) / (d2 - d1) * (t2 - t1)))
    return passes


def observations(net: Network, df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    df = df[df.route_id.isin(net.routes.keys())]
    x, y = to_xy(df.lat.to_numpy(), df.lon.to_numpy())
    df = df.assign(x=x, y=y)
    for (vid, trip, rid), g in df.groupby(["vehicle_id", "trip_id", "route_id"], sort=False):
        if len(g) < 3:
            continue
        route = net.routes[rid]
        passes = match_run(route, g.ts.to_numpy(float), g.x.to_numpy(), g.y.to_numpy())
        for (k1, t1), (k2, t2) in zip(passes, passes[1:]):
            if k2 != k1 + 1 or t2 <= t1:
                continue
            rows.append((rid, route.stops[k1], route.stops[k2], k1, t1, t2 - t1,
                         route.stop_dist[k2] - route.stop_dist[k1], vid))
    return pd.DataFrame(rows, columns=OBS_COLS)


def _day_observations(fs):
    from .network import load
    return observations(load(), read_logs(fs))


def build_observations(net: Network, log_dir=LOG_DIR, out=OBS_FILE, workers=None) -> pd.DataFrame:
    """Rebuild observations from every hourly log, one day per process.
    Runs crossing midnight are split at the day boundary."""
    files = sorted(Path(log_dir).glob("*.csv.gz"))
    by_day = {}
    for f in files:
        by_day.setdefault(f.name[:8], []).append(f)
    days = sorted(by_day)
    parts = []
    if len(days) > 1:
        with ProcessPoolExecutor(max_workers=workers or min(len(days), 4)) as pool:
            results = list(pool.map(_day_observations, [by_day[d] for d in days]))
    else:
        results = [observations(net, read_logs(by_day[d])) for d in days]
    for day, obs in zip(days, results):
        parts.append(obs)
        print(f"{day}: {len(by_day[day])} files -> {len(obs)} segment observations", flush=True)
    result = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=OBS_COLS)
    result = result.drop_duplicates(["vehicle_id", "route_id", "idx", "t0"])
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(LIVE_OBS_FILE, index=False)
    return write_combined(out)


def write_combined(out=OBS_FILE) -> pd.DataFrame:
    """Join our own live-log observations with the October archive's, tagged by source."""
    parts = []
    if LIVE_OBS_FILE.exists():
        parts.append(pd.read_csv(LIVE_OBS_FILE, dtype={"route_id": str, "from_stop": str, "to_stop": str})
                     .assign(source="live"))
    for f in sorted(ARCHIVE_OBS_DIR.glob("*.csv.gz")):
        parts.append(pd.read_csv(f, dtype={"route_id": str, "from_stop": str, "to_stop": str})
                     .assign(source="archive"))
    result = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=OBS_COLS + ["source"])
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    return result


if __name__ == "__main__":
    from .network import load
    obs = build_observations(load())
    print(f"total {len(obs)} observations, {obs[['from_stop', 'to_stop']].drop_duplicates().shape[0]} stop pairs")
