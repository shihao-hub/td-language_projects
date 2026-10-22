# typeai-gui（已归档）

- **归档日期**：2026-10-22
- **原路径**：`go_projects/typeai-gui`
- **归档原因**：`go_projects/typeai` 已按 `sh-go-wails-desktop` 标准改造为双通道产物，桌面工作台由 `typeai-gui.exe` 直接提供（原生 WebUI + HTTP/SSE），不再需要独立的 ConPTY + xterm.js 终端外壳。
- **替代方案**：
  - `go_projects/typeai` → `typeai-gui.exe`：双击打开桌面工作台。
  - `go_projects/typeai` → `typeai-cli.exe`：原终端 TUI 与管理命令，新增 `serve`。
- **历史**：原项目已从 `go_projects` 子仓删除，git 历史仍可通过子仓提交记录追溯。
- **相关文档**：本目录 `docs/specs/01-universal-terminal-shell/`（未实施的通用终端壳设计，作为历史资料保留）。
- **恢复**：如需重启该项目，将本目录内容移回 `go_projects/typeai-gui` 并重新纳入子仓跟踪。
