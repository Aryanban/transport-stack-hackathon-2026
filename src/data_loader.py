"""
Delhi Transport Stack - Data Loader & Spatial Indexer
Parses static GTFS (Bus & Metro), DMRC OD Matrix, Gate locations, and Footfall.
"""

from __future__ import annotations
import csv
import json
import math
import os
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

@dataclass
class Stop:
    stop_id: str
    stop_name: str
    lat: float
    lon: float
    mode: str = "bus"  # "bus" or "metro"
    stop_code: Optional[str] = None

@dataclass
class Route:
    route_id: str
    short_name: str
    long_name: str
    route_type: int
    mode: str = "bus"
    description: str = ""

@dataclass
class Trip:
    trip_id: str
    route_id: str
    service_id: str
    direction_id: int = 0
    shape_id: Optional[str] = None

@dataclass
class StopTime:
    trip_id: str
    arrival_time: str
    departure_time: str
    stop_id: str
    stop_sequence: int
    arrival_seconds: int = 0

def time_to_seconds(t_str: str) -> int:
    """Converts HH:MM:SS string to seconds from midnight."""
    parts = t_str.strip().split(":")
    if len(parts) >= 2:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2]) if len(parts) > 2 else 0
        return h * 3600 + m * 60 + s
    return 0

def seconds_to_time(sec: int) -> str:
    """Converts seconds from midnight to HH:MM:SS string."""
    sec = sec % 86400
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class TransitNetwork:
    """Encapsulates loaded Delhi transit network (Bus, Metro, OD matrix)."""

    def __init__(self):
        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: Dict[str, Trip] = {}
        self.stop_times: List[StopTime] = []
        self.stop_to_routes: Dict[str, set[str]] = {}
        self.trip_to_stoptimes: Dict[str, List[StopTime]] = {}
        self.route_to_trips: Dict[str, List[Trip]] = {}
        self.od_matrix: Dict[str, Dict[str, int]] = {}
        self.station_code_names: Dict[str, str] = {}

    def add_stop(self, stop: Stop):
        self.stops[stop.stop_id] = stop
        if stop.stop_id not in self.stop_to_routes:
            self.stop_to_routes[stop.stop_id] = set()

    def add_route(self, route: Route):
        self.routes[route.route_id] = route
        if route.route_id not in self.route_to_trips:
            self.route_to_trips[route.route_id] = []

    def add_trip(self, trip: Trip):
        self.trips[trip.trip_id] = trip
        if trip.route_id in self.route_to_trips:
            self.route_to_trips[trip.route_id].append(trip)

    def add_stop_time(self, st: StopTime):
        self.stop_times.append(st)
        if st.trip_id not in self.trip_to_stoptimes:
            self.trip_to_stoptimes[st.trip_id] = []
        self.trip_to_stoptimes[st.trip_id].append(st)
        
        # Link stop to route
        trip = self.trips.get(st.trip_id)
        if trip:
            self.stop_to_routes[st.stop_id].add(trip.route_id)

    def find_nearest_stops(self, lat: float, lon: float, mode: Optional[str] = None, max_km: float = 3.0, limit: int = 5) -> List[Tuple[Stop, float]]:
        """Finds closest stops to a given coordinate within max_km distance."""
        candidates = []
        for stop in self.stops.values():
            if mode and stop.mode != mode:
                continue
            dist = haversine_distance_km(lat, lon, stop.lat, stop.lon)
            if dist <= max_km:
                candidates.append((stop, dist))
        candidates.sort(key=lambda x: x[1])
        return candidates[:limit]

    def search_stops_by_name(self, query: str, limit: int = 10) -> List[Stop]:
        """Case-insensitive search for stops by name or ID."""
        q = query.lower().strip()
        matches = []
        for stop in self.stops.values():
            if q in stop.stop_name.lower() or q == stop.stop_id:
                matches.append(stop)
                if len(matches) >= limit:
                    break
        return matches

def load_gtfs_bus_data(network: TransitNetwork, data_dir: Optional[Path] = None):
    """Loads Delhi Bus static GTFS data into network."""
    path = (data_dir or DATA_DIR) / "delhi_buses_gtfs"
    if not path.exists():
        return

    # Load stops
    stops_file = path / "stops.txt"
    if stops_file.exists():
        with open(stops_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stop = Stop(
                        stop_id=f"BUS_{row['stop_id'].strip()}",
                        stop_name=row['stop_name'].strip(),
                        lat=float(row['stop_lat']),
                        lon=float(row['stop_lon']),
                        mode="bus",
                        stop_code=row.get('stop_code')
                    )
                    network.add_stop(stop)
                except (ValueError, KeyError):
                    continue

    # Load routes
    routes_file = path / "routes.txt"
    if routes_file.exists():
        with open(routes_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    route = Route(
                        route_id=f"BUS_{row['route_id'].strip()}",
                        short_name=row.get('route_short_name', '').strip() or row['route_id'].strip(),
                        long_name=row.get('route_long_name', '').strip(),
                        route_type=int(row.get('route_type', 3)),
                        mode="bus",
                        description=row.get('route_desc', '').strip()
                    )
                    network.add_route(route)
                except (ValueError, KeyError):
                    continue

    # Load trips
    trips_file = path / "trips.txt"
    if trips_file.exists():
        with open(trips_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trip = Trip(
                        trip_id=f"BUS_{row['trip_id'].strip()}",
                        route_id=f"BUS_{row['route_id'].strip()}",
                        service_id=row.get('service_id', '1').strip(),
                        direction_id=int(row.get('direction_id', 0) or 0),
                        shape_id=row.get('shape_id')
                    )
                    network.add_trip(trip)
                except (ValueError, KeyError):
                    continue

    # Load stop times
    stop_times_file = path / "stop_times.txt"
    if stop_times_file.exists():
        with open(stop_times_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    arr_sec = time_to_seconds(row['arrival_time'])
                    st = StopTime(
                        trip_id=f"BUS_{row['trip_id'].strip()}",
                        arrival_time=row['arrival_time'].strip(),
                        departure_time=row['departure_time'].strip(),
                        stop_id=f"BUS_{row['stop_id'].strip()}",
                        stop_sequence=int(row['stop_sequence']),
                        arrival_seconds=arr_sec
                    )
                    network.add_stop_time(st)
                except (ValueError, KeyError):
                    continue

def load_gtfs_metro_data(network: TransitNetwork, data_dir: Optional[Path] = None):
    """Loads Delhi Metro static GTFS data into network."""
    path = (data_dir or DATA_DIR) / "delhi_metro_gtfs"
    if not path.exists():
        return

    # Load stops
    stops_file = path / "stops.txt"
    if stops_file.exists():
        with open(stops_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stop = Stop(
                        stop_id=f"METRO_{row['stop_id'].strip()}",
                        stop_name=row['stop_name'].strip(),
                        lat=float(row['stop_lat']),
                        lon=float(row['stop_lon']),
                        mode="metro",
                        stop_code=row.get('stop_code')
                    )
                    network.add_stop(stop)
                except (ValueError, KeyError):
                    continue

    # Load routes
    routes_file = path / "routes.txt"
    if routes_file.exists():
        with open(routes_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    route = Route(
                        route_id=f"METRO_{row['route_id'].strip()}",
                        short_name=row.get('route_short_name', '').strip() or row['route_id'].strip(),
                        long_name=row.get('route_long_name', '').strip(),
                        route_type=int(row.get('route_type', 1)),
                        mode="metro",
                        description=row.get('route_desc', '').strip()
                    )
                    network.add_route(route)
                except (ValueError, KeyError):
                    continue

    # Load trips
    trips_file = path / "trips.txt"
    if trips_file.exists():
        with open(trips_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    trip = Trip(
                        trip_id=f"METRO_{row['trip_id'].strip()}",
                        route_id=f"METRO_{row['route_id'].strip()}",
                        service_id=row.get('service_id', '1').strip(),
                        direction_id=int(row.get('direction_id', 0) or 0),
                        shape_id=row.get('shape_id')
                    )
                    network.add_trip(trip)
                except (ValueError, KeyError):
                    continue

    # Load stop times
    stop_times_file = path / "stop_times.txt"
    if stop_times_file.exists():
        with open(stop_times_file, encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    arr_sec = time_to_seconds(row['arrival_time'])
                    st = StopTime(
                        trip_id=f"METRO_{row['trip_id'].strip()}",
                        arrival_time=row['arrival_time'].strip(),
                        departure_time=row['departure_time'].strip(),
                        stop_id=f"METRO_{row['stop_id'].strip()}",
                        stop_sequence=int(row['stop_sequence']),
                        arrival_seconds=arr_sec
                    )
                    network.add_stop_time(st)
                except (ValueError, KeyError):
                    continue

def load_od_matrix(network: TransitNetwork, data_dir: Optional[Path] = None):
    """Parses sample DMRC monthly origin-destination matrix CSV."""
    path = (data_dir or DATA_DIR) / "delhi_metro_od_matrix"
    csv_file = path / "08_DMRC_Monthly_OD_Sample.csv"
    if not csv_file.exists():
        return

    with open(csv_file, encoding="latin1") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return

        destinations = [h.strip() for h in header[1:] if h.strip() and h.strip() != '']
        for row in reader:
            if not row:
                continue
            origin = row[0].strip()
            if not origin or origin == '':
                continue
            network.od_matrix[origin] = {}
            for i, dest in enumerate(destinations, 1):
                if i < len(row):
                    val_str = row[i].strip()
                    if val_str.isdigit():
                        network.od_matrix[origin][dest] = int(val_str)

def get_loaded_network() -> TransitNetwork:
    """Convenience singleton loader for Delhi Transit Network."""
    net = TransitNetwork()
    load_gtfs_bus_data(net)
    load_gtfs_metro_data(net)
    load_od_matrix(net)
    return net
