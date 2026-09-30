# zedhub 对接协议

> 生成依据：`zedhub schema`（与实际注册定义同源）。本文是五通道契约的人读版；
> 机器可读版执行 `zedhub schema`（纯本地，不连 daemon、不连数据库）。
> 版本：随 `zedhub --version`。

## 总览（v2 daemon 架构）

```
CLI 薄壳 ─┐
rpc 薄壳 ─┤
MCP 桥  ──┼──→ HTTP+JSON API（127.0.0.1:8766，唯一契约）──→ daemon（zedhub serve）
第三方 curl┘        + SSE 进度流
                   WebSocket 学习通道（127.0.0.1:8765，冻结）
```

- Service 层只存在于 daemon；壳内只有参数解析、HTTP client 与渲染。
- 纯本地命令：`--help`、`--version`、`schema`、补全脚本（不触发 daemon）。
- 地址发现：`--host host:port` → `ZEDHUB_HOST` → 地址文件
  （`%APPDATA%\language_projects\zedhub\runtime\daemon.json`）→ 默认
  `127.0.0.1:8766`。
- 自动拉起仅生产构建（干净 tag 版本）；开发构建报错提示先 `zedhub serve`。
- buildID 握手：请求头 `X-Zedhub-Build`；开发态为源码指纹（`dev-<hash>`），
  生产态 `v{version}`；不等返回 `409 handshake_mismatch`。
- 自动拉起的 daemon 空闲 30 分钟退出；前台 `serve` 不退出。

## HTTP API（`/api/v1`）

### 信封

```jsonc
// 成功
{"ok": true, "data": ..., "meta": {"count": 3, "elapsed_ms": 12}}
// 失败（error.code 是唯一稳定契约；状态码仅辅助）
{"ok": false, "error": {"code": "not_found", "message": "..."}}
```

### 错误码 → HTTP 状态

| code | 状态 | 含义 |
|---|---|---|
| invalid_params | 400 | 参数错误 |
| not_found | 404 | 记录未找到 |
| source_not_supported | 400 | 数据源未实现（pi/claude-code/codex/antigravity） |
| data_source_missing | 503 | db 文件不存在 |
| schema_incompatible | 500 | 表/列缺失不可降级 |
| snapshot_failed | 500 | 快照复制失败 |
| process_running | 409 | 写前进程检查失败 |
| write_failed / verify_failed / data_dir_error | 500 | 写入/复查/数据目录失败 |
| method_not_supported | 404 | 未知端点 |
| invalid_request | 400 | 请求形状错 |
| handshake_mismatch | 409 | buildID 握手失败 |
| internal_error | 500 | 未捕获异常 |

### 端点

| Method | Path | 业务方法 | 说明 |
|---|---|---|---|
| GET | /health | — | 存活 + buildID（握手基准） |
| GET | /threads | threads.list | project/agent/archived/since/until/search/limit |
| GET | /threads/{thread_id} | threads.show | |
| GET | /projects | projects | |
| GET | /stats | stats | Zed 总览 |
| GET | /sources | sources | source 注册表状态 |
| GET | /sessions | sessions.list | source/project/agent/archived/limit |
| GET | /sessions/{session_id} | sessions.show | |
| GET | /sessions/{session_id}/content | sessions.content | |
| GET | /stats/effort | stats.effort | 启动模型×档位（降级标志在 payload） |
| POST | /sessions/link | sessions.link | 补登；SSE |
| POST | /archive/export | archive.export | SSE |
| POST | /archive/inspect | archive.inspect | |
| POST | /archive/import | archive.import | SSE |

安全边界：只监听回环；`Host` 头必须回环域（否则 403）；无鉴权（本地通道）。

### SSE（写类端点，`Accept: text/event-stream`）

```jsonc
event: stage\ndata: {"stage": "backup", "detail": "...", "pct": 40}
event: result\ndata: {完整结果对象（同同步形态 data）}
event: error\ndata: {"code": "...", "message": "..."}
```

- stage 阶段：validate → process_check → backup → id_map → write →
  checkpoint → verify；
- 客户端断流**不中止**已开始的写流水线：结果照常落 operation journal；
- 写流水线全局互斥（daemon 内单一写者）。

## MCP（`zedhub mcp`，stdio 桥）

- 桥启动先与 daemon 握手，失败即报错退出；写操作不注册。
- 存量平名（兼容，不迁移）：`threads_list`、`threads_show`、`projects`、`stats`；
- 三段式（`ToolAnnotations(read_only)` + structured_output）：
  `zedhub.sessions.list`、`zedhub.sessions.show`、`zedhub.sessions.content`、
  `zedhub.stats.effort`。

## 兼容 JSON-RPC（`zedhub rpc`，stdio，冻结）

- 行分隔 JSON-RPC 2.0；方法表冻结：`threads.list`、`threads.show`、
  `projects`、`stats`（经 HTTP 转发，payload 与错误码维持归档基线：
  `-32602` 参数、`-32001` 未找到、`-32000` 服务错误）；
- `rpc.discover`：OpenRPC 1.3.2 描述符，**本地响应，不依赖 daemon**；
- daemon 连接失败 → `-32000` + 「先运行 zedhub serve」提示；
- 新增业务能力不进入本方法表。

## WebSocket（127.0.0.1:8765，冻结声明）

> **该通道是一次性学习实现：本轮实现后冻结，不再新增任何方法或能力；
> 生产与自动化用途一律使用 HTTP API。**

```jsonc
// 请求（JSON 文本帧；binary 帧 → close 1003；单帧 ≤ 1 MiB；连接上限 8 → 1013）
{"id": 1, "method": "threads.list", "params": {"limit": 5}}
// 成功
{"id": 1, "ok": true, "data": [...], "elapsed_ms": 8}
// 失败（未知方法/写操作 → method_not_supported；非法 JSON → invalid_request）
{"id": null, "ok": false, "error": {"code": "invalid_params", "message": "..."}}
```

- 白名单仅 `threads.list` 与 `stats`；业务数据与 HTTP API 同源；
- `Origin`/`Host` 必须回环（带 Origin 且非回环 → close 1008）；
- 单请求 30 秒上限；断连释放请求资源；
- **不是 Agent 运行时桥接协议**：不处理 ACP/protobuf/CortexStep 等内部消息。

## CLI 信封

- 旧命令（threads/projects/stats）：`{"status":"ok","data":...,"count":...,
  "elapsed_ms":...}`（默认 JSON、`--table` 人读）；
- 新命令（sessions/stats effort/archive）：默认人读、`--json` 输出
  `{"ok":true,"data":...}` / `{"ok":false,"error":{...}}`；
- 退出码：0 成功（含空结果）、1 运行错误、2 用法错误。

## 写操作安全语义

- 默认 dry-run；显式 `--apply`（HTTP body `"apply": true`）才写库；
- 写前进程检查（opencode/zed 退出）→ 备份三件套到
  `%APPDATA%\language_projects\zedhub\backups\<operation_id>\` →
  分库短事务 → checkpoint → 只读复查；
- 跨库部分成功：`partial`/`unknown` 状态 + `operation_id` + 备份位置
  （journal 在 `%APPDATA%\language_projects\zedhub\operations\`），不虚报成功；
- 数据源边界：当前仅 OpenCode；未实现源返回 `source_not_supported`。
