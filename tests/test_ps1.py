"""PS1 checks on the real Delhi GTFS with synthetic GPS whose truth is known."""
from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from src.ps1.live import LiveTracker
from src.ps1.matcher import match_run
from src.ps1.model import IST, TravelModel, fit
from src.ps1.network import load
from src.ps1.planner import Planner


@pytest.fixture(scope="module")
def net():
    return load()


def toy_model(peak=1.5, night=0.7):
    R = {"*:*": 1.0, **{f"*:{h}": 1.0 for h in range(24)}}
    R.update({"*:8": peak, "*:9": peak, "*:23": night})
    return TravelModel(a=15.0, b=0.15, R=R, n_hour={}, pair={}, pair_hour={}, n_obs=0, days=[])


def synthetic_run(route, speed_ms, t0=1_794_800_000, every_s=30, noise_m=8, seed=0):
    """GPS points along the route shape at constant speed, with jitter."""
    rng = np.random.default_rng(seed)
    total = route.stop_dist[-1]
    d = np.arange(0, total, speed_ms * every_s)
    xy = np.stack([np.interp(d, route.shape_cum, route.shape_xy[:, i]) for i in (0, 1)], 1)
    xy += rng.normal(0, noise_m, xy.shape)
    return t0 + np.arange(len(d)) * every_s, xy[:, 0], xy[:, 1]


def test_network_stops_are_ordered_along_shape(net):
    assert len(net.routes) > 2000
    for r in list(net.routes.values())[:300]:
        assert np.all(np.diff(r.stop_dist) >= 0)
        assert len(r.departures) > 0


def test_matcher_recovers_known_speed(net):
    route = net.routes[next(iter(net.routes))]
    speed = 5.0  # 18 km/h
    ts, x, y = synthetic_run(route, speed)
    passes = match_run(route, ts.astype(float), x, y)
    assert len(passes) >= 0.8 * len(route.stops)
    for (k1, t1), (k2, t2) in zip(passes, passes[1:]):
        if k2 == k1 + 1:
            expected = (route.stop_dist[k2] - route.stop_dist[k1]) / speed
            assert abs((t2 - t1) - expected) < 15


def test_matcher_drops_off_route_points(net):
    route = net.routes[next(iter(net.routes))]
    ts, x, y = synthetic_run(route, 5.0)
    x = x.copy()
    x[5] += 3000  # a GPS jump 3 km sideways
    passes = match_run(route, ts.astype(float), x, y)
    assert passes == sorted(passes)  # still monotonic, the jump is ignored


def test_model_learns_hour_and_stretch_effects():
    rng = np.random.default_rng(1)
    rows = []
    base = pd.Timestamp("2026-11-17 00:00", tz=IST).timestamp()
    for n in range(4000):
        hour = int(rng.choice([9, 14]))
        pair = int(rng.integers(0, 50))
        dist = 300 + 10 * pair
        true = (15 + 0.15 * dist) * (1.6 if hour == 9 else 1.0) * (1.3 if pair == 0 else 1.0)
        rows.append(("r", f"s{pair}", f"s{pair + 1}", 0, base + hour * 3600 + rng.integers(0, 3000),
                     true * rng.lognormal(0, 0.1), dist, f"v{n}"))
    obs = pd.DataFrame(rows, columns=["route_id", "from_stop", "to_stop", "idx", "t0", "travel_s", "dist_m", "vehicle_id"])
    m = fit(obs)
    assert m.R["*:9"] / m.R["*:14"] == pytest.approx(1.6, rel=0.08)
    slow, _ = m.predict("s0", "s1", 300, 14, "weekday")
    norm, _ = m.predict("s1", "s2", 300, 14, "weekday")
    assert slow / norm == pytest.approx(1.3, rel=0.1)
    unseen, n = m.predict("x", "y", 400, 14, "weekday")
    assert n == 0 and unseen > 0


def test_planner_gives_rush_hour_longer_rides(net):
    p = Planner(net, toy_model())
    rush = p.plan("Kashmere Gate", "Nehru Place", datetime(2026, 11, 17, 8, 30, tzinfo=IST))
    night = p.plan("Kashmere Gate", "Nehru Place", datetime(2026, 11, 17, 22, 30, tzinfo=IST))
    assert rush["options"] and night["options"]
    r, n = rush["options"][0], night["options"][0]
    assert r["ride_min"] > n["ride_min"]
    for opt in rush["options"]:
        assert opt["legs"][0]["mode"] in ("walk", "bus")
        for leg in opt["legs"]:
            if leg["mode"] == "bus":
                route = net.routes[leg["route_id"]]
                assert leg["from"]["id"] in route.stops and leg["to"]["id"] in route.stops
                assert route.stops.index(leg["from"]["id"]) < route.stops.index(leg["to"]["id"])
        assert opt["arrive"] > opt["depart"]


def test_planner_drops_options_far_behind_the_best(net):
    p = Planner(net, toy_model())
    for a, b in [("Kashmere Gate", "Nehru Place"), ("Anand Vihar", "Connaught Place")]:
        opts = p.plan(a, b, datetime(2026, 11, 17, 17, 30, tzinfo=IST))["options"]
        best = datetime.fromisoformat(opts[0]["arrive"])
        slack = max(30, 0.5 * opts[0]["total_min"])
        assert all((datetime.fromisoformat(o["arrive"]) - best).total_seconds() / 60 <= slack + 0.01 for o in opts)


def test_planner_accepts_coordinates_and_rejects_unknown(net):
    p = Planner(net, toy_model())
    res = p.plan("28.6675,77.2285", "28.5494,77.2510", datetime(2026, 11, 17, 10, 0, tzinfo=IST))
    assert res["options"]
    with pytest.raises(LookupError):
        p.plan("zzzz-nowhere", "Nehru Place", datetime(2026, 11, 17, 10, 0, tzinfo=IST))


def test_live_falls_back_without_fresh_data(net):
    m = toy_model()
    lt = LiveTracker(net, m, client=None)
    assert lt.factor("a", "b", datetime.now(IST)) == 1.0
    route = next(iter(net.routes.values()))
    assert lt.next_arrival(route, 3, datetime.now(IST), Planner(net, m)) is None


def test_api_journeys(monkeypatch):
    monkeypatch.setenv("PS1_LIVE", "0")
    from fastapi.testclient import TestClient
    from src.ps1 import api
    if not api.MODEL_FILE.exists():
        pytest.skip("model.json not built; run python -m src.ps1.model")
    api.state.cache_clear()
    c = TestClient(api.app)
    r = c.get("/journeys", params={"from": "Kashmere Gate", "to": "Nehru Place", "depart": "2026-11-17T08:30"})
    assert r.status_code == 200 and r.json()["options"]
    assert c.get("/journeys", params={"from": "zzzz-nowhere", "to": "Nehru Place"}).status_code == 404
    assert c.get("/journeys", params={"from": "Kashmere Gate", "to": "Nehru Place", "depart": "soon"}).status_code == 400
    page = c.get("/accuracy")
    assert page.status_code == 200 and "How close are our bus times?" in page.text
    home = c.get("/")
    assert home.status_code == 200 and "map3d.js" in home.text and "planner.js" in home.text
    metro = c.get("/metro/network").json()["features"]
    assert metro and all(f["properties"]["type"] == "station" for f in metro)  # no made-up track lines
    spots = [tuple(round(v, 3) for v in f["geometry"]["coordinates"]) for f in metro]
    assert max(spots.count(x) for x in spots) < 3  # placeholder-stacked stations are left out
    assert c.get("/live/vehicles").json() == []  # live off: no buses, never simulated ones
    if api.REPORT.exists():
        rep = c.get("/validation").json()
        assert {"estimators", "coverage", "google"} <= rep.keys()
    api.state.cache_clear()


def test_gps_log_survives_cut_off_write_and_compacts(tmp_path):
    import gzip
    from src.ps1.gpslog import FIELDS, compact, read_file
    f = tmp_path / "20261116_17.csv.gz"
    rows = [",".join(FIELDS)] + [f"{1794828000 + i},V{i % 7},1709,1709_14_32,28.{600000 + i},77.{200000 + i},3.10"
                                 for i in range(1000)]
    with open(f, "wb") as fh:
        fh.write(gzip.compress(("\n".join(rows[:501]) + "\n").encode()))
        fh.write(gzip.compress(("\n".join(rows[501:]) + "\n").encode()))
        fh.write(gzip.compress(b"1794830000,V1,1709,1709_14_32,28.6,77.2,3.1\n" * 50)[:40])  # killed mid-write
    df = read_file(f)
    assert len(df) == 1000  # both complete polls kept, the cut-off one dropped
    _, after = compact(f)
    back = read_file(f)
    assert len(back) == 1000 and after > 0
    assert back.lat.round(6).isin(df.lat.round(6)).all()  # full coordinate precision kept
    assert (tmp_path / "20261116_17.csv.gz.compacted").exists()


def test_live_heading_comes_from_gps_movement():
    from collections import deque
    from src.ps1.live import LiveTracker
    t = LiveTracker.__new__(LiveTracker)
    t.traces = {("bus", "trip", "r"): deque([(0, 0.0, 0.0), (20, 50.0, 50.0), (40, 100.0, 100.0)]),
                ("parked", "trip", "r"): deque([(0, 0.0, 0.0), (20, 3.0, 2.0)])}
    assert t.heading(("bus", "trip", "r")) == 45  # moved north-east
    assert t.heading(("parked", "trip", "r")) is None  # never guessed for a bus that has not moved
    assert t.heading(("unknown", "", "")) is None


def test_live_snapshot_is_safe_while_polling():
    import threading
    from collections import defaultdict, deque
    from src.ps1.live import LiveTracker
    t = LiveTracker.__new__(LiveTracker)
    t._lock = threading.Lock()
    t.traces = defaultdict(deque)
    t.positions = [{"vehicle_id": f"v{i}", "trip_id": "", "route_id": "r"} for i in range(200)]
    stop = threading.Event()

    def writer():  # what the poll thread does, under the same lock
        k = 0
        while not stop.is_set():
            with t._lock:
                for i in range(200):
                    tr = t.traces[(f"v{i}", "", "r")]
                    tr.append((k, float(k), float(k)))
                    if len(tr) > 5:
                        tr.popleft()
            k += 1

    th = threading.Thread(target=writer)
    th.start()
    try:
        for _ in range(300):
            assert len(t.snapshot()) == 200
    finally:
        stop.set()
        th.join()
