# 多 Agent 开发流水线工具调研：用现成工具搭 subagents 流水线

- 调研日期：**2026-10-03**（所有活跃度数据、版本号、API 状态均以当日在线一手来源为准）
- 调研目标：回答「能否用现成工具搭 Uncle Bob 式五步多 Agent 开发流水线」：
  ① 规格定义器（需求 → Gherkin/测试骨架）→ ② 编码器（实现至测试全绿）→ ③ 清理器（按 lint/复杂度报告重构）→ ④ 强化器（变异测试补测试）→ ⑤ QA 门禁（依赖规则 + 全量测试 + 覆盖率）
- 流水线核心特征：每环节单一职责、干净上下文；环节间靠磁盘文件传递；通过标准由**确定性工具**的退出码/阈值判定；**LLM 只修不判**。
- 信息分级标注约定（全文严格区分）：
  - **【官方】**：来自官方文档原文（code.claude.com/docs、各框架官方文档站点）
  - **【README 自述】**：来自项目 README / 仓库自述，未经机制级验证的部分
  - **【推断】**：基于已验证机制做出的分析推断
- 数据取得方式：WebFetch 抓取官方文档页；`gh api`（GitHub REST API）查仓库元数据、release、README；PyPI JSON API 查发布版本。

---

## a. 执行摘要

**直接回答：截至 2026-10-03，没有一个现成工具可以开箱即用地完整实现这五步闭环；但用 Claude Code 原生件（`.claude/agents/*.md` + hooks + `claude -p` headless）在脚本层自建，是工作量最小、确定性最强、最贴合流水线核心特征的路线，量级约 1～2 天。**

各选项与五步闭环的距离：

| 选项 | 覆盖五步程度 | 主要差距 | 搭建工作量量级 |
| --- | --- | --- | --- |
| **自建 headless 脚本链**（5 个 subagent 定义 + `claude -p --json-schema` + 门禁脚本 + hooks 兜底） | 全部五步，判定权完全在确定性工具 | 需自己写编排脚本与门禁脚本 | **1～2 天**（门禁加固再 +0.5 天） |
| **Claude Code Dynamic Workflows**（官方，让 Claude 写 workflow 脚本存为 `/pipeline`） | 全部五步的编排；门禁在「门禁 agent」内执行 | workflow 脚本自身无 shell 访问，判定要靠 agent 结构化输出回传（弱一档） | 0.5～1 天 |
| **obra/superpowers**（社区插件） | ①②⑤大半（brainstorm→plan→subagent-driven-development→TDD→review） | ③清理器、④变异测试强化器无对应 skill；门禁是提示层强制而非退出码判定 | 复用 0.5 天 + 自写 2 个 skill 约 1～2 天 |
| **foreman**（社区编排器） | 结构上最接近（gated pipeline + headless Claude + 磁盘状态 + 编排器强制 guardrails） | **已停更约 3 个月**（2026-06-29 后无 push），流程是其自有五段（plan→ADR/PRD→issues→TDD build→e2e）而非我们的五步 | 不建议直接押注；借鉴其设计半天 |
| **通用框架**（LangGraph / CrewAI / AG2 / OpenAI Agents SDK） | 全部五步但要自己写全部编排+执行层代码 | 脱离 Claude Code 生态，subagent 系统提示、工具环、权限、hooks 都要重造 | 1～2 周起 |
| **CI 层**（GitHub Actions + claude-code-action） | 只适合外环⑤（PR 级 QA 门禁） | 内环 ①→④ 延迟与成本不划算 | 半天（仅外环） |

关键机制事实（详见 b 节）：Claude Code 的每个 subagent **原生运行在独立 context window**（【官方】），环节间天然通过共享工作目录的磁盘文件传递产物（【官方】+【推断】）；hooks 的 **exit 2 是唯一凭退出码就能阻断的信号**（【官方】），`claude -p` 的**进程退出码**与 `--json-schema` 结构化输出可以让「判定」完全落在 bash/PowerShell 脚本而不是 LLM 手里（【官方】）——这三点意味着流水线的三个硬约束（干净上下文、磁盘传递、确定性判定）在 Claude Code 上都有原生承载体。

---

## b. 逐工具调研

### 1. Claude Code 原生能力（最重要，全部以官方文档为准）

当前 CLI 版本背景：`anthropics/claude-code` 最新 release **v2.1.287**（2026-10-01 发布），处于高频发版状态（每日 patch）。下述机制均核实自 code.claude.com/docs 当前页面。

#### 1.1 Subagents（`.claude/agents/*.md`）——环节定义的原生载体

来源：<https://code.claude.com/docs/en/sub-agents>【官方】

- 定义方式：Markdown 文件 + YAML frontmatter，正文即该 agent 的 system prompt。最小必填字段只有 `name` 与 `description`。
- 关键 frontmatter 字段（部分）：

  | 字段 | 作用 | 对五步流水线的意义 |
  | --- | --- | --- |
  | `tools` / `disallowedTools` | 工具白名单/黑名单（白名单缺省继承全部；两者同设时先应用黑名单再解析白名单） | 规格定义器可只给 Read/Glob/Grep/Write；编码器不给 Web 访问等【官方】 |
  | `model` | `sonnet`/`opus`/`haiku`/完整 ID/`inherit` | 环节按需配模型 |
  | `permissionMode` | `default`/`acceptEdits`/`plan`/`bypassPermissions` 等，缺省继承主会话 | 编码器可给 `acceptEdits`，QA 环节只读 |
  | `maxTurns` | 限制轮数，超限输出标记 partial | 防单环节失控【官方】 |
  | `isolation: worktree` | 在默认分支新建的隔离仓库副本中工作，无改动自动清理 | 多环节并行改文件时防冲突【官方】 |
  | `background: true` | 强制后台运行 | 并行环节 |
  | `hooks` | agent 级生命周期 hooks | 环节内嵌门禁【官方】 |
  | `memory` | `user`/`project`/`local` 跨会话记忆 | 一般不需要，保持环节无状态更符合单一职责【推断】 |

- **上下文隔离机制**（文档原文要点）：每个 subagent 运行在自己的 context window；非 fork subagent 的初始上下文**只包含**：自身 system prompt（不是 Claude Code 的默认 system prompt）、主会话写的任务委托消息、CLAUDE.md 层级、git status 快照、预载 skills。**看不到主对话历史、主会话已读过的文件、已调用过的 skills**【官方】。→ 「每环节干净上下文」是原生语义，不是模拟。
- **环节间传递**：文档明确「没有直接的文件传递字段」，机制是：① subagent 从主会话 cwd 启动，共享同一份 checkout，前序环节写的文件后续环节可见（不开 `isolation: worktree` 时）；② 主会话串联（"先让 A 找问题，再让 B 修"）；③ 完成的 subagent 返回 agent ID，可用 `SendMessage` 续聊（保留完整历史）。→ 与「环节间靠磁盘文件传递」的设计天然契合：让每环节把产物落盘、把结论写进约定文件，上下文只经磁盘过手【官方 + 推断】。
- **并行/后台**：并发 subagent 默认上限 20（`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`）；交互会话 v2.1.232+ 默认 fork 模式即全部后台化；Ctrl+B 可把前台任务转后台；嵌套深度默认 3 层（`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` 可调）【官方】。
- 调用方式：主会话自动委托（按 description）、`@agent-<name>` 强制点名、`claude --agent <name>` 整会话化身、headless 下 `--agents '<json>'` 动态注入（v2.1.281+ 还支持 JSON 文件路径）【官方】。

#### 1.2 Agent Teams（实验性）——结论：不适合本场景

来源：<https://code.claude.com/docs/en/agent-teams>【官方】

- 需 `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 显式开启（默认关）。结构为 team lead + 多个 teammate（各自完整 Claude Code 实例）+ 共享任务列表 + JSON 文件 mailbox（`~/.claude/teams/{team-name}/inboxes/`）。
- 官方明确定位：适合**并行探索/相互挑战**型工作（并行 review、竞争假设调试）；「对顺序任务、同文件编辑、强依赖工作，单会话或 subagents 更有效」【官方原文语义】。
- 对流水线的不利点：headless `-p`（含 Agent SDK 会话）下**不会产生 teammates**【官方】；split-pane 模式不支持 VS Code 集成终端、**Windows Terminal** 与 Ghostty【官方】——本仓库是 Windows 11 环境。
- 可借鉴点：`TeammateIdle`/`TaskCreated`/`TaskCompleted` hooks 以 exit 2 阻断任务状态流转——这是「LLM 想宣布完成时被确定性检查拦回」的原生挂点【官方】。

#### 1.3 Dynamic Workflows——官方的「编排脚本化」答案

来源：<https://code.claude.com/docs/en/workflows>【官方】

- 形态：JavaScript 脚本（Claude 按任务替你写），由运行时在后台执行，编排大量 subagent。可用 `/workflows` 面板观察每个 phase/agent 的进度与 token，可暂停/恢复/存为 `/<名字>` 命令（存到 `.claude/workflows/` 或 `~/.claude/workflows/`）。
- 脚本 API：`agent(prompt, {schema, label})` 起一个 subagent；`pipeline(list, fn)` 对列表逐项各起一个；`parallel(...)` 并行；`phase()` 分组；`log()` 输出；`args` 全局变量接收调用入参；`meta` 块声明名字与描述。`schema` 使 agent 返回校验过的 JSON（结构不符最多重试 5 次，`MAX_STRUCTURED_OUTPUT_RETRIES` 可调）【官方】。
- 与流水线的关系：官方示例 prompt 里就有「use a workflow to run npx tsc --noEmit and keep fixing the reported errors until the type check passes or two rounds in a row make no progress」——正是 ②→门禁 回路的官方背书【官方】。
- **关键限制**（【官方】约束表原文语义）：
  - workflow 脚本自身**无文件系统/shell 访问**——「Agent 读写和跑命令，脚本只协调 agent」。因此确定性判定不能写在脚本里直接跑 `pytest && 判定`，要么让一个只跑命令的门禁 agent 把退出码/结果以 `schema` 结构化回传（LLM 是搬运工、判定逻辑在命令本身，尚可接受【推断】），要么把硬门禁留给 hooks/外层脚本。
  - 中途不接受用户输入；无 `import()`；默认并发 16（`CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` 可调 1–256）；单次 `parallel()`/`pipeline()` 上限 4096 项；单次 run 总 agent 上限 1000。
  - 同会话内可恢复（已完成 agent 回放缓存结果，中间失败会重放其后全部 agent）。
- Pro 计划需在 `/config` 打开 Dynamic workflows；付费计划/API/Bedrock/Vertex/Foundry 可用【官方】。

#### 1.4 Hooks——确定性门禁的核心承载

来源：<https://code.claude.com/docs/en/hooks>【官方】

- 事件清单覆盖全生命周期：`PreToolUse`（可阻断）、`PostToolUse`（不可阻断，stderr 反馈给 Claude）、`PostToolBatch`（整批工具后、下次模型调用前，exit 2 可停循环）、`Stop`/`SubagentStop`（exit 2 或 JSON `decision: block` 可**阻止收工**继续干）、`TaskCompleted`、`SessionStart` 等 30+ 事件。
- **退出码语义（关键）**：
  - exit 0 = 成功/无决策；**exit 2 = 阻断错误**——「对可阻断事件，无论是否输出 JSON，exit 2 一律阻断；即使 JSON 里写 allow 也压不过 exit 2」；除 0/2 外的退出码对多数事件**不自行阻断**；特别警告：exit 1 在无 JSON 输出时按非阻断错误处理、动作照常执行——「想让 hook 强制执行策略，用 exit 2」【官方原文语义】。
  - `PostToolUse` 例外：工具已执行完，exit 2 不阻断但把 stderr 喂给 Claude；`Stop` 事件用 `{"decision": "block", "reason": "Test suite must pass before proceeding"}` 可阻止 Claude 收工【官方示例】。
- 配置位置：`.claude/settings.json`（可入库共享）、`~/.claude/settings.json`、插件 `hooks/hooks.json`、subagent frontmatter 内（作用域限该 agent）。三层嵌套：事件 → matcher 组 → handler；matcher 支持 `Edit|Write` 这类精确/管道列表与其他字符触发的 JS regex【官方】。
- 默认 timeout 600 秒；**超时的 hook 输出被丢弃、不产生阻断**——意味着「跑全量测试的门禁 hook 必须控制时长或放宽 timeout」【官方 + 推断】。
- 组合出流水线门禁的配方【推断，基于上述官方语义】：`PostToolUse`（matcher `Edit|Write`）跑快速 lint → exit 2 把违规喂回；环节收尾用 `Stop` hook 跑测试命令，非零退出则 `decision: block`；`.claude/settings.json` 入库即全仓库复用。

#### 1.5 Headless 模式（`claude -p`）——脚本化流水线的执行单元

来源：<https://code.claude.com/docs/en/headless>、<https://code.claude.com/docs/en/cli-reference>【官方】

- 退出码：「`claude -p` 成功退出码 0，run 失败时非零，脚本可按退出状态分支」【官方】。
- 输出：`--output-format text|json|stream-json`；`json` 含 `result`、`session_id`、成本字段；`--json-schema` 强制结构化输出（放 `structured_output` 字段，schema 无效则启动报错）【官方】。
- 无人值守控制：`--permission-prompts none`（无人应答时一律拒绝且不重试）、`--permission-mode dontAsk|acceptEdits|auto`、`--max-turns`、`--max-budget-usd`（含 subagent 消耗）【官方】。
- `--bare`：跳过 hooks/skills/agents/plugins/MCP/CLAUDE.md 自动发现，官方标注「脚本与 SDK 调用推荐，未来将成为 `-p` 默认」；反之**不带 `--bare` 时 `-p` 会执行项目 `.claude/settings.json` 里的 hooks**——流水线门禁 hook 在 headless 下依然生效的依据【官方】。
- 会话链：`--continue` 续最近会话、`--resume <id>` 跨目录按 ID 续——可实现「同会话多步推进」，但流水线场景更建议每环节全新 `-p`（干净上下文）+ 磁盘文件传值【官方 + 推断】。
- 其他：stdin 管道输入上限 10MB（超限非零退出）；SIGTERM 退出码 143；`system/init` 事件里的 `mcp_server_errors`/`plugin_errors` 可让 CI 对「加载失败」直接失败【官方】。

#### 1.6 Claude Agent SDK（Python/TypeScript）——编程式编排

来源：<https://code.claude.com/docs/en/agent-sdk/overview>【官方】

- 定位：把 Claude Code 的工具、agent loop、上下文管理做成库，在自有 Python/TS 进程内运行 Claude Code 二进制。SDK 之外还有 Client SDK（直调 API）与 Managed Agents（Anthropic 托管）两条线【官方】。
- 能力表（官方）：内置工具、Hooks、Subagents、MCP、Permissions、Sessions（resume/fork）、Skills/Commands/Memory、Plugins。
- 仓库：`anthropics/claude-agent-sdk-python` 与 `anthropics/claude-agent-sdk-typescript`（官方 CHANGELOG 链接见 overview 页）。
- 与流水线的关系：可以用 Python 顺序调用五步，每步之间插入任意确定性 Python 判定（subprocess 跑 pytest/mutmut，按返回值决定是否叫下一步、重试还是终止），是「编排代码自由度最高」的版本；代价是要维护一段自有程序【官方能力 + 推断】。注意官方限制：第三方产品不得给基于 Agent SDK 的产品提供 claude.ai 登录【官方】。

### 2. 基于 Claude Code 的社区编排项目

GitHub 检索方法：`gh api search/repositories`，query 分别为 `claude code pipeline in:name,description` 与 `claude code subagents workflow`，按 stars 排序，逐个核对活跃度（2026-10-03）。

#### 2.1 foreman（VisionForge-OU/foreman）——结构上最接近，但已停更

- 定位【README 自述】：「supervises headless Claude Code agents through a _gated_ software-delivery pipeline」；流程 `plan → ADR/PRD → issues → TDD build → e2e`。
- 机制【README 自述】：spawn 本地 `claude` CLI 的 stream-json 模式并解析事件；每 run 强制 turn/成本/时间预算；每个设计阶段有人工 review gate，审批带 hash 封印（文档改动自动失效）；全状态为入库的可读文件（无数据库，崩溃后从磁盘恢复）；并行 worker 各占 git worktree 并以声明式 `touches` 集合防文件冲突；编排器（而非 agent）强制 guardrails——包括一个 `PreToolUse` deny hook 阻止 worker 自己写验证代码（正是「LLM 只修不判」的工程化）。
- 活跃度【GitHub API / PyPI】：444 stars；仓库创建 2026-06-17，**最后 push 2026-06-29**；PyPI `foreman-orchestrator` v0.6.0（2026-06-21 上传）。→ 距调研日约 3 个月无活动，单人项目特征明显。
- 结论【推断】：设计值得抄（hash 封印审批、PreToolUse 禁自证、预算硬停），但作为运行底座风险高。

#### 2.2 obra/superpowers——社区最大的方法论插件，覆盖 ①②⑤ 的大半

- 定位【README 自述】：「a complete software development methodology for your coding agents」，由 composable skills + SessionStart hook 注入的 bootstrap 构成，跨 17 个 coding agent harness（Claude Code、Codex、Cursor、Gemini CLI、OpenCode、Pi 等）。
- 基本工作流【README 自述】：brainstorming（设计成文）→ using-git-worktrees（隔离工作区 + 干净测试基线）→ writing-plans（2–5 分钟粒度任务，含精确文件路径与验证步骤）→ **subagent-driven-development**（每任务派一个全新 subagent + 事后 review，或 inline 执行 + 终审）→ **test-driven-development**（强制 RED-GREEN-REFACTOR：先写失败测试、看它失败、最小实现、看它通过、提交；「删除测试之前写的代码」）→ requesting-code-review（按严重度报告，Critical 阻断推进）→ finishing-a-development-branch（验证测试、merge/PR/丢弃决策）。README 称 skills 为「mandatory workflows, not suggestions」。
- 活跃度【GitHub API】：294,334 stars；最新 release v6.4.2（2026-09-25），last push 2026-09-27；已进 Anthropic 官方插件市场（`/plugin install superpowers@claude-plugins-official`）。
- 与五步的差距【推断】：②（TDD 至绿）与 ①（设计/计划）覆盖好；⑤ 有 review+测试验证但判定仍是「Claude 自觉走 skill」而非退出码；**③ 清理器（lint/复杂度驱动重构）与 ④ 变异测试强化没有对应 skill**；整体是提示层强制，确定性弱于 hooks/脚本门禁。

#### 2.3 github/spec-kit——第 ① 步的现成品

- 定位【README 自述】：SDD（Spec-Driven Development）工具包；`uv tool install specify-cli` + `specify init`，之后在 agent 内依次调用 `/speckit-constitution`、`/speckit-specify`、`/speckit-plan`、`/speckit-tasks`、`/speckit-implement`、`/speckit-converge`，产出规格→技术计划→任务清单并指导实现，`implement → converge` 循环直到报告 Converged。
- 活跃度【GitHub API】：139,806 stars；last push 2026-10-02（极活跃）；支持 Windows/Linux/macOS。
- 结论【推断】：与五步的 ① 高度重合（且其 constitution 概念可用于固化「依赖规则」等 QA 门禁宪法）；③④⑤ 无覆盖。

#### 2.4 ruflo（原 claude-flow，ruvnet）——声量最大，机制与声明需严格区分

- 活跃度【GitHub API】：73,716 stars；仓库已从 `claude-flow` 改名 `ruflo`（`gh api repos/ruvnet/claude-flow` 现返回 `full_name: ruvnet/ruflo`）；v3.51.1 发布于 2026-10-02，几乎每日发版，极活跃。
- 机制【README 自述 + 读取验证】：围绕 Claude Code/Codex 的「执行层」——`npx ruflo init` 脚手架出 `.claude/`、`.claude-flow/`、CLAUDE.md，注入 hooks 系统（自称 27 个 hooks）做任务路由与后台协调；注册 MCP server（自称约 314 个工具）+ CLI daemon + 12 个后台 worker（audit/testgaps 等）；AgentDB（HNSW 向量索引）做跨会话记忆；swarm 拓扑（hierarchical/mesh/adaptive）。
- README 声称 vs 可验证机制【本调研核对】：agent 数量声明内部不一致（同页出现 98 / 100+ / 33+21 等口径）；性能对比（1.3×–1953× 优于 LangGraph/AutoGen/CrewAI）链接指向 gist 与 `perf/` 分支而非主干；**确定性质量门禁（lint/test 退出码强制）没有文档化的机制**——相近的只有 SPARC「quality gates」提法与 `ruflo verify`（字节级完整性校验，非测试门禁）【README 自述 + 推断】。
- 结论【推断】：作为「Claude Code 增强层」活跃度高，但要拿它当确定性流水线底座，缺乏可核实的门禁机制，营销密度高，不建议作为本项目的关键依赖。

#### 2.5 claude-squad（smtg-ai/claude-squad）

- 定位【README 自述】：终端多 agent 会话管理（Claude Code/Codex/OpenCode/Amp），本质是 tmux/窗口级的并行会话编排，无门禁语义。
- 活跃度【GitHub API】：8,560 stars；最新 release v1.0.20（2026-08-20），last push 同日 → 约 6 周无活动，维护放缓。
- 结论【推断】：可作并行多会话的辅助工具，与本流水线的门禁诉求无直接关系。

#### 2.6 其他检索命中（简列）

- `tintinweb/pi-subagents`（1,244 stars）、`QuintinShaw/pi-dynamic-workflows`（551 stars）：Claude Code 式 subagents/workflows 在 **Pi** 这个 agent 上的移植，非 Claude Code 本体【README 自述】。
- `ethanhq/cc-fleet`（214 stars）：让 Claude Code 的 Dynamic Workflows/Agent Teams/Subagents 跑在 DeepSeek/GLM/Kimi 等第三方模型上【README 自述】。
- `shinpr/claude-code-workflows`（687 stars，2026-10-01 仍活跃）：开发流程 skills 集，定位「让宽探索收敛到已批准结果」【README 自述】，未做门禁机制验证。

### 3. 通用多 Agent 编排框架（可实现同样模式，但需自己写编排代码）

#### 3.1 LangGraph（langchain-ai/langgraph）

- 机制【官方 docs，docs.langchain.com/oss/python/langgraph/overview】：自称「low-level orchestration framework and runtime」；`StateGraph` + `add_node` + `add_edge(START, ...)` + `compile()` + `invoke()`；官方能力声明包括「在同一张图里混合 hand-coded 确定性步骤与 LLM 驱动的 agentic 步骤」、持久化（failure 后可恢复）、human-in-the-loop（interrupts）、长时运行。
- 门禁嵌入【推断，基于官方能力】：门禁就是普通 Python 节点（subprocess 跑测试并按结果走 conditional edge），这是四个框架里对「确定性节点 + LLM 节点混合」表达最直白的。
- 活跃度【GitHub API】：42,616 stars；MIT；last push 2026-10-02。
- 与 Claude Code 工作流的关系【推断】：替代关系——用自己的 agent loop 换掉 Claude Code 的；LangChain 的 Deep Agents 在其上提供 planning/subagents/filesystem。

#### 3.2 CrewAI（crewAIInc/crewAI）

- 机制【官方 docs，docs.crewai.com/concepts/flows】：Crew = 角色化 agent 团队（Crew 级 sequential/hierarchical process）；**Flow** = 事件驱动工作流，装饰器 `@start()`（可多入口/带标签条件）、`@listen()`（监听上游输出）、`@router()`（方法返回标签决定分支）、`or_`/`and_` 组合、`@persist`（默认 SQLiteFlowPersistence，支持 `kickoff(restore_from_state_id=...)` 恢复）；结构化状态用 `Flow[PydanticState]`；agent 输出校验用 `response_format=<Pydantic 模型>` 读 `result.pydantic`。
- 门禁嵌入【推断】：Flow 方法就是普通 Python——crew 调用之间插任意确定性代码/子进程完全自然；Pydantic 结构化输出做契约校验。
- 活跃度【GitHub API】：59,285 stars；MIT；v1.15.23（2026-09-28）。
- 关系【推断】：替代关系；相比 LangGraph 更「角色叙事」，五步流水线用 Flow 的顺序 `@listen` 链即可表达。

#### 3.3 AG2（ag2ai/ag2，原 AutoGen）

- 机制【官方 docs 首页 docs.ag2.ai 实读】：自称「The Open-Source AgentOS」；文档列出的核心概念为 Agents、models、tools、structured output，进阶概念为 **Multi-agent networks、subagents、middleware**，另有 Evaluation（「Score, compare, and regression-test your agents」）。本次未深入验证其具体编排 API 细节（文档首页未展开，深链未逐页核实）【官方 + 说明】。
- 活跃度【GitHub API】：4,973 stars（四者中最小）；Apache-2.0；v1.1.1（2026-09-29），last push 2026-10-02，仍活跃。
- 结论【推断】：可实现，但社区体量与文档厚度弱于前两者，本项目场景无明显增量。

#### 3.4 OpenAI Agents SDK（openai/openai-agents-python）

- 机制【官方 docs，openai.github.io/openai-agents-python】：原语为 `Agent`（LLM + instructions + tools，内建跑到完成的小循环）、`Runner.run_sync(agent, prompt)`、`result.final_output`；**handoffs** 让 agent 间移交控制权；**guardrails**「对 agent 输入/输出做校验，与 agent 执行并行跑，不通过即 fail fast」，API 参考另有 Tool guardrails（工具调用级检查）；Sessions 提供跨请求工作记忆（SQLAlchemy/SQLite/Redis/Mongo 等变体）；内建 tracing。
- 门禁嵌入【推断】：guardrail + 严格 schema（Pydantic）输出是天然挂点；但门禁「跑测试看退出码」仍需自己写工具函数（`@function_tool` 类机制）。
- 活跃度【GitHub API】：29,800 stars；MIT；v0.23.1（2026-10-02）——版本仍处 0.x，API 稳定性弱于 1.x 的 CrewAI/LangGraph 生态位【推断】。
- 关系【推断】：OpenAI 生态优先；除非刻意多供应商，否则对本仓库（Claude 订阅 + Claude Code 工作流）无必要性。

### 4. CI 平台层

#### 4.1 GitHub Actions + anthropics/claude-code-action（官方）

- 机制【官方 docs，code.claude.com/docs/en/github-actions】：两种模式——interactive（等 `@claude` mention）与 automation（workflow 传 `prompt` 输入即自动执行）；`claude_args` 可透传任意 CLI 参数（`--max-turns`、`--model`、`--allowedTools`、`--mcp-config`）；`prompt` 可直接是 skill 调用；触发前有写权限与「人类触发者」双重检查（防 bot 循环）；支持 Bedrock/Vertex/Foundry 与 OIDC 联邦免静态密钥。
- 活跃度【GitHub API】：9,361 stars；v1.0.239（2026-10-01），极活跃。
- 承载流水线评估【推断】：适合承载**外环**——PR 触发的 ⑤ QA 门禁（跑依赖规则/全量测试/覆盖率并按结论回帖或 fail check）；内环 ①→④ 需要「分钟级反馈 × 多次迭代」，放 CI 每圈排队 + 计费不划算。
- 另注：官方文档已有配套的 **GitLab CI/CD 页**（beta，由 GitLab 维护支持）：在 `.gitlab-ci.yml` 的 job 里装 CLI 后直接 `claude -p "${AI_FLOW_INPUT:-...}" --permission-mode acceptEdits`，支持 Bedrock/Vertex 的 OIDC 模板【官方】——若公司 GitLab 场景要用 Claude Code 跑门禁 job 有现成模板。

---

## c. 对比表

| 工具 | 类型 | 开箱程度 | 上下文隔离机制 | 确定性门禁支持 | 语言生态 | 维护状态（2026-10-03） |
| --- | --- | --- | --- | --- | --- | --- |
| Claude Code subagents | CLI 原生 | ★★★★（写 md 即得） | 每个 subagent 独立 context window【官方】 | 间接：靠 hooks（exit 2/Stop block）+ 外层脚本 | CLI/Python/TS SDK | v2.1.287，日更 |
| Claude Code Dynamic Workflows | CLI 原生 | ★★★★（说一句话生成脚本） | 每个 agent() 独立上下文，中间结果存脚本变量【官方】 | 中：schema 结构化输出；脚本自身无 shell，硬门禁需 hooks/外层【官方】 | 同上 | 同上 |
| claude -p 脚本链 | 自建 | ★★（要写脚本） | 每次 `-p` 全新会话=最强隔离【官方】 | **强**：进程退出码 + `--json-schema` + 门禁命令退出码全在脚本侧【官方】 | bash/PowerShell/任意 | 自有 |
| Claude Agent SDK | 官方库 | ★★★ | 同 Claude Code 语义（SDK 复用其二进制）【官方】 | 强：宿主语言里任意 if/subprocess | Python/TypeScript | 官方维护，双仓库 |
| foreman | 社区编排器（Python TUI） | ★★★（`foreman init` 即用） | headless `claude` 每 run 独立 + worktree 隔离【README 自述】 | 设计上强（预算硬停、PreToolUse 禁自证、hash 审批）【README 自述，未实测】 | Python | **停更 ~3 个月**（v0.6.0，2026-06-29） |
| obra/superpowers | 社区插件（skills） | ★★★★★（官方市场一键装） | 每任务派全新 subagent【README 自述】 | 弱：提示层强制，无退出码判定【推断】 | agent 无关（17 harness） | 极活跃（v6.4.2，2026-09-25） |
| github/spec-kit | 社区工具包（CLI+skills） | ★★★★ | 每步由人在 agent 内逐个调用，非自动隔离【README 自述】 | 无内建（converge 报告由 LLM 产）【README 自述】 | agent 无关 | 极活跃（2026-10-02） |
| ruflo（ex-claude-flow） | 社区插件/MCP | ★★★ | swarm/多 agent，机制不透明【README 自述】 | 未文档化【核对结论】 | Node.js | 极活跃（v3.51.1，2026-10-02） |
| claude-squad | 社区终端多会话 | ★★★ | tmux 级会话隔离【README 自述】 | 无 | Go | 放缓（v1.0.20，2026-08-20） |
| LangGraph | 通用框架 | ★★（全自写） | 图节点共享 state；subgraph 可隔离 | 强：确定性节点随意插 | Python（TS 版存在） | 活跃（2026-10-02） |
| CrewAI | 通用框架 | ★★★ | Crew/Flow 各自上下文；Flow 事件驱动 | 强：Flow 步骤即 Python；Pydantic 校验 | Python | 活跃（v1.15.23，2026-09-28） |
| AG2 | 通用框架 | ★★ | 未深入验证（文档首页见 subagents/networks/middleware 概念） | 可实现（细节未核实） | Python | 活跃（v1.1.1，2026-09-29） |
| OpenAI Agents SDK | 通用框架 | ★★★ | 每 Agent 独立循环 | 中强：guardrails fail-fast + 严格 schema | Python（TS 版存在） | 活跃（v0.23.1，2026-10-02，0.x） |
| claude-code-action（GH Actions） | 官方 CI 集成 | ★★★★ | CI job 内全新会话 | 强（CI 本身是退出码世界）+ `claude_args` | YAML | 极活跃（v1.0.239，2026-10-01） |
| GitLab CI/CD 集成 | 官方（GitLab 维护，beta） | ★★★ | CI job 内全新会话 | 同上 | YAML | beta，官方文档在册 |

---

## d. 落地建议（Windows 11 + Claude Code + Python/TypeScript/Go 多项目）

### 方案 A（推荐主线）：`.claude/agents/` 五个 subagent + 脚本链驱动 `claude -p` + hooks 兜底

结构（全部落在各子项目自己的 `.claude/` 与 `.pipeline/` 中，符合本仓库「一目录一项目、互不关联」原则）：

```
<project>/
├── .claude/
│   ├── agents/
│   │   ├── spec-writer.md      # ① tools: Read,Glob,Grep,Write
│   │   ├── coder.md            # ② tools: Read,Edit,Write,Bash（acceptEdits）
│   │   ├── cleaner.md          # ③ tools: Read,Edit,Bash（只许跑 lint/format/测试）
│   │   ├── hardener.md         # ④ tools: Read,Edit,Write,Bash
│   │   └── qa-gate.md          # ⑤ tools: Read,Glob,Grep,Bash（只跑检查，不改码）
│   └── settings.json           # hooks：PostToolUse(Edit|Write)→快速 lint；Stop→收尾门禁
├── .pipeline/
│   ├── run.ps1（或 uv run .pipeline/run.py）   # 编排：顺序调用五步
│   └── gates/                                  # 确定性判定脚本（退出码说话）
└── specs/  build/                              # 环节间磁盘契约
```

五步映射与「LLM 只修不判」的落点：

1. **① 规格定义器**：`claude -p --agents ... --json-schema '<要求输出 feature 名与文件清单的 schema>'`，产出 Gherkin `.feature` 与测试骨架到 `specs/`。判定=脚本校验 schema 与文件存在性，与 LLM 无关。
2. **② 编码器**：`claude -p "按 specs/ 实现至 pytest/vitest/go test 全绿" --allowedTools "Read,Edit,Write,Bash"`；门禁=编排脚本直接跑 `uv run pytest` / `pnpm vitest run` / `go test ./...`，看退出码决定放行或回炉（重试次数封顶）。
3. **③ 清理器**：跑 `ruff check --fix` / `eslint --fix` / `golangci-lint run --fix` 生成报告文件 → 让 cleaner 只按报告重构 → 门禁=lint 退出码 + 复杂度阈值（radon / `golangci-lint` 复杂度 linter / 自定脚本）。
4. **④ 强化器**：跑 mutmut（Python）/ Stryker（JS/TS）/ go-mutesting 系工具产出变异报告 → hardener 只补测试 → 门禁=mutation score 阈值脚本判定（阈值写在确定性脚本里）。
5. **⑤ QA 门禁**：依赖规则用 import-linter（Python）/ dependency-cruiser（TS）/ arch-go 或 depguard 规则（Go）+ 全量测试 + coverage（`coverage report --fail-under` / vitest `coverage.thresholds` / go 覆盖率脚本）——三者全是退出码/阈值判定，qa-gate subagent 只负责「看失败报告→修」，不允许宣布通过。

要点：

- 环节间一律磁盘传值（`specs/`、`build/report-*`），每步全新 `-p` 会话，不 `--continue`——干净上下文由「不续会话」保证，最简单也最硬【推断】。
- hooks 兜底入 `.claude/settings.json`：`Stop` hook 跑测试，非零则 `{"decision":"block"}`；`PostToolUse` 快速 lint 用 exit 2 回喂【官方语义组合】。注意 `claude -p` 不带 `--bare` 时项目 hooks 会执行——门禁在 headless 下依然生效【官方】；timeout 按最慢测试命令放宽【官方：默认 600s，超时输出丢弃且不阻断】。
- Windows 注意：hooks 命令写成 Python 单文件（PEP 723 + `uv run`，符合本仓库 `.scripts` 约定，避免 ps1/bat）；agent teams 的 split-pane 不支持 Windows Terminal（本方案不依赖 teams，无碍）【官方】；流水线中间产物放项目内 `.pipeline/build/` 并 gitignore，不落入外部目录（遵循仓库数据文件强约束）。
- 工作量：5 个 agent md（半天）+ 编排脚本与门禁（1 天）+ hooks（半天）。

### 方案 B（零基建起步）：Dynamic Workflow 直跑五步

直接对 Claude 说：「use a workflow to: 1) write Gherkin specs from <需求>, 2) implement until pytest passes, 3) refactor per ruff report, 4) add tests until mutation score ≥ X, 5) run import-linter + full tests + coverage, with a gate agent verifying each gate」→ 满意后 `/workflows` 里按 `s` 存为 `/pipeline`，以后一条命令复跑【官方流程】。

- 优点：零脚本基建，天生并行、可恢复、token 可视。
- 限制：workflow 脚本自己不能跑 shell【官方】，每个门禁是「一个只跑命令的 agent + schema 回传结果」，判定逻辑虽在命令里但「结果是否如实回传」多经一层 LLM；硬闸仍建议在 ⑤ 之外再叠 CI 或本地脚本。适合先验证流程价值，再固化为方案 A。

### 方案 C（复用社区）：superpowers + 自补两环

`/plugin install superpowers@claude-plugins-official` 拿到 ①设计/计划、②subagent-driven-development + TDD、review 收尾；自写 `cleaner`/`hardener` 两个 skill + 一个 Stop 门禁 hook 补 ③④⑤【README 自述 + 推断】。适合想要「设计-计划-执行」的完整方法论而不只想跑流水线的日常开发；门禁确定性仍弱于方案 A。

### 方案 D（观察与借鉴）：foreman

不作为底座（停更 ~3 个月、单人项目）【GitHub API】，但其「编排器强制 guardrails、PreToolUse 禁止 worker 自写验证、hash 封印审批、全状态磁盘文件」是方案 A hooks 设计的直接参考。

### 外环：CI 门禁

GitHub 仓库加 `anthropics/claude-code-action@v1` + `prompt`（automation 模式）做 PR 级 ⑤ 复核，`claude_args` 传 `--max-turns` 控成本【官方】；公司 GitLab 场景按官方 GitLab CI/CD 页模板起 job【官方】。注意：最终判定仍应以 CI 里直接跑的确定性检查为准，Claude 只做「修 + 写说明」。

### 风险与边界声明

- 本文所有版本号、星数、release 日期为 2026-10-03 快照，Claude Code 处于日更状态，机制（尤其 workflows/hooks 语义）可能随后续版本调整，采用前建议复核对应官方页。
- 【README 自述】类结论（foreman/superpowers/ruflo 的能力清单）均未经本机实测，仅核对了仓库活跃度与文本机制描述；【推断】为机制推演，落地时应以最小实验验证（如先用方案 B 跑一个 toy 仓库）。
