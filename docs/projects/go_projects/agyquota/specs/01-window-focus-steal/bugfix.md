# Bug Fix Document

## Summary

在 PowerShell（Windows Terminal）中启动 `agyquota --agy` 查询配额时，偶发（"有时候"）系统焦点被切换到隔壁的窗口（另一个 Windows Terminal 窗口），打断用户当前操作。

## Reproduction

间歇性问题，无法稳定复现，但触发环境与链路已实测确认：

1. 前置环境（本机已实测）：
   - Windows 11「默认终端应用程序」= Windows Terminal；
   - Windows Terminal `settings.json` 中 `"windowingBehavior": "useAnyExisting"`（任何新终端会话都附着到最近使用的现有 WT 窗口，并把该窗口带到前台）。
2. 触发步骤：在 WT 的某个窗口/tab 中运行 `agyquota --agy`；
3. 当 `agy` 内部产生新的终端会话/前台激活请求时（间歇性），WT 按 `useAnyExisting` 把隔壁的 WT 窗口提到前台——用户感知为"启动 agyquota 时帮我切换到了隔壁的窗口"。

## Root Cause

根因是三层叠加，agyquota 自身缺少对子进程树的「前台隔离」防线：

1. **agyquota 的静默标志只保护直接子进程，保护不到 agy 的后代**（`internal/agapi/proc_windows.go`）：`CREATE_NO_WINDOW + HideWindow` 只作用于 agy 进程本身的创建；agy 在运行期会自行 spawn 子进程并建立新的 console 会话（实测每次都出现 PPID=agy 的 `conhost.exe 0x4`），这些孙进程的窗口/前台行为完全不受 agyquota 控制。
2. **agy 无条件主动请求新 console 会话，defterm 路由无视一切隔离手段**：实测依次否决四种隔离——① Job Object `UILIMIT_SETFOREGROUND`（路由不是 `SetForegroundWindow` 调用，管不到）；② `DETACHED_PROCESS`（agy 运行期主动 AllocConsole，实测 spawn 后 0.23 秒 svchost 即拉起 WT 宿主 `OpenConsole.exe`）；③ ConPTY 伪控制台（agy 检测后仍 AllocConsole）；④ 私有桌面 + `UILIMIT_DESKTOP`（defterm 路由无视桌面边界，OpenConsole 照常出现）。agy（197MB 单文件、完整交互式 CLI）内部无条件初始化 console 组件且无禁用 flag，其 console 会话每次都会经 defterm 链路被 WT 接管，WT 再按 `windowingBehavior: "useAnyExisting"` 前台化最近使用的现有 WT 窗口——即"切到隔壁窗口"。
3. **收尾链路多一个 console 环节**：`FetchUsage` 结束时用 `taskkill /F /T /PID` 强杀进程树（`internal/agapi/client.go`），taskkill 本身又是一个新起的 console 进程，放大同一路径暴露面。

注：agy 是外部闭源二进制（`%LOCALAPPDATA%\agy\bin\agy.exe`，197MB 单文件、CONSOLE 子系统），其内部行为无法修改，只能在 agyquota 侧隔离或绕开。

## Impact

- 影响所有走 `--agy` 数据源的调用方：CLI 人读模式、`--json` 模式、MCP 入口（`internal/mcp` 同样经 `agapi.Client` 调 agy）；
- `--zed` 数据源为纯 HTTP 直连（`internal/agapi/zed.go`），不 spawn 进程，不受影响；
- 不影响查询结果的正确性，仅影响前台焦点体验。

## Fix Acceptance Criteria

### AC-1（最终方案：零进程直连优先）

WHEN 凭据管理器 `gemini:antigravity` 中的 access token 未过期（实测有效期约 1 小时），`agyquota --agy` 直接用该 token 调 `retrieveUserQuotaSummary`（与 `--zed` 同款端点/UA/解析），**全程不 spawn 任何进程**——console 会话不存在，WT 收不到任何会话请求，前台焦点零扰动；实测监控 agy 链路 conhost/OpenConsole 均为零、数据与 agy 输出等价（同账号同接口）。

### AC-1b（token 过期时的降级路径）

WHEN 本地 access token 已过期或直连失败，查询自动回退 spawn agy（保留伪控制台 + 私有桌面 + 作业双 UI 限制 + 挂起启动全套隔离，尽力压低切换概率）；agy 运行会自行刷新凭据管理器中的 token，下次查询恢复直连——窗口切换频率被压到每小时至多一次且仅在用户实际查询时发生。

### AC-2

WHEN agy 正常退出、查询失败或 2 分钟超时被取消，修复后进程树回收改由 Job Object 兜底（`TerminateJobObject`），不再经 `taskkill` 外部命令，查询结束后系统中不残留任何 agy 后代进程。

### AC-3

WHEN 分别以人读、`--json`、`--raw`、MCP 入口调用 `--agy` 查询，修复后输出内容、JSON 信封结构、退出码与 0.2.1 版本完全一致（`parseSnapshot` 天然兼容直连响应的 `bucketId/displayName` 结构与 agy 包装结构）；改动仅限 `internal/agapi` 的数据获取路径。

### AC-4

WHEN 在非 Windows 平台构建（`internal/agapi/proc_other.go`、`cred_other.go` 路径），修复后保持原 no-op 行为，交叉编译不受影响。
