# 06 - agyquota: 添加 --once 单次查询与临时 daemon 自动回收支持

## 概述

📋 Plan for: "为 agyquota CLI 添加 --once 标志，实现一行命令启动临时 daemon、获取结果并自动终止清理（0 残留）"

**问题陈述**：
当前用户查询配额时，常因本地处于开发构建态（非干净正式 Tag）被拦截自动拉起，必须在另一终端先手动执行 `agyquota serve`，再执行 `agyquota --zed`。且用户很多时候只需要查看单次结果，不需要常驻 daemon 占用系统端口与资源。

**需求确认**：
1. **参数契约**：根命令与 quota 命令支持 `--once` 参数（如 `agyquota --zed --once`）；
2. **选项 A 行为（已有 daemon 保护）**：若检测到后台已有常驻 daemon 在运行，则直接复用该 daemon 查完即走，保留原常驻 daemon；
3. **临时实例编排与自动回收**：若未检测到常驻 daemon，则由客户端自动拉起临时专属 daemon 子进程（附带 `--idle-timeout 10s` 兜底），查询完成后通过 `defer` 调用 `/v1/stop` 优雅关停并清理地址文件，实现后台 0 残留；
4. **开发构建豁免**：在 `--once` 模式下，豁免开发构建（`!buildinfo.IsProduction()`）不自动拉起 daemon 的限制；未传 `--once` 时的报错提示追加 `--once` 使用建议；
5. **架构不变量坚守**：保持《CLI 工具开发标准 v2》规定的薄客户端原则，CLI 壳层绝不直接 import `internal/service`（通过 `go list -deps` 校验）。

---

## 任务分解

- [x] Task 1: 客户端扩展支持 --once 与临时 daemon 生命周期管理 ✅ 完成
  - 文件：`go_projects/agyquota/internal/client/client.go`
  - 实现：
    - `Config` 新增 `Once bool` 字段；`Client` 维护 `spawnedEphemeral bool`；
    - 在 `EnsureDaemon` 中：若指定了 `Once` 且当前无法连上 daemon，则无论是否为开发构建，均允许调用 `spawnDaemonWithIdle` 拉起临时实例，并传入短超时参数（`--idle-timeout 10s`），成功后标记 `spawnedEphemeral = true`；若已有 daemon 在运行（ping 成功），则 `spawnedEphemeral = false`（不杀已有常驻进程）；
    - 新增 `IsEphemeral() bool` 与 `CleanupIfEphemeral(ctx context.Context) error`：当 `spawnedEphemeral` 为 true 时，调用 `/v1/stop` 关停临时 daemon 并清理；
    - 未开启 `Once` 且为开发构建时，在错误建议（Suggestion）中增加 `--once` 引导提示。
  - 验证：单元/模块逻辑可编排。

- [x] Task 2: CLI 接入 --once 标志并编排执行与 defer 优雅回收 ✅ 完成
  - 文件：`go_projects/agyquota/internal/cli/root.go`、`go_projects/agyquota/internal/cli/quota.go`
  - 实现：
    - 在 `root.go` 中注册 `PersistentFlags().Bool("once", false, "单次查询模式：若未运行 daemon 则启动临时实例，查询完毕后自动退出，不留后台进程")`；
    - 在 `quota.go` 的 `quotaRun` 中读取 `--once`，传入 `client.Config{Host: host, Once: once}`；
    - 挂载 `defer` 退出钩子：在查询完成（无论成功与否）后，检查若由本次临时拉起，则以独立 context 调用 `cl.CleanupIfEphemeral`；
    - 更新命令帮助与用例说明。
  - 验证：`go vet ./...`；`go list -deps ./internal/cli` 断言不含 `internal/service`。

- [x] Task 3: 验证单次查询、生命周期回收与文档同步 ✅ 完成
  - 文件：`go_projects/agyquota/README.md`
  - 实现：
    - 同步更新 `README.md` 的命令速查表与 daemon 架构说明，记录 `--once` 参数；
    - 实测 `agyquota --zed --once`，验证：
      1. 无 daemon 时：一行命令自动拉起临时 daemon、打印配额结果、自动退出并清理地址文件；
      2. 检查系统进程：无残留 `agyquota` 进程；
      3. 有 daemon 时：先启动 `agyquota serve`，执行 `agyquota --zed --once`，验证配额正常返回且原有 daemon 未被终止。
  - 验证：手工端到端验收通过。

## 实施说明

### 执行记录（2026-10-16）

- **Task 1**：在 `internal/client/client.go` 中支持 `Once` 模式与临时 daemon 调度，设置 10s 短空闲超时保底，增加 `IsEphemeral` 与 `CleanupIfEphemeral`，未指定 `--once` 且为开发构建时错误提示引导追加 `--once` 建议；
- **Task 2**：在 `internal/cli/root.go` 与 `quota.go` 中接入 `--once` 标志，通过 `defer` 保证无论查询成功还是失败均能优雅发送 `/v1/stop` 回收临时 daemon，`go list -deps` 依赖方向断言 100% 保持；
- **Task 3**：完成代码构建与部署，并在 Windows 宿主环境下完成了真实端到端测试：
  - 场景 A（无常驻 daemon）：`agyquota --zed --once` 零感知启动临时 daemon，打印完整配额，退出后检测进程与地址文件为 0 残留；
  - 场景 B（已有常驻 daemon）：在常驻 daemon 运行时执行 `agyquota --zed --once`，成功复用取数，且原有常驻 daemon 保持正常运行。

