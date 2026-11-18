import json
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

SOURCE = "https://github.com/hudl/open-data"
RAW = "https://raw.githubusercontent.com/hudl/open-data/master/"
MATCH_ID = 3869685
LOGO_RESOURCE = "img/SB%20-%20Icon%20Lockup%20-%20Colour%20positive.png"


def lab_cache(database: Path) -> Path:
    return database.with_suffix(".lab.json")


def lab_logo(database: Path) -> Path:
    return database.with_suffix(".statsbomb.png")


def write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(dir=path.parent, delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(content)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def normalize_match(match: dict, squads: list, events: list) -> dict:
    starters = {event["team"]["id"]: event["tactics"] for event in events
                if event["type"]["name"] == "Starting XI"}
    teams = []
    for side in ("home", "away"):
        team_id = match[f"{side}_team"][f"{side}_team_id"]
        match_squad = next(team for team in squads if team["team_id"] == team_id)
        initial = starters[team_id]
        positions = {entry["player"]["id"]: entry["position"]["name"] for entry in initial["lineup"]}
        players = []
        for player in match_squad["lineup"]:
            player_id = player["player_id"]
            initial_position = (player.get("positions") or [{}])[0].get("position")
            players.append({
                "id": player_id,
                "name": player.get("player_nickname") or player["player_name"],
                "number": player["jersey_number"],
                "position": positions.get(player_id, initial_position),
                "started": player_id in positions,
                "appeared": bool(player.get("positions")) or player_id in positions,
            })
        if sum(player["started"] for player in players) != 11:
            raise ValueError("The starting lineup is incomplete.")
        teams.append({
            "id": team_id,
            "name": match_squad["team_name"],
            "score": match[f"{side}_score"],
            "formation": "-".join(str(initial["formation"])),
            "players": sorted(players, key=lambda player: player["number"]),
        })

    shots = []
    shootout = Counter()
    for event in events:
        if event["type"]["name"] != "Shot":
            continue
        outcome = event["shot"]["outcome"]["name"]
        team_id = event["team"]["id"]
        if event["period"] == 5:
            if outcome == "Goal":
                shootout[team_id] += 1
            continue
        x, y, *_ = event["location"]
        if not (0 <= x <= 120 and 0 <= y <= 80):
            raise ValueError("A shot location is outside the StatsBomb pitch.")
        shots.append({
            "id": event["id"], "team_id": team_id, "player": event["player"]["name"],
            "x": x, "y": y, "xg": event["shot"].get("statsbomb_xg"),
            "minute": event["minute"], "second": event["second"], "period": event["period"],
            "outcome": outcome,
        })
    if not shots:
        raise ValueError("The match has no shot data.")

    return {
        "id": match["match_id"],
        "date": match["match_date"],
        "venue": (match.get("stadium") or {}).get("name"),
        "teams": teams,
        "shootout": [shootout[team["id"]] for team in teams],
        "shots": shots,
        "source_url": SOURCE,
    }


def import_match(database: Path) -> dict:
    with httpx.Client(base_url=RAW, timeout=25) as client:
        def fetch(resource: str) -> httpx.Response:
            response = client.get(resource)
            response.raise_for_status()
            return response

        matches = fetch("data/matches/43/106.json").json()
        match = next(match for match in matches if match["match_id"] == MATCH_ID)
        squads = fetch(f"data/lineups/{MATCH_ID}.json").json()
        events = fetch(f"data/events/{MATCH_ID}.json").json()
        logo = fetch(LOGO_RESOURCE).content
    result = normalize_match(match, squads, events)
    if not logo.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The StatsBomb logo is not a valid PNG.")
    write_file(lab_logo(database), logo)
    write_file(lab_cache(database), json.dumps(result, ensure_ascii=False).encode("utf-8"))
    return result
