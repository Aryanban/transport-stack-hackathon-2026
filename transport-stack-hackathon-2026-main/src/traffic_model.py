"""
Problem 1: Real-time Bus Traffic Model & Speed Estimator
Models historical and real-time Delhi traffic speeds across time-of-day,
corridors, and bus routes.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# Delhi Average Traffic Speed Profiles (km/h) by hour of day (0-23)
# Based on Delhi Master Plan & CSM IIIT-D urban transit studies:
# - Morning peak (08:00 - 11:00): 11 - 14 km/h
# - Mid-day (12:00 - 16:00): 18 - 21 km/h
# - Evening peak (17:30 - 20:30): 12 - 15 km/h
# - Late night / Early morning (22:00 - 06:00): 28 - 35 km/h
DEFAULT_HOURLY_SPEED_KMH = {
    0: 32.0, 1: 34.0, 2: 35.0, 3: 35.0, 4: 33.0, 5: 30.0,
    6: 25.0, 7: 20.0, 8: 14.5, 9: 12.0, 10: 13.5, 11: 16.0,
    12: 18.5, 13: 19.0, 14: 18.0, 15: 17.5, 16: 16.0, 17: 13.0,
    18: 11.5, 19: 12.5, 20: 15.0, 21: 20.0, 22: 26.0, 23: 29.0
}

# Key Delhi corridor congestion multipliers (>1.0 = slower / more congested)
CORRIDOR_CONGESTION_MULTIPLIERS = {
    "ring_road": 1.25,
    "outer_ring_road": 1.15,
    "ito_vikas_marg": 1.40,
    "kashmere_gate_isbt": 1.35,
    "nehru_place_outer_ring": 1.30,
    "connaught_place_inner": 1.20,
    "default": 1.00
}

@dataclass
class LiveVehiclePosition:
    vehicle_id: str
    route_id: str
    lat: float
    lon: float
    speed_kmh: float
    timestamp: int

class BusTrafficModel:
    """
    Traffic model that computes dynamic bus travel times across Delhi's road network
    by fusing historical time-of-day speed curves with live GPS observations.
    """

    def __init__(self):
        self.live_vehicle_updates: Dict[str, LiveVehiclePosition] = {}
        self.route_live_speeds: Dict[str, float] = {}

    def record_live_gps(self, vehicle: LiveVehiclePosition):
        """Records a live GTFS-RT bus position update."""
        self.live_vehicle_updates[vehicle.vehicle_id] = vehicle
        self.route_live_speeds[vehicle.route_id] = vehicle.speed_kmh

    def get_expected_speed(self, hour: int, route_id: Optional[str] = None, corridor: str = "default") -> float:
        """
        Returns estimated bus speed in km/h at a given hour.
        Fuses historical baseline with live GTFS-RT speed if available.
        """
        hour = max(0, min(23, hour))
        base_speed = DEFAULT_HOURLY_SPEED_KMH.get(hour, 18.0)
        
        # Apply corridor modifier
        corridor_factor = CORRIDOR_CONGESTION_MULTIPLIERS.get(corridor.lower(), 1.0)
        historical_speed = base_speed / corridor_factor

        # If live telemetry is available for this route, blend it (70% live, 30% historical)
        if route_id and route_id in self.route_live_speeds:
            live_spd = self.route_live_speeds[route_id]
            if live_spd > 2.0:  # Valid non-zero moving speed
                return 0.70 * live_spd + 0.30 * historical_speed

        return historical_speed

    def estimate_segment_travel_time(
        self,
        distance_km: float,
        hour: int,
        route_id: Optional[str] = None,
        dwell_stops_count: int = 1,
        traffic_signals_count: int = 1
    ) -> Tuple[float, float, str]:
        """
        Calculates estimated travel time for a route segment in minutes.
        
        Returns:
            (predicted_minutes, freeflow_offpeak_minutes, traffic_severity_label)
        """
        # Speed in km/h
        curr_speed = self.get_expected_speed(hour, route_id=route_id)
        freeflow_speed = DEFAULT_HOURLY_SPEED_KMH[2]  # ~35 km/h at 2 AM

        # Pure driving time (hours -> minutes)
        driving_min = (distance_km / max(curr_speed, 5.0)) * 60.0
        freeflow_min = (distance_km / freeflow_speed) * 60.0

        # Delhi bus dwell time model: ~30-45 sec per intermediate bus stop boarding
        dwell_min = (dwell_stops_count * 35.0) / 60.0
        
        # Traffic signal wait time model: ~45 sec per major signal during daytime
        signal_min = (traffic_signals_count * (45.0 if 8 <= hour <= 21 else 15.0)) / 60.0

        total_predicted = driving_min + dwell_min + signal_min
        total_freeflow = freeflow_min + (dwell_stops_count * 20.0 / 60.0)

        # Traffic delay indicator
        delay_ratio = total_predicted / max(total_freeflow, 1.0)
        if delay_ratio > 1.8:
            severity = "Heavy Congestion (+80% delay)"
        elif delay_ratio > 1.3:
            severity = "Moderate Traffic (+30-80% delay)"
        else:
            severity = "Smooth / Light Traffic"

        return round(total_predicted, 1), round(total_freeflow, 1), severity
