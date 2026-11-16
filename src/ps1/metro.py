"""Delhi Metro stations for map context, from DMRC's gate-location workbook and the metro GTFS stops.

Only station points are drawn. The repo has no complete metro track shapes, and stations whose
gate rows share one placeholder point are left out rather than drawn in the wrong place.
"""
import csv
from collections import Counter
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
GATES_FILE = ROOT / "data" / "delhi_metro_gates" / "03_DMRC_Gate_Locations.xlsx"
GTFS_STOPS = ROOT / "data" / "delhi_metro_gtfs" / "stops.txt"
LINES = {"1": "Red Line", "2": "Yellow Line", "3": "Blue Line", "4": "Blue Line", "5": "Green Line",
         "6": "Violet Line", "7": "Pink Line", "8": "Magenta Line", "9": "Grey Line",
         "AEL": "Airport Express", "RMGL": "Rapid Metro"}


def _coord(val):
    try:
        return float(str(val).strip().rstrip("NSEW").strip())
    except (TypeError, ValueError):
        return None


def stations():
    by_name = {}
    if GATES_FILE.is_file():
        wb = openpyxl.load_workbook(GATES_FILE, data_only=True, read_only=True)
        rows = list(wb.active.iter_rows(values_only=True))[1:]
        wb.close()
        for line, code, name, *_rest in rows:
            lat, lon = _coord(_rest[2] if len(_rest) > 2 else None), _coord(_rest[3] if len(_rest) > 3 else None)
            if not (line and code and lat and lon):
                continue
            name = str(name or code).strip()
            st = by_name.setdefault(name, {"name": name, "lat": lat, "lon": lon, "lines": set()})
            st["lines"].add(LINES.get(str(line).strip(), f"Line {line}"))
    if GTFS_STOPS.is_file():  # stations the gate file does not list
        with GTFS_STOPS.open(encoding="utf-8-sig", newline="") as fh:
            for row in csv.DictReader(fh):
                name = row["stop_name"].strip()
                if name.casefold() in {n.casefold() for n in by_name} or row.get("location_type", "") not in ("", "0", "1"):
                    continue
                if row.get("stop_lat") and row.get("stop_lon"):
                    by_name[name] = {"name": name, "lat": float(row["stop_lat"]), "lon": float(row["stop_lon"]), "lines": set()}
    spot = lambda s: (round(s["lat"], 3), round(s["lon"], 3))  # ~100 m
    stacked = Counter(spot(s) for s in by_name.values())
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature",
         "properties": {"type": "station", "name": s["name"], "lines": sorted(s["lines"]),
                        "interchange": len(s["lines"]) > 1},
         "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]}}
        for s in by_name.values() if stacked[spot(s)] < 3]}
