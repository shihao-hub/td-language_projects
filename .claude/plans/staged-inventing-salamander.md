# zedhub：sessions link 三源补登 + 跨目录挂载

## Context

上轮已交付 archive 三源迁移（`dc969c3`，schema v2）。用户现在需要 **`sessions link --source claude-code|codex|antigravity`**：把三源会话补登进 Zed 索引；并支持**跨目录挂载**——同一会话在另一个工作区目录下新建一份入口（新 thread_id、沿用 session_id、folder_paths=目标目录），原目录入口保留，两个工作区都能打开同一会话。典型场景：`sessions link .thirdparty --source antigravity --target <nanocode>`。

用户已确认：不要 rebind（UPDATE 挪走原行），要新建行、原目录保留。

**数据可得性已验证（本机真实数据）**：

| source | 目录锚点 | title | 时间戳 |
|---|---|---|---|
| claude-code | jsonl 行内 `cwd` 字段（取首个） | 首条 user 消息文本 | 行内 `timestamp`（ISO Z） |
| codex | 首行 `session_meta.payload.cwd` | 首个用户消息 | 行内 `timestamp` |
| antigravity | `conversations/<sid>.meta` JSON 的 `cwd`（91/93 有；无则跳过计数） | ✗（protobuf，留空） | 文件 mtime 兜底 |

## 设计

### 1. `src/zedhub/core/agent_sessions.py`（新建：三源会话扫描器）

- `AgentSessionRecord` dataclass：`session_id / directory(normpath) / title / time_created / time_updated`，时间统一 Zed ISO 格式（`+00:00`、9 位小数）；
- `scan_agent_sessions(source, *, home=None) -> list[AgentSessionRecord]`：
  - claude：扫 `~/.claude/projects/*/*.jsonl`，每文件读前 ~300 行取首个 `cwd`、首条 `type=user` 文本（title ≤80 字符）、首行 timestamp；文件尾部残段（seek size-64KB）取末行 timestamp；
  - codex：扫 `~/.codex/sessions/**/*.jsonl`，首行 `session_meta`（session_id/cwd/timestamp），首个用户消息作 title，末行 timestamp；
  - antigravity：扫 `~/.gemini/antigravity-acp/conversations/*.meta`（JSON 读 cwd）+ 同名 `.db` 存在性，mtime → 时间，title 空；
- 时间 helper：`iso_z_to_zed_ts()`（`Z` → `+00:00` 补 9 位小数）、`mtime_to_zed_ts()`；
- 数据根与 agent_id 映射复用 `core/agent_paths.py`（`agent_data_root` / `SOURCE_AGENT_IDS`）。

### 2. `src/zedhub/core/linking.py` 泛化

- `plan_link(query, *, source="opencode", ...)`：`source=opencode` 走现有 `_load_opencode_sessions` 路径**完全不动**（全局 session_id 查重语义保持，不破坏已交付行为的幂等预期）；
- 三源走 `scan_agent_sessions`；`directory` 为空的记录（antigravity 无 meta）跳过并计 `no_directory`；
- **三源查重语义**：`(agent_id, session_id, 目标目录)` 三元组已存在才跳过——跨目录允许新挂（用户场景核心）；opencode 仍是全局 session_id 查重；
- `LinkPlan` 加 `source` 字段；`execute_link` 的 INSERT 行按 source 参数化：`agent_id=agent_id_for(source)`、`archived=0`、时间直接用（已是 Zed ISO；opencode 仍走 `ms_to_zed_ts`）；
- 消歧（`--all`/`--target`）、进程检查→备份→单事务→checkpoint→复查流水线复用现有代码；复查核对插入的 `(session_id, folder)` 集合。

### 3. 参数面

- `contract.py`：`LinkBody.source: str = "opencode"`；
- `api.py` `_sessions_link` 透传 source；
- `cli.py`：`sessions link --source`（默认 opencode，help 列四值）；渲染加 source 行；
- `core/sources/file_sources.py`：`capabilities` 加 `LINK`，note 更新（支持 archive export/import 与 sessions link 补登，不支持会话查询）；
- README 补 `--source` 与跨目录挂载说明。

## 验证（真实链路 + 隔离 apply）

1. daemon 起后三源 dry-run：`sessions link language_projects --source <三源>` 核对 matched/already_linked/preview 的目录与 title；
2. 用户场景 dry-run + 隔离 apply：`sessions link .thirdparty --source antigravity --target <nanocode>`——验证跨目录新挂 4 行（新 thread_id、原 session_id、folder_paths=nanocode），`.thirdparty` 原行不动；
3. apply 级隔离验证：monkeypatch home（临时数据根）+ Zed db 副本 + 绕 `find_running`，验证写入行（agent_id/时间格式/复查计数）与幂等（重跑同命令 0 新增）；
4. opencode link 回归：全局查重行为不变；
5. `zedhub sources` 显示三源 LINK 能力；`zedhub schema` 含新参数。

## 提交与收尾

- 子仓单 commit：`zedhub:feat: sessions link 三源补登与跨目录挂载`（README 同 commit）；
- 父仓 `docs/projects/python_projects/zedhub/specs/01-zed-session-hub/tasks.md` 增补任务记录，单独 commit；
- 收尾 `aoci_maintain`（若仍 blocked 如实报告）。

## 已知边界

- opencode link 保持全局 session_id 查重（存量语义不动）；跨目录挂载仅三源；
- antigravity 无 `.meta` 的会话（2/93）无法定位目录，跳过并计数；
- 三源补登 thread 一律 `archived=0`、antigravity title 为空；
- session_id 沿用（数据文件锚点），新建的只是 thread_id。
