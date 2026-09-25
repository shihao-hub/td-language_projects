# Plan for: "glmquotawatch-gui 托盘图标对齐 Wails W"

**问题陈述**：应用 exe/任务栏当前使用 Wails 默认 W 图标，托盘却使用项目根 `icon.ico` 中的 Go 地鼠，两处视觉不一致。本次只处理 Windows GUI 图标来源，不改托盘菜单、业务逻辑和前端界面。

**需求**：
- 用户希望托盘图标与启动后看到的 W 图标对齐。
- 经只读确认，W 图标来自 `go_projects/glmquotawatch-gui/build/windows/icon.ico`；项目根 `icon.ico` 是 Go 地鼠，托盘当前通过 `//go:embed icon.ico` 使用它。
- 计划默认采用“复用 W 图标”方案：托盘直接嵌入既有 `build/windows/icon.ico`，不引入新设计。
- 计划默认按“构建 + 托盘确认”验证；如用户批准时改为“只做构建”或“只改不测”，以批准时的选择为准。

**背景**：
- `main.go` 用 `//go:embed icon.ico` 嵌入托盘字节，并传给 `guiapp.RunOptions.Icon`。
- `internal/guiapp/tray.go` 调用 `a.tray.SetIcon(a.icon)`，Wails v3 beta.25 支持 `[]byte` 图标。
- `build/windows/icon.ico` 由 `wails3 generate syso -icon windows/icon.ico` 注入 exe，因此它就是当前启动后看到的 W 图标。
- 项目根 `icon.ico` 与 `build/windows/icon.ico` 是不同文件：前者为 Go 地鼠，后者为 Wails W；继续保留会造成“同源”注释与实际不一致。
- 父仓与 Go 子仓均存在无关未提交改动，所有变更和提交必须限定在 `glmquotawatch-gui`。

**方案**：删除冗余的项目根 `icon.ico`，让 Go 入口直接嵌入 `build/windows/icon.ico`，使托盘、exe、任务栏和开始菜单共用同一份 Wails W 图标；同步修正源码注释和 README，避免继续描述为项目根同源文件。无需修改 `internal/guiapp` 的运行时逻辑。

**任务分解**：
- [ ] Task 1: 托盘图标切换到 Wails W 并收敛图标来源 待办
  - 文件：`go_projects/glmquotawatch-gui/main.go`、`go_projects/glmquotawatch-gui/internal/guiapp/app.go`、`go_projects/glmquotawatch-gui/README.md`、删除 `go_projects/glmquotawatch-gui/icon.ico`
  - 实现：将 `//go:embed icon.ico` 改为 `//go:embed build/windows/icon.ico`；更新变量注释与 `RunOptions.Icon` 注释为 `build/windows/icon.ico`；修正 README 图标来源说明；删除不再使用的根 `icon.ico`。
  - 验证：在 `go_projects/glmquotawatch-gui` 执行 `wails3 task windows:build`，预期构建成功且生成 `bin\glmquotawatch-gui.exe`。
  - Demo：启动构建产物后，托盘显示与 exe/任务栏一致的 Wails W 图标。
- [ ] Task 2: 短暂启动确认托盘并清理运行进程 待办
  - 文件：无新增/修改；仅检查 `go_projects/glmquotawatch-gui\bin\glmquotawatch-gui.exe`
  - 实现：以生产 exe 启动应用，等待托盘/窗口初始化后人工或截图确认 W 图标，随后通过托盘菜单或终止该启动进程退出。
  - 验证：托盘显示 Wails W；任务结束后无 `glmquotawatch-gui.exe` 本轮启动进程残留。
  - Demo：提供托盘状态说明或截图结论，确认托盘与应用图标一致。

---

**最后更新**：2026-09-25
**作者**：Codex
**版本**：v1
