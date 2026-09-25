# Task List

- [x] 1. 扩展阈值评估结果，记录本轮完整新触发档位
  - Files: `go_projects/glmquotawatch-gui/internal/quota/threshold.go`, `go_projects/glmquotawatch-gui/internal/quota/quota_test.go`
  - 实现细节：给 `Outcome` 增加 `Newly []int`，在触发通知时按升序填充所有本轮未通知且低于等于当前百分比的阈值。
  - Verify: `go test ./internal/quota`；新测试应证明一次跨多档时 `Newly` 保留完整档位集合。
  - Ref: AC-3
  - [test]
- [x] 2. 拆分提交式采样与未提交采样
  - Files: `go_projects/glmquotawatch-gui/internal/service/service.go`, `go_projects/glmquotawatch-gui/internal/service/service_test.go`
  - 实现细节：新增私有 `sampleResult` 和 `sample(ctx, commit)`；`SampleOnce` 保持先保存状态，新增 `SampleUncommitted` 不写 `state.json` 且确认前视图使用 `prev`。
  - Verify: `go test ./internal/service`；未提交采样跨档后 `state.json` 不新增档位，`SampleOnce` 语义保持不变。
  - Ref: AC-1, AC-2, AC-5
  - [test]
- [x] 3. 实现 Toast 成功门闩、失败重试与状态错误钩子
  - Files: `go_projects/glmquotawatch-gui/internal/service/daemon.go`, `go_projects/glmquotawatch-gui/internal/service/daemon_test.go`
  - 实现细节：daemon 改用未提交采样；通知成功后合并 pending `Newly` 并保存状态；失败时发出 `notify_failed`、保留 pending 下一轮重试；滞回清空、窗口消失或阈值指纹变化时丢弃 pending。`DaemonHooks` 增加 `OnNotifyError`。
  - Verify: `go test ./internal/service -race`；fake 通知失败时不写状态并回调错误，下一轮成功后完整记账。
  - Ref: AC-1, AC-2, AC-3
  - [test]
- [x] 4. 修复 Wails 必填 ID 并接入 GUI 通知错误
  - Files: `go_projects/glmquotawatch-gui/internal/guiapp/runtime.go`, `go_projects/glmquotawatch-gui/internal/guiapp/bindings.go`, `go_projects/glmquotawatch-gui/frontend/src/App.vue`, `go_projects/glmquotawatch-gui/frontend/src/pages/Dashboard.vue`
  - 实现细节：`NotificationOptions.ID` 使用 `glmquotawatch-gui-<UnixNano>`；新增 `notify-error` 事件；GUI 手动采样改用未提交路径；错误横幅区分 `notify_failed` 与 `state_save_failed`。
  - Verify: `go test ./...` 和 `npm run build`；schema/help 契约无需变化，但 GUI 构建必须通过。
  - Ref: AC-1, AC-2
  - [test]
- [x] 5. 更新文档并完成端到端验证
  - Files: `go_projects/glmquotawatch-gui/README.md`, `docs/projects/go_projects/glmquotawatch-gui/specs/02-demo-toast-no-alert/tasks.md`
  - 实现细节：README 说明 Toast 发送成功才记账、失败重试、Wails 成功不等于系统横幅展示；更新任务状态和实施记录。
- Verify: 在项目根执行 `gofmt -w .`、`go build ./...`、`go vet ./...`、`go test ./...`、`go test -race ./...`、`npm run build`；再用临时 demo 复测 50% Toast 交付。
- Ref: AC-1, AC-2, AC-4, AC-5

## Implementation Notes

- 2026-09-25：Task 1-5 已完成。`go build ./...`、`go vet ./...`、`go test ./...`、`go test -race ./...` 和 `npm run build` 通过。
- 真实 demo 复测：14:00:15 与 14:00:45 的 Windows 事件日志分别记录 tracking id 7037/7038 delivered to `glmquotawatch-gui`；`state.json` 在对应 Toast 成功后记录 `[50]` 和 `[50,60]`。
