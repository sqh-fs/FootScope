# Linux 单机部署

模板以 systemd、同机 SQLite 和 Nginx 为起点。目录采用 `/opt/footscope`，系统用户采用 `footscope`。对外入口使用正式域名和 TLS 证书，API 只监听本机回环地址。

1. 部署项目代码，在 `/opt/footscope/.venv` 中安装后端依赖，运行 `npm --prefix frontend ci` 和 `npm --prefix frontend run build`，确认 `frontend/dist/index.html` 存在。给 Nginx 用户读取构建产物的权限。
2. 创建 `footscope` 系统用户，将 `FOOTBALL_DATA_API_KEY` 放入权限为 `0600` 的 `/etc/footscope/sync.env`。如果从已有实例迁移，用 SQLite 在线备份生成副本，将校验通过的副本安装到 `/var/lib/footscope/footscope.sqlite3`，目录和文件归 `footscope` 所有。
3. 将 [systemd 单元](systemd/) 安装到 `/etc/systemd/system/`。旧机器负责同一站点时，先关闭旧同步触发器，再启用新计时器。首次启动顺序如下。

   ```sh
   sudo systemctl daemon-reload
   sudo systemctl start footscope-sync.service
   sudo systemctl enable --now footscope-api@8000.service
   curl --fail http://127.0.0.1:8000/ready
   sudo systemctl enable --now footscope-sync.timer
   ```

4. 如果需要补充战术实验室数据，用 `footscope` 用户运行 `backend import-lab --database /var/lib/footscope/footscope.sqlite3`。统计源和赛程同步采用各自的更新节奏。
5. 将 [Nginx 模板](nginx/footscope.conf) 放入 Nginx 的 `http` 配置包含目录，替换域名和证书路径。保证 Nginx 用户可写 `/var/cache/nginx/footscope`。创建站点后先执行 `nginx -t` 再 reload。访问 HTTPS 首页并复查三个 API，查看 `X-Cache-Status` 是否从 `MISS` 变为 `HIT`。

## 备份与切换

使用 SQLite 自带的在线备份命令，输出到新文件并将校验通过的副本保存至异机存储。以下命令假定 `backup_dir` 指向已创建的备份目录。

```sh
backup_file="$backup_dir/footscope-$(date -u +%Y%m%dT%H%M%SZ).sqlite3"
sqlite3 -readonly /var/lib/footscope/footscope.sqlite3 ".backup '$backup_file'"
sqlite3 -readonly "$backup_file" 'PRAGMA quick_check;'
```

恢复演练时先对副本核对赛季及 `matches`、`lab_match_stats` 行数。正式恢复时停 API、同步计时器与当前同步任务，等手工导入退出，保留损坏库及其日志文件，再把通过校验的备份放入空的数据库路径。检查 `/ready` 和三个 API 后恢复流量与计时器。

如需回滚响应缓存，在 Nginx 中关闭该 location 的 `proxy_cache`，并在 API 服务参数中设置 `--snapshot-cache-ttl 0`。版本回滚时保留旧前端哈希资源，启动旧服务并通过 `/ready` 后切回 Nginx 上游。各版本共用同一个 SQLite 路径，同一时段只启用一个同步计时器。
