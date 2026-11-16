# Delhi bus times — Transport Stack Hackathon 2026

A Delhi bus journey planner timed by a traffic model learned from real bus GPS, not by the timetable.
Our submission for **Problem 1: real-time bus traffic model and journey planner**.

[![Transport Stack Hackathon](https://img.shields.io/badge/WhereUElevate-Transport%20Stack%20Hackathon%202026-blue)](https://whereuelevate.com/drills/transport-stack-hackathon-2026?w_ref=J66P10)

## Run it

Python 3.10 or newer.

```bash
python -m pip install -r requirements.txt
python -m uvicorn src.ps1.api:app --port 8020
```

Open http://127.0.0.1:8020/ for the planner. For live buses, put your Delhi Transport Stack key in a
`.env` file as `DTS_API_KEY=...` (see `.env.example`). Without a key the planner still works; it just
shows no live buses.

## What it does

- **Journey options** between any two stops or `lat,lon` points: direct buses and one change, with
  step-by-step directions (walk to which stop, bus number and direction, when it is due, stops to ride,
  where to change and get off), an estimated fare, and the route drawn on a 3D map.
- **Travel times from GPS.** Each stretch between stops has a learned speed by hour and day type, adjusted
  live from the GTFS-RT feed. Held-out error is 1.27 min per sub-trip against 2.21 min for the timetable.
- **Live buses** on the map, next buses at any stop, look-up by bus number, and the same trip's time at
  every hour of the day.
- **Accuracy page** at `/accuracy` with the full validation report.

Crowding is not shown: no real ETM ticket data is available yet.

## API

Interactive docs at `/docs`. Main endpoints:

| Endpoint | What it returns |
| --- | --- |
| `GET /journeys?from=&to=&depart=` | Up to three journey options with legs, times, fares and directions |
| `GET /journeys/day?from=&to=&depart=` | Door-to-door time for the same trip at each hour |
| `GET /stops?q=` | Stops matching a name |
| `GET /stops/all` | Every served stop as GeoJSON |
| `GET /stops/{id}/departures` | Next buses at a stop |
| `GET /routes?q=` and `GET /routes/{id}` | Routes by number; a route's path, stops, first and last bus, frequency |
| `GET /traffic/hours`, `GET /traffic/stretches` | City-wide and per-stretch predicted speeds |
| `GET /live/status`, `GET /live/vehicles` | Live feed status and bus positions |
| `GET /validation` | Held-out accuracy report |

## Repository

```
src/ps1/            planner, travel-time model, GPS matcher, live layer, API and web app
src/gtfs_rt_client.py   live GTFS-RT client (live data only, never simulated)
scripts/log_gtfs_rt.py  logs the live feed to data/gps_log/ (hourly gzip CSV)
scripts/download_dts_data.py  downloads the DTS portal datasets
data/delhi_buses_gtfs/  official static GTFS (stop_times kept gzipped)
data/ps1/           fitted model, validation report, Google benchmark template
docs/hackathon/     problem statements and the PS1 submission note
```

The [PS1 submission note](docs/hackathon/PS1_SUBMISSION.md) covers the method, how to rebuild from raw
GPS, and validation.

## Tests

```bash
PYTHONPATH=. python -m pytest tests/ -q
```
