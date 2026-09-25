# 计划：typeai session HTML export

**问题陈述**：`typeai` 第一期已经把成功轮次持久化为 JSON，但用户阅读时仍要自己解析 JSON。第二期先提供一个单文件 `export` 子命令，把指定 session JSON 转成人类可读 HTML，不引入终端界面美化。
**需求**：
1. 新增 `typeai export SESSION_JSON [--output FILE] [--json]`。
2. 不传 `--output` 时，默认写入 session 文件同目录的同名 `.html` 文件。
3. `--json` 输出现有 `{ok,data}` 包络；人读输出只报告输出路径、消息数和字节数。
4. HTML 使用标准库 `html/template` 转义；保留换行，不解析 Markdown，不加颜色、动画或终端状态美化。
5. 更新 `help`、`schema` 与 README；不引入 MCP，延续现有例外理由。
6. 沿用第一期已确立的测试偏好：补齐业务加载、渲染和 CLI 契约测试，并执行构建、静态检查与测试。
**背景**：
- `session.Store` 当前只负责生成路径和原子保存，没有读取/校验 session JSON 的入口。
- CLI 命令契约由 `commandContracts()` 同源生成，`help` 与 `schema` 已复用该目录。
- 项目当前只有 Go 标准库依赖，架构分层为 CLI、service、LLM、session、config。
**方案**：
- 在 session 层新增 `Load`，严格读取并校验 `schema_version=1`、会话 ID、模型、时间戳、`user/assistant` 消息顺序与内容，拒绝未知字段；读取失败不产生 HTML。
- 在 service 层新增 `Export` 纯渲染用例：输入 `session.Session`，输出 UTF-8 HTML 字节；HTML 展示会话元数据、角色、时间与正文，`reasoning_content` 本来就不入库，因此也不会出现在导出里。
- 输出文件用同目录临时文件写入、`Sync` 后原子替换；目标默认为输入路径去掉 `.json` 后缀再加 `.html`，不允许输出路径与输入路径相同。
- CLI 负责参数解析、默认输出路径计算、`--json` 包络、stderr 错误与退出码；业务校验和渲染不放入 CLI。
**任务分解**：
- [ ] Task 1: 实现 session JSON 读取校验 待办
  - 文件：`go_projects/typeai/internal/session/store.go`、`go_projects/typeai/internal/session/store_test.go`
  - 实现：新增 `Load(path string) (Session, error)`，复用稳定错误文案风格，覆盖 JSON 损坏、版本错误、未知字段、空 ID/模型、非法消息角色和空消息。
  - 验证：在 `go_projects/typeai` 执行 `go test ./internal/session`，预期新增与既有 session 测试全部通过。
  - Demo：对第一期真实 session JSON 调用 `Load` 能返回完整消息列表。
- [ ] Task 2: 实现纯 HTML 导出与原子写入 待办
  - 文件：`go_projects/typeai/internal/service/export.go`、`go_projects/typeai/internal/service/export_test.go`
  - 实现：新增 `Export(session.Session) ([]byte, error)` 和 `WriteAtomic(path string, data []byte) error`；模板只做可读 HTML，正文使用 `white-space: pre-wrap`。
  - 验证：在 `go_projects/typeai` 执行 `go test ./internal/service`，预期 HTML 正确转义用户文本、保留换行、包含元数据，写入中途失败不产生损坏目标。
  - Demo：给一个两轮 session 渲染后可得到包含用户与助手正文的 UTF-8 HTML。
- [ ] Task 3: 接入 CLI 契约与文档 待办
  - 文件：`go_projects/typeai/internal/cli/export.go`、`go_projects/typeai/internal/cli/export_test.go`、`go_projects/typeai/internal/cli/run.go`、`go_projects/typeai/internal/cli/schema.go`、`go_projects/typeai/internal/cli/help.go`、`go_projects/typeai/README.md`
  - 实现：分发 `export`；`flag` 解析一个位置参数与 `--output/--json`；人读/JSON 成功输出与 `bad_args`、`not_found`、`invalid_session`、`internal` 错误映射；同源更新命令契约；README 补示例与限制。
  - 验证：在 `go_projects/typeai` 执行 `go test ./internal/cli`，并解析 `go run ./cmd/typeai schema`，预期包含 export 且 JSON 可解析。
  - Demo：`typeai export <session.json>` 生成同名 HTML，`--json` 返回输出路径、消息数和字节数。
- [ ] Task 4: 端到端验证与收尾 待办
  - 文件：`go_projects/typeai/internal/**`、`go_projects/typeai/README.md`
  - 实现：完成接线检查，更新计划执行记录；确认不影响无参数对话、config、schema、help 与 version。
  - 验证：在 `go_projects/typeai` 依次执行 `gofmt -w .`、`go build ./...`、`go vet ./...`、`go test ./...`、`go test -race ./...` 与 `.\build.ps1 -Version dev`，全部预期通过；再用临时 APPDATA 中的小型 session 执行 export。
  - Demo：`.\build\typeai.exe export <临时session.json> --output <临时export.html> --json` 成功，退出码 0，测试资源清理完成。

---
- 最后更新：2026-09-25
- 作者：AI
- 版本：v1.0
