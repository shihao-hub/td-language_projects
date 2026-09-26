# 设计说明

## 概述

`sourcecount` 使用“公共 Server/Service 核心 + CLI/MCP 适配器”结构。CLI 与 MCP 在同一进程内组装同一个 `internal/service.Server`，由 Server 调用配置加载、目录遍历、文件分类和聚合组件。项目无数据库和持久化状态。

## 背景与约束

仓库 CLI 标准要求公共业务核心独立于入口，CLI 默认人读并支持 `--json`，独立工具提供 `schema`，MCP 适配器不能复制业务编排。Go 子仓使用独立项目目录，不在子仓根建立 workspace。

## 目标与非目标

### 目标

- 以文件后缀提供稳定、可复用的项目源码统计结果。
- 让配置过滤和类型覆盖可提交到项目仓库并可由 CLI/MCP 同样调用。
- 在大文件和部分权限失败场景下保持有限内存、可诊断和可自动化调用。

### 非目标

- 不引入 daemon、数据库、缓存或后台任务。
- 不实现单文件明细、Git 历史统计或语言级 AST 分析。

## 详细设计

### 公共契约与 Server

`CREATED` `internal/service/server.go`

- 定义 `Server`、`ScanRequest`、`ScanReport`、`Group`、`Totals` 和稳定业务错误。
- `Scan(ctx, request)` 负责校验请求、加载配置、调用扫描器并返回聚合结果。
- 不写 stdout/stderr，不调用 `os.Exit`；取消通过 `context.Context` 传递。
- 单文件读取错误进入报告 `Errors`，配置和根路径等调用错误直接返回稳定错误。

`CREATED` `internal/contract/types.go`

- 定义 CLI 与 MCP 共用的公开 JSON DTO。
- 每个后缀只有一个聚合项，内部同时包含 `Text` 与 `Binary` 部分，以支持同一后缀的混合类型文件。
- 计数使用无符号或非负整数语义，JSON 字段固定为 `extension`、`text`、`binary`、`groups`、`totals`、`errors`。

### 配置加载与 Glob

`CREATED` `internal/config/config.go`

- 解析版本为 `1` 的 `.sourcestats.json`。
- 规范化后缀：补充前导点并转小写；拒绝同一后缀同时出现在文本和二进制覆盖列表。
- 加载顺序为显式配置路径、当前工作目录配置、单根目录配置、内置默认值。
- CLI 重复参数覆盖配置文件对应数组；没有显式值时保留配置值。

`CREATED` `internal/config/glob.go`

- 使用 `/` 作为逻辑路径分隔符。
- `*`、`?`、字符类只匹配单个路径段；`**` 匹配零个或多个路径段。
- 目录命中 exclude 时剪枝整棵子树；include 非空时保留匹配文件、匹配目录及其后代。
- 不支持 `!` 反选语法，避免与 include/exclude 优先级冲突。

默认排除目录：`.git`、`.hg`、`.svn`、`node_modules`、`vendor`、`dist`、`build`、`target`、`.idea`、`.vscode`、`.venv`、`__pycache__`、`coverage`。

### 扫描器与统计器

`CREATED` `internal/scanner/scanner.go`

- 使用 `filepath.WalkDir` 遍历根路径。
- 在进入目录时检查 reparse/symbolic link 和排除规则；不跟随链接。
- 使用绝对规范化路径作为去重键；Windows 下大小写不敏感。
- 文件扩展名以最后一个点为准；单独点文件归 `<none>`。
- 每个文件只产生一个分类结果或一个错误记录。

`CREATED` `internal/scanner/classify.go`

- 后缀覆盖优先于内容探测。
- 未覆盖文件读取有限前缀进行探测：出现 NUL 或无效 UTF-8 判二进制，否则判文本。
- 二进制文件使用 `DirEntry.Info().Size()`；不读取完整内容。

`CREATED` `internal/scanner/text.go`

- 文本文件通过流式 UTF-8 解码统计 code point。
- 无效 UTF-8 在强制文本模式下按每个无效字节产生一个替换字符计数。
- 识别 LF、CRLF 和单独 CR；最后一个换行符之后不额外制造空行。
- 空文件为 0 行、0 字符。

### 聚合与并发

`CREATED` `internal/service/aggregate.go`

- 扫描结果通过有界 worker 处理；默认 worker 数为 `min(GOMAXPROCS, 8)`，不暴露额外配置参数。
- 聚合使用后缀键，分别累加文本 files/lines/chars 和二进制 files/bytes。
- 最终按后缀排序；`<none>` 排在普通后缀之后；错误按规范化路径排序。
- context 取消时停止新任务并返回取消错误，不伪造完整结果。

### CLI 适配器

`CREATED` `cmd/sourcecount/main.go`、`internal/cli/commands.go`

- 支持根路径、`--config`、`--include`、`--exclude`、`--text-ext`、`--binary-ext`、`--no-default-excludes`、`--json`、`--pretty`、`--version` 和 `--help`。
- 默认人读表格显示后缀、文本 files/lines/chars、二进制 files/bytes 和总计；不适用列显示 `-`。
- JSON 使用统一包络；部分失败保留 `data` 并设置 `ok=false`。
- 参数错误退出码 `2`，部分扫描失败退出码 `1`，成功退出码 `0`。
- `schema` 和 `--help`/`--version` 不创建 Server 扫描依赖，不读取业务文件。

### MCP 适配器

`CREATED` `internal/mcp/server.go`、`internal/mcp/tools.go`、`internal/mcp/schema.go`

- `sourcecount mcp` 使用 Go MCP SDK v1.8.0 的 stdio transport。
- 注册 `sourcecount.project.scan`，其输入字段映射到 `ScanRequest`，输出为 `ScanReport`。
- MCP handler 只负责输入映射、调用 Server、结构化输出和错误映射。
- `schema` 通过 in-memory MCP transport 读取真实工具定义，避免维护第二份工具清单。
- 日志全部输出 stderr，stdout 只允许 MCP 协议字节。

### 组装与版本

`CREATED` `cmd/sourcecount/main.go`

- 版本变量默认 `dev`，支持构建时 `-ldflags -X` 注入。
- CLI 与 MCP 都创建同一个 `internal/service.Server` 实现；MCP 常驻时不持有文件句柄，单次扫描结束释放所有资源。
- 不创建 `%APPDATA%` 下运行数据目录，因为本工具没有自有持久化数据。

## 模块协作与数据流

```text
CLI flags / MCP input
        │
        ▼
  request normalization
        │
        ▼
 internal/service.Server.Scan
        │
 ┌──────┼────────┐
 ▼      ▼        ▼
config scanner  aggregate
        │
        ▼
  ScanReport / business error
        │
   ┌────┴────┐
   ▼         ▼
 CLI view   MCP result
```

不变量由 Server 层负责：根路径与配置校验、后缀规范化、类型覆盖优先级、部分错误语义和聚合一致性。CLI/MCP 不允许绕过 Server 直接访问扫描器。

## 错误处理

- 配置不存在（自动发现时）：视为未配置，不报错；显式 `--config` 指向不存在文件：`config_not_found`，退出码 `2`。
- JSON 无法解析、版本不支持、规则冲突或 Glob 无效：`bad_config`，退出码 `2`。
- 根路径不存在或不是可访问文件/目录：`root_not_found`，退出码 `2`。
- 单文件 stat/open/read 失败：记录 `path`、稳定 `code` 和安全 message，继续扫描；最终返回 `partial_scan`，退出码 `1`。
- context 取消：返回 `cancelled`，不宣称扫描完成。
- MCP 将业务失败映射为 `IsError=true` 的结构化结果，不将普通扫描失败伪装成协议断连。

## 可测性

- 配置、Glob、扩展名、路径规范化和文本统计可独立单测。
- Server 使用临时目录做集成测试，测试文件只放测试实例目录并在结束后清理。
- CLI JSON、退出码和 schema 使用真实进程测试。
- MCP 使用 in-memory transport 验证注册与 handler，再使用真实 stdio 做启动冒烟验证。

## 验收标准映射

| 验收标准 | 设计组件 |
|---|---|
| AC-1、AC-2 | scanner、config/glob、aggregate |
| AC-3、AC-4 | scanner/classify、scanner/text |
| AC-5、AC-6 | config/config、config/glob、CLI 参数合并 |
| AC-7 | service.Server、ScanReport.Errors |
| AC-8 | internal/cli |
| AC-9、AC-10 | internal/mcp、contract |

## 设计评审记录

- 已选定公共 Server 层，不采用 CLI 与 MCP 各自扫描的实现。
- 已选定内置 Glob matcher，不引入 Git ignore 语义。
- 已选定无 daemon、无数据库、无运行时持久化文件。
- 未实现单文件明细和文本字节数，遵循已批准范围。