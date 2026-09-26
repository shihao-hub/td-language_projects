# Task List

- [ ] 1. 建立分支树领域模型与 schema version 3 数据结构
  - Files: `internal/session/store.go`, `internal/session/branch.go`, `internal/session/store_test.go`, `internal/session/branch_test.go`
  - 实现细节：新增 `Branch`、根分支/激活分支字段、父历史解析、Fork 索引校验和唯一 branch ID；将 schema version 2 的线性 `Messages` 映射为 `main` 分支；保持现有原子写盘与旧字段读取兼容。
  - Verify: `go test ./internal/session`，预期 session v2 读取、v3 round-trip、非法父关系和 Fork 索引校验全部通过。
  - Ref: AC-2, AC-5, AC-6, AC-7
  - [test]

- [ ] 2. 将 TUI 的单线消息状态重构为按分支管理的运行时状态
  - Files: `internal/tui/model.go`, `internal/tui/branch.go`, `internal/tui/model_test.go`
  - 实现细节：增加 branch map、`activeBranchID` 和每分支的 messages/active/running/status/cancel 状态；把当前输入框和 viewport 作为激活 Tab 的渲染投影；切换分支时保存/恢复输入草稿并重建 transcript；没有 Fork 时保持 `main` 单分支行为。
  - Verify: `go test ./internal/tui`，预期现有输入、动态高度、取消和单分支流式测试继续通过。
  - Ref: AC-2, AC-3, AC-8

- [ ] 3. 实现 Fork 命令、稳定消息边界校验和分支切换命令
  - Files: `internal/tui/model.go`, `internal/tui/view.go`, `internal/cli/help.go`, `README.md`
  - 实现细节：实现 `/fork`、`Ctrl+Shift+F` 和 `/branch <id>`；使用最近一条已完成 AI 消息作为 Fork 边界；流式中、无可继承消息或当前回合失败时拒绝；增加 Tab 条、当前分支标记、`Ctrl+PageUp/PageDown` 切换与文本命令回退入口；保留 `/fork` 作为终端无法传递 `Ctrl+Shift+F` 时的可靠入口。
  - Verify: `go test ./internal/tui` 与 `go build ./...`，预期可创建子分支、切换 Tab、拒绝非法 Fork，且 CLI help 包含新入口。
  - Ref: AC-1, AC-3, AC-7, AC-8

- [ ] 4. 为流式事件和异步渲染增加 branch ID / turn ID 路由
  - Files: `internal/tui/stream.go`, `internal/tui/model.go`, `internal/tui/render_job.go`, `internal/tui/stream_test.go`
  - 实现细节：为 delta/result 消息增加 branch ID 与 turn ID；启动请求时绑定身份；`applyDelta`、`finishStream`、取消和错误处理只更新目标分支；Markdown 异步渲染结果应用前校验 generation、branch 和 source key；切换 Tab 不取消隐藏分支的请求。
  - Verify: `go test ./internal/tui`，预期交错到达的两个分支事件不会互相污染，隐藏分支完成后切回能看到完整结果。
  - Ref: AC-4, AC-8
  - [test]

- [ ] 5. 接入分支请求上下文与 session 原子保存边界
  - Files: `internal/service/chat.go`, `internal/tui/model.go`, `internal/session/store.go`
  - 实现细节：发送前通过分支历史解析得到有序消息，不改变现有 LLM 协议；已持久化 session 创建分支、切换激活分支和成功完成回合时保存 schema v3；保存失败保留内存状态并显示错误，不覆盖旧 session；首次成功回答前继续遵守当前“不写正式 session”的行为。
  - Verify: `go test ./internal/session ./internal/service ./internal/tui`，预期分支请求上下文顺序正确，原子写盘失败不损坏已有文件。
  - Ref: AC-2, AC-5, AC-6, AC-7
  - [test]

- [ ] 6. 实现按 session ID 的 /resume 恢复入口
  - Files: `internal/session/store.go`, `internal/service/chat.go`, `internal/tui/model.go`, `internal/cli/help.go`, `README.md`
  - 实现细节：实现只接受 8 位小写十六进制 session ID 的加载接口，扫描应用自己的 sessions 目录但不向用户展示目录；在 TUI 空闲且输入无未提交内容时处理 `/resume <session-id>`，成功后替换 Chat Store、session 元数据、分支树、激活 Tab 和 viewport；失败时保持当前会话不变；schema v2 在内存中迁移为 `main` 分支，后续保存写成 schema v3。
  - Verify: `go test ./internal/session ./internal/service ./internal/tui`，预期合法 ID 恢复成功，非法/不存在 ID、运行中恢复和脏输入恢复被拒绝，v2 session 可迁移。
  - Ref: AC-5, AC-6, AC-9, AC-10, AC-11
  - [test]

- [ ] 7. 补齐分支恢复、兼容性和用户文档
  - Files: `internal/session/store.go`, `internal/session/store_test.go`, `internal/tui/model_test.go`, `README.md`, `internal/cli/help.go`
  - 实现细节：覆盖 schema v2 到 v3 的读取迁移、schema v3 分支恢复、激活 Tab 恢复、`/resume <session-id>` 帮助和首版范围说明；明确鼠标右键选区、精确字符 Fork、双 Pane、session 列表和目录浏览为后续范围。
  - Verify: `go test ./...`、`go build ./...`、`.\build.ps1 -Version dev`，预期全仓 typeai 测试和构建通过，生成的可执行文件可启动 TUI。
  - Ref: AC-5, AC-6, AC-8, AC-9, AC-11

- [ ] 8. 完成真实 TTY 手工验收与发布前检查
  - Files: `internal/tui/model.go`, `internal/tui/view.go`, `internal/session/store.go`, `README.md`
  - 实现细节：在 Windows Terminal 中验证 `/fork`、Tab 切换、父子上下文、分支独立流式响应、`/resume <session-id>`、重启恢复和窄终端布局；记录 `Ctrl+Shift+F` 若被终端吞掉时使用 `/fork` 的备用路径；确认没有残留进程和临时 session 文件。
  - Verify: `.\build\typeai.exe`，预期手工验收完成后退出 TUI，后台无残留 typeai 进程；该任务不替代自动化测试。
  - Ref: AC-1, AC-3, AC-4, AC-5, AC-7, AC-9
