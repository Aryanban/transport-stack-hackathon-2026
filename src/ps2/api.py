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
from .timetable import IST, combine_feeds, load_feed, local_time
from .metro_loader import get_metro_network_geojson

app = FastAPI(title="Delhi Bus Planner · Transport Stack PS2", version="2.0")
WEB = Path(__file__).with_name("web")
SOURCE_LOCK = Lock()


@lru_cache(maxsize=1)
def _load_state():
    feed = load_feed(os.getenv("PS2_GTFS", str(ROOT / "data" / "delhi_buses_gtfs")))
    metro_path = os.getenv("PS2_METRO_GTFS")
    if metro_path:
        feed = combine_feeds(feed, load_feed(metro_path, mode="metro"))
    path = Path(os.getenv("PS2_PROFILES", str(DEFAULT_PROFILES)))
    profiles = SegmentProfiles(json.loads(path.read_text(encoding="utf-8")))
    return feed, profiles


def state():
    with SOURCE_LOCK:
        return _load_state()


@app.get("/api/config")
def config():
    feed, profiles = state()
    featured = corridor_options(feed, profiles)
    return {
        "demo": False, "sample": True, "source": profiles.source, "mode": "segment",
        "metroRouting": bool(os.getenv("PS2_METRO_GTFS")),
        "liveConfigured": bool(os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")),
        "defaultTime": datetime.now(IST).replace(hour=18, minute=0).strftime("%Y-%m-%dT%H:%M"),
        "origin": featured[0]["from"] if featured else None,
        "destination": featured[0]["to"] if featured else None,
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


@app.get("/api/metro/network")
def metro_network():
    """Returns dynamically parsed DMRC Metro network GeoJSON with stations and lines."""
    return get_metro_network_geojson()


def to_title_case(text: str) -> str:
    """Formats raw GTFS uppercase stop names into clean readable title case."""
    words = text.split()
    acronyms = {"ISBT", "DMRC", "DTC", "AIIMS", "ETM", "CBD", "TAZ", "GPO", "GGS", "SEC", "INA", "NDLS"}
    result = []
    for w in words:
        clean = w.strip("(),.-").upper()
        if clean in acronyms:
            result.append(clean)
        elif "/" in w:
            result.append("/".join(p.capitalize() for p in w.split("/")))
        else:
            result.append(w.capitalize())
    return " ".join(result)


def corridor_options(feed, profiles):
    candidates = []
    for pattern in sorted(feed.patterns):
        route, _, stops = pattern
        if route not in profiles.anchors:
            continue
        projected = profiles.project(pattern)
        for start in projected:
            if start - 1 in projected:
                continue
            stop = start
            while stop in projected and stop - start < 6:
                stop += 1
            if stop - start < 2:
                continue
            candidates.append((-(stop - start), route, stops[start], stops[stop]))
    featured = []
    routes = set()
    for distance, route, start, stop in sorted(candidates):
        if route in routes:
            continue
        origin, destination = (dict(feed.stops[key]) for key in (start, stop))
        origin["name"] = to_title_case(origin["name"])
        destination["name"] = to_title_case(destination["name"])
        featured.append({"route": feed.routes[route], "label": f"{origin['name']} to {destination['name']}",
                         "from": origin, "to": destination, "stop_count": 1 - distance})
        routes.add(route)
    return featured


@app.get("/api/corridors")
def corridors():
    """Suggest distinct stretches with stop order and crowd coverage from the feed."""
    return {"corridors": corridor_options(*state())}


@app.get("/api/vehicles")
def vehicles(route: str = Query("", description="Optional route filter e.g. '502' or '1995'")):
    if not (os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")):
        return {"status": "disabled", "positions": []}
    try:
        records = live_client().fetch_vehicle_positions()
    except ImportError:
        return {"status": "unavailable", "positions": []}
    
    now = datetime.now(IST).timestamp()
    clean_route = route.strip().upper().replace("BUS_", "")

    positions = []
    live_ids = set()

    for v in records:
        ts = v.get("timestamp")
        if not isinstance(ts, (int, float)) or not (0 <= now - ts <= 300) or v.get("source") != "live":
            continue
        
        vehicle_id = v.get("vehicle_id")
        if not vehicle_id or vehicle_id in live_ids:
            continue
        if not (-90 <= v["latitude"] <= 90 and -180 <= v["longitude"] <= 180):
            continue
        live_ids.add(vehicle_id)

        v_route = str(v.get("route_id", "")).upper()
        if clean_route:
            if clean_route != v_route and clean_route not in v_route:
                continue

        positions.append({
            "lat": v["latitude"],
            "lon": v["longitude"],
            "timestamp": ts,
            "vehicle_id": vehicle_id,
            "route_id": v.get("route_id", ""),
            "speed_kmh": v.get("speed_kmh"),
            "trip_id": v.get("trip_id", ""),
            "bearing": v.get("bearing", 0.0),
            "age_seconds": round(now - ts, 1)
        })

    return {
        "status": "live" if live_ids else "unavailable",
        "positions": positions,
        "count": len(positions),
        "total_live_fleet": len(live_ids),
        "timestamp": max((p["timestamp"] for p in positions), default=None)
    }


app.mount("/", StaticFiles(directory=WEB, html=True), name="ps2-ui")
