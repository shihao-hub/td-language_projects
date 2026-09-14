# clictl 使用指南

> 项目位置：`go_projects/clictl`（子仓内）。本文为父仓镜像文档，与项目内 `README.md` 保持同步。
> CLI + JSON 输出的通用实现模式（供其他 CLI 项目参考）：见同目录 `Go CLI JSON 输出模式参考.md`。
> 表结构变更 SQL 存档：见同目录 `migrations/`。

## 定位

Windows 单文件 CLI 工具注册器/启动器：注册任意 exe，`clictl run <名>` 前台透传启动，`clictl start <名>` 后台分离启动，启动过程被接管并记录。所有管理命令**永远输出 JSON**，存储用 SQLite（`%AppData%\clictl\clictl.db`）。

## 快速上手

```powershell
# 构建（产出单文件 clictl.exe，版本号注入）
cd go_projects/clictl
./scripts/build.ps1 -Version 1.0.0

# 注册（name 默认=文件名去 .exe 小写化）
clictl add "D:\Program Files\Go\bin\go.exe" --desc "Go toolchain" --meta '{\"source\":\"go\",\"tags\":[\"dev\"]}'

# 查看全部（launch_count 降序），--pretty 缩进输出
clictl list --pretty

# 透传启动：与直接执行 go version 完全一致，退出码直通
clictl run go version

# 后台启动托盘/服务类工具：立即返回 pid，不阻塞终端
clictl start zread-tray

# 看哪些后台工具活着 / 详情含 running 状态
clictl list --running --pretty
clictl info zread-tray --pretty

# 全量终止该工具的后台活实例（taskkill 树杀）
clictl stop zread-tray

# 复制已注册 exe 到指定目录（目录须已存在；目标已存在需 --force 覆盖）
clictl cp go "D:\tools"
clictl cp go "D:\tools" --force

# 详情：最近 10 条启动 + 累计耗时
clictl info go

# 更新/清空 meta
clictl set go --meta '{\"tags\":[\"cli\"]}'
clictl set go --meta '{}'

# 删除注册（级联删其 launches）
clictl rm go

# 未注册名智能建议（前缀 > 子串 > 编辑距离，取前 3）
clictl run goxx      # 错误 JSON 附 "suggestions":["go"]

# PS 5.1 下管道给下游工具时中文变 ? ：--ascii 转义非 ASCII（下游 JSON 解析自动还原）
clictl --ascii help | jtree

# PowerShell Tab 补全：一次性安装，新开窗口后 clictl run go<Tab> 即补全
clictl completion powershell --install
clictl completion powershell --uninstall   # 卸载
```

## run vs start

> **要在终端看它输出、等它干完的用 `run`；点火就走的用 `start`。**

| | `run` | `start` |
|---|---|---|
| 语义 | 前台透传，阻塞到子进程退出 | 后台分离（DETACHED），立即返回 |
| IO | stdin/stdout/stderr 直通 | 全部断开（console 程序无输出能力） |
| 退出码 | 透传子进程码 | 0 成功 / 127 未注册或失效 |
| 记账 | started_at + duration + exit_code 闭环 | 只落 started_at + pid；`stop` 杀完闭环（exit_code=1 强杀约定值） |

## JSON 包络

- 成功：`{"ok":true,"data":...}`
- 失败：`{"ok":false,"error":{"code":"...","message":"..."}}`
- 管理命令错误走 stdout；`run` 的前置错误（未注册/文件失效）走 **stderr**，保证 `run` 的 stdout 只属于子进程；`start`/`stop` 前置错误走 stdout 且保持退出码 127（跨命令一致）

常用错误码：`conflict`（name/path 重复）、`not_found`、`meta_unknown_key`、`meta_invalid`、`meta_too_large`、`not_exe`（v1 仅支持 .exe）、`file_not_found`（add 源不存在 / cp 源已失效）、`dest_not_found`（cp 目标目录不存在）、`dest_exists`（cp 目标已存在，需 `--force`）、`same_path`（cp 源与目标是同一文件）、`copy_failed`、`db_error`。

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

`--meta` 仅允许 `source`（string ≤64B）与 `tags`（[]string ≤8 项、每项 ≤32B、去重小写存储），白名单外 key 直接拒绝；序列化后 ≤ 4KB 硬限。

## 启动记账

每次 `run` 落一条 launches 记录（started_at / duration_ms / exit_code），完整闭环。父进程吞掉 Ctrl+C，同控制台的子进程照常退出，父进程回写记录后再退——异常终止也有完整记录（duration_ms 为 NULL 表示未正常结束）。

每次 `start` 落一条带 pid 的 launches 记录，不等待不闭环；`stop` 杀完回写（duration 取实测存活时长，exit_code=1 强杀约定值）；进程自行退出后记录保持未闭环，探活自然判死，不污染 `--running`。

## status 机制

落库 `status` 记录"上次校验结论"；list/info/run 触碰时一律现场 `os.Stat` 刷新并回写，JSON 输出的 status 永远是实时结论，`list --status invalid` 可过滤出失效条目。

## 智能提示（v1.1.0）

**未注册相似名建议**：`run`/`start`/`stop` 遇到未注册名时，按 前缀 > 子串 > 编辑距离 匹配已注册名取前 3，错误 JSON 附可选 `suggestions` 字段（run 走 stderr、start/stop 走 stdout），`message` 同步附"是否想找"；退出码仍 127。

**PowerShell Tab 补全**（PS 5.1+，clictl 需在 PATH 中）：

- `clictl completion powershell --install` 把补全安装块写入 `$PROFILE`（conda-init 风格标记区块，幂等；安装行带 `Get-Command clictl` 守卫，clictl 不在 PATH 的会话自动跳过，不污染 shell 启动）；安装块自带两行 UTF-8 编码固化（修 PS 5.1 原生 exe 间管道中文变 `?`，详见「管道编码与 --ascii」小节）；旧版 3 行块重跑 `--install` 自动升级为 5 行标准块（返回 `upgraded:true`）；`--uninstall` 按标记整块移除（removed=5）
- 补全行为：第 1 位置补全子命令名（`clictl ru<Tab>`）；`run/start/stop/rm/info/set/cp` 后第 1 位置补全工具名（候选来自注册列表，前缀过滤）；`run`/`start` 第 2 参数起为子进程透传段，不产生候选
- 只绑定 `clictl` 命令名，不影响其他工具的补全；内部 try/catch 静默失败
- `completion powershell` / `completion names` 输出 **raw 文本而非 JSON 包络**（消费者是 shell 补全脚本，输出即协议，同 `run` stdout 例外先例）；`--install`/`--uninstall` 为动作型命令仍输出 JSON

## 二期规划

`scan` 批量收编、`.cmd/.bat/.ps1` shim、`clictl rpc` JSON-RPC 模式（stdin NDJSON，GUI/AI 客户端接入）、标签体系、全局统计。详见项目内 `PLAN.md`。
