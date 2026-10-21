# clictl 终端启动 stdio 修复（console 子进程 isTTY）

- 现象：`start --console taskmon` 弹出控制台窗口但空白，约 2 秒后关闭，记录 `exit_code=0`。
- 根因：`os/exec` 把未设置的 stdin/stdout/stderr 一律替换为 `os.DevNull` 并设置 `STARTF_USESTDHANDLES`，因此 `CREATE_NEW_CONSOLE` 的子进程 stdout 仍指向 NUL；taskmon 以 `stdout.isTTY` 判定交互模式（`src/main.ts:44`），false 时走单帧分支并 `process.exit(0)`（`src/main.ts:752-785`）。
- 结论：问题在 clictl 的启动实现，不在 taskmon；同样影响所有依赖 TTY 的命令行工具。

## 修复

`runner.StartConsole` 弃用 `os/exec`，改用原生 `windows.CreateProcess`：

| 参数 | 取值 | 原因 |
|---|---|---|
| `CreationFlags` | `windows.CREATE_NEW_CONSOLE` | 分配独立控制台窗口 |
| `StartupInfo.Flags` | `0`（不设 `STARTF_USESTDHANDLES`） | 让系统把标准句柄初始化为新控制台，stdout 才是 TTY |
| `InheritHandles` | `false` | 不继承 GUI 父进程的无效句柄 |
| `CommandLine` | `syscall.ComposeCommandLine([path, args...])` | 正确转义，避免空格/引号问题 |
| `CurrentDirectory` | exe 所在目录 | 贴近双击语义 |

- 启动后用 `WaitForSingleObject` + `GetExitCodeProcess` 在 goroutine 内闭环记账；立即关闭 thread 句柄，Wait 后关闭 process 句柄。
- pid 仍为真实 exe，`list --running`、`stop` 树杀、路径探活语义不变；`Start`（DETACHED）保持原样。

## 验证（已完成）

- [x] `start --console taskmon`：窗口出现并显示完整 TUI（415 进程、分组视图），标题 `taskmon`，持续运行；`list --running` 可见 pid；`stop` 树杀闭环。
- [x] TTY 断言：新窗口内 PowerShell `[Console]::IsInputRedirected` / `IsOutputRedirected` / `IsErrorRedirected` 全部为 `false`（即均为控制台设备，非 NUL/管道）。
- [x] 窗口类名为 `ConsoleWindowClass`（原生 conhost，符合既定选择）。
- [x] 回归：`go test ./...` / `go vet ./...` / `gofmt -l` 通过；detached 与 GUI 工具行为不变。
- [x] 测试资源已清理（taskmon 进程、临时库与截图脚本）。

## 实施记录

- 代码提交：`clictl:fix: 终端启动改用原生 CreateProcess 修正 isTTY`（4 文件）。
- 关键实现：`spawnConsoleProcess`（appName/CommandLine、Flags=0、InheritHandles=false、CurrentDirectory=exe 目录、立即关 thread 句柄），goroutine `WaitForSingleObject` + `GetExitCodeProcess` 闭环。

## 未决问题（已按推荐关闭）

- [x] 工作目录：设为 exe 所在目录。
- [x] 允许临时启动 node/powershell 做 TTY 断言，测试后清理。
- [x] 不做 `--pause` 保持窗口（保持此前决策）。
