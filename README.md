# FootScope

本地运行的英超比赛中心，包含当季积分榜、按轮次浏览的赛程与赛果，以及赛季进度和场均进球。排名和积分来自上游积分榜。场均进球按有完整比分的已结束或已判定比赛计算，开球时间按浏览器所在时区显示。

## 在 Windows 上启动

在项目根目录运行以下命令，打开 [本地比赛中心](http://127.0.0.1:8000/)。按 `Ctrl+C` 停止前台服务。

```powershell
.\.venv\Scripts\python.exe -m backend serve
```

## 首次安装

使用 Python 3.12 和 Node.js 24。若 Python 3.12 安装在其他路径，替换第一条命令中的路径。保留已经填写的 `.env`，新环境可复制 `.env.example` 并在本地填写 `FOOTBALL_DATA_API_KEY`。

```powershell
& 'C:\Python312\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m backend sync
```

## 更新英超数据

页面可见时每分钟读取一次本地缓存，切回标签页时也会刷新。右上角的刷新按钮可立即读取缓存。上游失败时，SQLite 继续保存上一次成功同步的积分榜与赛程。缓存超过 24 小时后，页面会提示数据可能有延迟。

### Windows 自动同步

在项目根目录注册 `FootScope Data Sync`。当前 Windows 用户登录且电脑唤醒时，任务每 2 小时更新一次 SQLite 缓存，即使网站服务处于关闭状态也可以更新。电脑恢复可用后，任务计划程序可补跑错过的同步。结果写入 `data/sync.log`，日志时间为 UTC。

```powershell
.\scripts\register-sync-task.ps1
Start-ScheduledTask -TaskName 'FootScope Data Sync' -TaskPath '\'
Get-ScheduledTaskInfo -TaskName 'FootScope Data Sync' -TaskPath '\'
Get-Content -LiteralPath 'data\sync.log' -Tail 10 -Encoding UTF8
```

要暂停自动同步，运行 `Disable-ScheduledTask -TaskName 'FootScope Data Sync' -TaskPath '\'`。恢复时运行同名的 `Enable-ScheduledTask` 命令。

### 手动同步

```powershell
.\.venv\Scripts\python.exe -m backend sync
```

数据库位于 `data/footscope.sqlite3`。服务默认监听 `127.0.0.1:8000`。

Football data provided by the Football-Data.org API.

## 战术实验室与球队阵容

在积分榜、赛程或「战术实验室 → 英超球队」点击球队，即可查看本赛季球员名单，按位置筛选或搜索球员。名单来自 football-data.org，随同步任务每日更新，有新赛季时会重新同步。球员姓名使用数据源的原文。

「战术实验室 → 本赛季英超」按轮次和比赛查看当前赛季的全部赛程。已导入统计的比赛可以比较双方的 xG、射门、射正率、半场进球、角球、犯规和红黄牌。射正率为射正次数除以射门次数，射门次数为零时显示「—」。

先同步英超赛程，再运行以下命令从 [Football-Data.co.uk](https://football-data.co.uk/englandm.php) 下载和导入本赛季已结束比赛的统计。也可用 `--file <CSV 路径>` 导入本地下载的英超 CSV。导入按比赛日期、主客队和全场比分核对赛程，处理结果会显示已结束比赛的统计覆盖数。赛程随 `sync` 更新，比赛统计使用 `import-lab` 更新。CSV 提供整场统计，逐次射门和传球坐标需由事件数据源补充。

```powershell
.\.venv\Scripts\python.exe -m backend import-lab
```

## 球队队徽

队徽来自 [API-SPORTS 图片 CDN](https://www.api-football.com/documentation-v3#tag/Logos-Images)，按球队 ID 缓存到本地 `frontend/src/assets/crests/`，用于本地版的球队识别。缺少图片时显示球队缩写。新增球队时，在 `backend/team_crests.py` 补上对应的 API-SPORTS 球队 ID，再下载并构建前端。

```powershell
.\.venv\Scripts\python.exe -m backend.team_crests
npm --prefix frontend run build
```

公开发布前请核对各队徽的展示权限。参见 [API-SPORTS 图片条款](https://www.api-football.com/terms)。

## 首页球场图

[`stadium.jpg`](frontend/src/assets/stadium.jpg) 由内置 ImageGen 生成，使用以下提示词。

> Generate a wide photorealistic editorial banner photo for a modern football scores dashboard. View from high in the stands of a fictional English football stadium at blue hour, floodlights and tiny crowd in distant tiers, tidy vivid emerald grass with freshly painted touchline, center circle and grass mowing stripes seen on a strong diagonal perspective. The brightest field and stadium architecture are on the right, left fades naturally into deep navy shadow and will be overlaid with website headline. Moody steel-blue and green colors, realistic architecture, clean broadcast sports photography, atmospheric subtle haze. Wide landscape format, the field remains recognizable when cropped into a very wide horizontal banner. Image only, no text, no logo, no watermark, no signage, no close-up people.
