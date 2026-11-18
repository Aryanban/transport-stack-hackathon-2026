"""Validate predicted bus ride times against held-out observed bus trips.

Ground truth: whole sub-trips of real buses (5 to 30 consecutive stops of one
vehicle run), taken from the GPS log and never used for fitting.
Split: with the October archive loaded, its last 7 days are held out and the
model is fitted on the rest. Otherwise, with 3 or more days logged, the last day
is held out; with fewer, 30% of buses are (stated in the report).

Compared estimators for the same sub-trip and departure time:
  model      learned model (this package), historical only, no live data
  timetable  GTFS scheduled time between the two stops
  flat       one city-wide average speed for all hours

Google Maps: put rows in data/ps1/google_benchmark.csv with columns
origin,destination,depart,google_min (depart as YYYY-MM-DDTHH:MM, IST).
The report then adds the planner's door-to-door estimate against them.
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd

from .matcher import OBS_FILE
from .model import IST, add_time_fields, day_type, fit, read_obs
from .network import ROOT, load

REPORT = ROOT / "data" / "ps1" / "validation.json"
GOOGLE = ROOT / "data" / "ps1" / "google_benchmark.csv"
MIN_STOPS, MAX_STOPS = 5, 30
MAX_SUBTRIPS = 50_000


TEST_DAYS = 7


def split(obs, seed=7):
    if "source" in obs:
        archive_days = sorted(obs.day[obs.source == "archive"].unique())
        if len(archive_days) >= 2 * TEST_DAYS:
            test_days = set(archive_days[-TEST_DAYS:])
            mask = obs.day.isin(test_days) & (obs.source == "archive")
            return obs[~mask], obs[mask], (f"held-out days {min(test_days)} to {max(test_days)} "
                                          f"(last {TEST_DAYS} days of the October archive)")
    days = sorted(obs.day.unique())
    if len(days) >= 3:
        test_day = days[-1]
        return obs[obs.day != test_day], obs[obs.day == test_day], f"held-out day {test_day}"
    # Under 3 days, the earlier days do not cover the last day's hours, so hold out
    # 30% of buses instead: their runs are never seen in fitting, at every hour.
    buses = np.sort(obs.vehicle_id.unique())
    rng = np.random.default_rng(seed)
    test_buses = set(rng.choice(buses, size=int(len(buses) * 0.3), replace=False))
    mask = obs.vehicle_id.isin(test_buses)
    return obs[~mask], obs[mask], f"30% of buses held out ({len(days)} days logged; held-out day from 3 days)"


def subtrips(test, rng):
    """Chains of consecutive stretches from one bus run, cut into sub-trips."""
    out = []
    test = test.sort_values(["vehicle_id", "route_id", "t0"])
    for (_, rid), g in test.groupby(["vehicle_id", "route_id"], sort=False):
        idx, t0, tr = g.idx.to_numpy(), g.t0.to_numpy(), g.travel_s.to_numpy()
        start = 0
        for k in range(1, len(g) + 1):
            if k == len(g) or idx[k] != idx[k - 1] + 1 or abs(t0[k] - (t0[k - 1] + tr[k - 1])) > 1:
                n = k - start
                pos = start
                while n - (pos - start) >= MIN_STOPS:
                    length = int(rng.integers(MIN_STOPS, min(MAX_STOPS, n - (pos - start)) + 1))
                    out.append((rid, int(idx[pos]), int(idx[pos]) + length, float(t0[pos]),
                                float(tr[pos:pos + length].sum())))
                    pos += length
                start = k
    return pd.DataFrame(out, columns=["route_id", "i", "j", "t0", "observed_s"])


def predict_model(model, route, i, j, start):
    t, total = start, 0.0
    for k in range(i, j):
        sec, _ = model.predict(route.stops[k], route.stops[k + 1],
                               float(route.stop_dist[k + 1] - route.stop_dist[k]), t.hour, day_type(t))
        total += sec
        t = datetime.fromtimestamp(t.timestamp() + sec, IST)
    return total


def metrics(err_s, obs_s):
    ae = np.abs(err_s)
    return {"n": int(len(ae)), "mae_min": round(float(ae.mean() / 60), 2),
            "median_ae_min": round(float(np.median(ae) / 60), 2),
            "mape_pct": round(float((ae / obs_s).mean() * 100), 1),
            "within_20pct": round(float((ae / obs_s <= 0.2).mean() * 100), 1),
            "bias_min": round(float(np.mean(err_s) / 60), 2)}


def run(seed=7):
    net = load()
    obs = add_time_fields(read_obs(OBS_FILE))
    train, test, split_note = split(obs)
    model = fit(train)
    trips = subtrips(test, np.random.default_rng(seed))
    trips = trips[trips.route_id.isin(net.routes.keys())]
    if len(trips) > MAX_SUBTRIPS:  # a random sample keeps the report quick on a month of data
        trips = trips.sample(MAX_SUBTRIPS, random_state=seed)
    rows = []
    flat_mps = train.dist_m.sum() / train.travel_s.sum()
    for r in trips.itertuples():
        route = net.routes[r.route_id]
        start = datetime.fromtimestamp(r.t0, IST)
        dist = float(route.stop_dist[r.j] - route.stop_dist[r.i])
        rows.append({
            "observed": r.observed_s,
            "model": predict_model(model, route, r.i, r.j, start),
            "timetable": float(route.sched_offset[r.j] - route.sched_offset[r.i]),
            "flat": dist / flat_mps,
            "hour": start.hour, "daytype": day_type(start),
        })
    res = pd.DataFrame(rows)
    report = {"generated": datetime.now(IST).isoformat(timespec="seconds"), "split": split_note,
              "train_observations": int(len(train)), "test_subtrips": int(len(res)),
              "days_logged": sorted(str(d) for d, n in obs.day.value_counts().items() if n >= 1000),
              "estimators": {}, "by_period": {}}
    if len(res):
        for est in ("model", "timetable", "flat"):
            report["estimators"][est] = metrics(res[est] - res.observed, res.observed)
        peak = res.hour.isin([8, 9, 10, 17, 18, 19, 20])
        for name, mask in (("peak", peak), ("off_peak", ~peak)):
            if mask.sum():
                report["by_period"][name] = {est: metrics(res[est][mask] - res.observed[mask], res.observed[mask])
                                             for est in ("model", "timetable")}
        report["by_hour"] = [
            {"hour": int(h), "n": int(len(g)),
             "model_mae_min": round(float((g.model - g.observed).abs().mean() / 60), 2),
             "timetable_mae_min": round(float((g.timetable - g.observed).abs().mean() / 60), 2)}
            for h, g in res.groupby("hour")]
        sample = res.sample(min(len(res), 600), random_state=seed)
        report["points"] = [{"observed_min": round(r.observed / 60, 2), "model_min": round(r.model / 60, 2),
                             "timetable_min": round(r.timetable / 60, 2), "hour": int(r.hour)}
                            for r in sample.itertuples()]
    report["coverage"] = {
        "observations": int(len(obs)), "vehicles": int(obs.vehicle_id.nunique()),
        "stretches": int(obs.groupby(["from_stop", "to_stop"]).ngroups),
        "stretches_3plus": int((obs.groupby(["from_stop", "to_stop"]).size() >= 3).sum()),
        "routes": int(obs.route_id.nunique()), "routes_total": len(net.routes),
        "hours_with_data": sorted(int(h) for h, n in obs.groupby("hour").size().items() if n >= 30),
        "sources": source_summary(obs),
        "first": datetime.fromtimestamp(float(obs.t0.min()), IST).isoformat(timespec="minutes"),
        "last": datetime.fromtimestamp(float(obs.t0.max()), IST).isoformat(timespec="minutes"),
    }
    report["google"] = google_report()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2))
    return report


def source_summary(obs, min_obs=1000):
    """Observations and days per data source. A day counts if it has at least min_obs observations,
    so the few timings just before midnight in a daily file do not add a day."""
    if "source" not in obs:
        return []
    out = []
    for src, g in obs.groupby("source", observed=True):
        n = g.day.value_counts()
        days = sorted(str(d) for d in n[n >= min_obs].index)
        if days:
            out.append({"source": str(src), "observations": int(len(g)), "days": len(days),
                        "first_day": days[0], "last_day": days[-1]})
    return out


def google_report():
    if not GOOGLE.exists():
        return {"status": f"no benchmark file at {GOOGLE.relative_to(ROOT)}"}
    from .model import TravelModel
    from .planner import Planner
    bench = pd.read_csv(GOOGLE).dropna(subset=["google_min"])
    planner = Planner(load(), TravelModel.load())
    out = []
    for b in bench.itertuples():
        depart = datetime.fromisoformat(b.depart).replace(tzinfo=IST)
        plan = planner.plan(b.origin, b.destination, depart)
        ours = plan["options"][0]["total_min"] if plan["options"] else None
        out.append({"origin": b.origin, "destination": b.destination, "depart": b.depart,
                    "google_min": float(b.google_min), "ours_min": ours})
    ok = [o for o in out if o["ours_min"] is not None]
    if not ok:
        return {"pairs": out}
    err = np.array([o["ours_min"] - o["google_min"] for o in ok])
    g = np.array([o["google_min"] for o in ok])
    return {"pairs": out, "n": len(ok), "mae_min": round(float(np.abs(err).mean()), 1),
            "mape_pct": round(float((np.abs(err) / g).mean() * 100), 1),
            "within_20pct": round(float((np.abs(err) / g <= 0.2).mean() * 100), 1)}


if __name__ == "__main__":
    rep = run()
    print(f"split: {rep['split']}; {rep['test_subtrips']} held-out sub-trips")
    for est, m in rep["estimators"].items():
        print(f"  {est:9s} MAE {m['mae_min']} min  MAPE {m['mape_pct']}%  within 20%: {m['within_20pct']}%  bias {m['bias_min']}")
    print("google:", {k: v for k, v in rep["google"].items() if k != "pairs"})
