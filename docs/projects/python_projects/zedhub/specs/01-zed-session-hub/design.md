# 设计文档（design.md）

> 上游基准：同目录 `requirements.md`（已含 daemon 架构、多 agent 扩展边界与本地通道
> 安全边界）。
> 本文锁定实现方案；与需求冲突处以需求为准。
> 标准依据：《CLI 工具开发标准 v2（daemon 架构）》（运行机制）+ v1《CLI 工具开发标准》
> （JSON 包络、业务错误、`--schema` 导出、MCP 协议核对、验收矩阵）。

## Overview

当前 `python_projects` 子仓已在最新提交中将旧 `zedhub` 与
`zed-opencode-sessions` 归档到父仓库 `.archived/`。本设计不是对现存工作树做增量修改，
而是**重新创建** `python_projects/zedhub`，以归档源码、归档项目文档和现有行为契约作为
迁移输入。

1. **daemon 架构（v2 Python 试点）**：`zedhub serve` 是唯一业务进程；Service 层只存在于
   daemon，对 `127.0.0.1:8766` 提供 HTTP+JSON API（唯一契约）；CLI、MCP 桥、兼容 RPC
   全是 daemon 的薄客户端（参数解析 → HTTP → 渲染）；进度用 SSE。
2. 新项目的数据访问层引入 agent 数据源注册表；Zed 索引作为独立的索引源，当前只实现
   OpenCode 会话源。未来 Pi/Claude Code/Codex/Antigravity 以新增 source 接入，不改公共语义。
3. 将 `.archived/projects/python_projects/zed-opencode-sessions` 的 OpenCode 内容查询、
   Markdown 导出、补登、归档导出/导入，以及 `.archived/projects/go_projects/ocstat` 的
   启动模型/effort 统计移植进 Service 层。
4. WebSocket 是**一次性学习实现**的只读通道（仅 `threads.list` + `stats`），与 HTTP API
   并存于 daemon 进程；实现完成后冻结，README 点明生产用途一律走 HTTP API。它不是
   Antigravity ACP / localharness 一类的内部 WebSocket 桥接。
5. 按归档项目的公开契约保留旧 CLI/RPC/MCP 行为；已知行为变化（查询与写命令依赖
   daemon）登记迁移说明。新增命令遵循 v1 标准（默认人读、`--json` 稳定信封、`schema`
   离线导出）。
6. `python_projects/zedagentstats` 已经具备 pi/antigravity/opencode 的统计采集器；本次
   不把它作为运行时依赖，只吸收可复用的领域口径并为后续 source 接入保留边界。

技术栈锁定：Python 3.12、typer、pydantic v2、`mcp==2.2.0`（MCP 桥）、标准库 `sqlite3`、
`websockets>=15,<16`（仅 WS 学习通道）、`starlette>=0.40,<1` + `uvicorn>=0.30,<1`
（daemon HTTP）。选择 `mcp==2.2.0` 是为了锁定
`MCPServer.tool(name=..., annotations=..., structured_output=...)` 的实际 API，避免
`tools/list` 与离线 schema 在不同 SDK 版本间漂移。构建后端 hatchling + hatch-vcs
（版本由 git tag 推导，支撑生产/开发构建判定）。构建/运行走 `uv`。

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
- v2 标准定位为探索性试点（未取代 v1）：daemon 架构按 v2 执行，契约细节按 v1 执行；
  本项目是 v2 在 Python 侧的首个试点。

动机：相关项目曾重复读取 Zed/OpenCode 及 agent 本地数据。新 zedhub 应恢复一个独立、
可安装的 Python 项目，以单一 daemon、多薄壳架构承接已确认的旧契约，并为未来 agent
source 保留边界。

## Goals and Non-Goals

- Goals：
  - 从归档源码恢复一个可独立运行的 `python_projects/zedhub`，覆盖 Zed + OpenCode；
    `sessions.*`、`stats effort`、导出、补登、迁移全部落 Service 层，HTTP API 唯一契约。
  - daemon 全套生命周期机制：前台 `serve`、地址文件、发现优先级、生产构建自动拉起、
    buildID 握手、空闲 30 分钟退出、拉起互斥（FR-11 / AC-19）。
  - 公共领域模型区分「通用字段 / agent 专属字段 / 未支持状态」，且不依赖旧项目的
    Python 包。
  - WebSocket 最小只读学习骨架：回环监听、JSON 帧、双方法白名单、请求级快照，与
    Agent 内部 ACP/WebSocket 桥接隔离；实现后冻结。
  - 写操作安全流水线：参数校验 → 进程检查 → 备份 → 分库事务 → checkpoint → 只读复查，
    对跨数据库部分成功保留可恢复证据；apply 执行经 SSE 输出阶段进度。
- Non-Goals：
  - 不实现未来 agent 的实际数据源；不吸收 `zedagentstats` 的 pi/antigravity 运行时采集器。
  - 不做公网服务、鉴权、GUI、gRPC；不做通用日志流 SSE。
  - WebSocket 本轮实现后不再新增任何方法或能力（冻结）。
  - 不做 MCP/RPC/WebSocket 写工具；不改已有 `zedhub rpc` 方法。
  - 不修改 Zed/OpenCode 上游 schema；不删任何会话数据；不保证跨库写入具备单事务原子性。

## Detailed Design

### 1. 数据源抽象与注册表（Service 层）

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

  | code | 含义 | CLI 退出码 | HTTP | RPC 映射 | WS 映射 |
  |---|---|---|---|---|---|
  | `invalid_params` | 参数错误 | 2 | 400 | -32602 | error.code |
  | `not_found` | 记录未找到 | 1 | 404 | -32001 | error.code |
  | `source_not_supported` | 数据源未实现 | 1 | 400 | -32001/-32601 | error.code |
  | `data_source_missing` | db 文件不存在 | 1 | 503 | -32000 | error.code |
  | `schema_incompatible` | 表/列缺失不可降级 | 1 | 500 | -32000 | error.code |
  | `snapshot_failed` | 快照复制失败 | 1 | 500 | -32000 | error.code |
  | `process_running` | 写前进程检查失败 | 1 | 409 | （写仅 CLI） | 拒绝 |
  | `write_failed` | 事务回滚 | 1 | 500 | — | 拒绝 |
  | `verify_failed` | 写后复查不一致（结果未知） | 1 | 500 | — | 拒绝 |
  | `data_dir_error` | 数据目录/备份不可写 | 1 | 500 | — | 拒绝 |
  | `method_not_supported` | 非白名单方法/未知端点 | 2 | 404 | -32601 | error.code |
  | `invalid_request` | 非 JSON/形状错 | 2 | 400 | -32600 | error.code |
  | `handshake_mismatch` | buildID 握手失败 | 1 | 409 | — | — |
  | `daemon_unreachable` | daemon 未运行/连接失败 | 1 | — | -32000 | — |
  | `internal_error` | 未捕获异常 | 1 | 500 | -32603 | error.code |

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
  - 无论直接只读连接还是快照连接，都由一次业务请求显式拥有并关闭；daemon 不跨请求
    复用 SQLite 连接，不常驻持有任何数据库句柄。
- `CREATED` `src/zedhub/core/paths.py`：`zedhub_data_dir()` ——
  `%APPDATA%\language_projects\zedhub\`，无 `APPDATA` 回退
  `~/.language_projects/zedhub/`，`mkdir(parents=True, exist_ok=True)`。
  子目录：`snapshots/`、`backups/`、`operations/`、`runtime/`（地址文件与 daemon 日志）。
  所有快照、备份、操作日志和恢复记录只写入该目录，不跟随外部数据库目录写入。
- OpenCode 默认路径探测：`OPENCODE_DATA` env → `~/.local/share/opencode/opencode.db`；
  Zed 默认：`LOCALAPPDATA\Zed\db\0-stable\db.sqlite`，支持 `ZED_DB_DIR`。
- **Complexity**：Medium

### 4. effort 分析（ocstat 移植，Service 层）

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
- `watch`：CLI 层循环（见 §8），analytics 无状态、每次全量重算。
- **错误处理**：消息/事件 JSON 解析失败逐行跳过并计数（`skipped_rows`），不致命；
  配置缺失仅 `cfg_merged=false`。
- **Complexity**：Medium

### 5. daemon 进程与 HTTP API（唯一契约）

- `CREATED` `src/zedhub/http_api.py`：Starlette 应用 + 路由表；uvicorn 承载。
  - **路由表数据驱动**：所有端点在一张 `ROUTES` 声明表上定义（method、path、业务方法、
    参数 schema、是否 SSE 能力），路由注册与 `schema` 导出迭代同一张表（AC-10 同源）。
  - 端点（全部挂 `/api/v1`）：

    | Method | Path | 业务能力 | 形态 |
    |---|---|---|---|
    | GET | `/health` | 存活 + buildID 握手 | JSON |
    | GET | `/threads` | threads.list | JSON |
    | GET | `/threads/{id}` | threads.show | JSON |
    | GET | `/projects` | projects | JSON |
    | GET | `/stats` | stats | JSON |
    | GET | `/sources` | source 注册表状态 | JSON |
    | GET | `/sessions` | sessions.list | JSON |
    | GET | `/sessions/{id}` | sessions.show | JSON |
    | GET | `/sessions/{id}/content` | sessions.content | JSON |
    | GET | `/stats/effort` | stats.effort | JSON |
    | POST | `/sessions/link` | 补登 | dry-run JSON / apply SSE |
    | POST | `/archive/export` | 归档导出 | JSON / SSE |
    | POST | `/archive/inspect` | 归档检查 | JSON |
    | POST | `/archive/import` | 归档导入 | dry-run JSON / apply SSE |

    业务方法直接调 `api.call()` 注册表（与 WS 共源，AC-9/AC-15）。
  - **JSON 包络**（沿用 v1 规则）：
    ```json
    {"ok": true, "data": ..., "meta": {"count": 3, "elapsed_ms": 12}}
    {"ok": false, "error": {"code": "not_found", "message": "..."}}
    ```
    HTTP 状态码按 §2 错误表映射（辅助定位，`error.code` 是唯一稳定契约）。
  - **安全边界**：只绑定回环地址；每个请求校验 `Host` 头为
    `127.0.0.1|localhost|::1`，否则 403（防 DNS rebinding）；无鉴权（NFR-7）。
  - **并发模型**：uvicorn asyncio；同步 Service 调用（SQLite/快照）经
    `asyncio.to_thread` 进入有界线程池（默认 8 线程，与 WS 共用）；**写流水线全局
    互斥**（daemon 内单一写者信号量），读请求不受写互斥阻塞。daemon 不跨请求持有
    SQLite 连接。
  - **SSE**（v1 包络 + `text/event-stream`）：写类端点在 `Accept: text/event-stream`
    时流式返回阶段事件，事件类型：
    ```jsonc
    event: stage\ndata: {"stage": "backup", "detail": "...", "pct": 40}
    event: result\ndata: {完整结果对象（同同步模式 data）}
    event: error\ndata: {"code": "...", "message": "..."}
    ```
    未带 SSE Accept 时同步阻塞返回完整 JSON（小任务可用；CLI 的 apply 一律走 SSE）。
    SSE 客户端断开**不中止**已开始的写流水线：daemon 将流水线执行到 AC-6/AC-7 的
    可验证状态，结果落 operation journal，进度事件丢弃（NFR-7）。
  - **buildID 握手**：`GET /health` 响应 `{build_id, version, started_at}`；所有业务
    请求可带 `X-Zedhub-Build` 头，daemon 校验与自身 `build_id` 相等，不等返回 409 +
    `handshake_mismatch`，message 形如「daemon 是旧构建 dev-a1b2c3，请重启后重试」。
  - **优雅关闭**：SIGINT/TERM → 停止接受新连接 → 等待在途请求与线程池任务结束 →
    关 WS 监听 → 删地址文件 → 退出。
- **Complexity**：High（SSE 生命周期、写互斥与关闭次序）

### 6. daemon 生命周期与客户端发现

- `CREATED` `src/zedhub/lifecycle.py`（daemon 侧）+ `src/zedhub/client.py`（壳侧共享
  HTTP client）：
  - **地址文件** `zedhub_data_dir()/runtime/daemon.json`：
    `{host, port, pid, build_id, started_at, auto_spawned}`；启动时原子写
    （临时文件 + `os.replace`），退出时删除。`runtime/daemon.lock` 用于启动互斥。
    存活判定以「端口 TCP 可连 + /health 握手通过」为准，pid 仅作诊断展示（Windows 下
    不用信号探活，避免误杀语义）。
  - **发现优先级**（client 侧，v2 §2.2）：`--host` 参数 → `ZEDHUB_HOST` 环境变量 →
    地址文件 → 内置默认 `127.0.0.1:8766`。
  - **生产/开发构建判定**：hatch-vcs 由 git tag 推导版本；PEP 440 解析版本含 `.dev`
    或 local `+` 段 → 开发构建；干净发布号（如 `0.3.1`）→ 生产构建。
    开发态（`uv run` / editable）天然是 `X.Y.devN+g<hash>`。
  - **buildID**：生产 = `v{version}`；开发 = `dev-{源码指纹}`（对
    `src/zedhub/**/*.py` 的 size+mtime 聚合哈希，进程内只算一次）——单边重启后指纹
    不等，握手当场报错，弥补 Python 无链接期注入的弱探测。
  - **自动拉起（仅生产构建）**：连接失败且**未显式指定地址**（无 `--host`/`ZEDHUB_HOST`、
    地址文件缺失或失效）时，以 `sys.executable -m zedhub serve --auto-spawned` 拉起，
    Windows `creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`（脱离父子
    关系）；stderr 重定向 `runtime/daemon.log`（覆盖式，README 说明）；拉起后轮询
    地址文件 + 握手（默认 10 秒超时）。生产构建显式指定地址连不上 → 报错不拉起；
    开发构建一律报错并提示「先运行 `zedhub serve`」。
  - **拉起互斥**：拉起前二次探测（地址文件存活或默认端口可连即放弃拉起改为连接）；
    daemon 启动时持锁写地址文件，端口被占用即启动失败退出。
  - **空闲退出**：`--auto-spawned` 启动的 daemon 启用空闲计时（默认 30 分钟）：仅在
    「在途请求数 = 0」期间累计，任一请求结束即重置；触发后走优雅关闭并删地址文件；
    长任务执行中（在途 > 0）不触发。前台 `serve` 不设空闲退出。
  - `src/zedhub/__main__.py`：支持 `python -m zedhub`（自动拉起的 spawn 入口）。
- **Complexity**：High（detach、互斥与空闲退出的边界条件）

### 7. 公共契约模块（壳与 daemon 共享的纯定义）

- `CREATED` `src/zedhub/contract.py`：**纯协议定义，零业务依赖**（不 import sqlite/
  Service/入口）：
  - HTTP 端点声明的参数/响应 pydantic 模型；
  - MCP 工具元数据（名称、描述、输入模型、输出 DTO 类）——桥注册与 `schema` 导出同源；
  - 兼容 RPC 方法表（4 旧方法 → HTTP 端点映射 + rpc.discover 静态文档）；
  - WS 帧信封模型与白名单。
  daemon、MCP 桥、rpc 壳、`schema` 命令都 import 它；它是「契约」而非业务逻辑，不违反
  NFR-3 的壳内禁令。
- **Complexity**：Low

### 8. CLI 薄壳

新项目从 `.archived/projects/python_projects/zedhub/` 恢复既有命令
（`threads list/show`、`projects`、`stats`、`rpc`、`mcp`、`export*`），行为按 FR-9 回归。
所有查询/写命令 = 参数解析 → `client.call()` HTTP → 渲染。新增命令同构：

| 命令 | 默认输出 | 关键参数 | 说明 |
|---|---|---|---|
| `serve` | 前台日志 | `--host 127.0.0.1` `--port 8766` `--db` `--opencode-db` `--auto-spawned`(内部) | §5/§6 daemon |
| `sessions list` | 人读表格 | `--source`(默认 opencode) `--project` `--archived no\|only\|all` `--limit` `--json` `--host` | 经 HTTP；含 `zed_linked` 标记 |
| `sessions show` | 人读摘要 | `<session_id>` `--json` `--host` | session 元数据 |
| `sessions content` | 人读消息流 | `<session_id>` `--json` `--format text\|markdown` `--out` `--host` | 完整内容；markdown 移植 `export_markdown.py` |
| `sessions link` | 进度+计划/结果 | `<project>` `--all` `--target` `--include-subagents` `--apply` `--json` `--host` | 补登（§10）；apply 走 SSE 实时进度 |
| `stats effort` | 人读统计表(ocstat 版式) | `--json` `--watch` `-i 5s` `--host` | §4；`-i<=0` 报 invalid_params；watch = CLI 循环调 HTTP |
| `archive export` | 进度+摘要 | `<project>` `-o FILE` `--archived` `--json` `--host` | §10；SSE 进度可选 |
| `archive inspect` | 人读 | `FILE` `--json` `--host` | 读 `_archive_meta` 计数 |
| `archive import` | 进度+计划/结果 | `FILE` `--target DIR` `--apply` `--json` `--host` | §10；apply 走 SSE |
| `schema` | JSON | `--channel all\|http\|mcp\|ws\|rpc\|cli` | §12；**纯本地，不连 daemon** |

- 新命令 `--json` 遵循 v1 标准信封；归档旧命令继续保留其既有输出作为兼容例外
  （旧 `status/data/count/elapsed_ms` 信封原样保留，FR-9）。
- `--json` 时错误也走 stdout 单对象 + 非零退出码；诊断/进度仅在人读模式进 stdout、
  错误说明进 stderr。
- 写命令人读模式必须打印：计划数量、备份路径、实际写入数、复查结论；apply 执行时实时
  渲染 SSE `stage` 事件（单行刷新），结束打印最终摘要。
- `--help`、`--version`、`schema`、补全脚本生成：纯本地命令，不触发 daemon、不触碰
  数据库（v2 §1.1 硬规则）。
- `--host`（查询/写命令）：显式 daemon 地址，格式 `host:port`；非回环值直接拒绝
  （exit 2）。
- daemon 连接失败：生产构建自动拉起（§6）；开发构建报 `daemon_unreachable` 并提示
  「先运行 `zedhub serve`」。
- **Complexity**：Medium

### 9. MCP 桥与兼容 RPC 薄壳

- `UPDATED` `src/zedhub/mcp_bridge.py`（原 `mcp_server.py` 更名定位）：stdio MCP server
  （`mcp==2.2.0`），**工具实现全部经 HTTP 调 daemon**，桥不直连数据库：
  - 保留存量名称 `threads_list` 等（FR-9）+ 新增三段式只读工具
    `zedhub.sessions.list` / `zedhub.sessions.show` / `zedhub.sessions.content` /
    `zedhub.stats.effort`，显式
    `MCPServer.tool(name=..., annotations=ToolAnnotations(read_only_hint=True,
    destructive_hint=False, idempotent_hint=True), structured_output=True)`；
    工具元数据定义在 `contract.py`，桥注册与 `schema` 同源。
  - 桥启动时先与 daemon 完成握手（失败即启动报错，提示先 `zedhub serve`）；
    HTTP 错误码 → MCP 错误；写操作不注册。
- `UPDATED` `src/zedhub/rpc.py`：stdin JSON-RPC → HTTP 薄壳：
  - `rpc.discover`：本地静态响应（来自 `contract.py` 方法表），不依赖 daemon；
  - 既有 4 方法（`threads.list/show`、`projects`、`stats`）转 HTTP，错误映射维持旧码
    （§2 表）；daemon 连接失败 → `-32000` + 「daemon 未运行」提示；
  - 方法表冻结，不新增方法。
- **Complexity**：Medium

### 10. WebSocket 学习通道（冻结预告）

- `CREATED` `src/zedhub/ws.py`，`websockets>=15,<16` asyncio server，**运行于 daemon
  进程内**（`serve` 同时监听 HTTP 8766 与 WS 8765，共享事件循环与线程池）：
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
      （daemon 进程内直调 Service，与 HTTP 同源，AC-9/AC-15）。
    - 非白名单方法 → `method_not_supported`（message 内附已支持列表）；
      写类操作名同样返回此错误，绝不触达写入代码（AC-16）。
    - 非法 JSON → `invalid_request`。
  - **并发/资源**：每连接内请求串行处理；同步 SQLite 调用放入 §5 共享有界线程池；
    每个请求独立拥有快照/连接并在 `finally` 释放，单请求 30 秒上限。连接关闭时取消
    等待中的 asyncio task；同步 SQLite 调用依靠数据库超时和 `finally` 完成清理。
  - **冻结声明**：README 与 `schema` 的 ws 段必须注明——本通道是一次性学习实现，
    本轮之后不再扩展任何方法或能力；生产与自动化用途一律使用 HTTP API。
  - 角色边界：不桥接任何 agent 引擎内部协议（NFR-7 末段）。
- **错误处理**：`SnapshotError/SchemaError` → 对应 code 的失败响应，连接保持；
  未捕获异常 → `internal_error` 响应 + stderr 记录 traceback，连接保持。
- **Complexity**：Medium

### 11. 写操作：link / archive（导出、导入）+ SSE

公共流水线（全部在 `core/writes.py` `CREATED`，仅 daemon 内执行、CLI 触发）：

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
    备份目录和已提交阶段；本期不自动回滚已提交数据库。Zed 表结构含
    `main_worktree_paths*`、`remote_connection` 列时按当前 schema 显式列出；
  - ID 重生成（ses_/msg_/prt_ base64 22 字符 + uuid thread_id）与
    `get_or_create_project`（显式列）逻辑照搬；目标目录必须已存在；
  - 每个数据库提交后，在确认写连接关闭的前提下分别开新连接执行
    `PRAGMA wal_checkpoint(TRUNCATE)`；checkpoint 失败记录诊断，不把它伪装成成功；
  - 复查：只读连接按目标 directory 计数 thread/session，少于计划 →
    `verify_failed`（明确标注“可能部分状态未知，请查备份”）；跨库复查不完整时同样返回
    `partial/unknown`，并保留操作记录。
- 备份目录不可写 → 写入前终止（`data_dir_error`）。
- **SSE 进度**（§5）：link/export/import 的 daemon 端实现按阶段发射 `stage` 事件
  （validate/process_check/backup/write/checkpoint/verify 各阶段 + 计数明细），CLI
  人读实时渲染；SSE 断开不影响流水线执行，结果照常落 journal。
- **Complexity**：High（import 双库事务、SSE 与写互斥的编排）

### 12. schema 导出

- `CREATED` `src/zedhub/schema_export.py`：**纯本地**（不连 daemon、不连数据库）：
  - `http` 段：迭代 `http_api.ROUTES` 声明表（与路由注册同源），列 method/path/参数/
    响应模型/SSE 能力；
  - `mcp` 段：从 `contract.py` 工具元数据生成（与桥注册同源）；
  - `ws` 段：白名单 + 帧协议 + 冻结声明；
  - `rpc` 段：兼容方法表 + `rpc.discover` 说明；
  - `cli` 段：既有+新命令的输入输出契约摘要；
  - 目录对象：`{"name":"zedhub","version":...,"channels":{"http":{...},"mcp":{...},
    "ws":{...},"rpc":{...},"cli":{...}}}`，默认 `all`。
- **Complexity**：Low

### 13. 数据目录与旧脚本处置

- 快照、备份、操作记录、daemon 地址文件/锁/日志统一写入 `zedhub_data_dir()` 的
  `snapshots/`、`backups/`、`operations/`、`runtime/` 子目录；写前
  `mkdir(parents=True, exist_ok=True)`。
- 快照目录内文件在请求退出前删除；跨库写操作的 operation journal 在验证完成后保留，
  只记录恢复所需的操作状态、ID 映射和备份位置，不保存会话正文副本。
- 用户通过 `-o` 指定的归档文件是显式外部输出，不跟随内部数据目录；项目内部自产数据
  不因读取外部数据库而写回 Zed/OpenCode 或 agent home。
- `.archived/projects/python_projects/zed-opencode-sessions`、
  `.archived/projects/go_projects/ocstat` 和 `python_projects/zedagentstats` 本次不改动；
  新核心不 import、不子进程调用它们，只读取已确认的行为和算法作为迁移参考。
- `CREATED` `python_projects/zedhub/pyproject.toml`：恢复 `zedhub` 包、CLI entry point、
  Python 3.12 约束和已锁定依赖；hatchling + hatch-vcs 动态版本；`uv.lock` 随项目依赖
  生成，不手写。
- `CREATED` `python_projects/zedhub/README.md`：记录 daemon 架构（serve/自动拉起/
  buildID/空闲退出）、CLI、`--json`、MCP 桥、兼容 RPC、HTTP API、WebSocket 学习通道
  及其**冻结声明**、本地数据源路径、写操作安全边界和迁移状态；不在新项目目录创建额外
  docs。

### 14. 可测性与验证边界

- `CREATED` `python_projects/zedhub/tests/`：使用临时目录构造最小 Zed/OpenCode SQLite
  fixture，覆盖成功、空结果、缺表/缺列、坏 JSON、未找到、降级和路径匹配；测试不得读取
  用户真实数据库，也不得把业务数据库写入项目根目录。
- 公共模型、时间/路径解析、effort 时间线、参数校验、错误映射和归档 ID 映射使用单元测试。
- daemon 使用随机回环端口子进程启动：HTTP 端点、包络、错误码、Host 校验、握手、SSE、
  空闲退出（注入缩短时长）、地址文件生命周期；WS 用真实连接验证白名单、非法 JSON、
  binary 帧、超限、断连清理。
- CLI 使用子进程测试 `--help`、`--version`、纯本地命令不产生网络连接、新命令人读/
  `--json`、dry-run 和退出码；旧兼容命令保留归档基线测试。
- MCP 桥与 rpc 用真实 stdio 子进程各验证一次：initialize、tools/list、工具成功/失败、
  rpc.discover 离线可用、daemon 未运行时的报错。
- 写操作只在测试专属临时数据库执行，并在测试结束后关闭连接、删除快照/备份/操作记录；
  真实用户数据库只做显式的人工冒烟，不纳入自动测试。
- 真实验证命令锁定为：`uv sync`、`uv run pytest tests -q`、`uv run zedhub --help`、
  `uv run zedhub schema`；设计阶段只登记命令，执行阶段按用户指令运行。

### Module Collaboration and Data Flow

```
┌─ cli.py (typer 薄壳)      参数解析 → client.call() → 渲染
│   ├ 纯本地: --help/--version/schema/补全 （不触发 daemon）
│   └ 查询/写命令: HTTP+SSE
├─ rpc.py (冻结兼容薄壳)    stdio JSON-RPC ↔ HTTP ； rpc.discover 本地
├─ mcp_bridge.py            stdio(MCP) ↔ HTTP （协议细节按 v1）
└─ 第三方 curl / 脚本        HTTP
          │
          ▼   HTTP+JSON /api/v1 (127.0.0.1:8766) + SSE   ← 唯一契约
┌────────────────── daemon: zedhub serve （唯一业务进程） ──────────────────┐
│ http_api.py (Starlette 路由表/包络/Host 校验/握手/SSE/写互斥)             │
│ ws.py (学习通道 127.0.0.1:8765，冻结)      lifecycle.py (地址文件/空闲/锁) │
│                     │                                                     │
│                     ▼                                                     │
│        api.py (方法注册表/参数校验/序列化) ←─ contract.py (纯契约定义)     │
│                     │                                                     │
│   service.py + sources/ 注册表 + analytics + writes/linking/archive/      │
│   migration                                              (Service 层)      │
│                     │                                                     │
│        core/snapshot.open_snapshot (三件套 → data_dir/snapshots)           │
│                     ▼                                                     │
│        Zed db.sqlite / opencode.db (只读) + 显式列写入（仅 --apply）       │
└───────────────────────────────────────────────────────────────────────────┘
  自动拉起（仅生产构建）: client → detach spawn → runtime/daemon.json → 连接
```

- 依赖方向：壳（cli/rpc/mcp_bridge）→ client/contract；daemon（http_api/ws）→ api →
  service/sources → core；core 不 import 入口；`websockets` 仅 `ws.py` 引用。
- 并发模型：daemon asyncio；同步 SQLite/快照调用进共享有界线程池；写流水线全局互斥；
  每请求独立快照连接，不共享 sqlite 句柄。
- 组装顺序：`serve` 启动只建路由表、注册表与 server，数据库访问惰性到每次请求；
  壳命令先发现地址/握手再发请求。

### Acceptance Criteria Mapping

| AC | 设计组件 |
|---|---|
| AC-1 | §1/§2/§8 sessions 系列 + stats effort 全在 zedhub Service 层 |
| AC-2 | §8 既有命令业务语义不变；§9 rpc 映射维持旧码；daemon 依赖按迁移说明 |
| AC-3 | §2 `Session.zed_thread_id` 关联标记；`sessions list` 用 Zed 索引 join，缺失=None |
| AC-4 | §4 启动模型算法 + `mode/degraded` 标志 |
| AC-5 | §4 `merge_effort`、`cfg_merged`、解析失败跳过 |
| AC-6 | §11 流水线：dry-run 默认、apply 前置检查、备份 |
| AC-7 | §11 checkpoint + 只读复查 + `verify_failed` |
| AC-8 | §11 archive export/import + `schema_version` |
| AC-9 | §5/§10 HTTP 与 WS 共用 `api.call`；§8 信封 data=payload；§9 rpc/MCP 同源 |
| AC-10 | §12 schema 离线、五通道同源（ROUTES/contract/白名单/方法表） |
| AC-11 | §1/§4 `detect_mode` 三级 + `schema_incompatible` |
| AC-12 | §13 不 import 不子进程调用旧项目 |
| AC-13 | §1/§2 `NOT_IMPLEMENTED` + `source_not_supported` |
| AC-14 | §1/§2 `source_id` 标注 + source 命名空间扩展 DTO |
| AC-15 | §10 白名单双方法 + 请求级快照 + 断连清理 |
| AC-16 | §10 白名单外 `method_not_supported`，写代码不可达 |
| AC-17 | §1 source/agent 边界 + §10 白名单与内部协议隔离 |
| AC-18 | §5/§7/§8/§9 壳只含 client+渲染；纯本地命令不触发 daemon |
| AC-19 | §6 serve/地址文件/发现优先级/自动拉起/握手/空闲退出/互斥 |
| AC-20 | §5/§11 SSE 阶段事件、CLI 实时渲染、断流不中止流水线 |

## Design Review Notes

### 自审发现与处理

第一轮（进程内多入口架构）已修复的 HIGH/MEDIUM：目标已归档改重建、跨库不宣称原子性、
Zed/source 边界、CLI 信封兼容边界、agent raw JSON 暴露风险。

第二轮（v2 daemon 架构修订）自审：

1. **HIGH — 壳内禁止 Service 与「schema/MCP 同源」矛盾**：`schema` 纯本地、MCP 桥需要
   工具定义，若定义只存在于 daemon 内则壳必须连 daemon 才能注册工具。已引入
   `contract.py` 纯契约模块（§7，零业务依赖），daemon、桥、rpc、schema 共享同源定义，
   不违反 NFR-3。
2. **HIGH — SSE 断开与写流水线安全冲突**：客户端断流不能中止写流水线（半途中止比完成
   更危险）。已定：SSE 断开仅丢弃进度事件，流水线执行到 AC-6/AC-7 可验证状态，结果落
   journal（§5/§11）。
3. **HIGH — Python 缺少链接期 buildID，单边重启检测弱**：生产 `v{version}` 对开发态无
   分辨力。已定开发态用源码指纹（size+mtime 聚合哈希）作 buildID，改码重启单边即可
   当场检出（§6）。
4. **MEDIUM — Windows pid 探活风险**：`os.kill(pid, 0)` 在 Windows 语义不当。已定存活
   判定以端口 TCP 可连 + `/health` 握手为准，pid 仅诊断展示（§6）。
5. **MEDIUM — 自动拉起孤儿 daemon**：生产环境长期无人调用会后台残留。已按 v2.1 引入
   空闲 30 分钟退出 + 地址文件清理 + 拉起互斥（§6）。
6. **MEDIUM — WS 与 v2「HTTP 唯一契约」冲突**：用户决策保留 WS 作学习通道并存。已定
   WS 归入 daemon 进程、白名单冻结、README 与 schema 显式冻结声明，生产用途一律 HTTP
   （§10）。
7. **MEDIUM — 旧命令/rpc 依赖 daemon 属行为变化**：已在 FR-9 登记迁移说明；开发构建
   报错提示明确，生产构建自动拉起兜底（§6/§8/§9）。

### 已验证假设

- 旧 `zedhub`、`zed-opencode-sessions`、`ocstat` 的源码和公开行为均可从当前仓库归档路径
  读取；`zedagentstats` 是独立的现存多 agent 统计项目。
- 旧 `zedhub` 的 RPC/MCP 方法注册表和 Zed 快照边界已在归档源码中确认。
- `mcp==2.2.0` 的 `MCPServer.tool` 支持显式名称、`ToolAnnotations` 和
  `structured_output`；新项目锁定该版本。
- hatch-vcs 能从 git tag 推导 PEP 440 版本，`uv run` 开发态天然带 `.dev`/local 段，
  支撑生产/开发构建判定；`sys.executable -m zedhub` + `DETACHED_PROCESS` 可实现脱离
  父子关系的拉起。
- Starlette `StreamingResponse` + uvicorn 支持 SSE 长连接；websockets 与 uvicorn 可共享
  一个 asyncio 事件循环。
- 项目自产快照、备份、操作记录与 runtime 文件路径统一由 `APPDATA` 项目目录管理。

### 未作为实现假设的事项

- Zed/OpenCode 上游未来 schema 不稳定；实现必须在运行时探测并按设计降级或拒绝。
- 旧 `zedhub rpc` 是否存在仓库外调用方无法从本仓确认，因此保留既有方法而不扩展。
- daemon 不承诺底层同步 SQLite 调用可被强制中断，只承诺有界等待、最终清理和不泄漏资源。
- 空闲退出时长默认 30 分钟，可在项目文档调整；本轮不做运行时配置项。

**机械判定：HIGH=0，MEDIUM=0，NIT 仅为运行时 schema 演进和外部调用方未知的已登记风险；
设计评审通过。**
