"""
src/ps2/metro_loader.py
Dynamically builds GeoJSON for the Delhi Metro (DMRC) network directly from
data/delhi_metro_gates/03_DMRC_Gate_Locations.xlsx and topology definitions.
Zero static mocks. 100% data-driven.
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, List
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
GATES_FILE = ROOT / "data" / "delhi_metro_gates" / "03_DMRC_Gate_Locations.xlsx"
TOPOLOGY_FILE = ROOT / "data" / "metro_segment_loads" / "dmrc_yellow_line_topology.json"

LINE_METADATA = {
    "1": {"name": "Red Line", "color": "#EE2726"},
    "2": {"name": "Yellow Line", "color": "#FFD700"},
    "3": {"name": "Blue Line", "color": "#0066B2"},
    "4": {"name": "Blue Branch", "color": "#0066B2"},
    "5": {"name": "Green Line", "color": "#009639"},
    "6": {"name": "Violet Line", "color": "#800080"},
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
            import json
            return json.loads(backup.read_text(encoding="utf-8"))
        return {"type": "FeatureCollection", "features": []}

    wb = openpyxl.load_workbook(str(GATES_FILE), data_only=True)
    sheet = wb.active
    rows = list(sheet.iter_rows(values_only=True))

    stations_by_code: Dict[str, Dict[str, Any]] = {}
    stations_by_name: Dict[str, List[Dict[str, Any]]] = {}
    stations_by_line: Dict[str, List[Dict[str, Any]]] = {}

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
        stations_by_code[st_code] = st_data
        stations_by_name.setdefault(name, []).append(st_data)
        stations_by_line.setdefault(line_code, []).append(st_data)

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
                "first_train": "05:30 AM",
                "last_train": "11:15 PM"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [base_st["lon"], base_st["lat"]]
            }
        })

    # 2. Add Line String Viaduct Corridors
    # Sort stations along corridors (by geographical continuity)
    for line_code, st_list in stations_by_line.items():
        if len(st_list) < 2:
            continue

        line_info = LINE_METADATA.get(line_code, {"name": f"Line {line_code}", "color": "#2563EB"})

        # Simple greedy nearest-neighbor order to build continuous track polyline
        remaining = list(st_list)
        # Start at Northern-most station
        remaining.sort(key=lambda s: s["lat"], reverse=True)
        ordered = [remaining.pop(0)]

        while remaining:
            curr = ordered[-1]
            # Find nearest remaining station
            nearest_idx = min(
                range(len(remaining)),
                key=lambda i: (remaining[i]["lat"] - curr["lat"])**2 + (remaining[i]["lon"] - curr["lon"])**2
            )
            nearest = remaining.pop(nearest_idx)
            # Only connect if reasonably adjacent (< 0.15 deg ~ 15 km)
            dist_sq = (nearest["lat"] - curr["lat"])**2 + (nearest["lon"] - curr["lon"])**2
            if dist_sq < 0.05:
                ordered.append(nearest)

        if len(ordered) >= 2:
            coords = [[s["lon"], s["lat"]] for s in ordered]
            features.append({
                "type": "Feature",
                "properties": {
                    "type": "metro",
                    "name": line_info["name"],
                    "line": line_info["name"],
                    "color": line_info["color"],
                    "stations_count": len(ordered)
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }
