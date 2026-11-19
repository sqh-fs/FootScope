# FootScope 性能验证

对 SQLite 在线备份的副本发压。记录数据哈希、代码版本、CPU、内存、实例数、驱动版本和缓存配置。同一数据分别启动缓存关闭与开启的实例，配合 Web 代理测试时再增加一组 Nginx 入口的结果。

```powershell
@'
from contextlib import closing
from pathlib import Path
import sqlite3

target = Path("data/perf/league.sqlite3")
target.parent.mkdir(parents=True, exist_ok=True)
source_uri = Path("data/footscope.sqlite3").resolve().as_uri() + "?mode=ro"
with closing(sqlite3.connect(source_uri, uri=True)) as source, closing(sqlite3.connect(target)) as backup:
    source.backup(backup)
    assert backup.execute("PRAGMA quick_check").fetchone() == ("ok",)
'@ | .\.venv\Scripts\python.exe -B -
```

准备数据副本时先停止使用该副本的验证实例。随后分别启动对照服务。

```powershell
.\.venv\Scripts\python.exe -m backend serve --database data/perf/league.sqlite3 --port 8010 --snapshot-cache-ttl 0
.\.venv\Scripts\python.exe -m backend serve --database data/perf/league.sqlite3 --port 8011
```

上面两个服务分别在独立终端运行。以下命令测试开启缓存的 30 请求/秒场景，调整端口复测关闭缓存的实例。

```powershell
$env:BASE_URL = 'http://127.0.0.1:8011'
$env:RPS = '30'
$env:DURATION = '15m'
k6 run --no-usage-report perf/league.js
```

可通过 `MODEL=light|medium|high` 选择负载模型，通过 `ONLINE=100|1000|10000` 推导默认到达率。显式设定的 `RPS` 优先。设 `MODE=sessions` 时切换为有思考时间的在线会话模型，此时以实际 RPS 为准。设 `ACCEPT_ENCODING=gzip` 测试压缩响应，清除该变量可复现默认请求头。运行前检查数据含球队、已结束和未结束比赛。脚本按公开数据契约验证 HTTP 状态和路由延迟阈值，要求负载发生器没有丢失迭代。

正式验收在目标主机及独立负载机上，按架构方案第 10 节预热、稳态重复三轮、测试数据库写入重叠与缓存冷启动。上线判断同时核对服务端 CPU、内存、错误、日志和回源情况。

## 2026-11-19 本机对照

Windows 同机回环 HTTP，Python 3.12.8，k6 2.4.0，单 API 进程，采用 k6 默认请求头。副本包含 20 支球队和 380 场比赛，SHA-256 为 `209cc7ebbf9298eceb6e8a80e5287e91286d07646043a9d5794ac863d77aba71`。以改造前的 `f6a92a4` 作为基线，交替测试基线和缓存候选，30 请求/秒各测一轮，100 请求/秒各测三轮，每轮 15 秒。

| 联赛接口 | 基线平均 | 候选平均 | 基线 P95 | 候选 P95 | 基线 P99 | 候选 P99 |
|---|---:|---:|---:|---:|---:|---:|
| 30 请求/秒 | 6.96 ms | 4.80 ms | 23.80 ms | 22.85 ms | 28.14 ms | 26.59 ms |
| 100 请求/秒，各指标取三轮中位数 | 4.48 ms | 2.72 ms | 11.75 ms | 11.86 ms | 19.43 ms | 20.18 ms |

各轮均通过脚本阈值，无失败请求和丢失迭代。100 请求/秒时平均延迟约降 39%，P95 与 P99 小幅波动，尾延迟收益待目标环境长测。额外逐一核对联赛、20 个球队和 380 个比赛响应，响应体完全一致。CSV 导入重放两次均覆盖 100 场，重复行导致的导入失败完整回滚。

本机 Nginx 通过配置检查及 HTTP 验证，检查范围包括静态首页、gzip、缓存命中及带 Authorization 或 Cookie 请求的缓存绕过。代理入口以 300 请求/秒运行 60 秒，共收到 18,002 次 HTTP 请求（包括启动时取样），无失败或丢失迭代，整体 P95 为 4.05 ms，联赛接口 P95 为 2.00 ms。访问日志中 10,082 次联赛请求有 10,079 次缓存命中。同速率指定 gzip 补测 30 秒，9,002 次 HTTP 请求全部成功，联赛接口 P95 为 3.00 ms，接收速率约 1.1 MB/s。

部署模板的正式 TLS、systemd 调度和异机恢复仍需目标 Linux 主机验收。
