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
    perceived_time_multiplier: float = 1.0  # Hensher-Wardman VOT multiplier (1.0x seated, 1.45x standing, 2.25x crush)

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

        # Hensher-Wardman Value of Time (VOT) Crowding Multiplier
        if ratio <= 1.0:
            perceived_mult = 1.0
        elif ratio <= 1.5:
            # Standee penalty: standing feels 1.35x - 1.65x longer
            standing_share = (total_estimated - cfg.seating_capacity) / max(1, total_capacity - cfg.seating_capacity)
            perceived_mult = round(1.0 + 0.50 * standing_share, 2)
        else:
            # Crush penalty: physical crush feels up to 2.25x longer
            crush_share = (total_estimated - cfg.seating_capacity) / max(1, total_capacity - cfg.seating_capacity)
            perceived_mult = round(1.0 + 0.60 * crush_share + 0.65 * (crush_share ** 2), 2)

        return CrowdednessEstimate(
            occupancy_count=total_estimated,
            load_factor=round(ratio, 2),
            status_label=status,
            color_code=color,
            comfort_score=comfort,
            recommendation=rec,
            perceived_time_multiplier=perceived_mult
        )

    def calculate_perceived_travel_time(
        self,
        actual_travel_minutes: float,
        route_id: str,
        hour: int,
        stop_sequence_progress: float = 0.5
    ) -> float:
        """
        Applies Hensher-Wardman transit economics crowding multipliers to return
        perceived travel time in minutes.
        """
        crowd_est = self.estimate_load(route_id, hour, stop_sequence_progress)
        return round(actual_travel_minutes * crowd_est.perceived_time_multiplier, 1)

    def evaluate_pareto_journey_options(self, journeys: list) -> list:
        """
        McRAPTOR-inspired multi-criteria Pareto sorter.
        Categorizes candidate journey options into three distinct commuter choices:
        1. Fastest Option (minimal physical travel time)
        2. Balanced Option (compromise on duration and comfort)
        3. Comfort First Option (minimal perceived fatigue / seated guarantee)
        """
        if not journeys:
            return []

        # Annotate perceived times
        for j in journeys:
            dur = j.get("duration_minutes", j.get("travel_time_min", 30.0))
            load = j.get("occupancy_count", 30)
            seat_cap = j.get("seating_capacity", 35)
            crush_cap = j.get("crush_capacity", 70)
            
            if load <= seat_cap:
                mult = 1.0
            else:
                s_ratio = (load - seat_cap) / max(1, crush_cap - seat_cap)
                mult = 1.0 + 0.50 * s_ratio + 0.75 * (s_ratio ** 2)
            
            j["perceived_duration_minutes"] = round(dur * mult, 1)

        # Sort along two frontiers
        by_speed = sorted(journeys, key=lambda x: x.get("duration_minutes", 0))
        by_comfort = sorted(journeys, key=lambda x: x.get("perceived_duration_minutes", 0))

        fastest = by_speed[0]
        comfort = by_comfort[0]

        # Find balanced middle ground
        balanced = None
        for j in by_speed:
            if j != fastest and j != comfort:
                balanced = j
                break
        if not balanced:
            balanced = by_comfort[-1] if len(by_comfort) > 1 else fastest

        fastest["pareto_tier"] = "Fastest Route"
        fastest["pareto_description"] = "Minimizes physical travel time on road."

        comfort["pareto_tier"] = "Comfort First (Seated)"
        comfort["pareto_description"] = "Maximizes seating availability, minimizing commuter fatigue."

        balanced["pareto_tier"] = "Balanced Compromise"
        balanced["pareto_description"] = "Optimal balance of journey duration and acceptable crowding."

        return [fastest, balanced, comfort]
