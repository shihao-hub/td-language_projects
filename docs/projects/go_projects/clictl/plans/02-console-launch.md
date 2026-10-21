# clictl 命令行工具终端启动（console 模式）

- 背景：WebUI「启动」走 `start`（DETACHED_PROCESS，无控制台）。`taskmon.exe` 等 console 程序启动后不可见、无窗口，用户误以为没启动。
- 目标：新增「终端启动」模式，为 console 程序开独立控制台窗口；GUI 程序维持后台分离启动。
- 用户已确认：1) 原生 conhost，不接 Windows Terminal；2) 不做「秒退保持窗口」；3) 按 PE 子系统自动切换主按钮；4) CLI 与 WebUI 共用同一实现。

## 一、后端

| 层 | 改动 |
|---|---|
| `runner/subsystem.go` | 新增 `IsConsoleExe(path)`：读 PE 头 `Subsystem`，3 = console，其余按 GUI 处理，读失败返回 false |
| `runner/start.go` | 新增 `StartMode`（`detached` / `console`）与 `StartConsole`：`CREATE_NEW_CONSOLE` 启动，`go Wait()` 回写 duration/exit_code 闭环；`StartResult` 增加 `mode` |
| `service/process.go` | 新增 `StartConsole`，错误映射与 `Start` 一致 |
| `service/tools.go` | `InfoResult` 增加 `console`（PE 子系统探测结果） |
| `api/server.go` | `POST /api/tools/{name}/start` 接受 `mode`；为空时按 `IsConsoleExe` 自动选择；非法值 400 |
| `cli` | `start --console <name> [args...]`，`--console` 只在前置段生效，工具参数不受影响 |

- 记账沿用 launches 表：pid 为真实 exe，路径比对探活、`list --running`、`stop` 树杀全部可用；窗口关闭 → Wait 返回 → 记录闭环。
- 不新增表字段；`mode` 仅出现在启动结果 JSON。

## 二、前端

- 详情标题旁增加类型徽标：`命令行` / `窗口程序`。
- 主按钮：console → 「终端启动」；GUI → 「启动」（后台分离）。
- console 工具额外显示「后台启动」次按钮；带参数启动沿用主模式。
- 启动成功 toast 标注模式（终端窗口 / 后台）。

## 三、验证

- `go test ./...` / `go vet ./...` / `gofmt`。
- `IsConsoleExe` 单测：`cmd.exe`(3)=true、`explorer.exe`(2)=false、不存在路径=false。
- 实测：`start --console ping -- -n 20 127.0.0.1` 弹控制台窗口；`list --running` 可见；`stop` 后闭环。
- WebUI 实测 taskmon：点「终端启动」出现控制台窗口，记录闭环。
- GUI exe 走后台启动不产生空控制台窗口。

## 未决问题（已按推荐关闭）

- [x] 终端实现：原生 conhost（`CREATE_NEW_CONSOLE`）。
- [x] 不做「保持窗口」，避免 `cmd /k` 导致 pid/探活语义破坏。
- [x] 按 PE 子系统自动切换主按钮。
- [x] CLI 与 WebUI 同时支持，共用 `runner` 实现。
