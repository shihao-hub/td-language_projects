# clictl 源码命令启动与按需控制台

- 背景：clictl 目前只管理 exe。zedhub 等 Python 项目编译 exe 很慢，用户希望有时直接在工作目录执行 `uv run zedhub-gui`。
- 目标：一张工具卡片可同时持有「exe 目标」和「源码命令目标」；源码命令支持工作目录 + 固定参数；默认目标保持 exe；支持可见控制台、隐藏控制台，以及不重启进程前提下显示/隐藏控制台。
- 非目标：不引入 shell（管道/重定向/`&&`）、不做日志文件持久化、不做 ConPTY 浏览器终端、不自动编译源码。

## 决策（已确认）

| 议题 | 决策 |
|---|---|
| 卡片模型 | 一张卡片 = 可选 exe + 可选源码命令；至少一个目标 |
| 卡片形态 | 仅 exe / 仅源码 / exe + 源码 |
| 默认目标 | 固定 `exe`；仅源码卡片自然为 `source` |
| 源码字段 | `source_program`（解析后绝对路径）、`source_workdir`、`source_args`（固定前缀参数 JSON）、`source_type`（gui/console） |
| 启动模式 | `run`（前台透传）/ `console`（可见控制台）/ `hidden`（隐藏控制台）/ `detached`（无控制台） |
| 无窗口显示控制台 | 启动时创建隐藏控制台（`CREATE_NEW_CONSOLE` + `STARTF_USESHOWWINDOW/SW_HIDE`），之后用 helper `AttachConsole(pid)` + `ShowWindow` 显示/隐藏，不重启进程 |
| 源码默认模式 | `source_type=gui` → `hidden`；`source_type=console` → `console` |
| exe 默认模式 | 保持现状：PE Subsystem = console → `console`，否则 `detached` |
| 控制台历史 | 不落日志文件；进程退出后控制台缓冲不保留 |
| 多实例 | 同一卡片可多次 start；控制台显隐默认操作最新存活实例，UI 列出实例并可按 PID 指定；stop 仍全杀 |
| 编辑 | 全量编辑：exe、源码、默认目标、描述、meta |
| CLI 注册入口 | `add-cmd`（附加或创建源码目标） |
| 固定参数 CLI 形式 | 可重复 `--arg`，不解析 shell 字符串；WebUI 仍按引号解析 |

## 一、数据模型

```sql
CREATE TABLE tools (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  name            TEXT NOT NULL UNIQUE COLLATE NOCASE,
  description     TEXT NOT NULL DEFAULT '',
  status          TEXT NOT NULL DEFAULT 'active'
                  CHECK (status IN ('active','invalid')),
  meta            TEXT,
  added_at        TEXT NOT NULL,
  default_target  TEXT NOT NULL DEFAULT 'exe'
                  CHECK (default_target IN ('exe','source')),

  exe_path        TEXT NOT NULL DEFAULT '' COLLATE NOCASE,

  source_program  TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
  source_workdir  TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
  source_args     TEXT NOT NULL DEFAULT '[]',
  source_type     TEXT NOT NULL DEFAULT 'gui'
                  CHECK (source_type IN ('gui','console'))
);

CREATE UNIQUE INDEX idx_tools_exe_path
  ON tools(exe_path) WHERE exe_path <> '';
CREATE UNIQUE INDEX idx_tools_source
  ON tools(source_program, source_workdir, source_args)
  WHERE source_program <> '';
```

- 应用层强制：`exe_path` 与 `source_program` 至少一个非空；`default_target` 必须指向实际存在的目标。
- 总体 `status`：至少一个目标有效 = active；详情分别给出 `exe.status` / `source.status`，失效一侧按钮禁用。
- `launches` 增加 `target`（exe/source）与 `mode`（run/console/hidden/detached）。
- 顶层 `path` 保持兼容：有 exe 取 exe，否则取源码程序；`kind` 派生为 `exe` / `source` / `both`。

## 二、启动与控制台

| 目标 | 默认模式 | 可选 |
|---|---|---|
| exe GUI | `detached` | 无 |
| exe 命令行 | `console` | `hidden`（CLI） |
| 源码 gui | `hidden` | `console` |
| 源码 console | `console` | `hidden` |

- `hidden` 用原生 `CreateProcess`：`CREATE_NEW_CONSOLE | CREATE_NEW_PROCESS_GROUP`，`StartupInfo.Flags=STARTF_USESHOWWINDOW`、`ShowWindow=SW_HIDE`、`InheritHandles=false`，工作目录设为源码 `workdir`。
- 显示/隐藏：短命 helper `clictl-cli __console-ctl <pid> show|hide|status`，用 `FreeConsole` → `AttachConsole(pid)` → `GetConsoleWindow` → `ShowWindow`/`IsWindowVisible` → `FreeConsole`。helper 以 `CREATE_NO_WINDOW` 启动，不产生自己的窗口，也不 detach 调用者终端。
- `show` 时 `SetForegroundWindow`，控制台标题设为工具名。
- 关闭控制台窗口会结束进程；UI 提示使用“隐藏”。
- 风险：`uv` 若不常驻父进程，show/hide 可能找不到控制台。实施时实测 `uv run zedhub-gui` 进程树；必要时改为常驻 console host 拥有控制台。`SW_HIDE` 若闪窗，改为 `CREATE_SUSPENDED` + 先隐藏再 `ResumeThread`。

## 三、后端改动

| 层 | 文件 | 改动 |
|---|---|---|
| store | `internal/store/store.go` | v3 schema、迁移、双目标扫描/状态、Add/Edit、launches target/mode |
| runner | `internal/runner/start.go` | `LaunchSpec`、`StartHiddenConsole`、`spawnConsoleProcess` 支持 hidden/workdir |
| runner | `internal/runner/console_windows.go`（新增） | `SetConsoleVisible`、`__console-ctl` attach/show/hide/status |
| runner | `internal/runner/runner.go` / `alive.go` / `stop.go` | 统一目标启动、目标路径探活 |
| service | `internal/service/tools.go` / `process.go` | AddCmd、Edit、目标解析、Info/Running 双目标、console 显隐、cp/reveal 分支 |
| api | `internal/api/server.go` | 注册/编辑双目标、`mode=hidden`、`POST /api/tools/{name}/console`、running instances |
| cli | `internal/cli/commands.go` | `add-cmd`、`edit`、`run/start` 目标参数、`console`、help/补全 |
| mcp | `internal/mcp/tools.go` / `exec.go` | add/info/start/run 支持目标与 mode，保持 10 个工具 |
| web | `internal/web/assets/*` | 双目标注册/编辑、源码启动、控制台显隐、实例列表 |
| docs | 父仓使用指南 / MCP 文档 / README / CHANGELOG / migrations | 契约同步 |

## 四、CLI / API 契约

```powershell
clictl-cli add <path> [--name N] [--desc D] [--meta JSON]
clictl-cli add-cmd --name N --program uv --dir D --type gui --arg run --arg zedhub-gui
clictl-cli edit <name> [--desc D] [--default exe|source] [--exe PATH] [--no-exe]
  [--source-program P] [--source-dir D] [--source-type gui|console]
  [--source-arg A ...] [--no-source]
clictl-cli run   [--exe|--source] <name> [args...]
clictl-cli start [--console|--hidden|--detached] [--exe|--source] <name> [args...]
clictl-cli console <name> --show|--hide [--pid N]
```

- `add-cmd` 同名卡片无源码目标时附加，已有源码目标时 conflict；仅源码卡片自动创建。
- `add` 同名卡片无 exe 时附加 exe，已有 exe 时 conflict。
- `default_target` 固定 exe；`add-cmd` 附加源码不改变默认目标。
- API：`POST/PUT /api/tools` 接受 `default_target`、`exe`、`source`；`start` 接受 `target`/`mode`；`console` 接受 `visible`/`pid`。
- `cp` 仅 exe 目标；仅源码卡片报 `no_exe_target`。
- `reveal` 支持 `target`：exe 定位文件，source 打开工作目录。

## 五、WebUI

- 注册/编辑弹窗：两个可选区块（可执行文件、源码命令），至少填一项；源码含程序、工作目录、固定参数、类型；两个都填时显示默认目标（默认 exe）。
- 详情：`exe` / `源码` / `exe + 源码` 徽标；主按钮用默认目标，另一目标作次按钮；显式“启动目标”区块；带参数启动有目标下拉；运行实例列表含 PID/目标/模式/启动时间与显示/隐藏控制台；最近启动表增加目标与模式。
- 卡片：显示目标徽标；exe 失效但源码有效时整体仍有效并标“exe 失效”。
- 源码工作目录旁提供“打开目录”。

## 六、实施步骤

- [ ] 1. 计划落盘并独立提交。
- [ ] 2. store v3 schema、迁移、Add/Edit、状态、launches target/mode、迁移与唯一性测试。
- [ ] 3. runner `LaunchSpec`、hidden console、console ctl、uv 进程树实测与集成测试。
- [ ] 4. service/API 双目标、编辑、console 接口、running instances。
- [ ] 5. CLI `add-cmd` / `edit` / 目标参数 / `console` / help/补全。
- [ ] 6. MCP 双目标与 mode。
- [ ] 7. WebUI 双目标注册/编辑、源码启动、控制台显隐、实例列表。
- [ ] 8. 文档、CHANGELOG 2.2.0、迁移 SQL、构建验收。

## 七、验证

- [ ] `add-cmd` 创建仅源码卡片 → `start` 无窗口 → `console --show` 出现 → `--hide` 消失 → PID 不变 → `stop` 树杀。
- [ ] 现有 exe 卡片附加源码后，默认仍 exe，源码作为次按钮；`start --source` 覆盖默认。
- [ ] 仅 exe、仅源码、exe+源码 三种卡片的列表/详情/过滤/搜索正常。
- [ ] `run` stdout 纪律、退出码、Ctrl+C 记账不回归。
- [ ] `go test ./...`、`go vet ./...`、`gofmt -l`、`uv run scripts/build.py` 通过。
- [ ] PowerShell `list | ConvertFrom-Json` 正常；删除工具后 launches 级联删除。

## 八、风险与边界

- 隐藏控制台是“有控制台但不可见”，不是“无控制台”；真正的无控制台模式仍为 `detached`，无法事后显示。
- 控制台滚动缓冲受 conhost 限制，进程退出后消失（已确认不做日志文件）。
- `uv` 等启动器若不常驻父进程，按 PID attach 会失效；实施时验证并按需升级为常驻 console host。
- 旧启动记录的 `target/mode` 为空，详情显示 `--`。

## 九、未决问题（已关闭）

- [x] 同一卡片 vs 独立条目：同一卡片，exe + 可选源码。
- [x] 是否必须先有 exe：不需要，支持仅源码卡片。
- [x] 默认目标：固定 exe。
- [x] 控制台方案：隐藏控制台 + 按需显示/隐藏。
- [x] 是否保留日志：不保留。
- [x] 多实例：默认操作最新存活实例，UI 可按 PID 指定。
- [x] 编辑范围：exe、源码、默认目标、描述、meta 全量编辑。
