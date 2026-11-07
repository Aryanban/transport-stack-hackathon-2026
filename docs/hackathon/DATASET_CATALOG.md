# Delhi Transport Stack — Complete Dataset & Resource Catalog

This repository packages all official schemas, metadata documentation, instructions, and sample datasets from the **Delhi Transport Stack (DTS)** platform (`delhi.transportstack.in`) and **Open Transit Data Delhi (`otd.delhi.gov.in`)**.

---

## 📦 Dataset Inventory

| ID | Seq Code | Dataset Name | Mode | Type | API Available | Local Files Loaded in Repo |
| :--- | :--- | :--- | :--- | :--- | :---: | :--- |
| **1** | `DLM1` | **Delhi Buses: GTFS Static Data (v1-2)** | Bus | Core Transport | No | `data/delhi_buses_gtfs/` (Full production feed: 6,812 stops, 2,554 routes, 65,322 trips, 2.38M stop times, 765k shapes) |
| **2** | `DLM2` | **Delhi Metro: Static Data** | Metro | Core Transport | No | `data/delhi_metro_gtfs/` (`agency.txt`, `routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`, `shapes.txt`, `calendar.txt`) |
| **3** | `DLM3` | **Delhi Metro: Gate Locations** | Metro | Core Transport | No | `data/delhi_metro_gates/03_DMRC_Gate_Locations.xlsx` |
| **4** | `DLM4` | **Delhi Metro: Hourly Footfall Data** | Metro | Core Transport | No | `data/delhi_metro_footfall/04_DMRC_Hourly_Footfall_Sample.xlsx` |
| **5** | `DLM5` | **Rapid Rail: Static Data (NCRTC)** | Rapid Rail | Core Transport | No | `data/rapid_rail_ncrtc_gtfs/` (`routes.txt`, `stops.txt`, `trips.txt`, `stop_times.txt`) |
| **6** | `DLM6` | **Delhi Metro: Parking Locations** | Metro | Ancillary | No | `data/delhi_metro_parking/06_DMRC_Parking_Locations_Sample.xlsx`, `Station_Code_Parking_Index.xlsx` |
| **7** | `DLM7` | **Delhi Buses: GTFS-RT Feed** | Bus | Core Transport | **Yes** | `docs/metadata/7_Delhi_Buses_GTFS_Feed_Metadata.pdf`, `docs/metadata/7_Instructions_to_Access_Delhi_Buses_-_GTFS-RT_feed.pdf` |
| **8** | `DLM8` | **Delhi Metro: Monthly Passenger Count (OD)** | Metro | Core Transport | No | `data/delhi_metro_od_matrix/08_DMRC_Monthly_OD_Sample.csv` |
| **9** | `DLM9` | **Delhi Metro: Yearly Passenger Count (OD)** | Metro | Core Transport | No | `data/delhi_metro_od_matrix/09_DMRC_Yearly_OD_Sample.xls`, `Station_Code_Index.xlsx` |
| **10** | `DLM10`| **Delhi Streetlight: Static Data** | Road | Ancillary | No | `data/ancillary_images/10_street_image_1752046852741_streetlight.png` |
| **13** | `DLM13`| **Delhi Road: Static Data** | Road | Core Transport | No | `data/delhi_road_network/Data_Layer_04_Road.xlsb` (Road dimensions, widths >6m for feeder buses) |
| **14** | `DLM14`| **Delhi Shared Mobility: Static Data** | Shared | Core Transport | No | `data/delhi_shared_mobility_gtfs/` (Full shared mobility GTFS routes, schedules, stops, frequencies) |
| **15** | `DLM15`| **Delhi Accessibility: Static Data** | Metro | Core Transport | No | Accessibility friendly lifts, ramps, gates, parking |
| **16** | `DLM16`| **Delhi Shop: Static Data** | Road | Ancillary | No | `data/ancillary_images/16_shop_image_1751974398407_shop.jfif` |
| **17** | `DLM17`| **Delhi Subway and Overpass: Static Data** | Road | Core Transport | No | `data/ancillary_images/17_subway_image_1751974455881_subway.png` |

---

## 🎯 Problem 2 Dedicated Data Ecosystem (`data/etm_ticketing_data/`)

See the in-depth [Problem 2 Data Guide](file:///Users/aryanbansal/Documents/antigravity/transport-stack-hackathon-2026/docs/hackathon/PROBLEM_2_DATA_GUIDE.md) for schemas, formulas, and operational background.

| Dataset File | Format | Records / Size | Description |
| :--- | :--- | :--- | :--- |
| `delhi_bus_etm_5weeks_transactions_sample.csv` | CSV | 20,455 rows / 1.0 MB | 35-day (5 weeks) multi-corridor ETM transaction dump with boarding/alighting stops, fare stages, payment modes. |
| `delhi_bus_etm_transactions_sample.csv` | CSV | 9,648 rows / 1.6 MB | High-density corridor sample for Route 102 (Rohini to Old Delhi Railway Station). |
| `pink_pass_ridership_by_depot.csv` | CSV | 42 depots / 3.5 KB | Official depot-level female ridership shares (32.8% to 43.6%), electric vs CNG fleet assignments. |
| `pass_holder_expansion_factors.json` | JSON | 5.3 KB | Expansion multipliers ($K_{\text{expansion}}$) by route typology (Trunk, Radial, Feeder) and time band. |
| `stop_to_fare_stage_mapping.csv` | CSV | 85 stops / 6.6 KB | Sequenced fare stage mapping (Stages 1-6), distances, stage boundaries, and metro interchange lines. |
| `trip_fleet_assignment_roster.csv` | CSV | 200 trips / 25 KB | GTFS `trip_id` mapping to vehicle models (12m AC, 12m Non-AC, 9m Feeder) and crush capacities (40, 65, 70). |
| `passenger_alighting_decay_matrix.csv` | CSV | 13 slabs / 983 B | Conditional alighting probability matrix modeling distance decay and metro hub attractors. |
| `dwell_time_crowding_calibration.csv` | CSV | 15 scenarios / 1.1 KB | Stop dwell time (seconds) calibrated against boarding passenger volumes and on-board crowd level. |
| `delhi_daily_environmental_context.csv` | CSV | 35 days / 2.9 KB | 35-day timeline: weather, rain, holidays (Diwali, Dussehra), AQI index, GRAP Stages, ridership scaling. |
| `corridor_hourly_crowding_ground_truth.csv` | CSV | 2,754 rows / 244 KB | Hourly segment loads, occupancy ratios, standing probabilities, and crowd classifications. |
| `fare_stage_matrix.csv` | CSV | 5 slabs / 226 B | DTC official fare distance slabs and pricing for Non-AC, AC, and Pink Tickets. |
| `bus_fleet_specifications.json` | JSON | 877 B | Physical vehicle dimensions, door counts, floor heights, and rated crush thresholds. |

---

## 🔑 Accessing Full & Real-Time Datasets

1. **Sign up on DTS:** Visit [delhi.transportstack.in](https://delhi.transportstack.in) and register your team account.
2. **Request Dataset Subscriptions:**
   - For **Problem 1**: Subscribe to `DLM1` (Delhi Buses Static GTFS) and `DLM7` (Delhi Buses GTFS-RT Real-Time Feed).
   - For **Problem 2**: Subscribe to `DLM1` and the ETM / E-ticketing transaction dumps (requested via portal or email).
   - For **Problem 3, 4, 5**: Subscribe to `DLM2`, `DLM4`, `DLM8`, `DLM9`, `DLM13`.
3. **Open Transit Data Delhi (OTD):**
   - Live GTFS feeds and historical dumps are also accessible via [otd.delhi.gov.in](https://otd.delhi.gov.in).
