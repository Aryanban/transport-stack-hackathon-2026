"""
Test Suite for Delhi Transport Stack Hackathon 2026 Engine
"""

import pytest
from fastapi.testclient import TestClient

from src.data_loader import get_loaded_network, haversine_distance_km, time_to_seconds, seconds_to_time
from src.traffic_model import BusTrafficModel, LiveVehiclePosition
from src.crowdedness_model import CrowdednessModel, BusCapacityConfig
from src.gtfs_router import JourneyPlanner
from src.api import app

@pytest.fixture(scope="module")
def network():
    return get_loaded_network()

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

def test_network_loading(network):
    """Verifies that Bus and Metro GTFS data and OD matrices load properly."""
    assert len(network.stops) > 0, "Stops should be loaded"
    assert len(network.routes) > 0, "Routes should be loaded"
    assert len(network.od_matrix) > 0, "DMRC OD matrix should be loaded"

def test_haversine_distance():
    """Verifies GPS distance calculations between Connaught Place and India Gate (~2.3 km)."""
    cp_lat, cp_lon = 28.6315, 77.2167
    ig_lat, ig_lon = 28.6129, 77.2295
    dist = haversine_distance_km(cp_lat, cp_lon, ig_lat, ig_lon)
    assert 2.0 <= dist <= 2.8

def test_time_conversions():
    """Verifies HH:MM:SS to seconds and back."""
    sec = time_to_seconds("08:30:00")
    assert sec == 8 * 3600 + 30 * 60
    assert seconds_to_time(sec) == "08:30:00"

def test_traffic_model_speeds():
    """Verifies peak vs off-peak speeds in Delhi traffic model."""
    model = BusTrafficModel()
    morning_rush_speed = model.get_expected_speed(hour=9)
    night_speed = model.get_expected_speed(hour=2)
    assert morning_rush_speed < night_speed, "Morning rush hour must be significantly slower than night"
    assert 10.0 <= morning_rush_speed <= 16.0
    assert 28.0 <= night_speed <= 36.0

def test_traffic_segment_estimate():
    """Verifies travel time and delay calculation."""
    model = BusTrafficModel()
    pred, freeflow, severity = model.estimate_segment_travel_time(
        distance_km=10.0,
        hour=9,
        dwell_stops_count=8
    )
    assert pred > freeflow, "Predicted peak travel time must be greater than freeflow"
    assert pred > 30.0

def test_crowdedness_model():
    """Verifies passenger load and comfort tier categorization."""
    model = CrowdednessModel()
    # Off-peak 3 AM
    night_est = model.estimate_load(route_id="BUS_102ADOWN", hour=3)
    assert night_est.status_label == "Seats Available"
    assert night_est.color_code == "green"
    assert night_est.comfort_score >= 70

    # Peak 6 PM
    peak_est = model.estimate_load(route_id="BUS_102ADOWN", hour=18)
    assert peak_est.occupancy_count > night_est.occupancy_count
    assert peak_est.color_code in ["amber", "red"]

def test_journey_planner(network):
    """Verifies full end-to-end journey planning."""
    planner = JourneyPlanner(network)
    options = planner.plan_journey(
        from_input="Rohini Sec 22 Terminal",
        to_input="Azadpur Terminal",
        departure_time_str="08:30:00"
    )
    assert len(options) > 0, "Journey planner should return candidate options"
    first = options[0]
    assert first.total_duration_minutes > 0
    assert len(first.legs) >= 2
    assert first.primary_crowdedness in ["Seats Available", "Standing Room Only", "Heavily Crowded / Packed"]

def test_api_health(client):
    """Verifies API health endpoint."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["loaded_resources"]["bus_and_metro_stops"] > 0

def test_api_journey(client):
    """Verifies API journey query endpoint."""
    res = client.get("/api/v1/journey?from=Rohini%20Sec%2022%20Terminal&to=Azadpur%20Terminal&depart=09:00:00")
    assert res.status_code == 200
    data = res.json()
    assert "options" in data
    assert len(data["options"]) > 0

def test_feeder_optimizer():
    """Verifies Problem 4 Feeder Optimizer constraints (<= 7 km, electric bus allocations)."""
    from src.feeder_optimizer import FeederOptimizer
    optimizer = FeederOptimizer()
    routes = optimizer.design_feeder_network(total_ev_fleet=500)
    assert len(routes) > 0
    for r in routes:
        assert r.route_length_km <= 7.0, f"Route {r.route_id} exceeds 7km constraint"
        assert r.road_width_compliant is True
        assert r.daily_energy_kwh_per_bus > 0
        assert r.is_valid_route is True

def test_od_extrapolator():
    """Verifies Problem 3 OD matrix extrapolation and scaling logic."""
    from src.od_extrapolator import ODExtrapolator
    extrapolator = ODExtrapolator()
    flows = extrapolator.extrapolate_zone_matrix()
    assert len(flows) > 0
    top = flows[0]
    assert top.scaled_bus_trips > top.sample_bus_trips
    assert top.total_multimodal_trips >= top.scaled_bus_trips
    assert "Confidence" in top.confidence_interval

def test_api_new_endpoints(client):
    """Verifies Problem 3 and Problem 4 REST endpoints."""
    res_feeder = client.get("/api/v1/feeder-routes?total_fleet=500")
    assert res_feeder.status_code == 200
    data_f = res_feeder.json()
    assert data_f["total_electric_buses_allocated"] == 500
    assert len(data_f["routes"]) > 0

    res_od = client.get("/api/v1/od-extrapolation?limit=10")
    assert res_od.status_code == 200
    data_od = res_od.json()
    assert len(data_od["top_interzone_flows"]) == 10

