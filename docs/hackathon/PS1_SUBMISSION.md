# PS1 submission: Delhi bus times

## Proposal

A Delhi commuter asks how long a bus trip will take at the hour they leave. The timetable gives the same answer at 8:30 and at 23:00. We turn the live GPS of about 5,000 Delhi buses into a travel-time model for each stretch between two stops, at each hour, on weekdays and weekends. A journey planner uses that model for every minute after the first bus leaves its terminal.

## Run

Python 3.10 or newer, from the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn src.ps1.api:app --port 8020
```

Open http://127.0.0.1:8020/ for the planner on a 3D map of Delhi, and http://127.0.0.1:8020/accuracy for the accuracy report. On the map, **Live buses** shows every bus reporting now, pointed the way its GPS says it is moving, and **Speeds** colours each observed stretch by predicted bus speed at the chosen hour. Metro stations are drawn for reference only; plans are bus only. The repository ships a fitted `data/ps1/model.json`, so the planner runs offline. On first start it builds a network cache from the bundled GTFS in about 5 s. To turn on the live layer, put `DTS_API_KEY=<your key>` in `.env` (see `.env.example`). Without a key, the planner gives typical times for the hour.

## Rebuild from raw GPS

```bash
python scripts/log_gtfs_rt.py                 # poll GTFS-RT every 20 s into data/gps_log/
python -m src.ps1.matcher                     # GPS -> stop-to-stop travel times
python -m src.ps1.model                       # fit the model -> data/ps1/model.json
python -m src.ps1.validation                  # held-out report -> data/ps1/validation.json
python -m pytest tests/test_ps1.py
```

## Data

- **Timetable:** Delhi buses static GTFS v32 (DTC and DIMTS), in `data/delhi_buses_gtfs/`. Every route in the live feed is in it.
- **Bus GPS:** the GTFS-RT VehiclePositions feed from DTS, polled every 20 s by `scripts/log_gtfs_rt.py`.
- **GPS log format:** one gzip CSV per IST hour in `data/gps_log/` (columns `ts, vehicle_id, route_id, trip_id, lat, lon, speed_ms`). Each poll is written as its own gzip member and flushed to disk, so a crash loses at most that poll. When an hour ends, its file is sorted by bus and time, deduplicated and recompressed after a row-count check: about 13 bytes per position, about 115 MB per day. Read any file with `src.ps1.gpslog.read_file`.
- **Metro stations:** from DMRC's gate locations file, for map context only. Stations that the file stacks on one placeholder point are left out.
- **Crowding:** not shown. No real ETM ticket data is available yet, so the planner shows no crowd levels.

## API

| Path | Returns |
| --- | --- |
| `GET /journeys?from=&to=&depart=` | Up to 3 options. Each option lists every walk, the boarding stop, the route, the stop to get off, the change, total time, ride time now, ride time at the quiet hour and the timetable's ride time. `from` and `to` take a stop name, a stop_id or `lat,lon`. `depart` takes `YYYY-MM-DDTHH:MM` or `HH:MM` in IST. |
| `GET /journeys/day?from=&to=&date=` | The fastest door-to-door time for the same trip at each hour from 05:00 to 23:00 |
| `GET /stops?q=`, `GET /stops/all` | Stops matching a name; every served stop as GeoJSON |
| `GET /stops/{id}/departures?depart=` | The next buses at a stop: route, direction and arrival times |
| `GET /routes?q=`, `GET /routes/{id}` | Routes by bus number; a route's path, stops, first and last bus, and how often it runs |
| `GET /traffic/hours` | City-wide congestion factor by hour and day type, with observation counts |
| `GET /traffic/stretches?hour=&daytype=` | GeoJSON of observed stretches with predicted km/h |
| `GET /live/status`, `GET /live/vehicles?route=` | Live feed health, and current bus positions with a heading taken from each bus's own GPS movement |
| `GET /metro/network` | Metro station positions, for map context |
| `GET /validation` | The held-out accuracy report as JSON |
| `/accuracy` | The same report as a page: error figures, predicted against observed plots, error by hour, the Google comparison and data coverage |
| `/docs` | OpenAPI explorer |

## Technical note

**1. Linking GPS to routes.** Each GTFS route in the Delhi feed has exactly one stop pattern and one shape. Every GTFS-RT position carries its `route_id`. We project each stop onto the route shape to get its distance along the road. Each GPS point of a vehicle run (vehicle and `trip_id`) is then projected onto the same shape. The search runs only in a window ahead of the bus's last good position, so a looping route cannot snap a point to the wrong pass. We drop a point if it is more than 60 m off the shape, if it moves backwards by more than 40 m, or if it implies more than 90 km/h.

**2. Travel time on each stretch.** The bus reports roughly every 30 s. The time it passed each stop is interpolated between the two GPS points either side of the stop, if they are at most 150 s apart. Two consecutive passed stops give one observation of that stretch. Dwell at stops and waiting at signals are inside that observation on purpose, because the rider experiences them as part of the ride. A stretch is keyed by its stop pair, so several routes sharing a road all inform the same stretch.

**3. The model.** For a stretch of length L at hour h on day type d:

`time = prior(L) × R[d, h] × K[stretch] × K[stretch, h]`

- `prior(L) = a + b·L` is fitted on distance-bin medians across the city. The intercept absorbs average dwell.
- `R[d, h]` is the city-wide median ratio for that hour. It falls back to the hour pooled across day types, then to the nearest observed hour.
- The two `K` factors are geometric means of the residuals, shrunk toward 1 by `n / (n + w)` with `w = 5` and `w = 3`. A stretch with few buses stays close to the city pattern. A busy one follows its own data. A stretch never observed uses `prior × R`, and the planner says what share of each ride rests on observed stretches.

**4. Live and historical.** The API polls GTFS-RT every 20 s and matches the last 20 minutes of each vehicle with the same code. That gives two things:
- **A live factor per stretch:** the ratio of observed to historical time over the last 30 minutes, shrunk toward the city-wide live ratio. It applies fully to departures now and fades to nothing for departures an hour away.
- **A live arrival estimate** for a bus already on the route: the last stop it passed, plus the predicted remaining ride.

With no key or no fresh data, both switch off and the historical model stands.

**5. Planning.** The timetable is used for two things only: which routes exist, and when each trip leaves its first stop. The planner considers stops within 1 km of the origin and destination, at 4.5 km/h with 1.3× street detour. It searches direct trips and trips with one change, allowing a walk of up to 300 m and 3 minutes between buses. When the bus reaches your stop, how long the ride takes and when you arrive are all predicted by the model, stepping the hour forward along the ride.

## Validation

`python -m src.ps1.validation` holds out the last logged day. The ground truth is whole sub-trips of real buses, 5 to 30 consecutive stops, never used for fitting. It compares the model, the GTFS timetable and one flat city-wide speed on the same sub-trips. It reports mean error, percentage error, the share within ±20%, bias, and a peak versus off-peak split.

**Status, 16 November 2026:** logging started today, so the split is the last 30% of one evening: 52,914 stretch observations, 1,735 held-out sub-trips.

| Estimator | Mean error | % error | Within ±20% |
| --- | --- | --- | --- |
| Model | 1.27 min | 12.9% | 78.3% |
| GTFS timetable | 2.21 min | 23.2% | 52.9% |
| One flat city speed | 2.18 min | 23.3% | 55.2% |

These numbers cover one hour of one day. Rerun after 3 to 5 days of logging and replace this table.

**Google Maps.** `data/ps1/google_benchmark.csv` holds 11 origin–destination pairs at 08:30, 14:00 and 21:30 on Tuesday 24 November. That makes 33 trips. For each one, we read the duration of Google Maps' best transit option with only *Bus* selected, on 17 November 2026. We compare it with our fastest door-to-door option for the same place names and time.

| 33 trips against Google Maps | Value |
| --- | --- |
| Mean absolute difference | 12.1 min |
| Mean percentage difference | 17.9% |
| Within ±20% of Google | 66.7% |
| Mean signed difference (ours minus Google) | −7.6 min |

Google's bus times are themselves timetable-based estimates, not observed trips, so this is a comparison, not ground truth. Most of the gap comes from Dhaula Kuan to ITO, where Google's best bus option takes 92 to 121 min and ours 41 to 52 min. Google also places "ITO" and "Ashram" at its own points, which can differ from the stops we match. On many pairs Google gives the same time at 08:30 and at 21:30.

## Where it is least reliable

- **Hours and stretches with few buses.** Those cells fall back to the city pattern. The share of a ride on observed stretches is shown for every option.
- **The first bus.** Waiting time depends on the timetable's terminal departures, unless a live bus is already on its way.
- **Coverage.** The model covers only what the feed covered while we logged. Weekend and holiday patterns need their own days of data.
- **Transfers.** The planner allows at most one change.
