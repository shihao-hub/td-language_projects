# 「未来的一切都是 CLI or MCP」与「Unix 思想焕发新生」——一手资料调研

> 调研日期：2026-10-02
> 调研对象：Model Context Protocol（规范 2024-11-05 → 2026-07-28 全部 revision）、Anthropic 工程博客与 Claude Code 文档、OpenAI Codex CLI / Gemini CLI / opencode / Aider / goose 官方文档、AGENTS.md 与 Agent Skills 规范、Unix 哲学原始文本、Terminal-Bench / SWE-bench / τ-bench / ToolLLM / API-Bank / ReAct / SWE-agent / Voyager 等论文，以及 2025—2026 年关于 MCP 成本与安全的实证论文
> 一手来源口径说明：本文只把**官方规范原文、官方仓库源码/README 原文、官方文档与工程博客原文、arXiv/会议论文原文、CLI `--help` 级文档原文**计为证据；媒体报道、知乎/公众号总结、第三方博客一律只作为线索（D 级），并在引用处显式标注。**所有 URL 均在 2026-10-02 实际抓取成功后才写入**；抓不到的一律写「未找到来源，属推断」，不做二次转述。证据分级：**A** 一手代码/规范/CLI 文档原文；**B** 厂商官方文档/工程博客；**C** 论文/基准（有可复现实验）；**D** 媒体/二手总结（仅线索）；**U** 未证实（找不到来源，显式标注为推断）。
> 来源校验：本文 70 条来源已于 2026-10-02 经**独立对抗性校验**（逐条 GET 原文、比对页面标题与标签、关键论据原句逐字深核）：70/70 可达，69 条标签一致，1 条机构错挂已修（原第 67 条把 Cloudflare 工程博客标成 Anthropic），8 条 URL 漂移已按实际落点更新，5 组关键论据 17 个原句全部逐字命中。校验后已修正的取证瑕疵见 §8 第 1 项。
> 记号约定：**事实**直接陈述；**推断：**开头为推断；**观点：**开头为观点。每条结论后附 `【等级】` 与来源编号。

---

## 1. 结论速览

### 1.1 对两个原始问题的正面回答

**问题一：「未来的一切都是 CLI or MCP」成立吗？——作为事实描述不成立（全称命题为假），作为趋势描述部分成立。**

事实层面，CLI 与 MCP 不在同一抽象层：CLI 是**进程 + 文本接口的实现形态**，MCP 是**能力接入的协议与消息格式**【A】[[15]](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。2026-07-28 版 MCP 规范把协议改成「无状态、每请求携带版本与能力」的请求/响应模型后，MCP 在一次调用的形状上已经非常接近「把远程 CLI 包成 HTTP 端点」，二者是**可互相封装的两个层**，而不是互斥的两个选项【A】[[7]](https://modelcontextprotocol.io/specification/2026-07-28/changelog)。

更关键的是：**有受控实验直接否证了「必须 MCP」**。arXiv 2608.08654 在固定任务上跑了 7 个 agent 脚手架 × 5 个模型，结论原文：「Two of the seven ship no MCP support at all; they completed every run using only the CLI, which shows that MCP is unnecessary for this class of work, and they were 5.0x to 28x cheaper than the five scaffoldings that do support MCP」【C】[[1]](https://arxiv.org/abs/2608.08654)。同一篇论文还发现「thirteen strictly paired MCP-to-CLI ratios span 0.43x to 29x」——**同一对接口的成本比在不同脚手架间能差两个数量级**，说明这个比较本身不稳定。

**问题二：「Unix 思想焕发新生」成立吗？——部分成立：3 条被继承、2 条被打破、1 条属于「讲得像但无证据」。**

| Unix 哲学要素 | 在 agent 工具使用中的实际状态 | 结论 | 等级 |
|---|---|---|---|
| 文本流是通用接口 | 被继承且被强化：所有 agent CLI 都提供 `--output-format json/stream-json`，把「文本流」升级为「带 schema 的文本流」 | ✅ 继承（并升级） | A |
| 组合小工具解决问题 | 被继承：Skills 明确要求「脚本执行而不进上下文」；Anthropic 建议把 10,000 行表格在代码里过滤后再 `console.log` 5 行 | ✅ 继承 | B |
| 一切皆文件（作为统一抽象） | 被继承为**上下文的文件系统化**：Skills 三级渐进披露、MCP 工具以文件形式暴露、Claude Code 用 Bash 读文件而非入库 | ✅ 继承 | B |
| 工具小而专一 | **被打破**：官方明确说「More tools don't always lead to better outcomes」，并建议合并工具、用 `search_logs` 取代 `read_logs` | ❌ 打破 | B |
| 输出对人类可读、简洁即美 | **被打破**：agent 需要结构化契约与稳定字段；MCP 反过来把工具返回值形式化为 `structuredContent` + JSON Schema | ❌ 打破 | A |
| 「Unix 哲学的复兴解释了 CLI/MCP 之争」 | 只有**类比性论文**（position/essay 型），没有实验证据把「Unix 哲学」当作自变量测过任何 agent 指标 | ⚠️ 讲得像但无证据 | U（推断） |

**一句话总结**：真正决定 agent 成败的不是「用 CLI 还是用 MCP」，而是**脚手架（scaffolding）+ 上下文预算管理 + 接口契约设计**这三件事；Unix 思想在其中确实复活了，但复活的是「组合与文本流」，不是「工具越小越好」。

### 1.2 命题逐条判定速览

| # | 原始断言（拆解后） | 判定 | 关键依据 |
|---|---|---|---|
| 1 | 未来一切工具接口都会是 CLI 或 MCP | 不成立（全称）/ 部分成立（趋势） | 无 MCP 的脚手架完成了全部任务 [[1]](https://arxiv.org/abs/2608.08654) |
| 2 | 研究「AI 怎么使用 CLI 解决问题」是关键 | 成立（且已被实证：scaffolding 是主导变量） | [[1]](https://arxiv.org/abs/2608.08654) |
| 3 | 「为什么想到这个命令」可被研究 | 成立，且已有量化：工具数 >10~15 时选择准确率 <90% | [[2]](https://arxiv.org/abs/2606.30317) |
| 4 | 「拿到结果又做什么」是核心循环 | 成立：ReAct 的 interleaved reasoning/acting 即此循环 | [[3]](https://arxiv.org/abs/2210.03629) |
| 5 | Unix 思想焕发新生 | 部分成立（见 1.1 表） | [[4]](https://arxiv.org/abs/2601.11672) |

---

## 2. 命题拆解：可验证断言 vs 含混修辞

原始命题：「未来的一切都是 cli or mcp，那么研究 ai 怎么使用这些 cli 组织解决问题才是关键。比如为什么想到这个命令、拿到命令结果又做什么……所以 unix 思想焕发新生?」

| 片段 | 类型 | 问题所在 | 可验证化后的表述 | 判定 | 等级 |
|---|---|---|---|---|---|
| 「未来的一切都是 cli or mcp」 | 含混修辞（全称 + 二分） | 「一切」指工具、产品、协议还是交互形态？CLI 与 MCP 不是同一范畴，无法二分 | 「AI agent 的可调用能力是否将主要通过 CLI 进程或 MCP 服务暴露」 | 部分成立：两者都是主流，但不排他（HTTP API、SDK、in-process 函数仍在用） | A |
| 「研究 ai 怎么使用这些 cli 组织解决问题才是关键」 | 价值判断 + 可验证方向 | 「才是关键」不可证；但「什么决定成功率」可测 | 「在固定任务上，接口类型 vs 脚手架，哪个是成本/成功率的主导变量」 | 成立：**脚手架主导**，接口次之且不稳定 | C |
| 「为什么想到这个命令」 | 可验证 | 需要用 tool selection / planning 指标 | 「工具数量与描述如何影响模型选择正确率」 | 成立，已有数字 | C |
| 「拿到命令结果又做什么」 | 可验证 | 需要用 agent loop / observation 处理指标 | 「observation 如何反馈进下一轮决策」 | 成立（ReAct/ACI） | C |
| 「所以 unix 思想焕发新生?」 | 疑问句（要求正面回答） | 因果被当作既定前提 | 「Unix 哲学的各条规则，在 agent 工具设计中分别被继承/打破/未被检验」 | 见 §1.1、§4 | B/U |

**推断：**「cli or mcp」这个写法本身暴露了一个层混淆——把「协议」和「实现形态」并列成互斥选项。把它改成「能力暴露面（协议）× 运行时（进程/沙箱）× 上下文预算 × 治理」四层模型后，原命题里的困惑基本自动消解（见 §5）。

---

## 3. MCP：它到底解决了什么

### 3.1 事实基线（A1）

**发布**：2024-11-25，Anthropic 开源。原始公告原文：「Today, we're open-sourcing the Model Context Protocol (MCP), a new standard for connecting AI assistants to the systems where data lives」，并注明「MCP was created at Anthropic by David Soria Parra and Justin Spahr-Summers」【A/B】[[5]](https://www.anthropic.com/news/model-context-protocol)。

**规范迭代历史**（以官网 revision changelog 为准）：

| Revision | 关键变更（官方 changelog 摘要） | 日期/状态 |
|---|---|---|
| 2024-11-05 | 首版；HTTP+SSE 传输；`initialize` 握手 + 会话 | Final |
| 2025-03-26 | 新增 OAuth 2.1 授权框架（PR #133）；**HTTP+SSE 被 Streamable HTTP 取代**（PR #206）；新增 JSON-RPC batching（PR #228）；新增 tool annotations（PR #185） | Final |
| 2025-06-18 | 移除 batching；新增 structured tool output；MCP server 被归类为 OAuth Resource Server；要求客户端实现 RFC 8707 Resource Indicators；新增 elicitation；新增 resource links；要求 `MCP-Protocol-Version` 头 | Final |
| 2025-11-25 | OIDC Discovery；icons 元数据；增量 scope 同意；工具命名指引；URL 模式 elicitation；sampling 支持 `tools`/`toolChoice`；**OAuth Client ID Metadata Documents**；**tasks 实验特性**；工具输入校验错误应作为 Tool Execution Error 返回以支持模型自我纠正（SEP-1303）；确立 JSON Schema 2020-12 | Final |
| 2026-07-28 | **移除协议级会话与 `Mcp-Session-Id`**；**移除 `initialize` 握手，改为每请求 `_meta` 携带版本与能力**；新增 `server/discover`；用 `subscriptions/listen` 取代 GET 端点与 `resources/subscribe`；移除 `ping`/`logging/setLevel`/`notifications/roots/list_changed`；tasks 移出核心成为官方扩展；引入 MRTR（多轮往返请求）；所有结果新增必需 `resultType`；移除 SSE 可恢复性（`Last-Event-ID`）；**弃用 Roots、Sampling、Logging**；将 HTTP+SSE 正式重分类为 Deprecated；弃用 OAuth DCR（RFC 7591）改用 Client ID Metadata Documents；结果新增 `ttlMs`/`cacheScope` | **Current** |

来源：官网 Versioning 页明确「The **current** protocol version is 2026-07-28」【A】[[6]](https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning.md)；各 revision 的 Key Changes【A】[[7]](https://modelcontextprotocol.io/specification/2026-07-28/changelog)[[8]](https://modelcontextprotocol.io/specification/2025-11-25/changelog)[[9]](https://modelcontextprotocol.io/specification/2025-06-18/changelog)[[10]](https://modelcontextprotocol.io/specification/2025-03-26/changelog)。

> 注意一个容易踩的坑：2025—2026 年中文材料里大量说法仍停留在 2025-06-18 版语境（有 `initialize`、有会话、有 Roots/Sampling）。**截至 2026-10-02，这三样在最新规范里都已是 Deprecated 或已移除。**

### 3.2 传输演进：为什么从 HTTP+SSE 走到 Streamable HTTP（A2）

原提案 PR 标题即 **[RFC] Replace HTTP+SSE with new "Streamable HTTP" transport**，2025-03-17 提交、**2025-03-24 合并**。PR 正文给出的动机原文：「Remote MCP currently works over HTTP+SSE transport which: Does not support resumability / Requires the server to maintain a long-lived connection with high availability / Can only deliver server messages over SSE」，收益第一条是「**Stateless servers are now possible**」【A】[[11]](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/206)。

更早的争论留在 discussion #102。其中一句被反复引用的判断是：「I agree that looking in the ecosystem today it seems like **>90% of all MCP servers are doing stateless things** that do not require subscriptions or ongoing connections. Most of them are tools or prompts.」【A】[[12]](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/102)

到 2026-07-28，HTTP+SSE 被正式纳入弃用登记（PR #2596），且 Streamable HTTP 自身也去掉了 SSE 断线重放：「Remove SSE stream resumability and message redelivery (the `Last-Event-ID` header and SSE event IDs)… A broken response stream loses the in-flight request」【A】[[7]](https://modelcontextprotocol.io/specification/2026-07-28/changelog)。

**无状态化（SEP-2575）的官方理由**，PR 正文原文：「The current MCP specification requires a mandatory initialization handshake that establishes persistent session state. This creates significant challenges for **scalability (load balancing requires sticky sessions), resilience (server failure loses session state), and implementation complexity (both client and server must manage session lifecycles)**.」该 PR 于 2026-05-11 合并【A】[[13]](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)。

Claude 官方博客同步确认：「The latest spec **moves MCP to a stateless core**, while hardening authorization and graduating official extensions」「MCP moves from a bidirectional stateful protocol to a request/response model. Servers can now deploy on serverless and edge infrastructure.」【B】[[14]](https://claude.com/blog/bringing-mcp-2026-07-28-to-claude)

**结论**：MCP 用两年时间，把自己从「有状态长连接协议」改造成「无状态请求/响应协议」——这正是官方对「复杂度代价」的一次公开回应（见 §8）。

### 3.3 工具发现机制（A3）

规范原文（2026-07-28，server/tools）：

- 能力声明：支持工具的 server **MUST** 声明 `tools` capability，`listChanged` 指示是否会发出列表变更通知【A】[[15]](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)。
- `tools/list` 的硬约束：「Servers that declare the `tools` capability **MUST** respond to `tools/list` requests with the set of tools currently available to the requesting client. This set **MAY** be empty and **MAY** change over time… but **MUST NOT** vary per-connection or as a side effect of other requests on the connection.」
- 排序：server **SHOULD** 返回确定性顺序——官方理由写得很直白：「to enable client-side caching and improve **LLM prompt cache hit rates**」。
- 分页与缓存：`tools/list` 支持 pagination，结果带 `nextCursor`；新增 `ttlMs` 与 `cacheScope` 两个必需字段（通过 `CacheableResult` 接口），`ttlMs` 是新鲜度提示、`cacheScope` 决定共享中介能否缓存。
- 变更通知：声明了 `listChanged` 的 server **SHOULD** 向已打开订阅的客户端发送 `notifications/tools/list_changed`。
- 安全兜底：「For trust & safety and security, there **SHOULD** always be a human in the loop with the ability to deny tool invocations.」

**关于「工具数量 / 上下文膨胀」是否有官方提示：规范本身没有给出工具数量上限或「请保持工具数少」的提示。** 它给的是**机制性设计**（分页、`ttlMs`/`cacheScope` 缓存字段、确定性排序保护 prompt cache、`listChanged` 增量更新）。把「工具太多会挤爆上下文」讲清楚的是**工程博客**而不是规范：Anthropic 的 Tool Search 博文把 5 个 server 的工具数换算成 token，见 §3.5。

### 3.4 治理与采用（A4）

**2025-12-09，MCP 被捐赠给 Linux Foundation 下新成立的 Agentic AI Foundation（AAIF）。** Anthropic 公告原文：「we're donating the Model Context Protocol (MCP) to the Agentic AI Foundation (AAIF), a **directed fund under the Linux Foundation**, co-founded by Anthropic, Block and OpenAI, with support from Google, Microsoft, Amazon Web Services (AWS), Cloudflare, and Bloomberg.」并给出规模数字：「There are now **more than 10,000 active public MCP servers**」「adopted by ChatGPT, Cursor, Gemini, Microsoft Copilot, Visual Studio Code」「**97M+ monthly SDK downloads** across Python and TypeScript」【B】[[16]](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)。

Linux Foundation 新闻稿（2025-12-09，旧金山）标题即：「Linux Foundation Announces the Formation of the Agentic AI Foundation (AAIF), Anchored by New Project Contributions Including **Model Context Protocol (MCP), goose and AGENTS.md**」，并把 MCP 描述为「Anthropic's MCP, Block's goose, and OpenAI's AGENTS.md」；Platinum 成员含 AWS、Anthropic、Block、Bloomberg、Cloudflare、Google、Microsoft、OpenAI【A/B】[[17]](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)。同页还给出 OpenAI 方原话（Nick Cooper, Member of the Technical Staff）与 Google 方原话，可作为「官方采用」的一手引述。

规范官网 governance 页进一步固定法律主体为「**Model Context Protocol a Series of LF Projects, LLC**」，技术治理为 Lead Maintainers（BDFL）+ Core Maintainers + Maintainers + Contributors，当前 Lead Maintainers 为 David Soria Parra 与 Den Delimarsky，Justin Spahr-Summers 为「Co-Inventor, Lead Maintainer Emeritus」【A】[[18]](https://modelcontextprotocol.io/community/governance)。

**官方 Registry 现状**：页面顶部明确「The MCP Registry is currently in **preview**. Breaking changes or data resets may occur before general availability.」，由 Anthropic、GitHub、PulseMCP、Microsoft 等支撑；定位是「official centralized metadata repository」，且**不支持私有 server**，安全性依赖命名空间验证（reverse DNS）而非代码扫描【A】[[19]](https://modelcontextprotocol.io/registry/about)。

### 3.5 代价与实测数据（B1/B2/B4）

| 数据类型 | 具体数字（原文） | 来源 | 等级 |
|---|---|---|---|
| Token 节省 | 工具按文件系统渐进加载后「reduces the token usage from **150,000 tokens to 2,000 tokens—a time and cost saving of 98.7%**」 | Anthropic Code execution with MCP [[20]](https://www.anthropic.com/engineering/code-execution-with-mcp) | B |
| 工具定义占用 | 「GitHub: 35 tools (~26K tokens) / Slack: 11 tools (~21K) / Sentry: 5 (~3K) / Grafana: 5 (~3K) / Splunk: 2 (~2K)」→「That's **58 tools consuming approximately 55K tokens** before the conversation even starts」；「At Anthropic, we've seen tool definitions consume **134K tokens** before optimization」 | Anthropic Advanced tool use [[21]](https://www.anthropic.com/engineering/advanced-tool-use) | B |
| Tool Search 效果 | 「Only the Tool Search Tool loaded upfront (~500 tokens)」→「Total context consumption: **~8.7K tokens, preserving 95% of context window**」「an **85% reduction** in token usage」；准确率「Opus 4 improved from **49% to 74%**, and Opus 4.5 improved from **79.5% to 88.1%**」 | 同上 | B |
| Programmatic Tool Calling | 「Average usage dropped from **43,588 to 27,297 tokens, a 37% reduction**」；知识检索「**25.6% → 28.5%**」 | 同上 | B |
| 企业网关实测 | PayPal 生产环境 SCOUT：「reduces MCP tool-token consumption from **140.2k tokens (70.1% of context) to 1.3k tokens (0.8%), a 99% reduction**」 | arXiv 2608.23992 [[22]](https://arxiv.org/abs/2608.23992) | C |
| 工具数 vs 准确率 | 「tool-selection accuracy drops below 90% **between 10 and 15 tools** per context for Claude Haiku 4.5 and **between 20 and 30 tools** for Sonnet 4」 | arXiv 2606.30317 [[2]](https://arxiv.org/abs/2606.30317) | C |
| 上下文饱和机制 | 「eager tool loading saturates context, execution errors compound over time」 | arXiv 2603.06713 [[23]](https://arxiv.org/abs/2603.06713) | C |

**关于性能/延迟/鉴权复杂度的批评与官方回应**（B4）：

- **官方自认复杂度**：SEP-2575 动机段（见 §3.2）直接把「sticky sessions、server failure 丢状态、客户端与服务器都要管会话生命周期」列为问题【A】[[13]](https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575)。
- **社区批评（原始文本）**：discussion #102 中有参会者写道「The burden of integration for MCP is largely on the server developers - and expecting them to not only create a new set of endpoints but to run their software in an entirely different way (requiring long-running servers) **feels absurd to me**」；另有实现者列举 SSE 在 serverless 下的三个具体问题：「Connection Instability… Scaling Challenges… Browser Connection Limits（**6** per browser and domain）」【A】[[12]](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/102)。
- **鉴权复杂度的官方回应路径**：2026-07-28 做了三件事——弃用 OAuth DCR 改用 Client ID Metadata Documents、要求校验 RFC 9207 的 `iss`、要求凭证按 issuer 绑定且不得跨授权服务器复用【A】[[7]](https://modelcontextprotocol.io/specification/2026-07-28/changelog)。

**观点：**综合看，MCP 的代价不是「协议设计糟糕」，而是「**它把工具定义这一项成本显式化并集中到了上下文里**」。MCP 之前，工具成本散落在各家私有集成里看不见；MCP 之后，它变成可测量的 token 账单——所以「MCP 很贵」的抱怨，一半是协议问题，一半是**成本终于被看见**。

### 3.6 工业界的替代方案原文（B3）：不要把工具定义塞进上下文

这三条是「MCP 工具调用范式」的公开替代路线，全部有官方原文。

**① Cloudflare — Code Mode: the better way to use MCP（2025-09-26，作者 Kenton Varda / Sunil Pai）**【A（厂商工程博客）】[[67]](https://blog.cloudflare.com/code-mode/)

Cloudflare 从 token 机制层面解释了工具调用为什么代价高：「The special tokens used in tool calls are things LLMs have **never seen in the wild**. They must be specially trained to use tools, based on synthetic training data. **They aren't always that good at it.** If you present an LLM with too many tools, or overly complex tools, it may struggle to choose the right one or to use it correctly.」——中文：工具调用所用的 special token 是模型在自然语料里从未见过的，必须靠合成数据专门训练；**模型对工具调用的天生能力弱于写代码**，工具越多越复杂，选错用错的概率越高。

它的做法是让模型**写代码**而不是逐个发工具调用，并在隔离环境中执行：「In Code Mode, we **prohibit the sandboxed worker from talking to the Internet**. The global `fetch()` and `connect()` functions throw errors.」「In Code Mode, we give the sandbox access to **bindings representing the MCP servers** it is connected to.」「An additional benefit of bindings is that they **hide API keys**.」沙箱成本方面以 V8 isolate 替代容器：「It takes mere milliseconds to start a fresh isolate」【A】[[67]](https://blog.cloudflare.com/code-mode/)

**② Hugging Face smolagents 的 `CodeAgent`**【B】[[68]](https://huggingface.co/blog/smolagents)

官方博客明确两种 agent 并存：「On top of this `CodeAgent` class, we still support the standard **`ToolCallingAgent`** that writes actions as JSON/text blobs.」，并引导读者看对比基准：「see a comparison of **code agents versus tool calling agents** (spoilers: code works better)」。

> **标题核实（回应调研问题中的猜测）**：用户猜测的论文标题「Code Agents are the future」**不是** smolagents 相关论文的真实标题。可核实的对应物是两个不同的东西：官方博客标题为 **"Introducing smolagents"**（Hugging Face Blog）[[68]](https://huggingface.co/blog/smolagents)；方法论论文是 **CodeAct《Executable Code Actions Elicit Better LLM Agents》**（arXiv 2402.01030），结论原文：「use executable Python code to **consolidate LLM agents' actions into a unified action space**」「CodeAct outperforms widely used alternatives (**up to 20% higher success rate**)」【C】[[57]](https://arxiv.org/abs/2402.01030)。**「Code Agents are the future」未找到来源，属推断性说法。**

**③ OpenAI Code Interpreter（Responses API 官方文档）**【B】[[69]](https://developers.openai.com/api/docs/guides/tools-code-interpreter)

「The Code Interpreter tool allows models to **write and run Python code in a sandboxed environment** to solve complex problems in domains like data analysis, coding, and math.」并特别提示：「While we call this tool Code Interpreter, **the model knows it as the 'python tool'**」。执行环境是「a container… a **fully sandboxed virtual machine** that the model can run Python code in」，内存档位可选 `1g`/`4g`/`16g`/`64g`。

**观点：**三家路线不同（Cloudflare 换执行模型、Hugging Face 换 action 空间、OpenAI 提供沙箱运行时），但收敛到同一个判断——**「代码/脚本」比「结构化工具调用」是更宽的接口**。这与 Unix 的「组合 + 文本流」是同一件事的两种说法：代码是最终的组合器。但要注意：这三条**都不是**「MCP 已死」的证据——Cloudflare 的 Code Mode 仍以 MCP server 作为能力来源，只是把调用方式从 JSON 工具调用换成代码 binding。

### 3.7 规范里的安全原文（A5）

必须诚实地说：**2026-07-28 版规范的 Security Best Practices 页面里没有 「Tool Poisoning」 这一节**。该页实际章节为：Confused Deputy Problem、Token Passthrough、SSRF、State Handle Hijacking、Local MCP Server Compromise、OAuth Authorization URL Validation、stdio Transport Security in Proxy Scenarios、Mix-Up Attacks、Localhost Redirect URI Impersonation、CIMD Trust Policies、Scope Minimization【A】[[24]](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)。

官方可引用的原文（每条附中文翻译）：

| 议题 | 英文原句 | 中文 |
|---|---|---|
| Confused Deputy | 「Attackers can exploit MCP proxy servers that connect to third-party APIs… To prevent confused deputy attacks, MCP proxy servers **MUST** implement [consent flow]」 | 攻击者利用连接第三方 API 的 MCP 代理服务器；代理必须实现同意流程以防混淆代理攻击 |
| Token Passthrough | 「'Token passthrough' is an anti-pattern where an MCP server accepts [tokens not issued for it] … Token passthrough is explicitly forbidden」 | Token 透传是反模式；规范明确禁止 |
| 命令注入 | 「A malicious MCP server provides a URL containing **shell command injection** payloads」；缓解要求「**MUST NOT** use shell commands (e.g., `cmd.exe`, `sh`, PowerShell) to open URLs」 | 恶意 server 可提供带 shell 注入载荷的 URL；客户端**禁止**用 shell 命令打开 URL |
| 本地 server 信任 | 「Local MCP servers with inadequate restrictions or from **untrusted sources**…」 | 限制不足或来源不可信的本地 MCP server 构成风险 |
| 工具注解语义 | 「clients **MUST** consider tool annotations to be **untrusted** unless they come from a trusted server」 | 除非来自可信 server，客户端必须把工具注解视为不可信 |

而业界广为引用的「Tool Poisoning Attack」概念，**一手出处是 Invariant Labs 2025-04-01 的安全公告**，不是 MCP 规范。原文：「A Tool Poisoning Attack occurs when malicious instructions are embedded within MCP tool descriptions that are invisible to users but visible to AI models.」「**MCP's security model assumes that tool descriptions are trustworthy and benign.** However, our experiments reveal that attackers can craft tool descriptions containing instructions that [perform unauthorized actions]」，并定义了两种延伸手法：**rug pull**（server 在用户批准后偷偷改工具描述）与 **tool shadowing**（恶意 server 通过描述污染 agent 对**其他可信 server** 工具的行为）【D→一手安全研究】[[25]](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks)。

Simon Willison 在 2025-04-09 的判断可作为「观点类一手文本」引用：「The big challenge here is that these vulnerabilities **are not inherent to the MCP protocol itself—they're present any time we provide tools to an LLM** that can potentially be exposed to untrusted inputs.」以及「I have no idea how to make it universally safe.」【观点/D】[[26]](https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/)

---

## 4. CLI：为什么它对模型友好

### 4.1 Unix 哲学原文（C1）

**Doug McIlroy 的原始四条**（TAOUP 第 1.6 节引用，标注 [McIlroy78]）：

> 「(i) Make each program do one thing well. To do a new job, build afresh rather than complicate old programs by adding new features. (ii) **Expect the output of every program to become the input to another, as yet unknown, program.** Don't clutter output with extraneous information. Avoid stringently columnar or binary input formats. Don't insist on interactive input. (iii) Design and build software… to be tried early… (iv) Use tools in preference to unskilled help…」

**那句最常被引用的总结**，TAOUP 明确标注它来自 Salus 的《A Quarter Century of Unix》里 McIlroy 的转述：

> 「This is the Unix philosophy: **Write programs that do one thing and do it well. Write programs to work together. Write programs to handle text streams, because that is a universal interface.**」

TAOUP 自己的书目把 [McIlroy78] 落到：**「[BSTJ] The Bell System Technical Journal… "Unix Time-Sharing System Forward". M. D. McIlroy, E. N. Pinson, and B. A. Tague. © 1978. vol 57, number 6 part 2 (July-August).」**【A（TAOUP 原文与其书目）/B（BSTJ 期刊本身）】[[27]](http://www.catb.org/~esr/writings/taoup/html/ch01s06.html)[[28]](http://www.catb.org/~esr/writings/taoup/html/bibliography.html)

> **出处严谨性说明**：第一段「do one thing well / expect the output…」可追溯到 1978 年 BSTJ 的 Forward；第二段「text streams… universal interface」在 TAOUP 中是**经 Salus 1994 转述**的版本。两段都不是 1972 年某份 memo 的直接原文。中文材料里常见的「McIlroy 1972 memo」说法，**我没有找到可核实的一手来源**，标为 U。

**Eric Raymond《The Art of Unix Programming》**：章节名为 **Chapter 1. Philosophy → "Basics of the Unix Philosophy"**，给出 17 条规则（Rule of Modularity / Clarity / Composition / Separation / Simplicity / Parsimony / Transparency / Robustness / Representation / Least Surprise / Silence / Repair / Economy / Generation / Optimization / Diversity / Extensibility）【A】[[27]](http://www.catb.org/~esr/writings/taoup/html/ch01s06.html)。其中与 agent 最相关的是 Rule of Composition（"Design programs to be connected with other programs"）与 Rule of Repair（"Repair what you can — but when you must fail, fail noisily and as soon as possible"）。

**Rob Pike「cat -v considered harmful」**：可核实的事实是——**1983 年 USENIX Summer Conference 上 Rob Pike 做了一个题为 "UNIX Style, or cat -v Considered Harmful" 的报告**，他随后与 Brian Kernighan 合写了论文 *Program Design in the UNIX Environment*（AT&T Bell Laboratories Technical Journal, Oct 1984, Vol. 63 No. 8 Part 2）【D（站点转述，非原刊）】[[29]](https://harmful.cat-v.org/cat-v/)。**该演讲本身的正式会议论文集原文我未找到可引用的在线一手来源，标为 U**；如需引用请引 1984 年那篇论文，而不是转述稿。

### 4.2 文本接口与 `--json` 契约：agent CLI 的非交互接口（C4/C5）

这一节全部是**官方文档原文**（A 级），可直接作为「CLI 对模型友好」的工程证据。

| Agent CLI | 非交互入口 | 结构化输出 | 权限/沙箱开关（官方原文） | 来源 |
|---|---|---|---|---|
| Claude Code | 「Add the `-p` (or `--print`) flag to any `claude` command to run it non-interactively.」 | `--output-format json` / `stream-json`（"newline-delimited JSON for real-time streaming"，事件含 `permission_denied`）；`--json-schema` 可约束输出；`json` 含 `total_cost_usd` | `--allowedTools "Bash(git diff *),Bash(git log *)"`（permission rule 语法，尾部 `*` 为前缀匹配）；`--permission-mode dontAsk` 适合「locked-down CI runs」；`--bare` 用于 CI 免除宿主 hooks/plugins/CLAUDE.md | [[30]](https://code.claude.com/docs/en/headless) |
| OpenAI Codex CLI | 「Use `codex exec` to run Codex in scripts and CI」；「streams progress to **stderr** and prints only the final agent message to **stdout**」（可管道） | `codex exec --json` → 「stdout becomes a **JSON Lines (JSONL) stream**」，事件类型 `thread.started`/`turn.completed`/`item.*`/`error`；`--output-schema ./schema.json` 约束最终响应；`-o/--output-last-message` | 默认只读沙箱；`--sandbox workspace-write` / `--sandbox danger-full-access`；**`--full-auto` 已弃用**（"Codex keeps `codex exec --full-auto` as a deprecated compatibility flag and prints a warning"）；`codex exec -` 从 stdin 读 prompt | [[31]](https://learn.chatgpt.com/docs/non-interactive-mode) |
| Gemini CLI | 「Headless mode is triggered when the CLI is run in a non-TTY environment or when providing a query with the `-p` (or `--prompt`) flag.」 | `--output-format text,json,stream-json`；JSON 含 `response`/`stats`/`error`；stream-json 事件含 `tool_use`/`tool_result` | 退出码契约：`0` 成功、`1` 一般错误、`42` 输入错误、`53` 超过轮次上限；`--approval-mode default,auto_edit,yolo,plan`（`--yolo` 已弃用） | [[32]](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md)[[33]](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md) |
| opencode | 「Run opencode in non-interactive mode by passing a prompt directly: `opencode run [message..]`」 | `--format json`（"raw JSON events"） | 可 `--attach http://localhost:4096` 连到 headless server | [[34]](https://opencode.ai/docs/cli/) |
| Aider | 「Aider takes a `--message` argument… It will do that one thing, apply the edits to the files and then exit.」 | 官方定位是「useful for scripting」 | `--yes`「Always say yes to every confirmation」；`--message-file`；`--commit` | [[35]](https://aider.chat/docs/scripting.html) |
| goose | `goose run --instructions plan.md` / `--recipe recipe.yaml` | `--output-format <FORMAT>`「text, **json**, or **stream-json**… Use JSON structured output for automation and scripting」；`-q/--quiet`「printing only the model response to stdout」 | `--no-session`、`--max-turns` | [[36]](https://goose-docs.ai/docs/guides/goose-cli-commands) |

**事实**：六个主流 agent CLI **全部**提供了「一次性执行 + 结构化输出 + 权限开关」三件套。**推断：**这不是巧合，而是 agent 作为调用方对 CLI 提出的最低可用契约——没有 `--json` 就只能靠正则解析人读输出，没有权限开关就无法无人值守。这与 §8 的「解析脆弱性」互为因果。

### 4.3 给模型看的错误信息设计（C6）

Anthropic 的官方立场（工程博客《Writing effective tools for agents》）：

- **错误要可操作，不要 code/traceback**：「if a tool call raises an error (for example, during input validation), you can prompt-engineer your error responses to clearly communicate **specific and actionable improvements, rather than opaque error codes or tracebacks**.」文中给出 unhelpful / helpful 两个对照示例。
- **返回量要节流**：「we restrict tool responses to **25,000 tokens by default**」；建议对可能吃上下文的返回实现 pagination / range selection / filtering / truncation。
- **响应结构影响效果**：「Even your tool response structure—for example XML, JSON, or Markdown—can have an impact on evaluation performance: there is no one-size-fits-all solution.」
- **简洁 vs 详细**：同一个 Slack 工具，「detailed tool response (**206 tokens**)」对比「concise tool response (**72 tokens**)」，「we use **~⅓ of the tokens** with 'concise' tool responses」。
- **别把 API 直接包成工具**：「A common error we've observed is tools that merely wrap existing software functionality or API endpoints」【B】[[37]](https://www.anthropic.com/engineering/writing-tools-for-agents)。

MCP 规范层面也有对应条款：输入校验错误应作为 **Tool Execution Error** 返回而非 Protocol Error，理由是「to enable **model self-correction**」；2026-07-28 版更进一步写明「Clients **SHOULD** provide tool execution errors to language models to enable self-correction.」【A】[[15]](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)[[8]](https://modelcontextprotocol.io/specification/2025-11-25/changelog)

OpenAI 侧（function calling 官方指南）：「The result you pass in the `function_call_output` message should typically be a string, where the format is up to you (JSON, error codes, plain text, etc.). The model will interpret that string as needed.」以及「If your function has no return value (for example, `send_email`), return a string that indicates success or failure, such as `"success"`.」【B】[[38]](https://developers.openai.com/api/docs/guides/function-calling)

Anthropic《Effective context engineering for AI agents》给出总原则：「good context engineering means finding the **smallest possible set of high-signal tokens**」，并把工具设计单列：「it's extremely important that tools promote efficiency… One of the most common failure modes we see is **bloated tool sets** that cover too much functionality or lead to ambiguous decision points about which tool to use. **If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better.**」【B】[[39]](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

### 4.4 为什么「拿结果再决定下一步」是 agent loop 的本质（D4）

ReAct 原文摘要即定义：「we explore the use of LLMs to generate both reasoning traces and task-specific actions in an **interleaved manner**… reasoning traces help the model induce, track, and update action plans as well as handle exceptions, while actions allow it to interface with external sources… to gather additional information.」【C】[[3]](https://arxiv.org/abs/2210.03629)

**是否支持「AI 自己决定用哪个命令」这一叙事？——部分支持，但原文框架里动作空间是人工给定的。** ReAct 的实验设定是「interacting with a simple Wikipedia API」「two interactive decision making benchmarks (ALFWorld and WebShop)」，即 action space 由研究者预先设计；它证明的是「交替推理能提升选择与容错」，**不是**「模型能自主发明命令」。这两件事的差别，正是 §6 里 SWE-agent 的 ACI 论点要补的那块。

SWE-agent 的 ACI 论点原文：

> 「we posit that LM agents represent a **new category of end users** with their own needs and abilities, and would benefit from **specially-built interfaces** to the software they use. We investigate **how interface design affects the performance of language model agents**.」【C】[[40]](https://arxiv.org/abs/2405.15793)

Anthropic 的实务版本把「拿结果再决定」写成了 **just-in-time context**：「Rather than pre-processing all relevant data up front, agents built with the 'just in time' approach maintain lightweight identifiers (file paths, stored queries, web links, etc.) and use these references to dynamically load data into context at runtime… The model can write targeted queries, store results, and leverage **Bash commands like `head` and `tail`** to analyze large volumes of data without ever loading the full data objects into context.」【B】[[39]](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

**这是本次调研中最直接回应原命题「unix 思想焕发新生?」的一句官方文本**：Anthropic 明确把 `head`/`tail` 这类 Unix 小工具当作**上下文预算工具**在用。

---

## 5. CLI 与 MCP 不是二选一：四层正交模型

### 5.1 分层模型

| 层 | 回答的问题 | CLI 的答案 | MCP 的答案 | 能否互换 |
|---|---|---|---|---|
| **能力暴露面** | 模型怎么「看到」能力 | 名称 + `--help` / man / SKILL.md | `tools/list` 返回 JSON Schema 定义 | 可互换（可把 CLI 包成 MCP，也可把 MCP 包成 CLI） |
| **运行时** | 代码在哪跑、以什么身份跑 | 子进程，继承宿主权限（需沙箱隔离） | 进程内 stdio 或远程 HTTP 服务 | 不可互换（MCP 可远程，CLI 天然本地） |
| **上下文预算** | 每次决策要花多少 token | 按需 `--help`/读文件，天然渐进披露 | 默认全量注入 `tools/list`，需 Tool Search / 文件系统化 | 可互换但成本结构不同 |
| **治理** | 谁能授权、审计、限流 | OS 权限 + 命令白名单（`Bash(git diff *)`） | OAuth 2.1 + Resource Indicators + 命名空间验证 | 部分可互换，MCP 更标准化 |
| **状态** | 跨调用记忆放哪 | 文件系统 / NOTES.md / 会话文件 | 2026-07-28 后为无状态，跨调用状态必须由 server 显式颁发 handle | 已趋同（MCP 学 CLI 的无状态） |

### 5.2 决策表（可直接落地）

| 你的场景 | 建议 | 理由（来自原文） |
|---|---|---|
| 高频编码 agent，任务碎片化、有现成 CLI | **CLI + Skills** | 「Modern coding agents increasingly favor CLI–based workflows exposed as SKILLs over MCP because CLI invocations are more token-efficient: they avoid loading large tool schemas and verbose accessibility trees」（Microsoft 官方 README）【A】[[41]](https://github.com/microsoft/playwright-cli) |
| 需要持续浏览器/会话状态、富内省、自愈测试 | **MCP** | 「MCP remains relevant for specialized agentic loops that benefit from persistent state, rich introspection, and iterative reasoning over page structure… where maintaining continuous browser context outweighs token cost concerns」（同一份官方 README）【A】[[42]](https://github.com/microsoft/playwright-mcp) |
| 工具库 >10~15 个，选择准确率开始掉 | **先做工具收敛，再上检索** | 准确率在 10–15 个工具（Haiku 4.5）开始跌破 90%【C】[[2]](https://arxiv.org/abs/2606.30317)；官方对应手段是 Tool Search + `defer_loading`【B】[[21]](https://www.anthropic.com/engineering/advanced-tool-use) |
| 企业内网、需要统一鉴权与审计 | **MCP（放在网关上）** | SCOUT 的做法是「proxy MCP server aggregates many backend servers behind a single endpoint providing a secure, governable **chokepoint** for authentication, policy enforcement, and observability」【C】[[22]](https://arxiv.org/abs/2608.23992) |
| 团队规范、构建/测试约定 | **AGENTS.md（不是 MCP 也不是 CLI）** | 「Think of AGENTS.md as a **README for agents**: a dedicated, predictable place to provide the context and instructions」（官方站点）【A】[[43]](https://agents.md/) |
| 可复用的流程知识 + 脚本 | **Agent Skills** | 三级渐进披露，Level 1 每个 Skill 约 100 tokens、Level 2 <5k tokens、Level 3 未读不计费【A】[[44]](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |

### 5.3 AGENTS.md 与 Agent Skills 的原文定位

**AGENTS.md**（官网原文）：「README.md files are for humans: quick starts, project descriptions, and contribution guidelines. AGENTS.md complements this by containing the **extra, sometimes detailed context coding agents need**: build steps, tests, and conventions that might clutter a README or aren't relevant to human contributors.」规模：站点宣称「used by over **60k** open-source projects」，并说明「AGENTS.md is now stewarded by the **Agentic AI Foundation under the Linux Foundation**」。优先级规则：「The closest AGENTS.md to the edited file wins; explicit user chat prompts override everything.」【A】[[43]](https://agents.md/)

**Agent Skills**（Anthropic 工程博客原文）：三级结构被逐字写清——「the agent pre-loads the name and description of every installed skill into its system prompt. This metadata is the **first level of progressive disclosure**… The actual body of this file is the **second level** of detail… These additional linked files are the **third level (and beyond)** of detail」【B】[[45]](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)。**与 MCP 的关系，官方只说了一句互补**：「We'll also explore how Skills can **complement** Model Context Protocol (MCP) servers by teaching agents more complex workflows that involve external tools and software.」官方文档里唯一的实操性约束是：Skill 内引用 MCP 工具时必须用**全限定名**（`ServerName:tool_name`），否则「Claude may fail to locate the tool, especially when multiple MCP servers are available」【A】[[46]](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)。

**关于 E3「Anthropic 官方是否给出 MCP vs CLI vs Skills 的选择建议」——我没有找到 Anthropic 官方页面给出三者择一的直接建议，必须写「官方未给出直接建议」。** 能拿到的最接近表述有两处：一是上文的「Skills 补充 MCP」；二是 Anthropic 在工具层面的取舍原则（「More tools don't always lead to better outcomes」【B】[[37]](https://www.anthropic.com/engineering/writing-tools-for-agents)）。真正给出「CLI vs MCP」直接建议的是 **Microsoft 的 Playwright 仓库**（两份 README 互相引用，措辞一致）【A】[[41]](https://github.com/microsoft/playwright-cli)[[42]](https://github.com/microsoft/playwright-mcp)。

---

## 6. 实证：benchmark 与论文说明了什么

### 6.1 核心实证表

| 对象 | 关键数字（原文） | 日期/快照 | 等级 | 来源 |
|---|---|---|---|---|
| **MCP vs CLI 受控对比**（arXiv 2608.08654） | 7 脚手架 × 5 模型 × 1 固定任务（对私有 git 仓库的 6 个操作）。无 MCP 支持的两个脚手架**全部完成**且「**5.0x to 28x cheaper**」；27B 小模型成本跨脚手架「varied **139x**」；13 组严格配对比值「span **0.43x to 29x**」；失败成本「**12.9 per cent** of the money spent on MCP runs bought no completed work against **2.2 per cent** on CLI runs」，但「failures were equally common in both」 | v1 2026-08-09 | C | [[1]](https://arxiv.org/abs/2608.08654) |
| Terminal Agents 综述（arXiv 2608.20485） | 「realized behavior is jointly shaped by the **model, interface, harness, runtime, and environment**」；「prevailing evaluations emphasize final outcomes and expose **process quality, recovery, and governance unevenly**」 | v1 2026-08-20 | C | [[47]](https://arxiv.org/abs/2608.20485) |
| Terminal-Bench 2.0（arXiv 2601.11868） | 「**89 tasks**… frontier models and agents score **less than 65%**」 | v1 2026-01-17 | C | [[48]](https://arxiv.org/abs/2601.11868) |
| Terminal-Bench 站点当前状态 | 站点现为「**TERMINAL-BENCH 4.0**」，Hosted by Stanford / Harbor / Laude Institute；leaderboard 为**前端渲染**，本次抓取只拿到表头（RANK/MODEL/AGENT/RESOLUTION RATE/COST/TOKENS），**未能取到可引用的分数快照** | 2026-10-02 抓取 | A（站点）/U（分数） | [[49]](https://www.tbench.ai/) |
| SWE-bench 原始论文（arXiv 2310.06770） | 「**2,294** software engineering problems… across **12** popular Python repositories」；「The best-performing model, Claude 2, is able to solve a mere **1.96%** of the issues」 | 2023-10 | C | [[50]](https://arxiv.org/abs/2310.06770) |
| SWE-bench Verified 官方说明 | 「**Aug. 13, 2024**: Introducing *SWE-bench Verified*! Part 2 of our collaboration with OpenAI Preparedness. A subset of **500 problems** that real software engineers have confirmed are solvable.」（引用了 OpenAI 报告链接） | 2024-08-13 | A | [[51]](https://github.com/SWE-bench/swe-bench) |
| SWE-bench 当前 SOTA | 官方 leaderboard 页面为前端渲染；页面可见「SWE-bench **2294 instances**」「**Bash Only 500 instan[ces]**」，但**未取到可引用的最新分数** | 2026-10-02 抓取 | U（分数） | [[52]](https://www.swebench.com/) |
| τ-bench（arXiv 2406.12045） | 「even state-of-the-art function calling agents (like gpt-4o) succeed on **<50%** of the tasks, and are quite inconsistent (**pass^8 <25% in retail**)」 | 2024-06 | C | [[53]](https://arxiv.org/abs/2406.12045) |
| ToolLLM / ToolBench（arXiv 2307.16789） | 「**16,464** real-world RESTful APIs spanning **49** categories from RapidAPI Hub」；提出 DFS 决策树搜索 | 2023-07 | C | [[54]](https://arxiv.org/abs/2307.16789) |
| API-Bank（arXiv 2304.08244） | 「**73** API tools… **314** tool-use dialogues with **753** API calls」；训练集「**1,888** tool-use dialogues from **2,138** APIs spanning **1,000** distinct domains」；Lynx「surpasses Alpaca's tool utilization performance by more than **26 pts**」 | 2023-04 | C | [[55]](https://arxiv.org/abs/2304.08244) |
| ReAct（arXiv 2210.03629） | 见 §4.4 原句 | 2022-10 | C | [[3]](https://arxiv.org/abs/2210.03629) |
| SWE-agent（arXiv 2405.15793） | ACI 论点见 §4.4；成绩「pass@1 rate of **12.5%** and **87.7%**」（SWE-bench / HumanEvalFix） | 2024-05 | C | [[40]](https://arxiv.org/abs/2405.15793) |
| Voyager（arXiv 2305.16291） | 「an ever-growing **skill library of executable code**」；「obtains **3.3x** more unique items, travels **2.3x** longer distances, and unlocks key tech tree milestones up to **15.3x** faster than prior SOTA」 | 2023-05 | C | [[56]](https://arxiv.org/abs/2305.16291) |
| CodeAct（arXiv 2402.01030） | 「use executable Python code to consolidate LLM agents' actions into a unified action space」；「CodeAct outperforms widely used alternatives (**up to 20% higher success rate**)」 | 2024-02 | C | [[57]](https://arxiv.org/abs/2402.01030) |
| Darwin Gödel Machine（arXiv 2505.22954） | 自改代码 + 经验验证：「increasing performance on SWE-bench from **20.0% to 50.0%**, and on Polyglot from **14.2% to 30.7%**」 | v1 2025-05-29 / v3 2026-03-12 | C | [[58]](https://arxiv.org/abs/2505.22954) |
| Unix 哲学 × agent（arXiv 2601.11672） | 「adopting **file- and code-centric interaction models** may enable agentic systems that are more maintainable, auditable, and operationally robust」——**注意是 "may enable"，属论述型论文** | v1 2026-01-16 | C（观点/立场文） | [[4]](https://arxiv.org/abs/2601.11672) |
| Everything is Context（arXiv 2512.05470） | 提出「a file-system abstraction for context engineering, inspired by the Unix notion that 'everything is a file'」，在 AIGNE 框架实现（Context Constructor / Loader / Evaluator） | v1 2025-12-05 | C | [[59]](https://arxiv.org/abs/2512.05470) |
| 工具自造的官方产品化 | Anthropic Tool Search Tool + Programmatic Tool Calling，beta header `advanced-tool-use-2025-11-20`；`allowed_callers`/`defer_loading` 为原文参数名 | 抓取于 2026-10-02 | B | [[21]](https://www.anthropic.com/engineering/advanced-tool-use) |

### 6.2 D6 专项：有没有「CLI vs MCP 同任务直接对比」的研究？

**有。**这是本次调研最重要的发现：**arXiv 2608.08654**，标题 *The Scaffolding Matters More Than the Interface: A Controlled Comparison of MCP and CLI Tool Use Across Seven Agent Scaffoldings, Five Language Models, and One Software Task*（v1 2026-08-09）。它是目前唯一一篇**严格配对、并核验实际行为**的 MCP vs CLI 成本对比实验。三条结论都必须引：

1. **主导变量是脚手架，不是接口**：「The dominant effect was the scaffolding.」
2. **MCP 对该类任务并非必需**：「Two of the seven ship no MCP support at all; they completed every run using only the CLI, which shows that MCP is unnecessary for this class of work.」
3. **不核验行为的对比会测到未知混合物**：「Agents frequently ignored the interface they were assigned, so **comparisons that do not verify actual behaviour measure an unknown mixture**.」

**交叉核对与冲突记录**：该论文开篇即指出，此前公开的成本估计「**disagree by more than an order of magnitude** while resting on practitioner reports that cannot be reproduced」——这与 §3.5 中 Anthropic 的「98.7% 节省」、Tool Search 的「85% 减少」、SCOUT 的「99% 减少」并不矛盾但**口径不同**：Anthropic 与 SCOUT 测的是「工具定义注入的 token 量」，而 2608.08654 测的是「整条任务的总美元成本（含失败重试）」。**把前者的百分比当作「用了 MCP 就更贵 98%」是常见误读。**

---

## 7. 生态现状与真实案例

### 7.1 把 CLI/既有系统包成 MCP server（E1，工具数实测）

| 项目 | 官方仓库 | 实测工具数（计数依据） | 备注 |
|---|---|---|---|
| Playwright MCP | https://github.com/microsoft/playwright-mcp 【A】[[42]](https://github.com/microsoft/playwright-mcp) | **72**（对 README 全文正则去重统计 `browser_[a-z_]+`） | README 自带「Playwright MCP vs Playwright CLI」章节，官方推荐编码 agent 用 CLI+Skills |
| GitHub MCP Server | https://github.com/github/github-mcp-server 【A】[[64]](https://github.com/github/github-mcp-server) | **96** 个工具（README `## Tools` 自动生成段落内 `- **tool**` 去重计数）；**22** 个 toolset | 自带上下文治理机制：`--toolsets repos,issues,...` / `GITHUB_TOOLSETS` / `--tools` 白名单；「When no toolsets are specified, default toolsets are used」 |
| filesystem MCP | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem 【A】[[65]](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | **13**（`### Tools` 段 `- **name**` 计数：read_text_file / read_media_file / read_multiple_files / write_file / edit_file / create_directory / list_directory / list_directory_with_sizes / move_file / search_files / directory_tree / get_file_info / list_allowed_directories） | 权限靠目录白名单（command-line args 或 MCP Roots） |
| mcp-server-git | https://github.com/modelcontextprotocol/servers/tree/main/src/git 【A】[[66]](https://github.com/modelcontextprotocol/servers/tree/main/src/git) | **12**（`### Tools` 段编号列表计数：git_status / git_diff_unstaged / git_diff_staged / git_diff / git_commit / git_add / git_reset / git_log / git_create_branch / git_checkout / git_show / git_branch） | 典型「把 CLI 子命令一对一映射为工具」的样本——**也正因如此，它是 §4.3 所说「仅仅包装已有功能」的教科书案例** |

**推断：**`mcp-server-git` 的 12 个工具，`git` CLI 本身用 `--help` 就能按需发现；把 12 个工具定义常驻上下文，等于用固定 token 换取「不需要模型读 help」。这正是 Anthropic 所说「More tools don't always lead to better outcomes」的实例化。

### 7.2 反向案例：MCP server 被包成 CLI（E2）

**有，且是官方生态内的产物**：`wong2/mcp-cli`——「A CLI inspector for the Model Context Protocol」，功能为「Run MCP servers from various sources / List Tools, Resources, Prompts / Call Tools… / OAuth support for SSE and Streamable HTTP servers」。它还提供明确的**非交互模式**，README 原文：「This mode is useful for **scripting and automation**, as it bypasses all interactive prompts and executes the specified primitive directly.」，用法形如 `npx @wong2/mcp-cli -c config.json call-tool filesystem:read_file --args '{"path": "package.json"}'`，并支持 `--url http://localhost:8000/mcp`（Streamable HTTP）与 `--sse`【A】[[60]](https://github.com/wong2/mcp-cli)。

**观点：**这条双向通道（CLI→MCP、MCP→CLI）本身就是「cli or mcp」二分法不成立的最好证据：**两个东西都能互相包装，说明它们是层，不是选项。**

### 7.3 生态规模数字（注意口径冲突）

| 数字 | 出处 | 口径 | 日期 |
|---|---|---|---|
| >10,000 个活跃公共 MCP server | Anthropic 捐赠公告【B】[[16]](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation) | 公共生态 | 2025-12-09 |
| 97M+ 月 SDK 下载（Python + TypeScript） | 同上 | SDK 下载量 | 2025-12-09 |
| 400M 月 SDK 下载（"a 4x increase this year"）；Claude connectors 目录 **950+** MCP server | Claude 官方博客【B】[[14]](https://claude.com/blog/bringing-mcp-2026-07-28-to-claude) | SDK 下载量 / **单一产品目录** | 2026（2026-07-28 规范发布时） |
| **21,000+** 可在公网探测到的 MCP server 实例；确认 640 个生产 server，动态审计 414 个 | arXiv 2608.00150【C】[[61]](https://arxiv.org/abs/2608.00150) | 公网实例（被动发现，含非活跃） | 2026-07 四次测量 |

**冲突说明**：三者不矛盾但不可混用——「10,000 个 server（生态）」≠「950 个（Claude 目录）」≠「21,000 个实例（公网可探测，含重复与僵尸）」。**任何把这三个数字混着用的材料都不可信。**

---

## 8. 仍未解决的问题

| # | 问题 | 已有证据（原文/数字） | 等级 | 判定 |
|---|---|---|---|---|
| 1 | **权限模型** | Claude Code：默认只读 + `Bash(git diff *)` 规则语法 + `permissions.allow/deny` + `dontAsk` 模式【A】[[70]](https://code.claude.com/docs/en/settings)；沙箱化后「reduces permission prompts by **84%**」【B】[[62]](https://www.anthropic.com/engineering/claude-code-sandboxing) | A/B | **有证据**，但「规则语法」本身仍需人工设计；`*` 是前缀匹配（官方原句为「The trailing `*` enables prefix matching」），因此**过宽匹配是设计上的固有风险**——**推断：**`Bash(git diff*)` 这类写法会连带放行 `git diff-index` 之类同前缀命令，属本文推断，未在这些页面找到官方原句（原调研此行曾标【A】，经校验后降级） |
| 2 | **鉴权** | 规范仍在快速迭代：2026-07-28 弃用 DCR、要求 RFC 9207 `iss` 校验、凭证按 issuer 绑定；实测 **91.8%** 的动态审计 server **缺 OAuth 认证** | A/C | **有证据（且证据表明落地率极低）** |
| 3 | **跨会话状态** | 2026-07-28 明确「Servers that need cross-call state use explicit, server-minted handles passed as ordinary tool arguments」；Roots/Sampling 弃用 | A | **有证据**，但方案把状态责任推给 server 实现者，无统一语义 |
| 4 | **长任务编排** | tasks 从核心移出为官方扩展（`tasks/get` 轮询 + `tasks/update`）；MRTR 用 `input_required` 重试取代 server 发起请求 | A | **有证据**，属「刚定型、生态未验证」阶段 |
| 5 | **命令注入 → 代码执行** | 规范禁止用 shell 打开 URL【A】[[24]](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)；公网实测「**687** tool instances across confirmed servers **expose shell execution capabilities without access controls**」【C】[[61]](https://arxiv.org/abs/2608.00150)；安全 SoK 汇总 78 篇研究、42 类攻击手法，称自适应攻击下「attack success rates… **exceed 85%**」而多数防御「**less than 50%** mitigation」【C】[[63]](https://arxiv.org/abs/2601.17548) | A/C | **有证据**，且是目前最严重的一项 |
| 6 | **可观测性** | 2026-07-28 补了 OpenTelemetry trace context 约定（`traceparent`/`tracestate`/`baggage`，SEP-414）；Claude 侧提供 connector 性能看板；MCP 架构模式论文把 observability 列为 cross-cutting concern | A/C | **有证据**，但仍是「约定」而非强制，且日志能力刚被降级（Logging 弃用、建议 stderr 或 OTel） |
| 7 | **模型解析 `--json` 的脆弱性** | 间接证据：各 CLI 都提供 schema 约束（Claude `--json-schema`、Codex `--output-schema`）；2608.08654 发现「Agents **frequently ignored the interface they were assigned**」 | C | **部分有证据**：存在「行为不按预期」的实测，但**未找到专门量化「CLI JSON 输出解析失败率」的实验**——属未解决且缺直接证据 |
| 8 | **工具数量阈值** | 10–15 个工具（Haiku 4.5）/ 20–30 个（Sonnet 4）准确率跌破 90% | C | **有证据**，但属单一论文结论，未见独立复现 |
| 9 | **协议层工具列表治理** | 规范**没有**工具数量上限或「保持少量」的提示，只有分页、`ttlMs`/`cacheScope`、确定性排序（保护 prompt cache）、`listChanged` | A（缺失证据） | **规范未覆盖**——「工具膨胀」目前是工程约定，不是规范约束 |

---

## 9. 对实践的启示（面向自研 CLI/agent 工具链）

以下每条都是「因为…所以…」的因果链，因果两端都能在本文找到出处。

1. **因为**受控实验显示同一任务在不同脚手架间成本可差 139×，而接口类型只带来不稳定且可正可负的差异【C】[[1]](https://arxiv.org/abs/2608.08654)，**所以**自研 agent 应把工程预算优先投在脚手架（循环控制、重试、上下文裁剪、行为核验）上，而不是先纠结「要不要上 MCP」。
2. **因为**官方明确「限制工具返回 25,000 tokens」「工具集臃肿是最常见失败模式」【B】[[37]](https://www.anthropic.com/engineering/writing-tools-for-agents)，**所以**每个 CLI 的 `--json` 输出都应实现分页/过滤/截断三个参数并给出保守默认值——默认全量返回等于把成本转嫁给模型上下文。
3. **因为**MCP 规范要求 `tools/list` 顺序必须确定、理由写的是「improve LLM prompt cache hit rates」【A】[[7]](https://modelcontextprotocol.io/specification/2026-07-28/changelog)，**所以**自研 CLI 的输出字段顺序、`--help` 文本、错误消息模板都应保持**字节级稳定**，否则每次调用都在破坏上游缓存。
4. **因为**规范把输入校验错误定义为 Tool Execution Error 并要求「enable model self-correction」【A】[[8]](https://modelcontextprotocol.io/specification/2025-11-25/changelog)，**所以**CLI 的错误输出应写成「哪里错 + 可用字段/可用取值 + 一个正确示例」，禁止只返回错误码——错误消息是**给模型看的 API**，不是给人看的日志。
5. **因为**工具数超过 10–15 个后选择准确率跌破 90%【C】[[2]](https://arxiv.org/abs/2606.30317)，**所以**CLI 工具应优先设计为「少数高带宽命令 + 强大的过滤参数」（类似 `search_logs` 取代 `read_logs`），并把更多能力藏在子命令而非并列命令里。
6. **因为**Skills 的 Level 3 文件「在未被读取前消耗 0 token」、脚本「只把输出送进上下文」【A】[[46]](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)，**所以**把「长文档 + 确定性脚本」放进技能目录、把「需要模型判断的部分」留在 SKILL.md 正文，是当前最省上下文的组织方式。
7. **因为**沙箱+网络隔离能把权限提示减少 84%，而仅做文件隔离不足以阻止外泄【B】[[62]](https://www.anthropic.com/engineering/claude-code-sandboxing)，**所以**自研 CLI 若会被 agent 调用，必须同时给出**目录白名单**与**域名白名单**两个开关，缺一不可。
8. **因为**公网实测 91.8% 的 MCP server 没有 OAuth、687 个工具实例无访问控制地暴露 shell 执行【C】[[61]](https://arxiv.org/abs/2608.00150)，**所以**自研 MCP server 在上线前必须默认走 stdio/本地、远程化时强制鉴权，并把「能执行 shell」当作最高危能力单独标注与限流。
9. **因为**论文发现「agents frequently ignored the interface they were assigned」【C】[[1]](https://arxiv.org/abs/2608.08654)，**所以**任何 agent 评测都必须**核验实际发生的动作与最终状态**（如检查仓库状态），不能采信 agent 自报——这条同样适用于内部验收测试。

---

## 10. 未证实 / 需要继续跟踪的断言

以下 9 条**未找到可引用的一手来源**，或证据不足以支撑原断言的强度，一律标为 U（推断/未证实），禁止当作事实使用：

| # | 断言 | 状态 | 说明 |
|---|---|---|---|
| 1 | 「未来的一切都是 CLI or MCP」 | **U（推断）** | 无任何来源支持全称判断；现有证据只支持「两者都是主流形态之一」 |
| 2 | 「Unix 思想焕发新生解释了 CLI/MCP 之争」 | **U（推断）** | 只有论述型论文（2601.11672 用 "may enable"）与官方类比式表述，**没有任何实验把「Unix 哲学」作为自变量测过 agent 指标** |
| 3 | 「McIlroy 1972 年 memo 中提出 Unix 哲学」 | **U（未找到）** | 可考一手出处是 1978 BSTJ Forward 与 Salus 1994 转述；「1972 memo」说法未找到来源 |
| 4 | Rob Pike「cat -v considered harmful」演讲原文 | **U（未找到）** | 演讲存在（1983 USENIX Summer），但无正式在线一手文本；可引的是 1984 年 Kernighan & Pike 论文 |
| 5 | 「Perplexity 首先放弃 MCP」 | **U（未找到一手来源）** | 中文媒体广泛转载该说法（如知乎/搜狐标题「MCP已死，CLI当立！Perplexity首先放弃使用MCP」），**但未找到 Perplexity 官方声明或官方博客原文**，属媒体叙事，D 级线索 |
| 6 | 「越来越多大厂抛弃 MCP 转向 CLI」 | **U（未找到一手来源）** | 同上；**反证是**：Anthropic/Block/OpenAI 于 2025-12 把 MCP 捐给 AAIF，Google、Microsoft、AWS、Cloudflare、Bloomberg 为支持方，Claude 目录已列 950+ MCP server【A/B】[[16]](https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation)[[14]](https://claude.com/blog/bringing-mcp-2026-07-28-to-claude) |
| 7 | Terminal-Bench 当前 SOTA 分数 | **U（未取到）** | 官网为前端渲染，2026-10-02 抓取仅得表头；可引用的是 2026-01 论文的「<65%」 |
| 8 | SWE-bench Verified 当前 SOTA 分数 | **U（未取到）** | 同上；官方 README 只给出 Verified 定义（500 题）与历史事件 |
| 9 | 「模型解析 `--json` 输出很脆弱」（定量） | **U（缺直接证据）** | 只有间接证据（各家都加 `--json-schema`/`--output-schema`；2608.08654 发现 agent 会无视被分配的接口），**未找到解析失败率的专门量化研究** |

**另有 2 条「官方未明确表态」，需要继续跟踪：**

- **Anthropic 是否给出过 MCP vs CLI vs Skills 的择一建议**：**未找到**，只有「Skills 补充 MCP」的互补表述【A】[[46]](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)。给出直接建议的是 Microsoft（Playwright 两份 README）【A】[[41]](https://github.com/microsoft/playwright-cli)。
- **OpenAI / Google / Microsoft 各自的独立官方采用公告**：本次只核到 Linux Foundation 新闻稿内的官方引述（Nick Cooper/OpenAI、Google 代表）【A/B】[[17]](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)；**各家独立博客/公告原文本次未逐一抓取**，需补。

---

## 附录：来源清单

> 全部条目于 2026-10-02 实际抓取成功（`www.tbench.ai` 与 `www.swebench.com` 的 leaderboard 为前端渲染，仅取到页面骨架，已在正文标注）。

**MCP 规范与官方治理**

1. The Scaffolding Matters More Than the Interface（arXiv 2608.08654） — https://arxiv.org/abs/2608.08654（2026-10-02）
2. MCP Server Architecture Patterns for LLM-Integrated Applications（arXiv 2606.30317） — https://arxiv.org/abs/2606.30317（2026-10-02）
3. ReAct: Synergizing Reasoning and Acting in Language Models（arXiv 2210.03629） — https://arxiv.org/abs/2210.03629（2026-10-02）
4. From Everything-is-a-File to Files-Are-All-You-Need（arXiv 2601.11672） — https://arxiv.org/abs/2601.11672（2026-10-02）
5. Anthropic — Introducing the Model Context Protocol（2024-11-25） — https://www.anthropic.com/news/model-context-protocol（2026-10-02）
6. MCP — Versioning (2026-07-28, markdown) — https://modelcontextprotocol.io/docs/2026-07-28/learn/versioning.md（2026-10-02）
7. MCP Spec — 2026-07-28 Key Changes（无状态化、移除 initialize 与会话、MRTR、弃用 Roots/Sampling/Logging） — https://modelcontextprotocol.io/specification/2026-07-28/changelog（2026-10-02）
8. MCP 2025-11-25 Key Changes — https://modelcontextprotocol.io/specification/2025-11-25/changelog（2026-10-02）
9. MCP 2025-06-18 Key Changes — https://modelcontextprotocol.io/specification/2025-06-18/changelog（2026-10-02）
10. MCP 2025-03-26 Key Changes — https://modelcontextprotocol.io/specification/2025-03-26/changelog（2026-10-02）
11. MCP PR #206 [RFC] Replace HTTP+SSE with "Streamable HTTP"（merged 2025-03-24） — https://github.com/modelcontextprotocol/modelcontextprotocol/pull/206（2026-10-02）
12. MCP Discussion #102（stateful vs stateless 原始争论） — https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/102（2026-10-02）
13. MCP PR #2575 SEP-2575: Make MCP Stateless（merged 2026-05-11） — https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2575（2026-10-02）
14. Claude 官方博客 — Bringing MCP 2026-07-28 to Claude — https://claude.com/blog/bringing-mcp-2026-07-28-to-claude（2026-10-02）
15. MCP Spec — Server / Tools（2026-07-28） — https://modelcontextprotocol.io/specification/2026-07-28/server/tools（2026-10-02）
16. Anthropic — Donating the Model Context Protocol and establishing the AAIF（2025-12-09） — https://www.anthropic.com/news/donating-the-model-context-protocol-and-establishing-of-the-agentic-ai-foundation（2026-10-02）
17. Linux Foundation — Formation of the Agentic AI Foundation（2025-12-09） — https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation（2026-10-02）
18. MCP — Governance and Stewardship — https://modelcontextprotocol.io/community/governance（2026-10-02）
19. MCP Registry — About（preview） — https://modelcontextprotocol.io/registry/about（2026-10-02）
20. Anthropic — Code execution with MCP: building more efficient AI agents — https://www.anthropic.com/engineering/code-execution-with-mcp（2026-10-02）
21. Anthropic — Introducing advanced tool use on the Claude Developer Platform — https://www.anthropic.com/engineering/advanced-tool-use（2026-10-02）
22. Hybrid Semantic Tool Discovery for Enterprise MCP Gateway（SCOUT, arXiv 2608.23992） — https://arxiv.org/abs/2608.23992（2026-10-02）
23. Scaling Agentic Capabilities, Not Context（ATLAS, arXiv 2603.06713） — https://arxiv.org/abs/2603.06713（2026-10-02）
24. MCP — Security Best Practices（2026-07-28，页面已从 `/specification/` 迁至 `/docs/.../tutorials/security/`） — https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices（2026-10-02）
25. Invariant Labs — MCP Security Notification: Tool Poisoning Attacks（2025-04-01） — https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks（2026-10-02）
26. Simon Willison — Model Context Protocol has prompt injection security problems（2025-04-09，观点类一手文本） — https://simonwillison.net/2025/Apr/9/mcp-prompt-injection/（2026-10-02）

**Unix 哲学与 CLI 契约**

27. Eric S. Raymond — The Art of Unix Programming, Ch.1.6 Basics of the Unix Philosophy（页面未标「17 条」，该计数为本文人工枚举） — http://www.catb.org/~esr/writings/taoup/html/ch01s06.html（2026-10-02）
28. TAOUP Bibliography（[McIlroy78] = BSTJ 57(6) part 2 Forward；[Salus] = A Quarter-Century of Unix） — http://www.catb.org/~esr/writings/taoup/html/bibliography.html（2026-10-02）
29. harmful.cat-v.org — UNIX Style, or cat -v Considered Harmful（D 级线索，指向 1983 USENIX 演讲与 1984 论文） — https://harmful.cat-v.org/cat-v/（2026-10-02）
30. Claude Code Docs — Run Claude Code programmatically（原题 Headless mode；`-p`、`--output-format`、`--allowedTools`、`--json-schema`） — https://code.claude.com/docs/en/headless（2026-10-02）
31. OpenAI — Codex non-interactive mode（`codex exec`、`--json`、`--sandbox`；站点已迁至 learn.chatgpt.com） — https://learn.chatgpt.com/docs/non-interactive-mode（2026-10-02）
32. Gemini CLI — Headless mode reference — https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md（2026-10-02）
33. Gemini CLI — CLI reference（`--prompt`、`--output-format`、`--approval-mode`） — https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/cli-reference.md（2026-10-02）
34. opencode — CLI docs（`opencode run`、`--format json`、headless server） — https://opencode.ai/docs/cli/（2026-10-02）
35. Aider — Scripting（`--message`、`--yes`） — https://aider.chat/docs/scripting.html（2026-10-02）
36. goose — CLI commands（`goose run`、`--output-format`、`-q`） — https://goose-docs.ai/docs/guides/goose-cli-commands（2026-10-02）
37. Anthropic — Writing effective tools for agents — https://www.anthropic.com/engineering/writing-tools-for-agents（2026-10-02）
38. OpenAI — Function calling guide（`function_call_output` 与错误返回） — https://developers.openai.com/api/docs/guides/function-calling（2026-10-02）
39. Anthropic — Effective context engineering for AI agents — https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents（2026-10-02）
40. SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering（arXiv 2405.15793） — https://arxiv.org/abs/2405.15793（2026-10-02）

**生态与厂商定位**

41. microsoft/playwright-cli — README（CLI vs MCP 官方建议） — https://github.com/microsoft/playwright-cli（2026-10-02）
42. microsoft/playwright-mcp — README（含 "Playwright MCP vs Playwright CLI"） — https://github.com/microsoft/playwright-mcp（2026-10-02）
43. AGENTS.md — 官方站点（含 AAIF 归属与 60k 项目规模） — https://agents.md/（2026-10-02）
44. Claude Docs — Agent Skills overview（三级渐进披露与 token 成本） — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview（2026-10-02）
45. Anthropic — Equipping agents for the real world with Agent Skills — https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills（2026-10-02）
46. Claude Docs — Skill authoring best practices（原题 Agent Skills best practices；脚本、MCP 工具全限定名） — https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices（2026-10-02）
47. Terminal Agents: A Survey of AI Agents in Command-Line Environments（arXiv 2608.20485） — https://arxiv.org/abs/2608.20485（2026-10-02）
48. Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces（arXiv 2601.11868） — https://arxiv.org/abs/2601.11868（2026-10-02）
49. Terminal-Bench 官网（当前为 4.0，leaderboard 前端渲染） — https://www.tbench.ai/（2026-10-02）
50. SWE-bench: Can Language Models Resolve Real-World GitHub Issues?（arXiv 2310.06770） — https://arxiv.org/abs/2310.06770（2026-10-02）
51. SWE-bench 官方仓库 README（Verified = 500 题，2024-08-13） — https://github.com/SWE-bench/swe-bench（2026-10-02）
52. SWE-bench 官方 Leaderboard（前端渲染） — https://www.swebench.com/（2026-10-02）
53. τ-bench: A Benchmark for Tool-Agent-User Interaction（arXiv 2406.12045） — https://arxiv.org/abs/2406.12045（2026-10-02）
54. ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs（arXiv 2307.16789） — https://arxiv.org/abs/2307.16789（2026-10-02）
55. API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs（arXiv 2304.08244） — https://arxiv.org/abs/2304.08244（2026-10-02）
56. Voyager: An Open-Ended Embodied Agent with Large Language Models（arXiv 2305.16291） — https://arxiv.org/abs/2305.16291（2026-10-02）
57. Executable Code Actions Elicit Better LLM Agents（CodeAct, arXiv 2402.01030） — https://arxiv.org/abs/2402.01030（2026-10-02）
58. Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents（arXiv 2505.22954；arXiv 页无变音符） — https://arxiv.org/abs/2505.22954（2026-10-02）
59. Everything is Context: Agentic File System Abstraction for Context Engineering（arXiv 2512.05470） — https://arxiv.org/abs/2512.05470（2026-10-02）
60. wong2/mcp-cli — README（MCP → CLI，含非交互模式） — https://github.com/wong2/mcp-cli（2026-10-02）
61. Exposed by Design: A Dynamic Security Assessment of Internet-Facing MCP Servers（arXiv 2608.00150） — https://arxiv.org/abs/2608.00150（2026-10-02）
62. Anthropic — Beyond permission prompts: making Claude Code more secure and autonomous（2025-10-20） — https://www.anthropic.com/engineering/claude-code-sandboxing（2026-10-02）
63. Prompt Injection Attacks on Agentic Coding Assistants（SoK, arXiv 2601.17548） — https://arxiv.org/abs/2601.17548（2026-10-02）
64. GitHub MCP Server — README（96 工具 / 22 toolsets） — https://github.com/github/github-mcp-server（2026-10-02）
65. MCP servers — filesystem（13 工具） — https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem（2026-10-02）
66. MCP servers — git（12 工具） — https://github.com/modelcontextprotocol/servers/tree/main/src/git（2026-10-02）
67. Cloudflare — Code Mode: the better way to use MCP（Cloudflare 工程博客，2025-09-26，作者 Kenton Varda / Sunil Pai） — https://blog.cloudflare.com/code-mode/（2026-10-02）
68. Hugging Face — Introducing smolagents（CodeAgent vs ToolCallingAgent） — https://huggingface.co/blog/smolagents（2026-10-02）
69. OpenAI — Code Interpreter（Responses API，容器沙箱） — https://developers.openai.com/api/docs/guides/tools-code-interpreter（2026-10-02）
70. Claude Code Docs — Settings（permissions.allow / `Bash(...)` 规则） — https://code.claude.com/docs/en/settings（2026-10-02）
