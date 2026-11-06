"""
Problem 2: Crowdedness-aware Estimator & Occupancy Model
Models onboard bus passenger loads from ticket transactions (ETM & e-ticketing),
incorporating pass-holder expansions and fleet capacity tiers.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

@dataclass
class BusCapacityConfig:
    bus_type: str = "standard_12m"  # "standard_12m" (DTC AC/Non-AC) or "midi_9m" (Feeder)
    seating_capacity: int = 35
    crush_standing_capacity: int = 35  # Total max capacity = 70
    free_pass_multiplier: float = 1.35  # Accounting for non-ticketed pass holders (Delhi pink passes ~30-35%)

# Historical Hourly Crowding Probability Profile in Delhi Public Transit
# Peak hours (08:30-11:00 and 17:30-20:30) have highest load factor
HOURLY_LOAD_FACTOR = {
    0: 0.10, 1: 0.05, 2: 0.05, 3: 0.05, 4: 0.10, 5: 0.20,
    6: 0.35, 7: 0.60, 8: 0.95, 9: 1.15, 10: 1.05, 11: 0.80,
    12: 0.65, 13: 0.60, 14: 0.65, 15: 0.70, 16: 0.85, 17: 1.10,
    18: 1.25, 19: 1.20, 20: 0.90, 21: 0.60, 22: 0.40, 23: 0.20
}

@dataclass
class CrowdednessEstimate:
    occupancy_count: int
    load_factor: float
    status_label: str  # "Seats Available", "Standing Room", "Heavily Crowded"
    color_code: str    # "green", "amber", "red"
    comfort_score: int # 100 (empty) to 0 (packed)
    recommendation: str

class CrowdednessModel:
    """
    Estimates passenger load on transit vehicles across route segments and times of day.
    """

    def __init__(self, default_config: Optional[BusCapacityConfig] = None):
        self.config = default_config or BusCapacityConfig()
        # Route-specific baseline load overrides (e.g. Ring Road high density vs feeder)
        self.route_density_weights: Dict[str, float] = {
            "BUS_102ADOWN": 1.10,
            "BUS_102DOWN": 1.15,
            "METRO_RED": 1.20,
            "METRO_YELLOW": 1.35,
            "METRO_BLUE": 1.30,
        }

    def estimate_load(
        self,
        route_id: str,
        hour: int,
        stop_sequence_progress: float = 0.5,
        bus_config: Optional[BusCapacityConfig] = None
    ) -> CrowdednessEstimate:
        """
        Estimates the passenger occupancy and comfort level for a bus trip.
        
        Args:
            route_id: Transit route identifier
            hour: Departure hour (0-23)
            stop_sequence_progress: Fraction of route completed (0.0 = start, 0.5 = mid-route peak, 1.0 = terminal)
            bus_config: Optional vehicle capacity specifications
        """
        cfg = bus_config or self.config
        hour = max(0, min(23, hour))

        # Baseline time-of-day factor
        base_factor = HOURLY_LOAD_FACTOR.get(hour, 0.50)
        route_multiplier = self.route_density_weights.get(route_id, 1.0)

        # Mid-route bell curve: passenger load typically peaks in middle segments of trunk routes
        # bell curve factor between 0.7 (at terminals) and 1.2 (at central interchanges)
        route_position_factor = 0.70 + 0.50 * math.sin(math.pi * max(0.0, min(1.0, stop_sequence_progress)))

        combined_factor = base_factor * route_multiplier * route_position_factor

        # Estimated ticketed passengers
        nominal_seats = cfg.seating_capacity
        estimated_ticketed = int(nominal_seats * combined_factor)

        # Expand for Delhi pass holders (women free travel pink passes & passes)
        total_estimated = int(estimated_ticketed * cfg.free_pass_multiplier)
        total_capacity = cfg.seating_capacity + cfg.crush_standing_capacity

        ratio = total_estimated / cfg.seating_capacity

        if ratio <= 0.75:
            status = "Seats Available"
            color = "green"
            comfort = max(70, int(100 - (ratio * 40)))
            rec = "Good time to travel. Plenty of seating expected."
        elif ratio <= 1.25:
            status = "Standing Room Only"
            color = "amber"
            comfort = max(35, int(70 - ((ratio - 0.75) * 60)))
            rec = "Moderate crowd. You will likely have to stand for part of the trip."
        else:
            status = "Heavily Crowded / Packed"
            color = "red"
            comfort = max(10, int(35 - ((ratio - 1.25) * 40)))
            rec = "High crowding. Consider taking a route 15-20 min later or an alternate service."

        return CrowdednessEstimate(
            occupancy_count=total_estimated,
            load_factor=round(ratio, 2),
            status_label=status,
            color_code=color,
            comfort_score=comfort,
            recommendation=rec
        )
