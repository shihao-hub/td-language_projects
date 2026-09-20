# liteconf MCP 入口开发计划

## 项目概述

- liteconf 是轻量配置中心（server + client SDK + 调试 CLI），`liteconf.exe` 目前仅有 `http`（curlie 透传）与 `schema` 子命令，README 明确"不提供 MCP，属标准 0.1 节例外"。
- 本次为 `liteconf.exe` 新增 `mcp` 子命令：MCP stdio server，其他软件（AI 客户端）经 `mcpServers` 配置以子进程方式启动它，即可让 AI 读写配置中心。
- 数据面走运行中 server 的 HTTP API（与 Web 控制台、curlie 同地位，不重复业务逻辑）；client SDK（`client/`）定位不变，仍是给业务进程 import 的库，MCP 是新增的第三入口。
- 工具范围选 **B（读写完整数据面）**：discovery + 读配置 + 写配置；长轮询 `watch` 不暴露。
- 协议实现用**官方 `github.com/modelcontextprotocol/go-sdk v1.8.0`**（用户已确认；《CLI 工具开发标准》10.2 已核对该版本行为）。

## 项目结构

```
go_projects/liteconf/
├── go.mod                          # [改] go 1.22 → 1.25.0（SDK v1.8.0 硬要求）+ 新依赖
├── cmd/liteconf/main.go            # [不动] 组装入口无变化
├── internal/
│   ├── cli/
│   │   ├── cli.go                  # [改] Run 分发增加 case："mcp"
│   │   ├── mcp.go                  # [新] mcp 子命令：-server flag 解析 + StdioTransport 组装
│   │   ├── catalog.go              # [改] commands 目录增加 mcp 条目、更新 schema 条目描述、help 文本
│   │   └── schema.go               # [改] 契约目录改为 tools（MCP 同源）+ commands 并存，移除 interface 字段
│   └── mcp/                        # [新] MCP 适配器包
│       ├── mcp.go                  # server 构建（newServer）与 Run(transport) 入口
│       ├── api.go                  # apiClient：HTTP 调 server /api/*，统一 apiError
│       ├── tools.go                # 三个工具的 In/Out 类型、handler、点路径下钻 lookup
│       ├── view.go                 # ToolSpecs：in-memory transport 读注册视图（供 schema 导出）
│       ├── api_test.go             # apiClient 单测（httptest + 真 NewMux/store）
│       └── tools_test.go           # in-memory 端到端：initialize/tools/list/tools/call 全分支
├── client/                         # [不动]
├── internal/server/                # [不动]
└── scripts/build.ps1               # [不动]（同一 cmd/liteconf 二进制）

docs/projects/go_projects/liteconf/
├── plans/01-mcp-server.md          # [新] 本计划（父仓库）
└── brunos/ specs/                  # [不动]
README.md（子仓 liteconf）           # [改] 特性/快速开始/MCP 工具表/定位与边界
```

## 核心数据结构

```go
// ---- internal/mcp/api.go ----

// apiError server 包络错误或客户端网络错误的稳定业务错误
type apiError struct {
    Code    string // not_found | invalid_name | invalid_json | internal | server_unreachable | path_not_found
    Message string
}
func (e *apiError) Error() string { return e.Message }

// apiClient 调用运行中 server 的 HTTP API；Timeout 15s（无 watch，无长请求）
type apiClient struct {
    base string
    hc   *http.Client
}
func newAPIClient(serverURL string) *apiClient
func (c *apiClient) discovery(ctx context.Context) (discoveryData, error)
func (c *apiClient) get(ctx context.Context, app, env string) (json.RawMessage, uint64, error)
func (c *apiClient) put(ctx context.Context, app, env string, content map[string]any) (uint64, error)
// 响应体 io.LimitReader 8MiB（对齐 client/client.go）；非 2xx 或 code != "ok" → *apiError

// ---- internal/mcp/tools.go ----

// toolOutput 复用 CLI JSON 包络语义（标准 5.2：ok 与 isError 按同一完成状态映射）
type toolOutput[D any] struct {
    OK    bool       `json:"ok"`
    Data  D          `json:"data,omitempty"`
    Error *apiError  `json:"error,omitempty"`
}

// discoveryData 对齐 server GET /api/discovery 的 data.apps
type discoveryData struct {
    Apps []appEntry `json:"apps"`
}
type appEntry struct {
    App  string     `json:"app"`
    Envs []envEntry `json:"envs"`
}
type envEntry struct {
    Env     string `json:"env"`
    Version uint64 `json:"version"`
}

// configGetData Content：整份配置为 map[string]any；带 path 时为下钻值
type configGetData struct {
    App     string `json:"app"`
    Env     string `json:"env"`
    Version uint64 `json:"version"`
    Content any    `json:"content"`
}

// configPutData 对齐 server PUT 返回的新版本号
type configPutData struct {
    App     string `json:"app"`
    Env     string `json:"env"`
    Version uint64 `json:"version"`
}

// 工具输入（jsonschema-go 按 tag 生成 inputSchema；无 omitempty 字段默认 required）
type emptyIn struct{}
type configGetIn struct {
    App  string `json:"app" jsonschema:"应用名，仅 [a-zA-Z0-9_-]，最长 128"`
    Env  string `json:"env" jsonschema:"环境名，仅 [a-zA-Z0-9_-]，最长 128"`
    Path string `json:"path,omitempty" jsonschema:"可选点路径（如 db.host）；空 = 整份配置"`
}
type configPutIn struct {
    App     string         `json:"app" jsonschema:"应用名，仅 [a-zA-Z0-9_-]，最长 128"`
    Env     string         `json:"env" jsonschema:"环境名，仅 [a-zA-Z0-9_-]，最长 128"`
    Content map[string]any `json:"content" jsonschema:"完整配置 JSON 对象（整体覆盖写）"`
}
```

## 对外接口设计

### CLI（liteconf.exe）

| 命令 | 参数 | 退出码 | 说明 |
|---|---|---|---|
| `liteconf mcp` | `-server URL`（默认 `http://127.0.0.1:8646`） | 常驻；启动失败 1，参数错误 2 | stdio MCP server；stdin/stdout 专用于协议，日志/启动诊断写 stderr |
| `liteconf schema` | 无 | 0 成功；1 导出失败 | **契约变更**：输出改为 `{"name","version","tools":[...MCP 同源...],"commands":[...CLI 契约...]}`，移除 `interface:"cli"` 字段 |
| `http` / `version` / `help` | 不变 | 不变 | 存量行为保持 |

AI 客户端接入示例（opencode/Claude 等的 `mcpServers`）：

```json
{ "mcpServers": { "liteconf": { "command": "D:\\...\\build\\liteconf.exe", "args": ["mcp"] } } }
```

### MCP 工具（能力表，对齐标准 1.1/5.2，命名三段式）

| MCP 工具 | 对应 API | 输入 | 结构化输出（data） | 行为标注 | 说明 |
|---|---|---|---|---|---|
| `liteconf.discovery` | `GET /api/discovery` | 无 | `{apps:[{app,envs:[{env,version}]}]}` | `readOnlyHint=true` | 列出全部应用/环境/版本 |
| `liteconf.config.get` | `GET /api/{app}/{env}` | `app, env` 必填；`path` 可选 | `{app, env, version, content}` | `readOnlyHint=true` | path 为 MCP 附加的点路径下钻（复用 SDK Get 语义）；path 不存在 → `path_not_found` |
| `liteconf.config.put` | `PUT /api/{app}/{env}` | `app, env, content` 必填 | `{app, env, version}` | `readOnlyHint=false, destructiveHint=true, idempotentHint=false`（重复写版本号继续 +1） | 整体覆盖写，返回新版本号 |
| watch 长轮询 | `GET /api/watch/...` | — | — | **不暴露** | 挂起 30~120s 不适合 MCP 请求-响应模型；AI 可重读 `config.get` 对比 version 替代；README 记录理由 |
| `http` 透传 | — | — | — | **不暴露** | 纯终端体验，无合理 MCP 形态 |

工具结果统一 `structuredContent = toolOutput[D]`（对象根，符合标准基线）；成功 `isError=false`；业务失败/网络失败 `isError=true` 且 structuredContent 为 `{ok:false,error:{code,message}}`；SDK 自动在 `content` 附带 JSON 文本块兼容旧客户端。

### `liteconf schema` 输出示例（新契约）

```json
{
  "name": "liteconf",
  "version": "0.2.0",
  "tools": [
    { "name": "liteconf.config.get", "description": "...", "inputSchema": {}, "outputSchema": {}, "annotations": {"readOnlyHint": true} }
  ],
  "commands": [ { "name": "http", "summary": "存量 CLI 契约，新增 mcp 条目" } ]
}
```

## 核心模块设计

### internal/mcp/mcp.go — server 构建与运行

```go
type Config struct {
    ServerURL string // server 地址
    Version   string // 注入版本号（serverInfo.version）
}

// newServer 构建并注册全部工具；transport 无关，供 Run 与测试/视图导出共用
func newServer(cfg Config) (*mcp.Server, error)

// Run 构建后在该 transport 上服务直到连接关闭
func Run(ctx context.Context, cfg Config, t mcp.Transport) error
// 生产路径（internal/cli/mcp.go 调用）：Run(ctx, cfg, &mcp.StdioTransport{})
```

- `mcp.NewServer(&mcp.Implementation{Name: "liteconf", Version: cfg.Version}, nil)`
- 三次 `mcp.AddTool(server, &mcp.Tool{Name:..., Description:..., Annotations:...}, handler)`；工具描述含：用途、参数约束（`[a-zA-Z0-9_-]{,128}`）、副作用（put 覆盖写 + 版本 +1）、上限（server 端 body 4MiB）。
- handler 统一模式（标准 10.2 已核对 v1.8.0 行为）：
  - 成功：`return nil, toolOutput[T]{OK: true, Data: d}, nil`（SDK 填 structuredContent + 校验 outputSchema + content 附 JSON 文本）；
  - 失败：`return &mcp.CallToolResult{IsError: true}, toolOutput[T]{OK: false, Error: ae}, nil`（不用 `error` 返回值——那会丢弃结构化输出）。
- 输入非法（缺 required、content 非对象）由 SDK 在进 handler 前按 inputSchema 拒绝；app/env 名称规则由 server 校验，MCP 透传 `invalid_name`（server 是唯一事实来源，适配器不重复业务校验）。

### internal/mcp/tools.go — handler 与点路径下钻

- `discovery` / `config.get` / `config.put` 直接映射 apiClient 调用；`*apiError` 即失败分支的 `error` 字段（`errors.As` 归一，非 apiError 的意外错误兜底为 `internal`）。
- `lookup(content map[string]any, path string) (any, bool)`：按 `.` 逐级下钻，仅接受 `map[string]any` 节点；空 path 返回整份。此逻辑本期仅 MCP 使用，放适配器层（未来 CLI 需要时再下沉共享）。

### internal/mcp/view.go — 注册视图导出（schema 同源）

```go
// ToolSpecs 经 in-memory transport 读取实际注册视图（标准 5.5 推荐路径），
// 遍历 tools/list 全部分页（nextCursor 循环），不触碰网络与业务依赖（满足标准 4.3）
func ToolSpecs(ctx context.Context, cfg Config) ([]*mcp.Tool, error)
```

实现：`mcp.NewInMemoryTransports()` → `server.Connect(ctx, transports.Server(), nil)` + `mcp.NewClient(...).Connect(ctx, transports.Client(), nil)` → `ListTools` 循环翻页 → 收集 `[]*mcp.Tool`。

### internal/cli/mcp.go 与 schema.go

```go
// runMCP：flag.NewFlagSet("mcp")；-server 默认 http://127.0.0.1:8646；
// 解析失败/多余位置参数 → stderr 诊断 + 退出 2；
// 启动诊断打印到 opt.Stderr；调用 mcp.Run(ctx, cfg, &mcp.StdioTransport{})，错误退出 1
```

`schema.go`：`contract{Name, Version, Tools, Commands}`；`Tools` 来自 `mcp.ToolSpecs`（失败 → stderr + 退出 1）；`Commands` 沿用现有 `commands` 目录。存量公开契约变更（移除 `interface` 字段、tools 取代其位）在 README 兼容记录。

## 实现步骤（分阶段）

### Phase 1 依赖与 API 客户端（约 1h）

- [x] 1.1 go.mod：`go 1.22` → `go 1.25.0`，`go get github.com/modelcontextprotocol/go-sdk@v1.8.0`；全 module `go build ./...` 确认 server/SDK 代码在 1.25 下无回归
- [x] 1.2 新建 `internal/mcp/api.go`：apiClient（discovery/get/put）、apiError（code 归一：包络 code 透传 + `server_unreachable` 兜底）、响应 8MiB 限制
- [x] 1.3 `internal/mcp/api_test.go`：`httptest.Server` 挂真 `server.NewMux`（store 用 `t.TempDir()`），覆盖 get/put/discovery 成功、`not_found`、`invalid_name`、`invalid_json`、body 超 4MiB（413→internal）、server 不可达（`server_unreachable`）

**验收标准**：`go build ./...`、`go vet ./...`、`go test ./internal/mcp/` 全绿；`go.mod` 出现 go-sdk 且 go 指令为 1.25.0。

### Phase 2 MCP server 与工具（约 2h）

- [x] 2.1 `internal/mcp/tools.go`：In/Out 类型（含 `toolOutput[D]`）、三个 handler、`lookup` 点路径下钻、错误归一 helper
- [x] 2.2 `internal/mcp/mcp.go`：`newServer`（工具注册 + 描述 + Annotations）与 `Run(ctx, cfg, transport)`
- [x] 2.3 `internal/mcp/tools_test.go`：in-memory transport 端到端——initialize → tools/list（3 个工具、名称/schema/annotations 断言）→ tools/call 全分支：discovery 空与非空、get 整份、get path 命中/未命中（`path_not_found`）、put 成功返回递增 version、put 后 get 一致、`not_found`、`invalid_name`、server 不可达（`server_unreachable`）、SDK inputSchema 拒绝缺参（协议层非法输入）

**验收标准**：`go test ./internal/mcp/ -v` 全绿，覆盖上述全部分支；工具失败分支的 structuredContent 均为 `{ok:false,error:{code,message}}` 且通过 SDK outputSchema 校验。

### Phase 3 CLI 集成与 schema 同源导出（约 1.5h）

- [x] 3.1 `internal/cli/cli.go` 增加 `case "mcp"`；新建 `internal/cli/mcp.go`（-server flag、退出码 1/2、stderr 诊断）
- [x] 3.2 `internal/mcp/view.go`：`ToolSpecs`（in-memory + 全分页遍历）
- [x] 3.3 `internal/cli/schema.go` 改造：`contract{Name, Version, Tools, Commands}`（移除 `interface` 字段）；`internal/cli/catalog.go` 增加 mcp 条目、更新 schema 条目 summary、help 文本与示例补 `liteconf mcp`
- [x] 3.4 测试：schema 输出可解析、`tools` 与 in-memory `tools/list` 名称集合一致（同源对照）、`commands` 含 mcp 条目；`liteconf mcp -server` 缺参数退出 2；`go test ./...` 全绿

**验收标准**：`go build ./... && go vet ./... && go test ./...` 全绿；`.\build\liteconf.exe schema` 输出新契约 JSON（tools 非空）；`liteconf mcp -server` 帮助行为符合表格。

### Phase 4 构建冒烟与文档（约 1h）

- [x] 4.1 `.\scripts\build.ps1` 重新构建两个 exe；确认 liteconf-server.exe 行为不变（不 import mcp 包）
- [x] 4.2 真实进程冒烟：`-root` 指向临时目录启动 server → PowerShell 管道向 `liteconf.exe mcp` stdin 逐行发 initialize / initialized / tools/list / tools/call(`liteconf.discovery`) / tools/call(`liteconf.config.put`) JSON-RPC → 断言 stdout 响应正确、stderr 无协议数据泄漏、结束进程干净
- [x] 4.3 README 更新：特性列表、快速开始（mcpServers 接入示例）、HTTP API 章节后新增 MCP 工具表与 watch 不暴露理由、"定位与边界"重写（删除"不提供 MCP"例外；零依赖表述精确为"server 与 client SDK 仅标准库；调试 CLI 因 MCP 入口引入官方 go-sdk v1.8.0"）、能力表与兼容记录（schema 契约变更、go.mod 1.25）
- [x] 4.4 本计划勾选全部任务、更新页脚

**验收标准**：冒烟脚本证据齐全（响应 JSON + stderr 干净）；README 与实现一致（按标准 9.3 清单过一遍）；`git status` 确认子仓/父仓改动范围隔离。

## 技术依赖

| 依赖 | 版本 | 为什么需要 |
|---|---|---|
| `github.com/modelcontextprotocol/go-sdk` | v1.8.0 | 官方 MCP Go SDK；协议正确性由 SDK 保证（标准 10.2 已核对该版本 handler 行为）；用户已确认接受引入第三方依赖 |
| Go 工具链 | ≥ 1.25.0（SDK go.mod 硬要求；本机 1.25.3 满足） | go.mod go 指令需同步 bump |

## 关键技术点（决策理由）

1. **数据面走 server HTTP API，不直连配置目录文件**：与 Web 控制台/curlie 同地位，业务逻辑（版本、校验、原子写、广播）零重复；直连文件会绕过 server 版本管理、依赖 5s poller 补偿，语义混乱。
2. **官方 SDK 而非手写 stdio 协议**：用户拍板；SDK 自动完成 inputSchema 生成与校验、structuredContent 填充与 outputSchema 校验、content JSON 文本块，少维护一份协议实现。代价：零依赖卖点破例（表述改为"server 与 client SDK 零依赖"）+ go.mod bump。
3. **失败分支用 `(IsError=true, typedOut, nil)` 而非返回 error**：标准 10.2 已核对——泛型 handler 返回 error 会丢弃结构化输出；要 `{ok:false,error:{...}}` 可被机器读取就必须走 typedOut。
4. **`ok`/`isError` 同状态映射 + 复用包络**：标准 5.2 认可；AI 客户端读 structuredContent 即得稳定错误码，不必拆 `code: message` 文案。
5. **watch 不暴露**：长轮询挂起 30~120s 与 MCP 客户端等待预算/取消语义冲突；等价替代（重读 + 对比 version）已足够，README 记录。
6. **schema 同源走 in-memory transport**：标准 5.5 推荐路径，天然与注册一致；全分页遍历满足标准 9.1"契约导出对照"。
7. **`idempotentHint=false`（put）**：重复 put 相同内容配置状态一致但版本号每次 +1（副作用不同），如实标注。
8. **MCP 封装 server API 而非 client SDK（`client/`）**：技术上 MCP 进程可以 import client（公开包），但形态不匹配，硬封装会更差——
   - **App/Env 绑定冲突**：`client.Config` 初始化时固定单 App/Env，而 MCP 工具的 app/env 是每次调用的参数（AI 要读任意组合、discovery 要覆盖全部）；用 client 就得为每个 (app,env) 动态维护一个带长轮询后台任务的实例，生命周期复杂且覆盖不全。
   - **只有读能力**：client 无 Put、无 discovery，写与发现仍要走 HTTP，最终两套调用路径并存；为此给公开 SDK 加写方法会污染其"轻量读客户端"定位。
   - **写后读不一致**：client 读的是本地缓存（长轮询异步追平），put 成功后立即 get 可能拿到旧值；AI 工具需要实时一致（read-your-writes），直调 API 天然满足。
   - **核心卖点用不上**：client 的价值在热路径零网络开销、断线容错、OnChange 回调，均为业务进程长驻场景设计；MCP 工具调用低频且请求-响应，OnChange 无工具形态承载（watch 已决定不暴露）。
   - 结论：client 是"业务进程的消费面"（Go 库，只能被 import），server API 是"管理面"；MCP 属管理面入口，走 API 是同构映射（与 Web 控制台、curlie 同路，同 Apollo 的 client SDK / Open API 划分）。client 保持零改动；`internal` 包不可对外，`apiClient` 独立实现（~百行，标准库 http）。

## 预计时间

| Phase | 内容 | 估时 |
|---|---|---|
| P1 | 依赖升级 + apiClient + 单测 | 1h |
| P2 | MCP server、三工具、in-memory 端到端测试 | 2h |
| P3 | CLI 集成、schema 同源导出、catalog/help | 1.5h |
| P4 | 构建、真实进程冒烟、README、计划收尾 | 1h |
| **合计** | | **5.5h** |

## 后续扩展（二期）

- `liteconf.config.history`：server 端先支持历史版本存储后再暴露回滚工具（当前 server 无历史，不做）。
- watch 的有界等待工具（"等待版本变化最多 N 秒"），待真实场景需要再按标准 5.4 评估。
- 多 server / 多环境聚合（一个 MCP server 挂多个 liteconf 实例）。
- HTTP Streamable transport 远程形态（内网定位暂不需要）。

## 注意事项

- **stdout 纯净性**：`mcp` 子命令下任何诊断/日志只写 stderr；`schema` 失败诊断同理（存量已符合，改造时保持）。
- **SDK 升级敏感点**：升级 go-sdk 时按标准 10.2 重验 IsError + typed output 与 outputSchema 校验行为，并在 README 更新协议/SDK 版本记录（协商基线 2025-11-25，SDK 支持至 2026-07-28）。
- **PowerShell 5.1 冒烟**：JSON-RPC 消息含中文时注意管道编码（优先 ASCII 消息）；断言用 `ConvertFrom-Json`。
- **数据目录**：MCP 进程自身零数据文件，不涉 `%APPDATA%` 约束；冒烟测试 server 数据用临时目录，不碰用户真实配置。
- **提交范围隔离**：子仓（go_projects：代码+README）与父仓（docs：计划文档）分两次提交，各自 `cd` 后执行；README 属子仓范围。
- **Model 变更提示**：本计划不涉数据库/ORM；server store 无改动。

---
**最后更新：** 2026-09-19
**作者：** AI & User
**版本：** v1.0
