# deepseeksearch 对抗式审查报告与修复计划

## Context

用户要求对 `go_projects/deepseeksearch` 做对抗式审查。范围：全项目源码（三个 persona：破坏者/新人/安全审计员），重点为未提交改动（`main.go`、`gui.go` 重排序 + 新增 `launch_args.go` 的单实例静默唤醒逻辑）。已核验 Wails v3.0.0 模块缓存源码：`single_instance.go` 的 `notifyFirstInstance()` 传 `os.Args` 全量数组（含 argv[0]），故 `IsSilentStart(data.Args)` 跳过第 0 位的解析**正确**，该高风险疑点排除。整体设计良好（绑定回环、WAL、重试缓存防扣费），但存在若干正确性与安全收缩空间。

## 审查结论

**Verdict: CONCERNS**（无 CRITICAL，多项 WARNING；单机个人工具，风险可控）

### WARNING（建议修复）

| # | 发现 | 抓手 | 位置 |
|---|------|------|------|
| W1 | **时间戳双时区撕裂**：`created_at/fetched_at` 由 SQLite `CURRENT_TIMESTAMP` 写 UTC 墙钟，但缓存 cutoff 用 `time.Now()`（本地时区）格式化字符串比较 → UTC+8 机器上 24h 缓存窗口漂移成约 16~32h；回读 `time.Parse` 无时区 → 前端/CLI 显示的"检索于/缓存于"是 UTC 墙钟，差 8 小时 | Saboteur | `internal/storage/sqlite.go:230,253,321,338` |
| W2 | **吞错导致静默错效**：`GetCachedSearch/AddSearchHistory/AddFetchHistory` 调用处 `if cached, _ :=` / `_, _ =` 全吞——DB 故障/锁超时 → 静默 miss 直接打**付费 API**（恰是"0 元消耗"设计要防的）；`cfg, _ := store.GetConfig()` → 误导性"未配置 Key"报错 | Saboteur | `internal/api/server.go:139,179,203,235`、`cmd/deepseeksearch/cli.go:120,158,184,237,265,286,321` |
| W3 | **缓存条数契约错位**：`WHERE count >= ?` 允许请求 10 条命中历史 50 条记录，且返回完整 `ResultsJSON`（50 条）→ 实际结果数 ≠ 请求条数 | Saboteur | `internal/storage/sqlite.go:235` |
| W4 | **HTTP 响应无大小上限**：`io.ReadAll(resp.Body)` 无界读取；BaseURL 用户可配任意代理 → GB 级响应可 OOM 崩溃 | Saboteur | `internal/deepseek/client.go:133` |
| W5 | **localhost API key 双路径暴露**：(a) 无 Host 校验中间件 → DNS rebinding 后恶意页面以"同源"身份 `GET /api/config` 拿明文 key、`POST /api/config` 改写 BaseURL 劫持请求；(b) key 明文存 SQLite `app_settings`（备份/同步盘可读） | Security | `internal/api/server.go:279`、`internal/storage/sqlite.go:173` |
| W6 | **markdown 链接 href 无 scheme 白名单**：`formatInline` 正则生成 `<a href="$2">`，`[](javascript:...)` 直通（外部网页正文是不可信输入）；`fetchSourceLink.href = data.url` 同理；现代浏览器对 `javascript:` 顶层导航有阻断故实际可利用性低，但纵深防御缺失 | Security | `internal/web/assets/app.js:718,499` |
| W7 | **零测试回归缺口（双抓升级）**：本次 diff 引入新公共函数 `IsSilentStart`（静默唤醒语义，注释明确"单一事实源、两处共用"）与 `OnSecondInstanceLaunch` 新守卫分支，无任何回归测试——正是"自启炸窗"这类注释描述要防的 bug 最容易回归的位置 | Saboteur + New Hire | `internal/app/launch_args.go` |

### NOTE（可选）

| # | 发现 | 抓手 |
|---|------|------|
| N1 | `GetFetchRecordByID` 全仓无调用方（Grep 确认仅定义处） → 死代码 | 新人 |
| N2 | `/api/meta` 的 `dataDir/dbPath` 字段前端从未使用，却向外暴露本机路径 | 新人 |
| N3 | `dbTimeLayout = "2006-01-02 15:04:05"` 字面量在 sqlite.go 内重复 6 处，无常量 | 新人 |
| N4 | `SearchResultItem.Authority` 用 `interface{}`，若为对象则前端渲染出 `Lv.map[...]` | 新人 |
| N5 | `http.Serve` 无 graceful shutdown：`quit()` 里 `store.Close()` 时在途请求可能半写 | 破坏者 |
| N6 | `handleSearch` 把所有失败（含 5xx/超时/网络错）统一映射 HTTP 400，语义湮没 | 新人 |
| N7 | `CLI --hidden/--tray` 是隐形入口（printUsage 中未出现），`--tray` 路径直接服务 WebUI，语义与通道文档不一致 | 新人 |
| N8 | index.html 无 CSP meta（纵深防御） | 安全审计员 |
| N9 | `go build` 产物 bin/、`__pycache__/`、`.syso` 均被 `.gitignore` 覆盖，未污染仓库 ✓ | 通过项 |

### 正面确认（非发现）
- `IsSilentStart` 设计与 Wails v3.0.0 `os.Args` 语义吻合（已读模块缓存源码验证）
- `LaunchGUI` 重排序（先单实例锁、后重资源）逻辑正确，注释清楚
- 委托单实例抢锁失败路径 `store.Close()` 已处理
- `http.Client` 45s 超时 + 重试退避 + 429/502/503 处理符合意图

## 修复计划（需用户批准范围）

### P1 时间统一（修 W1 + N3）
- `sqlite.go` 新增 `dbTimeLayout` 常量 + `nowDB()` / `parseDBTime()` helper
- cutoff 侧：`time.Now().UTC().Add(-maxAge).Format(dbTimeLayout)`
- 回读侧：`time.ParseInLocation(layout, s, time.UTC)`；对外展示前统一 `.Local()`
- 兼容历史数据（同为 UTC 墙钟，无需迁移）

### P2 缓存条数截断（修 W3）
- `GetCachedSearch` 命中侧 + `server.go`/`cli.go` 缓存返回侧：`items = items[:min(count, len(items))]`，加注释说明"宽缓存截断"策略

### P3 错误不再静默（修 W2）
- 所有 `if cached, _ :=` 改为 err 非空时 `logf`/stderr 警告后继续 miss
- `_, _ = store.Add...` 改为失败时 `logf`

### P4 响应大小上限（修 W4）
- `client.go`：`io.LimitReader(resp.Body, 10<<20)`（10MB 上限，need_content 50 条足以容纳）

### P5 Host 校验中间件（修 W5a）
- `server.go` `Handler()` 增加中间件：`net.SplitHostPort(r.Host)` 后 host 仅允许 `127.0.0.1`/`localhost`/`::1`，否则 403

### P6 前端 href scheme 白名单（修 W6）
- `app.js` 加 `safeUrl(u)`：非 `http(s)://` 一律返回 `#`；套用到 `formatInline` 链接、结果卡 href/data-url、`fetchSourceLink.href`

### P7 launch_args 回归测试（修 W7）
- `internal/app/launch_args_test.go` 表驱动：i==0 含 `--hidden` 的 exe 路径不误判、大小写混合、空白字符串、命中/不命中

### 可选清理（批准则一并做）
- N1：删除 `GetFetchRecordByID`
- N2：`/api/meta` 移除 `dataDir/dbPath`
- N4：`Authority` 定型为 `float64`
- 其余 N5-N8 记录到技术债，不本次处理

### 提交序列（用户已确认：修复前先提交）

1. **先提交现存未提交改动**（与修复内容隔离，保证修复 diff 干净）：
   - 范围仅 `cmd/deepseeksearch/main.go`、`internal/app/gui.go`、`internal/app/launch_args.go`
   - 消息：`deepseeksearch:fix: 静默二次启动保持托盘驻留`，结尾附 Co-Authored-By: Claude Code <noreply@anthropic.com>
2. **实施 P1-P6 + W7 测试**，全部通过验证后单独提交：
   - 消息：`deepseeksearch:fix: 修复时区撕裂/吞错与 localhost 配置暴露等审查发现`
3. **沉淀正式计划文档**（"sh-plan 落盘强制路由"）：新建 `docs/projects/go_projects/deepseeksearch/plans/01-对抗式审查修复.md` 后**立即单独提交**（`docs(plans): ...`，Body 用 `- ` 列表），严禁与代码混提；父仓文档改动由父仓提交，与子仓提交严格分离

### 约束
- 修复一律在 `go_projects/deepseeksearch` 项目目录内（子仓单体），不跨项目改动
- `.claude/plans/` 本文件为会话暂存工件，不入库

## 验证

1. `go test ./...`（项目目录下，含新增 launch_args/storage 用例）全绿
2. `python scripts/build.py` 构建双通道产物成功
3. W1 视觉验证：CLI 缓存命中的"检索于"时间与 SQLite 内 created_at（UTC）换算本地时间一致
4. P5 验证：`curl http://127.0.0.1:<port>/api/meta` 200；`curl -H "Host: evil.com" ...` 返回 403
5. P6 验证：fetch 含 `[](javascript:alert(1))` 的 markdown，排版视图中链接 href 为 `#`
