# PS1 submission: Delhi bus times

## Proposal

A Delhi commuter asks how long a bus trip will take at the hour they leave. The timetable gives the same answer at 8:30 and at 23:00. We trained a travel-time model on a month of GPS from about 6,000 Delhi buses: 31 days of the organisers' October 2026 archive plus our own live log, cleaned and matched into 39.1 million timed stretches between stops. The model gives the time for each stretch, at each hour, on weekdays and weekends. A journey planner uses it for every minute after the first bus leaves its terminal, and the live feed adjusts trips that leave now. Tested on 25 to 31 October, a week it never saw, it has 40% less error than the timetable.

## Run

Python 3.10 or newer, from the repository root:

```bash
python -m pip install -r requirements.txt
python -m uvicorn src.ps1.api:app --port 8020
```

Open http://127.0.0.1:8020/ for the planner on a 3D map of Delhi, and http://127.0.0.1:8020/accuracy for the accuracy report. On the map, **Live buses** shows every bus reporting now, pointed the way its GPS says it is moving, and **Speeds** colours each observed stretch by predicted bus speed at the chosen hour. Metro stations are drawn for reference only; plans are bus only. The repository ships a fitted `data/ps1/model.json`, so the planner runs offline. On first start it builds a network cache from the bundled GTFS in about 5 s. To turn on the live layer, put `DTS_API_KEY=<your key>` in `.env` (see `.env.example`). Without a key, the planner gives typical times for the hour.

## Rebuild from raw GPS

Download `delhi-dtc-bus-gtfs-rt-2026-10.7z` (16.1 GB) from https://delhi.transportstack.in/hackathon/ into `data/raw/` and check it against `SHA256SUMS`. It needs 7-Zip (`7zz`), about 20 GB of free disk and 16 GB of RAM; the whole rebuild takes about 3 hours on a laptop.

```bash
python -m src.ps1.october                     # archive -> per-day stretch timings in data/raw/obs/
python scripts/log_gtfs_rt.py                 # optional: poll GTFS-RT every 20 s into data/gps_log/
python -m src.ps1.matcher                     # optional: live log -> stretch timings
python -m src.ps1.model                       # fit the model -> data/ps1/model.json
python -m src.ps1.validation                  # held-out report -> data/ps1/validation.json
python -m pytest tests/test_ps1.py
```

## Data

- **Timetable:** Delhi buses static GTFS v32 (DTC and DIMTS), in `data/delhi_buses_gtfs/`. Every route in the live feed is in it.
- **Historical bus GPS (main training data):** the organisers' October 2026 archive, DTC buses, 1 to 31 October, one SQLite database per day (124 GB unpacked; 15 October alone has 29.3 million raw positions). `src/ps1/october.py` unpacks one day at a time, converts the float `route_id` to the GTFS id, keeps at most one point per bus every 15 s (420+ million positions over the month), splits a bus's trip at gaps over 10 minutes, matches it with the same code as the live log, and deletes the unpacked day. Result: 38.6 million stretch timings.
- **Live bus GPS:** the GTFS-RT VehiclePositions feed from DTS, polled every 20 s by `scripts/log_gtfs_rt.py`. It adds cluster (DIMTS) buses, which the archive lacks: 565,241 stretch timings from 16 and 17 November 2026. It also feeds the live layer.
- **GPS log format:** one gzip CSV per IST hour in `data/gps_log/` (columns `ts, vehicle_id, route_id, trip_id, lat, lon, speed_ms`). Each poll is written as its own gzip member and flushed to disk, so a crash loses at most that poll. When an hour ends, its file is sorted by bus and time, deduplicated and recompressed after a row-count check: about 13 bytes per position, about 115 MB per day. Read any file with `src.ps1.gpslog.read_file`.
- **Metro stations:** from DMRC's gate locations file, for map context only. Stations that the file stacks on one placeholder point are left out.
- **Crowding:** not shown. October ticket data has just been published and is not built in yet, so the planner shows no crowd levels.

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

**2. Travel time on each stretch.** Positions are 15 to 30 s apart after thinning. The time it passed each stop is interpolated between the two GPS points either side of the stop, if they are at most 150 s apart. Two consecutive passed stops give one observation of that stretch. Dwell at stops and waiting at signals are inside that observation on purpose, because the rider experiences them as part of the ride. A stretch is keyed by its stop pair, so several routes sharing a road all inform the same stretch.

**3. The model.** For a stretch of length L at hour h on day type d:

`time = prior(L) × R[d, h] × K[stretch] × K[stretch, h]`

- `prior(L) = a + b·L` is fitted on distance-bin medians across the city. The intercept absorbs average dwell.
- `R[d, h]` is the city-wide median ratio for that hour and day type. With a month of data every one of the 48 cells has its own value: for example 0.62 at 2 am and 1.28 at 6 pm on weekdays, 1.21 at 6 pm on weekends. (Code falls back to the hour pooled across day types, then to the nearest observed hour, if a cell has fewer than 30 observations.)
- The two `K` factors are geometric means of the residuals, shrunk toward 1 by `n / (n + w)` with `w = 5` and `w = 3`. A stretch with few buses stays close to the city pattern. A busy one follows its own data. A stretch never observed uses `prior × R`, and the planner says what share of each ride rests on observed stretches. The fitted model has 13,525 stretch factors and 205,974 stretch-and-hour factors, 6.5 MB of JSON. Fitting on 39.1 million observations takes about a minute.

**4. Live and historical.** The API polls GTFS-RT every 20 s and matches the last 20 minutes of each vehicle with the same code. That gives two things:
- **A live factor per stretch:** the ratio of observed to historical time over the last 30 minutes, shrunk toward the city-wide live ratio. It applies fully to departures now and fades to nothing for departures an hour away.
- **A live arrival estimate** for a bus already on the route: the last stop it passed, plus the predicted remaining ride.

With no key or no fresh data, both switch off and the historical model stands.

**5. Planning.** The timetable is used for two things only: which routes exist, and when each trip leaves its first stop. The planner considers stops within 1 km of the origin and destination, at 4.5 km/h with 1.3× street detour. It searches direct trips and trips with one change, allowing a walk of up to 300 m and 3 minutes between buses. When the bus reaches your stop, how long the ride takes and when you arrive are all predicted by the model, stepping the hour forward along the ride.

## Validation

`python -m src.ps1.validation` holds out the last 7 days of the October archive, 25 to 31 October, and fits a separate model on everything else (30.5 million observations). The ground truth is whole sub-trips of real buses in the held-out week, 5 to 30 consecutive stops; 50,000 are sampled at random. It compares the model, the GTFS timetable and one flat city-wide speed on the same sub-trips, and reports mean and median error, percentage error, the share within ±20%, bias, a peak versus off-peak split and the error at each hour. The model the app ships is then fitted on all the data.

**Status, 18 November 2026:** fitted on 39.1 million stretch observations from 6,689 buses on 2,327 routes; 13,199 of 13,525 stretches have 3 or more.

| 50,000 sub-trips, 25 to 31 October | Mean error | Median error | % error | Within ±20% |
| --- | --- | --- | --- | --- |
| Model | 3.45 min | 1.57 min | 15.1% | 73.4% |
| GTFS timetable | 5.72 min | 3.51 min | 29.1% | 41.9% |
| One flat city speed | 5.88 min | 3.83 min | 32.0% | 39.5% |

The model beats the timetable at all 24 hours. Peak (8 to 10 am and 5 to 8 pm): 3.82 against 6.04 min. Off-peak: 3.16 against 5.48 min. Its error is largest at 6 pm (5.50 against 9.31 min) and smallest early in the morning (1.51 against 6.43 min at 5 am). Its mean bias is −2.27 min: it predicts the typical time, and a few very slow trips raise the average.

**Google Maps.** `data/ps1/google_benchmark.csv` holds 11 origin–destination pairs at 08:30, 14:00 and 21:30 on Tuesday 24 November. That makes 33 trips. For each one, we read the duration of Google Maps' best transit option with only *Bus* selected, on 17 November 2026. We compare it with our fastest door-to-door option for the same place names and time.

| 33 trips against Google Maps | Value |
| --- | --- |
| Mean absolute difference | 13.5 min |
| Mean percentage difference | 21.2% |
| Within ±20% of Google | 60.6% |
| Mean signed difference (ours minus Google) | −6.6 min |

Google's bus times are themselves timetable-based estimates, not observed trips, so this is a comparison, not ground truth. Most of the gap comes from Dhaula Kuan to ITO, where Google's best bus option takes 92 to 121 min and ours 38 to 62 min. Without that pair, 30 trips: 66.7% within ±20%, 9.4 min mean difference. Google also places "ITO" and "Ashram" at its own points, which can differ from the stops we match. On many pairs Google gives the same time at 08:30 and at 21:30.

## Where it is least reliable

- **Stretches with few buses.** Those fall back toward the city pattern. The share of a ride on observed stretches is shown for every option.
- **Cluster buses.** The archive is DTC only, so cluster routes rest on 2 days of our own live log.
- **The first bus.** Waiting time depends on the timetable's terminal departures, unless a live bus is already on its way.
- **Holidays, rain and events.** October gives weekdays and weekends, but there is no holiday or weather factor yet.
- **Typical, not worst case.** The estimate is the typical time; the slowest trips on a bad day take longer.
- **Transfers.** The planner allows at most one change.
