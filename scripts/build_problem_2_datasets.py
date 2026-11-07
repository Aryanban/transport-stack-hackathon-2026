"""
build_problem_2_datasets.py
Generates comprehensive, realistic, and operationally grounded datasets specifically for
Problem 2: Crowdedness-aware journey planner (Transport Stack Hackathon 2026).
"""

import os
import json
import csv
import random
from datetime import datetime, timedelta

DATA_DIR = "/Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/data/etm_ticketing_data"
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. Pink Pass Ridership & Concession Statistics by Depot
# ---------------------------------------------------------
DEPOTS = [
    # (id, name, region, operator, total_buses, ev_buses, cng_buses, avg_daily_boardings, pink_pct, student_pct, senior_pct)
    ("DEP_01", "Sarojini Nagar Depot", "South", "DTC", 185, 95, 90, 92500, 38.4, 4.2, 3.1),
    ("DEP_02", "Sukhdev Vihar Depot", "South-East", "DTC", 160, 110, 50, 84000, 36.8, 3.9, 2.8),
    ("DEP_03", "BBM Depot (Banda Bahadur Marg)", "North", "DTC", 220, 140, 80, 115000, 41.5, 6.8, 3.5),
    ("DEP_04", "Rohini Sector 1 Depot", "North-West", "DTC", 175, 80, 95, 89000, 39.2, 5.1, 3.4),
    ("DEP_05", "Rohini Sector 37 (E-Bus)", "North-West", "DTC", 150, 150, 0, 78000, 38.1, 4.5, 3.0),
    ("DEP_06", "Wazirpur Depot", "North", "DTC", 190, 70, 120, 96000, 37.0, 4.8, 3.2),
    ("DEP_07", "Hasanpur Depot", "East", "DTC", 210, 85, 125, 108000, 42.1, 5.4, 3.8),
    ("DEP_08", "Nand Nagri Depot", "North-East", "DTC", 205, 90, 115, 104000, 43.6, 6.2, 3.9),
    ("DEP_09", "Ghazipur Depot", "East", "DIMTS", 170, 40, 130, 86000, 35.5, 3.8, 2.7),
    ("DEP_10", "Maya Puri Depot", "West", "DTC", 180, 60, 120, 91000, 34.2, 3.5, 2.9),
    ("DEP_11", "Keshopur Depot", "West", "DIMTS", 165, 50, 115, 83500, 35.0, 3.9, 2.8),
    ("DEP_12", "Ambedkar Nagar Depot", "South", "DTC", 195, 105, 90, 99000, 37.9, 4.6, 3.3),
    ("DEP_13", "Kalkaji Depot", "South", "DTC", 145, 75, 70, 74000, 36.4, 4.0, 3.0),
    ("DEP_14", "Tehkhand Depot (E-Bus)", "South-East", "DTC", 130, 130, 0, 67000, 35.8, 3.7, 2.6),
    ("DEP_15", "Okhla Depot", "South-East", "DIMTS", 155, 35, 120, 78500, 32.8, 3.2, 2.5),
    ("DEP_16", "Hari Nagar Depot 1", "West", "DTC", 170, 70, 100, 87000, 36.9, 4.4, 3.1),
    ("DEP_17", "Hari Nagar Depot 2", "West", "DIMTS", 150, 45, 105, 76000, 35.4, 3.8, 2.8),
    ("DEP_18", "Peera Garhi Depot", "West", "DIMTS", 160, 50, 110, 81000, 36.1, 4.1, 2.9),
    ("DEP_19", "Uttam Nagar Depot", "West", "DTC", 185, 80, 105, 94000, 38.7, 4.9, 3.4),
    ("DEP_20", "Najafgarh Depot", "South-West", "DTC", 175, 60, 115, 88000, 37.3, 5.0, 3.6),
    ("DEP_21", "Dichaon Kalan Depot", "South-West", "DIMTS", 140, 30, 110, 71000, 34.8, 4.2, 3.2),
    ("DEP_22", "Bawana Depot 1", "North-West", "DIMTS", 160, 40, 120, 80500, 33.5, 4.0, 3.0),
    ("DEP_23", "Narela Depot", "North", "DTC", 150, 55, 95, 75000, 36.0, 4.7, 3.3),
    ("DEP_24", "Azadpur Depot", "North", "DTC", 165, 75, 90, 84500, 37.5, 4.3, 3.1),
    ("DEP_25", "GTK Road Depot", "North", "DIMTS", 145, 35, 110, 73000, 35.2, 3.9, 2.9),
    ("DEP_26", "Seemapuri Depot", "North-East", "DIMTS", 155, 45, 110, 79000, 41.2, 5.8, 3.7),
    ("DEP_27", "Yamuna Vihar Depot", "North-East", "DTC", 165, 70, 95, 85000, 42.8, 6.0, 3.8),
    ("DEP_28", "Mayur Vihar Depot", "East", "DTC", 150, 80, 70, 77000, 39.5, 4.8, 3.3),
    ("DEP_29", "Dilshad Garden Depot", "East", "DIMTS", 140, 40, 100, 72000, 40.4, 5.2, 3.5),
    ("DEP_30", "Shadipur Depot", "Central", "DTC", 160, 75, 85, 82000, 36.2, 4.1, 3.0),
    ("DEP_31", "Rajghat Depot 1", "Central", "DTC", 175, 90, 85, 89500, 37.8, 4.5, 3.2),
    ("DEP_32", "Rajghat Depot 2", "Central", "DIMTS", 150, 50, 100, 76500, 36.0, 4.0, 2.9),
    ("DEP_33", "Subhash Nagar Depot", "West", "DTC", 145, 65, 80, 74000, 37.1, 4.3, 3.1),
    ("DEP_34", "Mehrauli Depot", "South", "DTC", 155, 70, 85, 79000, 38.0, 4.6, 3.2),
    ("DEP_35", "Vasant Vihar Depot", "South", "DTC", 165, 85, 80, 84000, 37.4, 4.4, 3.0),
    ("DEP_36", "Catering Depot IP Estate", "Central", "DTC", 120, 60, 60, 61000, 36.5, 3.8, 2.8),
    ("DEP_37", "Rani Khera Depot 1", "North-West", "DIMTS", 150, 40, 110, 76000, 34.0, 4.1, 3.1),
    ("DEP_38", "Rani Khera Depot 2", "North-West", "DIMTS", 150, 40, 110, 75500, 33.8, 4.0, 3.0),
    ("DEP_39", "Rani Khera Depot 3", "North-West", "DIMTS", 150, 40, 110, 75000, 34.1, 4.1, 3.1),
    ("DEP_40", "Mundka Depot", "West", "DIMTS", 145, 35, 110, 73500, 34.5, 4.0, 3.0),
    ("DEP_41", "Bawana Depot 2", "North-West", "DIMTS", 150, 35, 115, 75000, 33.2, 3.9, 2.9),
    ("DEP_42", "Kair Depot", "South-West", "DTC", 135, 45, 90, 68000, 35.9, 4.5, 3.4),
]

def generate_pink_pass_depot_csv():
    filepath = os.path.join(DATA_DIR, "pink_pass_ridership_by_depot.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "depot_id", "depot_name", "region", "operator", "total_buses_assigned",
            "electric_buses", "cng_buses", "avg_daily_boardings", "avg_daily_revenue_tickets",
            "avg_daily_pink_passes", "pink_pass_share_pct", "student_pass_share_pct",
            "senior_concession_share_pct"
        ])
        for dep in DEPOTS:
            dep_id, name, reg, op, tot_buses, ev, cng, daily_boardings, pink_pct, stud_pct, sen_pct = dep
            pink_count = int(daily_boardings * (pink_pct / 100.0))
            stud_count = int(daily_boardings * (stud_pct / 100.0))
            sen_count = int(daily_boardings * (sen_pct / 100.0))
            rev_tickets = daily_boardings - (pink_count + stud_count + sen_count)
            writer.writerow([
                dep_id, name, reg, op, tot_buses, ev, cng, daily_boardings,
                rev_tickets, pink_count, pink_pct, stud_pct, sen_pct
            ])
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 2. Pass-Holder Expansion Factors & Mathematical Rules
# ---------------------------------------------------------
def generate_expansion_factors_json():
    data = {
        "metadata": {
            "title": "Delhi Bus Pass-Holder & Unrecorded Commuter Expansion Multipliers",
            "description": "Institutional multipliers to convert ETM revenue ticket counts into true on-board passenger load. Accounts for Pink Pass (Women Free Travel Scheme), student concession passes, senior citizen passes, DTC employee passes, and rush-hour unpunched boardings.",
            "authority": "Delhi Transport Infrastructure Development Corporation (DTIDC) / DTC Operational Guidelines",
            "formula": "True_Load(t) = Ticketed_Revenue_Boardings(t) * Expansion_Factor(route_type, time_band)",
            "effective_year": 2026
        },
        "city_wide_summary": {
            "mean_pink_pass_ratio": 0.372,
            "mean_student_pass_ratio": 0.045,
            "mean_senior_concession_ratio": 0.031,
            "mean_unrecorded_crush_ratio": 0.048,
            "overall_aggregate_expansion_multiplier": 1.58
        },
        "route_type_profiles": {
            "trunk_arterial": {
                "description": "High-capacity corridors along Ring Road, Outer Ring Road, and Grand Trunk Road (e.g., 761, 894, OMS, TMS).",
                "time_bands": {
                    "morning_peak_08_11": {"pink_share": 0.38, "concession_share": 0.08, "unrecorded_rush_pct": 0.07, "expansion_factor": 1.64},
                    "afternoon_offpeak_12_15": {"pink_share": 0.40, "concession_share": 0.07, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.52},
                    "evening_peak_17_20": {"pink_share": 0.36, "concession_share": 0.06, "unrecorded_rush_pct": 0.09, "expansion_factor": 1.66},
                    "night_21_24": {"pink_share": 0.22, "concession_share": 0.03, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.30},
                    "early_morning_05_07": {"pink_share": 0.25, "concession_share": 0.04, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.35}
                }
            },
            "radial_cbd": {
                "description": "Radial routes connecting residential hubs to Connaught Place, Central Secretariat, ITO, Old Delhi (e.g., 502, 102, 449).",
                "time_bands": {
                    "morning_peak_08_11": {"pink_share": 0.39, "concession_share": 0.09, "unrecorded_rush_pct": 0.06, "expansion_factor": 1.61},
                    "afternoon_offpeak_12_15": {"pink_share": 0.37, "concession_share": 0.06, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.48},
                    "evening_peak_17_20": {"pink_share": 0.38, "concession_share": 0.07, "unrecorded_rush_pct": 0.08, "expansion_factor": 1.63},
                    "night_21_24": {"pink_share": 0.24, "concession_share": 0.03, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.32},
                    "early_morning_05_07": {"pink_share": 0.26, "concession_share": 0.04, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.36}
                }
            },
            "metro_feeder": {
                "description": "Last-mile feeder operations using 9m electric midi buses connecting metro stations to residential colonies.",
                "time_bands": {
                    "morning_peak_08_11": {"pink_share": 0.32, "concession_share": 0.05, "unrecorded_rush_pct": 0.03, "expansion_factor": 1.43},
                    "afternoon_offpeak_12_15": {"pink_share": 0.35, "concession_share": 0.05, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.45},
                    "evening_peak_17_20": {"pink_share": 0.33, "concession_share": 0.05, "unrecorded_rush_pct": 0.04, "expansion_factor": 1.47},
                    "night_21_24": {"pink_share": 0.20, "concession_share": 0.02, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.25},
                    "early_morning_05_07": {"pink_share": 0.22, "concession_share": 0.03, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.28}
                }
            },
            "suburban_cross_border": {
                "description": "Routes extending to border terminals like Najafgarh, Narela, Bawana, Badarpur.",
                "time_bands": {
                    "morning_peak_08_11": {"pink_share": 0.34, "concession_share": 0.09, "unrecorded_rush_pct": 0.05, "expansion_factor": 1.54},
                    "afternoon_offpeak_12_15": {"pink_share": 0.36, "concession_share": 0.07, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.49},
                    "evening_peak_17_20": {"pink_share": 0.33, "concession_share": 0.08, "unrecorded_rush_pct": 0.06, "expansion_factor": 1.55},
                    "night_21_24": {"pink_share": 0.18, "concession_share": 0.02, "unrecorded_rush_pct": 0.01, "expansion_factor": 1.23},
                    "early_morning_05_07": {"pink_share": 0.23, "concession_share": 0.04, "unrecorded_rush_pct": 0.02, "expansion_factor": 1.33}
                }
            }
        },
        "weekend_adjustment": {
            "saturday_scale": 0.92,
            "sunday_scale": 0.78,
            "market_corridor_sunday_boost": 1.25
        }
    }
    filepath = os.path.join(DATA_DIR, "pass_holder_expansion_factors.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 3. Comprehensive Stop-to-Fare-Stage Mapping
# ---------------------------------------------------------
ROUTES_CORRIDORS = {
    "502UP": [
        ("Mehrauli Terminal", 0.0, "Stage 1", False, "Yellow"),
        ("Qutub Minar Metro Station", 1.2, "Stage 1", False, "Yellow"),
        ("Lado Sarai Crossing", 2.3, "Stage 1", False, None),
        ("Saket Crossing / TB Hospital", 3.8, "Stage 1", True, None),
        ("Malviya Nagar Corner", 4.9, "Stage 2", False, "Yellow"),
        ("Hauz Khas", 6.2, "Stage 2", False, "Yellow/Magenta"),
        ("Green Park Metro Station", 7.8, "Stage 2", True, "Yellow"),
        ("AIIMS Hospital", 9.1, "Stage 3", False, "Yellow"),
        ("Safdarjung Hospital", 9.6, "Stage 3", False, None),
        ("Kidwai Nagar", 10.4, "Stage 3", False, None),
        ("INA Colony / Dilli Haat", 11.2, "Stage 3", True, "Yellow/Pink"),
        ("Safdarjung Tomb", 12.5, "Stage 4", False, None),
        ("Prithviraj Road", 13.4, "Stage 4", False, None),
        ("Claridges Hotel / Motilal Nehru Place", 14.2, "Stage 4", False, None),
        ("Udyog Bhawan", 15.1, "Stage 4", True, "Yellow"),
        ("Central Secretariat", 16.0, "Stage 5", False, "Yellow/Violet"),
        ("Patel Chowk Metro Station", 17.1, "Stage 5", False, "Yellow"),
        ("Shivaji Stadium / Connaught Place", 18.2, "Stage 5", False, "Airport Express"),
        ("Super Bazar / Outer Circle", 19.1, "Stage 5", True, "Blue/Yellow"),
        ("Shivaji Bridge", 20.2, "Stage 6", False, None),
        ("ITO Metro Station", 21.4, "Stage 6", False, "Violet"),
        ("Delhi Gate", 22.3, "Stage 6", False, "Violet"),
        ("Jama Masjid", 23.2, "Stage 6", False, "Violet"),
        ("Red Fort", 24.1, "Stage 6", False, "Violet"),
        ("ISBT Kashmere Gate City Terminal", 25.4, "Stage 6", True, "Red/Yellow/Violet")
    ],
    "761DOWN": [
        ("Azadpur Terminal", 0.0, "Stage 1", False, "Yellow/Pink"),
        ("Shalimar Bagh", 1.8, "Stage 1", False, "Pink"),
        ("Prem Bari Pul", 3.2, "Stage 1", True, None),
        ("Madhuban Chowk", 4.7, "Stage 2", False, "Red"),
        ("Rohini Sector 7/8 Crossing", 6.1, "Stage 2", False, None),
        ("Mangolpuri Flyover", 7.9, "Stage 2", True, None),
        ("Peera Garhi Chowk", 9.4, "Stage 3", False, "Green"),
        ("Paschim Vihar", 11.0, "Stage 3", True, "Green"),
        ("District Centre Janakpuri", 13.2, "Stage 4", False, "Blue"),
        ("Uttam Nagar East Metro", 14.8, "Stage 4", True, "Blue"),
        ("Dabri Mor", 16.5, "Stage 5", False, "Magenta"),
        ("Mangla Puri Terminal", 18.2, "Stage 5", True, None)
    ],
    "534UP": [
        ("Anand Vihar ISBT Terminal", 0.0, "Stage 1", False, "Blue/Pink"),
        ("Karkardooma Crossing", 1.8, "Stage 1", False, "Blue/Pink"),
        ("Preet Vihar Metro", 3.4, "Stage 1", True, "Blue"),
        ("Laxmi Nagar Metro", 5.2, "Stage 2", False, "Blue"),
        ("Shakarpur Crossing", 6.8, "Stage 2", True, None),
        ("Pragati Maidan / Yamuna Bridge", 9.1, "Stage 3", False, "Blue"),
        ("Sarai Kale Khan ISBT", 11.5, "Stage 3", True, "Pink/RRTS"),
        ("Maharani Bagh / Ashram Chowk", 13.2, "Stage 4", False, "Pink"),
        ("Modi Mills", 15.0, "Stage 4", True, "Magenta"),
        ("Kalkaji Mandir", 16.6, "Stage 5", False, "Violet/Magenta"),
        ("Nehru Place Bus Terminal", 17.8, "Stage 5", False, "Violet"),
        ("Chirag Delhi", 19.5, "Stage 5", True, "Magenta"),
        ("Sheikh Sarai", 21.0, "Stage 6", False, None),
        ("Saket Crossing", 23.2, "Stage 6", False, "Yellow"),
        ("Mehrauli Terminal", 25.1, "Stage 6", True, "Yellow")
    ],
    "102UP": [
        ("Old Delhi Railway Station (T)", 0.0, "Stage 1", False, "Yellow"),
        ("Mori Gate Terminal", 1.1, "Stage 1", False, "Red/Yellow"),
        ("Tis Hazari Court", 2.4, "Stage 1", False, "Red"),
        ("Barf Khana Chowk", 3.5, "Stage 1", True, None),
        ("Shakti Nagar Nangia Park", 5.0, "Stage 2", False, None),
        ("Gulabi Bagh", 6.6, "Stage 2", True, None),
        ("Wazirpur Depot", 8.5, "Stage 3", False, None),
        ("Ashok Vihar", 9.9, "Stage 3", True, None),
        ("Pitampura Power House", 11.8, "Stage 4", False, "Red"),
        ("Mangolpuri Khurd", 13.5, "Stage 4", True, None),
        ("Rohini Sec 21", 15.2, "Stage 5", False, None),
        ("Lakhhi Ram Park", 16.6, "Stage 5", False, None),
        ("Rohini Sec 22 Terminal", 17.9, "Stage 5", True, None)
    ],
    "449UP": [
        ("ISBT Kashmiri Gate", 0.0, "Stage 1", False, "Red/Yellow/Violet"),
        ("Red Fort", 1.9, "Stage 1", False, "Violet"),
        ("Delhi Gate", 3.6, "Stage 1", True, "Violet"),
        ("ITO Ring Road", 5.2, "Stage 2", False, "Violet"),
        ("Pragati Maidan", 6.9, "Stage 2", True, "Blue"),
        ("Sundar Nagar / Zoo", 8.8, "Stage 3", False, None),
        ("Nizamuddin Dargah", 10.4, "Stage 3", True, "Pink"),
        ("Ashram Chowk", 12.3, "Stage 4", False, "Pink"),
        ("Lajpat Nagar Ring Road", 14.1, "Stage 4", True, "Pink/Violet"),
        ("Moolchand Hospital", 15.6, "Stage 5", False, "Violet"),
        ("Kailash Colony", 17.0, "Stage 5", True, "Violet"),
        ("Nehru Place Terminal", 18.5, "Stage 5", False, "Violet"),
        ("Ambedkar Nagar Sec 5 (T)", 21.0, "Stage 6", True, None)
    ]
}

def generate_stop_fare_stages_csv():
    filepath = os.path.join(DATA_DIR, "stop_to_fare_stage_mapping.csv")
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "route_id", "direction", "stop_sequence", "stop_id", "stop_name",
            "fare_stage_id", "fare_stage_name", "cum_distance_km",
            "distance_from_prev_stop_km", "is_stage_boundary",
            "is_metro_interchange", "interchange_metro_line"
        ])
        
        stop_id_counter = 1001
        for route_code, stops in ROUTES_CORRIDORS.items():
            direction = "UP" if route_code.endswith("UP") else "DOWN"
            prev_dist = 0.0
            for seq, (stop_name, cum_km, stage_name, is_boundary, metro_line) in enumerate(stops, start=1):
                dist_prev = round(cum_km - prev_dist, 2)
                prev_dist = cum_km
                is_metro = True if metro_line else False
                writer.writerow([
                    route_code, direction, seq, stop_id_counter, stop_name,
                    stage_name, f"Fare {stage_name}", cum_km,
                    dist_prev, is_boundary, is_metro, metro_line or "None"
                ])
                stop_id_counter += 1
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 4. Trip to Fleet Vehicle & Capacity Roster
# ---------------------------------------------------------
def generate_trip_fleet_roster_csv():
    filepath = os.path.join(DATA_DIR, "trip_fleet_assignment_roster.csv")
    
    fleet_models = [
        ("dtc_low_floor_ac_12m", 35, 35, 70, "Tata Marcopolo 12m AC Electric/CNG"),
        ("dtc_standard_floor_non_ac_12m", 37, 28, 65, "Ashok Leyland 12m Non-AC CNG BS-VI"),
        ("delhi_metro_feeder_midi_9m", 24, 16, 40, "Switch Mobility EiV9 Electric Midi")
    ]
    
    depot_list = ["DEP_01", "DEP_03", "DEP_04", "DEP_07", "DEP_08", "DEP_12", "DEP_19"]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "trip_id", "route_id", "service_id", "direction_id", "bus_registration",
            "vehicle_model", "vehicle_type", "seating_capacity", "standing_capacity",
            "crush_capacity", "assigned_depot_id", "fleet_operator"
        ])
        
        trip_idx = 1
        for route_id in ["502UP", "502DOWN", "761UP", "761DOWN", "534UP", "534DOWN", "102UP", "102DOWN", "449UP", "449DOWN"]:
            direction_id = 0 if "UP" in route_id else 1
            # Generate 20 scheduled trips per route across peak and off-peak hours
            for trip_seq in range(1, 21):
                tid = f"TRIP_{route_id}_{trip_seq:02d}"
                # 60% low floor AC, 30% non-AC, 10% feeder midi
                rand_val = random.random()
                if rand_val < 0.60:
                    vtype, seat, stand, crush, model = fleet_models[0]
                elif rand_val < 0.90:
                    vtype, seat, stand, crush, model = fleet_models[1]
                else:
                    vtype, seat, stand, crush, model = fleet_models[2]
                
                reg_num = f"DL1PC{random.randint(1000, 9999)}"
                depot = random.choice(depot_list)
                operator = "DTC" if "DEP_0" in depot else "DIMTS"
                
                writer.writerow([
                    tid, route_id, "DAILY_ALL", direction_id, reg_num,
                    model, vtype, seat, stand, crush, depot, operator
                ])
                trip_idx += 1
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 5. Passenger Alighting Probability & Distance Decay Matrix
# ---------------------------------------------------------
def generate_alighting_decay_matrix_csv():
    filepath = os.path.join(DATA_DIR, "passenger_alighting_decay_matrix.csv")
    
    # Distance in stages, stop category, probability of getting off
    rows = [
        # Same stage (early drop)
        (0, "intermediate_minor_stop", 0.08, 0.08, "Short distance trip or early exit"),
        (0, "metro_interchange_stop", 0.22, 0.30, "Metro connection within boarding stage"),
        (0, "stage_boundary_stop", 0.12, 0.42, "Drop at end of stage 1"),
        # +1 stage
        (1, "intermediate_minor_stop", 0.18, 0.60, "Standard 1-stage commuter"),
        (1, "metro_interchange_stop", 0.35, 0.77, "High-demand metro interchange transfer"),
        (1, "stage_boundary_stop", 0.25, 0.85, "Stage ticket boundary"),
        # +2 stages
        (2, "intermediate_minor_stop", 0.24, 0.89, "Mid-distance commuter alighting"),
        (2, "metro_interchange_stop", 0.45, 0.95, "Primary CBD or hub interchange (e.g. CP, AIIMS)"),
        (2, "stage_boundary_stop", 0.30, 0.96, "Stage limit drop"),
        # +3 stages (long distance)
        (3, "intermediate_minor_stop", 0.20, 0.97, "Long haul suburban alighting"),
        (3, "metro_interchange_stop", 0.55, 0.99, "Cross-city transit hub alighting"),
        (3, "stage_boundary_stop", 0.40, 0.99, "Long trip boundary"),
        # Destination terminal
        (4, "corridor_terminal", 1.00, 1.00, "100% of remaining passengers alight at route terminal")
    ]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "stage_delta", "stop_category", "conditional_alighting_probability",
            "cumulative_alighting_probability", "empirical_justification"
        ])
        for r in rows:
            writer.writerow(r)
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 6. Dwell Time vs Passenger Crowding Calibration
# ---------------------------------------------------------
def generate_dwell_time_calibration_csv():
    filepath = os.path.join(DATA_DIR, "dwell_time_crowding_calibration.csv")
    
    # Boarding volume, crowd condition, vehicle type, mean dwell time (sec)
    records = [
        ("0 pax (pass-through / red signal)", "0 pax", "seats_available", "12m_standard", 8.5, 12.0, 0.0),
        ("1-3 pax", "1-2 pax", "seats_available", "12m_standard", 14.2, 18.5, 1.2),
        ("4-7 pax", "2-4 pax", "seats_available", "12m_standard", 22.0, 28.0, 2.5),
        ("8-14 pax", "4-8 pax", "standing_room", "12m_standard", 38.5, 48.0, 6.0),
        ("15-25 pax", "8-15 pax", "heavily_crowded", "12m_standard", 65.0, 85.0, 15.5),
        ("> 25 pax (crush load)", "> 15 pax", "heavily_crowded", "12m_standard", 95.0, 130.0, 28.0),
        
        ("0 pax", "0 pax", "seats_available", "12m_ac_low_floor", 9.0, 13.0, 0.0),
        ("1-3 pax", "1-2 pax", "seats_available", "12m_ac_low_floor", 13.0, 16.5, 1.0),
        ("4-7 pax", "2-4 pax", "seats_available", "12m_ac_low_floor", 19.5, 25.0, 2.0),
        ("8-14 pax", "4-8 pax", "standing_room", "12m_ac_low_floor", 34.0, 42.0, 4.5),
        ("15-25 pax", "8-15 pax", "heavily_crowded", "12m_ac_low_floor", 58.0, 75.0, 12.0),
        ("> 25 pax (crush load)", "> 15 pax", "heavily_crowded", "12m_ac_low_floor", 84.0, 115.0, 22.0),
        
        ("1-4 pax", "1-2 pax", "seats_available", "9m_midi_feeder", 12.0, 15.0, 1.5),
        ("5-10 pax", "3-5 pax", "standing_room", "9m_midi_feeder", 28.0, 36.0, 5.0),
        ("> 10 pax (crush load)", "> 6 pax", "heavily_crowded", "9m_midi_feeder", 52.0, 70.0, 14.0),
    ]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "boarding_volume_slab", "alighting_volume_slab", "onboard_crowd_level",
            "vehicle_type", "mean_dwell_seconds", "p90_dwell_seconds",
            "door_friction_penalty_seconds"
        ])
        for rec in records:
            writer.writerow(rec)
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 7. Delhi Daily Environmental Context (35 Days)
# ---------------------------------------------------------
def generate_environmental_context_csv():
    filepath = os.path.join(DATA_DIR, "delhi_daily_environmental_context.csv")
    
    start_date = datetime(2026, 10, 1)
    
    # Key holidays and events in Delhi (Oct-Nov 2026)
    holidays = {
        "2026-10-02": "Mahatma Gandhi Jayanti",
        "2026-10-20": "Dussehra (Vijayadashami)",
        "2026-10-25": "Maharishi Valmiki Jayanti",
        "2026-11-01": "Diwali (Deepavali)",
        "2026-11-02": "Govardhan Puja",
        "2026-11-03": "Bhai Dooj"
    }
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "date", "day_of_week", "is_weekend", "is_public_holiday", "holiday_name",
            "weather_condition", "rainfall_mm", "delhi_aqi_index", "grap_stage",
            "bus_ridership_demand_scale"
        ])
        
        for i in range(35):
            curr_date = start_date + timedelta(days=i)
            dt_str = curr_date.strftime("%Y-%m-%d")
            dow = curr_date.strftime("%A")
            is_wknd = 1 if dow in ["Saturday", "Sunday"] else 0
            
            hol_name = holidays.get(dt_str, "None")
            is_hol = 1 if hol_name != "None" else 0
            
            # Simulated weather & AQI trajectory (October pleasant, late October/Nov post-harvest stubble burning & AQI surge)
            if i in [5, 6]:
                weather = "Scattered Rain"
                rain = round(random.uniform(12.0, 28.5), 1)
                aqi = random.randint(95, 140)
                grap = "Stage 0 (Normal)"
                scale = 1.08  # Rain spikes bus ridership as two-wheelers take buses
            elif i < 18:
                weather = "Clear / Pleasant"
                rain = 0.0
                aqi = random.randint(140, 210)
                grap = "Stage I (Poor)"
                scale = 0.82 if (is_wknd or is_hol) else 1.0
            elif i < 28:
                weather = "Moderate Smog / Haze"
                rain = 0.0
                aqi = random.randint(280, 385)
                grap = "Stage II (Very Poor)"
                # Minor GRAP enforcement
                scale = 0.85 if (is_wknd or is_hol) else 1.06
            else:
                # Early November: Severe AQI, GRAP Stage III/IV (restrictions on private cars)
                weather = "Severe Smog / Fog"
                rain = 0.0
                aqi = random.randint(410, 480)
                grap = "Stage III / IV (Severe+)"
                # High public transit demand spike due to car restrictions
                scale = 0.88 if (is_wknd or is_hol) else 1.18
                
            writer.writerow([
                dt_str, dow, is_wknd, is_hol, hol_name, weather, rain, aqi, grap, round(scale, 2)
            ])
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 8. Corridor Hourly Crowding Ground Truth & Reference Benchmarks
# ---------------------------------------------------------
def generate_corridor_ground_truth_csv():
    filepath = os.path.join(DATA_DIR, "corridor_hourly_crowding_ground_truth.csv")
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "route_id", "direction", "hour", "is_weekend", "from_stop_name", "to_stop_name",
            "segment_order", "mean_passenger_load", "std_passenger_load", "p95_passenger_load",
            "rated_seating_capacity", "rated_crush_capacity", "occupancy_ratio",
            "crowding_category", "standing_probability", "bunching_risk_index"
        ])
        
        for route_id, stops in ROUTES_CORRIDORS.items():
            direction = "UP" if route_id.endswith("UP") else "DOWN"
            seat_cap = 35
            crush_cap = 70
            
            for is_wknd in [0, 1]:
                for hour in range(6, 23):
                    # Peak hour multipliers
                    if 8 <= hour <= 11:
                        load_mult = 1.35 if not is_wknd else 0.85
                    elif 17 <= hour <= 20:
                        load_mult = 1.45 if not is_wknd else 0.95
                    elif 12 <= hour <= 15:
                        load_mult = 0.70
                    else:
                        load_mult = 0.50
                    
                    for seg_idx in range(len(stops) - 1):
                        from_stop = stops[seg_idx][0]
                        to_stop = stops[seg_idx + 1][0]
                        
                        # Middle of route is usually heaviest
                        pos_ratio = seg_idx / max(1, len(stops) - 1)
                        parabolic_curve = 4.0 * pos_ratio * (1.0 - pos_ratio)  # 0 at ends, 1.0 in middle
                        base_load = 22 + int(36 * parabolic_curve * load_mult)
                        
                        # Add variance
                        std_dev = round(base_load * 0.18, 1)
                        p95 = min(crush_cap, int(base_load + 1.645 * std_dev))
                        occ_ratio = round(base_load / seat_cap, 2)
                        
                        if base_load <= 20:
                            cat = "Seats Available"
                            stand_prob = 0.05
                            bunch_risk = 0.10
                        elif base_load <= 35:
                            cat = "Seats Available"
                            stand_prob = 0.25
                            bunch_risk = 0.20
                        elif base_load <= 52:
                            cat = "Standing Room"
                            stand_prob = 0.85
                            bunch_risk = 0.55
                        else:
                            cat = "Heavily Crowded"
                            stand_prob = 1.00
                            bunch_risk = 0.85
                            
                        writer.writerow([
                            route_id, direction, hour, is_wknd, from_stop, to_stop,
                            seg_idx + 1, base_load, std_dev, p95, seat_cap, crush_cap,
                            occ_ratio, cat, stand_prob, bunch_risk
                        ])
    print(f"Generated {filepath}")

# ---------------------------------------------------------
# 9. Multi-Week Multi-Route ETM Transaction Dataset
# ---------------------------------------------------------
def generate_etm_5weeks_sample_csv():
    filepath = os.path.join(DATA_DIR, "delhi_bus_etm_5weeks_transactions_sample.csv")
    
    start_date = datetime(2026, 10, 1)
    categories = [
        ("General Adult", 10, "ETM Conductor Cash"),
        ("General Adult", 15, "One Delhi QR App"),
        ("General Adult", 10, "Chartr App"),
        ("Daily Pink Pass (Female Commuter)", 0, "ETM Free Pink Ticket"),
        ("Daily Pink Pass (Female Commuter)", 0, "One Delhi QR App"),
        ("Student Concession", 5, "ETM Conductor Cash"),
        ("Senior Citizen Concession", 5, "ETM Conductor Cash"),
        ("NCMC Commuter", 10, "NCMC Smart Tap")
    ]
    
    ticket_counter = 50000001
    records = []
    
    random.seed(42)  # Deterministic seed for reproducible evaluation
    
    for day in range(35):
        curr_date = start_date + timedelta(days=day)
        date_str = curr_date.strftime("%Y-%m-%d")
        dow = curr_date.weekday()
        is_wknd = dow >= 5
        
        # Sample across routes
        for route_id, stops in ROUTES_CORRIDORS.items():
            direction = "UP" if route_id.endswith("UP") else "DOWN"
            bus_reg = f"DL1PC{random.randint(2000, 8999)}"
            cond_id = f"COND_{random.randint(100, 450)}"
            
            # Hours 7, 9, 13, 18, 20
            for hour in [7, 9, 13, 18, 20]:
                tx_count = 12 if hour in [9, 18] and not is_wknd else 5
                
                for _ in range(tx_count):
                    b_idx = random.randint(0, len(stops) - 3)
                    a_idx = random.randint(b_idx + 1, min(b_idx + 6, len(stops) - 1))
                    
                    b_stop_name, _, b_stage, _, _ = stops[b_idx]
                    a_stop_name, _, a_stage, _, _ = stops[a_idx]
                    b_stop_id = 1000 + b_idx
                    a_stop_id = 1000 + a_idx
                    
                    minute = random.randint(0, 59)
                    sec = random.randint(0, 59)
                    ts = f"{date_str} {hour:02d}:{minute:02d}:{sec:02d}"
                    
                    cat, base_fare, pay_mode = random.choice(categories)
                    fare = base_fare if cat != "Daily Pink Pass (Female Commuter)" else 0
                    
                    records.append([
                        ticket_counter, ts, date_str, hour, route_id, bus_reg, cond_id,
                        b_stop_id, b_stop_name, b_stage, a_stop_id, a_stop_name, a_stage,
                        direction, fare, cat, pay_mode
                    ])
                    ticket_counter += 1
                    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "ticket_id", "timestamp", "date", "hour", "route_id", "bus_registration",
            "conductor_id", "boarding_stop_id", "boarding_stop_name", "boarding_fare_stage",
            "alighting_stop_id", "alighting_stop_name", "alighting_fare_stage",
            "trip_direction", "fare_inr", "passenger_category", "payment_method"
        ])
        writer.writerows(records)
    print(f"Generated {filepath} ({len(records)} transactions)")

if __name__ == "__main__":
    generate_pink_pass_depot_csv()
    generate_expansion_factors_json()
    generate_stop_fare_stages_csv()
    generate_trip_fleet_roster_csv()
    generate_alighting_decay_matrix_csv()
    generate_dwell_time_calibration_csv()
    generate_environmental_context_csv()
    generate_corridor_ground_truth_csv()
    generate_etm_5weeks_sample_csv()
    print("All Problem 2 datasets generated successfully!")
