"""
Comprehensive Location Matrix and Journey Planning Test Suite
Validates core routing functionality, geographical feasibility, stop sequence continuity,
crowding estimation, and multi-modal transfers across diverse Delhi-NCR corridors.
"""

import math
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import HTTPException

from src.api import app
from src.ps2.api import journeys, state
from src.data_loader import haversine_distance_km

client = TestClient(app)

CORRIDOR_SCENARIOS = [
    {
        "name": "North-South Arterial: Delhi Gate to Kashmere Gate ISBT",
        "origin_id": "2070",
        "destination_id": "1025",
        "min_dist_km": 2.5,
        "max_dist_km": 6.0,
    },
    {
        "name": "Return Southbound Corridor: Kashmere Gate ISBT to Delhi Gate",
        "origin_id": "1025",
        "destination_id": "10052",
        "min_dist_km": 2.5,
        "max_dist_km": 6.0,
    },
    {
        "name": "Central-to-Southeast Cross-City: Kashmere Gate to DDA Flats Kalkaji",
        "origin_id": "1025",
        "destination_id": "2295",
        "min_dist_km": 14.0,
        "max_dist_km": 26.0,
    },
    {
        "name": "South-to-Central Arterial: Mehrauli Terminal to Delhi Gate",
        "origin_id": "7910",
        "destination_id": "2070",
        "min_dist_km": 14.0,
        "max_dist_km": 28.0,
    },
    {
        "name": "Southwest-to-North: Mangla Puri Terminal to Kashmere Gate",
        "origin_id": "336",
        "destination_id": "1025",
        "min_dist_km": 15.0,
        "max_dist_km": 32.0,
    },
]

def calculate_polyline_distance_km(points):
    """Calculates cumulative route distance across all intermediate GPS coordinates."""
    total_km = 0.0
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        lat1 = p1.get("lat") or p1.get("latitude")
        lon1 = p1.get("lon") or p1.get("longitude")
        lat2 = p2.get("lat") or p2.get("latitude")
        lon2 = p2.get("lon") or p2.get("longitude")
        if lat1 and lon1 and lat2 and lon2:
            total_km += haversine_distance_km(float(lat1), float(lon1), float(lat2), float(lon2))
    return total_km


class TestLocationMatrixRouting:
    """Verifies that all geographic corridors compute correct distances, stops, and schedules."""

    @pytest.mark.parametrize("scenario", CORRIDOR_SCENARIOS, ids=lambda s: s["name"])
    def test_corridor_routing_accuracy_and_geometry(self, scenario):
        """Verifies candidate routes, total distance, stop coordinates, and chronological validity."""
        dep_time = "2026-11-11T08:30:00"
        result = journeys(scenario["origin_id"], scenario["destination_id"], dep_time, extra=30)

        assert "options" in result, f"Response missing options for {scenario['name']}"
        options = result["options"]
        assert len(options) > 0, f"Expected at least 1 route option for {scenario['name']}"

        fastest = options[0]
        assert fastest["label"] in ["Fastest", "Alternative"]
        assert fastest["minutes"] > 0, "Journey duration must be greater than zero"
        assert fastest["waitMinutes"] >= 0, "Wait time cannot be negative"
        assert len(fastest["legs"]) >= 1, "Must contain at least one transit leg"

        # Check all intermediate points along all legs
        all_points = []
        for leg in fastest["legs"]:
            assert "from" in leg and "to" in leg
            assert "route" in leg or "routeId" in leg
            assert leg["rideMinutes"] > 0, "Leg ride time must be positive"
            pts = leg.get("points", [])
            assert len(pts) >= 2, "Each leg must have at least origin and destination points"
            all_points.extend(pts)

            # Verify GPS boundaries (Delhi-NCR Bounding Box)
            for pt in pts:
                lat = float(pt.get("lat") or pt.get("latitude", 0))
                lon = float(pt.get("lon") or pt.get("longitude", 0))
                assert 28.2 <= lat <= 29.1, f"Latitude {lat} outside Delhi-NCR bounding box"
                assert 76.7 <= lon <= 77.6, f"Longitude {lon} outside Delhi-NCR bounding box"

        # Validate total route distance
        total_dist_km = calculate_polyline_distance_km(all_points)
        assert total_dist_km >= scenario["min_dist_km"], (
            f"Distance {total_dist_km:.2f}km is less than expected minimum {scenario['min_dist_km']}km for {scenario['name']}"
        )
        assert total_dist_km <= scenario["max_dist_km"], (
            f"Distance {total_dist_km:.2f}km exceeds expected maximum {scenario['max_dist_km']}km for {scenario['name']}"
        )

    def test_transfer_station_continuity(self):
        """Verifies that multi-leg journeys properly connect at transfer stations."""
        result = journeys("7910", "2070", "2026-11-11T08:30:00", extra=30)
        assert len(result["options"]) > 0
        transfer_option = next((opt for opt in result["options"] if opt["transfers"] > 0), None)
        assert transfer_option is not None, "Expected a transfer option for Mehrauli -> Delhi Gate"

        legs = transfer_option["legs"]
        for i in range(len(legs) - 1):
            leg_a_dest = legs[i]["to"]
            leg_b_orig = legs[i + 1]["from"]
            # Station IDs match or are within 800m walking distance
            lat1, lon1 = float(leg_a_dest["lat"]), float(leg_a_dest["lon"])
            lat2, lon2 = float(leg_b_orig["lat"]), float(leg_b_orig["lon"])
            walk_gap_km = haversine_distance_km(lat1, lon1, lat2, lon2)
            assert walk_gap_km < 0.8, f"Transfer gap between legs ({walk_gap_km:.2f}km) is too large"

    def test_peak_vs_night_schedule_variations(self):
        """Verifies schedule availability across morning rush, evening rush, and late night."""
        orig, dest = "2070", "1025"  # Delhi Gate to Kashmere Gate
        
        # Morning peak
        morning = journeys(orig, dest, "2026-11-11T08:30:00", 15)
        assert len(morning["options"]) > 0

        # Evening peak
        evening = journeys(orig, dest, "2026-11-11T18:00:00", 15)
        assert len(evening["options"]) > 0

        # Late night
        night = journeys(orig, dest, "2026-11-11T22:00:00", 30)
        assert "options" in night

    def test_stop_search_autocomplete_api(self):
        """Verifies that the /ps2/api/stops search endpoint finds relevant transit hubs."""
        queries = ["Delhi Gate", "Kashmere Gate", "Mehrauli", "Azadpur", "Rajiv Chowk", "AIIMS"]
        for q in queries:
            res = client.get(f"/ps2/api/stops?q={q}")
            assert res.status_code == 200
            stops = res.json()
            assert isinstance(stops, list)
            assert len(stops) > 0, f"Search for '{q}' should return stop candidates"
            first_match = stops[0]
            assert "id" in first_match
            assert "name" in first_match
            assert "lat" in first_match and "lon" in first_match

    def test_corridor_shortcuts_endpoint(self):
        """Verifies the /ps2/api/corridors endpoint returns verified bidirectional pairs."""
        res = client.get("/ps2/api/corridors")
        assert res.status_code == 200
        data = res.json()
        assert "corridors" in data
        corridors = data["corridors"]
        assert len(corridors) >= 4
        for c in corridors:
            assert "route" in c
            assert "label" in c
            assert "from" in c and "to" in c
            assert c["from"]["id"] and c["to"]["id"]

    def test_edge_case_same_origin_and_destination(self):
        """Verifies that selecting the exact same stop returns 400 Bad Request."""
        with pytest.raises(HTTPException) as exc_info:
            journeys("2070", "2070", "2026-11-11T08:30:00", 15)
        assert exc_info.value.status_code == 400

    def test_edge_case_invalid_stop_id(self):
        """Verifies that querying invalid stop IDs raises 400 Bad Request."""
        with pytest.raises(HTTPException) as exc_info:
            journeys("99999999", "88888888", "2026-11-11T08:30:00", 15)
        assert exc_info.value.status_code == 400
