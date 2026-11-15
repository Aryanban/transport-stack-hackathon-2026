"""Build capacity-aware corridor profiles from the repository's generated PS2 data."""
import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[2]
TICKETS = ROOT / "data" / "etm_ticketing_data"
DEFAULT_PROFILES = Path(__file__).with_name("profiles.json")
SOURCE = "Generated ETM and app tickets · calibrated to sample benchmark"
CUT = "2026-10-29"


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def is_weekend(day):
    return int(date.fromisoformat(day).weekday() >= 5)


def tier(ratio):
    return "Seats available" if ratio <= 1 else "Standing room" if ratio <= 1.5 else "Heavily crowded"


def factor(config, route, hour):
    family = "trunk_arterial" if route.startswith(("761", "534")) else "radial_cbd"
    bands = config["route_type_profiles"][family]["time_bands"]
    if 17 <= hour <= 20:
        return bands["evening_peak_17_20"]["expansion_factor"]
    if 8 <= hour <= 11:
        return bands["morning_peak_08_11"]["expansion_factor"]
    if 12 <= hour <= 15:
        return bands["afternoon_offpeak_12_15"]["expansion_factor"]
    if 5 <= hour <= 7:
        return bands["early_morning_05_07"]["expansion_factor"]
    if hour >= 21 or hour < 5:
        return bands["night_21_24"]["expansion_factor"]
    return config["city_wide_summary"]["overall_aggregate_expansion_multiplier"]


def build(folder):
    routes = defaultdict(list)
    for row in rows(folder / "stop_to_fare_stage_mapping.csv"):
        routes[row["route_id"]].append(row)
    for stops in routes.values():
        stops.sort(key=lambda row: int(row["stop_sequence"]))
    index = {route: {normalize(stop["stop_name"]): i for i, stop in enumerate(stops)}
             for route, stops in routes.items()}
    roster, by_route = {}, defaultdict(list)
    for row in rows(folder / "trip_fleet_assignment_roster.csv"):
        capacity = int(row["seating_capacity"]), int(row["crush_capacity"])
        roster[row["route_id"], row["bus_registration"]] = capacity
        by_route[row["route_id"]].append(capacity)
    defaults = {route: tuple(round(median(column)) for column in zip(*capacities))
                for route, capacities in by_route.items()}
    expansion = json.loads((folder / "pass_holder_expansion_factors.json").read_text(encoding="utf-8"))
    days = defaultdict(list)
    runs, audit, channels, seen = defaultdict(list), Counter(), Counter(), set()
    for row in rows(folder / "delhi_bus_etm_5weeks_transactions_sample.csv"):
        audit["input_tickets"] += 1
        identity = row["ticket_id"]
        if identity in seen:
            audit["duplicate_tickets"] += 1
            continue
        seen.add(identity)
        route = row["route_id"]
        positions = index.get(route, {})
        board = positions.get(normalize(row["boarding_stop_name"]))
        alight = positions.get(normalize(row["alighting_stop_name"]))
        if board is not None and alight is None:
            # Resolve a fare-stage-only destination to its last valid stop.
            stage = row["alighting_fare_stage"]
            eligible = [i for i, stop in enumerate(routes[route])
                        if i > board and stop["fare_stage_id"] == stage]
            if eligible:
                alight = eligible[-1]
                audit["stage_only_destinations"] += 1
        if board is None or alight is None or alight <= board:
            audit["unmatched_or_reversed_tickets"] += 1
            continue
        key = (row["date"], route, int(row["hour"]), row["bus_registration"], row["conductor_id"])
        runs[key].append((board, alight, int(row["fare_inr"]) > 0))
        channels[row["payment_method"]] += 1
    for (day, route, hour, vehicle, _), tickets in runs.items():
        seats, crush = roster.get((route, vehicle), defaults[route])
        audit["fleet_roster_matches"] += int((route, vehicle) in roster)
        paid, recorded = Counter(), Counter()
        for board, alight, is_paid in tickets:
            recorded[board] += 1
            recorded[alight] -= 1
            if is_paid:
                paid[board] += 1
                paid[alight] -= 1
        load = paid_load = 0
        for i in range(len(routes[route]) - 1):
            load += recorded[i]
            paid_load += paid[i]
            # Expansion includes pass riders. Keep observed zero-fare tickets
            # once, and add only the residual implied by the paid-ticket model.
            expanded = max(load, paid_load * factor(expansion, route, hour))
            days[route, i, is_weekend(day), hour].append((day, expanded, seats, crush))
    reference = {}
    for row in rows(folder / "corridor_hourly_crowding_ground_truth.csv"):
        route = row["route_id"]
        i = index[route].get(normalize(row["from_stop_name"]))
        j = index[route].get(normalize(row["to_stop_name"]))
        if i is not None and j == i + 1:
            reference[route, i, int(row["is_weekend"]), int(row["hour"])] = float(row["mean_passenger_load"])
    scale_samples = defaultdict(list)
    for key, observations in days.items():
        training = [entry[1] for entry in observations if entry[0] < CUT]
        if training and mean(training) > 0 and key in reference:
            scale_samples[key[0]].append(reference[key] / mean(training))
    scales = {route: median(values) for route, values in scale_samples.items()}
    profiles, errors, reference_errors = [], [], []
    baseline_errors, band_hits = [], []
    spots = defaultdict(list)
    route_training = defaultdict(list)
    for (route, *_), observations in days.items():
        route_training[route].extend(load for day, load, _, _ in observations if day < CUT)
    for key, observations in sorted(days.items()):
        route, _, weekend, hour = key
        scale = scales.get(route, 1)
        training = [item[1] for item in observations if item[0] < CUT]
        holdout = [item[1] for item in observations if item[0] >= CUT]
        raw = mean(item[1] for item in observations)
        seats = mean(item[2] for item in observations)
        crush = mean(item[3] for item in observations)
        profiles.append({"key": key, "load": round(raw * scale, 3), "recorded_expanded": round(raw, 3),
                         "seats": round(seats, 2), "crush": round(crush, 2),
                         "days": len({item[0] for item in observations}), "runs": len(observations)})
        if training and holdout:
            pred, actual = mean(training) * scale, mean(holdout) * scale
            errors.append(abs(pred - actual))
            baseline_errors.append(abs(mean(route_training[route]) * scale - actual))
            band_hits.append(tier(pred / seats) == tier(actual / seats))
            spots[route, "weekend" if weekend else "weekday", "peak" if hour in (9, 18) else "off-peak"].append(actual)
        if training and key in reference:
            reference_errors.append(abs(mean(training) * scale - reference[key]))
    return {
        "source": SOURCE, "window": [min(key[0] for key in runs), max(key[0] for key in runs)],
        "audit": {**audit, "modeled_ticket_rows": sum(channels.values()), "run_proxies": len(runs),
                  "payment_methods": dict(channels), "sample_routes": sorted(routes)},
        "calibration_scale": {route: round(value, 3) for route, value in sorted(scales.items())},
        "validation": {"holdout_start": CUT, "scored_segment_hour_cells": len(errors),
                       "holdout_mae": round(mean(errors), 2), "route_baseline_mae": round(mean(baseline_errors), 2),
                       "holdout_band_agreement": round(mean(band_hits), 3),
                       "synthetic_reference_fit_cells": len(reference_errors),
                       "synthetic_reference_fit_mae": round(mean(reference_errors), 2),
                       "spot_checks": [{"route": r, "day_type": d, "period": p, "cells": len(values),
                                        "mean_load": round(mean(values), 2)}
                                       for (r, d, p), values in sorted(spots.items())]},
        "stops": {route: [stop["stop_name"] for stop in stops] for route, stops in routes.items()},
        "profiles": profiles,
    }


@dataclass
class SegmentProfiles:
    data: dict

    def __post_init__(self):
        self.source = self.data["source"]
        self.scores = {tuple(row["key"]): row for row in self.data["profiles"]}
        self.anchors = defaultdict(dict)
        for row in rows(Path(__file__).with_name("anchors.csv")):
            route = row["sample_route"]
            try:
                index = self.data["stops"][route].index(row["sample_stop"])
            except (KeyError, ValueError):
                continue
            self.anchors[row["gtfs_route"]][row["gtfs_stop"]] = (route, index)
        self.projections = {}

    def project(self, pattern):
        if pattern not in self.projections:
            route, _, stops = pattern
            anchors = self.anchors.get(route, {})
            matched = [(i, *anchors[stop]) for i, stop in enumerate(stops) if stop in anchors]
            segments = {}
            for (start, corridor, left), (end, next_corridor, right) in zip(matched, matched[1:]):
                if corridor == next_corridor and 0 < right - left <= 6:
                    for i in range(start, end):
                        segments[i] = corridor, range(left, right)
            self.projections[pattern] = segments
        return self.projections[pattern]

    def for_leg(self, leg, pattern):
        matched = self.project(pattern)
        midnight = leg.departure - timedelta(seconds=leg.trip.times[leg.start].departure)
        weighted = []
        total = 0
        for i in range(leg.start, leg.end):
            current, following = leg.trip.times[i:i + 2]
            stamp = midnight + timedelta(seconds=current.departure)
            duration = max(1, following.arrival - current.departure)
            total += duration
            if i not in matched:
                continue
            corridor, indexes = matched[i]
            cells = [self.scores.get((corridor, j, int(stamp.weekday() >= 5), stamp.hour)) for j in indexes]
            if not all(cell and cell["days"] >= 3 for cell in cells):
                continue
            weighted.append((duration, mean(cell["load"] / cell["seats"] for cell in cells),
                             mean(cell["load"] for cell in cells), min(cell["days"] for cell in cells)))
        covered = sum(row[0] for row in weighted)
        fraction = covered / total
        if fraction < .65:
            return {"level": "Unknown", "score": None, "confidence": None, "days": None,
                    "coverage": round(fraction, 2)}
        score = sum(duration * ratio for duration, ratio, _, _ in weighted) / covered
        load = sum(duration * load for duration, _, load, _ in weighted) / covered
        days = min(row[3] for row in weighted)
        return {"level": tier(score), "score": round(score, 4), "days": days,
                "confidence": "Sample corridor estimate", "coverage": round(fraction, 2),
                "modeledPassengers": round(load, 1), "busiestSegment": tier(max(row[1] for row in weighted))}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=TICKETS)
    parser.add_argument("--output", type=Path, default=DEFAULT_PROFILES)
    args = parser.parse_args()
    result = build(args.data)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("audit", "calibration_scale", "validation")}, indent=2))


if __name__ == "__main__":
    main()
