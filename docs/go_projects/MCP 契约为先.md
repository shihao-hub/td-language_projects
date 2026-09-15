# MCP-FIRST —— MCP 契约为先的工具设计方法论

> 面向开发者与 AI agent：以 MCP 契约为设计起点，service 承载实现，MCP/CLI 双壳平行适配。
>
> 相关文档：概念与决策框架见《[统一核心与多通道投影指南](<统一核心与多通道投影指南.md>)》；
> 双入口实施细节、SDK 行为与验收见《[CLI 与 MCP 双壳架构工作指南](<CLI 与 MCP 双壳架构工作指南.md>)》。
>
> 更新：2026-09-15，第一版。

## 背景与动机

MCP（Model Context Protocol）已经是行业既定协议：Anthropic 开源后，Claude Desktop、Zed、opencode 等主流 AI 客户端均已原生支持。而 CLI 没有等价的机器可读协议——`--help` 是给人看的松散文本，`man page` 是散文，没有任何一份「这个工具有哪些能力、每个能力吃什么参数、吐什么结果」的结构化定义。

这意味着在 AI 时代：

- **工具配套 MCP 是基本要求**：AI 客户端读到 JSON Schema 就能发现、理解、调用你的工具，零文档、零适配、零胶水代码。
- **MCP 契约可以充当 API 设计文档**：工具清单 + JSON Schema 的地位等同于 Web 开发中的 OpenAPI——它是一份可机器验证、可生成文档、可驱动多端渲染的能力契约。
- **CLI 的定位变了**：不再是唯一入口，而是面向 shell / 脚本 / cron / CI 的人机工程学包装。

因此新工具的正确开发范式是：**MCP 契约先行 → service 承载实现 → MCP/CLI 双壳平行适配**。

---

## 核心主张

### 一、设计顺序：MCP 契约先行

先定义 MCP 工具清单（名称 + JSON Schema + 描述），相当于先写 OpenAPI。这份契约就是完整的 API 设计文档：

- 每个工具的能力边界、参数类型、必填/可选、描述全部显式声明；
- 契约一旦定稿，MCP 壳、CLI、GUI、离线文档全部可以从同一份定义推导或生成；
- 设计阶段就能用 MCP Inspector 验证契约是否合理（参数是否自描述、粒度是否合适），比写完 CLI 再补 MCP 少了整整一轮返工。

**边界：契约先行指规格顺序，不是能力边界。** 先写对外契约（工具清单与 JSON Schema）是正当的规格工作流；核心的语义与执行模式（buffered / streaming / interactive）仍按领域用例定义，不能把 MCP 渠道的当前形状当成核心的能力上限与职责边界。渠道归类方法见《[统一核心与多通道投影指南](<统一核心与多通道投影指南.md>)》第 0 章与 5.1 节。

### 二、实现顺序：service 单一真相源

无论先做哪个壳，**业务逻辑只写一份，沉淀在 service 层**，MCP 壳和 CLI 壳都是薄适配层。

```
             ┌── internal/mcp   （薄壳：工具定义 + JSON-RPC → service）
service 层 ──┤
（核心业务）  └── internal/cli   （薄壳：flag 解析 → service → JSON 包络）
```

### 三、定位：双壳平行，CLI 不是降级配套

| | MCP 壳 | CLI 壳 |
|---|---|---|
| 消费者 | AI 客户端（LLM 决定调用） | 人类、shell 脚本、cron、CI |
| 可发现性 | 强（JSON Schema 自描述） | 弱（`--help` 散文本） |
| 组合能力 | 无（每次调用是独立 JSON-RPC 往返） | 强（管道、重定向、`&&`） |
| 交互能力 | 无（LLM 无法与子进程交互） | 强（stdin 透传、TUI） |
| 依赖 | 必须有 AI host 拉起 | 独立可执行 |

两者是**平行关系**，不是主从。CLI 服务脚本自动化场景，MCP 服务 AI 客户端场景，各自覆盖对方做不到的事。

---

## 分层架构

### service 层：三条铁律

```go
// Package service 承载 clictl 的业务逻辑：参数校验 + store/runner 调用，
// 返回 (data, error)。不做任何输出与 os.Exit——CLI 包络层与 MCP 适配层共用。
package service
```

**铁律一：输入输出用纯 Go 类型。** 不含 flag、不含 JSON Schema 概念、不含任何壳的术语。CLI 的 `flag.String` 和 MCP 的 `jsonschema` tag 都只是壳里的事：

```go
// Add 注册 exe：校验 .exe 后缀、路径存在性、名字合法性（name 空 = 文件名去
// .exe 小写化）。meta 为空/nil 时存 NULL。
func (s *Service) Add(path, name, desc string, meta json.RawMessage) (store.Tool, error) {
	if strings.ToLower(filepath.Ext(path)) != ".exe" {
		return store.Tool{}, &Error{Code: "not_exe", Message: "v1 仅支持注册 .exe 文件: " + path, ExitCode: 1}
	}
	abs, err := filepath.Abs(path)
	if err != nil {
		return store.Tool{}, &Error{Code: "bad_args", Message: "路径无效: " + err.Error(), ExitCode: 1}
	}
	if fi, err := os.Stat(abs); err != nil || fi.IsDir() {
		return store.Tool{}, &Error{Code: "file_not_found", Message: "文件不存在: " + abs, ExitCode: 1}
	}
	// ... 名字校验 ...
	tool, err := s.st.AddTool(finalName, abs, desc, metaRaw)
	if err != nil {
		return store.Tool{}, wrapErr("add", err)
	}
	return tool, nil
}
```

**铁律二：不写 stdout、不 os.Exit。** 输出与退出码是壳的职责，service 只返回 `(data, error)`。

**铁律三：错误类型同时携带两种壳需要的信息。**

```go
// Error 业务错误：Code 即 JSON 错误码；ExitCode 为 CLI 退出码（0 表示未指定，
// 调用方按命令类型取默认值 1）；Suggestions 为未注册工具的相似名建议（可选）。
type Error struct {
	Code        string
	Message     string
	ExitCode    int
	Suggestions []string
}
```

- `Code` + `Message` → MCP 的 `IsError` 结果、CLI 的 JSON 错误包络，同一份文案；
- `ExitCode` + `Suggestions` → CLI 专属，MCP 忽略；
- 一个错误类型，两个壳各取所需，永不漂移。

### MCP 壳：jsonschema tag 即工具契约

MCP 壳的输入类型用 struct + `jsonschema` tag 声明参数，SDK 自动推导 JSON Schema（2020-12），MCP 客户端据此渲染表单：

```go
type addIn struct {
	Path string         `json:"path" jsonschema:"exe 文件路径；须为 .exe 后缀且文件存在"`
	Name string         `json:"name,omitempty" jsonschema:"调用名；缺省为文件名去 .exe 后小写化"`
	Desc string         `json:"desc,omitempty" jsonschema:"描述"`
	Meta map[string]any `json:"meta,omitempty" jsonschema:"扩展属性对象；仅允许 source 与 tags 两个 key，传 {} 等价于不设置"`
}
```

注册与处理：工具定义一处编写，handler 里只做「参数转换 → 调 service → 结果包装」：

```go
// registerTools 注册全部 MCP 工具（与 clictl schema 导出同源）
func registerTools(s *mcp.Server) {
	mcp.AddTool(s, &mcp.Tool{
		Name:        "clictl.add",
		Description: "注册一个 exe 工具；名字缺省取文件名去 .exe 小写化",
		Annotations: &mcp.ToolAnnotations{Title: "注册工具", OpenWorldHint: boolPtr(false)},
	}, func(ctx context.Context, req *mcp.CallToolRequest, in addIn) (*mcp.CallToolResult, toolView, error) {
		svc, err := mustSvc()
		if err != nil {
			return errResult(err), toolView{}, nil
		}
		raw, err := marshalMeta(in.Meta)
		if err != nil {
			return errResult(&service.Error{Code: "bad_args", Message: "meta 序列化失败: " + err.Error()}), toolView{}, nil
		}
		tool, err := svc.Add(in.Path, in.Name, in.Desc, raw)
		if err != nil {
			return errResult(err), toolView{}, nil
		}
		return nil, toolToView(tool), nil
	})
	// ... 其余 9 个工具同上 ...
}
```

业务错误走 `IsError` 结果而非协议级错误（MCP 规范：客户端要能看到并自我纠正）：

```go
// errResult 把业务错误转为 IsError 结果。MCP 规范：工具自身的业务错误
// 走结果（IsError + 内容）而非协议级错误，客户端才能看到并自我纠正。
// 文本格式 "code: message"，与 CLI errText 展示一致。
func errResult(err error) *mcp.CallToolResult {
	var se *service.Error
	if !errors.As(err, &se) {
		se = &service.Error{Code: "internal", Message: err.Error()}
	}
	return &mcp.CallToolResult{
		IsError: true,
		// ... Content 为 "code: message" 文本 ...
	}
}
```

**关键约束：协议 stdout 必须纯净。** stdio 传输下 stdout 只走 JSON-RPC 消息，所有日志走 stderr：

```go
// Run 启动 stdio MCP server，阻塞至客户端断开。
// log 默认输出到 stderr，前缀标记来源，确保协议 stdout 纯净。
func Run(ctx context.Context) error {
	log.SetPrefix("[clictl-mcp] ")
	log.SetFlags(log.LstdFlags)
	return NewServer().Run(ctx, &mcp.StdioTransport{})
}
```

**契约同源导出**：`clictl schema` 子命令导出与 `tools/list` 同源的工具定义，离线可查、可进 CI：

```go
// cmdSchema 导出与 tools/list 同源的工具定义（含 JSON Schema），离线检查用；
// 与 help 一样不打开业务数据库。
func cmdSchema(args []string) int {
	tools, err := mcp.Schema(context.Background())
	if err != nil {
		Fail("internal", "导出工具定义失败: "+err.Error())
		return 1
	}
	Emit(map[string]any{
		"name":    "clictl",
		"version": Version,
		"tools":   tools,
	})
	return 0
}
```

### CLI 壳：flag 解析 → service → JSON 包络 + 退出码

```go
func cmdAdd(args []string) int {
	fs := newFlagSet("add")
	name := fs.String("name", "", "调用名，默认=文件名去 .exe 后小写")
	desc := fs.String("desc", "", "描述")
	meta := fs.String("meta", "", `扩展属性 JSON，如 {"source":"cargo","tags":["dev"]}`)
	flags, positional := splitFlags(args, map[string]bool{"name": true, "desc": true, "meta": true})
	if !parseFlags(fs, flags) {
		return 0
	}
	if len(positional) != 1 {
		Fail("bad_args", "用法: clictl add <path> [--name N] [--desc D] [--meta JSON]")
		return 1
	}
	tool, err := mustService().Add(positional[0], *name, *desc, json.RawMessage(*meta))
	if err != nil {
		failService(err, false)
		return 1
	}
	Emit(tool)
	return 0
}
```

CLI 壳只做四件事：**解析参数 → 调 service → JSON 序列化 → 退出码**。`failService` 把 `service.Error` 翻译成退出码与 JSON 错误包络，退出码语义由 service 的 `ExitCode` 字段决定（如未注册 = 127）。

**生命周期适配**：CLI 每命令一进程即用即弃（惰性打开，`help`/`version` 不触发建连）；MCP server 常驻复用（首个工具调用时才开数据库）。两种生命周期对 service 的接口要求一致——`Open()` + 长持连接。

---

## 能力对齐原则

### 必须同源对齐的（靠单一真相源保证，不靠人肉同步）

| 维度 | 同源机制 | clictl 证据 |
|---|---|---|
| 校验 | 运行时校验（存在性/唯一性/字节上限）全在 service 层 | `Add` 里的后缀/路径/名字校验；MCP 的 jsonschema tag 只描述结构 |
| 错误码 | `service.Error` 是唯一错误形态 | CLI 打成 JSON 包络、MCP 打成 IsError，文本格式 `code: message` 一致 |
| 业务行为 | 增删改查、记账、探活只有一份实现 | MCP handler 与 CLI cmd\* 调用同一个 `svc.Add` / `svc.ListTools` |
| 工具定义 | `registerTools` 一处定义，`tools/list` 与 `schema` 导出共用 | `mcp.Schema()` 与注册走同一份结构体 |

### 刻意不对齐的（这是设计而非遗漏）

以下差异不是 bug，是两种消费者的特性决定的：

| 维度 | CLI | MCP | 原因 |
|---|---|---|---|
| `run` 的 IO | stdin/stdout/stderr 直通，阻塞等退出 | stdin 关闭、stdout/stderr 各保留 1 MiB（超限截断标记） | LLM 无法与子进程交互，长输出会撑爆上下文 |
| `run` 的终止 | Ctrl+C 吞掉，等子进程退出回写记录 | 超时/取消 → 杀整棵进程树（Job Object） | 无人值守场景需要硬超时 |
| 输出格式 | `--pretty` / `--ascii` 修饰 | 结构化字段（`stdout_truncated` / `timed_out` / `cancelled`） | 人读 vs 机器读 |
| 补全脚本 | `completion` 输出 raw 文本（输出即协议） | 不存在 | MCP 客户端自带 schema 渲染，不需要补全 |
| 输出视图 | 直接序列化 store 类型 | `toolView` 把 `meta` 从 `RawMessage` 展开为对象 | Schema 推导不认 `json.RawMessage`（会被当成整数字节数组） |

### MCP 非交互执行的实现

```go
// execTool 非交互执行：stdin 关闭、参数数组直传、收集输出与退出码。
// 取消（ctx）/超时 → 杀整棵进程树；启动记账闭环与 CLI run 一致。
func execTool(ctx context.Context, svc *service.Service, name string, args []string, timeoutMs int64) (runOut, error) {
	tool, err := svc.PreflightRun(name)
	if err != nil {
		return runOut{}, err
	}
	// ... 执行、收集输出、超时树杀、记账闭环 ...
}

// limitedBuffer 读到上限后继续消费写入（返回成功）但不再保留，防 pipe
// 写满阻塞子进程；truncated 标记是否丢弃过内容。
func (lb *limitedBuffer) Write(p []byte) (int, error) {
	if remain := maxStreamBytes - lb.buf.Len(); remain > 0 {
		if len(p) <= remain {
			lb.buf.Write(p)
			return len(p), nil
		}
		lb.buf.Write(p[:remain])
	}
	lb.truncated = true
	return len(p), nil // 声明全部消费，调用方（exec copy）继续排空
}
```

注意 `svc.PreflightRun` 与 CLI `run` 的前置校验也是同一个 service 方法——对齐的是业务语义（未注册 = 127 错误），不对齐的是 IO 形态。

---

## 落地路径

### 新项目（推荐顺序）

```
① 契约先行   定义 MCP 工具清单（名称 + 参数 Schema + 描述）← 纯设计，类比写 OpenAPI
② service    按契约实现业务层（纯 Go 类型进出，无 IO/无 os.Exit）
③ MCP 壳     契约 → jsonschema tag + handler → service
④ CLI 壳     契约翻译成子命令 + flag → 同一个 service
```

用 MCP Inspector 在第一、三步之间反复调试验证（`npx @modelcontextprotocol/inspector <exe> mcp`），业务正确性最早可验证。

### 既有 CLI 整改

```
① 盘点命令面   分两类：业务命令（→ service）/ 体验命令（留壳：help、completion、透传）
② 抽 service   业务逻辑下沉，输入输出改纯 Go 类型，错误改 *Error{Code, ExitCode, Suggestions}
③ 重接 CLI 壳  原命令改为「flag → service → JSON 包络 + 退出码」
④ 叠 MCP 壳    按业务命令逐一映射为 MCP 工具（粒度可不同，见下）
```

### 契约 → CLI 的「翻译」注意三点

1. **粒度可不同**：MCP 工具面向 LLM 要自描述、防呆（枚举、默认值、互斥说明）；CLI 面向人有补全、管道习惯。不必一一对应。
2. **交互型能力留 CLI**：透传、交互式 stdin、流式输出在 MCP 没有等价物，不要强行映射。
3. **MCP 优先 ≠ 放弃 CLI 体验**：CLI 的 `--pretty`/`--ascii`/补全是合理特化，不要求 MCP 也具备。

---

## 适用性判断

| 适合 MCP 优先 | 不适合 / 不值得 |
|---|---|
| 有状态、有存储的管理型工具（注册表、任务队列、配置管理） | 一次性脚本、纯格式转换器 |
| 能力面稳定、可枚举为工具清单 | 输出即协议的命令（如补全脚本生成器） |
| 希望被 AI 客户端 / GUI / 其他程序接入 | 纯透传型能力（MCP 无法承载交互式 IO） |
| 多消费者（CLI + GUI + AI）共享核心逻辑 | 生命周期极端短暂、无状态可言的工具 |

---

## 参考实现：clictl

完整落地范例，各分层证据：

| 分层 | 文件 | 说明 |
|---|---|---|
| service | `internal/service/service.go` | `Error` 类型、`Service`、`wrapErr` 错误映射 |
| service | `internal/service/tools.go` | `Add`/`ListTools`/`Info` 等业务方法 |
| MCP 壳 | `internal/mcp/server.go` | `NewServer`、`Run`、`errResult` |
| MCP 壳 | `internal/mcp/tools.go` | `registerTools`、输入/输出类型、`jsonschema` tag |
| MCP 壳 | `internal/mcp/exec.go` | 非交互执行、`limitedBuffer` |
| CLI 壳 | `internal/cli/commands.go` | `cmdAdd` 等、`failService`、`cmdMcp`、`cmdSchema` |
| 契约导出 | `clictl schema` | 与 `tools/list` 同源的工具定义导出 |

配套文档（父仓）：
- `docs/go_projects/clictl/clictl 使用指南.md`
- `docs/go_projects/clictl/MCP 接口文档.md`
- `docs/go_projects/clictl/Go CLI JSON 输出模式参考.md`
- `docs/go_projects/clictl/migrations/`（表结构变更存档）

---

## 附：新项目 MCP + CLI 落地检查清单

### 设计阶段

- [ ] MCP 工具清单已定义：名称、描述、参数 Schema、每个工具的能力边界
- [ ] 工具粒度经过 Inspector 验证（参数自描述、无歧义、防呆枚举到位）
- [ ] 明确哪些能力**不进** MCP（交互式、透传型、输出即协议的命令）
- [ ] 输出形状已定义（含错误形态）

### service 层

- [ ] 输入输出均为纯 Go 类型，无 flag / jsonschema / JSON 包络概念
- [ ] 无 `fmt.Println` / `os.Exit` / 直接写 stdout
- [ ] 错误统一为 `*Error{Code, Message, ExitCode, Suggestions}` 形态
- [ ] `Open()` 惰性可用（支持即用即弃与常驻两种生命周期）
- [ ] 运行时校验（存在性、唯一性、上限）全在 service 层，不依赖 Schema

### MCP 壳

- [ ] `jsonschema` tag 覆盖所有参数（描述清晰、可选字段 omitempty）
- [ ] 业务错误走 `IsError` 结果而非协议错误
- [ ] 日志全走 stderr，stdout 只走协议
- [ ] 非交互执行有超时、输出截断、进程树终止机制
- [ ] `tools/list` 与 `schema` 导出同源

### CLI 壳

- [ ] 命令实现只有「解析 → service → 输出 → 退出码」四步
- [ ] 退出码语义与 service.Error 对齐（127 等）
- [ ] 管理命令输出 JSON 包络（`{"ok":true,"data":...}` / `{"ok":false,"error":...}`）
- [ ] 交互型命令（透传）的 stdout 不被管理数据污染
- [ ] `help` / `version` 不触发数据库/网络连接

### 对齐验证

- [ ] 同一操作的错误码 CLI 与 MCP 一致（对照表或自动化测试）
- [ ] 参数校验在两侧行为一致（同一输入 → 同一错误）
- [ ] 刻意不对齐项（IO 形态等）已记录在案，非遗漏
- [ ] MCP Inspector 全工具冒烟通过
