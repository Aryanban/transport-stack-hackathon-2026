#!/usr/bin/env python3
"""
Route Benchmark & Validation Script
Tests sample Delhi origin-destination pairs across Peak and Off-Peak hours.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import get_loaded_network
from src.gtfs_router import JourneyPlanner

BENCHMARK_PAIRS = [
    ("Rohini Sec 22 Terminal", "Azadpur Terminal"),
    ("Kashmere Gate", "Nehru Place"),
    ("Dilshad Garden", "Mansrover park"),
    ("28.6675,77.2285", "28.5494,77.2528") # Kashmere Gate coords to Nehru Place coords
]

HOURS_TO_TEST = [
    ("08:30:00", "Morning Rush (08:30 AM)"),
    ("14:00:00", "Mid-day Normal (02:00 PM)"),
    ("23:00:00", "Late Night Off-Peak (11:00 PM)")
]

def run_benchmarks():
    print("=" * 75)
    print("DELHI TRANSIT STACK — ROUTE & CROWDEDNESS BENCHMARK SUITE")
    print("=" * 75)

    net = get_loaded_network()
    planner = JourneyPlanner(net)

    for orig, dest in BENCHMARK_PAIRS:
        print(f"\n📍 TRIP: {orig} ➔ {dest}")
        print("-" * 75)
        for dep_time, label in HOURS_TO_TEST:
            options = planner.plan_journey(orig, dest, departure_time_str=dep_time)
            if options:
                best = options[0]
                print(f"  [{label}]")
                print(f"    • Route Option     : {best.title}")
                print(f"    • Total Duration   : {best.total_duration_minutes} min (Freeflow: {best.freeflow_duration_minutes} min)")
                print(f"    • Traffic Delay    : +{best.traffic_delay_minutes} min")
                print(f"    • Crowdedness      : {best.primary_crowdedness} (Comfort Score: {best.comfort_score}/100)")
                print(f"    • Advice           : {best.summary_advice}")
            else:
                print(f"  [{label}] No candidate route found.")

if __name__ == "__main__":
    run_benchmarks()
