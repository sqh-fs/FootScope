import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

from .football_data import SyncError, sync
from .storage import DATABASE


def run_sync(database: Path, log_file: Path | None) -> int:
    try:
        message = sync(database)
        exit_code = 0
    except (SyncError, sqlite3.Error, OSError) as error:
        reason = str(error) if isinstance(error, SyncError) else "无法写入本地数据库。"
        message = f"同步失败：{reason}"
        exit_code = 1

    print(message, file=sys.stderr if exit_code else sys.stdout)
    if log_file is not None:
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("a", encoding="utf-8") as log:
                timestamp = datetime.now(UTC).isoformat(timespec="seconds")
                log.write(f"{timestamp} {message}\n")
        except OSError:
            print("无法写入同步日志。", file=sys.stderr)
            return 1
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m backend")
    parser.add_argument("command", choices=("sync", "import-lab", "serve"))
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--snapshot-cache-ttl", type=int, default=30, help="League response cache lifetime in seconds (0 disables it).")
    parser.add_argument("--log-file", type=Path, help="Append the sync result to this file.")
    parser.add_argument("--file", type=Path, help="Import a local Premier League stats CSV.")
    args = parser.parse_args()

    if args.command == "sync":
        return run_sync(args.database, args.log_file)

    if args.command == "import-lab":
        from httpx import HTTPError

        from .lab import import_match_stats

        try:
            print(import_match_stats(args.database, args.file))
        except (HTTPError, ValueError, OSError, sqlite3.Error) as error:
            print(f"英超比赛统计导入失败：{error}", file=sys.stderr)
            return 1
        return 0

    import uvicorn

    from .main import create_app

    if not 0 <= args.snapshot_cache_ttl <= 30:
        parser.error("--snapshot-cache-ttl must be between 0 and 30")
    uvicorn.run(create_app(args.database, snapshot_cache_ttl=args.snapshot_cache_ttl), host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
