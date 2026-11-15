"""GTFS schedule loading and bounded stop-to-stop journey search."""
import csv
import io
import math
import sys
import zipfile
from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30), "IST")
DAY = 86400


def seconds(value):
    hours, minutes, secs = map(int, value.split(":"))
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= secs < 60:
        raise ValueError(f"Invalid GTFS time: {value}")
    return hours * 3600 + minutes * 60 + secs


def local_time(value):
    stamp = datetime.fromisoformat(value)
    return stamp.replace(tzinfo=IST) if stamp.tzinfo is None else stamp.astimezone(IST)


def gtfs_date(value):
    return datetime.strptime(value, "%Y%m%d").date()


@dataclass(frozen=True, slots=True)
class StopTime:
    stop: str
    arrival: int
    departure: int
    sequence: int
    pickup: bool = True
    dropoff: bool = True


@dataclass(frozen=True, slots=True)
class Trip:
    id: str
    route: str
    direction: str
    service: str
    times: tuple
    mode: str = "bus"

    @property
    def pattern(self):
        return self.route, self.direction, tuple(point.stop for point in self.times)


@dataclass(frozen=True, slots=True)
class Leg:
    trip: Trip
    service_date: date
    start: int
    end: int
    departure: datetime
    arrival: datetime
    walk_minutes: int = 0


class Feed:
    def __init__(self, stops, routes, trips, calendars, exceptions, *, demo=False):
        self.stops = stops
        self.routes = routes
        self.trips = trips
        self.calendars = calendars
        self.exceptions = exceptions
        self.demo = demo
        self.departures = defaultdict(list)
        self.patterns = set()
        self.trip_patterns = {}
        canonical_patterns = {}
        self.max_day_offset = 0
        self.interchanges = {}
        for trip in trips.values():
            pattern = trip.pattern
            pattern = canonical_patterns.setdefault(pattern, pattern)
            self.patterns.add(pattern)
            self.trip_patterns[trip.id] = pattern
            for i, point in enumerate(trip.times[:-1]):
                if point.pickup:
                    self.departures[point.stop].append((point.departure, trip.id, i))
            self.max_day_offset = max(self.max_day_offset, trip.times[-1].arrival // DAY)
        for rows in self.departures.values():
            rows.sort()

    def active(self, service, day):
        if self.demo:
            return True
        override = self.exceptions.get((service, day))
        if override is not None:
            return override
        calendar = self.calendars.get(service)
        return bool(calendar and calendar[0] <= day <= calendar[1] and calendar[2][day.weekday()])

    def boardings(self, stop, start, end):
        rows = self.departures.get(stop, ())
        first_day = start.date() - timedelta(days=self.max_day_offset)
        last_day = end.date()
        day = first_day
        while day <= last_day:
            midnight = datetime.combine(day, time.min, IST)
            lower = math.ceil((start - midnight).total_seconds())
            upper = int((end - midnight).total_seconds())
            i = bisect_left(rows, (lower,))
            while i < len(rows) and rows[i][0] <= upper:
                departure, trip_id, index = rows[i]
                trip = self.trips[trip_id]
                if self.active(trip.service, day):
                    yield trip, day, index, midnight, midnight + timedelta(seconds=departure)
                i += 1
            day += timedelta(days=1)

    @staticmethod
    def make_leg(trip, day, first, last, midnight, departure):
        return Leg(trip, day, first, last, departure,
                   midnight + timedelta(seconds=trip.times[last].arrival))

    def journeys(self, origin, destination, start, *, limit_hours=3, transfer_minutes=4):
        deadline = start + timedelta(hours=limit_hours)
        direct = []
        connections = defaultdict(list)
        for trip, day, first, midnight, departure in self.boardings(origin, start, deadline):
            for last in range(first + 1, len(trip.times)):
                point = trip.times[last]
                if not point.dropoff:
                    continue
                leg = self.make_leg(trip, day, first, last, midnight, departure)
                if leg.arrival > deadline:
                    break
                if point.stop == destination:
                    direct.append((leg,))
                    break
                if point.stop != origin:
                    if point.stop in self.departures:
                        connections[point.stop, 0].append(leg)
                    for transfer, walk in self.interchanges.get(point.stop, ()):
                        connections[transfer, walk].append(leg)

        options = list(direct)
        buffer = timedelta(minutes=transfer_minutes)
        # Index second legs once per transfer stop. This also preserves later,
        # less crowded departures on the same route.
        for (stop, walk), first_legs in connections.items():
            transfer_buffer = buffer + timedelta(minutes=walk)
            earliest = min(leg.arrival for leg in first_legs) + transfer_buffer
            second_legs = []
            for trip, day, first, midnight, departure in self.boardings(stop, earliest, deadline):
                for last in range(first + 1, len(trip.times)):
                    point = trip.times[last]
                    if point.stop == destination and point.dropoff:
                        leg = self.make_leg(trip, day, first, last, midnight, departure)
                        if leg.arrival <= deadline:
                            second_legs.append(leg)
                        break
            second_legs.sort(key=lambda leg: leg.departure)
            departures = [leg.departure for leg in second_legs]
            for first in first_legs:
                ready = first.arrival + transfer_buffer
                for i in range(bisect_left(departures, ready), len(second_legs)):
                    second = second_legs[i]
                    if self.trip_patterns[second.trip.id] != self.trip_patterns[first.trip.id]:
                        if walk:
                            second = Leg(second.trip, second.service_date, second.start, second.end,
                                         second.departure, second.arrival, walk)
                        if not walk or first.trip.mode != second.trip.mode:
                            options.append((first, second))
        return options


def load_feed(filename, *, mode="bus"):
    filename = Path(filename)
    if filename.is_dir():
        return _load(lambda name, required=False: _folder_rows(filename, name, required), mode)
    with zipfile.ZipFile(filename) as archive:
        members = {Path(name).name: name for name in archive.namelist() if not name.endswith("/")}
        return _load(lambda name, required=False: _rows(archive, members, name, required), mode)


def _load(read, mode):
    if any(read("frequencies.txt")):
        raise ValueError("Frequency-based GTFS trips need schedule expansion before import.")
    prefix = "metro:" if mode == "metro" else ""
    stops = {row["stop_id"]: {"id": row["stop_id"], "name": row["stop_name"],
                             "lat": float(row["stop_lat"]), "lon": float(row["stop_lon"])}
             for row in read("stops.txt", required=True)
             if row.get("location_type", "") in ("", "0") and row.get("stop_lat") and row.get("stop_lon")}
    routes = {}
    for row in read("routes.txt", required=True):
        route_type = row.get("route_type", "")
        name = row.get("route_short_name") or row.get("route_long_name") or row["route_id"]
        if mode == "metro":
            if route_type == "1":
                routes[row["route_id"]] = row.get("route_long_name") or name
        elif route_type == "3" or route_type.isdigit() and 700 <= int(route_type) <= 799:
            routes[row["route_id"]] = name
    metadata = {row["trip_id"]: row for row in read("trips.txt", required=True)
                if row["route_id"] in routes}
    trip_times = defaultdict(list)
    incomplete = set()
    for row in read("stop_times.txt", required=True):
        trip_id = row["trip_id"]
        if trip_id not in metadata:
            continue
        arrival, departure = row.get("arrival_time"), row.get("departure_time")
        if not arrival and not departure or row["stop_id"] not in stops:
            incomplete.add(trip_id)
            continue
        arrives = seconds(arrival or departure)
        leaves = arrives if not departure or arrival == departure else seconds(departure)
        trip_times[trip_id].append(StopTime(sys.intern(prefix + row["stop_id"]), arrives,
                                           leaves, int(row["stop_sequence"]),
                                           row.get("pickup_type", "") in ("", "0"),
                                           row.get("drop_off_type", "") in ("", "0")))
    trips = {}
    for trip_id, points in trip_times.items():
        if trip_id in incomplete or len(points) < 2:
            continue
        points.sort(key=lambda point: point.sequence)
        if any(p.arrival > p.departure for p in points) or any(
                a.departure > b.arrival or a.sequence == b.sequence
                for a, b in zip(points, points[1:])):
            continue
        row = metadata[trip_id]
        trips[trip_id] = Trip(prefix + trip_id, prefix + row["route_id"], row.get("direction_id", ""),
                              prefix + row["service_id"], tuple(points), mode)
    weekdays = "monday tuesday wednesday thursday friday saturday sunday".split()
    calendars = {prefix + row["service_id"]: (gtfs_date(row["start_date"]), gtfs_date(row["end_date"]),
                                      tuple(row[key] == "1" for key in weekdays))
                 for row in read("calendar.txt")}
    exceptions = {(prefix + row["service_id"], gtfs_date(row["date"])): row["exception_type"] == "1"
                  for row in read("calendar_dates.txt")}
    if not trips or not (calendars or exceptions):
        raise ValueError("No usable scheduled trips or service calendar found in the GTFS feed.")
    return Feed({prefix + key: {**value, "id": prefix + key} for key, value in stops.items()},
                {prefix + key: value for key, value in routes.items()},
                {trip.id: trip for trip in trips.values()}, calendars, exceptions)


def combine_feeds(bus, metro):
    """Link stops across modes only when the estimated walk is short."""
    from ..data_loader import haversine_distance_km

    combined = Feed(bus.stops | metro.stops, bus.routes | metro.routes, bus.trips | metro.trips,
                    bus.calendars | metro.calendars, bus.exceptions | metro.exceptions)
    rail_stops = {point.stop for trip in metro.trips.values() for point in trip.times}
    for rail in metro.stops.values():
        if rail["id"] not in rail_stops:
            continue
        nearby = []
        for stop in bus.stops.values():
            if abs(stop["lat"] - rail["lat"]) > .005 or abs(stop["lon"] - rail["lon"]) > .006:
                continue
            length = haversine_distance_km(rail["lat"], rail["lon"], stop["lat"], stop["lon"])
            if length <= .35:
                nearby.append((length, stop["id"]))
        for length, stop in sorted(nearby)[:4]:
            minutes = max(1, math.ceil(length * 1.25 / 4.5 * 60))
            combined.interchanges.setdefault(rail["id"], []).append((stop, minutes))
            combined.interchanges.setdefault(stop, []).append((rail["id"], minutes))
    return combined


def _folder_rows(folder, name, required):
    path = folder / name
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)
    elif required:
        raise ValueError(f"GTFS directory is missing {name}.")


def _rows(archive, members, name, required=False):
    if name not in members:
        if required:
            raise ValueError(f"GTFS ZIP is missing {name}.")
        return
    with archive.open(members[name]) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)
