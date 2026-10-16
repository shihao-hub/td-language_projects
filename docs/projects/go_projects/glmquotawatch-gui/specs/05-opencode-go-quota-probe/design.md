# Design Document: OpenCode Go 额度探测快速实现

## Overview

在 `glmquotawatch-gui` 中快速引入 OpenCode Go 额度探测能力，提供端到端的 API 探测、配置持久化、CLI 独立子命令和 GUI 专属仪表盘。通过 Provider 隔离设计，保持原有 GLM 监控链路 100% 独立稳定，以最轻量优雅的方式支持用户即时查看 OpenCode Go 的三大配额窗口（滑动窗口、周窗口、月窗口）。

## Context

OpenCode Go 官方用量接口规范已实测探明：
- **端点**：`GET https://opencode.ai/zen/go/v1/usage`
- **鉴权**：`Authorization: Bearer <API_KEY>`（格式形如 `oc_sk_...`）
- **响应体**：
  ```json
  {
    "usage": {
      "rolling": {
        "status": "ok",
        "percent": 0,
        "resetsAt": "2026-10-14T05:21:41.000Z"
      },
      "weekly": {
        "status": "ok",
        "percent": 3,
        "resetsAt": "2026-10-19T00:00:00.000Z"
      },
      "monthly": {
        "status": "ok",
        "percent": 83,
        "resetsAt": "2026-10-20T17:59:00.000Z"
      }
    }
  }
  ```
- **错误形式**：HTTP 401（未授权/Key 无效）、HTTP 403（未订阅 Go 套餐），返回 `{"type":"error","error":{"type":"AuthError"|"EntitlementError","message":"..."}}`。

当前 `glmquotawatch-gui` 架构为：
- Go 后端（Cobra CLI + Wails v3 Service 核心 + Store 本地存储）
- 前端（Vue 3 + Tailwind CSS）

## Goals and Non-Goals

- **Goals**:
  1. 新建 `internal/opencode` 客户端模块，封装 HTTP 探测与错误处理。
  2. 扩展 `internal/store`，支持 `opencode_token` 持久化与脱敏。
  3. 在 `internal/service` 编排 OpenCode 探测与配置业务逻辑。
  4. 扩展 `internal/cli`，增加 `opencode` 独立子命令（`status`、`token`）。
  5. 扩展 `internal/guiapp`，暴露 Wails Bindings 并维护前端全局快照中的 Provider 状态。
  6. 前端实现 Provider 切换、OpenCode 专属卡片式仪表盘与设置页 Key 维护。
- **Non-Goals**:
  1. 第一步不实现 OpenCode Go 的后台常驻定时轮询与 Windows Toast 阈值告警。
  2. 第一步不记录 OpenCode Go 的历史用量到 `samples-*.jsonl`，亦不绘制历史曲线。
  3. 不引入第三方网络库或图表组件，保持零新增依赖。

## Detailed Design

### 模块详细划分

#### 1. `CREATED` `internal/opencode/client.go` & `client_test.go`
- **Purpose**: OpenCode Go 官方 API 客户端与数据模型定义。
- **Complexity**: Low
- **Design Details**:
  ```go
  package opencode

  const (
      DefaultBaseURL = "https://opencode.ai/zen/go/v1"
      EnvBaseURL     = "OPENCODE_GO_API_BASE"
  )

  type WindowUsage struct {
      Status   string `json:"status"`   // "ok" | "rate-limited"
      Percent  int    `json:"percent"`  // 0..100
      ResetsAt string `json:"resetsAt"` // ISO 8601
  }

  type Usage struct {
      Rolling WindowUsage `json:"rolling"`
      Weekly  WindowUsage `json:"weekly"`
      Monthly WindowUsage `json:"monthly"`
  }

  type Client struct {
      BaseURL string
      Token   string
      HTTP    *http.Client
  }

  func NewClient(baseURL, token string) *Client
  func (c *Client) FetchUsage(ctx context.Context) (*Usage, error)
  ```
- **错误分类**：
  - 401: `ErrUnauthorized` ("auth_error: API key 无效或未授权")
  - 403: `ErrForbidden` ("entitlement_error: 需要 OpenCode Go 订阅")
  - 其他 HTTP 错误或网络超时封装为清晰的 `*Error`。

#### 2. `UPDATED` `internal/store/store.go`
- **Purpose**: 配置结构支持 OpenCode API Token。
- **Complexity**: Low
- **Changes**:
  - `Config` 结构体追加字段：
    ```go
    type Config struct {
        Token         string `json:"token"`
        OpenCodeToken string `json:"opencode_token,omitempty"`
        Interval      string `json:"interval"`
        Thresholds    []int  `json:"thresholds"`
        Hysteresis    int    `json:"hysteresis"`
        Silent        bool   `json:"silent"`
    }
    ```
  - `LoadConfig()` 与 `SaveConfig()` 原生支持，旧版文件解析时 `OpenCodeToken` 自动为空，双向兼容。

#### 3. `CREATED` `internal/service/opencode.go`
- **Purpose**: OpenCode 业务用例编排与视图模型组装。
- **Complexity**: Low
- **Design Details**:
  ```go
  type OpenCodeConfigView struct {
      Token    string `json:"token"`
      HasToken bool   `json:"has_token"`
      Dir      string `json:"dir"`
  }

  type OpenCodeWindowView struct {
      Name          string `json:"name"`            // "rolling" | "weekly" | "monthly"
      Label         string `json:"label"`           // "滑动短期窗口" | "本周窗口" | "本月窗口"
      Status        string `json:"status"`          // "ok" | "rate-limited"
      Percent       int    `json:"percent"`         // 0..100
      ResetsAt      string `json:"resets_at"`       // ISO 8601
      ResetIn       string `json:"reset_in"`        // 人读倒计时，如 "3h25m"
  }

  type OpenCodeStatusView struct {
      SampledAt string               `json:"sampled_at"`
      Windows   []OpenCodeWindowView `json:"windows"`
  }

  func (s *Service) GetOpenCodeConfig() OpenCodeConfigView
  func (s *Service) SetOpenCodeToken(token string) (OpenCodeConfigView, error)
  func (s *Service) RemoveOpenCodeToken() (OpenCodeConfigView, error)
  func (s *Service) SampleOpenCodeOnce(ctx context.Context) (OpenCodeStatusView, error)
  ```
- **Token 解析策略**：优先取 `store.Config.OpenCodeToken`，为空时回退读取环境变量 `OPENCODE_API_KEY`。

#### 4. `CREATED` `internal/cli/opencode.go` & `UPDATED` `internal/cli/root.go`
- **Purpose**: 增加 `opencode` 顶级子命令组，保持恒 JSON 信封输出。
- **Complexity**: Low
- **Commands**:
  - `opencode token set <key>`
  - `opencode token show`
  - `opencode token remove`
  - `opencode status`
- **Schema 导出**：在 `internal/cli/schema.go` 中注册 `opencode` 命令树，`glmquotawatch-gui schema` 零 I/O 导出完整契约。

#### 5. `UPDATED` `internal/guiapp/bindings.go` & `runtime.go`
- **Purpose**: 扩展 Wails 前端状态与绑定服务。
- **Complexity**: Medium
- **Changes**:
  - `GUIState` 新增字段：
    ```go
    ActiveProvider string                     `json:"active_provider"` // "glm" | "opencode"
    OpenCodeStatus *service.OpenCodeStatusView `json:"opencode_status"`
    OpenCodeConfig *service.OpenCodeConfigView `json:"opencode_config"`
    ```
  - `BindingsService` 暴露方法：
    ```go
    func (b *BindingsService) SetActiveProvider(provider string) error
    func (b *BindingsService) SampleOpenCodeNow() (service.OpenCodeStatusView, error)
    func (b *BindingsService) SetOpenCodeToken(token string) (service.OpenCodeConfigView, error)
    func (b *BindingsService) RemoveOpenCodeToken() (service.OpenCodeConfigView, error)
    ```

#### 6. `UPDATED` 前端组件与页面（Vue 3）
- **Purpose**: 前端支持 Provider 切换、OpenCode 专属仪表盘与设置页配置。
- **Complexity**: Medium
- **Changes**:
  - `frontend/src/api.ts`：导出新增的 OpenCode 相关类型。
  - `frontend/src/store.ts`：维护 `activeProvider` 与 `openCodeStatus`，提供 `sampleOpenCodeNow()` 动作。
  - `frontend/src/App.vue`：顶栏常驻 Provider 切换胶囊按钮 `[智谱 GLM | OpenCode Go]`（两视图位置与形态一致，不隐藏、不移位）。
  - `frontend/src/pages/Dashboard.vue`：根据 `activeProvider` 分流展示：
    - `glm`：保留现有 GLM 仪表盘；
    - `opencode`：渲染与 GLM 同骨架的专属仪表盘（顶部控制条：左标题、右「上次采样 + 立即采样」；下方滑动/周/月 3 个额度行：百分比、细进度条、状态灯、倒计时；未配置 Key 时显示居中引导卡），差异仅在皮肤（暗色 console）。
  - `frontend/src/pages/History.vue`：Provider 为 opencode 时渲染空状态说明卡（结构与 GLM 未绑定引导卡一致；第一步无 OpenCode 历史），Provider 为 glm 时保持既有历史曲线零改动。
  - `frontend/src/pages/Settings.vue`：增加 OpenCode API 密钥维护卡片（支持保存、清除与脱敏展示）。
  - `frontend/src/style.css`（+ 新建 `frontend/src/components/oc/` 目录）：落地《需求·视觉规范：OpenCode Console 风格》的暗色 console 令牌与组件。

#### 7. `CREATED` 前端 OpenCode 控制台风格层（FR-4 视觉落地）
- **Purpose**: 将 OpenCode 官方 console（`opencode.ai/console` Go 用量页）的暗色扁平 console 语言作为 OpenCode Provider 视图的**皮肤层**（色彩/排版/细条形态）落地，交互骨架与 GLM 视图对齐，且严格隔离于既有浅色主题。
- **Complexity**: Medium
- **Style 依据**: `requirements.md` 的《视觉规范：OpenCode Console 风格》；上游开源参考 `sst/opencode`（分支 `dev`）的 `packages/console/app/src/style/token/{color,font,space}.css`、`packages/console/app/src/style/component/button.css`、`packages/console/app/src/component/{go-plan-chart,limits-graph}.css`、`packages/ui/src/styles/tokens/colors.css`。
- **Design Details**:
  - **令牌作用域**：新增 `.oc-console` 根容器类，全部暗色自定义属性（`--oc-bg: #242424`、`--oc-surface: #2e2e2e`、`--oc-track: #3a3a3a`、`--oc-border: #ffffff14`、`--oc-text: #f2f2f2`、`--oc-text-2: #aeaeae`、`--oc-text-3: #808080`、`--oc-warn: #f2cf76`、`--oc-crit: #ffa478`、`--oc-danger: #f1484f`、`--oc-bar-radius: 2px`）定义在该作用域内，**不**进入全局 `@theme`，保证 GLM 视图与外壳浅色令牌零污染（对齐 AC-7）。
  - **等宽数字类**：新增 `.oc-mono`（等宽字体栈）与复用既有 `.tnum`（`tabular-nums`），用于百分比、倒计时、`HH:MM:SS` 时间戳（对齐 AC-8）。
  - **组件拆分**：
    - `oc/ProviderSwitch.vue`：Provider 分段切换，常驻应用顶栏（沿用既有胶囊外形；两视图一致，过渡 ≤150ms）。
    - `oc/QuotaRow.vue`：单窗口额度行——标签 + 重置弱文本 / 右对齐百分比 + 4–6px 状态点 / 通栏 6px 细条（轨道 `#3a3a3a`、圆角 ≤2px、按 60% / 85% / `rate-limited` 阈值取色）。
    - `oc/SampleButton.vue`：控制条右侧「立即采样」按钮（刷新图标 + 加载旋转、按压反馈，`focus-visible` 用 `outline: 2px solid currentColor; outline-offset: 3px`）。
    - `oc/EmptyState.vue`：居中引导卡（与 GLM 未绑定卡同结构：图标 + 标题 + 说明 +「前往设置」按钮），触发 `store.tab = 'settings'` 并聚焦 OpenCode Token 输入框。
  - **动效**：填充过渡 400–700ms `cubic-bezier(0.22,1,0.36,1)`；悬停背景过渡 120–180ms；`prefers-reduced-motion: reduce` 下整体禁用。
  - **响应式**：容器查询窄于 640px 时额度行堆叠为两段式（标签整行 + 条形/数值次行），字号降一档，禁止横向滚动。
  - **反模式守卫**：不使用圆环/仪表盘组件、不使用阴影与大圆角卡片、除状态点与填充外不着色。
- **Verify**: `npm run build` 通过；人工核对 OpenCode 视图截图与参考截图逐条对齐（底色、1px 描边、6px 细条、tabular-nums 稳定性、无圆环组件）。

## Module Collaboration and Data Flow

```mermaid
flowchart TD
    subgraph UI ["前端界面 (Vue 3)"]
        TopNav["Provider 切换器 (GLM / OpenCode Go)"]
        DashView["OpenCode 仪表盘 (3卡片 + 采样按钮)"]
        SetView["设置页 (OpenCode Key 配置)"]
    end

    subgraph Wails ["Wails 绑定层 (guiapp)"]
        Bindings["BindingsService\n(SampleOpenCodeNow / SetOpenCodeToken)"]
        Runtime["MonitorRuntime (GUIState 快照)"]
    end

    subgraph Core ["业务服务层 (service)"]
        Svc["Service.SampleOpenCodeOnce()\nService.SetOpenCodeToken()"]
    end

    subgraph IO ["I/O 客户端与持久化"]
        Client["opencode.Client (net/http 探测)"]
        Store["store.Store (config.json)"]
        Remote["OpenCode 官方端点\n(https://opencode.ai/zen/go/v1/usage)"]
    end

    TopNav -->|切换 activeProvider| Bindings
    DashView -->|点击立即采样| Bindings
    SetView -->|保存/清除 Key| Bindings
    Bindings --> Runtime
    Bindings --> Svc
    Svc --> Client
    Svc --> Store
    Client -->|Bearer Token HTTP GET| Remote
```

## Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | `internal/cli/opencode.go` + `internal/store/store.go` + `internal/service/opencode.go` (Token set/show 脱敏) |
| AC-2 | `internal/cli/opencode.go` + `internal/opencode/client.go` (`opencode status` JSON 信封) |
| AC-3 | `internal/opencode/client.go` + `internal/service/opencode.go` (401 AuthError / 403 EntitlementError 规范映射) |
| AC-4 | `frontend/src/App.vue` + `Dashboard.vue` + `internal/guiapp/bindings.go` (Provider 切换与卡片展示) |
| AC-5 | 既有 `internal/service/service.go`、`internal/cli/root.go` 及 GLM 组件完全保持原逻辑与不变式 |
| AC-6 | `frontend/src/components/oc/*` + `frontend/src/style.css` 的 `.oc-console` 作用域令牌（底色/1px 描边/无阴影/6px 细条） |
| AC-7 | `.oc-console` 令牌作用域隔离（不写入全局 `@theme`），GLM 视图与外壳保持浅色 |
| AC-8 | `.oc-mono` + `.tnum` 数字排版与 `prefers-reduced-motion` 动效降级 |
| AC-9 | `frontend/src/App.vue` + `pages/Dashboard.vue` + `oc/ProviderSwitch.vue`（顶栏常驻切换器、单一导航、控制条与按钮同位、空状态同结构） |
| AC-10 | `frontend/src/pages/History.vue`（OpenCode Provider 下空状态说明，GLM 曲线零改动） |

## Design Review Notes

- **Q1: 为什么采用独立命名空间 `opencode` 而不是在原有命令加 `--provider`？**  
  **回应**：根据《CLI 工具开发标准》与 Unix 原则，各供应商的数据结构、窗口周期与认证机制不尽相同。独立命令组 `opencode status` 与 `status` 边界清晰，避免 flag 膨胀和破坏已有调用方的脚本假设。
- **Q2: 为什么第一步不开启后台轮询与 Toast 告警？**  
  **回应**：符合用户明确的“第一步可以先快速实现...让我很方便立刻查看现在的额度情况”原则。即时探测只需被动触发，零后台开销与锁竞争，风险极低且交付极快；告警记账可在第二步从容设计。
- **Q3: 为什么 console 暗色风格只作用于 OpenCode 视图，而不整体换肤？**  
  **回应**：用户已确认（仅 OpenCode Provider 内暗色，其余保持浅色）。既有浅色 Raycast/Linear 语言覆盖 GLM 仪表盘、历史走势与设置页，全量换肤会牵动 4 个页面与全部 GLM 组件，回归面远大于本次“快速交付”的范围；以 `.oc-console` 作用域隔离令牌，既拿到 console 的观感，又把回归风险收敛到新增视图内部（AC-7 即为此不变式）。**修订（交互对齐 v2，实测体验反馈）**：暗色仅保留为**皮肤层**——信息架构与交互骨架与 GLM 视图完全对齐（导航仅走顶栏、切换器常驻顶栏、控制条与按钮同位、空状态同结构），视图内不再复制 console 的独立页签导航与切换器位（AC-9 固化）。
- **Q4: 上游 console 页面不开源，如何保证“参考源代码”不流于口号？**  
  **回应**：区分“结构”与“数值”两条可核验来源——结构以用户提供的线上 console 截图为基准，数值取 OpenCode 开源仓库中实际在用的设计令牌与组件样式（`packages/console/app/src/style/token/*`、`component/go-plan-chart.css`、`limits-graph.css`、`packages/ui/src/styles/tokens/colors.css`）。所有取值均在《需求·视觉规范》表格中列出并附仓库路径，便于逐条比对，不对未公开源码做臆测。
- **Q5: 为什么数字必须等宽 + `tabular-nums`？**  
  **回应**：OpenCode console 明确使用等宽字体栈并设 `font-variant-numeric: tabular-nums`。本工具存在每秒倒计时刷新，比例字体下数字宽度变化会造成整行抖动；等宽数字是 console 质感与稳定读数的共同前提（AC-8 固化）。
