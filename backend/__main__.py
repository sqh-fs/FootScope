import argparse
import sqlite3
import sys
from pathlib import Path

from .football_data import SyncError, sync
from .storage import DATABASE


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m backend")
    parser.add_argument("command", choices=("sync", "serve"))
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.command == "sync":
        try:
            print(sync(args.database))
        except (SyncError, sqlite3.Error, OSError) as error:
            message = str(error) if isinstance(error, SyncError) else "无法写入本地数据库。"
            print(f"同步失败：{message}", file=sys.stderr)
            return 1
        return 0

    import uvicorn

    from .main import create_app

    uvicorn.run(create_app(args.database), host="127.0.0.1", port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
