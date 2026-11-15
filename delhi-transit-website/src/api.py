"""
Delhi Transport Stack Hackathon 2026 — REST API Server
Provides real-time traffic-modeled journey planning, crowdedness estimation,
and transit analytics.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from pydantic import BaseModel, Field

from .data_loader import get_loaded_network, Stop, Route
from .gtfs_router import JourneyPlanner, JourneyOption
from .traffic_model import BusTrafficModel, LiveVehiclePosition, DEFAULT_HOURLY_SPEED_KMH
from .crowdedness_model import CrowdednessModel, CrowdednessEstimate
from .feeder_optimizer import FeederOptimizer
from .od_extrapolator import ODExtrapolator
from .gtfs_rt_client import DelhiGTFSRealtimeClient
from .ps2.api import app as ps2_app

app = FastAPI(
    title="Delhi Transport Stack Hackathon 2026 API",
    description="Real-Time Bus Traffic Model, Crowdedness Planner, OD Extrapolation & EV Feeder Engine",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize network and engines on startup
network = get_loaded_network()
planner = JourneyPlanner(network)
traffic_model = planner.traffic_model
crowdedness_model = planner.crowdedness_model
feeder_optimizer = FeederOptimizer()
od_extrapolator = ODExtrapolator()
gtfs_rt_client = DelhiGTFSRealtimeClient()

app.mount("/ps2", ps2_app)

class GPSUpdatePayload(BaseModel):
    vehicle_id: str = Field(..., json_schema_extra={"example": "DL1PC1234"})
    route_id: str = Field(..., json_schema_extra={"example": "BUS_102ADOWN"})
    lat: float = Field(..., json_schema_extra={"example": 28.7179})
    lon: float = Field(..., json_schema_extra={"example": 77.0638})
    speed_kmh: float = Field(..., json_schema_extra={"example": 14.5})
    timestamp: int = Field(..., json_schema_extra={"example": 1730000000})

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Redirects root directly to the unified Problem Statement 2 visualizer."""
    return RedirectResponse(url="/ps2/")

@app.get("/api/v1/health")
def health_check():
    """Returns system status, loaded datasets, and resource metrics."""
    return {
        "status": "healthy",
        "service": "Transport Stack Hackathon 2026 Engine",
        "loaded_resources": {
            "bus_and_metro_stops": len(network.stops),
            "transit_routes": len(network.routes),
            "scheduled_trips": len(network.trips),
            "stop_times_indexed": network.stop_times_count or len(network.stop_times),
            "od_matrix_origin_stations": len(network.od_matrix),
            "live_vehicles_tracked": len(traffic_model.live_vehicle_updates)
        },
        "phase_1_problems_supported": [
            "Problem 1: Real-time bus traffic model and journey planner",
            "Problem 2: Crowdedness-aware journey planner"
        ],
        "datasets_available": [
            "DLM1: Delhi Buses GTFS Static",
            "DLM2: Delhi Metro GTFS Static",
            "DLM3: Delhi Metro Gate Locations",
            "DLM4: Delhi Metro Hourly Footfall",
            "DLM5: Rapid Rail NCRTC Static",
            "DLM6: Delhi Metro Parking Locations",
            "DLM7: Delhi Buses GTFS-RT Live Feed",
            "DLM8: Delhi Metro Monthly OD Matrix",
            "DLM9: Delhi Metro Yearly OD Matrix"
        ]
    }

@app.get("/api/v1/stops")
def search_stops(
    q: Optional[str] = Query(None, description="Search stop by name or ID"),
    mode: Optional[str] = Query(None, description="Filter by mode: 'bus' or 'metro'"),
    lat: Optional[float] = Query(None, description="Latitude for spatial proximity"),
    lon: Optional[float] = Query(None, description="Longitude for spatial proximity"),
    limit: int = Query(20, le=100)
):
    """Searches transit stops by name or finds closest stops to coordinates."""
    if lat is not None and lon is not None:
        nearby = network.find_nearest_stops(lat, lon, mode=mode, limit=limit)
        return [
            {
                "stop_id": s.stop_id,
                "stop_name": s.stop_name,
                "lat": s.lat,
                "lon": s.lon,
                "mode": s.mode,
                "distance_km": round(dist, 2)
            }
            for s, dist in nearby
        ]
    
    if q:
        found = network.search_stops_by_name(q, limit=limit)
        return [
            {
                "stop_id": s.stop_id,
                "stop_name": s.stop_name,
                "lat": s.lat,
                "lon": s.lon,
                "mode": s.mode
            }
            for s in found
        ]

    # Return sample of stops
    sample_stops = list(network.stops.values())[:limit]
    return [
        {
            "stop_id": s.stop_id,
            "stop_name": s.stop_name,
            "lat": s.lat,
            "lon": s.lon,
            "mode": s.mode
        }
        for s in sample_stops
    ]

@app.get("/api/v1/routes")
def list_routes(mode: Optional[str] = None, limit: int = 50):
    """Lists available bus and metro routes in the network."""
    routes = list(network.routes.values())
    if mode:
        routes = [r for r in routes if r.mode == mode]
    return [
        {
            "route_id": r.route_id,
            "short_name": r.short_name,
            "long_name": r.long_name,
            "mode": r.mode,
            "description": r.description
        }
        for r in routes[:limit]
    ]

@app.get("/api/v1/journey")
def plan_journey(
    origin: str = Query(..., alias="from", description="Origin coordinates 'lat,lon' or stop name (e.g. 'Kashmere Gate' or '28.6675,77.2285')"),
    destination: str = Query(..., alias="to", description="Destination coordinates 'lat,lon' or stop name (e.g. 'Nehru Place' or '28.5494,77.2528')"),
    depart: str = Query("08:30:00", description="Departure time in HH:MM or HH:MM:SS format"),
    mode: Optional[str] = Query(None, description="Preferred transit mode ('bus', 'metro', or None for all)")
):
    """
    Primary Phase 1 Journey Planner API Endpoint.
    Returns journey options with:
    - Step-by-step legs (walking, boarding stop, transit route, transfers, alighting stop)
    - Traffic-modeled travel time vs off-peak freeflow baseline
    - Crowdedness estimates (Seats Available, Standing, Crowded) and comfort scores
    """
    options = planner.plan_journey(
        from_input=origin,
        to_input=destination,
        departure_time_str=depart,
        pref_mode=mode
    )
    if not options:
        raise HTTPException(
            status_code=404,
            detail=f"No transit route found between '{origin}' and '{destination}' for departure at {depart}."
        )

    return {
        "query": {
            "origin": origin,
            "destination": destination,
            "departure_time": depart,
            "mode_filter": mode or "all"
        },
        "options_count": len(options),
        "options": [
            {
                "option_id": opt.option_id,
                "title": opt.title,
                "departure_time": opt.departure_time,
                "arrival_time": opt.arrival_time,
                "total_duration_minutes": opt.total_duration_minutes,
                "freeflow_offpeak_minutes": opt.freeflow_duration_minutes,
                "traffic_delay_minutes": opt.traffic_delay_minutes,
                "total_walk_minutes": opt.total_walk_minutes,
                "total_transit_minutes": opt.total_transit_minutes,
                "transfers_count": opt.transfers_count,
                "crowdedness": {
                    "level": opt.primary_crowdedness,
                    "color": opt.primary_color,
                    "comfort_score": opt.comfort_score
                },
                "summary_advice": opt.summary_advice,
                "legs": [
                    {
                        "type": leg.leg_type,
                        "from": leg.from_name,
                        "from_coords": leg.from_coords,
                        "to": leg.to_name,
                        "to_coords": leg.to_coords,
                        "distance_km": leg.distance_km,
                        "duration_minutes": leg.duration_minutes,
                        "route_name": leg.route_name,
                        "traffic_note": leg.traffic_delay_note,
                        "crowdedness": leg.crowdedness.__dict__ if leg.crowdedness else None
                    }
                    for leg in opt.legs
                ]
            }
            for opt in options
        ]
    }

@app.get("/api/v1/traffic/speed-profile")
def get_traffic_speed_profile():
    """Returns the Delhi city-wide 24-hour bus speed curve (km/h) and corridor congestion factors."""
    return {
        "city": "Delhi NCR",
        "hourly_speed_kmh": DEFAULT_HOURLY_SPEED_KMH,
        "peak_windows": {
            "morning_peak": "08:30 - 11:00 (11.5 - 14.5 km/h)",
            "evening_peak": "17:30 - 20:30 (11.5 - 15.0 km/h)",
            "offpeak_night": "22:00 - 06:00 (26.0 - 35.0 km/h)"
        }
    }

@app.get("/api/v1/crowdedness")
def get_crowdedness(
    route_id: str = Query("BUS_102ADOWN", description="Route ID to analyze"),
    hour: int = Query(9, ge=0, le=23, description="Hour of the day (0-23)"),
    progress: float = Query(0.5, ge=0.0, le=1.0, description="Route segment progress (0.0 to 1.0)")
):
    """Returns passenger occupancy estimate, comfort score, and recommendation for a route and hour."""
    est = crowdedness_model.estimate_load(route_id=route_id, hour=hour, stop_sequence_progress=progress)
    return {
        "route_id": route_id,
        "hour": hour,
        "segment_progress": progress,
        "estimate": est.__dict__
    }

@app.get("/api/v1/od-matrix")
def get_od_flows(origin: Optional[str] = Query(None, description="Origin station code (e.g. 'NBAA', 'MNGM', 'JLML')")):
    """Returns Origin-Destination passenger flows from the DMRC AFC dataset."""
    if origin:
        flows = network.od_matrix.get(origin)
        if not flows:
            raise HTTPException(status_code=404, detail=f"Origin station code '{origin}' not found.")
        # Sort top destinations
        sorted_flows = sorted(flows.items(), key=lambda x: x[1], reverse=True)[:25]
        return {
            "origin_station_code": origin,
            "top_destinations": [{"destination_code": k, "monthly_passengers": v} for k, v in sorted_flows]
        }
    
    return {
        "total_origins_indexed": len(network.od_matrix),
        "sample_origins": list(network.od_matrix.keys())[:20]
    }

@app.post("/api/v1/gps-telemetry")
def ingest_gps(telemetry: GPSUpdatePayload):
    """Ingests a real-time GTFS-RT vehicle position update into the traffic model."""
    pos = LiveVehiclePosition(
        vehicle_id=telemetry.vehicle_id,
        route_id=telemetry.route_id,
        lat=telemetry.lat,
        lon=telemetry.lon,
        speed_kmh=telemetry.speed_kmh,
        timestamp=telemetry.timestamp
    )
    traffic_model.record_live_gps(pos)
    return {
        "status": "success",
        "message": f"Updated live speed for route {telemetry.route_id}: {telemetry.speed_kmh} km/h",
        "active_vehicles": len(traffic_model.live_vehicle_updates)
    }

@app.get("/api/v1/feeder-routes")
def get_feeder_routes(total_fleet: int = Query(500, description="Total electric buses available in fleet")):
    """
    Problem 4 API Endpoint: Metro Feeder Route & Electric Bus Fleet Plan.
    Returns feeder routes respecting constraints (length <= 7km, roads > 6m width, EV charging duty cycle).
    """
    routes = feeder_optimizer.design_feeder_network(total_ev_fleet=total_fleet)
    return {
        "target_metro_stations_count": len(feeder_optimizer.target_stations),
        "total_electric_buses_allocated": total_fleet,
        "feeder_routes_count": len(routes),
        "routes": [r.__dict__ for r in routes]
    }

@app.get("/api/v1/od-extrapolation")
def get_od_extrapolation(limit: int = Query(25, le=100)):
    """
    Problem 3 API Endpoint: City-Wide Public Transit OD Extrapolation.
    Scales 3.5% bus e-ticketing sample to total daily ridership (~4.2M), anchored by Metro AFC gates.
    """
    flows = od_extrapolator.extrapolate_zone_matrix()
    return {
        "total_travel_analysis_zones": len(od_extrapolator.taz_zones),
        "total_flows_computed": len(flows),
        "scaling_method": "Gravity Model + Furness Bi-proportional Balancing (Anchored on DMRC AFC Gates)",
        "sample_expansion_multiplier": 28.57,
        "top_interzone_flows": [f.__dict__ for f in flows[:limit]]
    }

@app.get("/api/v1/road-compliance")
def get_road_compliance():
    """
    Problem 4 Data Endpoint: Summarizes Delhi road width compliance for EV feeder buses from Data_Layer_04_Road.xlsb.
    """
    summary_file = Path(__file__).resolve().parent.parent / "data" / "metro_feeder_ev_data" / "road_width_compliance_summary.json"
    if summary_file.exists():
        with open(summary_file) as f:
            return json.load(f)
    return {"message": "Road compliance summary not found"}

@app.get("/api/v1/live/fleet-stats")
def get_live_fleet_stats():
    """
    Returns real-time fleet telemetry metrics (active buses, active routes, fleet velocity)
    parsed directly from the Delhi Buses GTFS-RT feed (VehiclePositions.pb).
    """
    return gtfs_rt_client.get_fleet_live_stats()

@app.get("/api/v1/live/vehicles")
def get_live_vehicles(
    route_id: Optional[str] = Query(None, description="Optional route filter e.g. '502UP' or '1346'"),
    limit: int = Query(50, ge=1, le=500, description="Max vehicles to return")
):
    """
    Returns live vehicle positions from the Delhi Buses GTFS-RT feed.
    """
    if route_id:
        vehicles = gtfs_rt_client.get_vehicles_by_route(route_id)
    else:
        vehicles = gtfs_rt_client.fetch_vehicle_positions()
    return {
        "total_matching": len(vehicles),
        "limit": limit,
        "vehicles": vehicles[:limit]
    }


