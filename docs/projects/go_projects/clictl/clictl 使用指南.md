# clictl 使用指南

> 项目位置：`go_projects/clictl`（子仓内）。本文为父仓镜像文档，与项目内 `README.md` 保持同步。
> 双通道改造设计：见同目录 `plans/01-wails-dual-channel.md`。
> CLI + JSON 输出的通用实现模式（供其他 CLI 项目参考）：见同目录 `Go CLI JSON 输出模式参考.md`。
> 表结构变更 SQL 存档：见同目录 `migrations/`。

## 定位

Windows 工具注册器/启动台，双通道产物：

- `clictl-gui[-dev].exe`：Wails v3 托盘 + 内嵌 WebUI，注册/搜索/启动/停止/定位/meta/启动记录全部可在窗口完成
- `clictl-cli[-dev].exe`：console 子系统的完整 CLI（`run`/`start`/`stop`/`add`/`list`/`serve`/`where`/`mcp` 等），终端、脚本与 Agent 一律用它

所有管理命令**永远输出 JSON**，GUI 与 `serve` 共用同一套 HTTP Handler；存储用 SQLite（`%APPDATA%\language_projects\clictl\{dev,prod}\clictl.db`）。

## 快速上手

```powershell
# 构建（dev 双产物：bin/clictl-gui-dev.exe + bin/clictl-cli-dev.exe）
cd go_projects/clictl
uv run scripts/build.py            # 默认 dev 通道
uv run scripts/build.py --release  # 正式名（需 clictl/v* tag + 工作区干净）

# 桌面启动台：双击 clictl-gui-dev.exe；--hidden 为静默托盘
.\bin\clictl-gui-dev.exe

# 终端一律用 cli 产物（PATH 里建议把 clictl-cli.exe 命名为 clictl）
.\bin\clictl-cli-dev.exe list --pretty

# 注册（name 默认=文件名去 .exe 小写化）
clictl-cli add "D:\Program Files\Go\bin\go.exe" --desc "Go toolchain" --meta '{\"source\":\"go\",\"tags\":[\"dev\"]}'

# 源码命令：给已有卡片附加 / 新建仅源码卡片（示例：uv run zedhub-gui）
clictl-cli add-cmd --name zedhub-gui-dev --program uv `
  --dir D:\Users\language_projects\python_projects\zedhub `
  --type gui --arg run --arg zedhub-gui

# 隐藏控制台启动，随后按需显示/隐藏（不重启进程）
clictl-cli start zedhub-gui-dev
clictl-cli console zedhub-gui-dev --show
clictl-cli console zedhub-gui-dev --hide

# 显式源码目标；可见控制台
clictl-cli start --source zedhub-gui-dev
clictl-cli start --console --source zedhub-gui-dev

# 查看全部（名称升序），--pretty 缩进输出
clictl-cli list --pretty

# 透传启动：与直接执行 go version 完全一致，退出码直通
clictl-cli run go version

# 后台启动托盘/服务类工具：立即返回 pid，不阻塞终端
clictl-cli start zread-tray

# 看哪些后台工具活着 / 详情含 running 状态
clictl-cli list --running --pretty
clictl-cli info zread-tray --pretty

# 全量终止该工具的后台活实例（taskkill 树杀）
clictl-cli stop zread-tray

# 复制已注册 exe 到指定目录（目录须已存在；目标已存在需 --force 覆盖）
clictl cp go "D:\tools"
clictl cp go "D:\tools" --force

# 详情：最近 10 条启动 + 累计耗时
clictl-cli info go

# 更新/清空 meta
clictl-cli set go --meta '{\"tags\":[\"cli\"]}'
clictl-cli set go --meta '{}'

# 删除注册（级联删其 launches）
clictl-cli rm go

# 未注册名智能建议（前缀 > 子串 > 编辑距离，取前 3）
clictl-cli run goxx      # 错误 JSON 附 "suggestions":["go"]

# PS 5.1 下管道给下游工具时中文变 ? ：--ascii 转义非 ASCII（下游 JSON 解析自动还原）
clictl-cli --ascii help | jtree

# PowerShell Tab 补全：一次性安装，新开窗口后 clictl-cli run go<Tab> 即补全
clictl-cli completion powershell --install
clictl-cli completion powershell --uninstall   # 卸载
```

## 双通道与桌面启动台（v2.0.0）

| 产物 | 子系统 | 行为 |
|---|---|---|
| `clictl-gui[-dev].exe` | Windows GUI | 只开窗口/托盘；除 `--hidden`/`--tray` 外忽略一切参数（`clictl-gui list` 不会执行 CLI） |
| `clictl-cli[-dev].exe` | Console | 全部子命令只在这里；prompt/管道/重定向合规 |

- 托盘菜单：打开启动台 / 在默认浏览器中打开 / 开机自启（dev 置灰）/ 彻底退出；关窗只销毁窗口，进程留托盘
- 窗口几何（尺寸/位置/最大化）落在 `<通道目录>\window.json`，重开精确恢复
- WebUI：左侧工具卡片（搜索 + 全部/运行中/有效/失效过滤 + 平铺/分组视图（分组内可在标签页与树形折叠间切换） + 排序），右侧详情（exe/源码双目标、运行实例、路径、分组徽标、大小、累计耗时、meta、最近 10 条启动）；支持目标化启动（可带参数）/停止/控制台显示隐藏/定位/设置分组/编辑/编辑 meta/删除/注册（内置目录浏览选 exe/程序/工作目录）
- 分组与视图：默认平铺、名称升序；点击详情标题旁的分组徽标即可选择已有分组或新建（写入 `meta.group`），注册时也可直接指定；分组视图顶部以标签页切换分组，也可一键切到树形折叠；视图/排序/当前分组/折叠状态落在 `<通道目录>\ui_preferences.json`，重启保持
- WebUI 不提供 `run` 前台透传：浏览器无法接管 TTY，需要看输出请用 `clictl-cli run`
- 无 GUI 时也可只跑 WebUI：`clictl-cli serve [--port 0] [--open]`，根路径即完整工作台
- 通道自省：`clictl-cli where`（JSON）确认当前通道、库路径、工具数与两通道 GUI 运行状态

## 数据目录与迁移

- dev 产物 → `%APPDATA%\language_projects\clictl\dev\clictl.db`
- release 产物 → `%APPDATA%\language_projects\clictl\prod\clictl.db`
- 旧库 `%APPDATA%\language_projects\clictl\clictl.db` 在**每个通道首次启动时各复制一份**（含 `-wal`/`-shm`，旧文件保留）；此后两通道独立演进
- 日志：`<通道目录>\clictl.log`（GUI 无控制台排障）；WebView2 缓存：`<通道目录>\webview2\`

## run vs start

> **要在当前终端看它输出、等它干完的用 `run`；点火就走的用 `start`；命令行工具要在独立窗口里跑的用 `start --console`。**

| | `run` | `start` | `start --console` | `start --hidden` |
|---|---|---|---|---|
| 语义 | 前台透传，阻塞到子进程退出 | 按目标默认模式启动，立即返回 | 可见控制台窗口，立即返回 | 隐藏控制台，立即返回 |
| 默认场景 | 调试/看输出 | exe GUI → detached；源码 gui → hidden；console 目标 → console | 需要交互/看窗口 | 不占屏幕，可随时显示 |
| IO | 当前终端 stdin/stdout/stderr 直通 | 无控制台（detached）或隐藏/可见控制台 | 子进程独占新窗口的控制台 | 子进程独占隐藏控制台 |
| 退出码 | 透传子进程码 | 0 成功 / 127 未注册或失效 | 0 成功 / 127 未注册或失效 | 0 成功 / 127 未注册或失效 |
| 记账 | 闭环 | 只落 started_at + pid；`stop` 闭环 | 同 start；GUI/serve 常驻时窗口关闭即闭环 | 同 start；`console` 显示/隐藏不重启进程 |

## 源码命令与双目标（v2.2.0）

- 卡片模型：一张卡片 = 可选 exe + 可选源码命令，支持「仅 exe」「仅源码」「exe + 源码」；默认目标固定 exe，仅源码卡片自然为 source
- 源码字段：`source_program`（解析后的程序绝对路径）、`source_workdir`、`source_args`（固定前缀参数）、`source_type`（gui/console）
- 注册/附加：
  - `clictl-cli add-cmd --name N --program uv --dir D --type gui --arg run --arg zedhub-gui`
  - 同名卡片没有源码目标时附加；没有同名卡片时创建仅源码卡片；已有源码目标时用 `edit` 修改
  - `add <path> --name N` 同名卡片没有 exe 时附加 exe
- 全量编辑：`clictl-cli edit <name> [--desc D] [--default exe|source] [--exe PATH] [--no-exe] [--source-program P] [--source-dir D] [--source-type gui|console] [--source-arg A ...] [--no-source] [--meta JSON]`
- 启动目标：`run/start` 支持 `--exe|--source`；缺省走 `default_target`；`start` 缺省模式按目标类型自动选择
- 隐藏控制台：源码 gui / exe console 可用 `start`（源码 gui 默认 hidden）或 `start --hidden`；随后 `console <name> --show|--hide [--pid N]` 不重启进程显示/隐藏
- 控制台实现：启动时 `CREATE_NEW_CONSOLE + STARTF_USESHOWWINDOW/SW_HIDE` 创建隐藏控制台；显隐用短命 `__console-ctl` 子进程 `AttachConsole(pid)` + `ShowWindow`
- 多实例：同一卡片可多次 start；控制台显隐缺省操作最新存活实例，`--pid` 可指定；`stop` 仍全量树杀
- 边界：隐藏控制台是“有控制台但不可见”，不是“无控制台”；真正的无控制台模式为 `--detached`，无法事后显示；不做日志文件，进程退出后控制台缓冲不保留
- UI：详情页双目标区块分别提供「启动 exe」「源码启动/终端启动」「打开目录」；运行实例列表按 PID 显示目标/模式与显示/隐藏按钮；「编辑」弹窗可同时改 exe、源码、默认目标、描述、meta

## 命令行工具终端启动（console 模式）

- CLI：`clictl-cli start --console <name> [args...]`；`--console` 只在前置段生效，工具名之后的同名参数原样透传
- WebUI：exe 读 PE 子系统、源码读注册类型，显示「命令行 / 窗口程序 / 源码命令 / exe + 源码」徽标；详情页双目标区块分别提供启动按钮，运行实例可显示/隐藏控制台；命令行目标主按钮为「终端启动」，窗口程序主按钮为「启动」，源码 gui 主按钮为「源码启动」（hidden）
- API：`POST /api/tools/{name}/start` 的 `target` 支持 `exe`/`source`，`mode` 支持 `console`/`hidden`/`detached`，省略时按目标自动选择；返回结果含 `target`/`mode`
- API：`POST /api/tools/{name}/console` 显示/隐藏运行中实例控制台 `{visible,pid?}`；`PUT /api/tools/{name}` 全量编辑双目标
- 窗口内是**真实控制台设备**（`isTTY=true`）：由原生 `CreateProcess` 初始化标准句柄，TUI 程序（如 taskmon）可正常渲染、刷新与按键交互
- 已知语义：CLI 的 `start --console` 自身立即退出，子进程自然退出时无法回写闭环（与后台 `start` 一致）；GUI/serve 常驻时 `Wait` 会回写 duration/exit_code

## JSON 包络

- 成功：`{"ok":true,"data":...}`
- 失败：`{"ok":false,"error":{"code":"...","message":"..."}}`
- 管理命令错误走 stdout；`run` 的前置错误（未注册/文件失效）走 **stderr**，保证 `run` 的 stdout 只属于子进程；`start`/`stop` 前置错误走 stdout 且保持退出码 127（跨命令一致）

常用错误码：`conflict`（name / exe 路径 / 源码三元组重复）、`not_found`、`meta_unknown_key`、`meta_invalid`、`meta_too_large`、`not_exe`、`file_not_found`、`dest_not_found`、`dest_exists`、`same_path`、`copy_failed`、`db_error`、`program_not_found`、`workdir_not_found`、`no_exe_target`、`no_source_target`、`not_running`、`console_unavailable`、`console_failed`。

## 退出码约定

- 管理命令：0 成功 / 1 失败
- `clictl run`：透传子进程退出码；未注册/文件失效 = 127
- `clictl start`：0 成功 / 未注册或失效 = 127（错误 JSON 附相似名 suggestions，同 run）
- `clictl stop`：0（含无活实例 already_stopped）/ 1（存在杀后仍存活的实例）
- `help` / `-h` / `--help` / 无参数：输出帮助（JSON），exit 0；子命令级 `-h`（如 `clictl add -h`）同样输出帮助

## 后台启动与探活（v1.2.0）

- `clictl start <name> [args...]`：DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP 分离启动，无控制台不闪黑框；输出 `pid`；已有活实例附 `already_running:true`（不拦截多实例）
- 探活三重校验：OpenProcess 存在性 + GetExitCodeProcess 终止态 + exe 路径比对（防 PID 回收复用误判）
- `clictl list --running`：只看后台活实例（附 running_pids / last_start，与 --status 互斥）；`clictl info` 的 `running.alive/pids` 字段
- `clictl stop <name>`：对该工具全部存活实例 `taskkill /PID x /T /F` 树杀（含子进程），杀后复探确认再闭环记录（exit_code=1 强杀约定值）
- launches 表 `pid` 列仅 start 写入；存量库首次运行新版自动 ALTER 加列；已知局限见项目 PLAN.md（退出码 259 哨兵歧义、SysWOW64 重定向，概率极低）

## 复制命令（v1.3.0）

- `clictl cp <name> <dest_dir> [--force]`：把已注册 exe 复制到目标目录，保留原文件名；输出 `name` / `src` / `dest` / `size_bytes`
- 目标目录必须已存在（不自动创建，缺失报 `dest_not_found`）；目标同名文件默认拒绝（`dest_exists`），`--force` 强制覆盖；源与目标为同一文件时始终拒绝（`same_path`，防复制中途截断损坏源文件）
- 流式复制不整读内存；正在运行的 exe 可正常复制（Windows 读共享允许），仅目标文件被占用时如实报 `copy_failed`

## 管道编码与 --ascii（v1.4.0）

- **根因**：PowerShell 5.1 中两个原生 exe 间的管道不是字节直通——PS 先用 `[Console]::OutputEncoding`（中文系统默认 OEM 936/GBK）解码 clictl 的 UTF-8 stdout，再用 `$OutputEncoding`（**PS 5.1 默认 ASCII**）重编码写入下游 stdin，中文经 ASCII 重编码不可逆地变 `?`。下游工具（jtree 等）无法修复：数据进它之前已被毁
- **`--ascii` 开关**：显式 opt-in，把 JSON 输出中非 ASCII 字符转义为 `\uXXXX`（BMP 外拆代理对，小写十六进制），产物全 ASCII 对任何管道重编码免疫，下游 JSON 解析（`JSON.parse` / `ConvertFrom-Json` / 各语言 json 库）自动还原中文。位置规则同 `--pretty`（子命令前后皆可，`run`/`start` 透传段除外——透传段的 `--ascii` 属于子进程）；stdout 与 stderr 两个 JSON 出口同时覆盖
- **默认行为不变**：不加 `--ascii` 输出仍是 UTF-8 中文原文，不违反"不改输出编码"约定
- **raw 例外天然不受影响**：`completion powershell` / `completion names` 直出 raw 文本不经转义（`names` 绝不能转义——补全脚本靠 `-like` 前缀匹配工具名）
- **profile 固化**：`completion powershell --install` 安装块自带两行编码固化（`$OutputEncoding` 与 `[Console]::OutputEncoding` 均设 UTF8，位于安装行之前、Get-Command 守卫之外无条件执行），新开 PS 5.1 会话中原生 exe 间管道免 `--ascii` 直接可用
- **已知副作用**：`[Console]::OutputEncoding=UTF8` 会使 ping 等 GBK 老工具在该会话输出乱码（仅影响该会话，不改系统设置）

## meta 白名单

`--meta` 仅允许 `source`（string ≤64B）、`tags`（[]string ≤8 项、每项 ≤32B、去重小写存储）与 `group`（string ≤32B、首尾空白裁剪），白名单外 key 直接拒绝；序列化后 ≤ 4KB 硬限。

## 启动记账

每次 `run` 落一条 launches 记录（started_at / duration_ms / exit_code），完整闭环。父进程吞掉 Ctrl+C，同控制台的子进程照常退出，父进程回写记录后再退——异常终止也有完整记录（duration_ms 为 NULL 表示未正常结束）。

每次 `start` 落一条带 pid 的 launches 记录，不等待不闭环；`stop` 杀完回写（duration 取实测存活时长，exit_code=1 强杀约定值）；进程自行退出后记录保持未闭环，探活自然判死，不污染 `--running`。

## status 机制

落库 `status` 记录"上次校验结论"；list/info/run 触碰时一律现场校验并回写，JSON 输出的 status 永远是实时结论，`list --status invalid` 可过滤出失效条目。双目标卡片的总体 status 为「任一目标有效 = active」，详情分别给出 `exe.status` / `source.status`，失效一侧按钮禁用。

## 智能提示（v1.1.0）

**未注册相似名建议**：`run`/`start`/`stop` 遇到未注册名时，按 前缀 > 子串 > 编辑距离 匹配已注册名取前 3，错误 JSON 附可选 `suggestions` 字段（run 走 stderr、start/stop 走 stdout），`message` 同步附"是否想找"；退出码仍 127。

**PowerShell Tab 补全**（PS 5.1+，clictl 需在 PATH 中）：

- `clictl-cli completion powershell --install` 把补全安装块写入 `$PROFILE`（conda-init 风格标记区块，幂等；安装行带 `Get-Command clictl` 守卫，clictl 不在 PATH 的会话自动跳过，不污染 shell 启动）；安装块自带两行 UTF-8 编码固化（修 PS 5.1 原生 exe 间管道中文变 `?`，详见「管道编码与 --ascii」小节）；旧版 3 行块重跑 `--install` 自动升级为 5 行标准块（返回 `upgraded:true`）；`--uninstall` 按标记整块移除（removed=5）
- 补全行为：第 1 位置补全子命令名（`clictl ru<Tab>`）；`run/start/stop/rm/info/set/cp/edit/console` 后第 1 位置补全工具名（候选来自注册列表，前缀过滤）；`run`/`start` 第 2 参数起为子进程透传段，不产生候选
- 只绑定 `clictl` 命令名，不影响其他工具的补全；内部 try/catch 静默失败
- `completion powershell` / `completion names` 输出 **raw 文本而非 JSON 包络**（消费者是 shell 补全脚本，输出即协议，同 `run` stdout 例外先例）；`--install`/`--uninstall` 为动作型命令仍输出 JSON

## 二期规划

`scan` 批量收编、`.cmd/.bat/.ps1` shim、标签体系、全局统计、WebUI 内的前台 run（终端弹窗形态）。详见项目内 `PLAN.md`。
