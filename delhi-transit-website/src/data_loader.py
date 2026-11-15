"""
Delhi Transport Stack - Data Loader & Spatial Indexer
Parses static GTFS (Bus, Metro, Shared Mobility), DMRC OD Matrix, Gate locations, and Footfall.
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
    mode: str = "bus"  # "bus", "metro", or "shared_mobility"
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
        try:
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            return h * 3600 + m * 60 + s
        except ValueError:
            return 0
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
    """Encapsulates loaded Delhi transit network (Bus, Metro, Shared Mobility, OD matrix)."""

    def __init__(self):
        self.stops: Dict[str, Stop] = {}
        self.routes: Dict[str, Route] = {}
        self.trips: Dict[str, Trip] = {}
        self.stop_times: List[StopTime] = []
        self.stop_times_count: int = 0
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
        self.stop_times_count += 1
        # Keep sample stop_times in memory for trips index
        if len(self.stop_times) < 5000:
            self.stop_times.append(st)
        if st.trip_id not in self.trip_to_stoptimes and len(self.trip_to_stoptimes) < 2000:
            self.trip_to_stoptimes[st.trip_id] = []
        if st.trip_id in self.trip_to_stoptimes:
            self.trip_to_stoptimes[st.trip_id].append(st)
        
        # Link stop to route
        trip = self.trips.get(st.trip_id)
        if trip:
            if st.stop_id not in self.stop_to_routes:
                self.stop_to_routes[st.stop_id] = set()
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
            if q in stop.stop_name.lower() or q == stop.stop_id.lower():
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
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                idx_id = header.index("stop_id") if "stop_id" in header else 0
                idx_name = header.index("stop_name") if "stop_name" in header else 2
                idx_lat = header.index("stop_lat") if "stop_lat" in header else 3
                idx_lon = header.index("stop_lon") if "stop_lon" in header else 4
                idx_code = header.index("stop_code") if "stop_code" in header else 1
                for row in reader:
                    if len(row) > max(idx_id, idx_name, idx_lat, idx_lon):
                        try:
                            stop = Stop(
                                stop_id=f"BUS_{row[idx_id].strip()}",
                                stop_name=row[idx_name].strip(),
                                lat=float(row[idx_lat]),
                                lon=float(row[idx_lon]),
                                mode="bus",
                                stop_code=row[idx_code].strip() if idx_code < len(row) else None
                            )
                            network.add_stop(stop)
                        except (ValueError, IndexError):
                            continue

    # Load routes
    routes_file = path / "routes.txt"
    if routes_file.exists():
        with open(routes_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                idx_id = header.index("route_id") if "route_id" in header else 1
                idx_long = header.index("route_long_name") if "route_long_name" in header else 2
                idx_short = header.index("route_short_name") if "route_short_name" in header else 3
                idx_desc = header.index("route_desc") if "route_desc" in header else 4
                idx_type = header.index("route_type") if "route_type" in header else 5
                for row in reader:
                    if len(row) > idx_id:
                        try:
                            s_name = row[idx_short].strip() if idx_short < len(row) and row[idx_short].strip() else row[idx_id].strip()
                            l_name = row[idx_long].strip() if idx_long < len(row) else s_name
                            r_type = int(row[idx_type]) if idx_type < len(row) and row[idx_type].isdigit() else 3
                            desc = row[idx_desc].strip() if idx_desc < len(row) else ""
                            route = Route(
                                route_id=f"BUS_{row[idx_id].strip()}",
                                short_name=s_name,
                                long_name=l_name,
                                route_type=r_type,
                                mode="bus",
                                description=desc
                            )
                            network.add_route(route)
                        except (ValueError, IndexError):
                            continue

    # Load trips
    trips_file = path / "trips.txt"
    trip_to_route_map: Dict[str, str] = {}
    if trips_file.exists():
        with open(trips_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                idx_rid = header.index("route_id") if "route_id" in header else 0
                idx_tid = header.index("trip_id") if "trip_id" in header else 2
                idx_dir = header.index("direction_id") if "direction_id" in header else 5
                idx_shape = header.index("shape_id") if "shape_id" in header else 7
                for row in reader:
                    if len(row) > max(idx_rid, idx_tid):
                        try:
                            tid = row[idx_tid].strip()
                            rid = row[idx_rid].strip()
                            direction = int(row[idx_dir]) if idx_dir < len(row) and row[idx_dir].isdigit() else 0
                            shape = row[idx_shape].strip() if idx_shape < len(row) else None
                            trip = Trip(
                                trip_id=f"BUS_{tid}",
                                route_id=f"BUS_{rid}",
                                service_id="1",
                                direction_id=direction,
                                shape_id=shape
                            )
                            network.add_trip(trip)
                            trip_to_route_map[tid] = f"BUS_{rid}"
                        except (ValueError, IndexError):
                            continue

    # Load stop times with fast streaming
    stop_times_file = path / "stop_times.txt"
    if stop_times_file.exists():
        with open(stop_times_file, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                idx_tid = header.index("trip_id") if "trip_id" in header else 0
                idx_arr = header.index("arrival_time") if "arrival_time" in header else 1
                idx_dep = header.index("departure_time") if "departure_time" in header else 2
                idx_sid = header.index("stop_id") if "stop_id" in header else 3
                idx_seq = header.index("stop_sequence") if "stop_sequence" in header else 4

                count = 0
                for row in reader:
                    if len(row) > max(idx_tid, idx_arr, idx_sid):
                        count += 1
                        tid = row[idx_tid].strip()
                        sid = f"BUS_{row[idx_sid].strip()}"
                        
                        # Link stop to route
                        rid = trip_to_route_map.get(tid)
                        if rid:
                            if sid not in network.stop_to_routes:
                                network.stop_to_routes[sid] = set()
                            network.stop_to_routes[sid].add(rid)

                        # Sample first 5000 full stop times into memory
                        if count <= 5000:
                            try:
                                seq = int(row[idx_seq]) if idx_seq < len(row) and row[idx_seq].isdigit() else 0
                                st = StopTime(
                                    trip_id=f"BUS_{tid}",
                                    arrival_time=row[idx_arr].strip(),
                                    departure_time=row[idx_dep].strip() if idx_dep < len(row) else row[idx_arr].strip(),
                                    stop_id=sid,
                                    stop_sequence=seq,
                                    arrival_seconds=time_to_seconds(row[idx_arr])
                                )
                                network.stop_times.append(st)
                            except (ValueError, IndexError):
                                pass

                network.stop_times_count += count

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

def load_shared_mobility_data(network: TransitNetwork, data_dir: Optional[Path] = None):
    """Loads Delhi Shared Mobility GTFS data into network."""
    path = (data_dir or DATA_DIR) / "delhi_shared_mobility_gtfs"
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
                        stop_id=f"SHARED_{row['stop_id'].strip()}",
                        stop_name=row['stop_name'].strip(),
                        lat=float(row['stop_lat']),
                        lon=float(row['stop_lon']),
                        mode="shared_mobility",
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
                        route_id=f"SHARED_{row['route_id'].strip()}",
                        short_name=row.get('route_short_name', '').strip() or row['route_id'].strip(),
                        long_name=row.get('route_long_name', '').strip(),
                        route_type=int(row.get('route_type', 3)),
                        mode="shared_mobility",
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
                        trip_id=f"SHARED_{row['trip_id'].strip()}",
                        route_id=f"SHARED_{row['route_id'].strip()}",
                        service_id=row.get('service_id', '1').strip(),
                        direction_id=int(row.get('direction_id', 0) or 0),
                        shape_id=row.get('shape_id')
                    )
                    network.add_trip(trip)
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
    load_shared_mobility_data(net)
    load_od_matrix(net)
    return net
