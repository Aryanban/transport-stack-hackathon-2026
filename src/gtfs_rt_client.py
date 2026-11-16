"""Delhi buses GTFS-RT client: fetches VehiclePositions.pb from the Delhi Transport Stack.

Live data only. With no API key, or when the feed is unreachable, it returns an empty list,
so callers show "no live data" instead of made-up positions. The key comes from the
environment (DTS_API_KEY), loaded from the gitignored .env when present.
"""
from __future__ import annotations

import os
import time

import requests
from google.transit import gtfs_realtime_pb2


def _load_local_env():
    """Read KEY=VALUE lines from the repo's .env without overriding the real environment."""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


_load_local_env()

DEFAULT_DTS_ENDPOINT = (
    "https://dts-backend.transportstack.in/api/dataset/otd/get-file"
    "?agency=delhi-buses&category=realtime_gtfs&filename=VehiclePositions.pb"
)


class DelhiGTFSRealtimeClient:
    def __init__(self, api_key: str | None = None, endpoint: str | None = None, timeout_seconds: int = 10):
        self.api_key = api_key or os.getenv("DTS_API_KEY") or os.getenv("DELHI_GTFS_RT_API_KEY", "")
        self.endpoint = endpoint or os.getenv("DTS_RT_ENDPOINT", DEFAULT_DTS_ENDPOINT)
        self.timeout = timeout_seconds
        self._cache: list[dict] = []
        self._cache_time = 0.0

    def fetch_vehicle_positions(self, force_refresh: bool = False) -> list[dict]:
        """Current vehicle positions from the live feed, or [] when there is none."""
        now = time.time()
        if not force_refresh and self._cache and now - self._cache_time < 15:
            return self._cache
        if not self.api_key:
            return []
        try:
            resp = requests.get(self.endpoint, headers={"x-api-key": self.api_key},
                                timeout=self.timeout, allow_redirects=False)
            resp.raise_for_status()
            feed = gtfs_realtime_pb2.FeedMessage()
            feed.ParseFromString(resp.content)
        except Exception:
            return []
        vehicles = []
        for entity in feed.entity:
            if not (entity.HasField("vehicle") and entity.vehicle.HasField("position")):
                continue
            v = entity.vehicle
            vehicles.append({
                "vehicle_id": v.vehicle.id or entity.id,
                "route_id": v.trip.route_id,
                "trip_id": v.trip.trip_id,
                "latitude": round(v.position.latitude, 6),
                "longitude": round(v.position.longitude, 6),
                "timestamp": v.timestamp or feed.header.timestamp,
                "source": "live",
            })
        self._cache, self._cache_time = vehicles, now
        return vehicles
