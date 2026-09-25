# 设计文档（design.md）

> 上游基准：同目录 `requirements.md`（已含多 agent 扩展边界与 WebSocket 角色边界）。
> 本文锁定实现方案；与需求冲突处以需求为准。

## Overview

当前 `python_projects` 子仓已在最新提交中将旧 `zedhub` 与
`zed-opencode-sessions` 归档到父仓库 `.archived/`。本设计不是对现存工作树做增量修改，
而是**重新创建** `python_projects/zedhub`，以归档源码、归档项目文档和现有行为契约作为
迁移输入。

1. 新项目的数据访问层引入 agent 数据源注册表；Zed 索引作为独立的索引源，当前只实现
   OpenCode 会话源。未来 Pi/Claude Code/Codex/Antigravity 以新增 source 接入，不改公共语义。
2. 将 `.archived/projects/python_projects/zed-opencode-sessions` 的 OpenCode 内容查询、
   Markdown 导出、补登、归档导出/导入，以及 `.archived/projects/go_projects/ocstat` 的
   启动模型/effort 统计移植进新 zedhub 公共核心。
3. 新增最小只读 WebSocket 通道（仅 `threads.list` + `stats`），复用公共方法注册表；它是
   对外查询投影，不实现 Antigravity ACP / localharness 一类的内部 WebSocket 桥接。
4. 按归档项目的公开契约保留旧 CLI/RPC/MCP 行为；新增命令遵循仓库《CLI 工具开发标准》
   （默认人读、`--json` 稳定信封、`schema` 离线导出）。
5. `python_projects/zedagentstats` 已经具备 pi/antigravity/opencode 的统计采集器；本次
   不把它作为运行时依赖，也不把其未来 agent 数据源误称为新 zedhub 已实现能力，只吸收
   可复用的领域口径并为后续 source 接入保留边界。

技术栈锁定：Python 3.12、typer、pydantic v2、`mcp==2.2.0`、标准库 `sqlite3`、
`websockets>=15,<16`（仅 `ws` 子命令使用）。选择 `mcp==2.2.0` 是为了锁定
`MCPServer.tool(name=..., annotations=..., structured_output=...)` 的实际 API，避免
`tools/list` 与离线 schema 在不同 SDK 版本间漂移。构建/运行走 `uv`，新项目的 exe 壳仍可由
pythonlauncher 部署，本设计不包含打包壳改造。

由于目标项目当前已归档，下面标记为 `UPDATED` 的文件表示“从归档行为恢复并改造”；在
新的 `python_projects/zedhub` 工作树中它们实际都需要重新创建。归档目录只读作为迁移
参考，不建立运行时 import 关系。

## Context

现状（已从当前分支和归档源码确认）：

- 旧 `zedhub` 的方法注册表、Zed `core/`、CLI/RPC/MCP 和测试位于
  `.archived/projects/python_projects/zedhub/`；当前分支没有可直接修改的
  `python_projects/zedhub` 源码目录。
- 归档 `zedhub` 的公开契约包括 `threads.list/show`、`projects`、`stats`、JSON-RPC、MCP
  和 Zed WAL 快照读取；这些是新项目需要回归的兼容基线。
- 归档 `zed-opencode-sessions` 提供 `OpencodeRepo`、会话内容、Markdown 导出，以及
  `export_sessions.py`、`import_sessions.py`、`link_sessions.py`；其中旧脚本存在
  `%TEMP%` 备份、直接读取 OpenCode 数据库和 `SELECT *` 等本次必须修正的实现。
- 归档 `ocstat` 提供 event 时间线还原启动模型、配置档位合并、full/basic/broken 降级、
  watch 刷新和快照兜底；其 235/235 口径验证作为迁移时的行为基线。
- 当前仍在 `python_projects/zedagentstats` 的项目已经注册 pi、antigravity、opencode
  采集器并提供 token 统计；它是并行项目和参考实现，不作为新 zedhub 的运行时依赖。

动机：相关项目曾重复读取 Zed/OpenCode 及 agent 本地数据。新 zedhub 应恢复一个独立、
可安装的 Python 项目，以单一核心、多入口投影承接已确认的旧契约，并为未来 agent source
保留边界。

## Goals and Non-Goals

- Goals：
  - 从归档源码恢复一个可独立运行的 `python_projects/zedhub`，覆盖 Zed + OpenCode；
    `sessions.*`、`stats effort`、导出、补登、迁移全部落公共核心，多入口共用。
  - 公共领域模型区分「通用字段 / agent 专属字段 / 未支持状态」，且不依赖旧项目的
    Python 包。
  - WebSocket 最小只读骨架：回环监听、JSON 帧、双方法白名单、请求级快照，明确与
    Agent 内部 ACP/WebSocket 桥接隔离。
  - 写操作安全流水线：参数校验 → 进程检查 → 备份 → 分库事务 → checkpoint → 只读复查，
    对跨数据库部分成功保留可恢复证据。
- Non-Goals：
  - 不实现未来 agent 的实际数据源；不吸收 `zedagentstats` 的 pi/antigravity 运行时采集器。
  - 不做公网服务、鉴权、GUI；不做 MCP/RPC/WebSocket 写工具；不改已有 `zedhub rpc` 方法。
  - 不修改 Zed/OpenCode 上游 schema；不删任何会话数据；不保证跨库写入具备单事务原子性。

## Detailed Design

### 1. 数据源抽象与注册表

- `CREATED` `src/zedhub/core/sources/base.py`
    - **Purpose**：跨 agent 的源能力协议与注册表。
    - **Changes**：
      ```python
      class Availability(str, Enum):
          SUPPORTED = "supported"          # 本版本实现了该源
          NOT_IMPLEMENTED = "not_implemented"  # 规划中但未实现（Pi/claude/codex/agy）
          UNAVAILABLE = "unavailable"      # 已实现但本机数据源缺失/不可读

      class Capability(str, Enum):
          THREADS = "threads"; SESSIONS = "sessions"; CONTENT = "content"
          EFFORT = "effort"; EXPORT = "export"; LINK = "link"; IMPORT = "import"

      @dataclass
      class SourceInfo:
          source_id: str        # "zed" | "opencode" | ...
          display_name: str
          availability: Availability
          capabilities: list[Capability]
          note: str | None      # unavailable 原因等

      class AgentSource(Protocol):
          info: SourceInfo

          def list_sessions(self, request: SessionListRequest) -> list[Session]: ...
          def get_session(self, external_id: str) -> Session: ...
          def get_content(self, external_id: str) -> SessionContent: ...

      SOURCES: dict[str, AgentSource]  # 本版本仅注册 opencode
      ```
    - `ZedDb` 不伪装成 `AgentSource`：它是独立的 Zed 索引源，用于 thread 查询、关联
      session_id 和项目统计；OpenCode source 负责 agent session/message/part。
    - **校验/不变量**：`source_id` 全局唯一；未注册 id 一律映射到
      `source_not_supported` 错误（AC-13）；注册表只增不改已有条目语义；source 方法
      不向入口层暴露数据库连接、游标或 agent 专属表对象。
    - `SessionListRequest`、`Session`、`SessionContent` 在公共模型章节定义，source
      必须明确声明不支持的 capability，调用方不能通过缺省值伪造结果。
    - **Complexity**：Medium

- `CREATED` `src/zedhub/core/repo.py`：从归档基线恢复 `ZedDb` 只读层，保持其显式列查询
  和 schema 检查；新增 `src/zedhub/core/opencode_repo.py`：`OpencodeDb` 只读层，
  显式列字段查询（无 `SELECT *`）：
  - `list_sessions()` → `id, project_id, directory, title, version, agent, model,
    parent_id, time_created, time_updated, time_archived`
  - `get_session_content(session_id)` → session + `message(id, session_id,
    time_created, data)` + `part(id, message_id, session_id, time_created, data)`
  - `iter_first_assistant()` / `iter_model_events()`：供 analytics 使用（见 §4）
  - `detect_mode()`：三级探测，口径同 ocstat（session 必需列缺→`broken`；
    message/event 缺→`basic`；齐→`full`）
  - schema 不符抛 `SchemaError`（复用 `core/repo.py` 同名异常，提到 `core/errors.py`）。
- `CREATED` `src/zedhub/core/sources/opencode_source.py`：薄适配器，把 `OpencodeDb` 包装成
  `AgentSource`，声明当前 OpenCode capabilities。Zed 不创建对应的 agent source 包装，
  继续由 `ZedDb` + `ThreadService` 作为独立索引源提供 thread 和关联查询。
- **Complexity**：Medium

### 2. 领域模型（通用 vs agent 专属）

- `CREATED` `src/zedhub/core/model.py`：恢复归档基线的 `Thread` 等模型，并新增跨 source 的
  pydantic 模型：
  ```python
  class ModelRef(BaseModel):          # 通用：不暴露 agent 原始 JSON
      provider: str | None
      model_id: str | None
      variant: str | None              # 可选 effort/variant 通用投影

  class Session(BaseModel):           # 通用会话（agent 数据源侧）
      source_id: str                  # "opencode"，未来 "pi"/"codex"...
      external_id: str
      title: str
      directory: str | None
      agent: str | None
      model: ModelRef | None
      created_at: datetime | None     # UTC aware，序列化时转本地（同 CLI 契约）
      updated_at: datetime | None
      archived: bool
      zed_thread_id: str | None       # 关联；缺失=None，不伪造

  class Message(BaseModel):
      id: str; role: str; agent: str | None; model_id: str | None
      created_at: datetime | None
      parts: list[MessagePart]

  class MessagePart(BaseModel):
      id: str; type: str; text: str | None; created_at: datetime | None
  ```
  agent 专属字段不塞入 `ModelRef` 的开放 `raw` 字典；需要对外公开时由 source 自己提供
  带 source 命名空间、字段白名单和大小上限的扩展 DTO。当前 OpenCode 只返回上述通用字段，
  不把数据库原始 JSON 原样透出。
- 解析口径统一：blob→uuid hex、>6 位小数时间戳、`folder_paths` 换行分隔
  （归档 `zedhub/core/model.py` 已实现；`zed-opencode-sessions` 重复实现废弃，只取一套）。
- `CREATED` `src/zedhub/core/errors.py`：统一错误层级（现 `SchemaError`/
  `SnapshotError`/`ApiError`/`NotFoundError` 归口于此，原模块保留导入别名，兼容不破）：
  `code` 枚举（公共契约，各入口映射）：

  | code | 含义 | CLI 退出码 | RPC 映射 | WS 映射 |
  |---|---|---|---|---|
  | `invalid_params` | 参数错误 | 2 | -32602 | error.code |
  | `not_found` | 记录未找到 | 1 | -32001 | error.code |
  | `source_not_supported` | 数据源未实现 | 1 | -32001/-32601 | error.code |
  | `data_source_missing` | db 文件不存在 | 1 | -32000 | error.code |
  | `schema_incompatible` | 表/列缺失不可降级 | 1 | -32000 | error.code |
  | `snapshot_failed` | 快照复制失败 | 1 | -32000 | error.code |
  | `process_running` | 写前进程检查失败 | 1 | （写仅 CLI） | 拒绝 |
  | `write_failed` | 事务回滚 | 1 | — | 拒绝 |
  | `verify_failed` | 写后复查不一致（结果未知） | 1 | — | 拒绝 |
  | `method_not_supported` | WS 非白名单方法 | — | — | error.code |
  | `invalid_request` | WS 非 JSON/形状错 | — | — | error.code |

- **Complexity**：Low

### 3. 快照与读取策略

- `CREATED` `src/zedhub/core/snapshot.py`：
  - `open_snapshot(db, *, stem)` 按主文件名匹配主库、`-wal`、`-shm` 三件套，复制到
    `zedhub_data_dir()/snapshots/<uuid>`，退出时在 `finally` 中删除；快照目录只允许存放
    本次请求的临时副本。
  - Zed 始终通过快照读取，因为 Zed WAL 数据必须与主库一起复制，且现有契约已明确这条
    读库铁律。
  - OpenCode 默认先使用 `mode=ro` + `busy_timeout` 的只读连接，绝不使用写连接或
    `immutable=1`（后者可能忽略 WAL）；连接/读取失败时复制三件套后重试。这样避免每次
    访问 GB 级 OpenCode 库都复制完整文件，同时保留运行中数据库的安全兜底。
  - 无论直接只读连接还是快照连接，都由一次业务请求显式拥有并关闭；WebSocket 不跨请求
    复用 SQLite 连接。
- `CREATED` `src/zedhub/core/paths.py`：`zedhub_data_dir()` ——
  `%APPDATA%\language_projects\zedhub\`，无 `APPDATA` 回退
  `~/.language_projects/zedhub/`，`mkdir(parents=True, exist_ok=True)`。
  所有快照、备份、操作日志和恢复记录只写入该目录，不跟随外部数据库目录写入。
- OpenCode 默认路径探测：`OPENCODE_DATA` env → `~/.local/share/opencode/opencode.db`；
  Zed 默认：`LOCALAPPDATA\Zed\db\0-stable\db.sqlite`，支持 `ZED_DB_DIR`。
- **Complexity**：Medium

### 4. effort 分析（ocstat 移植）

- `CREATED` `src/zedhub/core/analytics.py`，纯函数可单测：
  - `resolve_startup(db: OpencodeDb) -> EffortReport`，算法照抄 ocstat 已验证口径：
    1. `session` 全量取 `id, model, version, time_created`；
    2. full 模式：扫 `message`（显式列，按 time_created），每会话首条
       `role=assistant && agent!=title && modelID!=empty` 的时间戳；
    3. 扫 `event`（`type in ('session.created.1','session.updated.1')`，按 rowid），
       解析 `data.info.model{id,providerID,variant}` 与 `info.time.updated`，构建每会话
       时间线，二分/线性取 ≤ 首条消息时刻的最后生效模型；无命中回退首事件模型；
    4. basic 模式：仅当前模型，`degraded=true` + note；broken：抛 `schema_incompatible`。
  - `merge_effort(cfg, provider, model, variant)`：variant 空/default 且配置写死
    `reasoningEffort`/`effort` → `"default→<eff>"`；配置读取
    `OPENCODE_CONFIG`（默认 `~/.config/opencode`）按
    `config.json → opencode.json → opencode.jsonc` 覆盖顺序，jsonc 解析失败即跳过
    （与 Go 版行为一致，不实现注释剥离器——记为已知近似）。
  - `EffortReport` 字段：`mode, note, db_path, db_size, db_mtime, using_snapshot,
    versions, cfg_merged, generated_at, groups[{provider, model, effort, sessions}],
    total, no_msg_count, startup_count`；排序：会话数降序 + provider/model 字典序，
    档位序 max>high>medium>low>default>缺失（`default→x` 按 x 参与排序）。
  - 快照兜底：只读打开失败 → 临时快照副本重试（ocstat `snapshotDB` 语义并入
    §3 统一快照，天然满足）。
- `watch`：CLI 层循环（见 §5），analytics 无状态、每次全量重算。
- **错误处理**：消息/事件 JSON 解析失败逐行跳过并计数（`skipped_rows`），不致命；
  配置缺失仅 `cfg_merged=false`。
- **Complexity**：Medium

### 5. CLI 命令面

新项目从 `.archived/projects/python_projects/zedhub/` 恢复既有命令
（`threads list/show`、`projects`、`stats`、`rpc`、`mcp`、`export*`），行为按 FR-9
回归，不从当前工作树复制运行时依赖。新增：

| 命令 | 默认输出 | 关键参数 | 说明 |
|---|---|---|---|
| `sessions list` | 人读表格 | `--source`(默认 opencode) `--project` `--archived no\|only\|all` `--limit` `--json` `--opencode-db` `--zed-db` | 列会话 + `zed_linked` 标记 |
| `sessions show` | 人读摘要 | `<session_id>` `--json` | session 元数据 |
| `sessions content` | 人读消息流 | `<session_id>` `--json` `--format text\|markdown` `--out` | 完整内容；markdown 移植 `export_markdown.py` |
| `sessions link` | 计划/结果人读 | `<project>` `--all` `--target` `--include-subagents` `--apply` `--json` | 补登（§8）；默认 dry-run |
| `stats effort` | 人读统计表(ocstat 版式) | `--json` `--watch` `-i 5s` `--opencode-db` | §4；`-i<=0` 报 invalid_params |
| `archive export` | 进度+摘要 | `<project>` `-o FILE` `--archived` `--json` | §8 |
| `archive inspect` | 人读 | `FILE` `--json` | 读 `_archive_meta` 计数 |
| `archive import` | 计划/结果人读 | `FILE` `--target DIR` `--apply` `--json` | §8 |
| `ws` | 启动行+stderr 诊断 | `--host 127.0.0.1` `--port 8765` `--db` `--opencode-db` | §7 |
| `schema` | JSON | `--channel all\|mcp\|cli\|ws` | §9 |

新命令 `--json` 遵循 CLI 标准信封；归档旧命令继续保留其既有输出作为兼容例外：

```json
{"ok": true,  "data": ..., "meta": {"count": 3, "elapsed_ms": 12}}
{"ok": false, "error": {"code": "not_found", "message": "..."}}
```

- 旧 `zedhub` 命令若历史上输出 `status/data/count/elapsed_ms`，按 FR-9 原样保留；新
  `sessions.*`、`stats effort`、`archive.*` 命令不复制该旧信封，避免继续扩大兼容负担。
- `--json` 时错误也走 stdout 单对象 + 非零退出码；诊断/进度仅在人读模式进 stdout、
  错误说明进 stderr。公共 `api.call()` 只返回业务 payload，不绑定任一入口信封。
- 写命令人读模式必须打印：计划数量、备份路径、实际写入数、复查结论。
- `--help/--version/schema` 不触碰任何数据库。
- `--host` 非回环值直接拒绝（exit 2）；`stats effort --watch` 用 ANSI 清屏，
  Ctrl+C 干净退出。
- **Complexity**：Medium

### 6. api 注册表与 MCP 扩展

- `UPDATED` `src/zedhub/api.py`：新增方法（payload 即 `--json` 的 `data`）：
  - `sessions.list`（`source?`, `project?`, `archived?`, `limit?`）
  - `sessions.show`（`session_id`）
  - `sessions.content`（`session_id`）
  - `stats.effort`（`degraded` 等标志在 payload 内，非错误）
  - 复用 `PARAM_SPECS/METHOD_SPECS` 机制；序列化统一本地时区（既有 `dump_*` 模式）。
  - 参数未注册 source → `source_not_supported`。
- `UPDATED` `src/zedhub/mcp_server.py`：新增 4 个只读 tool，显式使用
  `MCPServer.tool(name=..., annotations=ToolAnnotations(read_only_hint=True,
  destructive_hint=False, idempotent_hint=True), structured_output=True)` 注册三段式名称
  `zedhub.sessions.list` / `zedhub.sessions.show` / `zedhub.sessions.content` /
  `zedhub.stats.effort`；既有 `threads_list` 等存量名称不迁移。每个新 tool 返回 Pydantic
  对象根 DTO，由 `mcp==2.2.0` 推导准确 input/output schema；写操作不注册。
- `rpc.py` 逻辑按归档契约恢复但不扩展现有方法；既有 4 方法 payload 不变，新方法不要求
  自动增加 RPC 映射。
- **Complexity**：Low

### 7. WebSocket 通道（最小只读骨架）

- `CREATED` `src/zedhub/ws.py`，`websockets>=15,<16` asyncio server：
  - 绑定：默认 `127.0.0.1:8765`；启动时校验 host 为 `127.0.0.1`/`localhost`/`::1`，
    否则拒绝启动；无鉴权（NFR-7）；并发连接上限 8，超限 close code 1013。
  - **Origin/Host 防护**：握手请求头若带 `Origin` 且其 host 不为
    `127.0.0.1|localhost|::1` → close 1008（挡浏览器跨站 WebSocket 探测）；
    `Host` 头同样校验。非浏览器客户端不受影响。
  - 帧协议（JSON 文本帧，UTF-8；binary 帧 close 1003；单帧 ≤ 1 MiB）：
    ```jsonc
    // 请求
    {"id": 1, "method": "threads.list", "params": {"agent": "opencode", "limit": 5}}
    // 成功响应
    {"id": 1, "ok": true, "data": [...], "elapsed_ms": 8}
    // 失败响应
    {"id": 1, "ok": false, "error": {"code": "invalid_params", "message": "..."}}
    ```
    - `id` 允许 number/string；缺省或非法时响应 `id: null`。
    - 白名单仅 `{"threads.list", "stats"}`，参数校验直接走 `api.call()`
      （与 CLI/RPC/MCP 同一注册表，AC-9/AC-15）。
    - 非白名单方法 → `method_not_supported`（message 内附已支持列表）；
      写类操作名同样返回此错误，绝不触达写入代码（AC-16）。
    - 非法 JSON → `invalid_request`。
  - **并发/资源**：每连接内请求串行处理（一条消息一个响应）；同步的
    `open_snapshot`、SQLite 查询和 `api.call` 放入受限线程池，不得阻塞事件循环。每个请求
    独立拥有快照/连接并在 `finally` 释放，单请求设置 30 秒上限。连接关闭时取消等待中的
    asyncio task；由于同步 SQLite 调用无法被线程安全强杀，线程内操作必须依靠数据库超时
    和 `finally` 完成清理，服务端不承诺瞬时中断底层系统调用。线程池有界且服务关闭时等待
    其任务结束，避免无界后台线程和遗留快照（NFR-7/AC-15）。
  - **扩展预留**：信封判别规则写入协议文档——含 `id+ok` = 响应；未来服务器主动推送
    用 `{"event": "...", "data": ...}`（本版本不发送）；未知字段接收方忽略。
  - 角色边界：本通道是查询投影，不桥接任何 agent 引擎内部协议（需求 NFR-7 末段）。
- **错误处理**：`SnapshotError/SchemaError` → 对应 code 的失败响应，连接保持；
  未捕获异常 → `internal_error` 响应 + stderr 记录 traceback，连接保持。
- **Complexity**：Medium

### 8. 写操作：link / archive（导出、导入）

公共流水线（全部在 `core/writes.py` `CREATED`，CLI 独占调用）：

```
参数校验 → 进程检查（tasklist 匹配 opencode|zed，Windows-only；非 win 平台跳过并 note）
→ 备份三件套到 zedhub_data_dir()/backups/<yyyyMMdd_HHmmss>_<db文件名>/
→ 事务写入 → commit → 每库 PRAGMA wal_checkpoint(TRUNCATE) → 重开只读复查 → 报告
```

- **进程检查仅在 `--apply` 时强制**；dry-run 允许进程运行（只读快照安全）。
- **link**（`core/linking.py` `CREATED`，移植 `link_sessions.py`）：
  - OpenCode 快照读 session 列表；目录子串匹配 + `--all/--target` 消歧（逻辑照搬）；
  - 复用原 `session_id`、`uuid4().bytes` 作 thread_id、毫秒→Zed UTC ISO(9 位) 转换；
  - 幂等：已存在 session_id 跳过；写入单事务；复查插入集合与快照重读比对。
- **archive export**（`core/archive.py` `CREATED`，移植 `export_sessions.py`）：
  - 归档 schema = 原 5 表结构（**改为显式列**，禁 `SELECT *`）；
  - `_archive_meta` 固定键：`schema_version=1, source_agent="opencode",
    export_time, source_project, thread_count, session_count, message_count,
    part_count, include_archived`；
  - 输出到用户指定 `-o`（自产数据目录约束仅针对项目内部数据，导出工件由用户指定，
    与现状一致）。
- **archive import**（`core/migration.py` `CREATED`，移植 `import_sessions.py`）：
  - `schema_version` 与 `source_agent` 不识别 → 拒绝（`schema_incompatible`，
    不猜测旧/新格式）；
  - **跨库一致性边界**：不承诺 Zed 与 OpenCode 两个 WAL 数据库的单事务原子性，也不使用
    `ATTACH` 制造“整体回滚”的假象。先完成两库 schema/进程/备份预检，再分别执行短事务：
    先写 OpenCode 并提交，再写 Zed 并提交，最后分别复查。任一库提交后另一库失败时，
    保留操作清单、ID 映射、备份和 `partial/unknown` 状态，禁止报告成功；恢复由备份和
    后续人工/专用恢复动作完成。操作 journal 状态固定为 `planned`、`opencode_committed`、
    `zed_committed`、`verified`、`partial`、`unknown`，失败输出必须带 `operation_id`、
    备份目录和已提交阶段；本期不自动回滚已提交数据库，避免再次覆盖用户数据。这样明确
    覆盖数据库级 WAL 和跨文件 crash 的不可原子边界。Zed 表结构含
    `main_worktree_paths*`、`remote_connection` 列时按当前 schema 显式列出；
  - ID 重生成（ses_/msg_/prt_ base64 22 字符 + uuid thread_id）与
    `get_or_create_project`（显式列）逻辑照搬；目标目录必须已存在；
  - 每个数据库提交后，在确认写连接关闭的前提下分别开新连接执行
    `PRAGMA wal_checkpoint(TRUNCATE)`；checkpoint 失败记录诊断，不把它伪装成成功；
  - 复查：只读连接按目标 directory 计数 thread/session，少于计划 →
    `verify_failed`（明确标注“可能部分状态未知，请查备份”）；跨库复查不完整时同样返回
    `partial/unknown`，并保留操作记录。
- 备份目录不可写 → 写入前终止（`write_failed` 前置变体 `data_dir_error`）。
- **Complexity**：High（import 双库事务与列假设）

### 9. schema 导出

- `CREATED` `src/zedhub/schema_export.py`：
  - MCP tools：与 `mcp_server.build_server()` 实际注册同源（从注册表读取描述与
    input schema，不手抄）；通过内存 session 完整走 `tools/list` 并翻页；
  - 目录对象：`{"name":"zedhub","version":...,"interface":"mcp","tools":[...]}`；
  - `--channel ws|rpc|cli` 追加 `{"channel":..., "methods":[...]}` 段；默认 `all`
    输出 `{"name","version","channels":{"mcp":{...},"ws":{...},"rpc":{...},"cli":{...}}}`；
  - `ws` 段即 §7 白名单 + 帧协议描述；`cli` 段列既有+新命令的输入输出契约摘要；
  - 数据库缺失也能完整输出（纯元数据路径）。
- **Complexity**：Low

### 10. 数据目录与旧脚本处置

- 快照、备份、操作记录和（未来）日志统一写入
  `zedhub_data_dir()` 的 `snapshots/`、`backups/`、`operations/` 子目录；写前
  `mkdir(parents=True, exist_ok=True)`。
- 快照目录内文件在请求退出前删除；跨库写操作的 operation journal 在验证完成后保留，
  只记录恢复所需的操作状态、ID 映射和备份位置，不保存会话正文副本。
- 用户通过 `-o` 指定的归档文件是显式外部输出，不跟随内部数据目录；项目内部自产数据
  不因读取外部数据库而写回 Zed/OpenCode 或 agent home。
- `.archived/projects/python_projects/zed-opencode-sessions`、
  `.archived/projects/go_projects/ocstat` 和 `python_projects/zedagentstats` 本次不改动；
  新核心不 import、不子进程调用它们，只读取已确认的行为和算法作为迁移参考。
- `CREATED` `python_projects/zedhub/pyproject.toml`：恢复 `zedhub` 包、CLI entry point、
  Python 3.12 约束和已锁定依赖；`uv.lock` 随项目依赖生成，不手写。
- `CREATED` `python_projects/zedhub/README.md`：记录 CLI、`--json`、MCP、兼容 RPC、
  WebSocket、本地数据源路径、写操作安全边界和迁移状态；不在新项目目录创建额外 docs。

### 11. 可测性与验证边界

- `CREATED` `python_projects/zedhub/tests/`：使用临时目录构造最小 Zed/OpenCode SQLite
  fixture，覆盖成功、空结果、缺表/缺列、坏 JSON、未找到、降级和路径匹配；测试不得读取
  用户真实数据库，也不得把业务数据库写入项目根目录。
- 公共模型、时间/路径解析、effort 时间线、参数校验、错误映射和归档 ID 映射使用单元测试。
- CLI 使用子进程测试 `--help`、`--version`、新命令人读/`--json`、dry-run 和退出码；
  旧兼容命令保留归档基线测试。
- WebSocket 使用内存/临时 fixture 和真实 `zedhub ws` 子进程各验证一次：连接、两个白名单
  方法、非法 JSON、binary 帧、未知方法、超限、断连清理；不把只调用 `tools/list` 当作
  MCP 业务验收替代品。
- 写操作只在测试专属临时数据库执行，并在测试结束后关闭连接、删除快照/备份/操作记录；
  真实用户数据库只做显式的人工冒烟，不纳入自动测试。
- 真实验证命令锁定为：`uv sync`、`uv run pytest tests -q`、`uv run zedhub --help`、
  `uv run zedhub schema`；设计阶段只登记命令，执行阶段按用户指令运行。

### Module Collaboration and Data Flow

```
                 ┌─ cli.py (typer)          人读/--json 渲染, 退出码映射
  使用者 ────────┼─ rpc.py  (冻结兼容) ─┐
                 ├─ mcp_server.py ──────┼─→ api.py (方法注册表/参数校验/序列化)
                 └─ ws.py (白名单) ─────┘        │
                                                  ▼
                                     core/service.py + sources/  (查询/聚合)
                                                  │
                              ZedDb 索引源 + OpencodeSource│AgentSource 注册表
                                                  ▼
                              core/snapshot.open_snapshot(三件套 → data_dir/snapshots)
                                                  ▼
                                   Zed db.sqlite / opencode.db (只读)

  写路径（仅 CLI --apply）:
  cli.py → core/linking|archive|migration → core/writes(进程检查/备份/分库事务/checkpoint/复查)
        → 分别写入目标库（进程已退出前提；跨库部分失败由 operation journal + 备份恢复）
  analytics.py ← OpencodeDb 只读 + ~/.config/opencode 配置合并（读路径）
```

- 依赖方向：入口 → api → service/sources → core；core 不 import 入口；`websockets`
  仅 `ws.py` 引用。
- 并发模型：CLI/RPC 进程内单线程串行；MCP 与 WS 为 asyncio——WS 每请求开独立
  快照连接，不共享 sqlite 句柄（快照本身是文件副本，天然隔离）。
- 组装顺序：`ws`/`mcp`/`rpc` 启动只建注册表与 server，数据库访问惰性到每次请求。

### Acceptance Criteria Mapping

| AC | 设计组件 |
|---|---|
| AC-1 | §1/§2/§5/§6 sessions 系列 + stats effort 全在 zedhub 核心 |
| AC-2 | §5 既有命令零改动；§2 保留 `repo/service` 行为 |
| AC-3 | §2 `Session.zed_thread_id` 关联标记；§5 `sessions list --project` 用 Zed 索引 join，缺失=None |
| AC-4 | §4 启动模型算法 + `mode/degraded` 标志 |
| AC-5 | §4 `merge_effort`、`cfg_merged`、解析失败跳过 |
| AC-6 | §8 流水线：dry-run 默认、apply 前置检查、备份 |
| AC-7 | §8 checkpoint + 只读复查 + `verify_failed` |
| AC-8 | §8 archive export/import + `schema_version` |
| AC-9 | §6/§7 同一 `api.call`；§5 信封 data=payload |
| AC-10 | §9 schema 离线、同源、含 ws 段 |
| AC-11 | §1/§4 `detect_mode` 三级 + `schema_incompatible` |
| AC-12 | §10 不 import 不子进程调用旧项目 |
| AC-13 | §1/§2 `NOT_IMPLEMENTED` + `source_not_supported` |
| AC-14 | §1/§2 `source_id` 标注 + source 命名空间扩展 DTO |
| AC-15 | §7 白名单双方法 + 请求级快照 + 断连清理 |
| AC-16 | §7 白名单外 `method_not_supported`，写代码不可达 |
| AC-17 | §1 source/agent 边界 + §7 WebSocket 白名单与内部协议隔离 |

## Design Review Notes

### 自审发现与处理

以下按零上下文、故障破坏和安全边界重新检查设计；所有 HIGH/MEDIUM 发现均已修复：

1. **HIGH — 目标项目已不在当前工作树**：原稿假设可以在现有 `zedhub` 上增量修改，
   但当前分支已将其归档。已改为重新创建 `python_projects/zedhub`，明确归档源码只作
   迁移输入，且不建立运行时依赖。
2. **HIGH — 跨库单事务不可作为可靠承诺**：原稿曾计划用 `ATTACH` 实现 Zed/OpenCode
   整体回滚。已改为两库独立短事务、operation journal、备份和 `partial/unknown` 状态，
   不伪造原子性。
3. **HIGH — WebSocket 同步 SQLite 会阻塞事件循环**：已改为有界线程池、单请求 30 秒上限、
   请求级资源所有权和明确的取消限制。
4. **MEDIUM — Zed 索引与 agent source 概念混淆**：已明确 `ZedDb` 是独立索引源，只有
   OpenCode 注册为当前 `AgentSource`，避免未来 agent source 被迫模拟 Zed 表结构。
5. **MEDIUM — 新 CLI 与旧 JSON 信封边界不清**：已明确旧命令保留 `status` 兼容信封，
   新命令采用 CLI 标准的 `ok/data/error` 信封，公共核心不绑定入口信封。
6. **MEDIUM — `ModelRef.raw` 可能原样泄露 agent JSON**：已移除开放 raw 字段，当前只返回
   通用模型字段；未来专属扩展必须使用 source 命名空间、白名单和大小上限。

### 已验证假设

- 旧 `zedhub`、`zed-opencode-sessions`、`ocstat` 的源码和公开行为均可从当前仓库归档路径
  读取；`zedagentstats` 是独立的现存多 agent 统计项目。
- 旧 `zedhub` 的 RPC/MCP 方法注册表和 Zed 快照边界已在归档源码中确认。
- `mcp==2.2.0` 的 `MCPServer.tool` 支持显式名称、`ToolAnnotations` 和
  `structured_output`；新项目锁定该版本，避免按未锁定 SDK 猜测 API。
- 项目自产快照、备份和操作记录路径可以统一由 `APPDATA` 项目目录管理；外部数据库仍只读
  或在明确 `--apply` 且进程退出后写入。

### 未作为实现假设的事项

- Zed/OpenCode 上游未来 schema 不稳定；实现必须在运行时探测并按设计降级或拒绝。
- 旧 `zedhub rpc` 是否存在仓库外调用方无法从本仓确认，因此保留既有方法而不扩展新方法。
- WebSocket 不承诺底层同步 SQLite 调用可被强制中断，只承诺有界等待、最终清理和不泄漏资源。

**机械判定：HIGH=0，MEDIUM=0，NIT 仅为运行时 schema 演进和外部调用方未知的已登记风险；
设计评审通过。**
