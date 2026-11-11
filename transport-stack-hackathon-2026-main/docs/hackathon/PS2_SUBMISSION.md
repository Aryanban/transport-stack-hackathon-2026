# PS2 submission · Delhi Bus Planner

## Proposal

Let a Delhi bus rider see the earliest scheduled arrival and compare alternatives within an extra-time budget. The planner shows seats available, standing room, or heavy crowding by bus leg. It also shows the busiest modeled stretch and makes gaps in coverage visible. Operators can inspect sample-corridor estimates by stretch, direction, hour and day type.

## Run

From the repository root with Python 3.10 or newer:

```powershell
python -m pip install fastapi uvicorn
python -m uvicorn src.ps2.api:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010/. The first request loads the Delhi bus timetable and can take about 20 seconds. Subsequent searches reuse the index. The prior multi-problem app also mounts this planner at `/ps2/` when started using `src.api:app`.

## Rebuild and verify

```powershell
python -m src.ps2.model
python -m unittest discover -s tests -p test_ps2.py -v
```

The build command reads the repository's five-week ticket file, fare-stage stop mapping, pass-holder factors, fleet assignment roster and corridor benchmark. It writes `src/ps2/profiles.json` and prints the audit and validation metrics. The included output can run offline. The extra 102-only ticket extract is a separate sample with different topology and dates. It was excluded from fitting to avoid pooling incompatible run assumptions.

## Technical note

1. **Reconstruct sample loads.** Match boarding and planned alighting names to ordered positions on the same sample corridor. For a stage-only destination, use the last downstream stop in that stage. Deduplicate ticket IDs. The generator issues tickets in route, date and hour blocks for a vehicle and conductor. These blocks proxy runs. Passenger changes are applied at stops to calculate the load after each stop. The sample does not contain a confirmed GTFS trip ID.
2. **Account for passes and capacity.** Count each recorded transaction once, including zero-fare pink tickets. Take the larger of the recorded load and the paid load expanded using the route family and time band. Use a capacity from the fleet roster when the bus identifier matches. Zero sample vehicles matched this roster, so the included results use each corridor's median roster seating and crush capacities.
3. **Calibrate the sparse sample.** Fit one scale per sample corridor from the median ratio of synthetic benchmark load to nonzero expanded ticket load using training dates only. Scales are large, about 20–40×. They put the generated counts on the benchmark scale for demonstration and have no independently measured sampling-rate interpretation. The labels follow the supplied guide's seating ratio cutoffs of 1.0 and 1.5. An estimate can exceed rated capacity and should be interpreted as a saturation signal from the model.
4. **Join to the actual timetable.** The ticket IDs reuse unrelated GTFS stop IDs. The reviewed anchor file maps matching stops and ordered stretches. The sample label 502UP aligns to GTFS route 1995, displayed as 502DOWN, by geography and order. A bounded gap of up to six sample segments is projected to the GTFS stretch between its anchors and averaged. Other edges are left unknown. A leg needs at least 65% of its ride time covered and three contributing sample days per included cell.
5. **Plan trips.** Use GTFS service dates, ordered stops and scheduled arrival and departure times. Evaluate direct journeys and one same-stop transfer with four minutes to change, within a three-hour search window. For each leg, look up the projected segment using its own scheduled hour. Rank comfort using the ride-time-weighted passenger-to-seat ratio and require a meaningful improvement. If the fastest option has no estimate, label a covered alternative **Crowd estimate available**.

## Validation on the supplied files

The archive contains **generated ticket and reference data**, with 6,125 usable transactions over 35 days, 875 run proxies and five sample corridors. Train before 29 October 2026 and hold out 29 October–4 November. On 730 sample stretch/hour/day-type cells, the model's MAE was **17.22 modeled passengers** versus **25.41** for a route-only baseline. Crowd-band agreement was **57.7%**. Training-cell fit against the generated reference had an MAE of **15.22**. The held-out check tests repeatability of sample patterns and does not measure accuracy against observed onboard loads. The machine-readable report includes weekday/weekend and peak/off-peak summaries for each route. Final app profiles use all 35 sample days after evaluation.

The generator has observations at 07:00, 09:00, 13:00, 18:00 and 20:00. Missing hours stay unknown. Some stretches have sparse observations, approximate stop anchors or planned rather than observed alighting. Official historical transactions, confirmed trips, a verified fleet roster and independent counts are needed for claims about real onboard occupancy.

## API

| Path | Purpose |
| --- | --- |
| `/api/journeys` | Stop-to-stop options. Parameters are `origin`, `destination`, `departure` and `extra`. |
| `/api/crowding?route=502UP&hour=18&weekend=false` | Sample-corridor estimates by ordered stretch |
| `/api/validation` | Data audit, fit and holdout evaluation |
| `/docs` | OpenAPI explorer |

## Demo recording outline

1. Open the planner and show the preloaded Delhi Gate to Kashmere Gate City Bus Terminal search.
2. Open a result to show boarding and arrival times, busiest modeled stretch and coverage. Compare another departure time or a result without enough crowd data.
3. In **Crowding by corridor**, compare 502UP at 09:00 and 13:00 on a weekday, then switch to weekend. Point out the sample status and validation numbers.
4. Close with the reproducible model command and note that live locations are optional.

Optional live positions require `python -m pip install requests gtfs-realtime-bindings` and `$env:DTS_API_KEY = "<your-current-key>"` in the shell before starting Uvicorn. The PS2 overlay displays only fresh responses from the approved endpoint. Its schedule and crowd model remain historical.
