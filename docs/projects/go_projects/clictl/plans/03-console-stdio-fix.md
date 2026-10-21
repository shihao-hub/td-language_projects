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

## 验证

- `start --console taskmon`：控制台窗口显示 TUI 并持续运行；`list --running` 可见 pid；关窗后记录闭环。
- 对照：`node -e "console.log(process.stdout.isTTY)"` 在新窗口应为 `true`（用保持窗口的命令观察）。
- 回归：GUI 工具仍走 detached 无空控制台；detached 启动、stop、MCP 不变。
- `go test ./...` / `go vet ./...` / `gofmt`。

## 未决问题（已按推荐关闭）

- [x] 工作目录：设为 exe 所在目录。
- [x] 允许临时启动 node/powershell 做 TTY 断言，测试后清理。
- [x] 不做 `--pause` 保持窗口（保持此前决策）。
