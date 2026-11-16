"""Storage for the raw GTFS-RT log: hourly gzip CSV files in data/gps_log/.

Writing: the logger appends one gzip member per poll, so a crash can only cut
off the last member. Reading: read_file keeps every complete row before a cut.
Compacting: when an hour is over, its file is rewritten sorted by vehicle and
time as one gzip member at level 9 (about half the size), after checking the
row count, then swapped in atomically.
"""
from __future__ import annotations

import gzip
import io
import os
import zlib
from pathlib import Path

import pandas as pd

FIELDS = ["ts", "vehicle_id", "route_id", "trip_id", "lat", "lon", "speed_ms"]
DTYPES = {"ts": "int64", "vehicle_id": "category", "route_id": "category", "trip_id": "category",
          "lat": "float64", "lon": "float64", "speed_ms": "float32"}
DONE_SUFFIX = ".compacted"  # marker file next to a compacted hour


def _decompress_members(data: bytes) -> bytes:
    """Decompress concatenated gzip members, stopping cleanly at a cut-off one."""
    out = bytearray()
    while data:
        d = zlib.decompressobj(zlib.MAX_WBITS | 16)
        try:
            out += d.decompress(data)
        except zlib.error:
            break
        if not d.eof:  # truncated last member: keep what decoded
            break
        data = d.unused_data
    return bytes(out)


def read_file(path) -> pd.DataFrame:
    text = _decompress_members(Path(path).read_bytes()).decode("utf-8", "replace")
    if "\n" not in text:
        return pd.DataFrame({c: pd.Series(dtype=t) for c, t in DTYPES.items()})
    text = text[: text.rfind("\n") + 1]  # drop a partial last line
    df = pd.read_csv(io.StringIO(text), dtype={"vehicle_id": str, "route_id": str, "trip_id": str},
                     on_bad_lines="skip")
    df = df[[c for c in FIELDS if c in df.columns]].dropna(subset=["ts", "vehicle_id", "lat", "lon"])
    df["ts"] = df["ts"].astype("int64")
    for c in ("vehicle_id", "route_id", "trip_id"):
        df[c] = df[c].fillna("").astype("category")
    return df


def header(path) -> list[str]:
    text = _decompress_members(Path(path).read_bytes()[:65536]).decode("utf-8", "replace")
    return text.split("\n", 1)[0].strip().split(",") if text else []


def compact(path, mark_done=True) -> tuple[int, int]:
    """Sort, dedupe and recompress one hour file. Returns (bytes before, after)."""
    path = Path(path)
    before = path.stat().st_size
    df = read_file(path).drop_duplicates(["vehicle_id", "ts"])
    df = df.sort_values(["vehicle_id", "ts"], kind="stable")
    tmp = path.with_suffix(".tmp")
    df = df.assign(lat=df.lat.round(6), lon=df.lon.round(6), speed_ms=df.speed_ms.astype("float64").round(2))
    payload = df.to_csv(index=False, columns=FIELDS).encode()
    with open(tmp, "wb") as fh:
        fh.write(gzip.compress(payload, 9))
    check = read_file(tmp)
    if len(check) != len(df):
        tmp.unlink()
        raise RuntimeError(f"compaction check failed for {path.name}: {len(check)} != {len(df)} rows")
    os.replace(tmp, path)
    if mark_done:
        Path(str(path) + DONE_SUFFIX).touch()
    return before, path.stat().st_size


def compact_finished(log_dir, current_name: str | None = None):
    """Compact every hour file except the one being written."""
    for f in sorted(Path(log_dir).glob("*.csv.gz")):
        if f.name == current_name or Path(str(f) + DONE_SUFFIX).exists():
            continue
        b, a = compact(f)
        print(f"compacted {f.name}: {b / 1e6:.1f} MB -> {a / 1e6:.1f} MB", flush=True)
