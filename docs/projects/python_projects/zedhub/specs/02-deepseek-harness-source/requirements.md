# 需求文档

## Summary

zedhub 当前已注册 `opencode`（结构化）与 `claude-code` / `codex` / `antigravity` /
`pi`（文件级）五个 agent 数据源，但用户日常使用的 DeepSeek Harness（DSH）会话完全
不在覆盖范围内。DSH 是本机独立 Electron 应用（`DeepSeek Harness Desktop`），会话数据
不与 Zed 索引共享，也不在 OpenCode 数据库中。

本需求新增 **`deepseek-harness` 结构化只读数据源**，让 zedhub 能直接发现、列出、
查看和检索 DSH 本地会话，并把 DSH 正文纳入现有 FTS5 全文索引。明确**不做**
`sessions link` 补登进 Zed，也不做 `archive export/import` 跨机迁移。

已核实的 DSH 本地数据形态（本机实测，251 个会话）：

- 会话文件：`~/.dsh/sessions/<项目 slug>/<session-dir>/session.v4.jsonl.zstd`；
- 内容：zstd 压缩的 JSONL 事件流，首行 `type=session` 携带 `id` / `createdAt` /
  `cwd` / `agentPreset`；
- 关键事件：`session/title`（标题）、`user/message`、`assistant/message`、
  `tool/call`、`tool/result`、`turn/start`、`turn/end`；
- 归档状态：`~/.dsh/storages/workspace.json` 的 `global.archivedSessionIds`；
- 标题缓存：`~/.dsh/storages/session_projcache/sessions/<uuid>.json`（可选兜底）。

## Functional Requirements

### FR-1 源注册与数据根

- 注册 source id `deepseek-harness`，别名 `dsh`；
- 数据根默认 `~/.dsh`，可由环境变量 `DSH_DATA` 覆盖（指向 `<root>`，其下为
  `sessions/` 与 `storages/`）；
- `sources` 查询必须列出该源及 `availability` / `capabilities`；
- capabilities 为 `sessions` / `content` / `discovery`，**不含** `export` / `link`。

### FR-2 会话发现与元数据

- 发现规则：在数据根下递归匹配 `sessions/**/session.v4.jsonl.zstd`；
- `external_id` 取会话目录名（与首行 `id` 一致时以目录名为准，保证稳定）；
- 标题取 `session/title` 事件；无该事件时回退首条真人 `user/message` 文本，
  再回退 `session_projcache` 的 `record.rows.title.val`，最后回退会话 id 前缀；
- 项目目录取首行 `cwd`；
- `created_at` 取首行 `createdAt`（毫秒 epoch，转 UTC aware）；
- `updated_at` 取会话文件 mtime（UTC aware）；
- `archived` 取 `workspace.json` 的 `global.archivedSessionIds` 集合；文件缺失或
  损坏时全部按 `false`，不得让整源失败。

### FR-3 列表、详情与过滤

- 支持 `SessionListRequest` 的 `project`（目录子串）、`agent`、`archived`
  （`no` / `only` / `all`）、`limit`；
- 结果按 `updated_at` 倒序；
- `get_session` 对单个 `external_id` 可用；会话不在当前扫描结果时仍可按文件路径
  直接构造。

### FR-4 正文提取

- 只提取纯文本对话气泡：
  - `user/message` → `data.content[]` 中 `type=text` 的 `text`；
  - `assistant/message` → `data.message.content[]` 中 `type=text` 的 `text`；
- 过滤 `reasoning`、`tool/call`、`tool/result`、系统消息与审批事件；
- 时间取事件 `time`（毫秒 epoch，UTC aware）；
- 按事件流顺序返回 `Message` 列表。

### FR-5 元数据检索

- 该源声明 `sessions` 能力后，检索接口（HTTP / CLI / MCP / Web）自动把 DSH 会话
  投影为 `external_session` 命中；
- 由于 DSH 不进入 Zed 索引，默认 `scope=zed` 下不可见；`scope=all` 或
  `scope=external` 时可见，与 OpenCode 未关联会话语义一致；
- 结果 `agent_id` 为 `deepseek-harness`，`source_id` 为 `deepseek-harness`，
  `management` 为 `external`。

### FR-6 正文全文索引

- 纳入现有 `ContentIndexService`：`build_index` 的 `session_source_ids()` 自动包含
  `deepseek-harness`，无需单独索引库；
- 增量语义沿用 `session_key = "<source_id>:<external_id>"` 与 `updated_at` 比较；
- 单会话解析失败计入 `skipped_sessions`，不中断整批构建。

### FR-7 Web 检索页

- Agent 下拉按外部源动态出现 `deepseek-harness`（沿用现有 `/search?scope=all` 统计）；
- 详情面板类型文案不再冒充 OpenCode：外部源显示为
  `<源展示名> 会话（未被 Zed 管理）`；
- 详情面板「加载正文」对 DSH 可用（走 `GET /api/v1/sessions/{id}/content?source=deepseek-harness`）；
- 「查看轨迹」对 DSH 不显示（本轮不支持轨迹解析）。

### FR-8 契约与文档

- CLI `sessions list/show/content` 的 `--source` 帮助文本、`contract.py` 的 source
  描述更新为包含 `deepseek-harness`；
- README「数据源边界」段落说明 DSH 为独立只读源、不支持 link/export；
- 对接协议文档同步数据源清单。

## Non-Functional Requirements

- **只读**：不得向 `~/.dsh` 写入任何文件、锁或缓存；所有自产数据仍落在
  `%APPDATA%\language_projects\zedhub\<通道>\`。
- **性能**：元数据扫描必须短路读取——逐行解压直到拿到标题或达到行数上限
  （400 行）即停止，不得为列表/搜索全量解压。实测 251 会话元数据扫描约 0.13s；
  全量正文解压约 1.5s / 314MB，仅索引构建与单会话正文读取触发。
- **健壮性**：截断、损坏或非 zstd 文件必须按单会话跳过，不抛未捕获异常；单源失败
  不得影响其他源与整次检索。
- **依赖**：`zstandard` 从 dev 依赖组提升为运行时依赖。
- **安全**：会话文件路径必须限定在数据根内，不跟随符号链接逃逸。

## Acceptance Criteria

### AC-1
WHEN 本机存在 `~/.dsh/sessions`，`GET /api/v1/sources` 返回 `deepseek-harness`，
`availability=supported`，capabilities 含 `sessions`/`content`/`discovery` 且不含
`export`/`link`。

### AC-2
WHEN 数据根不存在，`sources` 返回 `availability=unavailable` 并附原因；
`sessions list --source deepseek-harness` 返回空结果而非错误（不伪造数据）。

### AC-3
WHEN 扫描 `~/.dsh/sessions`，每个 `session.v4.jsonl.zstd` 产出一条会话，标题、
目录、创建时间、更新时间、归档状态按 FR-2 规则填充；251 个会话的扫描耗时在
1s 以内（普通开发机）。

### AC-4
WHEN 调用 `GET /api/v1/sessions/{id}/content?source=deepseek-harness`，返回按事件
顺序排列的 user/assistant 纯文本消息，不含 reasoning 与 tool 内容，时间戳可解析
为 UTC。

### AC-5
WHEN `uv run zedhub search <关键字> --scope all`（或 Web 勾选全部会话），DSH 会话
以 `external_session` 出现在结果中；`--scope zed` 下不出现。

### AC-6
WHEN 执行 `uv run zedhub index build`，DSH 会话正文进入 `content_search.db`；
再次执行且文件未变时计入 `skipped_sessions`；`--content` 检索能命中 DSH 正文。

### AC-7
WHEN 在 Web 检索页查看 DSH 命中，详情面板类型文案正确、可加载正文、不显示
「查看轨迹」；OpenCode 与其他源的既有行为不变。

### AC-8
WHEN `sessions link --source deepseek-harness` 或 `archive export --source deepseek-harness`
被调用，返回 `source_not_supported` 明确错误，不写任何文件或数据库。

## Out of Scope

- `sessions link` 补登 DSH 会话进 Zed `sidebar_threads`；
- `archive export/import` 对 DSH 的跨机迁移；
- DSH 轨迹（trajectory）时间线解析；
- 任何写操作（重命名、删除、归档、改标题）；
- 读取 DSH 的凭据、配置、附件或 `session_projcache` 以外的内部缓存；
- Zed 侧新增 DSH ACP agent 或修改 Zed 配置。
