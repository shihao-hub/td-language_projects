# Requirements Document

## Summary

glmquotawatch-gui 当前只有一条通知出口：GUI 进程内注入的 Windows Toast（`service.Notifier` 的唯一实现 `toastNotifier`，见 `internal/guiapp/runtime.go`）。当用户不在电脑前（或关掉托盘通知）时，超阈值告警会丢失——今天的实例就是 5h 窗口被吃到 100%，而告警只在本地闪了一下。

本次要做的是一次**通知出口的通用化改造**：把"通知"从"GUI 里的一个 Toast 调用"变成"一组可绑定、可插拔、可独立记账的渠道"，让同一套告警能同时投递到 QQ 邮箱、飞书机器人、微信/QQ 机器人、短信网关等任意端点，且**新增渠道不需要改核心代码**。

## Functional Requirements

- **FR-1 多渠道配置**：`config.json` 支持 0..N 个通知渠道；无配置时行为与现状完全一致（仅 Toast），旧格式配置文件可直接读取。
- **FR-2 三种内置渠道类型**：`toast`（本地通知，默认启用）、`smtp`（邮件）、`http`（通用 HTTP/Webhook 模板）。所有"平台机器人"都归到 `http` 类型，不为每个平台写代码。
- **FR-3 预设（preset）**：为常见端点提供预设，用户只填密钥/地址，不手写请求模板。首批预设：飞书自定义机器人（含签名 secret）、企业微信群机器人、Server酱/PushPlus（微信推送）、Bark、ntfy、OneBot（QQ 机器人 HTTP API）、通用短信网关、自定义空白模板。
- **FR-4 渠道可绑定 QQ 邮箱**：`smtp` 类型支持 QQ 邮箱（`smtp.qq.com`，465 隐式 TLS / 587 STARTTLS，授权码鉴权）、多收件人、发件人显示名。
- **FR-5 独立记账**：每个渠道独立记录"已通知的窗口-档位"。某渠道失败只在该渠道重试，不阻塞、不影响已成功的渠道；全部渠道都失败时保持现有的"待发送"语义（不吞告警）。
- **FR-6 投递可观测**：每个渠道的最近一次投递结果（成功/失败、错误摘要、时间）落盘并在 GUI 展示；CLI 可查询。
- **FR-7 测试发送**：CLI 与 GUI 都能对单个渠道发送测试消息，且**不参与告警记账**（不污染已通知档位）。
- **FR-8 脱敏**：任何出口（CLI JSON、GUI 展示、日志、错误信息）都不得回显密码/授权码/webhook token/签名密钥，统一脱敏为 `前4…后4` 形态。
- **FR-9 渠道级静音**：全局 `silent` 保留；单个渠道可覆盖（仅对支持静音的 `toast` 生效，其余渠道忽略该字段）。
- **FR-10 CLI 契约同步**：新增 `notify` 命令组（list/add/update/remove/enable/disable/test），恒 JSON 信封，并同步更新 `schema` 导出的命令契约（遵循《CLI 工具开发标准》的 `--json` + `schema` 基线与"Service 核心 + 多壳"分层）。
- **FR-11 免费额度说明**：文档必须写清各渠道的真实成本边界——飞书/企业微信机器人、Bark、ntfy 免费；Server酱/PushPlus 有免费额度但限频；**短信不存在长期免费**，只有云厂商（阿里云/腾讯云等）新用户赠送的少量条数，且需实名 + 模板报备。

## Non-Functional Requirements

- **NFR-1 不阻塞采样**：投递不得拖慢采样循环；渠道并发发送，单渠道超时 10s，整批预算 20s，超时按失败处理（下轮重试）。
- **NFR-2 不新增第三方依赖**：仅用标准库（`net/smtp`、`crypto/tls`、`net/http`、`encoding/json`）。项目当前依赖只有 cobra + Wails，不为通知引入任何新模块。
- **NFR-3 可测**：渠道实现可脱离 GUI 与网络单测（HTTP 用 `httptest`，SMTP 用假连接或注入 dialer）；分发器的并发、超时、部分失败必须有测试覆盖。
- **NFR-4 兼容与迁移**：旧 `state.json`（只有 `notified` 字段）可无损读取，语义等价于"这些档位已由默认渠道通知过"，不得因迁移导致重复告警。

## Acceptance Criteria

### AC-1
WHEN `config.json` 中配置了 `smtp` 渠道（QQ 邮箱，授权码正确）且窗口用量跨过 50% 档，THEN 该邮箱在 30s 内收到一封告警邮件，且 `state.json` 中该渠道的已通知档位包含 50。

### AC-2
WHEN 配置了飞书自定义机器人 preset（仅填 webhook token，可选 secret），THEN `notify test <name>` 能收到一条测试消息；若 URL 里带 secret 签名，则请求携带正确的 `timestamp` + `sign`，服务端返回 2xx。

### AC-3
WHEN 某渠道发送失败（如 SMTP 认证失败、webhook 5xx），THEN 其他渠道仍正常投递、其记账正常推进；失败渠道在下一采样周期重试，且 GUI/CLI 能看到该渠道的最近错误摘要。

### AC-4
WHEN 未配置任何 `notify` 项（或旧版本配置文件），THEN 行为与现状逐条一致：只在 GUI 进程内发 Toast，`state.json` 结构可被旧逻辑读取。

### AC-5
WHEN 执行 `notify list`，THEN stdout 为合法 JSON 信封，其中 `password`/`token`/`secret`/`key` 类字段全部为脱敏形态，不出现明文；执行 `schema` 时新命令出现在契约里且不触发任何网络 I/O。

### AC-6
WHEN 渠道投递失败一次后用户修正配置，THEN 不需要重启 GUI 进程，下一个采样周期即按新配置投递（配置热加载）。

## Out of Scope

- 个人微信/QQ 的**协议级**机器人（hook 客户端、灰色自动化）：不实现、不推荐，仅文档提示风险。
- 短信厂商的原生 SDK/签名算法适配（阿里云 ACS3、腾讯云 TC3）：v1 只提供通用 HTTP 模板与自建网关 preset；原生适配器留待 v2，若要做需单独开 spec。
- 渠道级独立阈值、渠道级重试次数/退避策略、聚合去抖（同一告警合并投递）：v1 沿用"每窗口每档位一次"。
- MCP 入口：沿用项目既有决策（GUI 面向人 + CLI 恒 JSON 已覆盖机器消费），本次不新增。
- 通知历史的独立存储与检索（只保留各渠道最近一次结果，不建投递历史库）。
