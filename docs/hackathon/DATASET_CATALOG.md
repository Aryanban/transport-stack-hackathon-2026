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

## 🔑 Accessing Full & Real-Time Datasets

1. **Sign up on DTS:** Visit [delhi.transportstack.in](https://delhi.transportstack.in) and register your team account.
2. **Request Dataset Subscriptions:**
   - For **Problem 1**: Subscribe to `DLM1` (Delhi Buses Static GTFS) and `DLM7` (Delhi Buses GTFS-RT Real-Time Feed).
   - For **Problem 2**: Subscribe to `DLM1` and the ETM / E-ticketing transaction dumps (requested via portal or email).
   - For **Problem 3, 4, 5**: Subscribe to `DLM2`, `DLM4`, `DLM8`, `DLM9`, `DLM13`.
3. **Open Transit Data Delhi (OTD):**
   - Live GTFS feeds and historical dumps are also accessible via [otd.delhi.gov.in](https://otd.delhi.gov.in).
