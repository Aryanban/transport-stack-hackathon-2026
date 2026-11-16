#!/usr/bin/env python3
"""Poll the Delhi buses GTFS-RT feed and append new positions to hourly gzip CSVs.

Usage:
    python scripts/log_gtfs_rt.py [--interval 20] [--out data/gps_log]

Each row is one vehicle position, deduplicated on (vehicle_id, timestamp).
Files are named YYYYMMDD_HH.csv.gz in IST. When an hour ends, its file is
compacted (sorted, recompressed, row count checked). Safe to stop with Ctrl+C
and start again: a cut-off write loses at most the poll being written.
"""
import argparse
import csv
import gzip
import io
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from google.transit import gtfs_realtime_pb2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.gtfs_rt_client import DEFAULT_DTS_ENDPOINT  # noqa: E402  (also loads .env)
from src.ps1.gpslog import FIELDS, compact, compact_finished, header  # noqa: E402

IST = timezone(timedelta(hours=5, minutes=30))


def fetch(session, url, key):
    resp = session.get(url, headers={"x-api-key": key}, timeout=15, allow_redirects=False)
    resp.raise_for_status()
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(resp.content)
    return feed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=20.0)
    ap.add_argument("--out", default=str(ROOT / "data" / "gps_log"))
    args = ap.parse_args()

    key = os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY")
    if not key:
        sys.exit("DTS_API_KEY is not set (.env or environment).")
    url = os.getenv("DTS_RT_ENDPOINT", DEFAULT_DTS_ENDPOINT)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    current = f"{datetime.now(IST):%Y%m%d_%H}.csv.gz"
    compact_finished(out, current_name=current)
    cur_path = out / current
    if cur_path.exists() and header(cur_path) != FIELDS:  # file from an older column layout
        compact(cur_path, mark_done=False)

    session = requests.Session()
    last_seen = {}  # vehicle_id -> last timestamp written
    backoff = args.interval
    while True:
        started = time.time()
        try:
            feed = fetch(session, url, key)
            stamp = datetime.now(IST)
            name = f"{stamp:%Y%m%d_%H}.csv.gz"
            if name != current:  # the hour rolled over: compact the finished file
                compact_finished(out, current_name=name)
                current = name
            path = out / name
            buf = io.StringIO()
            w = csv.writer(buf)
            if not path.exists():
                w.writerow(FIELDS)
            written = 0
            for ent in feed.entity:
                if not ent.HasField("vehicle"):
                    continue
                v = ent.vehicle
                vid = v.vehicle.id or ent.id
                ts = int(v.timestamp)
                if not ts or last_seen.get(vid) == ts:
                    continue
                last_seen[vid] = ts
                p = v.position
                w.writerow([ts, vid, v.trip.route_id, v.trip.trip_id,
                            f"{p.latitude:.6f}", f"{p.longitude:.6f}", f"{p.speed:.2f}"])
                written += 1
            with open(path, "ab") as fh:  # one complete gzip member per poll
                fh.write(gzip.compress(buf.getvalue().encode(), 6))
                fh.flush()
                os.fsync(fh.fileno())
            print(f"{stamp:%H:%M:%S} entities={len(feed.entity)} new={written}", flush=True)
            backoff = args.interval
        except Exception as exc:  # network blips: keep going with backoff
            backoff = min(backoff * 2, 300)
            print(f"{datetime.now(IST):%H:%M:%S} error: {exc!r}; retry in {backoff:.0f}s", flush=True)
        time.sleep(max(1.0, backoff - (time.time() - started)))


if __name__ == "__main__":
    main()
