import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "footscope.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    current_matchday INTEGER,
    sync_started_at TEXT NOT NULL,
    synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    code TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standings (
    season_id INTEGER NOT NULL REFERENCES seasons (id),
    team_id INTEGER NOT NULL REFERENCES teams (id),
    position INTEGER NOT NULL,
    played INTEGER NOT NULL,
    won INTEGER NOT NULL,
    drawn INTEGER NOT NULL,
    lost INTEGER NOT NULL,
    goals_for INTEGER NOT NULL,
    goals_against INTEGER NOT NULL,
    goal_difference INTEGER NOT NULL,
    points INTEGER NOT NULL,
    PRIMARY KEY (season_id, team_id)
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    season_id INTEGER NOT NULL REFERENCES seasons (id),
    matchday INTEGER,
    kickoff_utc TEXT NOT NULL,
    status TEXT NOT NULL,
    home_team_id INTEGER NOT NULL REFERENCES teams (id),
    away_team_id INTEGER NOT NULL REFERENCES teams (id),
    home_score INTEGER,
    away_score INTEGER
);

CREATE INDEX IF NOT EXISTS matches_season_kickoff ON matches (season_id, kickoff_utc);

CREATE TABLE IF NOT EXISTS roster_snapshots (
    season_id INTEGER PRIMARY KEY REFERENCES seasons (id),
    sync_started_at TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    squads_json TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(path: Path = DATABASE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as connection:
        connection.executescript(SCHEMA)


def save_snapshot(
    path: Path,
    season: dict,
    teams: list[dict],
    standings: list[dict],
    matches: list[dict],
) -> bool:
    initialize(path)
    with closing(connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        latest = connection.execute("SELECT MAX(sync_started_at) FROM seasons").fetchone()[0]
        if latest and latest >= season["sync_started_at"]:
            return False

        connection.execute(
            """
            INSERT INTO seasons VALUES
                (:id, :start_date, :end_date, :current_matchday, :sync_started_at, :synced_at)
            ON CONFLICT (id) DO UPDATE SET
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                current_matchday = excluded.current_matchday,
                sync_started_at = excluded.sync_started_at,
                synced_at = excluded.synced_at
            """,
            season,
        )
        connection.executemany(
            """
            INSERT INTO teams VALUES (:id, :name, :short_name, :code)
            ON CONFLICT (id) DO UPDATE SET
                name = excluded.name, short_name = excluded.short_name, code = excluded.code
            """,
            teams,
        )
        connection.execute("DELETE FROM standings WHERE season_id = ?", (season["id"],))
        connection.executemany(
            """
            INSERT INTO standings VALUES
                (:season_id, :team_id, :position, :played, :won, :drawn, :lost,
                 :goals_for, :goals_against, :goal_difference, :points)
            """,
            standings,
        )
        connection.executemany(
            """
            INSERT INTO matches VALUES
                (:id, :season_id, :matchday, :kickoff_utc, :status,
                 :home_team_id, :away_team_id, :home_score, :away_score)
            ON CONFLICT (id) DO UPDATE SET
                season_id = excluded.season_id,
                matchday = excluded.matchday,
                kickoff_utc = excluded.kickoff_utc,
                status = excluded.status,
                home_team_id = excluded.home_team_id,
                away_team_id = excluded.away_team_id,
                home_score = excluded.home_score,
                away_score = excluded.away_score
            """,
            matches,
        )

        # The provider sends a full-season list. Withdrawn fixtures should disappear.
        stored_ids = (
            row["id"] for row in connection.execute(
                "SELECT id FROM matches WHERE season_id = ?", (season["id"],)
            )
        )
        incoming_ids = {match["id"] for match in matches}
        removed_ids = [(match_id,) for match_id in stored_ids if match_id not in incoming_ids]
        connection.executemany("DELETE FROM matches WHERE id = ?", removed_ids)
    return True


def read_snapshot(path: Path) -> dict | None:
    if not path.is_file():
        return None
    with closing(connect(path)) as connection, connection:
        connection.execute("BEGIN")
        season = connection.execute(
            "SELECT * FROM seasons ORDER BY sync_started_at DESC LIMIT 1"
        ).fetchone()
        if season is None:
            return None

        season_key = (season["id"],)
        teams = {row["id"]: dict(row) for row in connection.execute("SELECT * FROM teams")}
        standings = [dict(row) for row in connection.execute(
            "SELECT * FROM standings WHERE season_id = ? ORDER BY position", season_key
        )]
        matches = [dict(row) for row in connection.execute(
            "SELECT * FROM matches WHERE season_id = ? ORDER BY kickoff_utc, id", season_key
        )]

    for row in standings:
        row["team"] = teams[row.pop("team_id")]
        del row["season_id"]
    for match in matches:
        match["home_team"] = teams[match.pop("home_team_id")]
        match["away_team"] = teams[match.pop("away_team_id")]
        del match["season_id"]

    synced_at = datetime.fromisoformat(season["synced_at"])
    return {
        "season": {
            "start_date": season["start_date"],
            "end_date": season["end_date"],
            "current_matchday": season["current_matchday"],
        },
        "standings": standings,
        "matches": matches,
        "meta": {
            "source": "football-data.org",
            "last_synced_at": season["synced_at"],
            "is_stale": datetime.now(UTC) - synced_at >= timedelta(hours=24),
        },
    }


def rosters_are_fresh(path: Path, season_id: int) -> bool:
    with closing(connect(path)) as connection:
        row = connection.execute(
            "SELECT synced_at FROM roster_snapshots WHERE season_id = ?", (season_id,)
        ).fetchone()
    return bool(row and datetime.now(UTC) - datetime.fromisoformat(row["synced_at"]) < timedelta(days=1))


def save_rosters(path: Path, season_id: int, started_at: datetime, rosters: dict) -> None:
    with closing(connect(path)) as connection, connection:
        connection.execute(
            """
            INSERT INTO roster_snapshots VALUES (?, ?, ?, ?)
            ON CONFLICT (season_id) DO UPDATE SET
                sync_started_at = excluded.sync_started_at,
                synced_at = excluded.synced_at,
                squads_json = excluded.squads_json
            WHERE excluded.sync_started_at > roster_snapshots.sync_started_at
            """,
            (season_id, started_at.isoformat(), datetime.now(UTC).isoformat(), json.dumps(rosters, ensure_ascii=False)),
        )


def read_team(path: Path, team_id: int) -> dict | None:
    if not 0 < team_id < 2**63:
        return None
    with closing(connect(path)) as connection:
        row = connection.execute(
            """
            SELECT teams.*, seasons.start_date, seasons.end_date, roster_snapshots.synced_at,
                   roster_snapshots.squads_json
            FROM standings
            JOIN teams ON teams.id = standings.team_id
            JOIN seasons ON seasons.id = standings.season_id
            LEFT JOIN roster_snapshots ON roster_snapshots.season_id = seasons.id
            WHERE teams.id = ? AND seasons.id = (
                SELECT id FROM seasons ORDER BY sync_started_at DESC LIMIT 1
            )
            """,
            (team_id,),
        ).fetchone()
    if row is None:
        return None
    roster = json.loads(row["squads_json"]).get(str(team_id)) if row["squads_json"] else None
    return {
        "team": {key: row[key] for key in ("id", "name", "short_name", "code")},
        "season": {"start_date": row["start_date"], "end_date": row["end_date"]},
        "roster": roster,
        "meta": {"source": "football-data.org", "last_synced_at": row["synced_at"] if roster else None},
    }
