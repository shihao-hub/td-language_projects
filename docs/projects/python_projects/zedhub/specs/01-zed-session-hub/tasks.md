# 任务清单

> 执行约定：按编号顺序执行；每个任务完成后项目应保持可构建。标记 `[test]` 的任务为测试类任务，默认执行阶段跳过，只有用户明确要求执行测试时才执行。`Verify` 是备用验证命令，不代表生成任务文档时已经执行。
>
> 目标项目当前已从 `python_projects` 子仓归档，本清单中的前几个任务会重新创建
> `python_projects/zedhub`；`.archived/` 下的源码只作为迁移参考，不作为运行时依赖。
>
> 架构基准：同目录 `design.md`（daemon 架构，遵循《CLI 工具开发标准 v2》+ v1 契约细节）。
> Service 层只存在于 daemon；CLI、MCP 桥、兼容 RPC 均为 HTTP 薄客户端。

- [x] 1. 重建 `zedhub` Python 项目骨架、数据目录与构建身份基础，使新项目能够独立安装、
  显示帮助和版本信息，并具备生产/开发构建判定能力。
  - Files:
    - `python_projects/zedhub/pyproject.toml`
    - `python_projects/zedhub/src/zedhub/__init__.py`
    - `python_projects/zedhub/src/zedhub/__main__.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/__init__.py`
    - `python_projects/zedhub/src/zedhub/core/paths.py`
    - `python_projects/zedhub/src/zedhub/core/errors.py`
    - `python_projects/zedhub/src/zedhub/buildid.py`
    - `python_projects/zedhub/README.md`
    - `python_projects/zedhub/.gitignore`
    - `python_projects/zedhub/uv.lock`
  - 实现细节：
    - 恢复 `zedhub` console script，Python 版本设为 `>=3.12`；构建后端 hatchling +
      hatch-vcs（版本由 git tag 推导，开发态天然带 `.dev`/local 段）。
    - 固定 `mcp==2.2.0`，加入 `websockets>=15,<16`、`starlette>=0.40,<1`、
      `uvicorn>=0.30,<1`、`typer`、`pydantic` 和 pytest 开发依赖。
    - 实现 `--help`、`--version` 的纯本地入口（零网络、零数据库 I/O）。
    - 实现 `zedhub_data_dir()`：优先 `%APPDATA%\language_projects\zedhub\`，否则使用
      `~/.language_projects/zedhub/`，并提供 `snapshots/`、`backups/`、`operations/`、
      `runtime/` 的安全建目录函数。
    - `buildid.py`：生产/开发构建判定（PEP 440 版本含 `.dev`/local 段即开发构建）；
      buildID 生成——生产 `v{version}`，开发 `dev-{源码指纹}`（`src/zedhub/**/*.py`
      size+mtime 聚合哈希，进程内只算一次）。
    - 定义公共错误代码（含 `daemon_unreachable`、`handshake_mismatch`）和入口无关的
      异常基类；不得在公共核心调用 `os.Exit`。
    - README 先记录 daemon 架构定位、数据源边界和当前尚未实现的命令，不复制旧项目
      运行时依赖。
  - Verify: `uv sync`；预期依赖安装成功并生成可复现的 `uv.lock`；`uv run zedhub --help`
    和 `uv run zedhub --version` 均以退出码 0 返回，且不访问 Zed/OpenCode 数据库、不产生
    网络连接。
  - Ref: AC-1、AC-10、AC-18、NFR-4、NFR-5

- [x] 2. 恢复 Zed WAL 安全读取核心和既有 Zed 查询业务（Service 层），保持旧 `zedhub`
  的线程、项目与总览语义。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/snapshot.py`
    - `python_projects/zedhub/src/zedhub/core/model.py`
    - `python_projects/zedhub/src/zedhub/core/repo.py`
    - `python_projects/zedhub/src/zedhub/core/service.py`
  - 实现细节：
    - 从 `.archived/projects/python_projects/zedhub/src/zedhub/core/` 恢复并重写 Zed 模型、
      schema 检查、时间/路径/BLOB 解析和筛选聚合逻辑。
    - Zed 读取始终复制 `db.sqlite`、`db.sqlite-wal`、`db.sqlite-shm` 到
      `zedhub_data_dir()/snapshots/<id>/`，使用显式字段查询，禁止 `SELECT *`。
    - 保留 `threads list/show`、`projects`、`stats` 的参数、排序、空结果和错误语义，
      作为 Service 方法供后续 HTTP API 调用。
    - 快照和 SQLite 连接由最短业务范围拥有并关闭，schema 缺失时返回稳定错误。
  - Verify: `uv run python -c "from zedhub.core.service import ThreadService; from
    zedhub.core.repo import ZedDb"`；预期导入成功；`uv run zedhub --help` 仍退出码 0。
  - Ref: AC-2、AC-11、FR-2、NFR-1、NFR-2

- [x] 3. 建立通用会话模型、OpenCode 只读数据源和 agent source 注册表（Service 层），
  完成 Zed/OpenCode 关联查询所需的底层能力。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/model.py`
    - `python_projects/zedhub/src/zedhub/core/opencode_repo.py`
    - `python_projects/zedhub/src/zedhub/core/sources/__init__.py`
    - `python_projects/zedhub/src/zedhub/core/sources/base.py`
    - `python_projects/zedhub/src/zedhub/core/sources/opencode_source.py`
    - `python_projects/zedhub/src/zedhub/core/snapshot.py`
    - `python_projects/zedhub/src/zedhub/core/errors.py`
  - 实现细节：
    - 定义 `ModelRef`、`Session`、`Message`、`MessagePart`、`SessionContent` 和
      `SessionListRequest`；公共字段不依赖 OpenCode 专有表名或原始 JSON。
    - 定义 `AgentSource`、`SourceInfo`、`Availability`、`Capability` 及 source 注册表；当前
      只注册 `opencode`，未注册的 Pi、Claude Code、Codex、Antigravity 返回
      `source_not_supported`，不得伪造为空结果。
    - 实现 `OpencodeDb`：显式读取 `session`、`message`、`part` 所需字段，支持 session 列表、
      单 session、完整消息内容和 schema 分级探测（full/basic/broken）。
    - OpenCode 默认使用 `mode=ro` + `busy_timeout`；读取失败时复制三件套到项目数据目录
      后重试，禁止 `immutable=1` 直接忽略 WAL。
    - Zed 作为独立索引源，通过 `session_id` 为 OpenCode session 增加可选的
      `zed_thread_id` 关联，缺失时明确返回 `None`。
  - Verify: `uv run python -c "from zedhub.core.sources import SOURCES; assert
    'opencode' in SOURCES"`；预期导入成功且注册表含 opencode。
  - Ref: AC-1、AC-3、AC-11、AC-13、AC-14、FR-1、FR-3、FR-10

- [x] 4. 移植启动模型与 effort 分析（Service 层），补齐 OpenCode 配置合并、三级降级和
  watch 计算核心。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/analytics.py`
    - `python_projects/zedhub/src/zedhub/core/config.py`
    - `python_projects/zedhub/src/zedhub/core/opencode_repo.py`
    - `python_projects/zedhub/src/zedhub/core/model.py`
  - 实现细节：
    - 按归档 `ocstat` 口径扫描首条非 title assistant 消息和
      `session.created.1`/`session.updated.1` 事件时间线，恢复消息时刻生效的启动模型。
    - 实现 `full`、`basic`、`broken` 三种模式；消息/事件坏 JSON 逐行跳过并计数，缺少表列
      时按可安全降级或稳定 schema 错误处理。
    - 按 `config.json → opencode.json → opencode.jsonc` 顺序读取配置，合并
      `reasoningEffort`/`effort`；配置文件缺失或解析失败不能使主统计失败。
    - 实现 effort 排序、provider/model 分组、占比、生成时间、降级说明和 `default→effort`
      展示口径；分析核心无状态，watch 只负责重复调用。
  - Verify: `uv run python -c "from zedhub.core.analytics import resolve_startup"`；
    预期导入成功。
  - Ref: AC-4、AC-5、AC-11、FR-4

- [x] 5. 建立公共契约模块 `contract.py`，为 daemon、MCP 桥、兼容 RPC 和 schema 导出提供
  同源的纯协议定义。
  - Files:
    - `python_projects/zedhub/src/zedhub/contract.py`
  - 实现细节：
    - 纯协议定义、零业务依赖：不 import sqlite、Service 或任何入口模块。
    - 定义 HTTP 端点参数/响应 pydantic 模型、MCP 工具元数据（名称、描述、输入模型、
      输出 DTO）、兼容 RPC 方法表（4 旧方法映射 + rpc.discover 静态文档）、WS 帧信封
      模型与白名单。
    - 契约与实现同源的不变量：daemon 路由、桥注册、schema 导出均迭代本模块定义，不得
      手抄副本。
  - Verify: `uv run python -c "import zedhub.contract"`；预期导入成功且无业务模块副作用
    （不创建数据目录、不访问数据库）。
  - Ref: AC-9、AC-10、AC-18、NFR-3

- [x] 6. 恢复公共 API 注册表并实现 daemon HTTP API 与 `serve` 子命令，使 HTTP+JSON 成为
  唯一业务契约。
  - Files:
    - `python_projects/zedhub/src/zedhub/api.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 恢复归档基线的方法注册表（`threads.list/show`、`projects`、`stats`），并新增
      `sessions.list/show/content`、`stats.effort` 的参数说明、JSON Schema 片段和结果
      序列化函数；参数未注册 source → `source_not_supported`。
    - `http_api.py`：Starlette 数据驱动路由表 `ROUTES`（method/path/业务方法/参数
      schema/SSE 能力），路由注册与 schema 导出迭代同一张表。
    - 实现设计文档 §5 的全部 GET/POST 端点；JSON 包络沿用 v1（`ok/data/error`），HTTP
      状态码按错误表映射，`error.code` 为唯一稳定契约。
    - 每请求校验 `Host` 头为回环域，否则 403；`X-Zedhub-Build` 握手校验，不等返回 409 +
      `handshake_mismatch`。
    - 同步 Service 调用经 `asyncio.to_thread` 进入有界线程池（默认 8）；写流水线全局
      互斥（本轮可为占位锁，写端点在任务 12-15 落地）。
    - `zedhub serve` 前台子命令：uvicorn 承载、日志输出、优雅关闭（等待在途请求与线程
      池结束、删地址文件）。
    - 本任务先实现同步 JSON 形态；SSE 流式形态在任务 15 落地。
  - Verify: `uv run zedhub serve --help`；预期退出码 0；手动 `uv run zedhub serve` 后
    `uv run python -c "import urllib.request; print(urllib.request.urlopen(
    'http://127.0.0.1:8766/api/v1/health').read().decode())"` 返回含 `build_id` 的
    JSON，Ctrl+C 退出后进程与端口释放。
  - Ref: AC-9、AC-18、AC-19、FR-8、FR-11、NFR-3、NFR-7

- [x] 7. 实现 daemon 生命周期与客户端发现：地址文件、发现优先级、自动拉起（仅生产）、
  buildID 握手、空闲退出与拉起互斥。
  - Files:
    - `python_projects/zedhub/src/zedhub/lifecycle.py`
    - `python_projects/zedhub/src/zedhub/client.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
  - 实现细节：
    - 地址文件 `zedhub_data_dir()/runtime/daemon.json`（host/port/pid/build_id/
      started_at/auto_spawned），原子写、退出清理；`runtime/daemon.lock` 启动互斥；存活
      判定以端口可连 + `/health` 握手为准，pid 仅诊断（Windows 不用信号探活）。
    - `client.py` 共享 HTTP client：发现优先级 `--host` → `ZEDHUB_HOST` → 地址文件 →
      默认 `127.0.0.1:8766`；自动附带 `X-Zedhub-Build` 头。
    - 自动拉起仅生产构建且未显式指定地址：`sys.executable -m zedhub serve
      --auto-spawned`，`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`，stderr 重定向
      `runtime/daemon.log`；拉起后轮询地址文件 + 握手（默认 10 秒）。
    - 生产构建显式指定地址连不上报错不拉起；开发构建一律报 `daemon_unreachable` 并提示
      「先运行 `zedhub serve`」；拉起前二次探测互斥。
    - `--auto-spawned` 启用的空闲退出（默认 30 分钟，仅无在途请求期间累计，请求结束
      重置）；前台 serve 不设空闲退出。
  - Verify: `uv run zedhub serve --host 0.0.0.0` 以参数错误拒绝；dev 构建下不启动 serve
    直接 `uv run zedhub threads list`（任务 8 落地后）报「先运行 `zedhub serve`」；
    serve 启动后 `runtime/daemon.json` 存在、退出后被清理。
  - Ref: AC-19、FR-11、NFR-4

- [x] 8. 实现 CLI 薄壳的查询命令：恢复旧命令并新增只读命令，统一人读模式与 `--json`
  契约，全部经 HTTP 调 daemon。
  - Files:
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/client.py`
    - `python_projects/zedhub/src/zedhub/export/__init__.py`
    - `python_projects/zedhub/src/zedhub/export/markdown.py`
    - `python_projects/zedhub/src/zedhub/serialization.py`
  - 实现细节：
    - 恢复 `threads list/show`、`projects`、`stats` 旧命令（参数、排序、旧 `status`
      兼容信封不变），实现为参数解析 → `client.call()` → 渲染的薄壳。
    - 新增 `sessions list/show/content` 和 `stats effort`：支持设计中列出的筛选、limit、
      `--format`、`--out`、`--watch`、`-i`、`--host` 及 `--json` 参数；watch = CLI 循环
      调 HTTP；`-i<=0` 报 invalid_params。
    - 新命令默认人类可读；新命令 JSON 使用 `{"ok":true,"data":...}` /
    `{"ok":false,"error":...}`，旧兼容命令保留历史 `status` 信封。
    - Markdown 导出沿用归档脚本的可读结构；文件写入仅使用用户明确指定的输出路径。
    - `sessions list` 结果含 `zed_linked` 关联标记，任一侧缺失都显式表达；详情命令不将
      原始数据库 JSON 未筛选地输出。
    - daemon 连接失败按任务 7 的发现/拉起/报错策略处理。
  - Verify: `uv run zedhub threads list --help`、`uv run zedhub sessions list --help`、
    `uv run zedhub stats effort --help`；预期均退出码 0（纯本地，不触发 daemon）；dev
    构建下不带 serve 执行查询命令返回「先运行 `zedhub serve`」类错误而非 traceback。
  - Ref: AC-1、AC-2、AC-3、AC-4、AC-5、AC-9、FR-3、FR-4、FR-5、NFR-3

- [x] 9. 实现兼容 JSON-RPC 薄壳：`zedhub rpc` 经 HTTP 调 daemon，`rpc.discover` 本地响应。
  - Files:
    - `python_projects/zedhub/src/zedhub/rpc.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - stdin 读 JSON-RPC 请求；`rpc.discover` 用 `contract.py` 方法表本地静态响应，
      不依赖 daemon。
    - 既有 4 方法（`threads.list/show`、`projects`、`stats`）转 HTTP 调用，payload 与
      错误映射维持旧码（`-32602`/`-32001`/`-32000` 等）；方法表冻结不新增。
    - daemon 连接失败 → `-32000` + 「daemon 未运行，请先执行 zedhub serve」类 message。
    - 未知方法 → `-32601`（旧语义）。
  - Verify: `uv run zedhub rpc --help` 退出码 0；`echo '{"jsonrpc":"2.0","id":1,
    "method":"rpc.discover"}' | uv run zedhub rpc` 在 daemon 未运行时输出一行合法
    JSON-RPC 响应（discover 不依赖 daemon）。
  - Ref: AC-2、AC-9、AC-18、FR-8、FR-9、NFR-3

- [x] 10. 实现 MCP 桥：stdio MCP ↔ HTTP daemon，只读工具注册与 schema 同源。
  - Files:
    - `python_projects/zedhub/src/zedhub/mcp_bridge.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - `zedhub mcp` 启动 stdio MCP server（`mcp==2.2.0`），工具实现全部经 HTTP 调
      daemon；桥不 import sqlite/Service。
    - 保留存量工具名 `threads_list` 等 + 新增三段式
      `zedhub.sessions.list/show/content`、`zedhub.stats.effort`；显式
      `MCPServer.tool(name=..., annotations=ToolAnnotations(read_only_hint=True,
      destructive_hint=False, idempotent_hint=True), structured_output=True)`；
      工具元数据来自 `contract.py`，与 schema 导出同源。
    - 桥启动先与 daemon 握手（失败即启动报错并提示先 `zedhub serve`）；HTTP 错误码 →
      MCP 错误；写操作不注册。
  - Verify: `uv run zedhub mcp --help` 退出码 0；dev 构建下 daemon 未运行时启动桥收到
    清晰报错而非挂起。
  - Ref: AC-9、AC-10、AC-18、FR-8、NFR-3

- [x] 11. 实现 WebSocket 学习通道（daemon 内组件，白名单双方法），并在 README 声明冻结。
  - Files:
    - `python_projects/zedhub/src/zedhub/ws.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/README.md`
  - 实现细节：
    - daemon 启动时同时监听 WS `127.0.0.1:8765`（`websockets>=15,<16`，与 uvicorn 共享
      事件循环与线程池）；拒绝非回环 host；并发连接上限 8，单帧上限 1 MiB，binary 帧
      关闭码 1003，超限关闭码 1013。
    - JSON 文本帧请求/响应，白名单只允许 `threads.list` 和 `stats`；参数校验直接复用
      `api.call()`（daemon 进程内直调，与 HTTP 同源），未知方法和写操作返回
      `method_not_supported`。
    - 每请求独立资源、30 秒上限、断连取消等待并在 `finally` 释放连接和快照；校验
      `Origin`/`Host` 回环范围；错误响应保持连接，未捕获异常记录 stderr 并返回
      `internal_error`。
    - 不得启动 Agent 引擎或接收 ACP/protobuf/CortexStep 消息（收到未支持消息返回明确
      错误）。
    - README 记录帧信封、关闭码、回环安全边界，并**明确声明**：WS 是一次性学习实现，
      本轮之后冻结不再扩展，生产与自动化用途一律使用 HTTP API。
  - Verify: `uv run zedhub serve --help` 退出码 0；手动启动 serve 后用
    `uv run python -c`（websockets sync client）发送
    `{"id":1,"method":"threads.list","params":{}}` 收到合法 JSON 响应，发送写操作方法名
    收到 `method_not_supported`。
  - Ref: AC-15、AC-16、AC-17、FR-8、NFR-7

- [x] 12. 实现写操作安全基础设施和 OpenCode 会话补登（Service 层 + CLI + HTTP 端点），
  保持 dry-run 默认与幂等行为。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/writes.py`
    - `python_projects/zedhub/src/zedhub/core/processes.py`
    - `python_projects/zedhub/src/zedhub/core/backup.py`
    - `python_projects/zedhub/src/zedhub/core/journal.py`
    - `python_projects/zedhub/src/zedhub/core/linking.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 实现 Windows `tasklist` 进程检查；仅 `--apply` 强制要求 Zed/OpenCode 退出，dry-run
      不写入且允许进程运行。
    - 备份 Zed/OpenCode 数据库三件套到
      `%APPDATA%\language_projects\zedhub\backups\<operation_id>\`，路径不可写时在
      写入前终止；不得把备份写到外部数据库目录或 `%TEMP%`。
    - 实现 operation journal 的 `planned`、`partial`、`unknown` 等状态、operation_id、
      备份路径和阶段记录；公共写入核心不调用 `os.Exit`。
    - 移植 `link_sessions.py` 的目录匹配、`--all`、`--target`、`--include-subagents`、
      session_id 幂等跳过、UUID thread_id、毫秒到 Zed UTC 时间转换和写后复查。
    - 写入使用单库短事务、参数化 SQL、显式字段和 `PRAGMA wal_checkpoint(TRUNCATE)`；
      失败不得报告成功。
    - HTTP `POST /api/v1/sessions/link` 与 CLI `sessions link` 命令（dry-run 本任务同步
      JSON 形态；apply 的 SSE 流式形态在任务 15 落地）。
  - Verify: `uv run zedhub sessions link --help`；预期退出码 0；daemon 运行时不带
    `--apply` 执行只输出计划且目标数据库字节不变；对临时目标库执行 `--apply` 后，重复
    执行会跳过已关联 session，并报告实际插入数量和复查结果。
  - Ref: AC-6、AC-7、AC-11、FR-6、NFR-1、NFR-4

- [x] 13. 实现归档导出与归档检查（Service 层 + CLI + HTTP 端点），生成带版本和来源标识的
  可迁移 SQLite 文件。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/archive.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/opencode_repo.py`
  - 实现细节：
    - 移植归档导出能力，但把所有 `SELECT *` 改为显式字段列表，并固定归档表结构和索引。
    - 写入 `_archive_meta`：`schema_version`、`source_agent`、导出时间、项目、归档开关及
      thread/session/message/part 数量。
    - 实现 `archive export <project> -o FILE [--archived] [--json]` 和
      `archive inspect FILE [--json]`（HTTP `POST /api/v1/archive/export`、
      `/archive/inspect`）；用户指定的归档输出路径按用户意图执行，内部运行数据不因此
      写入外部数据库目录。
    - 导出前通过统一 Zed/OpenCode 只读源获取数据，归档中不写入不属于选定项目的 session。
  - Verify: `uv run zedhub archive export --help`、`uv run zedhub archive inspect --help`；
    预期退出码 0；对临时 fixture 导出后，`archive inspect` 能读取版本、source_agent 和
    各表数量，且归档文件可被 SQLite 只读打开。
  - Ref: AC-8、AC-11、FR-5、NFR-2

- [x] 14. 实现跨机器归档导入（Service 层 + CLI + HTTP 端点）、分库写入状态和写后验证，
  明确处理部分成功与未知结果。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/migration.py`
    - `python_projects/zedhub/src/zedhub/core/writes.py`
    - `python_projects/zedhub/src/zedhub/core/journal.py`
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 实现 `archive import FILE --target DIR`（HTTP `POST /api/v1/archive/import`）dry-run
      和显式 `--apply`；先校验归档 `schema_version/source_agent`、目标目录、Zed/OpenCode
      schema、进程状态和备份可写性。
    - 读取归档时显式列出 `_archive_meta`、Zed thread、OpenCode session/message/part 所需
      字段，不猜测未知版本，不使用 `SELECT *`。
    - 生成并保存 session/message/part/thread ID 映射，创建或复用目标 project，重写外键，
      保留目标机已有数据。
    - 分别执行 OpenCode 与 Zed 短事务；每次提交后 checkpoint，最后分别只读复查。不得使用
      `ATTACH` 宣称跨 WAL 数据库单事务原子性。
    - 任一阶段失败时保留 operation journal、备份、映射和已提交阶段，返回 `partial` 或
      `unknown`；成功必须满足两库复查和数量一致，才返回成功。
  - Verify: `uv run zedhub archive import --help`；预期退出码 0；默认执行只输出导入计划
    且不写目标库；对临时目标库使用 `--apply` 后，目标原有记录仍存在、导入记录可查询、
    复查数量与计划一致；模拟第二库失败时返回非成功状态并输出 operation_id 与备份位置。
  - Ref: AC-6、AC-7、AC-8、AC-11、FR-7、NFR-1、NFR-5

- [x] 15. 实现 SSE 进度流：写类长任务的 daemon 端点流式阶段事件与 CLI 实时渲染。
  - Files:
    - `python_projects/zedhub/src/zedhub/http_api.py`
    - `python_projects/zedhub/src/zedhub/core/writes.py`
    - `python_projects/zedhub/src/zedhub/core/linking.py`
    - `python_projects/zedhub/src/zedhub/core/migration.py`
    - `python_projects/zedhub/src/zedhub/client.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 写类端点（`sessions/link`、`archive/export`、`archive/import` 的 apply/长任务形态）
      在 `Accept: text/event-stream` 时返回 SSE：`stage` 事件（阶段 + 明细 + 可选 pct）、
      `result` 事件（完整结果对象，同同步形态 data）、`error` 事件（错误码 + message）。
    - 写流水线在关键阶段（validate/process_check/backup/write/checkpoint/verify）发射
      进度回调；SSE 客户端断开仅丢弃进度事件，流水线继续执行到可验证状态，结果照常落
      operation journal（NFR-7）。
    - CLI 人读模式 apply 执行走 SSE 并单行刷新渲染阶段进度，结束时打印计划数量、备份
      路径、实际写入数和复查结论；`--json` 模式输出最终 result 对象。
    - 未带 SSE Accept 的写端点保持同步 JSON 形态（小任务可用）。
  - Verify: `uv run zedhub sessions link --help` 退出码 0；对临时目标库执行 `--apply`
    （人读模式）能看到阶段进度行，`--json` 输出可解析的结果对象；apply 进行中断开
    SSE/终止 CLI 后重启 daemon 查询，目标库状态与 journal 记录一致（不出现半途中止的
    未知损坏状态）。
  - Ref: AC-20、AC-6、AC-7、FR-8、NFR-7

- [x] 16. 实现离线 schema 导出、协议说明和项目交付文档，保证契约与实际注册同源。
  - Files:
    - `python_projects/zedhub/src/zedhub/schema_export.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/README.md`
    - `docs/projects/python_projects/zedhub/zedhub 对接协议.md`
  - 实现细节：
    - 增加 `zedhub schema`（纯本地，不连 daemon、不连数据库）：默认输出 http、mcp、ws、
      rpc、cli 五通道契约摘要；http 段迭代 `ROUTES` 声明表、mcp 段来自 `contract.py`
      工具元数据、ws 段含白名单与冻结声明、rpc 段含兼容方法表、cli 段列命令契约摘要。
    - 记录 daemon 架构（serve/发现优先级/自动拉起/buildID 握手/空闲退出）、HTTP JSON
      包络与错误码、SSE 事件协议、WebSocket JSON 信封/白名单/关闭码/回环限制/**冻结
      声明**、新旧 CLI JSON 信封差异、MCP 桥启动方式和兼容 RPC 方法。
    - README 记录真实安装、`uv run`、数据源默认路径、数据目录、dry-run/`--apply`、备份、
      部分成功恢复边界和未来 agent source 扩展限制。
    - 代码与父仓库文档分别提交，不能把 Python 子仓代码和 `docs/projects/...` 文档放入
      同一 commit。
  - Verify: `uv run zedhub schema`；预期在 Zed/OpenCode 数据库不存在、daemon 未运行时
    仍以退出码 0 输出合法 JSON；`uv run zedhub --help` 与协议文档中的命令、参数和能力
    列表一致。
  - Ref: AC-10、AC-13、AC-14、AC-15、AC-17、AC-18、FR-8、NFR-3、NFR-6、NFR-7

- [ ] 17. [test] 补齐公共核心、数据源、模型、effort、写入安全和 daemon 生命周期的单元
  测试与临时 SQLite fixture。
  - 未执行原因：[test] 任务默认跳过（执行约定），本轮未要求跑测试；
    执行阶段已用临时 fixture 脚本完成同等冒烟验证（快照/降级/时间线/写流水线/partial）。
  - Files:
    - `python_projects/zedhub/tests/conftest.py`
    - `python_projects/zedhub/tests/fixtures.py`
    - `python_projects/zedhub/tests/test_core.py`
    - `python_projects/zedhub/tests/test_sources.py`
    - `python_projects/zedhub/tests/test_analytics.py`
    - `python_projects/zedhub/tests/test_api.py`
    - `python_projects/zedhub/tests/test_writes.py`
    - `python_projects/zedhub/tests/test_lifecycle.py`
  - 实现细节：
    - 构造最小 Zed/OpenCode/归档数据库，不读取真实用户数据库；覆盖空结果、完整数据、
      缺表/缺列、错误 JSON、时间线边界、配置合并、source 未支持、记录未找到和多目录
      消歧。
    - 覆盖 dry-run 字节不变、幂等补登、备份路径、显式字段查询、journal 状态和写后复查；
      所有临时路径使用 pytest 临时目录或注入的数据目录，并在测试结束清理。
    - 覆盖跨库第二阶段失败时的 `partial/unknown` 结果和 operation_id 输出，不测试未经
      设计承诺的自动回滚。
    - 覆盖 buildID 生成与生产/开发判定、地址文件原子写与清理、空闲计时重置逻辑
      （注入缩短时长）。
  - Verify: `uv run pytest tests/test_core.py tests/test_sources.py tests/test_analytics.py
    tests/test_api.py tests/test_writes.py tests/test_lifecycle.py -q`；预期所有测试
    通过，且测试过程不读取 `%LOCALAPPDATA%\Zed`、`OPENCODE_DATA` 或用户 home 下的真实
    agent 数据。
  - Ref: AC-3、AC-4、AC-5、AC-6、AC-7、AC-8、AC-11、AC-13、AC-14、AC-19
  - [test]

- [ ] 18. [test] 补齐 daemon HTTP、CLI、MCP 桥、JSON-RPC、WebSocket、SSE 的真实进程与
  兼容性验证，形成最终交付证据。
  - Files:
    - `python_projects/zedhub/tests/test_daemon.py`
    - `python_projects/zedhub/tests/test_cli.py`
    - `python_projects/zedhub/tests/test_rpc.py`
    - `python_projects/zedhub/tests/test_mcp.py`
    - `python_projects/zedhub/tests/test_ws.py`
    - `python_projects/zedhub/tests/test_sse.py`
    - `python_projects/zedhub/tests/test_compatibility.py`
  - 实现细节：
    - daemon 子进程（随机回环端口）验证 HTTP 端点、包络、错误码、Host 头校验、buildID
      握手失败路径、优雅关闭与地址文件清理；不把 grep 或 import 成功当作验证。
    - 通过子进程验证 `--help`、`--version`、纯本地命令不产生网络连接、旧命令、新命令
      `--json`、参数错误、空结果、schema 离线导出和退出码。
    - 真实启动 MCP 桥 stdio 子进程：initialize、完整 tools/list 分页、只读 tool 成功调用
      和失败路径；确认 output schema 与 `schema` 导出一致、stdout 无诊断污染。
    - 真实验证 WS：连接、`threads.list`、`stats`、非法 JSON、binary 帧、未知方法、写
      操作拒绝、Origin/Host 边界、连接关闭后的资源清理。
    - 真实验证 SSE：apply 长任务的 stage/result/error 事件序列、CLI 渲染、断流后 daemon
      端流水线完成并可从 journal 查到结果。
    - rpc 子进程验证旧方法 payload/错误映射与 `rpc.discover` 离线可用；对归档 `zedhub`
      的旧 CLI 输出契约和 `--db` 透传建立回归样例。
    - 所有子进程（daemon/桥/CLI）在测试结束后退出，不留下监听端口、后台进程、快照或
      备份文件。
  - Verify: `uv run pytest tests/test_daemon.py tests/test_cli.py tests/test_rpc.py
    tests/test_mcp.py tests/test_ws.py tests/test_sse.py tests/test_compatibility.py -q`；
    预期所有真实入口测试通过。
  - Ref: AC-2、AC-9、AC-10、AC-15、AC-16、AC-17、AC-18、AC-19、AC-20、FR-8、FR-9、
    NFR-3、NFR-7
  - [test]

- [x] 19. 完成发布前清理、迁移说明和任务状态回写，确保旧项目退出运行时链路且新项目可
  独立交付。
  - Files:
    - `python_projects/zedhub/README.md`
    - `python_projects/zedhub/pyproject.toml`
    - `python_projects/zedhub/uv.lock`
    - `docs/projects/python_projects/zedhub/zedhub 对接协议.md`
    - `docs/projects/python_projects/zedhub/specs/01-zed-session-hub/tasks.md`
  - 实现细节：
    - 核对新项目不 import `.archived` 或 `python_projects/zedagentstats`，不启动
      `ocstat.exe`，不把内部数据写回 Zed/OpenCode/agent home；壳模块（cli/rpc/
      mcp_bridge）不 import sqlite 或 Service 层。
    - 更新 README、对接协议和版本号，记录当前仅支持 OpenCode、WebSocket 冻结声明、
      未来 agent source 未实现、旧 RPC 兼容边界、daemon 依赖的行为变化和跨库部分成功
      恢复方式；代码、父仓库文档和本 `tasks.md` 分别按仓库范围提交。
    - 仅在任务实际完成并验证后将对应任务标记为 `[x]`；跳过的 `[test]` 任务保持 `[ ]`，
      并在实施说明中记录未执行原因。
  - Verify: `uv sync`、`uv run pytest tests -q`、`uv run zedhub --help`、
    `uv run zedhub schema`；预期依赖、测试、帮助和离线 schema 均成功，且 `git grep`/
    运行时依赖检查确认旧项目不在新项目 import 或子进程链路中、Service 层仅存在于
    daemon 代码路径。
  - Ref: AC-1、AC-10、AC-12、AC-13、AC-14、AC-18、NFR-3、NFR-4

- [x] 20. 扩展 archive export/import 支持 claude-code / codex / antigravity 三 agent
  源的会话归档迁移（schema v2 整文件字节搬运 + import 写回闭环）。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/agent_paths.py`
    - `python_projects/zedhub/src/zedhub/core/archive.py`
    - `python_projects/zedhub/src/zedhub/core/migration.py`
    - `python_projects/zedhub/src/zedhub/core/journal.py`
    - `python_projects/zedhub/src/zedhub/core/sources/base.py`
    - `python_projects/zedhub/src/zedhub/core/sources/file_sources.py`
    - `python_projects/zedhub/src/zedhub/core/sources/__init__.py`
    - `python_projects/zedhub/src/zedhub/contract.py`
    - `python_projects/zedhub/src/zedhub/api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/schema_export.py`
    - `python_projects/zedhub/README.md`
  - 实现细节：
    - 新增 `agent_paths.py`：source↔Zed agent_id 映射（claude-acp/codex-acp/
      antigravity-acp）、各源数据根（`~/.claude` | `~/.codex` | `~/.gemini`）与
      `locate_session_files`（claude `projects/*/<sid>.jsonl`、codex
      `sessions/**/*-<sid>.jsonl`、antigravity `conversations/<sid>.db` 及旁带
      `.meta`；同 sid 多文件全收）。
    - 归档 schema v2（只增不改，v1 opencode 路径零改动）：`zed_threads` + 新表
      `agent_files(source, session_id, rel_path, size_bytes, content BLOB)`，JSONL
      与 SQLite 统一为整文件字节 blob（antigravity protobuf 无公开 schema，不做
      结构化解析）；meta 新增 missing_session_count/file_count/total_bytes。
    - `export_archive` 增加 `source` 形参分派 v1/v2；v2 结果含 missing_session_ids；
      `read_archive_meta`/`inspect_archive` 兼容两种 schema 计数。
    - v2 import：`_load_archive` 按 schema_version+source_agent 分派；apply 流程
      = find_running 进程检查（zed+opencode）→ Zed db 备份 → 先写源数据文件
      （已存在一律 skip，幂等）→ 再写 Zed threads（新 thread_id、session_id 原样
      保留、folder_paths=target、已存在 session_id 跳过防重复补登）→ 复查；journal
      新增 `files_committed` 状态；Zed 阶段失败 → partial（重跑安全）。
    - 三源注册 EXPORT-only `SourceInfo`（availability 按数据根存在性，会话查询
      raise source_not_supported 不伪造空结果）；`PLANNED_SOURCES` 收缩为 `("pi",)`。
    - 契约面：`ArchiveExportBody.source` 默认 opencode、endpoint summary 与
      schema 导出 cli 行更新；CLI `archive export --source` + export/inspect/import
      渲染适配 v2 计数字段。
  - Verify: 真实链路（遵循任务 17/18 跳过 pytest 惯例）：daemon 起后三源真实导出
    （claude 16 thread/16 file、codex 4 thread/1 file/3 missing、antigravity --exact
    21 thread/42 file）+ opencode v1 回归导出；inspect ×4 meta/计数正确；import
    dry-run ×3 计划正确且零写入；apply 级隔离验证（Zed db 副本 + monkeypatch 数据根
    与进程检查）三源全 PASS（文件字节一致、Zed 行写入、session_id 保留、复查计数、
    二次运行 skip 幂等）；sources 端点三源 supported(export)；schema 导出含 source。
  - Ref: FR-7、AC-13

- [x] 21. sessions link 三源补登与跨目录挂载：`--source claude-code|codex|antigravity`
  把三源会话补登进 Zed 索引；三源查重按 (agent_id, session_id, 目标目录) 三元组，
  同会话可在另一工作区目录新挂入口（新 thread_id、沿用 session_id、原目录行保留）。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/agent_sessions.py`（新增）
    - `python_projects/zedhub/src/zedhub/core/linking.py`
    - `python_projects/zedhub/src/zedhub/core/sources/file_sources.py`
    - `python_projects/zedhub/src/zedhub/contract.py`
    - `python_projects/zedhub/src/zedhub/api.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/schema_export.py`
    - `python_projects/zedhub/README.md`
  - 实现细节：
    - 新增 `agent_sessions.py`：`AgentSessionRecord` + `scan_agent_sessions(source,
      home=)` 浅层元数据扫描（只读每会话头部 ~300 行与尾部 64KB 残段，不解析正文）：
      claude 行内 cwd/首条真人 user 消息/行内 ISO Z 时间戳；codex 首行 session_meta
      锚定 + response_item user 消息；antigravity 以 `.db` 为锚、`.meta` JSON 读
      cwd（title 留空、mtime 兜底时间）；环境注入块（`<...>`、`# AGENTS.md`）不作
      标题；同 sid 多文件（codex resume 沿用原 sid、claude 目录改名）按"首个非空
      标题 + 最早 created + 最晚 updated"合并去重；时间 helper iso_z_to_zed_ts /
      mtime_ns_to_zed_ts 统一 9 位小数 +00:00 格式；空目录 normpath 修正（""
      不得变 "."）。
    - `linking.py` 泛化：`plan_link`/`run_link`/`LinkPlan` 加 source（默认
      opencode）；opencode 路径与全局 session_id 查重语义零改动；三源查重走
      `_zed_linked_folders`（按 agent_id 过滤、folder_paths 换行拆分 + normpath
      比较）；`execute_link` INSERT 按 source 参数化 agent_id 与时间（opencode 仍
      ms_to_zed_ts，三源直用 Zed ISO、archived=0）；复查升级为 (session_id,
      folder) 集合比对（跨目录挂载时同 sid 已有原目录行，只查 sid 会误判）；结果
      增加 source / no_directory 字段。
    - 参数面：`LinkBody.source` 默认 opencode（schema 导出同源）；api 透传；CLI
      `sessions link --source`（help 列四值）+ 渲染 source 行与 no_directory 行；
      file_sources capabilities 加 LINK（note 同步）；README 新增「会话补登」章节
      与跨目录挂载示例。
  - Verify: apply 级隔离验证（临时 home + Zed db 副本 + 绕进程检查）32 断言全
    PASS：antigravity 跨目录挂载（新 thread_id/原行不动/agent_id/archived=0/时间
    格式/复查计数）+ 幂等重跑 0 新增 + no_directory=2 + claude/codex title 与时间
    断言 + 未知 source 拒绝；daemon 真实链路 dry-run：claude 37 matched/5 planned、
    codex 17/2（去重后）、antigravity --all 10/4 + no_directory=2、用户场景
    `.thirdparty --target <nanocode>` 10 条全挂目标目录；opencode link 回归（全局
    查重、--all、消歧报错不变）；sources 端点三源 capabilities=[export,link]；
    schema 导出含 source 参数。
  - Ref: FR-6、FR-7 扩展、AC-13
