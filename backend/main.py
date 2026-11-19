from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .lab import read_match_stats
from .storage import DATABASE, ROOT, initialize, read_snapshot, read_team

DIST = ROOT / "frontend" / "dist"


def create_app(database: Path = DATABASE) -> FastAPI:
    initialize(database)
    app = FastAPI(title="FootScope", version="0.1.0")
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/api/v1/competitions/PL")
    def premier_league() -> JSONResponse:
        snapshot = read_snapshot(database)
        if snapshot is None:
            return JSONResponse(
                {"error": {"code": "NO_DATA", "message": "请先同步英超数据。"}},
                status_code=503,
                headers={"Cache-Control": "no-store"},
            )
        return JSONResponse(snapshot, headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/teams/{team_id}")
    def league_team(team_id: int) -> JSONResponse:
        result = read_team(database, team_id)
        if result is None:
            raise HTTPException(status_code=404, detail="当前赛季没有这支球队。")
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    @app.get("/api/v1/lab/matches/{match_id}")
    def lab_match(match_id: int) -> JSONResponse:
        result = read_match_stats(database, match_id)
        if result is None:
            raise HTTPException(status_code=404, detail="当前英超赛季没有这场比赛。")
        return JSONResponse(result, headers={"Cache-Control": "no-store"})

    if (DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    def home() -> FileResponse | JSONResponse:
        index = DIST / "index.html"
        if not index.is_file():
            return JSONResponse({"message": "请先在 frontend 目录运行 npm run build。"}, status_code=503)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app
