# ccquota P0 设计：只读额度聚合（CLI + WebUI）

> 状态：设计定稿，待实现。日期：2026-11-18。
> 读者：实现者、评审者。
> 关联：`tasks.md`（同目录）、《CLI 工具开发标准》（v1，现行）。

## 1. 目标与范围

在不开 cc-switch 窗口的前提下，一条命令或一个页面看到 cc-switch 里所有已启用用量查询的供应商额度，并支持定时刷新。

- **做**：只读 cc-switch 数据、聚合查询、CLI 输出、内置 WebUI、缓存。
- **不做**：切换供应商、写 cc-switch 任何文件、OAuth token 刷新、修改 cc-switch 配置。
- **P0 查询器锁定六个**：`opencode_go`、`command_code`、`deepseek_balance`、`codex_wham`、`kimi_coding`、`agy_quota`。

## 2. 硬约束（已确认决策）

| # | 决策 | 说明 |
|---|---|---|
| 1 | 项目名 `ccquota`，路径 `go_projects/ccquota` | 子仓内单目录一项目 |
| 2 | 数据源只读 `~/.cc-switch/cc-switch.db` | `mode=ro` + `busy_timeout`；不写 |
| 3 | 全程只读，不写 `~/.cc-switch` | 含备份、日志、锁文件一律不落该目录 |
| 4 | 前端零构建纯 HTML/JS | `go:embed`，WebUI 与后续 Wails 共用 |
| 5 | Wails v2（P1） | 非 v3 |
| 6 | P0 仅六个查询器 | 其余内置模板留 P2 |
| 7 | 监听地址 `127.0.0.1:0` | 内核动态探测端口，打印 URL + 写 runtime.json（见 6.3） |

## 3. 数据源

### 3.1 cc-switch 库接入

`~/.cc-switch/cc-switch.db`（SQLite，`journal_mode=delete`，非 WAL），`PRAGMA busy_timeout` 兜住 cc-switch 的短写事务。

读取字段（显式列出，禁止 `SELECT *`）：

```sql
SELECT id, app_type, name, settings_config, meta, is_current, category
FROM providers
ORDER BY app_type, sort_index;
```

- 只取 `meta.usage_script.enabled = true` 的供应商（等价 cc-switch 卡片上开了「启用用量查询」的）。
- `autoQueryInterval`（本机实测为 5 分钟）作为默认刷新间隔来源。
- `settings_config.env.ANTHROPIC_AUTH_TOKEN` / `ANTHROPIC_BASE_URL` 用于第三方中转类查询。

### 3.2 凭据来源矩阵（逐项实测）

| 查询器 | 凭据落点 | 字段 |
|---|---|---|
| `opencode_go` | db `settings_config` | `env.ANTHROPIC_AUTH_TOKEN` |
| `command_code` | db `settings_config` | 同上 |
| `deepseek_balance` | db `settings_config` | 同上 |
| `codex_wham` | `~/.codex/auth.json` | `tokens.access_token`、`tokens.account_id` |
| `kimi_coding` | `~/.kimi-code/credentials/*.json` | `access_token`（注意：不是 `~/.cc-switch/kimi_accounts.json`，那里只有账号展示信息，用它请求会 401） |
| `agy_quota` | Windows 凭据管理器 | 目标名 `gemini:antigravity`（CredReadW） |

凭据只在内存中传递；任何日志、缓存、HTTP 响应都不含原始密钥。

## 4. 统一模型

```go
type Tier struct {
    Key         string     `json:"key"`         // five_hour / weekly / monthly
    Utilization float64    `json:"utilization"` // 0-100，已用百分比
    ResetsAt    *time.Time `json:"resetsAt,omitempty"`
}

type Balance struct {
    Value float64 `json:"value"`
    Unit  string  `json:"unit"` // CNY / USD
}

type Card struct {
    App        string    `json:"app"`    // claude / codex / kimi / agy
    ProviderID string    `json:"providerId"`
    Name       string    `json:"name"`
    BaseURL    string    `json:"baseUrl"`
    Kind       string    `json:"kind"`   // coding_plan / balance / subscription
    Current    bool      `json:"current"`
    OK         bool      `json:"ok"`
    Tiers      []Tier    `json:"tiers,omitempty"`
    Balance    *Balance  `json:"balance,omitempty"`
    Err        string    `json:"err,omitempty"`
    QueriedAt  time.Time `json:"queriedAt"`
}
```

`Utilization` 语义与 cc-switch 一致：**已用百分比**，展示时统一换算成「剩余 = 100 - utilization」。

## 5. 六个查询器契约

| Key | 请求 | 解析 | 错误映射 |
|---|---|---|---|
| `opencode_go` | `GET https://opencode.ai/zen/go/v1/usage`，`Authorization: Bearer <key>` | `usage.{rolling,weekly,monthly}.percent`；`percent == 0` 时丢弃 `resetsAt`（上游占位值） | 403 → 「Key 有效但无 Go 订阅」；解析空 → 「响应形态不认识」 |
| `command_code` | 顺序四调：`/alpha/whoami?limits=1` → `/alpha/billing/credits?orgId` → `/alpha/billing/subscriptions?orgId` → `/alpha/usage/summary?since&orgId`，同一 `Bearer` | `window{used,cap,resetAt}` → 百分比 | 401 → 「认证失败」；`org.id` 缺失时后续请求不带 `orgId` |
| `deepseek_balance` | `GET https://api.deepseek.com/user/balance`，`Bearer` | `balance_infos[].total_balance` + `currency` | 401/网络错误原样上抛为卡片 `Err` |
| `codex_wham` | `GET https://chatgpt.com/backend-api/wham/usage`，`Bearer access_token` | 主/次窗口 → `five_hour` / `weekly`；`plan_type` 作套餐名 | 401 → 「登录待刷新」（**不刷新**，引导回 cc-switch 授权中心） |
| `kimi_coding` | `GET https://api.kimi.com/coding/v1/usages`，`Bearer token` | `limits[].detail{limit,remaining,resetTime}` → `five_hour`；`usage{limit,remaining}` → `weekly` | 401/403 → 认证失败 |
| `agy_quota` | 执行 `agy -p "/usage" --output-format json` | `command.data.groups[].buckets[]`（`remaining_fraction`、`reset_time`）→ Gemini 组 + Claude/GPT 组 | 未安装 agy → 「未找到 Antigravity CLI」；EOF 类瞬态错误重试 3 次（1s/2s） |

### 5.1 `agy_quota` 为何走 CLI 而非 HTTP

cc-switch 直接打 `daily-cloudcode-pa.googleapis.com` 并伪装 UA `antigravity/cli/<ver>`，服务端按 UA 决定是否返回 Gemini 那组。本仓 `agyquota` 已验证另一条路：调用 agy 自己的 `/usage`，语义与 agy 界面一致、不受 UA 规则变动影响。

- 采用：调 agy CLI（`agy -p "/usage" --output-format json`，实测返回 `command.data.groups[].buckets[]`，含 `remaining_fraction` 与 `reset_time`）。
- 代价：依赖本机 agy；每次查询多一次进程启动（轮询 5 分钟一次可接受）。
- 备选（P2）：HTTP + UA 伪装，作为 agy 缺失时的降级路径。

## 6. 入口设计

### 6.1 CLI

```
ccquota list    [--json] [--app claude|codex|kimi|agy] [--enabled-only] [--refresh]
ccquota watch   [--interval 5m] [--once]
ccquota web     [--addr 127.0.0.1:0] [--open] [--refresh-interval 5m]
ccquota doctor  [--json]
ccquota schema
```

- 人读输出：零依赖纯文本对齐（不引入 lipgloss），一卡一行：名称、状态、各档剩余 + 倒计时、余额。
- `--json`：`{"ok":true,"data":{"items":[...]}}`；失败 `{"ok":false,"error":{"code","message"}}`。
- 退出码：`0` 成功、`2` 参数错误、`1` 其他失败。
- `doctor` 分四层定位：db 可读性 → 凭据存在性 → 端点连通性 → 响应形态；这是「额度查询失败」的第一排查入口。
- `schema` 零 I/O 输出 JSON Schema（不连 db、不发网络）。

### 6.2 WebUI

- 单页深色，按 `app` 分组，卡片信息密度对齐 cc-switch：名称 + 地址 + 「使用中」标记 + 各档「5 小时剩余 98% ⟳4h21m」+ 余额行。
- 剩余 < 10% 加粗加深；失败红字「额度没查到」，悬停显示 `Err`。
- 前端只请求 `/api/cards`，不含任何密钥。
- 默认仅绑 `127.0.0.1`；`--addr 0.0.0.0:port` 需显式指定才对外开放。

### 6.3 端口与实例发现

沿用本仓既有做法（liteconf / plansql / typeai / nutvault 一致）：`net.Listen("tcp", "127.0.0.1:0")` 由内核分配，启动时打印实际 URL 并写 `runtime.json`（`%APPDATA%\language_projects\ccquota\<dev|prod>\runtime.json`），供 `ccquota url` 与后续 GUI/MCP 发现。

**已知坑**（来自 clictl）：GUI/WebUI 每次随机端口会让 `localStorage` 的 origin 变化，因此任何界面偏好必须服务端持久化，不能只存 localStorage。

### 6.4 MCP 位置

P0 不提供 MCP，理由记录于此：P0 先验证六个查询器与只读接入。P1 补 `ccquota mcp`（stdio，按当前协议基线 `2026-07-28`），因 Service 层已独立、`schema` 同源导出，接入成本低，符合《CLI 工具开发标准》对普通管理工具的要求。

## 7. 缓存与刷新

- 缓存文件：`%APPDATA%\language_projects\ccquota\<dev|prod>\cards.json`，只存 `Card` 快照与 `queriedAt`，**不含凭据**。
- 默认 TTL 5 分钟（对齐 cc-switch `autoQueryInterval`）：`list` 命中缓存直接返回，`--refresh` 强制拉取；`web`/`watch` 常驻时后台按 TTL 刷新。
- 查询失败不清空上一条成功快照：卡片保留旧值并标记 `Err` + 陈旧时间，避免「一次抖动全变红」。

## 8. 安全红线

- 密钥仅进程内存；日志统一掩码（仅保留前 4 / 后 4 字符）。
- 不读取、不复制浏览器登录态；不碰系统凭据管理器以外的账号存储。
- 不写 `~/.cc-switch`、不向其目录落任何缓存/锁/临时文件（AGENTS §四 反面案例）。
- HTTP 响应与 `--json` 输出均不含 token、不含完整 base URL 之外的敏感字段。

## 9. 复用的既有先例

| 先例 | 复用内容 |
|---|---|
| `.archived/.../agyquota` | agy `/usage` 调用、EOF 重试、`CredReadW` 读 `gemini:antigravity`、PE 子系统静默副本 |
| `.archived/.../glmquotawatch` | Wails 额度监控的产物形态与托盘交互（P1 参考，不复用 v3） |
| `go_projects/liteconf` | `127.0.0.1:0` + `runtime.json` + `--open` 的 serve 结构 |
| `go_projects/plansql` | Wails GUI 与 CLI 共用 HTTP 数据面的分层 |

## 10. 风险与防御

| 风险 | 防御 |
|---|---|
| 未文档化端点变更（`zen/go/v1/usage`、`/alpha/*`） | 逐窗口防御解析，单窗口失败不整体失败；每查询器独立单测覆盖异常形态 |
| OAuth token 过期 | 只读不刷新，返回明确状态文案；绝不回写凭据 |
| agy CLI 抢焦点 | 静默副本（PE Subsystem 改写），失败时不回退原 exe |
| cc-switch 写库时短暂占用 | `busy_timeout` + 只读连接重试一次 |
| 本仓同类项目反复停更（agyquota 两次归档） | 查询器与入口解耦，接口变更只改一个文件；`doctor` 降低排障成本 |

## 11. 验收（DoD）

1. `ccquota list` 一次输出六张卡，其中与截图逐项对齐：DeepSeek `73.91 CNY`、OpenCode Go `5h 98% / 周 99% / 月 56%`、Codex `5h 84% / 周 91%`、Kimi `5h 93%`、Antigravity 两组 `100%`。
2. Command Code 走 401 分支，卡片显示「认证失败」而非空白。
3. `ccquota list --json` 可被 `jq` 直接解析，符合 `{"ok":true,"data":...}` 包络。
4. `ccquota doctor` 对缺失凭据/不可达端点给出定位结论。
5. `ccquota web` 随机端口启动、打印 URL，页面同屏六卡、阈值着色正确。
6. `git status` 干净：无临时脚本、无密钥、无 `~/.cc-switch` 写入。
