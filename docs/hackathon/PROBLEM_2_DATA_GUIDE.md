# Problem 2: Crowdedness-Aware Journey Planner — Complete Data Guide & Specifications

> **Target Challenge:** Problem 2 (Phase 1), Transport Stack Hackathon 2026  
> **Core Objective:** Estimate Delhi bus crowdedness by route, stretch, and time-of-day using 4–5 weeks of ETM & e-ticketing transaction data, and integrate capacity-aware comfort metrics into a multi-modal transit journey planner.

---

## 🧭 1. Overview & Data Philosophy

In Delhi transit, a commuter often chooses a slightly slower route over a crush-loaded bus where boarding is difficult, standing is exhausting, and personal space is minimal. Problem 2 challenges teams to turn digital ticketing records into reliable on-board load and crowdedness estimates.

Solving Problem 2 in Delhi requires modeling five unique operational realities:
1. **Fare Stage Ticketing:** Conductors punch tickets by *Fare Stages* (groups of stops corresponding to ₹5, ₹10, ₹15, ₹25 distance bands), rather than individual stop names.
2. **The Pink Pass Phenomenon:** Under the Government of NCT of Delhi's scheme, women travel free by receiving daily zero-fare Pink Tickets. This represents **$33\%\text{ to }42\%$** of daily bus ridership. Any algorithm failing to account for pink tickets and unrecorded passes will underestimate crowding by more than a third.
3. **Vehicle Capacity Tiers:** Delhi operates diverse fleet sizes: 12m Low-Floor Electric/AC (70 capacity), 12m Standard-Floor CNG (65 capacity), and 9m Electric Midi Feeders (40 capacity). A load of 45 passengers is comfortable on a 12m bus but over-crush capacity on a 9m feeder!
4. **Alighting Uncertainty:** ETM tickets record the destination fare stage or terminal, but passengers frequently alight early at intermediate metro hubs or minor stops.
5. **Dwell Time & Bus Bunching:** Heavily crowded buses spend 60–120 seconds boarding passengers per stop, compounding headway delays and causing subsequent buses to experience erratic crowding.

---

## 📁 2. Problem 2 Dataset Directory Layout

All Problem 2 datasets are stored in `data/etm_ticketing_data/` and integrate seamlessly with `data/delhi_buses_gtfs/`:

```
data/etm_ticketing_data/
├── delhi_bus_etm_5weeks_transactions_sample.csv   # 20,455 transactions spanning 35 days (5 weeks)
├── delhi_bus_etm_transactions_sample.csv          # High-density route 102 single-corridor sample (9,648 rows)
├── pink_pass_ridership_by_depot.csv               # 42 DTC/DIMTS depots with official pink pass & fleet shares
├── pass_holder_expansion_factors.json             # Mathematical multipliers by route type & time band
├── stop_to_fare_stage_mapping.csv                 # Detailed stop sequence to fare stage index (Routes 502, 761, 534, etc.)
├── trip_fleet_assignment_roster.csv               # GTFS trip_id to vehicle model, capacity, and depot mapping
├── passenger_alighting_decay_matrix.csv           # Empirical conditional probability of alighting by stage delta
├── dwell_time_crowding_calibration.csv            # Stop dwell time (seconds) vs boarding volume & crowding level
├── delhi_daily_environmental_context.csv          # 35-day daily diary: holidays, weather, AQI, and GRAP stages
├── corridor_hourly_crowding_ground_truth.csv      # 5-week hourly segment load benchmarks for model validation
├── fare_stage_matrix.csv                          # Distance bands & fare slabs (Non-AC, AC, Pink Pass)
└── bus_fleet_specifications.json                  # Physical dimensions, door counts, and floor heights
```

---

## 📊 3. Detailed Dataset Specifications

### 3.1 5-Week ETM Transactions (`delhi_bus_etm_5weeks_transactions_sample.csv`)
Simulates 35 consecutive days (October 1 to November 4, 2026) across Delhi's major corridors (502, 761, 534, 102, 449).

| Column | Data Type | Description |
| :--- | :--- | :--- |
| `ticket_id` | Integer | Unique identifier for the ticketing event (e.g. `70000001`). |
| `timestamp` | Datetime | Exact timestamp of ticket issuance (`YYYY-MM-DD HH:MM:SS`). |
| `date` | Date | `YYYY-MM-DD` covering all 35 days. |
| `hour` | Integer | Hour of day (0 to 23). |
| `route_id` | String | GTFS Route Identifier (e.g. `502UP`, `761DOWN`). |
| `bus_registration` | String | Vehicle registration number (e.g. `DL1PC5436`). |
| `conductor_id` | String | Handheld ETM operator code (e.g. `COND_214`). |
| `boarding_stop_id` | Integer | GTFS Stop ID where passenger boarded. |
| `boarding_stop_name` | String | Stop name at boarding point. |
| `boarding_fare_stage`| String | Fare stage name (e.g. `Stage 1`, `Stage 2`). |
| `alighting_stop_id` | Integer | Designated alighting stop ID. |
| `alighting_stop_name` | String | Designated alighting stop name. |
| `alighting_fare_stage`| String | Target alighting fare stage. |
| `trip_direction` | String | `UP` or `DOWN`. |
| `fare_inr` | Integer | Fare charged (₹0 for Pink Pass, ₹5, ₹10, ₹15, ₹20, ₹25). |
| `passenger_category`| String | `General Adult`, `Daily Pink Pass (Female Commuter)`, `Student Concession`, `Senior Citizen Concession`. |
| `payment_method` | String | `ETM Conductor Cash`, `ETM Free Pink Ticket`, `One Delhi QR App`, `Chartr App`, `NCMC Smart Tap`. |

### 3.2 Depot-Level Pink Pass & Fleet Distribution (`pink_pass_ridership_by_depot.csv`)
Covers **42 bus depots** across Delhi's North, South, East, West, Central, and North-East regions.

- **Ridership Split:** Demonstrates how female commuter share varies by locality:
  - Institutional/Educational corridors (BBM Depot, Nand Nagri): **$41.5\% - 43.6\%$** pink pass share.
  - Industrial/Commercial zones (Okhla, Mayapuri): **$32.8\% - 34.2\%$** pink pass share.
- **Fleet Modernization:** Details the rollout of pure electric zero-emission buses (e.g., Rohini Sector 37 and Tehkhand depots are 100% electric).

### 3.3 Pass-Holder Expansion Engine (`pass_holder_expansion_factors.json`)
Provides mathematical factors to expand ticketed transactions to true passenger load:

$$\text{Estimated Load}(t) = \text{Revenue ETM Tickets}(t) \times K_{\text{expansion}}(\text{route\_type}, \text{time\_band})$$

Where $K_{\text{expansion}}$ accounts for:
1. Pink Pass commuters ($33\% - 40\%$).
2. Monthly student passes and senior concession cards ($6\% - 9\%$).
3. Rush-hour unpunched passengers during crush loads ($5\% - 9\%$).

### 3.4 Stop to Fare Stage Mapping (`stop_to_fare_stage_mapping.csv`)
Unlike open-loop GPS, Delhi bus conductors punch fares by stage boundaries:
- **Stage 1:** $0.0 - 4.0\text{ km}$ (₹5 Non-AC / ₹10 AC)
- **Stage 2:** $4.1 - 8.0\text{ km}$ (₹10 Non-AC / ₹15 AC)
- **Stage 3:** $8.1 - 12.0\text{ km}$ (₹10 Non-AC / ₹20 AC)
- **Stage 4:** $12.1 - 16.0\text{ km}$ (₹15 Non-AC / ₹25 AC)
- **Stage 5 & 6:** $>16.0\text{ km}$ (₹15 Non-AC / ₹25 AC)

This dataset maps every stop to cumulative distance, fare stage index, stage boundary status, and metro interchange availability.

### 3.5 Trip Fleet Assignment Roster (`trip_fleet_assignment_roster.csv`)
Maps individual GTFS `trip_id`s to vehicle models and exact capacities:
- **12m Low-Floor AC (Electric/CNG):** 35 Seats, 35 Standing, 70 Crush Capacity.
- **12m Standard-Floor Non-AC (CNG):** 37 Seats, 28 Standing, 65 Crush Capacity.
- **9m Electric Midi Feeder:** 24 Seats, 16 Standing, 40 Crush Capacity.

### 3.6 Passenger Alighting Decay Matrix (`passenger_alighting_decay_matrix.csv`)
Solves destination ambiguity by providing empirical conditional drop-off probabilities:
$$P(\text{alight at stop } s \mid \text{destination stage } S)$$
Major metro interchange attractors (Rajiv Chowk, Kashmere Gate, AIIMS, Anand Vihar) capture up to $45\% - 55\%$ of intermediate drop-offs before the stage limit.

### 3.7 Dwell Time Crowding Calibration (`dwell_time_crowding_calibration.csv`)
Relates passenger boarding and alighting volume to stop dwell delays in seconds. Under crush loads ($>25$ passengers boarding), dwell time surges from 14s to 95–130s, causing bus bunching.

### 3.8 Environmental Context Diary (`delhi_daily_environmental_context.csv`)
Captures real external drivers across the 35 days:
- **Public Holidays:** Gandhi Jayanti (Oct 2), Dussehra (Oct 20), Valmiki Jayanti (Oct 25), Diwali (Nov 1), Govardhan Puja (Nov 2).
- **Rain Events:** Monsoon showers causing immediate +8% spikes in bus ridership.
- **AQI & GRAP Restrictions:** Severe post-monsoon smog in late October/early November triggers GRAP Stage III/IV (restrictions on private older vehicles), inducing a **+18% surge** in public bus demand.

### 3.9 Corridor Hourly Crowding Ground Truth (`corridor_hourly_crowding_ground_truth.csv`)
A reference benchmark of mean loads, 95th-percentile loads, occupancy ratios, standing probabilities, and crowding categories:
- **Seats Available:** Occupancy ratio $\le 1.0$ (mean load $\le 35$).
- **Standing Room:** Occupancy ratio $1.0 < \text{Ratio} \le 1.5$ (mean load $36 - 52$).
- **Heavily Crowded:** Occupancy ratio $> 1.5$ (mean load $> 52$, approaching 70 crush limit).

---

## 🛠️ 4. How to Scale Dataset Generation

A dedicated CLI script is included to generate extended transaction datasets of arbitrary size:

```bash
# Generate 35 days (default: ~20,000 transactions)
python scripts/generate_etm_5weeks_data.py --days 35

# Generate 60 days to a custom file
python scripts/generate_etm_5weeks_data.py --days 60 --output data/etm_ticketing_data/etm_60days.csv

# Re-run full Problem 2 dataset pipeline
python scripts/build_problem_2_datasets.py
```
