# Design Document

## Overview

把"通知"从 GUI 内的单个 Toast 调用，重构为**渠道（Channel）插件化 + 分发器（Dispatcher）并发投递 + 逐渠道独立记账**的三层结构。新增渠道 = 往 `internal/notify` 加一个实现或加一条 preset 表项，**daemon、service、CLI、GUI 均无需改动**。

核心改动点：新增 `internal/notify` 包（纯标准库，不依赖 Wails）；`store.Config` 增加 `notify` 渠道列表；`store.State` 增加逐渠道记账；daemon 由"调一次 Notifier"改为"分发 + 按渠道结果记账"；CLI 增加 `notify` 命令组并同步 `schema` 契约；GUI 偏好配置页增加渠道管理区。

## Context

现状（读码确认）：

- `service.Notifier` 只有一个方法 `Notify(title, msg string, silent bool) error`（`internal/service/service.go:36`），实现只有 `toastNotifier`（`internal/guiapp/runtime.go:48-56`），在 `runtime.go:240` 注入 daemon。
- daemon 的告警语义是"**发送成功后才记账**"：`RunDaemon`（`internal/service/daemon.go`）维护 `pending` 映射，`n.Notify(...)` 返回 nil 才把 `newly` 档位 merge 进 `state.Notified` 并落盘；失败则保留 pending 下轮重试。
- 记账键是窗口稳定键，实测形态 `TOKENS_LIMIT:3:5`（`%APPDATA%\language_projects\glmquotawatch-gui\prod\state.json`）。
- 配置只有 5 个扁平字段（token/interval/thresholds/hysteresis/silent），`store.Config` 由 `SaveConfig` 原子写。
- 仓库根 `AGENTS.md` 强制《CLI 工具开发标准》：Service 层是唯一业务真相源，壳层只做解析与渲染；`--json` + `schema` 必须同步；**严禁在壳层写业务逻辑**。本次改造必须落在 Service 层，CLI/GUI 只做投影。

本次改造后，通知能力从"1 个出口"变为"1 个可扩展的出口集合"。

```mermaid
flowchart LR
  T[采样 tick] --> Q[quota 阈值评估]
  Q --> P[pending 聚合]
  P --> D[notify.Dispatcher.Notify]
  D --> C1[toast]
  D --> C2[smtp]
  D --> C3[http / preset]
  C1 --> R[[]Delivery]
  C2 --> R
  C3 --> R
  R --> A[成功渠道 merge Notified]
  A --> S[store.SaveState]
  R --> G[GUI 展示最近投递状态]
```

## Goals and Non-Goals

- Goals：渠道可插拔、可绑定 QQ 邮箱 / 飞书机器人 / 微信（企业微信 + 推送类）/ QQ（OneBot）/ 短信网关；逐渠道独立记账与重试；配置与结果可观测；脱敏；不新增依赖；旧配置与旧状态无损兼容。
- Non-Goals：不做个人微信/QQ 协议级机器人；不做短信厂商原生签名适配（v1 只做通用 HTTP preset）；不做渠道级阈值、退避策略、告警聚合；不新增 MCP 入口。

## Detailed Design

### 1. `internal/notify`（CREATED 包）

- `CREATED internal/notify/message.go`
    - **Purpose**：渠道与分发器共用的纯数据类型。
    - **Changes**：
      ```go
      type Alert struct {
          WindowKey  string // 窗口稳定键，如 TOKENS_LIMIT:3:5
          Label      string // 人读标签，如 "5h 窗口"
          Percentage int64  // 触发时的百分比
          Newly      []int  // 本次新跨过的档位
          Text       string // 单行文案（daemon 侧由 quota 产出，渠道不重排）
      }
      type Message struct {
          Title  string    // 恒定 quota.AlertTitle
          Alerts []Alert
          Silent bool
          At     time.Time
      }
      func (m Message) PlainBody() string // Title 之外的多行正文：每条 Alert.Text 一行
      ```
    - **Complexity**：Low
- `CREATED internal/notify/channel.go`
    - **Purpose**：渠道契约与分发。
    - **Changes**：
      ```go
      type Channel interface {
          Name() string                 // 渠道唯一名（配置里的 name）
          Kind() string                 // toast | smtp | http
          Send(ctx context.Context, m Message) error
      }
      type Delivery struct { Channel string; Err error }
      type Dispatcher struct { channels []Channel; perTimeout, budget time.Duration }
      func NewDispatcher(chs []Channel, opts ...Option) *Dispatcher
      func (d *Dispatcher) Notify(ctx context.Context, m Message) []Delivery // 顺序与 channels 一致
      ```
      并发模型：每个渠道一个 goroutine（`sync.WaitGroup`），各自 `context.WithTimeout(perTimeout=10s)`；`budget=20s` 到点后未完成者按超时失败返回（结果切片按配置顺序写入，避免竞态）。Dispatcher 实现 `service.Notifier`（结构化子集），不感知 store。
    - **Complexity**：Medium
- `CREATED internal/notify/toast.go`：`func NewToast(name string, send func(title, body string, silent bool) error) Channel`。gui 侧把 `r.ns.SendNotification` 包成该回调；CLI/服务化场景可传 stub 或直接不注册 toast。
- `CREATED internal/notify/smtp.go`
    - **Purpose**：SMTP 邮件渠道（QQ 邮箱为首要目标）。
    - **Changes**：参数 `host/port/security(username,password)/from/from_name/to(逗号分隔)/subject_prefix`。`security=ssl` 走 `tls.Dial` + `smtp.NewClient`（**标准库 `net/smtp` 不支持隐式 TLS，必须自建 TLS 连接**）；`security=starttls` 走 `smtp.Dial` + `StartTLS`。主题 `{subject_prefix}{title}`，正文纯文本 `PlainBody()`。错误分类：认证失败（`notify_auth_failed`）、连接/超时（`notify_unreachable`）、收件人拒绝（`notify_rejected`）。
    - **Complexity**：Medium
- `CREATED internal/notify/http.go`
    - **Purpose**：一个渠道覆盖所有 webhook/机器人/短信网关。
    - **Changes**：参数 `url/method/content_type/body/query/headers.<HeaderName>/expect_status`。渲染器用 `strings.NewReplacer` 替换 `{{title}} {{body}} {{time}} {{windows}}`（`{{windows}}` = 各 Alert.Text 用 `\n` 连接）；未识别的占位符保留原文不报错。成功判定：状态码在 `expect_status`（默认 `2xx`）。参数 `headers.*` 的值禁止含 CR/LF（头注入防护）。
    - **Complexity**：Medium
- `CREATED internal/notify/presets.go`
    - **Purpose**：预设表 —— 新增平台只加一条表项。
    - **Changes**：
      ```go
      type Preset struct {
          ID, Title, Kind string
          Defaults  map[string]string // method/content_type/body/...
          Required  []string          // 必填参数键
          SecretKeys []string         // 需脱敏的键
      }
      func Presets() []Preset
      func LookupPreset(id string) (Preset, bool)
      ```
      首批：`feishu`（自定义机器人，body `{"msg_type":"text","content":{"text":"{{title}}\n{{body}}"}}`，可选 `secret` → 追加 `timestamp` + `sign`，算法 `base64(HMAC-SHA256(key=timestamp, data=timestamp+"\n"+secret))`）、`wecom`（企业微信群机器人）、`serverchan`、`pushplus`、`bark`、`ntfy`、`onebot`（`POST {api_url}/send_private_msg`，body `{"user_id":…,"message":…}`）、`sms-generic`（自建/聚合短信网关，body `{"phone":…,"content":…}`）、`custom`（全空手填）。
    - **Complexity**：Low
- `CREATED internal/notify/factory.go`
    - **Purpose**：由配置构造渠道实例 + 校验。
    - **Changes**：`func Build(cfg store.ChannelConfig, toastFn ToastFunc) (Channel, error)`；校验规则集中在 `Validate(cfg)`：`name` 非空 ≤32 且 `^[A-Za-z0-9_-]+$`、`kind` 白名单、`smtp` 端口 1..65535、`security` 枚举、`from/to` 含 `@`、`http` 的 url 必须 http/https、参数键必须在该 kind/preset 允许集合内（未知键 → `bad_value`）。
    - **Complexity**：Low

### 2. `internal/service`（UPDATED）

- `UPDATED internal/service/service.go`
    - **Purpose**：Notifier 契约升级 + 渠道用例 + 脱敏视图。
    - **Changes**：
      - `type Notifier interface { Notify(ctx context.Context, m notify.Message) []notify.Delivery }`（替换旧三参方法）。
      - `ConfigView` 增加 `Notify []ChannelView`；`ChannelView{ Name, Kind, Preset, Enabled, Silent *bool, Params map[string]string }`，其中 `Params` 的值对 `SecretKeys` 命中的键统一脱敏为 `前4…后4`（长度 ≤8 时全掩）。
      - 新用例：`ListChannels() ([]ChannelView, error)`、`AddChannel(ChannelInput) (ChannelView, error)`、`UpdateChannel(ChannelInput)`、`RemoveChannel(name)`、`SetChannelEnabled(name, bool)`、`TestChannel(ctx, name, text string) error`（构造单渠道直接 `Send`，**不触碰 state**）。
      - 校验失败返回既有 `*Error{Code:"bad_value"}`；重名返回 `conflict`；不存在返回 `not_found`。
    - **Complexity**：Medium
- `UPDATED internal/service/daemon.go`
    - **Purpose**：分发 + 逐渠道独立记账。
    - **Changes**：
      - 发送段改为：构造 `notify.Message`（Alerts 来自 pending，Newly 原样带上）→ `n.Notify(ctx, msg)`。
      - 记账改为：**仅对 `Delivery.Err == nil` 的渠道** merge `alert.Newly` 到 `state.Channels[渠道名].Notified[windowKey]`；失败渠道写入 `LastErr/LastAt/LastOK=false` 并保留 pending（下轮重试）；全部失败时不 merge 任何档位（保持"不吞告警"语义）。
      - 窗口 `Cleared` 时：从**所有渠道**的 Notified 中删除该 key。
      - `DaemonHooks.OnNotifyError` 逐渠道上报（保持现有回调，故障可见性不降级）。
    - **Complexity**：Medium
- `UPDATED internal/service/service.go`（配置热加载）：daemon 每轮 tick 现有 `LoadConfig()` 读取 `interval/silent`，追加读取 `notify` 并对比指纹（渠道名+kind+preset+params 的哈希）；指纹变化即重建 Dispatcher（满足 AC-6，无需重启）。

### 3. `internal/store`（UPDATED）

- `UPDATED internal/store/store.go`
    - **Changes**：
      ```go
      type ChannelConfig struct {
          Name    string            `json:"name"`
          Kind    string            `json:"kind"`             // toast | smtp | http
          Preset  string            `json:"preset,omitempty"` // kind=http 时的预设 id
          Enabled bool              `json:"enabled"`
          Silent  *bool             `json:"silent,omitempty"` // nil 继承全局
          Params  map[string]string `json:"params,omitempty"`
      }
      type Config struct { /* 既有 5 字段 */ ; Notify []ChannelConfig `json:"notify,omitempty"` }

      type ChannelState struct {
          Notified map[string][]int `json:"notified,omitempty"`
          LastAt   time.Time        `json:"last_at,omitempty"`
          LastOK   bool             `json:"last_ok"`
          LastErr  string           `json:"last_err,omitempty"`
      }
      type State struct { /* 既有字段 */ ; Channels map[string]ChannelState `json:"channels,omitempty"` }
      ```
      **迁移不变量**：`LoadState` 时若 `Channels == nil && len(Notified) > 0`，则 `Channels = {"toast": {Notified: 旧 Notified}}`（旧记录视为默认 toast 渠道，保证 AC-4 不重复告警）。`LoadConfig` 缺 `notify` 字段 → 空切片，语义 = 只要 toast。
    - **Complexity**：Low

### 4. `internal/cli`（UPDATED）

- `UPDATED internal/cli/root.go`：新增 `notify` 命令组
    - `notify list`、`notify add --name --kind [--preset] [--set k=v]... [--params -]`、`notify update --name [--set k=v]...`、`notify remove --name`、`notify enable|disable --name`、`notify test --name [--text "..."]`。
    - 参数合并规则：`--params -` 从 stdin 读 JSON 对象作为基底，`--set k=v` 逐项覆盖；两者都缺时按 preset 默认值 + 必填字段报 `bad_value`。
    - 全部命令恒 JSON 信封（复用 `outOK/outErr`），退出码沿用 0/1/2。
- `UPDATED internal/cli/schema.go`：契约目录追加 `notify` 命令与 `NotifyChannelView` 输出视图描述；`schema` 分支保持零 I/O（不得实例化渠道、不得读配置外的文件）。

### 5. `internal/guiapp`（UPDATED）

- `UPDATED internal/guiapp/runtime.go`：`toastNotifier` 降级为 `notify.NewToast("toast", 回调)` 的构造参数；组装逻辑改为 `Dispatcher`。
- `UPDATED internal/guiapp/bindings.go`：新增前端绑定 `ListNotifyChannels/AddNotifyChannel/UpdateNotifyChannel/RemoveNotifyChannel/SetNotifyChannelEnabled/TestNotifyChannel`，返回脱敏视图与业务错误码。
- `UPDATED frontend/src/**`：偏好配置页新增"通知渠道"区（列表 + 启用开关 + 测试按钮 + 新增/编辑对话框，字段随 kind/preset 动态渲染；密钥字段用 password 输入 + 显示脱敏占位）。实现时按该页现有组件风格落地，不引入新 UI 依赖。

### Module Collaboration and Data Flow

依赖方向（单向，无环）：

```
cli ─┐
     ├─→ service ─→ store / api / quota / notify(类型与接口)
gui ─┘        └─→ notify(构造 Dispatcher，注入 toast 回调)
notify ─→ 标准库（net/smtp、crypto/tls、net/http、encoding/json）
```

关键不变量：

1. **state 只能由 daemon 串行写**：渠道实现禁止读写 store（渠道只接收 Message、返回 error）。
2. **记账后置于投递成功**：任一档位只有在其渠道 `Send` 返回 nil 后才写入该渠道的 `Notified`。
3. **脱敏在出口层完成**：`ChannelView` 是唯一的读出口，任何 CLI/GUI 输出都必须经它。
4. **无配置即现状**：`notify` 为空时 Dispatcher 只含 `toast` 渠道，行为与当前版本逐条一致。

### Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | `notify/smtp.go` + `service.AddChannel` + `daemon` 逐渠道记账 |
| AC-2 | `notify/presets.go`（`feishu` 签名）+ `service.TestChannel` + `cli notify test` |
| AC-3 | `notify/channel.go`（Dispatcher 汇总结果）+ `store.ChannelState.LastErr` + `daemon` 部分失败记账 |
| AC-4 | `store.LoadState` 迁移不变量 + `notify/factory.go` 空配置分支 |
| AC-5 | `service.ChannelView` 脱敏 + `cli/schema.go` 契约更新 |
| AC-6 | `daemon` 渠道指纹热加载 |

## Design Review Notes

自审（零上下文视角）发现与处置：

- **HIGH｜依赖方向错误（已修复）**：初稿把 `Notifier` 定义在 service 包、由 notify 包实现，会造成 `service → notify → service` 环。现改为 notify 包只定义纯数据类型与 `Channel/Dispatcher`，service 依赖 notify，gui 负责组装。
- **MEDIUM｜`net/smtp` 不支持 465（已修复）**：不能只写"支持 SSL"，必须显式 `tls.Dial` 后 `smtp.NewClient`；已在 smtp.go 卡片里写明，并要求 587/465 两条路径都走同一 `Channel` 实现。
- **MEDIUM｜并发投递与状态写入竞态（已修复）**：初稿未限定 state 的写者。现固化不变量 1/2：渠道不触碰 store，结果回传 daemon 后串行落盘。
- **MEDIUM｜旧 state 迁移可能重复告警（已修复）**：若不迁移 `Notified`，升级后会把当前窗口已通知的档位再发一轮。现规定旧记录映射到 `toast` 渠道。
- **MEDIUM｜模板注入面（已修复）**：`http` 渠道的 `headers.*` 值若含 CR/LF 可注入请求头，已加入校验并在设计里显式禁止。
- **NIT｜`Params map[string]string` 牺牲类型安全**：换取零 schema 迁移与"新渠道不改代码"。补偿手段是 kind/preset 级白名单校验；风险可接受。
- **已验证假设**：`service.Notifier` 仅有 `toastNotifier` 一个实现（全仓 grep 确认）；窗口键形态 `TOKENS_LIMIT:3:5`（prod `state.json` 实测）；项目直接依赖只有 `cobra` + `wails/v3`（`go.mod` 实测）；CLI 壳层已有 `outOK/outErr` 信封工具与 `schema` 导出分支（`internal/cli/output.go`、`schema.go`）。
- **未验证假设**：① 飞书自定义机器人签名算法按官方文档描述实现，落地时需真机发一次验证；② QQ 侧 `onebot` preset 的字段名（`send_private_msg`/`user_id`/`message`）依赖用户实际部署的 OneBot 实现，需按其文档核对；③ 企业微信/Server酱/PushPlus/Bark/ntfy 的端点与参数以各自官方文档为准，preset 表落地时逐条核对并写进 README。
