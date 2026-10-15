# Requirements Document: OpenCode Go 额度探测快速实现

## Summary

`glmquotawatch-gui` 当前专注于智谱 GLM（bigmodel）编码套餐用量监控。随着多 AI 编程平台的日常高频使用，用户需要在一个统一的轻量级工具中快速查看 OpenCode Go 套餐的额度情况。

第一步实施目标为**快速实现核心探测与即时查看**：完成 OpenCode Go 官方用量 API 适配，提供本地 Token 安全存储，在 CLI 增加独立的 `opencode` 命令组，并在 GUI 顶部提供 Provider 切换（GLM / OpenCode Go）及 OpenCode Go 专属仪表盘（展示滑动窗口、周窗口、月窗口的当前百分比、重置时间和健康状态），并支持一键「立即采样」。后台持续轮询告警与历史曲线归并至后续迭代。

## Functional Requirements

- **FR-1 OpenCode Go 探测客户端**：
  - 调用官方端点 `GET https://opencode.ai/zen/go/v1/usage`，携带请求头 `Authorization: Bearer <API_KEY>`。
  - 解析上游响应的 `usage` 字段，提取 `rolling`（滑动窗口）、`weekly`（周窗口）、`monthly`（月窗口）的 `status`（"ok" 或 "rate-limited"）、`percent`（整数/浮点百分比）以及 `resetsAt`（ISO 8601 重置时间戳）。
  - 支持通过环境变量 `OPENCODE_GO_API_BASE` 覆盖基地址（用于单元测试与本地 Mock）。
- **FR-2 本地凭证持久化（Token 管理）**：
  - `store.Config` 扩展支持 `opencode_token` 字段，持久化于现有 `%APPDATA%\language_projects\glmquotawatch-gui\<dev|prod>\config.json` 中。
  - 保持配置双向兼容：旧配置文件无此字段时解析为空，不影响既有 GLM 配置。
  - 所有展示出口（CLI JSON、GUI 绑定、日志）恒脱敏（`前4…后4`），禁止暴露明文。
  - 支持通过环境变量 `OPENCODE_API_KEY` 作为临时回退源（当本地配置为空时）。
- **FR-3 独立 CLI 命令命名空间（`opencode`）**：
  - 新增顶级子命令 `opencode`，与现有 GLM 命令完全解耦、互不影响。
  - `opencode token set <key>`：设置并保存 OpenCode API Key。
  - `opencode token show`：查看脱敏后的 Key 及配置状态。
  - `opencode token remove`：清除本地保存的 OpenCode Key（幂等）。
  - `opencode status`：立即触发一次探测，stdout 恒输出统一 JSON 信封（包含 3 个窗口的详细用量）。
  - `schema` 导出同步包含 `opencode` 完整子命令契约（无网络 I/O）。
- **FR-4 GUI 导航与 Provider 切换**：
  - 主窗口顶部或侧边增加 Provider 切换组件（GLM / OpenCode Go）。
  - 切换至 OpenCode Go 时，呈现专属卡片式仪表盘（滑动、周、月 3 个额度卡片）。
  - 每个卡片清晰展示用量环/进度条、百分比、下次重置倒计时（例如 "3小时25分后"）以及状态指示灯。
  - 仪表盘配备「立即采样」按钮，点击立即发起探测并刷新视图，附带上次采样时间戳。
  - 若未配置 Token，展示内凹引导卡片，一键跳转到设置页。
- **FR-5 GUI 设置页支持 OpenCode Key 维护**：
  - 设置页面增加 OpenCode Go 配置卡片，支持查看脱敏 Token、输入新 Token 保存、清除 Token。

## Non-Functional Requirements

- **NFR-1 隔离性与零破坏**：GLM 的既有 CLI 命令、GUI 仪表盘、采样 daemon、历史存储和 Windows Toast 告警逻辑不受任何破坏。
- **NFR-2 零冗余依赖**：Go 后端完全复用标准库 `net/http` 与 `encoding/json`，不引入任何第三方网络或辅助依赖。
- **NFR-3 严格超时与错误分类**：探测请求强制 10 秒超时；清晰识别并映射网络超时、HTTP 401（密钥失效/未授权）、HTTP 403（未订阅 Go 套餐）及上游 5xx 故障。
- **NFR-4 数据目录强约束**：严格遵循父仓统一规范，所有配置只落盘在 `%APPDATA%\language_projects\glmquotawatch-gui\<dev|prod>\`，严禁在外部目录散落临时文件。

## Acceptance Criteria

### AC-1
WHEN 用户在终端执行 `glmquotawatch-gui.exe opencode token set oc_sk_...` 时，THEN 写入 `config.json` 的 `opencode_token`，且执行 `glmquotawatch-gui.exe opencode token show` 返回 JSON 信封中的 token 为 `前4…后4` 脱敏格式。

### AC-2
WHEN 用户在终端执行 `glmquotawatch-gui.exe opencode status` 且已配置有效 Token，THEN stdout 输出 `{"ok":true,"data":{...}}`，包含 `rolling`、`weekly`、`monthly` 三个窗口各自的 `status`、`percent` 和 `resets_at`。

### AC-3
WHEN 传入无效的 API Key 执行 `opencode status`，THEN 返回 `{"ok":false,"error":{"code":"auth_error","message":"..."}}`，进程退出码为 1。

### AC-4
WHEN 用户在 GUI 界面顶部点击切换到 OpenCode Go，THEN 主界面切换为 OpenCode Go 仪表盘；点击「立即采样」后，各卡片百分比与重置倒计时立即更新为最新探测值。

### AC-5
WHEN 整个功能上线后，THEN 既有 GLM 的 `status`、`token`、Toast 告警和主界面仪表盘保持完全一致，无任何行为回归。

## Out of Scope

- OpenCode Go 的后台常驻定时轮询采样与 Windows Toast 阈值告警（第一步快速交付只聚焦即时探测，告警放后续迭代）。
- OpenCode Go 采样历史（`samples-*.jsonl`）与 24h/7d 趋势折线图（放后续迭代）。
- 演示模式（Demo mode）下的 OpenCode Go 虚拟回放（仅针对真实网络探测）。
