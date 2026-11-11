"""FastAPI entry point for the bus-only PS2 planner."""
import json
import os
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from .model import DEFAULT_PROFILES, ROOT, SegmentProfiles, tier
from .ranking import recommend
from .timetable import IST, load_feed, local_time

app = FastAPI(title="Delhi Bus Planner · Transport Stack PS2", version="2.0")
WEB = Path(__file__).with_name("web")
SOURCE_LOCK = Lock()


@lru_cache(maxsize=1)
def _load_state():
    feed = load_feed(os.getenv("PS2_GTFS", str(ROOT / "data" / "delhi_buses_gtfs")))
    path = Path(os.getenv("PS2_PROFILES", str(DEFAULT_PROFILES)))
    profiles = SegmentProfiles(json.loads(path.read_text(encoding="utf-8")))
    return feed, profiles


def state():
    with SOURCE_LOCK:
        return _load_state()


@app.get("/api/config")
def config():
    feed, profiles = state()
    return {
        "demo": False, "sample": True, "source": profiles.source, "mode": "segment",
        "liveConfigured": bool(os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")),
        "defaultTime": "2026-11-11T18:00",
        "origin": feed.stops.get("2070"), "destination": feed.stops.get("1025"),
    }


@app.get("/api/stops")
def stops(q: str = Query("", max_length=80)):
    term = q.strip().casefold()
    if not term:
        return []
    feed, _ = state()
    hits = [stop for stop in feed.stops.values()
            if stop["id"] in feed.departures and (term in stop["name"].casefold() or term == stop["id"])]
    hits.sort(key=lambda stop: (term != stop["id"], not stop["name"].casefold().startswith(term),
                                stop["name"], stop["id"]))
    return hits[:12]


@app.get("/api/journeys")
def journeys(origin: str, destination: str, departure: str, extra: int = Query(15, ge=0, le=60)):
    feed, profiles = state()
    if origin == destination or origin not in feed.stops or destination not in feed.stops:
        raise HTTPException(400, "Select two different stops from the suggestions.")
    try:
        start = local_time(departure)
        if not 1900 <= start.year <= 2100:
            raise ValueError
    except (ValueError, OverflowError):
        raise HTTPException(400, "Enter a valid departure date and time.") from None
    return recommend(feed, profiles, origin, destination, start, extra)


@app.get("/api/crowding")
def crowding(route: str, hour: int = Query(18, ge=0, le=23), weekend: bool = False):
    _, profiles = state()
    route = route.upper()
    topology = profiles.data["stops"].get(route)
    if topology is None:
        raise HTTPException(404, "No sample corridor with this route ID.")
    segments = []
    for i, (start, end) in enumerate(zip(topology, topology[1:])):
        cell = profiles.scores.get((route, i, int(weekend), hour))
        segments.append({"from": start, "to": end, "segment": i + 1,
                         "level": tier(cell["load"] / cell["seats"]) if cell else "Unknown",
                         "estimate": cell["load"] if cell else None,
                         "days": cell["days"] if cell else 0,
                         "seats": cell["seats"] if cell else None, "crush": cell["crush"] if cell else None})
    return {"source": profiles.source, "route": route, "hour": hour, "weekend": weekend, "segments": segments}


@app.get("/api/validation")
def validation():
    _, profiles = state()
    return {key: profiles.data[key] for key in ("source", "window", "audit", "calibration_scale", "validation")}


@lru_cache(maxsize=1)
def live_client():
    from ..gtfs_rt_client import DelhiGTFSRealtimeClient
    key = os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")
    return DelhiGTFSRealtimeClient(api_key=key, live_only=True)


@app.get("/api/vehicles")
def vehicles():
    if not (os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")):
        return {"status": "disabled", "positions": []}
    try:
        records = live_client().fetch_vehicle_positions()
    except ImportError:
        return {"status": "unavailable", "positions": []}
    now = datetime.now(IST).timestamp()
    positions = [
        {"lat": v["latitude"], "lon": v["longitude"], "timestamp": v["timestamp"]}
        for v in records
        if isinstance(v.get("timestamp"), (int, float)) and 0 <= now - v["timestamp"] <= 120
        and v.get("source") == "live"
    ]
    return {"status": "live" if positions else "unavailable", "positions": positions,
            "timestamp": max((v["timestamp"] for v in positions), default=None)}


app.mount("/", StaticFiles(directory=WEB, html=True), name="ps2-ui")
