from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx

from .storage import DATABASE, ROOT, read_snapshot

MEDIA_BASE = "https://media.api-sports.io/football/teams/"
CREST_DIRECTORY = ROOT / "frontend" / "src" / "assets" / "crests"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# football-data.org team ID -> API-SPORTS team ID.
MEDIA_TEAM_IDS = {
    57: 42,     # Arsenal
    58: 66,     # Aston Villa
    61: 49,     # Chelsea
    62: 45,     # Everton
    63: 36,     # Fulham
    64: 40,     # Liverpool
    65: 50,     # Manchester City
    66: 33,     # Manchester United
    67: 34,     # Newcastle United
    71: 746,    # Sunderland
    73: 47,     # Tottenham Hotspur
    322: 64,    # Hull City
    341: 63,    # Leeds United
    349: 57,    # Ipswich Town
    351: 65,    # Nottingham Forest
    354: 52,    # Crystal Palace
    397: 51,    # Brighton & Hove Albion
    402: 55,    # Brentford
    1044: 35,   # Bournemouth
    1076: 1346,  # Coventry City
}


def save_crest(path: Path, content: bytes) -> None:
    temporary = NamedTemporaryFile(dir=path.parent, delete=False)
    temporary_path = Path(temporary.name)
    try:
        with temporary:
            temporary.write(content)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    snapshot = read_snapshot(DATABASE)
    if snapshot is None:
        print("请先同步英超赛季数据。")
        return 1

    CREST_DIRECTORY.mkdir(parents=True, exist_ok=True)
    teams = [row["team"] for row in snapshot["standings"]]
    missing = []
    with httpx.Client(base_url=MEDIA_BASE, timeout=12) as client:
        for team in teams:
            team_id = team["id"]
            path = CREST_DIRECTORY / f"{team_id}.png"
            if path.is_file():
                continue
            media_id = MEDIA_TEAM_IDS.get(team_id)
            if media_id is None:
                missing.append(team["name"])
                continue
            try:
                response = client.get(f"{media_id}.png")
                response.raise_for_status()
                if not response.content.startswith(PNG_SIGNATURE):
                    raise ValueError("expected a PNG image")
                save_crest(path, response.content)
            except (httpx.HTTPError, OSError, ValueError) as error:
                print(f"{team['name']}: {error}")
                missing.append(team["name"])

    print(f"已准备 {len(teams) - len(missing)}/{len(teams)} 张队徽。")
    if missing:
        print("暂无队徽：" + "、".join(missing))
    return int(bool(missing))


if __name__ == "__main__":
    raise SystemExit(main())
