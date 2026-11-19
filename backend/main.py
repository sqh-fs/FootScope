import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from time import monotonic

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .lab import read_match_stats
from .storage import DATABASE, ROOT, connect, initialize, read_snapshot, read_team

DIST = ROOT / "frontend" / "dist"


def create_app(database: Path = DATABASE, *, snapshot_cache_ttl: int = 30) -> FastAPI:
    initialize(database)
    app = FastAPI(title="FootScope", version="0.1.0")
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    snapshot_lock = Lock()
    snapshot_body: bytes | None = None
    snapshot_expires_at = 0.0

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/ready")
    def readiness() -> JSONResponse:
        available = False
        try:
            if database.is_file():
                with closing(connect(database, timeout=0.2)) as connection:
                    available = connection.execute("SELECT 1 FROM seasons LIMIT 1").fetchone() is not None
        except (OSError, sqlite3.Error):
            pass
        return JSONResponse(
            {"status": "ready" if available else "unavailable"},
            status_code=200 if available else 503,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/v1/competitions/PL")
    def premier_league() -> Response:
        nonlocal snapshot_body, snapshot_expires_at
        if snapshot_cache_ttl > 0:
            with snapshot_lock:
                now = monotonic()
                if snapshot_body is None or now >= snapshot_expires_at:
                    snapshot = read_snapshot(database)
                    if snapshot is None:
                        snapshot_body = None
                    else:
                        ttl = float(snapshot_cache_ttl)
                        if not snapshot["meta"]["is_stale"]:
                            synced_at = datetime.fromisoformat(snapshot["meta"]["last_synced_at"])
                            until_stale = synced_at + timedelta(hours=24) - datetime.now(UTC)
                            ttl = max(0.0, min(ttl, until_stale.total_seconds()))
                        snapshot_body = JSONResponse(snapshot).body
                        snapshot_expires_at = now + ttl
                if snapshot_body is not None:
                    remaining = max(0, int(snapshot_expires_at - monotonic()))
                    return Response(
                        snapshot_body,
                        media_type="application/json",
                        headers={"Cache-Control": f"public, max-age=0, s-maxage={remaining}"},
                    )
        else:
            snapshot = read_snapshot(database)
            if snapshot is not None:
                return JSONResponse(snapshot, headers={"Cache-Control": "no-store"})

        return JSONResponse(
            {"error": {"code": "NO_DATA", "message": "请先同步英超数据。"}},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )

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
