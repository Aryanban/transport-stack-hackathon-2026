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
