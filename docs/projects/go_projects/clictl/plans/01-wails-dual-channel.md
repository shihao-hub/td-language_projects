# clictl 双通道化改造（Wails v3 桌面台）

- 目标：把单产物 CLI `clictl.exe` 改造为 `clictl-gui`（Wails v3 托盘 + 内嵌 WebUI）与 `clictl-cli`（终端）双通道，dev/release 五维隔离。
- 基线：sh-go-wails-desktop SOP v1.6.0；实机模板 `go_projects/anatomymanager`。
- 版本：2.0.0（形态变更，破坏性：产物改名）。

## 一、现状与差距

| 项 | 现状 | 目标 |
|---|---|---|
| 产物 | `clictl.exe`（控制台单产物） | `clictl-gui[-dev].exe` + `clictl-cli[-dev].exe` |
| 服务层 | `internal/service` + SQLite | 复用，不动业务语义 |
| HTTP | 无 | 新增 `internal/api`（REST + WebUI），GUI 与 `serve` 共用 |
| WebUI | 无 | 新增 `internal/web/assets` 单页工作台 |
| 桌面壳 | 无 | 新增 `internal/app`（Wails v3 托盘、窗口几何记忆、自启门禁） |
| 数据目录 | `%APPDATA%\language_projects\clictl\clictl.db` | `...\clictl\{dev,prod}\clictl.db` |
| 构建 | 单 exe + `-ldflags` | 双产物 + go-winres 版本资源 + 图标双通道 |

## 二、目录与模块

```text
cmd/clictl/main.go        //go:build !cli  GUI 入口（只出窗口）
cmd/clictl/cli.go         //go:build cli   终端入口 → internal/cli.Run
internal/appinfo/         无 Wails 依赖：Version/BuildMode/Channel/DataDir/Logf
internal/app/             Wails 桌面壳：gui.go / autostart.go / window_state.go / icon_* / instance_probe_*
internal/api/             HTTP REST + 内嵌 WebUI（不 import internal/app）
internal/web/             //go:embed assets
internal/store/           dbPath 改走 appinfo；新增 OpenAt(path)
scripts/build.py          双通道构建 + 门禁
scripts/render_icon.py    专属图标渲染
winres/{gui,cli}.json     PE VERSIONINFO 模板
```

拆包铁律：`internal/api`、`internal/appinfo` 不得 import `internal/app`，保证 `-tags cli` 产物不链接 Wails。

## 三、HTTP API（GUI 与 `serve` 共用同一 Handler）

统一包络：成功 `{"ok":true,"data":...}`；失败 `{"ok":false,"error":{"code","message"}}` + 4xx/5xx。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/meta` | 通道、版本、库路径、工具数 |
| GET | `/api/tools?status=&running=` | 列表 / 运行中过滤 |
| POST | `/api/tools` | 注册 exe（path/name/desc/meta） |
| GET | `/api/tools/{name}` | info（详情 + 最近启动 + running） |
| DELETE | `/api/tools/{name}` | 删除注册 |
| PUT | `/api/tools/{name}/meta` | 替换 meta |
| POST | `/api/tools/{name}/start` | 后台分离启动（可带 args） |
| POST | `/api/tools/{name}/stop` | 树杀全部后台实例 |
| POST | `/api/tools/{name}/reveal` | 资源管理器定位 exe |
| GET | `/api/fs?dir=` | 只读目录浏览（WebUI 选 exe 用） |
| GET | `/` | 内嵌 WebUI |

- `run`（前台透传）不提供 HTTP 入口：浏览器无法接管 TTY，UI 明确提示改用 `clictl-cli run`。
- GUI 写操作与 CLI 并发由现有 WAL + `busy_timeout=2000` 覆盖，不引入跨进程锁。

## 四、桌面壳

- 托盘：打开工作台 / 浏览器打开 / 开机自启（仅 release）/ 彻底退出。
- 单实例 ID `shihao.langproj.clictl.gui[.dev]`，与 `where` 的 OpenMutex 探测同源。
- 窗口：默认 1180×780，最小 900×600；`window.json` 记忆尺寸/位置/最大化（700ms 防抖 + 关闭前同步落盘 + 外接屏兜底）。
- 端口：`net.Listen(0)` 动态端口，GUI 窗口 URL 与 CLI `serve` 打印地址同源。

## 五、CLI 通道新增/调整

- 保留全部现有子命令与 JSON 契约。
- 新增 `serve [--port 0] [--open]`：阻塞式托管同一 Handler，根路径返回完整 WebUI。
- `--hidden` / `--tray`：退化为无窗口 `serve`。
- 新增 `where [--json]`：通道 / 版本 / 库路径 / 工具数 / 两通道 GUI 运行状态。
- `version` 保持 JSON 包络（既有契约），增加 `channel`、`build_mode`、`db_path`。
- 版本真源迁移到 `internal/appinfo`，`internal/cli.Version` 删除。

## 六、数据与迁移

- `appinfo.DefaultDBPath()`：`%APPDATA%\language_projects\clictl\<channel>\clictl.db`，回退 `~/.language_projects/clictl/<channel>`。
- 每通道首次启动若目标库不存在，则从旧库 `...\clictl\clictl.db` 复制（含 `-wal`/`-shm`），旧文件保留。
- 迁移只在目标缺失时执行，不覆盖已有通道库。

## 七、WebUI 范围

- 顶栏：品牌、搜索、通道徽标（DEV 琥珀 / PROD 青）、刷新、添加。
- 左栏：工具卡片（名称、图标字母块、运行中呼吸点、启动次数、状态）。
- 右栏：详情（路径、大小、注册时间、累计启动/耗时、meta、最近 10 条启动记录）。
- 操作：启动（可填参数）、停止、定位、编辑 meta、删除。
- 添加弹窗：路径输入 + 内置目录浏览（`/api/fs`），name/desc/meta 可选。
- 风格：中性深灰工业台面 + 琥珀/青点缀，禁用蓝紫渐变与霓虹光晕。

## 八、构建与门禁

- `scripts/build.py`：HEAD 精确 `<project>/v*` tag + 工作区干净 → release，否则 dev；每个产物构建前重建 syso（GUI/CLI 的 FileDescription 不同）。
- `go-winres` 生成 VERSIONINFO + manifest + 图标；dev 用 Go 地鼠、release 用专属图标。
- 产物守卫：release 名不带 dev、dev 名必须带 `-dev`；自动清理历史 `clictl.exe`。

## 九、验收

- [ ] `go build` / `go test ./...` / `go vet ./...` 通过。
- [ ] gui 产物 Subsystem=2、cli=3；GUI 带任意参数只出窗口。
- [ ] `clictl-cli list --json | ConvertFrom-Json` 非空。
- [ ] `clictl-cli serve` 根路径为完整工作台，`/api/*` 正常。
- [ ] 窗口移动/缩放/最大化后关窗重开可恢复。
- [ ] dev 与 release 同时运行互不唤醒，数据分别落 `dev`/`prod`。
- [ ] 现有 1.4.0 全部 CLI 契约无回归。

## 未决问题与阻塞确认清单

- [ ] 旧库 `...\clictl\clictl.db` 是否允许 dev / prod **各自复制一份**（之后两通道数据分叉）？默认按此执行。
- [ ] 2.0.0 是否直接作为新版本基线（`info.json` fixed=2.0.0），不打 tag 前只出 dev 产物。
- [ ] WebUI 是否需要 `run` 前台透传的替代形态（如终端弹窗）？默认不做，仅 `start`/`stop`。
- [ ] 旧 `clictl.exe` 构建产物是否允许由构建脚本自动删除（源码与文档不动）？默认是。
