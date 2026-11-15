"""
src/ps2/metro_loader.py
Dynamically builds GeoJSON for the Delhi Metro (DMRC) network directly from
data/delhi_metro_gates/03_DMRC_Gate_Locations.xlsx and topology definitions.
Zero static mocks. 100% data-driven.
"""
import csv
import json
import io
import os
import zipfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
GATES_FILE = ROOT / "data" / "delhi_metro_gates" / "03_DMRC_Gate_Locations.xlsx"
TOPOLOGY_FILE = ROOT / "data" / "metro_segment_loads" / "dmrc_yellow_line_topology.json"

LINE_METADATA = {
    "1": {"name": "Red Line", "color": "#DC2626"},
    "2": {"name": "Yellow Line", "color": "#F59E0B"},
    "3": {"name": "Blue Line", "color": "#2563EB"},
    "4": {"name": "Blue Branch", "color": "#2563EB"},
    "5": {"name": "Green Line", "color": "#009639"},
    "6": {"name": "Violet Line", "color": "#7C3AED"},
    "7": {"name": "Pink Line", "color": "#FF69B4"},
    "8": {"name": "Magenta Line", "color": "#990099"},
    "9": {"name": "Grey Line", "color": "#808080"},
    "AEL": {"name": "Airport Express", "color": "#E65100"},
    "RMGL": {"name": "Rapid Metro", "color": "#008080"},
}

def _parse_coordinate(val) -> float | None:
    if val is None:
        return None
    s = str(val).strip().rstrip("NSEW").strip()
    try:
        return float(s)
    except ValueError:
        return None

@lru_cache(maxsize=1)
def get_metro_network_geojson() -> Dict[str, Any]:
    """
    Parses DMRC Gate Locations workbook and emits GeoJSON FeatureCollection.
    Features include both line viaduct corridors and individual station gates.
    """
    if not GATES_FILE.is_file():
        # Fallback to local geojson if xlsx is missing
        backup = Path(__file__).parent / "web" / "delhi_metro.geojson"
        if backup.is_file():
            return json.loads(backup.read_text(encoding="utf-8"))
        return {"type": "FeatureCollection", "features": []}

    with GATES_FILE.open("rb") as stream:
        wb = openpyxl.load_workbook(stream, data_only=True, read_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
        wb.close()

    stations_by_name: Dict[str, List[Dict[str, Any]]] = {}

    for row in rows[1:]:
        line_code = str(row[0]).strip() if row[0] is not None else ""
        st_code = str(row[1]).strip() if row[1] is not None else ""
        name = str(row[2]).strip() if row[2] is not None else st_code
        st_type = str(row[3]).strip() if row[3] is not None else "Elevated"
        interchange = str(row[4]).strip().upper() == "Y" if row[4] is not None else False
        lat = _parse_coordinate(row[5])
        lon = _parse_coordinate(row[6])

        if not lat or not lon or not st_code or not line_code:
            continue

        st_data = {
            "code": st_code,
            "name": name,
            "line": line_code,
            "type": st_type,
            "interchange": interchange,
            "lat": lat,
            "lon": lon,
        }
        stations_by_name.setdefault(name, []).append(st_data)

    features: List[Dict[str, Any]] = []

    # 1. Add Station Point Features (Grouped by station name for interchanges)
    for st_name, gate_list in stations_by_name.items():
        base_st = gate_list[0]
        line_names = sorted(set(
            LINE_METADATA.get(g["line"], {}).get("name", f"Line {g['line']}")
            for g in gate_list
        ))
        is_interchange = len(line_names) > 1 or any(g["interchange"] for g in gate_list)
        prime_line = LINE_METADATA.get(base_st["line"], {"name": f"Line {base_st['line']}", "color": "#2563EB"})

        features.append({
            "type": "Feature",
            "properties": {
                "type": "station",
                "name": st_name,
                "code": base_st["code"],
                "line": prime_line["name"],
                "color": prime_line["color"],
                "lines": line_names,
                "lines_str": " · ".join(line_names),
                "interchange": is_interchange,
                "station_type": base_st["type"],
                "gate_count": len(gate_list),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [base_st["lon"], base_st["lat"]]
            }
        })

    # Draw only observed GTFS geometry and explicitly supplied station order.
    folder = Path(os.getenv("PS2_METRO_GTFS", ROOT / "data" / "delhi_metro_gtfs"))
    def read(name):
        filename = name + ".txt"
        if folder.is_dir():
            path = folder / filename
            if path.is_file():
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    return list(csv.DictReader(handle))
            return []
        with zipfile.ZipFile(folder) as archive:
            entry = next((name for name in archive.namelist() if Path(name).name == filename), None)
            if entry is None:
                return []
            with archive.open(entry) as stream:
                return list(csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")))

    names = {}
    for row in read("routes"):
        label = row.get("route_long_name") or row.get("route_short_name") or row["route_id"]
        names[row["route_id"]] = label.partition("_")[0].strip().title()
    mapped_names = {name.casefold() for name in stations_by_name}
    for row in read("stops"):
        name = row["stop_name"]
        if name.casefold() in mapped_names or not row.get("stop_lat") or not row.get("stop_lon"):
            continue
        if row.get("location_type", "") not in ("", "0", "1"):
            continue
        mapped_names.add(name.casefold())
        features.append({"type": "Feature",
            "properties": {"type": "station", "name": name, "line": "Metro", "interchange": False},
            "geometry": {"type": "Point", "coordinates": [float(row["stop_lon"]), float(row["stop_lat"])]}})

    shapes = defaultdict(list)
    for row in read("shapes"):
        shapes[row["shape_id"]].append((int(row["shape_pt_sequence"]),
                                       [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])]))

    def track(name, coords, source):
        if len(coords) < 2:
            return
        color = next((meta["color"] for meta in LINE_METADATA.values()
                      if meta["name"].casefold().startswith(name.casefold())), "#64748B")
        features.append({"type": "Feature",
                         "properties": {"type": "metro", "name": name, "color": color, "source": source},
                         "geometry": {"type": "LineString", "coordinates": coords}})

    for route, shape in sorted({(r["route_id"], r["shape_id"]) for r in read("trips")}):
        if route in names:
            points = sorted(shapes[shape])
            # The supplied file contains samples of shapes. Never bridge omitted points.
            contiguous = []
            last = None
            for sequence, coord in points:
                if last is not None and sequence != last + 1:
                    track(names[route], contiguous, "GTFS shape sample")
                    contiguous = []
                contiguous.append(coord)
                last = sequence
            track(names[route], contiguous, "GTFS shape sample")

    if TOPOLOGY_FILE.is_file() and not any(
            f["properties"].get("source") == "GTFS shape sample"
            and f["properties"]["name"].startswith("Yellow") for f in features):
        topology = json.loads(TOPOLOGY_FILE.read_text(encoding="utf-8"))
        lookup = {name.casefold(): station for name, stations in stations_by_name.items()
                  for station in stations if station["line"] == "2"}
        contiguous = []
        for name in topology["stations"]:
            station = lookup.get(name.casefold())
            if station is None:
                track("Yellow Line", contiguous, "Ordered station schematic")
                contiguous = []
            else:
                contiguous.append([station["lon"], station["lat"]])
        track("Yellow Line", contiguous, "Ordered station schematic")

    return {"type": "FeatureCollection", "features": features}
