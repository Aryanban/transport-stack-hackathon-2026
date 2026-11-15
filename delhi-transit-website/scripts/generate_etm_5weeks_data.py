#!/usr/bin/env python3
"""
generate_etm_5weeks_data.py
CLI generator to synthesize multi-week, multi-route ETM & e-ticketing transaction dumps
for Delhi bus routes (Problem 2: Crowdedness-aware journey planner).

Usage:
    python scripts/generate_etm_5weeks_data.py --days 35 --output data/etm_ticketing_data/etm_transactions_extended.csv
"""

import os
import sys
import csv
import random
import argparse
from datetime import datetime, timedelta

CORRIDOR_STOPS = {
    "502UP": [
        ("Mehrauli Terminal", "Stage 1"), ("Qutub Minar Metro", "Stage 1"),
        ("Malviya Nagar Corner", "Stage 2"), ("Hauz Khas", "Stage 2"),
        ("Green Park Metro", "Stage 2"), ("AIIMS Hospital", "Stage 3"),
        ("INA Colony / Dilli Haat", "Stage 3"), ("Safdarjung Tomb", "Stage 4"),
        ("Central Secretariat", "Stage 5"), ("Shivaji Stadium / CP", "Stage 5"),
        ("ITO Metro", "Stage 6"), ("Delhi Gate", "Stage 6"),
        ("ISBT Kashmere Gate City Terminal", "Stage 6")
    ],
    "761DOWN": [
        ("Azadpur Terminal", "Stage 1"), ("Shalimar Bagh", "Stage 1"),
        ("Madhuban Chowk", "Stage 2"), ("Mangolpuri Flyover", "Stage 2"),
        ("Peera Garhi Chowk", "Stage 3"), ("Paschim Vihar", "Stage 3"),
        ("District Centre Janakpuri", "Stage 4"), ("Uttam Nagar East Metro", "Stage 4"),
        ("Dabri Mor", "Stage 5"), ("Mangla Puri Terminal", "Stage 5")
    ],
    "534UP": [
        ("Anand Vihar ISBT", "Stage 1"), ("Preet Vihar Metro", "Stage 1"),
        ("Laxmi Nagar Metro", "Stage 2"), ("Sarai Kale Khan ISBT", "Stage 3"),
        ("Ashram Chowk", "Stage 4"), ("Nehru Place Bus Terminal", "Stage 5"),
        ("Chirag Delhi", "Stage 5"), ("Saket Crossing", "Stage 6"),
        ("Mehrauli Terminal", "Stage 6")
    ],
    "102UP": [
        ("Old Delhi Railway Station (T)", "Stage 1"), ("Mori Gate Terminal", "Stage 1"),
        ("Shakti Nagar", "Stage 2"), ("Wazirpur Depot", "Stage 3"),
        ("Pitampura Power House", "Stage 4"), ("Rohini Sec 21", "Stage 5"),
        ("Rohini Sec 22 Terminal", "Stage 5")
    ],
    "449UP": [
        ("ISBT Kashmiri Gate", "Stage 1"), ("Delhi Gate", "Stage 1"),
        ("ITO Ring Road", "Stage 2"), ("Nizamuddin Dargah", "Stage 3"),
        ("Lajpat Nagar Ring Road", "Stage 4"), ("Nehru Place Terminal", "Stage 5"),
        ("Ambedkar Nagar Sec 5 (T)", "Stage 6")
    ]
}

PAYMENT_PROFILES = [
    ("General Adult", 10, "ETM Conductor Cash", 0.35),
    ("General Adult", 15, "One Delhi QR App", 0.15),
    ("General Adult", 10, "Chartr App", 0.08),
    ("Daily Pink Pass (Female Commuter)", 0, "ETM Free Pink Ticket", 0.28),
    ("Daily Pink Pass (Female Commuter)", 0, "One Delhi QR App", 0.08),
    ("Student Concession", 5, "ETM Conductor Cash", 0.03),
    ("Senior Citizen Concession", 5, "ETM Conductor Cash", 0.03)
]

def generate_transactions(num_days=35, output_file=None, seed=42):
    random.seed(seed)
    start_date = datetime(2026, 10, 1)
    
    if not output_file:
        output_file = "data/etm_ticketing_data/delhi_bus_etm_5weeks_transactions_sample.csv"
        
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    
    ticket_id = 70000001
    total_records = 0
    
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ticket_id", "timestamp", "date", "hour", "route_id", "bus_registration",
            "conductor_id", "boarding_stop_id", "boarding_stop_name", "boarding_fare_stage",
            "alighting_stop_id", "alighting_stop_name", "alighting_fare_stage",
            "trip_direction", "fare_inr", "passenger_category", "payment_method"
        ])
        
        for d in range(num_days):
            curr_date = start_date + timedelta(days=d)
            dt_str = curr_date.strftime("%Y-%m-%d")
            is_wknd = curr_date.weekday() >= 5
            
            for route_id, stops in CORRIDOR_STOPS.items():
                direction = "UP" if route_id.endswith("UP") else "DOWN"
                bus_reg = f"DL1PC{random.randint(1100, 9999)}"
                cond_id = f"COND_{random.randint(101, 399)}"
                
                # Iterate across active operating hours
                for hour in range(6, 23):
                    # Peak vs off-peak transaction intensity
                    if 8 <= hour <= 11 or 17 <= hour <= 20:
                        batch_size = random.randint(8, 16) if not is_wknd else random.randint(4, 9)
                    elif 12 <= hour <= 15:
                        batch_size = random.randint(3, 7)
                    else:
                        batch_size = random.randint(1, 4)
                        
                    for _ in range(batch_size):
                        b_idx = random.randint(0, len(stops) - 2)
                        a_idx = random.randint(b_idx + 1, len(stops) - 1)
                        
                        b_name, b_stage = stops[b_idx]
                        a_name, a_stage = stops[a_idx]
                        
                        minute = random.randint(0, 59)
                        second = random.randint(0, 59)
                        ts = f"{dt_str} {hour:02d}:{minute:02d}:{second:02d}"
                        
                        # Pick payment profile based on weight
                        roll = random.random()
                        cum = 0.0
                        chosen = PAYMENT_PROFILES[0]
                        for prof in PAYMENT_PROFILES:
                            cum += prof[3]
                            if roll <= cum:
                                chosen = prof
                                break
                                
                        p_cat, fare, pay_mode, _ = chosen
                        
                        writer.writerow([
                            ticket_id, ts, dt_str, hour, route_id, bus_reg, cond_id,
                            2000 + b_idx, b_name, b_stage,
                            2000 + a_idx, a_name, a_stage,
                            direction, fare, p_cat, pay_mode
                        ])
                        ticket_id += 1
                        total_records += 1

    print(f"Successfully generated {total_records} transactions across {num_days} days to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate 5-week ETM transaction datasets")
    parser.add_argument("--days", type=int, default=35, help="Number of days to simulate (default: 35)")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    
    generate_transactions(args.days, args.output, args.seed)
