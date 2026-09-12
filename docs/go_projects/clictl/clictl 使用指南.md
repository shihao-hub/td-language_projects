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

# 详情：最近 10 条启动 + 累计耗时
clictl info go

# 更新/清空 meta
clictl set go --meta '{\"tags\":[\"cli\"]}'
clictl set go --meta '{}'

# 删除注册（级联删其 launches）
clictl rm go

# 未注册名智能建议（前缀 > 子串 > 编辑距离，取前 3）
clictl run goxx      # 错误 JSON 附 "suggestions":["go"]

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

常用错误码：`conflict`（name/path 重复）、`not_found`、`meta_unknown_key`、`meta_invalid`、`meta_too_large`、`not_exe`（v1 仅支持 .exe）、`file_not_found`、`db_error`。

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

- `clictl completion powershell --install` 把补全安装块写入 `$PROFILE`（conda-init 风格标记区块，幂等；安装行带 `Get-Command clictl` 守卫，clictl 不在 PATH 的会话自动跳过，不污染 shell 启动）；`--uninstall` 按标记整块移除
- 补全行为：第 1 位置补全子命令名（`clictl ru<Tab>`）；`run/start/stop/rm/info/set` 后第 1 位置补全工具名（候选来自注册列表，前缀过滤）；`run`/`start` 第 2 参数起为子进程透传段，不产生候选
- 只绑定 `clictl` 命令名，不影响其他工具的补全；内部 try/catch 静默失败
- `completion powershell` / `completion names` 输出 **raw 文本而非 JSON 包络**（消费者是 shell 补全脚本，输出即协议，同 `run` stdout 例外先例）；`--install`/`--uninstall` 为动作型命令仍输出 JSON

## 二期规划

`scan` 批量收编、`.cmd/.bat/.ps1` shim、`clictl rpc` JSON-RPC 模式（stdin NDJSON，GUI/AI 客户端接入）、标签体系、全局统计。详见项目内 `PLAN.md`。
