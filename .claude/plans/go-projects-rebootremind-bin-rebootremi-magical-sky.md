# rebootremind 告警时弹终端黑窗修复计划

## Context（背景与动机）

用户发现 `go_projects\rebootremind\bin\rebootremind-dev.exe` 触发告警时，除符合预期的告警通知外还凭空弹出一个终端窗口。目标：根治弹终端，且不破坏 CLI 输出契约。

## 根因（本会话已实测确认）

- **告警链零子进程**：告警弹窗是纯 Win32 `TaskDialogIndirect`（`internal/ui/dialog_windows.go:158`），不 spawn 任何外部命令；全项目仅有的 2 处 `exec.Command`（schtasks / shutdown）均已 `HideWindow + CREATE_NO_WINDOW` 正确隐藏。终端不是子进程弹的。
- **弹的是 exe 自己的控制台**：`bin\` 下两份 exe（dev/正式版）实测 PE **Subsystem=3（CUI 控制台子系统）**，`scripts/build.py:177-186` 的 ldflags 无 `-H=windowsgui`。计划任务 `rebootremind_check`（每小时 :06，动作 = `bin\rebootremind.exe check --notify`）以**无控制台宿主**拉起 CUI exe → Windows 强制为其新建可见控制台 → Win11 下表现为弹出的终端窗口；控制台随告警弹窗存续、dismiss 后进程退出窗口消失，主观即"告警时弹终端"。未达阈值的整点巡检也会闪一下。
- 机制与知识库 kb-052（PE Subsystem/DefTerm 委托）、kb-084（无控制台父进程造黑窗）完全同构。

## 修复方案（GUI 子系统根治 + AttachConsole 保 CLI 契约）

单命令一刀切 `-H=windowsgui` 会让终端裸跑 `status`/`config` 无 stdout（违反 CLI 标准 §4.1 人读输出契约），故必须配套启动引导：

1. **`scripts/build.py`**（~177-185 行）：ldflags 增加 `-H=windowsgui`；同步更新脚本头部使用说明（记录该决策理由：计划任务无控制台宿主拉起不弹窗 + AttachConsole 恢复终端输出）。
2. **新增 `cmd/rebootremind/console_windows.go`**：`attachParentConsole()`——启动早期 `AttachConsole(ATTACH_PARENT_PROCESS)` 挂回父进程控制台；挂接失败（计划任务/双击等无父控制台场景）静默返回保持无窗口；挂接成功且 `GetStdHandle` 句柄无效时，用 `os.NewFile` 重绑 `os.Stdout`/`os.Stderr`（兜底 `os.OpenFile("CONOUT$")`）。用 `windows.NewLazySystemDLL` 惯用法，对齐 `internal/ui/dialog_windows.go:19` 风格；文件头注释写透背景与取舍。
3. **新增 `cmd/rebootremind/console_other.go`**：`//go:build !windows` 空实现（对齐仓库 `_other.go` 桩惯例）。
4. **`cmd/rebootremind/main.go:46`**：`main()` 首行调用 `attachParentConsole()`——必须在 `run(os.Args[1:], os.Stdout, ...)` 之前，保证重绑后的 `os.Stdout` 被传入。

不改动：告警 TaskDialog、已正确隐藏的 2 处 exec、计划任务注册动作路径（exe 原地换新）。

## 构建与发布（用户已确认：随本次打 tag 重建正式版）

顺序敏感：工作区干净是 release 门禁前提。

1. dev 构建 + 验证通过后，子模块内提交修复。
2. 打 tag `rebootremind/v0.1.1`（执行时可改号），`uv run scripts/build.py --release` 重建 `bin\rebootremind.exe`。
3. PE 复检：两份 exe Subsystem 均应为 2（GUI）。

## 验证

- 子模块内：`go build ./...`、`go vet ./...`、`go test ./...` 全绿。
- PE 探针（本会话同款 Python struct 读 `opt+68`）：Subsystem=2。
- CLI 契约：PowerShell 终端裸跑 `bin\rebootremind-dev.exe status` / `--version` / `status --json` 均正常输出（AttachConsole 生效）；`status > out.txt` 重定向仍写文件（句柄有效时不重绑）。
- 告警路径：`bin\rebootremind-dev.exe check --force --notify` → 仅弹 TaskDialog，无新增终端窗口。
- 计划任务路径：`schtasks /Run /TN rebootremind_check`（正式版重建后）→ 无终端窗口，行为与整点触发一致；下次整点 :06 复核。

## 提交切分（仓库规范）

- 子模块 `go_projects/rebootremind`：`rebootremind:fix: 计划任务拉起告警不再弹出控制台窗口`（build.py + console_windows.go + console_other.go + main.go）。
- 父仓库 1：`docs(plans): 增补 rebootremind 弹终端根因与 GUI 子系统决策`（`docs/projects/go_projects/rebootremind/plans/01-rebootremind-plan.md` 单文件独占）。
- 父仓库 2：`chore: 更新 go_projects 子模块指针`。
- 收尾按需 `aoci_maintain` 一次；可选把本案例增补进 kb-052（PE Subsystem 治理同族）。

### 未决问题与阻塞确认清单

- [x] 正式版是否随本次打 tag 重建 → 已确认：随本次打 tag（默认 `rebootremind/v0.1.1`，执行时可改号）。
- 无其余阻塞项。
