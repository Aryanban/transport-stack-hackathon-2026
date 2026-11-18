"""Stop-to-stop observations from the organisers' October 2026 bus GPS archive.

The archive (data/raw/delhi-dtc-bus-gtfs-rt-2026-10.7z) holds one SQLite
database per day, bus_movements_YYYY_MM_DD.db, with a table vehicle_feed
(vehicle_id, lat, lng, speed, route_id as float, trip_id, timestamp as UTC
epoch text, date, time). DTC buses only.

Each day is extracted on its own, matched with the same code as the live log
(src.ps1.matcher), written to data/raw/obs/YYYY-MM-DD.csv.gz, and deleted, so
the run never needs more than a few days unpacked at once.

    python -m src.ps1.october            # every day not processed yet
    python -m src.ps1.october 2026_10_15 # one day
"""
from __future__ import annotations

import sqlite3
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from .network import ROOT

RAW = ROOT / "data" / "raw"
ARCHIVE = RAW / "delhi-dtc-bus-gtfs-rt-2026-10.7z"
DAYS_DIR = RAW / "days"
OBS_DIR = RAW / "obs"
THIN_S = 15        # keep at most one point per bus per 15 s, like the live feed
RUN_GAP_S = 600    # a gap this long starts a new run of the same bus and trip
SEVEN_ZIP = "7zz"


def day_names():
    out = subprocess.run([SEVEN_ZIP, "l", "-ba", str(ARCHIVE)], capture_output=True, text=True, check=True)
    names = [line.split()[-1] for line in out.stdout.splitlines() if line.strip().endswith(".db")]
    return sorted(n[len("bus_movements_"):-3] for n in names)


def extract(day: str) -> Path:
    name = f"bus_movements_{day}.db"
    DAYS_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([SEVEN_ZIP, "x", "-y", f"-o{DAYS_DIR}", str(ARCHIVE), name],
                   check=True, capture_output=True)
    return DAYS_DIR / name


def read_day(db: Path) -> pd.DataFrame:
    """Positions as the matcher expects: ts, vehicle_id, route_id, trip_id, lat, lon."""
    sql = """SELECT vehicle_id, CAST(timestamp AS INTEGER) AS ts,
                    CAST(lat AS REAL) AS lat, CAST(lng AS REAL) AS lon,
                    CAST(CAST(route_id AS INTEGER) AS TEXT) AS route_id, trip_id
             FROM vehicle_feed
             WHERE route_id IS NOT NULL AND vehicle_id IS NOT NULL AND timestamp IS NOT NULL"""
    parts = []
    with sqlite3.connect(f"file:{db}?immutable=1", uri=True) as con:
        for chunk in pd.read_sql_query(sql, con, chunksize=2_000_000):
            chunk = chunk.dropna(subset=["ts", "lat", "lon"])
            chunk = chunk[chunk.lat.between(28.0, 29.2) & chunk.lon.between(76.6, 77.7)]
            chunk = chunk.assign(bucket=chunk.ts // THIN_S).drop_duplicates(["vehicle_id", "bucket"])
            parts.append(chunk)
    df = pd.concat(parts, ignore_index=True).drop_duplicates(["vehicle_id", "bucket"])
    df["trip_id"] = df.trip_id.fillna("").astype(str)
    df = df.sort_values(["vehicle_id", "ts"], kind="stable")
    # Split a bus's trip into separate runs at long gaps, so one run never spans two passes.
    key = df.vehicle_id + "|" + df.trip_id + "|" + df.route_id
    new_run = (key != key.shift()) | (df.ts.diff() > RUN_GAP_S)
    df["trip_id"] = df.trip_id + "#" + new_run.cumsum().astype(str)
    return df[["ts", "vehicle_id", "route_id", "trip_id", "lat", "lon"]].reset_index(drop=True)


def process(day: str) -> tuple[str, int, int]:
    from .matcher import observations
    from .network import load
    out = OBS_DIR / f"{day.replace('_', '-')}.csv.gz"
    db = extract(day)
    try:
        pos = read_day(db)
        obs = observations(load(), pos)
        obs = obs.drop_duplicates(["vehicle_id", "route_id", "idx", "t0"])
        OBS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(".tmp")
        obs.to_csv(tmp, index=False, compression="gzip")
        tmp.replace(out)
    finally:
        db.unlink(missing_ok=True)
    return day, len(pos), len(obs)


def main(days=None, workers=3):
    days = days or [d for d in day_names() if not (OBS_DIR / f"{d.replace('_', '-')}.csv.gz").exists()]
    print(f"{len(days)} day(s) to process", flush=True)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for day, n_pos, n_obs in pool.map(process, days):
            print(f"{day}: {n_pos} positions -> {n_obs} stretch observations", flush=True)
    from .matcher import write_combined
    combined = write_combined()
    print(f"combined: {len(combined)} observations ({(combined.source == 'archive').sum()} from the archive)")


if __name__ == "__main__":
    main(sys.argv[1:] or None)
