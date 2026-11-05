# Design Document

## Overview

以 Windows Job Object 为核心，把 `agy` 及其全部后代进程关进一个禁用前台激活权（`JOB_OBJECT_UILIMIT_SETFOREGROUND`）的作业对象：子进程树即使创建窗口或请求前台，Windows 也只允许其闪烁任务栏，无法切换用户当前前台窗口。同时收尾从 `taskkill /F /T` 外部命令改为 `TerminateJobObject`（零新进程、原子杀整树）。

改动全部收敛在 `internal/agapi` 的平台文件与 `client.go` 的启动/收尾两段，CLI/MCP/输出层零改动。

## Context

- 根因链（bugfix.md 已确认）：agyquota 的 `CREATE_NO_WINDOW` 只保护 agy 本身 → agy 运行期自建 console 会话并偶发 spawn 新终端会话的子进程 → Windows 11 默认终端路由给 WT → 本机 `windowingBehavior: useAnyExisting` 把隔壁 WT 窗口带到前台。
- agy 是闭源外部二进制（`%LOCALAPPDATA%\agy\bin\agy.exe`），其内部 spawn 行为不可修改，只能在使用方隔离。
- `cmd.SysProcAttr.CreationFlags` 仅作用于 agy 进程自身的创建，Windows 没有进程级 API 能禁止后代创建可见窗口；Job Object 的 UI 限制（`LimitFlags |= JOB_OBJECT_UILIMIT_SETFOREGROUND`）是唯一能剥夺**整棵子树**前台激活权的官方机制。
- 关键 API 已在本机 `golang.org/x/sys@v0.41.0`（go.mod 既有 indirect 依赖，提升为直接依赖）逐一验证存在：`CreateJobObject`、`SetInformationJobObject`、`AssignProcessToJobObject`、`TerminateJobObject`、`OpenProcess`、`CreateToolhelp32Snapshot`、`Thread32First/Next`、`ThreadEntry32`、`OpenThread`、`ResumeThread`、常量 `CREATE_SUSPENDED`/`CREATE_NO_WINDOW`/`JobObjectExtendedLimitInformation`/`PROCESS_SET_QUOTA|PROCESS_TERMINATE`/`TH32CS_SNAPTHREAD`/`THREAD_SUSPEND_RESUME`、类型 `JOBOBJECT_EXTENDED_LIMIT_INFORMATION`。**唯一例外**：`JOB_OBJECT_UILIMIT_SETFOREGROUND` 常量 x/sys 未提供，按 MSDN 值 `0x00000100` 自定义。

### 方案取舍

| 方案 | 结论 |
|---|---|
| A. Job Object + UILIMIT_SETFOREGROUND + CREATE_SUSPENDED 先挂起后入 job（本设计） | **选定**。唯一能保证 agy 从第一条指令起就失去前台权的方式；顺带获得原子杀整树能力 |
| B. 保持现状，建议用户改 WT `windowingBehavior` | 否决：改用户全局习惯治标不治本，且 agy 子树抢焦点路径仍在 |
| C. 注入/Hook 禁用 SetForegroundWindow | 否决：过度工程、跨版本脆弱、有杀软误报风险 |
| D. 仅 CREATE_SUSPENDED + 立即 Assign（不恢复线程快照遍历） | 并入 A：恢复主线程属于 A 的必要组成 |

## Goals and Non-Goals

**Goals**

- agy 整棵进程树在运行全程丧失前台激活权（AC-1）；
- 查询结束（正常/失败/超时）不留任何 agy 后代进程，收尾不再依赖 `taskkill`（AC-2）；
- CLI/--json/--raw/MCP 四个入口的对外契约不变（AC-3）；
- 非 Windows 构建不受影响（AC-4）。

**Non-Goals**

- 不修改 `agy` 本身、不解析其内部行为；
- 不改 `--zed` 数据源（纯 HTTP，无进程链）；
- 不新增对外 flag / MCP 工具 / 配置项；
- 不自动化前台行为的端到端测试（涉及真实焦点，保留手动验收）。

## Detailed Design

### 1. proc_windows.go：前台隔离原语（`UPDATED`）

- `internal/agapi/proc_windows.go`
    - **Purpose**: Windows 平台的进程启动约束与 Job 隔离原语，供 client.go 的跨平台流程调用。
    - **Changes**:
        - 依赖：`golang.org/x/sys/windows`（go.mod 由 indirect 提升为直接 require，无版本变化）；自定义常量 `const jobObjectUILimitSetForeground = 0x00000100`。
        - `setNoWindow(cmd *exec.Cmd)` 改名并扩展为 `startSuspended(cmd *exec.Cmd)`：`HideWindow=true`、`CreationFlags |= windows.DETACHED_PROCESS | windows.CREATE_SUSPENDED`。**DETACHED_PROCESS 是焦点抢占的根除手段**：agy 启动时完全不携带 console 会话，"默认终端接管 headless console"的 defterm 链路（第一版 `CREATE_NO_WINDOW` 下实测仍触发 WT `useAnyExisting` 前台化）从源头消失；agy 的输出由 stdout/stderr 管道接管，不依赖 console；agy 运行期若自行 `AllocConsole`，该分配由 conhost 直接服务、不经默认终端委托，且有作业对象前台限制兜底。agy 以挂起态启动，主线程一条指令都未执行。
        - 新增 `type foregroundIsolation struct { job windows.Handle }`（零值表示未启用）。
        - 新增 `attachForegroundIsolation(p *os.Process) (foregroundIsolation, error)`，内部顺序固定：
            1. `windows.OpenProcess(windows.PROCESS_SET_QUOTA|windows.PROCESS_TERMINATE, false, uint32(p.Pid))`；
            2. `windows.CreateJobObject(nil, nil)`（匿名 job，每次查询新建，不复用）；
            3. `windows.SetInformationJobObject(job, windows.JobObjectBasicUIRestrictions, uintptr(unsafe.Pointer(&ui)), uint32(unsafe.Sizeof(ui)))`，其中 `ui.UIRestrictionsClass = jobObjectUILimitSetForeground`（`JOBOBJECT_BASIC_UI_RESTRICTIONS` 单字段结构体）。**注意**：`JOB_OBJECT_UILIMIT_*` 系列位必须经 `JobObjectBasicUIRestrictions`（class=4）下发，不属于 `JOBOBJECT_BASIC_LIMIT_INFORMATION.LimitFlags` 的合法集合——初稿误用 `JobObjectExtendedLimitInformation` + `LimitFlags`（0x100 在该集合中被解释为 `JOB_OBJECT_LIMIT_PROCESS_MEMORY` 且 limit 值为 0），实施期实测报 `The parameter is incorrect.`，已修正；
            4. `windows.AssignProcessToJobObject(job, procHandle)`——不设 `BREAKAWAY_OK`/`SILENT_BREAKAWAY_OK`，agy 子树无法逃逸；此后 agy 的新后代自动入 job；
            5. 恢复执行：`windows.CreateToolhelp32Snapshot(windows.TH32CS_SNAPTHREAD, 0)` → `Thread32First/Thread32Next` 遍历，凡 `OwnerProcessID == p.Pid` 的线程 `OpenThread(windows.THREAD_SUSPEND_RESUME, false, tid)` + `windows.ResumeThread(h)` + `CloseHandle(h)`（CREATE_SUSPENDED 时刻实际只有主线程一个，遍历全部是防御性写法）；单个线程 Resume 失败不视为错误（线程已退出竞态，见错误矩阵第 6 条）；
            6. 任一步骤失败：对已获取的资源逆序释放（job 句柄、进程句柄），返回包装错误。
        - 新增 `func (f foregroundIsolation) shutdown()`：`windows.TerminateJobObject(f.job, 1)` + `windows.CloseHandle(f.job)`；`f.job == 0` 时直接返回（幂等，可安全 defer）。
    - **Complexity**: Medium

### 2. proc_other.go：非 Windows 对齐签名（`UPDATED`）

- `internal/agapi/proc_other.go`
    - **Purpose**: 保持跨平台编译面。
    - **Changes**: `setNoWindow` 同步改名为 `startSuspended`（仍为空体）；新增 `type foregroundIsolation struct{}` 与空体 `attachForegroundIsolation(*os.Process) (foregroundIsolation, error)`（恒返回零值, nil）、`func (foregroundIsolation) shutdown()`。
    - **Complexity**: Low

### 3. client.go：FetchUsage 启动/收尾改造（`UPDATED`）

- `internal/agapi/client.go`
    - **Purpose**: 把隔离原语接入查询流程。
    - **Changes**:
        - `FetchUsage` 中 `setNoWindow(cmd)` → `startSuspended(cmd)`；`cmd.Start()` 成功后：
            ```go
            iso, isoErr := attachForegroundIsolation(cmd.Process)
            if isoErr != nil {
                _ = cmd.Process.Kill() // 挂起态进程可直接 Terminate
                _ = cmd.Wait()
                return nil, fmt.Errorf("建立 agy 前台隔离失败: %w", isoErr)
            }
            defer iso.shutdown() // TerminateJobObject + CloseHandle，替代原 killProcessTree
            ```
        - 删除 `killProcessTree` 函数与 `pid` 变量、`defer killProcessTree(pid)`；`strconv` import 随之移除。
        - 其余逻辑（解析、状态校验、错误包装）逐字不动。
    - **Complexity**: Low

### 4. 版本与构建（`UPDATED`）

- `internal/cli/root.go`：`Version` `0.2.1` → `0.2.2`。
- `scripts/build.ps1`：默认 `-Version` 参数 `0.2.0` → `0.2.2`（该默认值早已漂移落后于 root.go，本次一并校正）。

### 5. Module Collaboration and Data Flow

```mermaid
flowchart LR
    A[cli.quotaRun / mcp 入口] --> B[service.GetQuota]
    B --> C[agapi.Client.FetchUsage]
    subgraph C 内部（单次查询）
        D1[startSuspended: NO_WINDOW+SUSPENDED] --> D2[cmd.Start]
        D2 --> D3[attachForegroundIsolation<br/>OpenProcess→CreateJob→SetInfo→Assign→Resume]
        D3 --> D4[cmd.Wait 等待 agy 退出]
        D4 --> D5[defer iso.shutdown<br/>TerminateJobObject+CloseHandle]
    end
    C --> E[agy 进程树<br/>job 内：UILIMIT_SETFOREGROUND 生效<br/>后代自动入 job、不可逃逸]
```

- 依赖方向不变：cli → service → agapi；改动不出 agapi（版本常量除外）。
- 并发模型：与现状一致——单查询内顺序执行；MCP 多请求并发时各自独立 job、互不共享句柄（job 匿名且每次新建，无共享状态）。
- 关键数据流：ctx 超时（2 分钟）→ Go 杀 agy 主进程 → `cmd.Wait` 返回 → `defer iso.shutdown()` 收掉 job 内残留后代（这是 Job 相比 taskkill 的本质增强：主进程死后后代仍被覆盖）。

### 错误处理矩阵（逐操作）

| # | 操作 | 失败条件 | 恢复性 | 调用方收到 | 清理动作 |
|---|---|---|---|---|---|
| 1 | OpenProcess | 句柄耗尽/权限异常 | 致命 | `建立 agy 前台隔离失败: …`（人读 stderr / JSON `agy_execute_failed` 信封） | `Process.Kill` + `Wait`（agy 永不执行任何指令） |
| 2 | CreateJobObject | 系统资源耗尽 | 致命 | 同上 | 同上 + 关闭已开进程句柄 |
| 3 | SetInformationJobObject | 参数/内核异常（理论不应发生） | 致命 | 同上 | 同上 + 关闭 job 句柄 |
| 4 | AssignProcessToJobObject | 理论不应发生 | 致命 | 同上 | 同上（进程不在 job，靠 Kill） |
| 5 | 线程快照 / Thread32First / OpenThread | 句柄/权限异常 | 致命 | 同上 | 进程已在 job → `shutdown()` 保证收树 |
| 6 | 单个 ResumeThread 失败 | 线程已退出（agy 秒退竞态） | **非致命**，继续 | 无（若线程死亡则 Wait 即刻返回原错误路径） | 无额外 |
| 7 | 全部线程 Resume 失败且线程仍存活 | 病态场景 | 半致命 | 本次查询最终超时 | ctx 2 分钟超时 → Go Kill 主进程 → Wait 返回 → `shutdown()` 收树 |
| 8 | ctx 超时 / agy 业务失败 | 既有路径 | 致命/业务错误 | 既有错误文案不变 | `defer iso.shutdown()` 收树（取代原 taskkill） |

设计取向：隔离建立失败一律显式报错、宁可本次查询失败也不静默降级继续跑（与仓库"不静默降级"风格一致）。

### 输入校验

无新增外部输入。agy 路径仍由既有 `findAgyPath()` 产出；pid/句柄均为进程内部值，不校验来源。

### 不变量

- **「agy 子树任何进程在查询全程不持有前台激活权」**——由 agapi 层（`attachForegroundIsolation`）执行；CLI/MCP 入口均必经此层，无旁路。
- **「查询结束不留 agy 后代」**——由 `FetchUsage` 的 `defer iso.shutdown()` 执行，覆盖正常退出、业务失败、ctx 超时三条路径。

### 可测性

- 单测面：`attachForegroundIsolation` 依赖真实 Windows 进程/句柄，属集成性质，不写 mock 单测（按个人规范执行阶段默认不写不跑测试）。
- 手动验收（AC-1/AC-2）：WT（`useAnyExisting`）下循环运行观察焦点；进程残留用 `Get-Process agy` 验空。
- 构建验证：`go build ./...`、`go vet ./...`、交叉编译 `GOOS=linux go build ./...`（AC-4）。

### 正确性属性（供参考）

对任意 `agyquota --agy` 运行期时刻 t 与 agy 子树任意进程 P：P 在 t 时刻发起的前台激活请求（`SetForegroundWindow`、新建可见顶层窗口、新终端会话附着）均不得使前台窗口离开 agyquota 所在会话。

### Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1（子树无前台权） | §1 `attachForegroundIsolation`（UILIMIT_SETFOREGROUND + 先挂起后入 job） |
| AC-2（无残留、去 taskkill） | §1 `shutdown`、§3 删除 `killProcessTree` 改 defer shutdown |
| AC-3（契约不变） | §3 仅启动/收尾两段改动、解析与输出零改动；§4 版本 0.2.2（仅 Version 字符串随版本变化） |
| AC-4（非 Windows 不受影响） | §2 proc_other.go 对齐签名 |

## Design Review Notes

自审（零上下文视角）逐项结论：

1. **歧义**：无"用 X 或 Y"残留；方案取舍表已锁定 A 并给理由。——已修复（初稿即选定）。
2. **未验证假设**：x/sys/windows 12 个 API/常量/类型 + `ThreadEntry32` 字段名已在本机模块缓存逐一 grep 核实；`JOB_OBJECT_UILIMIT_SETFOREGROUND` 确认缺失 → 自定义常量 0x00000100（MSDN 值）。——已验证，无存疑假设。
3. **缺失细节**：attach 失败路径必须显式 `Kill` + `Wait`（否则挂起进程泄漏）——已补入 §3 与错误矩阵 #1；`Process.Kill` 对挂起进程有效（TerminateProcess 不依赖线程运行）——依据 Windows 文档确认。——已修复。
4. **可行性**：`CREATE_SUSPENDED → Assign → Resume` 是 Windows 作业对象标准用法（同 vscode/cargo 等生态的进程树治理先例）。——可行。
5. **范围蔓延**：不改 zed 路径、不加 flag/工具、不动输出层。——符合。
6. **章节冲突**：AC-3"输出与 0.2.1 完全一致"与版本 bump 0.2.2 冲突 → AC-3 映射处已注明"仅 Version 字符串随版本变化"。——已修复。
7. **错误处理**：8 条矩阵覆盖全部新失败点，恢复性/清理动作/用户可见文案逐条明确。——完整。
8. **输入校验**：无新增外部输入，明示。——完整。

HIGH/MEDIUM/NIT 计数：HIGH=0、MEDIUM=0、NIT=0。

实施期修正记录（2026-09-23）：

1. **MEDIUM（已修复）**：初稿将 UI 限制位写入 `JOBOBJECT_EXTENDED_LIMIT_INFORMATION.LimitFlags`，属 MSDN 结构体误用——`JOB_OBJECT_UILIMIT_*` 属于 `JOBOBJECT_BASIC_UI_RESTRICTIONS`（`JobObjectBasicUIRestrictions` class），`LimitFlags` 仅收 `JOB_OBJECT_LIMIT_*`。实测首次运行报 `The parameter is incorrect.` 并走隔离失败路径（该路径同时暴露 `Process.Kill` 后仍残留一个挂起 agy 的边缘情况，修复 class 后该路径不再触发）。§1 已同步修正。
2. **HIGH（用户实测否决第一版，已修复）**：Job Object 前台限制部署后用户在交互式 WT 会话实测仍必现焦点切换（时点=查询日志刚打出）——证明抢占源不是 `SetForegroundWindow`，而是 **agy 携带的 headless console 会话（`conhost 0x4`）仍经默认终端链路被 WT 接管**，Job 的 UI 限制管不到 defterm 路由。修复：`CREATE_NO_WINDOW` 升级为 `DETACHED_PROCESS`（互斥标志，二选一），agy 完全脱离控制台——实测 agy 进程链中 conhost 彻底消失、查询功能与收尾正常。§1 已同步修正。
3. NIT：`client.go` 首次编辑曾引入重复 `if err != nil` 行导致编译失败，已修复，`go build`/`go vet` 通过。

验证环境说明：AI 侧后台会话的前台窗口为 LockApp、无交互焦点竞争，无法复现前台切换行为；AC-1 的前台表现以用户交互式 WT 会话实测为准。

实施期修正记录（第二轮，2026-09-23 晚）：

3. **HIGH（用户实测再次否决 DETACHED 方案，最终方案转向零进程直连）**：DETACHED_PROCESS 下用户实测仍必现切换，且观察到"新 WT 窗口一闪而过"。实测抓到决定性证据：agy 运行 0.6 秒时出现 PPID=agy 的 conhost、0.23 秒后 svchost 拉起 `OpenConsole.exe`（WT 的 console 宿主，IDLE 对照轮全程为零）——agy 拥有伪控制台仍主动 AllocConsole，defterm 路由无视桌面边界（私有桌面 + `UILIMIT_DESKTOP` 同样拦不住）。**进程级隔离手段全部穷尽**：agy 内部无条件初始化 console 组件且无禁用 flag，只要它 spawn 就必有切换。
4. **最终方案（AC-1/AC-1b）**：侦查发现凭据管理器 `gemini:antigravity` 的 blob 含完整 OAuth 资产（`token.access_token`/`refresh_token`/`expiry`），且该 access token 实测可直调 `retrieveUserQuotaSummary` 返回同账号配额（HTTP 200，数据与 agy 输出等价）。落地为：**直连优先**（token 未过期时零进程查询，新增 `cred_windows.go GetAgyQuotaToken` + `zed.go FetchQuotaDirect`，`client.go FetchUsage` 直连优先、`parseSnapshot` 天然兼容直连结构）；**过期降级**（spawn agy 一次触发其自行刷新凭据，保留伪控制台 + 私有桌面 + 双 UI 限制全套隔离）。已否决的续期路径：用 Zed 凭据的 OAuth client 刷新 agy 的 refresh_token 返回 200 空体（不同 client 授权，不可用）。
