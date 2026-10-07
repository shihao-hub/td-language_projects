# 计划：typeai-gui 终端窗口壳（Wails v3 + xterm.js + ConPTY）

## 背景

`typeai` 是 Go + Bubble Tea 的终端 AI 对话工具（`go_projects/typeai`），TUI 形态成熟。用户需要一个"长得就是终端"的桌面窗口壳：双击打开窗口，窗口内直接呈现原版 TUI，**不重画任何图形界面，typeai 零改动**。

经用户确认，选型为 **Wails v3 终端窗口**方案（备选的 launcher 控制台方案与 Electron/Tauri 均被否决：Electron/Tauri 对 Go 后端只能走 sidecar 且更重；Wails 单二进制且仓内 glmquotawatch-gui 已有先例）。

## 需求

1. 双击 `typeai-gui.exe` 弹出桌面窗口，窗口内是 xterm.js 渲染的终端，运行原汁原味的 typeai TUI。
2. 键盘输入、窗口尺寸变化同步到 PTY；Bubble Tea 的布局与滚动行为原样可用。
3. 关闭窗口时终止 typeai 子进程与 ConPTY 资源，**不残留任何后台进程**。
4. 找不到 typeai.exe 时给出清晰错误提示（弹窗或窗口内红字），不闪退。
5. 壳自身除窗口状态外不产生自有数据；typeai 的数据目录（`%APPDATA%\language_projects\typeai\`）保持不变。

## 关键决策

- **独立新项目 `go_projects/typeai-gui/`**：不塞进 typeai 子项目。理由：typeai 保持纯 CLI/TUI 形态；壳与被壳进程解耦，符合"一个子目录 = 一个项目"与项目间隔离原则。GUI 项目属 go_projects 例外形态，收录理由即本需求（用户明确的桌面终端窗口诉求）。
- **壳不 import typeai 代码**：Go `internal` 包禁止跨模块 import；且 ConPTY 方案天然需要独立进程承载 TTY。
- **typeai.exe 定位优先级**：① 环境变量 `TYPEAI_GUI_TYPEAI_PATH`；② 与 typeai-gui.exe 同目录的 `typeai.exe`；③ 报清晰错误退出。
- **ConPTY 库**：`github.com/aymanbagabas/go-pty`（Windows ConPTY 封装，API 简洁，gliderlabs/ssh 采用）。
- **Wails v3**：版本对齐 glmquotawatch-gui（`wails/v3 v3.0.0-beta.25`），前端数据流用 Wails events（终端吞吐为文本量级，无需 WebSocket）。
- **前端**：`@xterm/xterm` + `@xterm/addon-fit` + `@xterm/addon-web-links`，深色主题，无框架（原生 TS + Vite，保持壳极简）。
- **构建**：统一 `build.py`（PEP 723 + uv，dev/release 自动判定），遵循 go_projects 构建规范。
- **图标**：GUI 项目禁止地鼠图标，配套专属矢量图标流水线 `scripts/render_icon.py`（终端窗口 + 提示符造型），产出多尺寸 `icon.ico` 并注入窗口与 exe 资源。
- **数据目录**：`%APPDATA%\language_projects\typeai-gui\`，按 dev/prod 子目录隔离（仅存窗口尺寸等状态，如有）；写入前自动创建目录链。

## 设计

```text
typeai-gui.exe (Wails v3 窗口)
 ├─ frontend (Vite + TS)
 │   └─ xterm.js Terminal ── onData → Bindings.Write(input)
 │                          ── onResize → Bindings.Resize(cols, rows)
 │                          ← Events Emit "terminal:data" (字节流)
 └─ internal/terminal
     ├─ Session: go-pty 拉起 typeai.exe（继承 ConPTY）
     ├─ 读 goroutine: PTY → events emit("terminal:data")
     ├─ Write/Resize: 前端绑定调用
     └─ Close: 窗口关闭 → kill 进程树 + ClosePseudoConsole，Wait 收尸
```

要点：

- 进程退出检测：PTY 读到 EOF 后 emit `terminal:exit`，前端显示"会话已结束（退出码 N），关闭窗口或按 Ctrl+R 重启"。
- 尺寸同步顺序：先 `pty.Resize` 再通知 TUI（ConPTY 会触发缓冲区变化事件，Bubble Tea 自行重绘）。
- 剪贴板粘贴依赖 typeai 自身的 Ctrl+V 逻辑（它直接读系统剪贴板，无需前端转发）；xterm.js 仅需禁用默认右键菜单冲突。
- 中文与 UTF-8：PTY 管道按字节透传，前端 xterm.js `convertEol` 关闭、UTF-8 解码，与现有 TUI 的 VT 序列完全兼容。

## 任务

- [x] Task 1: 搭建项目骨架
  - 文件：`go_projects/typeai-gui/go.mod`、`main.go`、`internal/guiapp/app.go`、`frontend/`（Vite + TS + xterm.js 最小可编译）、`frontend/wailsjs/` 绑定、`.gitignore`
  - 验证：`go build ./...` 与 `npm run build`（frontend 内）均通过；`wails3 doctor` 无致命项。
- [x] Task 2: ConPTY 终端会话桥接
  - 文件：`internal/terminal/session.go`、`internal/terminal/session_test.go`、`internal/guiapp/bindings.go`、`internal/guiapp/runtime.go`
  - 验证：`go test ./internal/terminal`（用 fake 子进程脚本验证读/写/resize/退出码/无残留）；`go vet ./...` 通过。
- [x] Task 3: 前端终端视图与事件桥
  - 文件：`frontend/src/main.ts`、`frontend/src/terminal.ts`、`frontend/index.html`、`frontend/src/style.css`
  - 验证：`npm run build` 通过；启动应用手工确认：TUI 出现、输入回显、窗口缩放重排、thinking 折叠等按键可用。
- [x] Task 4: 图标流水线与构建脚本
  - 文件：`scripts/render_icon.py`、`build.py`、`internal/guiapp/icon.go`、`.syso` 资源
  - 验证：`uv run scripts/render_icon.py` 产出 1024px PNG 与多尺寸 ico；`uv run build.py --help`；dev 构建产物名带 `-dev` 后缀。
- [x] Task 5: 端到端验收
  - 验证：以真实 GLM 端点跑 `typeai-gui.exe`：发问一轮（流式 + Markdown 渲染）、`/fork` 分支、`Alt+V` 图片、`/resume` 弹窗；关闭窗口后 `Get-Process` 确认 typeai 进程为 0；非 TTY 错误路径（找不到 typeai.exe）提示清晰。
- [ ] Task 6: 提交与归档
  - 验证：typeai-gui 在 go_projects 子仓内完成 `feat` 提交；本计划勾选状态单独成笔提交。

## 执行记录

- 2026-10-07 全部实施完成。关键事实与偏差：
  - ConPTY 收尾踩坑（均有实验依据，见 `internal/terminal/session.go` 注释）：
    子进程退出后 conhost 不关闭输出管道（Read 永不 EOF，"等自然 EOF"死锁）；
    Wait 后立即 ClosePseudoConsole 会与 conhost 末批写入并发（堆损坏
    0xc0000374）。最终方案：Wait → 300ms flush 宽限 → 关 PTY → 读循环被
    唤醒 → OnExit；另设 5s 看门狗兜底僵死进程。Windows os.Pipe 不支持
    SetReadDeadline（实验验证），轮询读方案不可行。
  - `go-pty` 的 `Command()` 返回自有 `*pty.Cmd`（Windows 不可用 exec.Cmd，
    上游 issue go#62708）；ConPTY 初始尺寸须在 Start 前 Resize。
  - Task 4 实际落文件为 `internal/version/version.go`（ldflags 注入）+
    windres 生成 `.syso`（替代计划中的 icon.go；Wails 窗口图标随 PE 资源）。
  - Task 3 文件合并为 `frontend/src/main.ts`（无独立 terminal.ts）；guiapp
    无 runtime.go（壳无监控运行时，只有 bindings.go）。
  - Task 5 自动化部分完成：进程链路（GUI→ConPTY→typeai.exe）冒烟通过、
    关窗无残留钩子验证通过、release 拒绝路径验证通过；真实 GLM 对话、
    /fork、Alt+V、/resume 的人工视觉验收待用户确认。
- 涉及本计划的父仓提交：计划创建（dda3cd6）与本归档更新各一笔。

## 约束回查

- 数据文件只落 `%APPDATA%\language_projects\typeai-gui\`（缺 APPDATA 回退 `~/.language_projects/`），禁写外部文件目录。
- 测试资源用后即清：验证用的临时目录、fake 子进程在测试内自清理。
- GUI 专属图标规范已纳入 Task 4；窗口初始化显式绑定图标。
- 提交规范：`typeai-gui:feat: ...`（子仓内一项目一目录），计划文件变动独立提交。

## 决策记录

- 2026-xx-xx 用户确认路线 2（Wails 终端窗口），并澄清核心诉求为"GUI 就是终端结构，不需要复杂样子"。
- Electron 与 Tauri 被否：壳重、且对 Go 后端均需 sidecar，无收益。
