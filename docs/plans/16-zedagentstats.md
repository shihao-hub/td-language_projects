# 📋 Plan for: zed-pi-stats → zedagentstats 多智能体统计改造

**问题陈述**：`zed-pi-stats` 仅支持统计 Zed 内 `pi-acp` 智能体的 Token/费用，名称与能力均不通用。需原地改造为 `zedagentstats`，支持 pi / antigravity / opencode 三种 ACP 智能体的 Token 与模型消耗统计，CLI 采用子命令形式，保留既有「人读表格 + `--json` + `--schema`」三位一体契约。

**需求**（澄清阶段确认的决策）：

1. v1 覆盖 **pi + antigravity + opencode** 三个 agent（opencode 数据源已在规划期探明）。
2. **原地改名**：目录/包名/CLI 入口全部改为 `zedagentstats`，`git mv` 保留历史，旧 `zed-pi-stats` 入口消失。
3. CLI 用**子命令**：`zedagentstats pi` / `zedagentstats antigravity`（缩写 `agy`）/ `zedagentstats opencode`（缩写 `oc`）；**不带子命令 = 三 agent 合并总览**。
4. 各子命令内保留既有投影参数（`--by-model/--by-project/--by-session`）与 `--json/--schema/-n/--days/--wide/--raw`。
5. 忽略 `~/.gemini/antigravity-acp/.quota_token_cache.json`（那是 agyquota 写的缓存，非 Antigravity 自身数据）。

**背景**（规划期只读调研结论）：

- **Zed 层（三 agent 共用）**：`%LOCALAPPDATA%\Zed\db\0-stable\db.sqlite` → `sidebar_threads` 表按 `agent_id` 过滤（`pi-acp`=17 / `antigravity-acp`=24 / `opencode`=261 线程），提供标题、folder、ISO 时间戳。`session_id` 与各 agent 自身存储的主键**直接相等**（已抽样验证，opencode 的 `ses_xxx` 完全对上）。读取需快照复制（WAL/SHM 三件套）防锁，现有 `collector.get_zed_threads()` 已实现，仅需参数化 agent_id。
- **pi 数据源（现状复用）**：`~/.pi/pi-acp/session-map.json` → 会话 JSONL，逐条 `message.usage` 含 input/output/cacheRead/cacheWrite/reasoning/cost。
- **antigravity 数据源（本次新探明）**：`~/.gemini/antigravity-acp/conversations/<sid>.db`，每会话一个 SQLite，`gen_metadata` 表每次 LLM 生成一行，`data` 列为**无 schema protobuf**。已解码字段：field 19=模型名明文、field 1.4=usage 子消息（f2=input、f3=output、f5=thoughts）、field 1.9.10.4=上下文窗口。f9/f10 语义未定（数值远小于主字段），**保守忽略并注明待校准**。`<sid>.meta` JSON 含 `cwd`。无任何 cost 数据（订阅制）。锚点数字（本机 23 个有数据会话）：1358 次生成全为 `gemini-3.8-flash`，input≈13.4M、output≈0.7M、thoughts≈97.9M。
- **opencode 数据源（本次新探明）**：`~/.local/share/opencode/opencode.db`（**1.9 GB，禁止快照复制**，用 `file:...?mode=ro` 只读 URI 直查，已验证可行；WAL 活跃写入下偶发锁需重试）。`session` 表（431 行）**自带聚合列**：`cost, tokens_input/output/reasoning/cache_read/cache_write, model(JSON), agent, directory, title, time_created/time_updated(ms epoch)`。`message.data` JSON 逐条含 `modelID/providerID/tokens/cost`，可做会话内按模型细分。cost 字段存在但本机全为 0（zhipu 订阅 plan 不回传费用）。
- **现有代码结构**：`src/zed_pi_stats/{models,collector,reporter,cli}.py`，Service 核心已与 CLI/渲染解耦（上一轮重构成果），`models.py` 含纯标准库 JSON Schema。`pyproject.toml`：hatchling、Python>=3.10、仅依赖 rich。
- 父仓 `docs/projects/go_projects/CLI 工具开发标准.md` 有未提交改动（上一任务遗留），与本计划无关，另行处理。

**方案**（高层设计）：

```mermaid
graph TD
    subgraph CLI 层（argparse 子命令）
        A[zedagentstats] --> B{子命令}
        B -->|pi / antigravity·agy / opencode·oc| C[单 agent 投影]
        B -->|无子命令| D[合并总览]
    end
    subgraph Service 核心
        C --> E[AgentSpec 注册表<br/>zed_id / cli名 / 别名 / collector]
        D --> E
        E --> F1[PiCollector<br/>session-map + JSONL]
        E --> F2[AntigravityCollector<br/>conversations/*.db + protobuf 解码]
        E --> F3[OpencodeCollector<br/>opencode.db 只读 URI]
        F1 & F2 & F3 --> G[统一 SessionStats 列表<br/>新增 agent 字段]
    end
    G --> H[reporter 渲染层<br/>表格 / --json / --schema]
    Z[Zed db 快照读取<br/>sidebar_threads 按 agent_id] --> F1 & F2 & F3
```

关键决策与假设：

- **假设 1（f9/f10）**：antigravity usage 的 f9/f10 未定语义字段不展示、不计入 total，代码注释与 README 注明待校准。
- **假设 2（总览形态）**：总览 = 合并 summary + **by-agent 分解表** + 跨 agent 的 by-model 表；`--json/--schema` 同构扩展 `by_agent` 维度。
- **假设 3（opencode 读锁）**：只读 URI + 短重试（3 次 × 0.5s）；失败时该 agent 计数为 0 并在输出中标注不可用，不中断其他 agent。
- **假设 4（cost 展示）**：cost 为 0 时表格显示 `-`（订阅制不回传费用），JSON 保留数值 0。
- antigravity protobuf 解码引入 **`blackboxprotobuf`**（纯 Python 零传递依赖，专为无 .proto 的 schema-less 解码设计，比手写 wire-format 遍历健壮；用户批准）；Schema **生成**继续纯标准库（沿用交接简报既有决策，不引 Pydantic）。
- Schema title 前缀 `ZedPiStats*` 统一改 `Zedagentstats*`，`summary` 增加 `agent` 维度字段属破坏性契约变更，随改名一次性完成。

**任务分解**：

- [x] Task 1: 原地改名骨架（目录、包、入口、元数据）
  - 实施说明：顶层目录被外部进程句柄锁定，改为「子项 git mv + 新建目录」完成迁移（git 仍按相似度识别为 rename，历史保留）；`zed-pi-stats` 旧目录成空壳无法删除，待锁释放后手工清理。构建残留物 `zed-pi-stats.exe` 与 `.venv` 已清理，`__version__` 升至 0.2.0。验证通过：`uv run zedagentstats --by-model` 输出与改名前一致（21 会话 / 68.45M / $1.57）。
  - 文件：`python_projects/zed-pi-stats` → `python_projects/zedagentstats`（`git mv`）；`src/zed_pi_stats` → `src/zedagentstats`（`git mv`）；`pyproject.toml`、`README.md`、`src/zedagentstats/__init__.py`
  - 实现：`git mv` 两个层级保留历史；pyproject 改 `name/description/[project.scripts] zedagentstats = "zedagentstats.cli:main"`；全量替换 import 与文档字符串中的旧名；README 改标题并留「多 agent 改造中」占位说明（此时功能仍是 pi 单体）
  - 验证：`uv run --project python_projects/zedagentstats zedagentstats --by-model` 正常输出表格，数值与改名前一致
  - Demo：新命令名下看到与旧版相同的 pi 模型汇总

- [x] Task 2: 多 agent 架构骨架 + 子命令路由（pi 先接入）
  - 文件：`src/zedagentstats/agents.py`（新建）、`cli.py`、`models.py`、`collector.py`（改造为 `collectors/pi.py`，`get_zed_threads()` 参数化 agent_id）
  - 实现：`AgentSpec` 注册表（zed agent_id、cli 名、别名 agy/oc、collector 工厂）；argparse subparsers（`pi`/`antigravity(agy)`/`opencode(oc)` + 无子命令总览占位）；`SessionStats` 增加 `agent` 字段；pi 采集器挂到新架构
  - 验证：`uv run --project python_projects/zedagentstats zedagentstats pi --by-session -n 3` 正常；`zedagentstats pi --schema` 零 I/O 输出
  - Demo：`pi` 子命令走通新架构；`antigravity`/`opencode` 子命令报「数据源未实现」提示（占位）

- [x] Task 3: antigravity 采集器（protobuf 解码 + 会话库聚合）
  - 实施说明：镜像源仅有 blackboxprotobuf 1.0.1（2.x 不在索引），带来 protobuf 3.10/six/setuptools 三个传递依赖，功能不受影响。锚点验证通过：gemini-3.8-flash 23 会话/1358 轮/in 13.40M/out 700.1K，总 112.00M = in+out+thoughts 97.9M；另见探索期未出现的 gemini-3.7-flash（新会话）。
  - 性能返工（用户实测 `agy` 过慢触发）：进程内剖析 1396 条 blob——bbp 逐条全量解码 22.37s、typedef 复用 2.45s（工具内因 typedef 不完整反复回退实测仍 ~25s）、手写字段遍历 0.04s 且结果逐位一致。**推翻 1=a 决策**，热路径改为手写 wire-format 遍历，`uv remove blackboxprotobuf`（含 3 个传递依赖全部移除）。端到端 `agy --by-model` 25s → 0.46s，数字与锚点一致。
  - 文件：`src/zedagentstats/collectors/antigravity.py`（新建）、`pyproject.toml`（新增 `blackboxprotobuf` 依赖）、`models.py`（thoughts 等字段映射）
  - 实现：`uv add blackboxprotobuf`；快照复制 `conversations/*.db`（单库 ≤6MB 可复制）；用 blackboxprotobuf 解码 `gen_metadata.data`，按字段号路径提取：field 19 → model、field 1.4 → {f2 input, f3 output, f5 reasoning}，f9/f10 按假设 1 忽略并注释；读 `<sid>.meta` 的 `cwd`；与 Zed threads 按 sid join 补标题/时间；无 cost 置 0
  - 验证：`uv run --project python_projects/zedagentstats zedagentstats antigravity --by-model` 输出 `gemini-3.8-flash` 且 in≈13.4M / out≈0.7M / reasoning≈97.9M（对照锚点数字）；`agy` 缩写等价
  - Demo：`zedagentstats agy` 看到 24 个 antigravity 会话的模型消耗与项目归属

- [x] Task 4: opencode 采集器（只读大库查询）
  - 实施说明：覆盖 opencode.db 全量 431 会话（含 Zed 内与独立终端运行，README 注明）；只读 URI + 3×0.5s 重试；message.data 单遍聚合出按模型细分与轮次。验证通过：`oc --by-session --json` 首条即「Pi stats projection handoff」（当前会话自身，in/out/reason=310926/27179/27691 非零）。
  - 文件：`src/zedagentstats/collectors/opencode.py`（新建）
  - 实现：`file:...?mode=ro` URI 连接 + 按假设 3 重试；`session` 表聚合列直接映射 `TokenUsage`；`model` 列 JSON 解析（`providerID/id`）；`message.data` 聚合出会话内按模型细分；ms epoch 时间戳转 ISO 8601；`directory` 映射项目维度
  - 验证：`uv run --project python_projects/zedagentstats zedagentstats opencode --by-session -n 5` 含「Pi stats projection handoff」会话且 in/out/reasoning 数值非零；`oc --json` 合法 JSON
  - Demo：`zedagentstats oc --by-model` 看到 zhipu-glm/glm-5.3 等模型的分布

- [x] Task 5: 合并总览 + 三视图契约收尾 + 文档
  - 实施说明：by_agent 聚合仅出现在合并总览与全量 JSON/Schema（投影视图契约不变）；Schema title 全部改为 Zedagentstats*，SESSION_ITEM_SCHEMA 增加 agent 字段；cost=0 终端显示 `-`。验证通过：无参数总览三段视图非空且 by_agent 行数=3（33/23/431）；`--schema` required 与 `--json` 顶层键一一对应；`uv build` 出包成功；全仓无 zed_pi_stats/zed-pi-stats 残留引用。
  - 文件：`reporter.py`、`models.py`（总览 Schema）、`cli.py`、`README.md`
  - 实现：无子命令总览（合并 summary + by_agent 分解 + 跨 agent by-model，按假设 2）；总览与各子命令的 `--json/--schema` 全量对齐（Schema title 改 `Zedagentstats*`）；README 全面重写（三 agent 用法、数据源说明、f9/f10 与 cost=0 的语义说明）；全链路接线检查无孤儿代码
  - 验证：`uv run --project python_projects/zedagentstats zedagentstats`（无参数）三段视图均非空且 by_agent 行数=3；`--schema` 与 `--json` 字段一一对应；`uv build` 可出包
  - Demo：一条命令看到三 agent 的合并消耗看板

**结构化问题**：无（需求已收敛；关键不确定点均以假设形式记录在方案节，批准即视为认可）。

---

- 最后更新：2026-09-23
- 作者：AI & User
- 版本：v1.1（执行完成：5/5 任务勾选；原被锁的 `python_projects/zed-pi-stats` 空目录已随锁释放删除）
