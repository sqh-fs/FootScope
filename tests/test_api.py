import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend import main

LEAGUE = "/api/v1/competitions/PL"


class LeagueApiTest(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(directory) / "test.sqlite3"
        self.client = self.enterContext(TestClient(main.create_app(self.database)))

    def seed_season(self, synced_at=None):
        timestamp = (synced_at or datetime.now(UTC)).isoformat()
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "INSERT INTO seasons VALUES (1, '2026-08-21', '2027-05-30', 1, ?, ?)",
                (timestamp, timestamp),
            )

    def test_empty_snapshot_is_not_cached(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/ready").status_code, 503)
        response = self.client.get(LEAGUE)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "NO_DATA")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.seed_season()
        self.assertEqual(self.client.get("/ready").status_code, 200)
        self.assertEqual(self.client.get(LEAGUE).status_code, 200)

    def test_concurrent_requests_share_snapshot_and_see_updates_after_expiry(self):
        self.seed_season()
        with (
            patch.object(main, "monotonic", return_value=100) as clock,
            patch.object(main, "read_snapshot", wraps=main.read_snapshot) as read,
            ThreadPoolExecutor(max_workers=8) as pool,
        ):
            responses = list(pool.map(self.client.get, [LEAGUE] * 16))
            self.assertEqual(read.call_count, 1)
            self.assertTrue(all(response.status_code == 200 for response in responses))
            self.assertTrue(all(response.content == responses[0].content for response in responses))
            self.assertIn("s-maxage=30", responses[0].headers["cache-control"])

            with closing(sqlite3.connect(self.database)) as connection, connection:
                connection.execute("UPDATE seasons SET current_matchday = 2")
            clock.return_value = 117
            cached = self.client.get(LEAGUE)
            self.assertEqual(cached.json()["season"]["current_matchday"], 1)
            self.assertIn("s-maxage=13", cached.headers["cache-control"])
            clock.return_value = 130
            self.assertEqual(self.client.get(LEAGUE).json()["season"]["current_matchday"], 2)
            self.assertEqual(read.call_count, 2)

    def test_cache_lifetime_stops_at_stale_boundary(self):
        self.seed_season(datetime.now(UTC) - timedelta(hours=24) + timedelta(seconds=10))
        response = self.client.get(LEAGUE)
        self.assertFalse(response.json()["meta"]["is_stale"])
        max_age = int(response.headers["cache-control"].split("s-maxage=")[1])
        self.assertLessEqual(max_age, 10)

    def test_disabled_cache_reads_each_request(self):
        self.seed_season()
        with (
            TestClient(main.create_app(self.database, snapshot_cache_ttl=0)) as client,
            patch.object(main, "read_snapshot", wraps=main.read_snapshot) as read,
        ):
            first = client.get(LEAGUE)
            second = client.get(LEAGUE)
            self.assertEqual(first.content, second.content)
            self.assertEqual(read.call_count, 2)
            self.assertEqual(first.headers["cache-control"], "no-store")
