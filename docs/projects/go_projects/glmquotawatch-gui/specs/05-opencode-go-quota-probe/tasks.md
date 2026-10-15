# Task List: OpenCode Go 额度探测快速实现

- [ ] 1. OpenCode Go API 客户端与数据结构实现
  - Files: `go_projects/glmquotawatch-gui/internal/opencode/client.go`, `go_projects/glmquotawatch-gui/internal/opencode/client_test.go`
  - 实现细节：
    - 定义 `WindowUsage`、`Usage` 结构体。
    - 实现 `NewClient(baseURL, token string) *Client`。
    - 实现 `FetchUsage(ctx context.Context) (*Usage, error)`，请求 `https://opencode.ai/zen/go/v1/usage` 并解析响应。
    - 401 明确映射为 `ErrUnauthorized`，403 映射为 `ErrForbidden`，10s 超时控制。
    - 编写基于 `httptest.Server` 的单元测试，覆盖 200 成功解析、401 报错、403 报错与网络错误。
  - Verify: 在 `go_projects/glmquotawatch-gui` 运行 `go test -v ./internal/opencode/...` 且测试全部通过。
  - Ref: AC-2, AC-3

- [ ] 2. Store 配置持久化扩展支持 OpenCode Token
  - Files: `go_projects/glmquotawatch-gui/internal/store/store.go`, `go_projects/glmquotawatch-gui/internal/store/store_test.go`
  - 实现细节：
    - `Config` 结构体增加 `OpenCodeToken string json:"opencode_token,omitempty"` 字段。
    - 兼容现有 `config.json`，缺失时反序列化为空字符串。
    - 单元测试验证新旧配置文件的反序列化与存取往返。
  - Verify: 在 `go_projects/glmquotawatch-gui` 运行 `go test -v ./internal/store/...` 且测试全部通过。
  - Ref: AC-1

- [ ] 3. Service 层增加 OpenCode 业务用例与状态组装
  - Files: `go_projects/glmquotawatch-gui/internal/service/opencode.go`, `go_projects/glmquotawatch-gui/internal/service/opencode_test.go`
  - 实现细节：
    - 定义 `OpenCodeConfigView`、`OpenCodeWindowView`、`OpenCodeStatusView`。
    - 实现 `GetOpenCodeConfig()`、`SetOpenCodeToken(token)`（写入 store 并脱敏返回）、`RemoveOpenCodeToken()`。
    - 实现 `SampleOpenCodeOnce(ctx)`：优先取 store 的 token，为空取环境变量 `OPENCODE_API_KEY`；发起探测并组装视图（计算倒计时 `reset_in`）。
    - 编写单元测试验证 Token 设置、脱敏输出与 Mock 采样。
  - Verify: 在 `go_projects/glmquotawatch-gui` 运行 `go test -v ./internal/service/...` 且测试全部通过。
  - Ref: AC-1, AC-2, AC-3

- [ ] 4. CLI 新增 `opencode` 独立子命令组与 Schema 同步
  - Files: `go_projects/glmquotawatch-gui/internal/cli/opencode.go`, `go_projects/glmquotawatch-gui/internal/cli/root.go`, `go_projects/glmquotawatch-gui/internal/cli/schema.go`, `go_projects/glmquotawatch-gui/internal/cli/cli_test.go`
  - 实现细节：
    - 新增 `opencodeCmd()`，挂载 `token`（set/show/remove）与 `status` 命令。
    - 保持恒 JSON 信封输出（`outOK` / `outErr`），退出码规范遵循 0 成功 / 1 业务失败 / 2 参数错误。
    - 在 `schema.go` 中同步注册 `opencode` 命令树。
    - 单元测试覆盖 CLI 参数解析与输出信封。
  - Verify: 在 `go_projects/glmquotawatch-gui` 运行 `go test -v ./internal/cli/...` 且测试全部通过。
  - Ref: AC-1, AC-2, AC-3, AC-5

- [ ] 5. Wails 后端 Bindings 扩展与状态快照集成
  - Files: `go_projects/glmquotawatch-gui/internal/guiapp/bindings.go`, `go_projects/glmquotawatch-gui/internal/guiapp/runtime.go`
  - 实现细节：
    - `GUIState` 增加 `ActiveProvider`、`OpenCodeStatus`、`OpenCodeConfig` 字段。
    - `BindingsService` 增加 `SetActiveProvider(provider)`、`SampleOpenCodeNow()`、`SetOpenCodeToken(token)`、`RemoveOpenCodeToken()`。
    - `runtime.go` 支持管理 `activeProvider` 与 OpenCode 探测状态缓存。
  - Verify: 在 `go_projects/glmquotawatch-gui` 运行 `go test -v ./internal/guiapp/...` 且编译无错误。
  - Ref: AC-4

- [ ] 6. 前端 Provider 切换、OpenCode 专属仪表盘与设置页开发
  - Files: `go_projects/glmquotawatch-gui/frontend/src/api.ts`, `go_projects/glmquotawatch-gui/frontend/src/store.ts`, `go_projects/glmquotawatch-gui/frontend/src/App.vue`, `go_projects/glmquotawatch-gui/frontend/src/pages/Dashboard.vue`, `go_projects/glmquotawatch-gui/frontend/src/pages/Settings.vue`
  - 实现细节：
    - `api.ts` 导出新增的 OpenCode 类型定义。
    - `store.ts` 接入 `activeProvider` 状态管理与 `sampleOpenCodeNow()` 方法。
    - `App.vue` 顶部导航栏增加 Provider 切换选项卡 `[智谱 GLM | OpenCode Go]`。
    - `Dashboard.vue` 在 `activeProvider === 'opencode'` 时展示 3 个配额卡片（滑动窗口、周窗口、月窗口），展示当前百分比、重置倒计时与状态，支持点击「立即采样」。
    - `Settings.vue` 增加 OpenCode API 密钥维护卡片。
  - Verify: 在 `go_projects/glmquotawatch-gui/frontend` 运行 `npm run build`，产出无报错并输出 `dist/`。
  - Ref: AC-4, AC-5

- [ ] 7. 端到端构建与双入口联调验证
  - Files: `go_projects/glmquotawatch-gui` 整体工程
  - 实现细节：
    - 运行 `uv run scripts/build-dev.py` 构建开发版 exe。
    - 使用测试 Key 执行 `.\bin\glmquotawatch-gui-dev.exe opencode token set <key>`。
    - 执行 `.\bin\glmquotawatch-gui-dev.exe opencode status` 验证真实 API 探测输出。
    - 验证既有 GLM CLI `.\bin\glmquotawatch-gui-dev.exe status` 行为未退化。
  - Verify: 终端执行 `.\bin\glmquotawatch-gui-dev.exe opencode status` 返回 `{"ok":true,"data":...}` 且退出码为 0。
  - Ref: AC-1, AC-2, AC-3, AC-4, AC-5
