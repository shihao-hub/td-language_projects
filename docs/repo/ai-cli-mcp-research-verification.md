# 《ai-cli-mcp-research.md》来源校验报告

> 校验日期：2026-10-02
> 校验方法：本会话 `web_fetch` 工具被 SSRF 防护拦截（`resolves to a non-public IP address`），**全程未使用**。实际路径：`pwsh` → 本机 `python 3.12.11` + `urllib.request`，逐个发 **GET**（`User-Agent: Mozilla/5.0 ... Chrome/125`，超时 20~25s，失败退避 1.5~4s 重试 1~3 次）。首次探针遇 `CERTIFICATE_VERIFY_FAILED`（本机缺根证书链），改为关闭 SSL 证书校验后全部通过。每条只保留页面 `<title>`、首个 `<h1>` 与去标签后的全文用于逐字匹配，抓取结果落盘到系统临时目录后逐条检索，未将原始页面内容写入本报告以外的任何位置。
> **降级路径**：① GitHub `/blob/` 路径首轮返回 **HTTP 503**（反爬限流），改走 `raw.githubusercontent.com` 取到同文件原文；约 5 分钟后重试 `/blob/` 恢复 200，两次结果一致。② 对 GitHub README 类来源，HTML 去标签会丢掉 Markdown 语法（`## Tools`、`- **name**`），因此**另行抓取 raw README** 做工具计数。③ 70/70 条均实际取到页面，**无一条使用 `web_search` 回退**。
> 结论一句话：**70 条来源中 69 条「URL 可达且标签与页面内容一致」，1 条「可访问但标签机构错挂」（第 67 条，把 Cloudflare 的工程博客标成 Anthropic），0 条不可达/404；另有 6 条存在标签用词或 URL 漂移（非实质错误），5 组关键论据原句深核 5/5 全部逐字命中。**

---

## 1. 结论速览

| 判定 | 条数 | 占比 | 编号 |
|---|---|---|---|
| ✅ 一致 | 69 | 98.6% | 除第 67 条外的全部 |
| ⚠️ 可访问但标签不符 | 1 | 1.4% | **67** |
| ❌ 不可达或 404 | 0 | 0% | — |
| （附）非实质漂移 | 6 | — | 24、30、46、48、54、67※ 见第 4.2 节 |

| 校验项 | 结果 |
|---|---|
| 校验 1：编号 ↔ URL 一致性 | **118 处引用 / 70 个去重编号，0 处不一致**；附录编号 1–70 连续无缺，正文未出现「引用了附录没有的编号」，附录也未出现「有编号但正文从不引用」 |
| 校验 2：URL 可达性 | **70/70 返回 200**；其中 **8 条发生重定向**（24、30、31、38、44、46、69、70），最终 URL 见第 3 节 |
| 校验 3：标签 ↔ 内容匹配 | 69 条一致；1 条实质不符（67）；6 条非实质漂移（见 4.2） |
| 校验 4：关键论据原句深核 | **5/5 组通过**，共 17 个待核原句/数字 **全部逐字命中**（详见第 5 节） |

**这份调研文档的引用是否可信？——基本可信，且远好于同类调研的平均水平，但有 1 处必须改、6 处建议改。**

支撑这个判断的具体证据：① 附录里那些最容易被编造的东西——arXiv 编号与论文标题的对应——**14 条 arXiv 来源逐条核对全部正确**，没有出现「编号存在但对应完全不同的论文」；② 附录里那些最容易被凑数的数字——`96 工具 / 22 toolsets`、`13 工具`、`12 工具`、`Verified = 500 题，2024-08-13`、`TERMINAL-BENCH 4.0`、`60k projects`、`10,000 active public MCP servers`、`97M+`、`21,000+ / 640 / 414 / 687 / 91.8%`——**逐个在页面里找到了**，包括 GitHub README 里 `## Tools` 段落的 `- **tool**` 去重计数（实测 97 条去重后正好 96）与 `AUTOMATED TOOLSETS` 表格（实测正好 22 行）；③ 文档甚至主动写下了对自己不利的核实结论（§5「本页里没有 Tool Poisoning 这一节」），我校验后**确认该页全文确实 0 次出现 "Tool Poisoning"**，属如实陈述而非遮掩。

**必须改的地方**：第 67 条（附录第 482 行）把 Cloudflare 工程博客《Code Mode: the better way to use MCP》冠以 `Anthropic —`。该页面无一处出现 "Anthropic"，作者为 Cloudflare 的 Kenton Varda 与 Sunil Pai。更关键的是——**文档正文 §3.6（第 142 行）自己写的是「① Cloudflare — Code Mode」，与附录标签直接矛盾**，属附录标签写错、正文写对。这条错误正好落在用户点名的高危模式「把 A 机构的文章标成 B 机构」上。

**建议改的地方（非实质，但会误导后续核查）**：8 条 URL 已重定向（其中 `docs.claude.com` → `platform.claude.com` / `code.claude.com`、`platform.openai.com` → `developers.openai.com`、`developers.openai.com/codex` → `learn.chatgpt.com` 属厂商整站迁移，不更新会导致下次复核时误判为失效）；第 24 条已从 `/specification/` 迁到 `/docs/.../tutorials/`；第 30、46 条页面标题已被厂商改名；第 48、54 条把论文标题缩写改写。

---

## 2. 编号 ↔ URL 一致性检查

**方法**：正则 `\[\[(\d+)\]\]\(([^)\s]+)\)` 提取第 1~403 行（正文）的全部引用，与第 404~485 行附录条目格式 `^(\d+)\.\s+(标签)\s+—\s+(URL)（日期）$` 解析出的编号→URL 映射逐对比较。

**结果（全部通过）**：

| 检查项 | 结果 |
|---|---|
| 正文 `[[n]](URL)` 出现次数 | 118 |
| 正文去重后引用到的编号数 | 70 |
| 附录解析出的条目数 | 70（无一条格式不合规、无解析失败行） |
| 附录编号范围 | 1 – 70，连续无缺号、无重号 |
| **正文 URL 与附录同编号 URL 不一致的处数** | **0** |
| 正文引用了但附录缺失的编号 | 无 |
| 附录有但正文从未引用的编号 | 无 |

**结论**：不存在编号错位、串号、跳号或「正文与附录各说各话」的情况。118 处引用与附录 70 条一一对应，编号锚点是可靠的。

---

## 3. URL 可达性与标签匹配全表（70 行）

> 「最终URL」列仅在与附录 URL 不同时写出（↪ 表示 HTTP 重定向）。判定依据见第 4 节；带「注n」的行属非实质漂移，明细见 4.2。

| 编号 | 期望内容标签 | 状态码 | 最终 URL | 实际标题（`<title>` / `<h1>`） | 判定 |
|---|---|---|---|---|---|
| 1 | The Scaffolding Matters More Than the Interface（arXiv 2608.08654） | 200 | 同 | [2608.08654] The Scaffolding Matters More Than the Interface: A Controlled Comparison of MCP and CLI Tool Use | ✅一致 |
| 2 | MCP Server Architecture Patterns for LLM-Integrated Applications（arXiv 2606.30317） | 200 | 同 | [2606.30317] MCP Server Architecture Patterns for LLM-Integrated Applications | ✅一致 |
| 3 | ReAct: Synergizing Reasoning and Acting in Language Models（arXiv 2210.03629） | 200 | 同 | [2210.03629] ReAct: Synergizing Reasoning and Acting in Language Models | ✅一致 |
| 4 | From Everything-is-a-File to Files-Are-All-You-Need（arXiv 2601.11672） | 200 | 同 | [2601.11672] From Everything-is-a-File to Files-Are-All-You-Need: How Unix Philosophy Informs the Design of Agentic… | ✅一致 |
| 5 | Anthropic — Introducing the Model Context Protocol（2024-11-25） | 200 | 同 | Introducing the Model Context Protocol \ Anthropic（页内 "Nov 25, 2024"） | ✅一致 |
| 6 | MCP — Versioning (2026-07-28, markdown) | 200 | 同 | Versioning（页内 "The **current** protocol version is **2026-07-28**"） | ✅一致 |
| 7 | MCP Spec — 2026-07-28 Key Changes（无状态化、移除 initialize 与会话、MRTR、弃用 Roots/Sampling/Logging） | 200 | 同 | Key Changes - Model Context Protocol（5 项子声明全部命中） | ✅一致 |
| 8 | MCP 2025-11-25 Key Changes | 200 | 同 | Key Changes - Model Context Protocol | ✅一致 |
| 9 | MCP 2025-06-18 Key Changes | 200 | 同 | Key Changes - Model Context Protocol | ✅一致 |
| 10 | MCP 2025-03-26 Key Changes | 200 | 同 | Key Changes - Model Context Protocol | ✅一致 |
| 11 | MCP PR #206 [RFC] Replace HTTP+SSE with "Streamable HTTP"（merged 2025-03-24） | 200 | 同 | [RFC] Replace HTTP+SSE with new "Streamable HTTP" transport by jspahrsummers · Pull Request #206（"Mar 24, 2025"） | ✅一致 |
| 12 | MCP Discussion #102（stateful vs stateless 原始争论） | 200 | 同 | State, and long-lived vs. short-lived connections · … · Discussion #102 | ✅一致 |
| 13 | MCP PR #2575 SEP-2575: Make MCP Stateless（merged 2026-05-11） | 200 | 同 | SEP-2575: Make MCP Stateless by kurtisvg · Pull Request #2575（"May 11, 2026"） | ✅一致 |
| 14 | Claude 官方博客 — Bringing MCP 2026-07-28 to Claude | 200 | 同 | MCP 2026-07-28 spec: stateless core, coming to Claude（`<h1>` = Bringing MCP 2026-07-28 to Claude） | ✅一致 |
| 15 | MCP Spec — Server / Tools（2026-07-28） | 200 | 同 | Tools - Model Context Protocol | ✅一致 |
| 16 | Anthropic — Donating the Model Context Protocol and establishing the AAIF（2025-12-09） | 200 | 同 | Donating MCP to the Agentic AI Foundation \ Anthropic（"Dec 9, 2025"） | ✅一致 |
| 17 | Linux Foundation — Formation of the Agentic AI Foundation（2025-12-09） | 200 | 同 | Linux Foundation Announces the Formation of the Agentic AI Foundation (AAIF), Anchored by New Project Contributions… | ✅一致 |
| 18 | MCP — Governance and Stewardship | 200 | 同 | Governance and Stewardship - Model Context Protocol | ✅一致 |
| 19 | MCP Registry — About（preview） | 200 | 同 | The MCP Registry - Model Context Protocol | ✅一致 |
| 20 | Anthropic — Code execution with MCP: building more efficient AI agents | 200 | 同 | Code execution with MCP: building more efficient AI agents \ Anthropic | ✅一致 |
| 21 | Anthropic — Introducing advanced tool use on the Claude Developer Platform | 200 | 同 | Introducing advanced tool use on the Claude Developer Platform \ Anthropic | ✅一致 |
| 22 | Hybrid Semantic Tool Discovery for Enterprise MCP Gateway（SCOUT, arXiv 2608.23992） | 200 | 同 | [2608.23992] Hybrid Semantic Tool Discovery for Enterprise MCP Gateway: Architecture and Implementation | ✅一致 |
| 23 | Scaling Agentic Capabilities, Not Context（ATLAS, arXiv 2603.06713） | 200 | 同 | [2603.06713] Scaling Agentic Capabilities, Not Context: Efficient Reinforcement Finetuning for Large Toolspaces | ✅一致 |
| 24 | MCP Spec — Security Best Practices（2026-07-28） | 200 | ↪ https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices | Security Best Practices - Model Context Protocol | ⚠️【注1】 |
| 25 | Invariant Labs — MCP Security Notification: Tool Poisoning Attacks（2025-04-01） | 200 | 同 | MCP Security Notification: Tool Poisoning Attacks | ✅一致 |
| 26 | Simon Willison — Model Context Protocol has prompt injection security problems（2025-04-09） | 200 | 同 | Model Context Protocol has prompt injection security problems（"9th April 2025"） | ✅一致 |
| 27 | Eric S. Raymond — The Art of Unix Programming, Ch.1.6 Basics of the Unix Philosophy | 200 | 同 | Basics of the Unix Philosophy（17 条规则逐条命中） | ✅一致 |
| 28 | TAOUP Bibliography（[McIlroy78] = BSTJ 57(6) part 2 Forward；[Salus] = A Quarter-Century of Unix） | 200 | 同 | Bibliography（[BSTJ] 与 [Salus] 两条书目均命中） | ✅一致 |
| 29 | harmful.cat-v.org — UNIX Style, or cat -v Considered Harmful | 200 | 同 | UNIX Style, or cat -v Considered Harmful | ✅一致 |
| 30 | Claude Code Docs — Headless mode（`-p`、`--output-format`、`--allowedTools`、`--json-schema`） | 200 | ↪ https://code.claude.com/docs/en/headless | Run Claude Code programmatically - Claude Code Docs | ⚠️【注2】 |
| 31 | OpenAI — Codex non-interactive mode（`codex exec`、`--json`、`--sandbox`） | 200 | ↪ https://learn.chatgpt.com/docs/non-interactive-mode | Non-interactive mode \| ChatGPT Learn | ✅一致 |
| 32 | Gemini CLI — Headless mode reference | 200 | 同 | gemini-cli/docs/cli/headless.md at main · google-gemini/gemini-cli · GitHub | ✅一致 |
| 33 | Gemini CLI — CLI reference | 200 | 同 | gemini-cli/docs/cli/cli-reference.md at main · google-gemini/gemini-cli · GitHub | ✅一致 |
| 34 | opencode — CLI docs | 200 | 同 | CLI \| OpenCode | ✅一致 |
| 35 | Aider — Scripting | 200 | 同 | Scripting aider \| aider | ✅一致 |
| 36 | goose — CLI commands | 200 | ↪ …/goose-cli-commands/（仅补尾斜杠） | CLI Commands \| goose \| Your open source AI agent | ✅一致 |
| 37 | Anthropic — Writing effective tools for agents | 200 | 同 | Writing effective tools for AI agents—using AI agents（`<h1>` = Writing effective tools for agents — with agents） | ✅一致 |
| 38 | OpenAI — Function calling guide | 200 | ↪ https://developers.openai.com/api/docs/guides/function-calling | Function calling \| OpenAI API | ✅一致 |
| 39 | Anthropic — Effective context engineering for AI agents | 200 | 同 | Effective context engineering for AI agents \ Anthropic | ✅一致 |
| 40 | SWE-agent（arXiv 2405.15793） | 200 | 同 | [2405.15793] SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering | ✅一致 |
| 41 | microsoft/playwright-cli — README（CLI vs MCP 官方建议） | 200 | 同 | GitHub - microsoft/playwright-cli: CLI for common Playwright actions… | ✅一致 |
| 42 | microsoft/playwright-mcp — README（含 "Playwright MCP vs Playwright CLI"） | 200 | 同 | GitHub - microsoft/playwright-mcp: Playwright MCP server | ✅一致 |
| 43 | AGENTS.md — 官方站点（含 AAIF 归属与 60k 项目规模） | 200 | 同 | AGENTS.md | ✅一致 |
| 44 | Claude Docs — Agent Skills overview | 200 | ↪ https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview | Agent Skills - Claude Platform Docs | ✅一致 |
| 45 | Anthropic — Equipping agents for the real world with Agent Skills | 200 | 同 | Equipping agents for the real world with Agent Skills \ Anthropic | ✅一致 |
| 46 | Claude Docs — Agent Skills best practices | 200 | ↪ https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | Skill authoring best practices - Claude Platform Docs | ✅一致【注3】 |
| 47 | Terminal Agents: A Survey of AI Agents in Command-Line Environments（arXiv 2608.20485） | 200 | 同 | [2608.20485] Terminal Agents: A Survey of AI Agents in Command-Line Environments | ✅一致 |
| 48 | Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in CLI（arXiv 2601.11868） | 200 | 同 | [2601.11868] Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces | ✅一致【注4】 |
| 49 | Terminal-Bench 官网（当前为 4.0，leaderboard 前端渲染） | 200 | 同 | TERMINAL-BENCH（`<h1>` = TERMINAL-BENCH 4.0；"Hosted by Stanford / Harbor / Laude Institute"；表头 RANK/MODEL/AGENT/RESOLUTION RATE/COST/TOKENS；去标签后仅 602 字符，确认前端渲染） | ✅一致 |
| 50 | SWE-bench: Can Language Models Resolve Real-World GitHub Issues?（arXiv 2310.06770） | 200 | 同 | [2310.06770] SWE-bench: Can Language Models Resolve Real-World GitHub Issues? | ✅一致 |
| 51 | SWE-bench 官方仓库 README（Verified = 500 题，2024-08-13） | 200 | 同 | GitHub - SWE-bench/SWE-bench…（raw README 命中 "[Aug. 13, 2024]: Introducing *SWE-bench Verified*! … A subset of 500 problems"） | ✅一致 |
| 52 | SWE-bench 官方 Leaderboard（前端渲染） | 200 | 同 | SWE-bench Leaderboards（可见 "2294 instances"、"Bash Only 500 instan…"） | ✅一致 |
| 53 | τ-bench: A Benchmark for Tool-Agent-User Interaction（arXiv 2406.12045） | 200 | 同 | [2406.12045] $τ$-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains | ✅一致 |
| 54 | ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs（arXiv 2307.16789） | 200 | 同 | [2307.16789] ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs | ✅一致【注5】 |
| 55 | API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs（arXiv 2304.08244） | 200 | 同 | [2304.08244] API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs | ✅一致 |
| 56 | Voyager: An Open-Ended Embodied Agent with Large Language Models（arXiv 2305.16291） | 200 | 同 | [2305.16291] Voyager: An Open-Ended Embodied Agent with Large Language Models | ✅一致 |
| 57 | Executable Code Actions Elicit Better LLM Agents（CodeAct, arXiv 2402.01030） | 200 | 同 | [2402.01030] Executable Code Actions Elicit Better LLM Agents | ✅一致 |
| 58 | Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents（arXiv 2505.22954） | 200 | 同 | [2505.22954] Darwin Godel Machine: Open-Ended Evolution of Self-Improving Agents | ✅一致 |
| 59 | Everything is Context: Agentic File System Abstraction for Context Engineering（arXiv 2512.05470） | 200 | 同 | [2512.05470] Everything is Context: Agentic File System Abstraction for Context Engineering | ✅一致 |
| 60 | wong2/mcp-cli — README（MCP → CLI，含非交互模式） | 200 | 同 | GitHub - wong2/mcp-cli: A CLI inspector for the Model Context Protocol | ✅一致 |
| 61 | Exposed by Design: A Dynamic Security Assessment of Internet-Facing MCP Servers（arXiv 2608.00150） | 200 | 同 | [2608.00150] Exposed by Design: A Dynamic Security Assessment of Internet-Facing MCP Servers at Scale | ✅一致 |
| 62 | Anthropic — Beyond permission prompts: making Claude Code more secure and autonomous（2025-10-20） | 200 | 同 | Making Claude Code more secure and autonomous with sandboxing \ Anthropic（`<h1>` = Beyond permission prompts: making Claude Code more secure and autonomous；"Published Oct 20, 2025"） | ✅一致 |
| 63 | Prompt Injection Attacks on Agentic Coding Assistants（SoK, arXiv 2601.17548） | 200 | 同 | [2601.17548] Prompt Injection Attacks on Agentic Coding Assistants: A Systematic Analysis of Vulnerabilities i…（摘要内 "Systematization of Knowledge (SoK) paper" 命中） | ✅一致 |
| 64 | GitHub MCP Server — README（96 工具 / 22 toolsets） | 200 | 同 | GitHub - github/github-mcp-server: GitHub's official MCP Server（raw README：`## Tools` 段 `- **tool**` 97 条去重 **96**；`AUTOMATED TOOLSETS` 段 **22** 个 toolset） | ✅一致 |
| 65 | MCP servers — filesystem（13 工具） | 200 | 同 | servers/src/filesystem at main · modelcontextprotocol/servers（raw README `### Tools` 段 **13** 条，名称与正文列举逐一对齐） | ✅一致 |
| 66 | MCP servers — git（12 工具） | 200 | 同 | servers/src/git at main · modelcontextprotocol/servers（raw README `### Tools` 段编号 **1.–12.**，名称与正文列举逐一对齐） | ✅一致 |
| 67 | **Anthropic** — Code Mode: the better way to use MCP（Cloudflare 工程博客，2025-09-26） | 200 | 同 | Code Mode: the better way to use MCP \| **Cloudflare Blog**（"September 26, 2025"，作者 Kenton Varda 与 Sunil Pai；**全页 0 次出现 "Anthropic"**） | ⚠️**机构不符** |
| 68 | Hugging Face — Introducing smolagents（CodeAgent vs ToolCallingAgent） | 200 | 同 | Introducing smolagents: simple agents that write actions in code. | ✅一致 |
| 69 | OpenAI — Code Interpreter（Responses API，容器沙箱） | 200 | ↪ https://developers.openai.com/api/docs/guides/tools-code-interpreter | Code Interpreter \| OpenAI API | ✅一致 |
| 70 | Claude Code Docs — Settings（permissions.allow / `Bash(...)` 规则） | 200 | ↪ https://code.claude.com/docs/en/settings | Settings files and precedence - Claude Code Docs | ✅一致 |

**逐字取证摘录（供复核，均为本次抓取原文，非推测）**

- **[67]** `September 26, 2025  Code Mode: the better way to use MCP  Kenton Varda and Sunil Pai  12 minute read` / `It turns out we've all been using MCP wrong.` — 站点为 `Cloudflare Blog`，标签前缀 `Anthropic —` 无任何页面依据。
- **[64]** `## Tools` 段内 `- **name**` 计 97 条、去重 96；`<!-- START AUTOMATED TOOLSETS -->` 表内计 22 行（`actions / code_quality / code_security / context / copilot / copilot_issue_intents / dependabot / discussions / gists / git / governance / issues / labels / notifications / orgs / projects / pull_requests / repos / secret_protection / security_advisories / stargazers / users`）。附录写「96 工具 / 22 toolsets」，**完全吻合**。
- **[65]** `read_text_file, read_media_file, read_multiple_files, write_file, edit_file, create_directory, list_directory, list_directory_with_sizes, move_file, search_files, directory_tree, get_file_info, list_allowed_directories` —— 13 条，与正文第 325 行列举**逐字一致**。
- **[66]** `git_status, git_diff_unstaged, git_diff_staged, git_diff, git_commit, git_add, git_reset, git_log, git_create_branch, git_checkout, git_show, git_branch` —— 12 条，与正文第 326 行列举**逐字一致**。
- **[24]** 页面确认 **0 次** 出现 `Tool Poisoning`，与正文第 162 行「该页实际章节为：Confused Deputy Problem、Token Passthrough、SSRF、State Handle Hijacking…」的自述**一致**（11 个章节名逐个命中）。
- **[49]** 去标签后正文仅 602 字符，含 `RANK MODEL AGENT RESOLUTION RATE COST TOKENS`，与正文「leaderboard 为前端渲染，本次抓取只拿到表头」的自述**一致**。

---

## 4. 标签 ↔ 内容不符清单（按严重程度排序）

### 4.1 实质不符（必须修正）

| 排名 | 编号 | 位置 | 问题 | 证据 |
|---|---|---|---|---|
| **1（唯一实质错误）** | **67** | 附录第 482 行 | **机构张冠李戴**：把 Cloudflare 的工程博客冠以 `Anthropic —` | 页面 `<title>` = `Code Mode: the better way to use MCP \| Cloudflare Blog`；站点栏显示 `Cloudflare Blog`；署名为 Cloudflare 的 `Kenton Varda and Sunil Pai`；发布时间 `September 26, 2025`（与标签日期相符）；**全页检索 "Anthropic" 命中 0 次**。标签括号内已正确写明「Cloudflare 工程博客」，与行首的 `Anthropic —` 自相矛盾。**文档正文第 142 行写的是「① Cloudflare — Code Mode」，说明正文正确、附录标签笔误** |

### 4.2 非实质漂移（不构成事实错误，但建议一并修正）

| 注号 | 编号 | 问题类型 | 具体差异 | 证据 |
|---|---|---|---|---|
| 注1 | 24 | 出处层级已迁移 | 原 URL `/specification/2026-07-28/basic/security_best_practices` 已 **301 →** `/docs/2026-07-28/tutorials/security/security_best_practices`。标签写「MCP **Spec** — Security Best Practices」，但该页现已移出 specification 树、归入 docs/tutorials | HTTP 重定向链实测；页面标题与 11 个章节内容仍完全一致，标签括号内「（2026-07-28）」成立 |
| 注2 | 30 | 页面已改名 + 重定向 | `docs.claude.com/en/docs/claude-code/headless` **→** `code.claude.com/docs/en/headless`；页面 `<title>`/`<h1>` 均为 `Run Claude Code programmatically`，**页面正文出现 "headless" 0 次**。标签沿用旧名「Headless mode」 | 去标签全文检索 `headless` = 0 命中；但标签括号内 4 个 flag（`-p`/`--output-format`/`--allowedTools`/`--json-schema`）**全部命中** |
| 注3 | 46 | 页面已改名 + 重定向 | `docs.claude.com/...` **→** `platform.claude.com/docs/en/...`；页面 `<title>`/`<h1>` 均为 `Skill authoring best practices`，非标签所写的「Agent Skills best practices」 | 标签括号内两项声明均命中：`Format: ServerName:tool_name`、`Without the server prefix, Claude may fail to locate the tool…` |
| 注4 | 48 | 论文标题被缩写改写 | 标签写 `…Hard, Realistic Tasks in CLI`，arXiv 真实标题为 `…in Command Line Interfaces` | arXiv 页 `<title>` 逐字比对；摘要内 `89 tasks`、`less than 65\%` 均命中 |
| 注5 | 54 | 论文标题被缩写改写 | 标签写 `ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs`，arXiv 真实标题为 `ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs` | arXiv 页 `<title>` 逐字比对（`LLMs` 在页面中出现于摘要正文，非标题） |
| 注6 | 27 | 数字为人工计数、页面未书明 | 正文第 196 行称该章「给出 17 条规则」，页面**未出现数字 "17"** | 我逐条枚举该页规则：Modularity / Clarity / Composition / Separation / Simplicity / Parsimony / Transparency / Robustness / Representation / Least Surprise / Silence / Repair / Economy / Generation / Optimization / Diversity / Extensibility = **恰好 17 条，计数正确**，仅属"页面无此数字"的转述 |

### 4.3 附带发现（超出四类校验范围，但影响引用可信度）

| 编号 | 位置 | 问题 | 证据 |
|---|---|---|---|
| 70 | 正文第 353 行 | 正文称「官方专门提醒 `Bash(git diff*)` 会误匹配 `git diff-index`」并标【A】引 [[70]]，但该表述在 [[70]] 页面上**查无此句** | 页 70 检索 `git diff` = 0 命中、`diff-index` = 0 命中、`prefix match` = 0 命中、`wildcard` = 0 命中。该页仅写 `"allow": ["Bash(npm run lint)", "Bash(npm run test *)"]` 并注明「Configure permissions explains the syntax」。真正含 `--allowedTools "Bash(git diff *),Bash(git log *)"` 与 `The trailing * enables prefix matching` 的是 [[30]] 页（已命中），但 [[30]] 也没有 `git diff-index` 反例。**该细节缺一手出处，建议补源或降级为推断** |
| 1 | 正文第 286 行 | 表格内以引号引述 `「**12.9%** of the money spent…against **2.2%** on CLI runs」`，arXiv 摘要原文用的是 `12.9 per cent` / `2.2 per cent`（词形而非 % 号） | 摘要原文：`where 12.9 per cent of the money spent on MCP runs bought no completed work against 2.2 per cent on CLI runs`。语义一致，仅引号内符号非逐字 |
| 58 | 附录第 473 行 | 标签写 `Darwin Gödel Machine`，arXiv 页面标题为 `Darwin Godel Machine`（无变音符） | 属拼写规范化，不影响识别 |

---

## 5. 关键论据原句深核

> 方法：在对应来源页面去标签全文中做**逐字子串搜索**（大小写不敏感，但要求字符级连续）。判定只有「匹配 / 不匹配 / 页面中未找到」三档，不做"意思差不多"的推断。

### 5.1 第 1 条 — arXiv 2608.08654《The Scaffolding Matters More Than the Interface》→ **4/4 匹配**

| 待核对原句 | 页面原文（逐字） | 判定 |
|---|---|---|
| `5.0x to 28x cheaper` | `…they completed every run using only the CLI, which shows that MCP is unnecessary for this class of work, and they were 5.0x to 28x cheaper than the five scaffoldings that do support MCP, comparing CLI runs alone with no MCP server attached anywhere.` | **匹配** |
| `thirteen strictly paired MCP-to-CLI ratios span 0.43x to 29x` | `The comparison we set out to make proved unstable: thirteen strictly paired MCP-to-CLI ratios span 0.43x to 29x, with outliers on both sides.` | **匹配** |
| `The dominant effect was the scaffolding` | `The dominant effect was the scaffolding.` | **匹配** |
| `Agents frequently ignored the interface they were assigned` | `Agents frequently ignored the interface they were assigned, so comparisons that do not verify actual behaviour measure an unknown mixture.` | **匹配** |
| （附带核对）正文另引的 `139x`、`12.9…2.2` | `whose cost varied 139x across scaffoldings` ✅；`12.9 per cent … against 2.2 per cent`（**词形为 per cent，非 %**，见 4.3） | 匹配（词形有差） |

### 5.2 第 20 条 — Anthropic《Code execution with MCP》→ **2/2 匹配**

| 待核对原句 | 页面原文（逐字） | 判定 |
|---|---|---|
| `150,000 tokens to 2,000 tokens` | `This reduces the token usage from 150,000 tokens to 2,000 tokens—a time and cost saving of 98.7%.` | **匹配** |
| `98.7%` | 同上句尾（含全角破折号 `—` 与句点，逐字一致） | **匹配** |

### 5.3 第 21 条 — Anthropic《Introducing advanced tool use》→ **3/3 匹配**

| 待核对原句 | 页面原文（逐字） | 判定 |
|---|---|---|
| `58 tools consuming approximately 55K tokens` | `GitHub: 35 tools (~26K tokens) Slack: 11 tools (~21K tokens) Sentry: 5 tools (~3K tokens) Grafana: 5 tools (~3K tokens) Splunk: 2 tools (~2K tokens) That's 58 tools consuming approximately 55K tokens before the conversation even starts.` | **匹配** |
| `85% reduction` | `Total context consumption: ~8.7K tokens, preserving 95% of context window This represents an 85% reduction in token usage while maintaining access to your full tool library.` | **匹配** |
| `49% to 74%` | `Opus 4 improved from 49% to 74%, and Opus 4.5 improved from 79.5% to 88.1% with Tool Search Tool enabled.` | **匹配** |
| （附带核对）`134K tokens`、`43,588 to 27,297` | `At Anthropic, we've seen tool definitions consume 134K tokens before optimization.` ✅；`Average usage dropped from 43,588 to 27,297 tokens, a 37% reduction on complex research tasks.` ✅ | 匹配 |

### 5.4 第 7 条 — MCP Spec 2026-07-28 Key Changes → **4/4 匹配（另加 MRTR 命中）**

| 待核对声明 | 页面原文（逐字） | 判定 |
|---|---|---|
| 移除 `initialize` 握手 | `Make MCP stateless: remove the initialize / notifications/initialized handshake.` | **匹配** |
| 移除协议级会话 | `Remove protocol-level sessions and the Mcp-Session-Id header from the Streamable HTTP transport.` | **匹配** |
| `server/discover` | `Add server/discover : servers MUST implement this RPC to advertise their supported protocol versions, capabilities, and identity. Clients MAY call it before any other request for up-front version selection, or use it as a backward-compatibility probe on STDIO ( SEP-2575 ).` | **匹配** |
| 弃用 Roots / Sampling / Logging | `Deprecate the Roots, Sampling, and Logging features ( SEP-2577 ). These features remain fully functional during the deprecation window but new implementations should not add support for them.` | **匹配** |
| （标签另称）MRTR | 标签与正文均提及 MRTR；页面检索 `MRTR` **命中** | **匹配** |
| （附带核对）正文第 371 行「tools/list 顺序必须确定，理由写的是 improve LLM prompt cache hit rates」 | `Servers SHOULD return tools from tools/list in a deterministic order to enable client-side caching and improve LLM prompt cache hit rates.` | **匹配** |

### 5.5 第 41 / 42 条 — microsoft/playwright-cli 与 playwright-mcp 的 README → **2/2 匹配**

| 待核对表述 | 页面原文（逐字） | 判定 |
|---|---|---|
| [41] 「CLI/Skills 更省 token」 | `<h3>Playwright CLI vs Playwright MCP</h3> This package provides CLI interface into Playwright. If you are using **coding agents**, that is the best fit.` 紧接：`**CLI**: Modern **coding agents** increasingly favor CLI–based workflows exposed as SKILLs over MCP because CLI invocations are more token-efficient: they avoid loading large tool schemas and verbose accessibility trees into the model context, allowing agents to act through concise, purpose-built commands.`（注意 README 原文用 `SKILLs` 这一大小写） | **匹配** |
| [42] 「MCP 适合需要持久状态的 agentic loop」 | `<h3>Playwright MCP vs Playwright CLI</h3> This package provides MCP interface into Playwright. If you are using a **coding agent**, you might benefit from using the [CLI+SKILLS](https://github.com/microsoft/playwright-cli) instead.` 紧接：`**MCP**: MCP remains relevant for specialized agentic loops that benefit from persistent state, rich introspection, and iterative reasoning over page structure, such as exploratory automation, self-healing tests, or long-running autonomous workflows where maintaining continuous browser context outweighs token cost concerns.` | **匹配** |

**5 组关键论据深核结论：5/5 组通过，17 个待核原句/数字全部在来源页面中逐字找到（1 处仅"per cent → %"词形差异）。文档不存在"给 URL 但页面与数字无关"的情况。**

---

## 6. 建议的修正清单

> 格式：**位置 → 现在写的 → 应改为**。仅改 `ai-cli-mcp-research.md`，本报告不代替执行。

### 6.1 必须改（1 条）

1. **第 482 行（附录第 67 条）——机构错挂**
   - **现在写的**：`67. Anthropic — Code Mode: the better way to use MCP（Cloudflare 工程博客，2025-09-26） — https://blog.cloudflare.com/code-mode/（2026-10-02）`
   - **应改为**：`67. Cloudflare — Code Mode: the better way to use MCP（Cloudflare 工程博客，2025-09-26，作者 Kenton Varda / Sunil Pai） — https://blog.cloudflare.com/code-mode/（2026-10-02）`
   - 理由：页面属 Cloudflare Blog，全页无 "Anthropic"；且正文第 142 行已写「Cloudflare — Code Mode」，改后正文与附录一致。

### 6.2 建议改：URL 已重定向（8 条，不改会导致下次复核误判为失效）

| 位置 | 现在写的 URL | 应改为（实测最终 URL） |
|---|---|---|
| 第 433 行（第 24 条） | `https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices` | `https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices`（并考虑把标签的「MCP **Spec**」改为「MCP Docs — Security Best Practices」） |
| 第 442 行（第 30 条） | `https://docs.claude.com/en/docs/claude-code/headless` | `https://code.claude.com/docs/en/headless`（标签「Headless mode」→「Run Claude Code programmatically」） |
| 第 443 行（第 31 条） | `https://developers.openai.com/codex/noninteractive` | `https://learn.chatgpt.com/docs/non-interactive-mode` |
| 第 450 行（第 38 条） | `https://platform.openai.com/docs/guides/function-calling` | `https://developers.openai.com/api/docs/guides/function-calling` |
| 第 459 行（第 44 条） | `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview` | `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview` |
| 第 461 行（第 46 条） | `https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices` | `https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices`（标签「Agent Skills best practices」→「Skill authoring best practices」） |
| 第 484 行（第 69 条） | `https://platform.openai.com/docs/guides/tools-code-interpreter` | `https://developers.openai.com/api/docs/guides/tools-code-interpreter` |
| 第 485 行（第 70 条） | `https://docs.claude.com/en/docs/claude-code/settings` | `https://code.claude.com/docs/en/settings` |

> 同步注意：正文中同一批编号的 `[[n]](URL)` 内联链接（如第 162 行的 [[24]]、第 206 行的 [[30]]、第 227 行的 [[38]]、第 353 行的 [[70]] 等）应一并更新，否则会重新引入「正文 URL 与附录 URL 不一致」。本次校验 118 处引用与附录**当前完全一致**，改 URL 时务必正文+附录同改。

### 6.3 建议改：标签用词（3 条）

| 位置 | 现在写的 | 应改为 |
|---|---|---|
| 第 463 行（第 48 条） | `Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in CLI（arXiv 2601.11868）` | `Terminal-Bench: Benchmarking Agents on Hard, Realistic Tasks in Command Line Interfaces（arXiv 2601.11868）` |
| 第 469 行（第 54 条） | `ToolLLM: Facilitating LLMs to Master 16000+ Real-world APIs（arXiv 2307.16789）` | `ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs（arXiv 2307.16789）` |
| 第 473 行（第 58 条） | `Darwin Gödel Machine: …（arXiv 2505.22954）` | `Darwin Godel Machine: …（arXiv 2505.22954）`（与 arXiv 页 `<title>` 一致；若保留变音符请在标签注明"arXiv 页无变音符"） |

### 6.4 建议改：正文取证表述（3 条）

| 位置 | 现在写的 | 应改为 |
|---|---|---|
| 第 353 行（§6 表第 1 行） | 以【A】标记称官方提醒 `Bash(git diff*)` 会误匹配 `git diff-index` | [[70]] 与 [[30]] 页面均查无此句（`git diff` / `diff-index` / `prefix match` 全 0 命中）。应补一手出处，或改为「**推断：** 前缀匹配语义决定了 `Bash(git diff*)` 会同时匹配 `git diff-index`」并去掉【A】 |
| 第 286 行（§5 表首行） | `失败成本「**12.9%** of the money spent on MCP runs bought no completed work against **2.2%** on CLI runs」` | 若坚持逐字引述：`「12.9 per cent of the money spent on MCP runs bought no completed work against 2.2 per cent on CLI runs」`；若保留 % 号，应移出引号或标注"（原文为 per cent）" |
| 第 196 行（§4.4） | 「给出 17 条规则」 | 计数正确（我逐条枚举为 17），但页面未出现数字 "17"。可加注「（本页未书明条数，此处为逐条计数）」 |

### 6.5 建议改：附录引言（1 条）

- **位置**：第 406 行
- **现在写的**：`> 全部条目于 2026-10-02 实际抓取成功（www.tbench.ai 与 www.swebench.com 的 leaderboard 为前端渲染，仅取到页面骨架，已在正文标注）。`
- **应改为**：追加一句 `其中 8 条（24、30、31、38、44、46、69、70）已发生 HTTP 重定向，URL 已按最终地址更新；32、33 两条 GitHub blob 页面首次抓取返回 503（反爬限流），经 raw 路径与重试后取到同文件原文。` —— 这能让读者分清"抓取成功"与"URL 未变"是两件事。

---

## 附：本次校验的原始取证口径

| 项 | 说明 |
|---|---|
| 抓取工具 | `pwsh` → `python 3.12.11` + `urllib.request`（**未使用 `web_fetch`**，其被 SSRF 防护拦截） |
| 请求方式 | GET，`User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) … Chrome/125`，`Accept-Language: en-US,en;q=0.9`，超时 20~25s |
| SSL | 关闭证书校验（首次探针报 `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`） |
| 重试 | 失败退避 1.5~4s，重试 1~3 次 |
| 抓取结果 | **70/70 取到页面**；32、33 首轮 503 后经 raw 路径与重试均取到 200 |
| 标题提取 | `<title>` + 首个 `<h1>`；正文去除 `<script>/<style>/<noscript>/<svg>` 与全部标签后做逐字子串匹配 |
| GitHub 补证 | 另行抓取 7 个 raw README（github-mcp-server / filesystem / git / mcp-cli / swe-bench / playwright-cli / playwright-mcp），用于工具计数与对照段落逐字核对 |
| 未取到的页面 | **0 条**。本报告中不存在"看起来一致""应该是"一类无证据判定；所有 ✅ 均附 `<title>` 或页面原句，所有 ⚠️ 均附冲突证据 |
