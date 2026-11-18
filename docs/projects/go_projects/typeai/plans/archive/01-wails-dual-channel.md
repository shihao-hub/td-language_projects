# typeai 改造为 Wails 双通道桌面应用

## 目标

按 `sh-go-wails-desktop` 标准把 `go_projects/typeai` 从纯 TUI 工具改造为双通道产物，并归档独立外壳项目 `go_projects/typeai-gui`。

- `typeai-gui.exe`：双击只开桌面窗口，窗口内是原生 WebUI 聊天工作台。
- `typeai-cli.exe`：保留原 TUI 与管理命令，并新增 `serve` 托管同一 WebUI。
- GUI 与 CLI `serve` 共用同一 `internal/api.Handler()`，业务通信只走 HTTP/SSE。
- dev / release 在产物名、版本、数据目录、单实例 ID、图标五个维度隔离。

## 架构

```text
cmd/typeai/main.go      //go:build !cli   GUI 壳（忽略子命令，--hidden 静默托盘）
cmd/typeai/cli.go       //go:build cli    TUI / config / schema / version / serve
internal/buildinfo      版本与通道（-X 注入）
internal/appdata        dev/prod 数据目录 + 旧数据一次性迁移（不依赖 Wails）
internal/api            REST + SSE，GUI 与 serve 共用 Handler()
internal/web            //go:embed 静态 WebUI
internal/app            Wails 托盘 / 单实例 / 窗口几何 / 自启 / 日志 / 图标
internal/service        现有对话业务（加锁保证 HTTP 并发安全）
internal/tui            现有 TUI（CLI 通道保留）
scripts/build.py        双通道构建（GUI + Console 各一产物）
scripts/render_icon.py  专属图标（同时生成 dev 地鼠资产）
winres/{gui,cli}.json   PE VERSIONINFO + manifest + 图标模板
```

数据目录：`%APPDATA%\language_projects\typeai\{dev,prod}`（回退 `~/.language_projects/typeai/<通道>`）。首次启动把旧 `%APPDATA%\language_projects\typeai\config.json` 与 `sessions/` 复制到当前通道，旧文件保留。

## HTTP 契约

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | WebUI 单页 |
| GET | `/api/state` | 配置（密钥脱敏）、会话快照、分支树、流状态 |
| POST | `/api/chat` | 发送消息，返回 `text/event-stream`（delta/done/error） |
| POST | `/api/chat/cancel` | 取消当前流 |
| POST | `/api/branch/fork` | 在指定 assistant 消息后创建子分支 |
| POST | `/api/branch/switch` | 切换激活分支 |
| POST | `/api/branch/rename` | 重命名分支 |
| POST | `/api/branch/delete` | 删除分支（根/有子分支时拒绝） |
| GET | `/api/sessions` | 持久化会话摘要 |
| POST | `/api/sessions/resume` | 恢复指定会话 |
| POST | `/api/images` | 上传图片（base64），落临时目录并返回元数据 |
| GET | `/api/image?path=` | 读取会话内图片用于预览 |
| GET/PUT | `/api/config` | 读取/更新配置 |
| GET | `/api/version` | 版本与通道 |

同一时刻只允许一个进行中的流；流式期间分支切换、重命名、查看均可用。

## WebUI 功能（首批）

- 会话列表与恢复、新建会话。
- 分支 Tab：切换、fork、重命名、删除；进行中分支标记。
- 消息流：Markdown、thinking 折叠、超长文本折叠、图片预览。
- 输入：多行、Enter 发送 / Shift+Enter 换行、图片选择与粘贴、发送/取消。
- 配置面板：base_url、api_key（只写不回显）、model。
- 状态栏与错误条；窗口几何记忆；托盘（打开/浏览器打开/自启/退出）。

## 任务分解

- [x] Task 1：`internal/buildinfo`、`internal/appdata`（含旧数据迁移）。
- [x] Task 2：`internal/service.Chat` 并发保护与只读快照。
- [x] Task 3：`internal/api`（REST + SSE）与 `internal/web` 静态资源。
- [x] Task 4：`internal/app` Wails 壳（托盘、单实例、窗口几何、自启、日志、图标）。
- [x] Task 5：GUI/CLI 双入口与 `serve`；数据目录统一走 `appdata`。
- [x] Task 6：构建流水线（build.py、render_icon.py、winres、manifest、info.json、gitignore）。
- [x] Task 7：README 更新，`go_projects/typeai-gui` 归档到 `.archived/projects/go_projects/typeai-gui`。
- [x] Task 8：验收（go vet / go test / 构建 / CLI / GUI 启动 / HTTP 冒烟）。

## 验收

- `go vet ./...`、`go test ./...` 全绿。
- `uv run scripts/build.py` 产出 `typeai-gui-dev.exe` 与 `typeai-cli-dev.exe`。
- CLI：`typeai-cli-dev.exe version|schema|config get|help` 正常；`serve` 根路径返回 WebUI。
- GUI：双击无黑框；托盘就绪；窗口几何记忆；dev 与 release 可并存。
- PE 子系统：GUI=2、CLI=3；两者 FileDescription 不同。
- 数据目录 dev/prod 隔离；旧配置与会话已迁移。

## 实测记录（2026-10-22）

- `go vet ./...`、`go test ./...` 全绿。
- `uv run scripts/build.py` 产出 `typeai-gui-dev.exe`（12.35 MB）与 `typeai-cli-dev.exe`（15.98 MB）。
- PE Subsystem：GUI=2、CLI=3；两者 FileDescription 不同，版本注入成功。
- `serve` 根路径返回 WebUI；`/api/state`、`/api/sessions`、`/api/version` 正常。
- GUI `--hidden` 启动成功，内嵌 HTTP 可访问，日志落 `<数据目录>/typeai.log`。
- 旧配置与会话迁移到 `dev` 通道成功，旧文件保留。
- mock LLM 验证 SSE 流式、session 落盘、fork 分支历史解析（`main` 2 条 / `fork-01` 4 条）。
- Edge headless 验证 WebUI 脚本执行：分支 Tab、空态、会话列表均渲染。

## 未决问题与阻塞确认清单

- [x] GUI 形态：原生 WebUI（已确认）。
- [x] `typeai-gui` 处理：归档（已确认）。
- [x] 首批功能范围（已确认）。
