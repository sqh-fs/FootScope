from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .storage import DATABASE, ROOT, read_snapshot

DIST = ROOT / "frontend" / "dist"


def create_app(database: Path = DATABASE) -> FastAPI:
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

    if (DIST / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    def home() -> FileResponse | JSONResponse:
        index = DIST / "index.html"
        if not index.is_file():
            return JSONResponse({"message": "请先在 frontend 目录运行 npm run build。"}, status_code=503)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app
