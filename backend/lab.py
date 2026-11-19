import csv
import json
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import httpx

from .storage import connect, initialize

SOURCE = "https://football-data.co.uk/englandm.php"
TEAM_ALIASES = {
    "Brighton": "BHA", "Coventry": "COV", "Hull": "HUL", "Ipswich": "IPS",
    "Leeds": "LEE", "Nott'm Forest": "NOT",
}
STAT_COLUMNS = {
    "half_time_goals": ("HTHG", "HTAG"),
    "xg": ("HxG", "AxG"),
    "shots": ("HS", "AS"),
    "shots_on_target": ("HST", "AST"),
    "corners": ("HC", "AC"),
    "fouls": ("HF", "AF"),
    "yellow_cards": ("HY", "AY"),
    "red_cards": ("HR", "AR"),
}
CURRENT_SEASON = "SELECT id FROM seasons ORDER BY sync_started_at DESC LIMIT 1"
MATCH_STATS_JOIN = """
    LEFT JOIN lab_match_stats AS stats
        ON stats.match_id = matches.id AND matches.status = 'FINISHED'
        AND stats.kickoff_utc = matches.kickoff_utc
        AND stats.home_team_id = matches.home_team_id AND stats.away_team_id = matches.away_team_id
        AND stats.home_score = matches.home_score AND stats.away_score = matches.away_score
"""


def normalize_stats(row: dict) -> dict:
    stats = {}
    for metric, columns in STAT_COLUMNS.items():
        parse = float if metric == "xg" else int
        values = [parse(row[column]) if row.get(column) else None for column in columns]
        if any(value is not None and not 0 <= value < float("inf") for value in values):
            raise ValueError(f"比赛统计字段 {metric} 无效。")
        stats[metric] = values
    accuracy = []
    for shots, on_target in zip(stats["shots"], stats["shots_on_target"]):
        if shots is not None and on_target is not None and on_target > shots:
            raise ValueError("射正次数超过射门次数。")
        accuracy.append(round(100 * on_target / shots, 1) if shots and on_target is not None else None)
    stats["shot_accuracy_pct"] = accuracy
    return stats


def import_match_stats(database: Path, source_file: Path | None = None) -> str:
    started_at = datetime.now(UTC).isoformat()
    initialize(database)
    with closing(connect(database)) as connection:
        season = connection.execute(f"SELECT * FROM seasons WHERE id = ({CURRENT_SEASON})").fetchone()
        if season is None:
            raise ValueError("请先同步英超赛程。")

        if source_file is None:
            season_code = season["start_date"][2:4] + season["end_date"][2:4]
            response = httpx.get(f"https://football-data.co.uk/mmz4281/{season_code}/E0.csv", timeout=20)
            response.raise_for_status()
            content = response.content.decode("utf-8-sig")
        else:
            content = source_file.read_text(encoding="utf-8-sig")

        reader = csv.DictReader(content.splitlines())
        if not {"Div", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HS", "AS"}.issubset(reader.fieldnames or []):
            raise ValueError("文件缺少英超比赛统计所需的列。")

        with connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(CURRENT_SEASON).fetchone()["id"] != season["id"]:
                raise ValueError("导入期间英超赛季已切换，请重新导入。")
            teams = connection.execute(
                "SELECT teams.* FROM teams JOIN standings ON standings.team_id = teams.id WHERE season_id = ?",
                (season["id"],),
            ).fetchall()
            team_ids = {name: team["id"] for team in teams for name in (team["name"], team["short_name"], team["code"])}
            matches = connection.execute(
                "SELECT * FROM matches WHERE season_id = ? AND status = 'FINISHED'", (season["id"],),
            ).fetchall()
            fixtures = {
                (match["kickoff_utc"][:10], match["home_team_id"], match["away_team_id"],
                 match["home_score"], match["away_score"]): match for match in matches
            }

            imported = set()
            skipped = 0
            for row in reader:
                if row["Div"] != "E0":
                    continue
                if not all(row.get(field) for field in ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG")):
                    skipped += 1
                    continue
                home, away = row["HomeTeam"], row["AwayTeam"]
                key = (
                    datetime.strptime(row["Date"], "%d/%m/%Y").date().isoformat(),
                    team_ids.get(TEAM_ALIASES.get(home, home)), team_ids.get(TEAM_ALIASES.get(away, away)),
                    int(row["FTHG"]), int(row["FTAG"]),
                )
                match = fixtures.get(key)
                if match is None:
                    skipped += 1
                    continue
                match_id = match["id"]
                if match_id in imported:
                    raise ValueError(f"比赛 {match_id} 在文件中重复。")
                stats = normalize_stats(row)
                if not any(value is not None for pair in stats.values() for value in pair):
                    skipped += 1
                    continue
                imported.add(match_id)
                connection.execute(
                    """
                    INSERT INTO lab_match_stats VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (match_id) DO UPDATE SET
                        kickoff_utc = excluded.kickoff_utc,
                        home_team_id = excluded.home_team_id, away_team_id = excluded.away_team_id,
                        home_score = excluded.home_score, away_score = excluded.away_score,
                        import_started_at = excluded.import_started_at, stats_json = excluded.stats_json
                    WHERE excluded.import_started_at > lab_match_stats.import_started_at
                    """,
                    (match_id, match["kickoff_utc"], *key[1:], started_at, json.dumps(stats)),
                )
            covered = connection.execute(
                f"SELECT COUNT(stats.match_id) FROM matches {MATCH_STATS_JOIN} WHERE matches.season_id = ?",
                (season["id"],),
            ).fetchone()[0]

    return (f"本次匹配 {len(imported)} 场英超比赛。已结束场次统计覆盖 {covered}/{len(matches)}。"
            f"跳过无法匹配或无统计的记录 {skipped} 条。")


def read_match_stats(database: Path, match_id: int) -> dict | None:
    if not 0 < match_id < 2**63:
        return None
    with closing(connect(database)) as connection:
        row = connection.execute(
            f"""
            SELECT matches.status, stats.stats_json FROM matches {MATCH_STATS_JOIN}
            WHERE matches.id = ? AND matches.season_id = ({CURRENT_SEASON})
            """,
            (match_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "status": row["status"],
        "stats": json.loads(row["stats_json"]) if row["stats_json"] else None,
        "source_url": SOURCE,
    }
