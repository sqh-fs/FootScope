import os
import sqlite3
import time
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

from .storage import ROOT, rosters_are_fresh, save_rosters, save_snapshot

API_BASE = "https://api.football-data.org/v4/competitions/PL/"
TOKEN_NAME = "FOOTBALL_DATA_API_KEY"


class SyncError(Exception):
    """A sync failed before updating the saved snapshot."""


def get_resource(client: httpx.Client, path: str) -> dict:
    for attempt in range(3):
        try:
            response = client.get(path)
        except httpx.RequestError:
            if attempt == 2:
                raise SyncError(f"无法连接 football-data.org（{path}）") from None
            time.sleep(2 ** attempt)
            continue

        status = response.status_code
        if status == 200:
            try:
                return response.json()
            except ValueError:
                raise SyncError(f"上游返回了无效 JSON（{path}）") from None
        if status >= 500 and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        if status == 429:
            raise SyncError("上游请求超出配额。请稍后重新同步。")
        raise SyncError(f"上游请求失败（{path}，HTTP {status}）")
    raise AssertionError("The retry loop must return or raise")


def normalize(
    standings_data: dict, matches_data: dict, started_at: datetime,
) -> tuple[dict, list[dict], list[dict], list[dict]]:
    upstream_season = standings_data["season"]
    season = {
        "id": upstream_season["id"],
        "start_date": date.fromisoformat(upstream_season["startDate"]).isoformat(),
        "end_date": date.fromisoformat(upstream_season["endDate"]).isoformat(),
        "current_matchday": upstream_season.get("currentMatchday"),
        "sync_started_at": started_at.isoformat(),
        "synced_at": datetime.now(UTC).isoformat(),
    }
    teams: dict[int, dict] = {}

    def team_id(team: dict) -> int:
        identifier = team["id"]
        name = team["name"]
        teams[identifier] = {
            "id": identifier,
            "name": name,
            "short_name": team.get("shortName") or name,
            "code": team.get("tla") or name[:3].upper(),
        }
        return identifier

    total_table = next(group["table"] for group in standings_data["standings"]
                       if group["type"] == "TOTAL")
    standings = [{
        "season_id": season["id"],
        "team_id": team_id(row["team"]),
        "position": row["position"],
        "played": row["playedGames"],
        "won": row["won"],
        "drawn": row["draw"],
        "lost": row["lost"],
        "goals_for": row["goalsFor"],
        "goals_against": row["goalsAgainst"],
        "goal_difference": row["goalDifference"],
        "points": row["points"],
    } for row in total_table]

    matches = []
    for match in matches_data["matches"]:
        if match["season"]["id"] != season["id"]:
            raise SyncError("赛程与积分榜来自不同赛季，请稍后重新同步。")
        full_time = (match.get("score") or {}).get("fullTime") or {}
        kickoff = datetime.fromisoformat(match["utcDate"]).astimezone(UTC)
        matches.append({
            "id": match["id"],
            "season_id": season["id"],
            "matchday": match.get("matchday"),
            "kickoff_utc": kickoff.isoformat(),
            "status": match.get("status") or "UNKNOWN",
            "home_team_id": team_id(match["homeTeam"]),
            "away_team_id": team_id(match["awayTeam"]),
            "home_score": full_time.get("home"),
            "away_score": full_time.get("away"),
        })

    if not standings or not matches:
        raise SyncError("上游积分榜或赛程为空，保留上次同步的数据。")
    if len({match["id"] for match in matches}) != len(matches):
        raise SyncError("上游赛程包含重复比赛，保留上次同步的数据。")
    return season, list(teams.values()), standings, matches


def normalize_rosters(payload: dict, season_id: int, team_ids: set[int]) -> dict:
    if payload["season"]["id"] != season_id:
        raise SyncError("球队名单与积分榜来自不同赛季。")
    rosters = {}
    for team in payload["teams"]:
        players = [{
            "id": player["id"],
            "name": player["name"],
            "position": player.get("position"),
            "nationality": player.get("nationality"),
        } for player in team.get("squad") or []]
        if not players or len({player["id"] for player in players}) != len(players):
            raise SyncError("上游球队名单不完整。")
        rosters[team["id"]] = {
            "players": players,
            "coach": (team.get("coach") or {}).get("name"),
            "venue": team.get("venue"),
        }
    if rosters.keys() != team_ids:
        raise SyncError("上游球队名单与当前联赛球队不一致。")
    return rosters


def sync(path: Path) -> str:
    token = os.environ.get(TOKEN_NAME) or dotenv_values(ROOT / ".env").get(TOKEN_NAME)
    if not token or not token.strip():
        raise SyncError(f"请在本地 .env 中填写 {TOKEN_NAME}。")

    started_at = datetime.now(UTC)
    with httpx.Client(
        base_url=API_BASE,
        headers={"X-Auth-Token": token.strip()},
        timeout=15,
    ) as client:
        standings_data = get_resource(client, "standings")
        matches_data = get_resource(client, "matches")

        try:
            season, teams, standings, matches = normalize(standings_data, matches_data, started_at)
        except (KeyError, ValueError, TypeError, StopIteration, AttributeError):
            raise SyncError("上游数据格式有变化，保留上次同步的数据。") from None

        if not save_snapshot(path, season, teams, standings, matches):
            return "已有更新的数据，本次同步未覆盖缓存。"

        message = f"同步成功：{len(standings)} 支球队，{len(matches)} 场比赛。"
        season_id = season["id"]
        try:
            if rosters_are_fresh(path, season_id):
                return message
            team_ids = {row["team_id"] for row in standings}
            rosters = normalize_rosters(get_resource(client, "teams"), season_id, team_ids)
            save_rosters(path, season_id, started_at, rosters)
        except SyncError as error:
            return f"{message}球队名单同步失败：{error}"
        except (KeyError, ValueError, TypeError, AttributeError, sqlite3.Error):
            return f"{message}球队名单更新失败，保留已缓存的名单。"

    return f"{message}球员名单已更新，共 {sum(len(team['players']) for team in rosters.values())} 条球员记录。"
