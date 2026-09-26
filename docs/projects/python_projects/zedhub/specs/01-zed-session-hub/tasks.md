# 任务清单

> 执行约定：按编号顺序执行；每个任务完成后项目应保持可构建。标记 `[test]` 的任务为测试类任务，默认执行阶段跳过，只有用户明确要求执行测试时才执行。`Verify` 是备用验证命令，不代表生成任务文档时已经执行。
>
> 目标项目当前已从 `python_projects` 子仓归档，本清单中的前几个任务会重新创建
> `python_projects/zedhub`；`.archived/` 下的源码只作为迁移参考，不作为运行时依赖。

- [ ] 1. 重建 `zedhub` Python 项目骨架与运行时路径基础，使新项目能够独立安装、显示帮助和版本信息。
  - Files:
    - `python_projects/zedhub/pyproject.toml`
    - `python_projects/zedhub/src/zedhub/__init__.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/__init__.py`
    - `python_projects/zedhub/src/zedhub/core/paths.py`
    - `python_projects/zedhub/src/zedhub/core/errors.py`
    - `python_projects/zedhub/README.md`
    - `python_projects/zedhub/.gitignore`
    - `python_projects/zedhub/uv.lock`
  - 实现细节：
    - 恢复 `zedhub` console script，Python 版本设为 `>=3.12`。
    - 固定 `mcp==2.2.0`，加入 `websockets>=15,<16`、`typer`、`pydantic` 和 pytest 开发依赖。
    - 实现 `--help`、`--version` 的零业务 I/O 入口。
    - 实现 `zedhub_data_dir()`：优先 `%APPDATA%\\language_projects\\zedhub\\`，否则使用
      `~/.language_projects/zedhub/`，并提供 `snapshots/`、`backups/`、`operations/` 的安全建目录函数。
    - 定义公共错误代码和入口无关的异常基类；不得在公共核心调用 `os.Exit`。
    - README 先记录项目定位、数据源边界和当前尚未实现的命令，不复制旧项目运行时依赖。
  - Verify: `uv sync`；预期依赖安装成功并生成可复现的 `uv.lock`；`uv run zedhub --help` 和
    `uv run zedhub --version` 均以退出码 0 返回，且不访问 Zed/OpenCode 数据库。
  - Ref: AC-1、AC-10、NFR-4、NFR-5

- [ ] 2. 恢复 Zed WAL 安全读取核心和既有 Zed 查询业务，保持旧 `zedhub` 的线程、项目与总览语义。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/snapshot.py`
    - `python_projects/zedhub/src/zedhub/core/model.py`
    - `python_projects/zedhub/src/zedhub/core/repo.py`
    - `python_projects/zedhub/src/zedhub/core/service.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 从 `.archived/projects/python_projects/zedhub/src/zedhub/core/` 恢复并重写 Zed 模型、
      schema 检查、时间/路径/BLOB 解析和筛选聚合逻辑。
    - Zed 读取始终复制 `db.sqlite`、`db.sqlite-wal`、`db.sqlite-shm` 到
      `zedhub_data_dir()/snapshots/<id>/`，使用显式字段查询，禁止 `SELECT *`。
    - 保留 `threads list/show`、`projects`、`stats` 的参数、排序、空结果和错误语义；
      既有 `--db` 路径参数必须继续透传到快照入口。
    - 快照和 SQLite 连接由最短业务范围拥有并关闭，schema 缺失时返回稳定错误。
  - Verify: `uv run zedhub threads list --help`、`uv run zedhub threads show --help`、
    `uv run zedhub projects --help`、`uv run zedhub stats --help`；预期均退出码 0，且帮助命令
    不触碰业务数据库。
  - Ref: AC-2、AC-11、FR-2、NFR-1、NFR-2

- [ ] 3. 建立通用会话模型、OpenCode 只读数据源和 agent source 注册表，完成 Zed/OpenCode 关联查询所需的底层能力。
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
      单 session、完整消息内容和 schema 分级探测。
    - OpenCode 默认使用 `mode=ro` + `busy_timeout`；读取失败时复制三件套到项目数据目录
      后重试，禁止 `immutable=1` 直接忽略 WAL。
    - Zed 作为独立索引源，通过 `session_id` 为 OpenCode session 增加可选的
      `zed_thread_id` 关联，缺失时明确返回 `None`。
  - Verify: `uv run zedhub --help`；预期命令仍能启动；使用显式不存在的 `--opencode-db` 路径
    调用新查询入口时返回稳定的数据源缺失错误，而不是 traceback 或空成功结果。
  - Ref: AC-1、AC-3、AC-11、AC-13、AC-14、FR-1、FR-3、FR-10

- [ ] 4. 恢复公共 API 注册表并接入兼容 CLI、JSON-RPC 与 MCP，使参数校验和序列化只有一个事实源。
  - Files:
    - `python_projects/zedhub/src/zedhub/api.py`
    - `python_projects/zedhub/src/zedhub/rpc.py`
    - `python_projects/zedhub/src/zedhub/mcp_server.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/service.py`
  - 实现细节：
    - 从归档基线恢复 `threads.list`、`threads.show`、`projects`、`stats` 和
      `rpc.discover`，保持旧 RPC 方法名、payload 和错误映射。
    - 在同一注册表增加 `sessions.list`、`sessions.show`、`sessions.content`、
      `stats.effort` 的参数说明、JSON Schema 片段和结果序列化函数。
    - 入口层只负责解析、协议适配和渲染；公共 `api.call()` 负责参数校验、source 路由、
      错误分类和业务调用，不操作标准流。
    - 使用 `mcp==2.2.0` 的 `MCPServer.tool(name=..., annotations=..., structured_output=True)`；
      新只读工具显式使用三段式名称和 Pydantic 对象根 output schema，写操作不注册。
    - 兼容 RPC 不新增新业务方法，新增能力由 CLI/MCP 提供。
  - Verify: `'{"jsonrpc":"2.0","id":1,"method":"rpc.discover"}' | uv run zedhub rpc`；
    预期输出一行合法 JSON-RPC 响应且不要求数据库存在；`uv run zedhub mcp --help` 退出码 0。
  - Ref: AC-2、AC-9、AC-10、FR-8、FR-9、NFR-3

- [ ] 5. 移植启动模型与 effort 分析，补齐 OpenCode 配置合并、三级降级和 watch 计算核心。
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
  - Verify: `uv run zedhub stats effort --help`；预期退出码 0；针对一个包含完整 session、
    message、event 的 fixture 执行统计时，结果能区分启动模型与当前模型，并在缺少 event
    表时返回 `degraded=true` 或等价降级标记。
  - Ref: AC-4、AC-5、AC-11、FR-4

- [ ] 6. 实现新的只读 CLI 命令和 Markdown/文本内容输出，统一人读模式与 `--json` 契约。
  - Files:
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/service.py`
    - `python_projects/zedhub/src/zedhub/export/__init__.py`
    - `python_projects/zedhub/src/zedhub/export/markdown.py`
    - `python_projects/zedhub/src/zedhub/core/serialization.py`
  - 实现细节：
    - 增加 `sessions list/show/content` 和 `stats effort`，支持设计中列出的筛选、limit、
      `--format`、`--out`、`--watch`、`-i`、数据源路径及 `--json` 参数。
    - 新命令默认人类可读；新命令 JSON 使用 `{"ok":true,"data":...}` 或
      `{"ok":false,"error":...}`，旧兼容命令保留历史 `status` 信封。
    - `sessions list` 通过 `session_id` 关联 Zed thread，任一侧缺失都显式表达；详情命令不
      将原始数据库 JSON 未筛选地输出。
    - Markdown 导出沿用归档脚本的可读结构，文件写入仅使用用户明确指定的输出路径；内部
      快照、缓存和操作记录仍写入项目数据目录。
  - Verify: `uv run zedhub sessions list --help`、`uv run zedhub sessions content --help`、
    `uv run zedhub stats effort --help`；预期均退出码 0；对空 fixture 使用 `--json` 时输出
    可解析成功对象和空数据，而非错误或人读表格。
  - Ref: AC-1、AC-3、AC-4、AC-5、FR-3、FR-4、FR-5、NFR-3

- [ ] 7. 实现最小 WebSocket 只读通道，并严格隔离 Agent 内部 ACP/WebSocket 协议。
  - Files:
    - `python_projects/zedhub/src/zedhub/ws.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/api.py`
    - `python_projects/zedhub/src/zedhub/README.md`
  - 实现细节：
    - 增加 `zedhub ws`，默认监听 `127.0.0.1:8765`，拒绝非回环 host；并发连接上限为 8，
      单帧上限 1 MiB，binary 帧关闭码 1003，超限关闭码 1013。
    - 使用 JSON 文本帧请求/响应，白名单只允许 `threads.list` 和 `stats`；参数校验直接
      复用公共 `api.call()`，未知方法和写操作返回 `method_not_supported`。
    - 使用有界线程池执行同步 SQLite/快照调用，每请求独立资源、30 秒上限、断连取消等待，
      并在 `finally` 中释放连接和快照；服务关闭时等待线程池清理。
    - 校验 `Origin`/`Host` 的回环范围，错误响应保持连接，未捕获异常记录 stderr 并返回
      `internal_error`；不得启动 Agent 引擎或接收 ACP/protobuf/CortexStep 消息。
    - README 记录帧信封、关闭码、回环安全边界和当前不支持的内部桥接协议。
    - `python_projects/zedhub` 代码与父仓库文档若需同时提交，必须分别在 Python 子仓和父仓库
      创建独立 commit，不跨提交范围混提。
  - Verify: `uv run zedhub ws --help`；预期退出码 0；启动 `uv run zedhub ws --host 0.0.0.0`
    时以参数错误拒绝；使用 WebSocket 客户端发送 `threads.list` 和 `stats` 能收到合法响应，
    发送写操作或 binary 帧不会修改数据库。
  - Ref: AC-15、AC-16、AC-17、FR-8、NFR-7

- [ ] 8. 实现写操作安全基础设施和 OpenCode 会话补登，保持 dry-run 默认与幂等行为。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/writes.py`
    - `python_projects/zedhub/src/zedhub/core/processes.py`
    - `python_projects/zedhub/src/zedhub/core/backup.py`
    - `python_projects/zedhub/src/zedhub/core/journal.py`
    - `python_projects/zedhub/src/zedhub/core/linking.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 实现 Windows `tasklist` 进程检查；仅 `--apply` 强制要求 Zed/OpenCode 退出，dry-run 不
      写入且允许进程运行。
    - 备份 Zed/OpenCode 数据库三件套到
      `%APPDATA%\\language_projects\\zedhub\\backups\\<operation_id>\\`，路径不可写时在
      写入前终止；不得把备份写到外部数据库目录或 `%TEMP%`。
    - 实现 operation journal 的 `planned`、`partial`、`unknown` 等状态、operation_id、
      备份路径和阶段记录；公共写入核心不调用 `os.Exit`。
    - 移植 `link_sessions.py` 的目录匹配、`--all`、`--target`、`--include-subagents`、
      session_id 幂等跳过、UUID thread_id、毫秒到 Zed UTC 时间转换和写后复查。
    - 写入使用单库短事务、参数化 SQL、显式字段和 `PRAGMA wal_checkpoint(TRUNCATE)`；
      失败不得报告成功。
  - Verify: `uv run zedhub sessions link --help`；预期退出码 0；不带 `--apply` 执行时只输出
    计划且目标数据库字节不变；对临时目标库执行 `--apply` 后，重复执行会跳过已关联 session，
    并报告实际插入数量和复查结果。
  - Ref: AC-6、AC-7、AC-11、FR-6、NFR-1、NFR-4

- [ ] 9. 实现归档导出与归档检查，生成带版本和来源标识的可迁移 SQLite 文件。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/archive.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/src/zedhub/core/opencode_repo.py`
    - `python_projects/zedhub/README.md`
  - 实现细节：
    - 移植归档导出能力，但把所有 `SELECT *` 改为显式字段列表，并固定归档表结构和索引。
    - 写入 `_archive_meta`：`schema_version`、`source_agent`、导出时间、项目、归档开关及
      thread/session/message/part 数量。
    - 支持 `archive export <project> -o FILE [--archived] [--json]` 和
      `archive inspect FILE [--json]`；用户指定的归档输出路径按用户意图执行，内部运行数据
      不因此写入外部数据库目录。
    - 导出前通过统一 Zed/OpenCode 只读源获取数据，归档中不写入不属于选定项目的 session。
  - Verify: `uv run zedhub archive export --help`、`uv run zedhub archive inspect --help`；预期
    退出码 0；对临时 fixture 导出后，`archive inspect` 能读取版本、source_agent 和各表数量，
    且归档文件可被 SQLite 只读打开。
  - Ref: AC-8、AC-11、FR-5、FR-7、NFR-2

- [ ] 10. 实现跨机器归档导入、分库写入状态和写后验证，明确处理部分成功与未知结果。
  - Files:
    - `python_projects/zedhub/src/zedhub/core/migration.py`
    - `python_projects/zedhub/src/zedhub/core/writes.py`
    - `python_projects/zedhub/src/zedhub/core/journal.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
  - 实现细节：
    - 支持 `archive import FILE --target DIR` dry-run 和显式 `--apply`；先校验归档
      `schema_version/source_agent`、目标目录、Zed/OpenCode schema、进程状态和备份可写性。
    - 读取归档时显式列出 `_archive_meta`、Zed thread、OpenCode session/message/part 所需字段，
      不猜测未知版本，不使用 `SELECT *`。
    - 生成并保存 session/message/part/thread ID 映射，创建或复用目标 project，重写外键，
      保留目标机已有数据。
    - 分别执行 OpenCode 与 Zed 短事务；每次提交后 checkpoint，最后分别只读复查。不得使用
      `ATTACH` 宣称跨 WAL 数据库单事务原子性。
    - 任一阶段失败时保留 operation journal、备份、映射和已提交阶段，返回 `partial` 或
      `unknown`；成功必须满足两库复查和数量一致，才返回成功。
  - Verify: `uv run zedhub archive import --help`；预期退出码 0；默认执行只输出导入计划且不
    写目标库；对临时目标库使用 `--apply` 后，目标原有记录仍存在、导入记录可查询、复查数量
    与计划一致；模拟第二库失败时返回非成功状态并输出 operation_id 与备份位置。
  - Ref: AC-6、AC-7、AC-8、AC-11、FR-7、NFR-1、NFR-5

- [ ] 11. 实现离线 schema 导出、协议说明和项目交付文档，保证契约与实际 MCP/WS 注册同源。
  - Files:
    - `python_projects/zedhub/src/zedhub/schema_export.py`
    - `python_projects/zedhub/src/zedhub/cli.py`
    - `python_projects/zedhub/README.md`
    - `docs/projects/python_projects/zedhub/zedhub 对接协议.md`
  - 实现细节：
    - 增加 `zedhub schema`，默认输出 MCP、WS、兼容 RPC 和 CLI 的契约摘要；MCP 部分从实际
      注册定义生成，并完整处理 `tools/list` 分页，不连接任何业务数据库。
    - 记录 WebSocket JSON 信封、白名单、错误码、回环限制、关闭码和 Agent 内部协议隔离；
      记录新旧 CLI JSON 信封差异、MCP 启动方式和兼容 RPC 方法。
    - README 记录真实安装、`uv run`、数据源默认路径、数据目录、dry-run/`--apply`、备份、
      部分成功恢复边界和未来 agent source 扩展限制。
    - 代码与父仓库文档分别提交，不能把 Python 子仓代码和 `docs/projects/...` 文档放入同一
      commit。
  - Verify: `uv run zedhub schema`；预期在 Zed/OpenCode 数据库不存在时仍以退出码 0 输出合法
    JSON；`uv run zedhub --help` 与协议文档中的命令、参数和能力列表一致。
  - Ref: AC-10、AC-13、AC-14、AC-15、AC-17、FR-8、NFR-3、NFR-6、NFR-7

- [ ] 12. [test] 补齐公共核心、数据源、模型、effort 和写入安全的单元测试与临时 SQLite fixture。
  - Files:
    - `python_projects/zedhub/tests/conftest.py`
    - `python_projects/zedhub/tests/fixtures.py`
    - `python_projects/zedhub/tests/test_core.py`
    - `python_projects/zedhub/tests/test_sources.py`
    - `python_projects/zedhub/tests/test_analytics.py`
    - `python_projects/zedhub/tests/test_api.py`
    - `python_projects/zedhub/tests/test_writes.py`
  - 实现细节：
    - 构造最小 Zed/OpenCode/归档数据库，不读取真实用户数据库；覆盖空结果、完整数据、缺表/缺列、
      错误 JSON、时间线边界、配置合并、source 未支持、记录未找到和多目录消歧。
    - 覆盖 dry-run 字节不变、幂等补登、备份路径、显式字段查询、journal 状态和写后复查；
      所有临时路径使用 pytest 临时目录或注入的数据目录，并在测试结束清理。
    - 覆盖跨库第二阶段失败时的 `partial/unknown` 结果和 operation_id 输出，不测试未经设计
      承诺的自动回滚。
  - Verify: `uv run pytest tests/test_core.py tests/test_sources.py tests/test_analytics.py tests/test_api.py tests/test_writes.py -q`；预期所有测试通过，且测试过程不读取 `%LOCALAPPDATA%\\Zed`、
    `OPENCODE_DATA` 或用户 home 下的真实 agent 数据。
  - Ref: AC-3、AC-4、AC-5、AC-6、AC-7、AC-8、AC-11、AC-13、AC-14
  - [test]

- [ ] 13. [test] 补齐 CLI、MCP、JSON-RPC、WebSocket 的真实进程与兼容性验证，形成最终交付证据。
  - Files:
    - `python_projects/zedhub/tests/test_cli.py`
    - `python_projects/zedhub/tests/test_rpc.py`
    - `python_projects/zedhub/tests/test_mcp.py`
    - `python_projects/zedhub/tests/test_ws.py`
    - `python_projects/zedhub/tests/test_compatibility.py`
  - 实现细节：
    - 通过子进程验证 `--help`、`--version`、旧命令、new command `--json`、参数错误、空结果、
      schema 离线导出和退出码；禁止把 grep 或 import 成功当作 CLI 验证。
    - 真实启动 MCP stdio server，完成 initialize、完整 tools/list 分页、只读 tool 成功调用和
      工具失败路径；检查 stdout 无诊断污染，确认 output schema 与 `schema` 导出一致。
    - 真实启动 WebSocket server，验证连接、`threads.list`、`stats`、非法 JSON、binary 帧、
      未知方法、写操作拒绝、Origin/Host 边界、连接关闭后的资源清理和端口关闭。
    - 对归档 `zedhub` 的旧 RPC 方法、旧 CLI 输出契约和 `--db` 透传建立回归样例；新方法不要求
      出现在旧 RPC 方法表中。
  - Verify: `uv run pytest tests/test_cli.py tests/test_rpc.py tests/test_mcp.py tests/test_ws.py tests/test_compatibility.py -q`；预期所有真实入口测试通过，MCP/WS 子进程在测试结束后退出，
    不留下监听端口、后台进程、快照或备份文件。
  - Ref: AC-2、AC-9、AC-10、AC-15、AC-16、AC-17、FR-8、FR-9、NFR-3、NFR-7
  - [test]

- [ ] 14. 完成发布前清理、迁移说明和任务状态回写，确保旧项目退出运行时链路且新项目可独立交付。
  - Files:
    - `python_projects/zedhub/README.md`
    - `python_projects/zedhub/pyproject.toml`
    - `python_projects/zedhub/uv.lock`
    - `docs/projects/python_projects/zedhub/zedhub 对接协议.md`
    - `docs/projects/python_projects/zedhub/specs/01-zed-session-hub/tasks.md`
  - 实现细节：
    - 核对新项目不 import `.archived` 或 `python_projects/zedagentstats`，不启动 `ocstat.exe`，
      不把内部数据写回 Zed/OpenCode/agent home。
    - 更新 README、对接协议和版本号，记录当前仅支持 OpenCode、WebSocket 仅两个只读方法、
      未来 agent source 未实现、旧 RPC 兼容边界和跨库部分成功恢复方式；代码、父仓库文档和
      本 `tasks.md` 分别按仓库范围提交。
    - 仅在任务实际完成并验证后将对应任务标记为 `[x]`；跳过的 `[test]` 任务保持 `[ ]`，并在
      实施说明中记录未执行原因。
  - Verify: `uv sync`、`uv run pytest tests -q`、`uv run zedhub --help`、`uv run zedhub schema`；
    预期依赖、测试、帮助和离线 schema 均成功，且 `git grep`/运行时依赖检查确认旧项目不在
    新项目 import 或子进程链路中。
  - Ref: AC-1、AC-10、AC-12、AC-13、AC-14、NFR-3、NFR-4
