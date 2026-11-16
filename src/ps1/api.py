"""PS1 API: bus journeys timed by a traffic model learned from bus GPS.

Run:  python -m uvicorn src.ps1.api:app --port 8020
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .live import LiveTracker
from .model import IST, MODEL_FILE, TravelModel
from .network import load
from .planner import Planner
from .validation import REPORT

WEB = Path(__file__).parent / "web"
app = FastAPI(title="Delhi bus journey planner (PS1)", version="1.0",
              description="Bus journeys between two points, timed by a travel-time model learned "
                          "from Delhi bus GPS, with optional live adjustment from GTFS-RT.")


@lru_cache(maxsize=1)
def state():
    net = load()
    model = TravelModel.load(MODEL_FILE)
    live = None
    if os.getenv("PS1_LIVE", "1") == "1":
        from src.gtfs_rt_client import DelhiGTFSRealtimeClient
        client = DelhiGTFSRealtimeClient()
        if client.api_key:
            live = LiveTracker(net, model, client)
            live.start()
    return net, model, live, Planner(net, model, live)


def parse_depart(value: str | None) -> datetime:
    if not value:
        return datetime.now(IST).replace(second=0, microsecond=0)
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        try:
            hh, mm = value.split(":")[:2]
            dt = datetime.now(IST).replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        except ValueError:
            raise HTTPException(400, "depart must be YYYY-MM-DDTHH:MM or HH:MM (IST)") from None
    return dt if dt.tzinfo else dt.replace(tzinfo=IST)


@app.get("/journeys", summary="Bus journey options between two places")
def journeys(from_: str = Query(..., alias="from", description="Stop name, stop_id, or 'lat,lon'"),
             to: str = Query(..., description="Stop name, stop_id, or 'lat,lon'"),
             depart: str | None = Query(None, description="YYYY-MM-DDTHH:MM or HH:MM in IST; default now")):
    *_, planner = state()
    try:
        return planner.plan(from_, to, parse_depart(depart))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None


@app.get("/journeys/day", summary="Fastest door-to-door time for the same trip at each hour")
def journeys_day(from_: str = Query(..., alias="from"), to: str = Query(...),
                 date: str | None = Query(None, description="YYYY-MM-DD, default today (IST)")):
    net, model, _, _ = state()
    historical = Planner(net, model, None)  # typical day, no live adjustment
    try:
        day = datetime.fromisoformat(date).date() if date else datetime.now(IST).date()
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD") from None
    rows = []
    try:
        for h in range(5, 24):
            plan = historical.plan(from_, to, datetime(day.year, day.month, day.day, h, tzinfo=IST))
            best = plan["options"][0] if plan["options"] else None
            rows.append({"hour": h, "total_min": best["total_min"] if best else None,
                         "ride_min": best["ride_min"] if best else None})
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from None
    return {"date": day.isoformat(), "hours": rows}


@app.get("/stops", summary="Search stops by name")
def stops(q: str = Query(..., min_length=2)):
    *_, planner = state()
    return planner.search_stops(q)


@app.get("/stops/all", summary="Every served bus stop as GeoJSON points, for the map")
@lru_cache(maxsize=1)
def stops_all():
    net, *_ , planner = state()
    feats = [{"type": "Feature", "properties": {"id": s, "name": net.stops[s][0], "routes": len(net.stop_routes[s])},
              "geometry": {"type": "Point", "coordinates": [round(net.stops[s][2], 6), round(net.stops[s][1], 6)]}}
             for s in planner.stop_ids]
    return {"type": "FeatureCollection", "features": feats}


@app.get("/stops/{stop_id}/departures", summary="Next buses at a stop")
def stop_departures(stop_id: str, depart: str | None = Query(None, description="YYYY-MM-DDTHH:MM in IST; default now")):
    net, *_, planner = state()
    if stop_id not in net.stops:
        raise HTTPException(404, "No such stop.")
    name, lat, lon = net.stops[stop_id]
    when = parse_depart(depart)
    return {"id": stop_id, "name": name, "lat": lat, "lon": lon, "at": when.isoformat(),
            "departures": planner.departures(stop_id, when)}


@app.get("/routes", summary="Find bus routes by number")
def routes(q: str = Query(..., min_length=1)):
    *_, planner = state()
    return planner.find_routes(q)


@app.get("/routes/{route_id}", summary="A bus route: its path, stops, first and last bus, and how often it runs")
def route(route_id: str):
    net, *_, planner = state()
    if route_id not in net.routes:
        raise HTTPException(404, "No such route.")
    return planner.route_detail(route_id)


@app.get("/traffic/hours", summary="City-wide congestion factor by hour")
def traffic_hours():
    _, model, _, _ = state()
    rows = []
    for h in range(24):
        for d in ("weekday", "weekend"):
            f, src = model.hour_factor(d, h)
            rows.append({"hour": h, "daytype": d, "factor": round(f, 3), "source": src,
                         "observations": model.n_hour.get(f"{d}:{h}", 0)})
    return {"note": "Factor 1.0 = all-day average. 1.3 = buses take 30% longer.", "hours": rows,
            "days_logged": model.days, "observations": model.n_obs}


@app.get("/traffic/stretches", summary="Predicted bus speed on observed stretches at an hour")
def traffic_stretches(hour: int = Query(9, ge=0, le=23), daytype: str = Query("weekday", pattern="^(weekday|weekend)$"),
                      min_obs: int = Query(3, ge=1)):
    net, model, _, _ = state()
    feats = []
    done = set()
    for route in net.routes.values():
        for k in range(len(route.stops) - 1):
            key = f"{route.stops[k]}>{route.stops[k + 1]}"
            if key in done or model.pair.get(key, (1, 0))[1] < min_obs:
                continue
            done.add(key)
            dist = float(route.stop_dist[k + 1] - route.stop_dist[k])
            sec, n = model.predict(route.stops[k], route.stops[k + 1], dist, hour, daytype)
            a, b = net.stops[route.stops[k]], net.stops[route.stops[k + 1]]
            feats.append({"type": "Feature", "properties": {"kmh": round(dist / sec * 3.6, 1), "n": n},
                          "geometry": {"type": "LineString", "coordinates": [[a[2], a[1]], [b[2], b[1]]]}})
    return {"type": "FeatureCollection", "features": feats}


@app.get("/live/status", summary="Live feed status")
def live_status():
    _, _, live, _ = state()
    return live.status() if live else {"enabled": False, "fresh": False}


@app.get("/live/vehicles", summary="Current bus positions")
def live_vehicles(route: str | None = None):
    net, _, live, _ = state()
    if not live:
        return []
    out = []
    for v in live.snapshot():
        if route and v["route_id"] != route and net.routes[v["route_id"]].name != route:
            continue
        out.append({"id": v["vehicle_id"], "route": net.routes[v["route_id"]].name, "lat": v["latitude"],
                    "lon": v["longitude"], "ts": v["timestamp"],  # feed speed field is unreliable, omitted
                    "heading": v["heading"]})
    return out


@app.get("/metro/network", summary="Delhi Metro stations, for map context only")
@lru_cache(maxsize=1)
def metro_network():
    from .metro import stations
    return stations()


@app.get("/validation", summary="Held-out accuracy report")
def validation():
    if not REPORT.exists():
        raise HTTPException(404, "Run: python -m src.ps1.validation")
    return json.loads(REPORT.read_text())


if WEB.exists():
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/accuracy", include_in_schema=False)
    def accuracy_page():
        return FileResponse(WEB / "accuracy.html")
