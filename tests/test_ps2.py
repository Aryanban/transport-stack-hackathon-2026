"""Regression checks against the actual uploaded schedule and ticket samples."""
import json
import unittest

from src.ps2.api import config, crowding, journeys, state, validation, vehicles
from src.ps2.model import DEFAULT_PROFILES, TICKETS, build, tier


class ProblemTwoTests(unittest.TestCase):
    def test_rebuild_and_holdout(self):
        built = build(TICKETS)
        self.assertEqual(json.loads(json.dumps(built)), json.loads(DEFAULT_PROFILES.read_text(encoding="utf-8")))
        self.assertEqual(built["audit"]["modeled_ticket_rows"], 6125)
        report = built["validation"]
        self.assertEqual(report["scored_segment_hour_cells"], 730)
        self.assertLess(report["holdout_mae"], report["route_baseline_mae"])
        self.assertGreater(built["audit"]["payment_methods"]["One Delhi QR App"], 0)

    def test_coverage_and_capacity(self):
        self.assertEqual(tier(1.0), "Seats available")
        self.assertEqual(tier(1.4), "Standing room")
        self.assertEqual(tier(1.6), "Heavily crowded")
        covered = crowding("502UP", 18, False)
        self.assertTrue(any(row["days"] >= 3 for row in covered["segments"]))
        missing = crowding("502UP", 2, False)
        self.assertTrue(all(row["level"] == "Unknown" for row in missing["segments"]))
        self.assertIn("generated", validation()["source"].lower())

    def test_real_schedule_and_sample_annotations(self):
        sample = config()
        feed, _ = state()
        self.assertGreater(len(feed.trips), 50_000)
        result = journeys(sample["origin"]["id"], sample["destination"]["id"], sample["defaultTime"], 15)
        self.assertTrue(result["options"])
        self.assertEqual(result["options"][0]["label"], "Fastest")
        self.assertTrue(any(leg["crowd"]["days"] for option in result["options"] for leg in option["legs"]))
        for option in result["options"]:
            for leg in option["legs"]:
                scheduled_stops = {stop.stop for stop in feed.trips[leg["tripId"]].times}
                self.assertIn(leg["from"]["id"], scheduled_stops)
                self.assertIn(leg["to"]["id"], scheduled_stops)
        self.assertEqual(journeys("2070", "1025", "2026-11-11T18:00", 0)["options"][0]["label"], "Fastest")

    def test_disabled_live_feed(self):
        from unittest.mock import patch
        import os
        with patch.dict(os.environ, {"DTS_API_KEY": "", "DELHI_GTFS_RT_API_KEY": ""}):
            self.assertEqual(vehicles(), {"status": "disabled", "positions": []})


def test_multimodal_transfer_waits_for_walk_and_boarding_buffer():
    from datetime import date
    from src.ps2.timetable import Feed, StopTime, Trip, combine_feeds, local_time

    day = date(2026, 11, 14)
    calendar = {"daily": (day, day, (True,) * 7)}
    bus_stops = {"a": {"id": "a", "lat": 28.600, "lon": 77.20},
                 "b": {"id": "b", "lat": 28.610, "lon": 77.20}}
    metro_stops = {"metro:x": {"id": "metro:x", "lat": 28.611, "lon": 77.20},
                   "metro:y": {"id": "metro:y", "lat": 28.625, "lon": 77.20}}
    bus_trip = Trip("b1", "B", "", "daily", (StopTime("a", 28800, 28800, 1),
                                             StopTime("b", 29400, 29400, 2)))
    def metro_trip(trip, start):
        return Trip(trip, "metro:R", "", "metro:daily",
                    (StopTime("metro:x", start, start, 1),
                     StopTime("metro:y", start + 360, start + 360, 2)), "metro")

    bus = Feed(bus_stops, {"B": "Bus"}, {"b1": bus_trip}, calendar, {})
    metro = Feed(metro_stops, {"metro:R": "Metro"},
                 {key: metro_trip(key, stamp) for key, stamp in (("early", 29700), ("valid", 29820))},
                 {"metro:daily": calendar["daily"]}, {})
    result = combine_feeds(bus, metro).journeys("a", "metro:y", local_time("2026-11-14T08:00"))
    assert len(result) == 1
    first, second = result[0]
    assert first.trip.mode == "bus" and second.trip.mode == "metro"
    assert second.trip.id == "valid"
    assert second.walk_minutes == 2
