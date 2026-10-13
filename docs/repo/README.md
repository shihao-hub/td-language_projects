# 仓库级文档与技术调研库（docs/repo）

> 本目录收录 **`language_projects` 仓库级基础设施规范、环境配置演进记录与前沿技术调研报告**。  
> 遵循「一手权威信源追踪、架构机理深度溯源、权衡替代方案完整」的调研准则，作为跨 Agent 协同与项目工程决策的底层知识资产。

---

## 一、AI Agent、IDE 与终端架构调研

覆盖现代 AI 编程助手、终端模拟器、协议扩展与多会话调度架构的深度调研：

| 文档 | 核心主题与摘要 |
|---|---|
| [windows-terminal-dsh-embedding-research.md](windows-terminal-dsh-embedding-research.md) | **Windows Terminal 嵌入 DSH (Electron) 技术可行性与底层架构调研**<br>剖析 WinUI 3 / XAML Islands、ConPTY 字符管道、Win32 `SetParent` 跨进程死锁、Chromium DirectComposition 渲染黑洞及窗口平铺替代方案。 |
| [antigravity-acp-architecture-research.md](antigravity-acp-architecture-research.md) | **Antigravity ACP (Agent Client Protocol) 架构调研**<br>调研 Agent Client Protocol 协议设计、双向通信通道与多客户端接入模型。 |
| [pi-and-dsh-acp-support-research.md](pi-and-dsh-acp-support-research.md) | **Pi 与 DSH 的 ACP 协议支持调研**<br>分析 Pi 运行时与 DeepSeek Harness 对 ACP 协议的标准支持现状与改造路径。 |
| [zed-multi-session-agent-architecture-research.md](zed-multi-session-agent-architecture-research.md) | **Zed 多会话 Agent 架构调研**<br>分析 Zed 编辑器多 Agent 并发会话机制、状态同步与上下文隔离机制。 |
| [zed-edit-prediction-providers-research.md](zed-edit-prediction-providers-research.md) | **Zed 编辑预测（Edit Prediction）提供商调研**<br>分析 Zed 的次世代行内预测补全（Inline Completion）提供商协议与架构。 |
| [ai-cli-mcp-research.md](ai-cli-mcp-research.md) | **AI CLI 与 MCP 架构调研**<br>探讨主流 AI 命令行工具与 Model Context Protocol (MCP) 的标准集成规范。 |
| [ai-cli-mcp-local-agent-cli-survey.md](ai-cli-mcp-local-agent-cli-survey.md) | **本地 Agent CLI 工具全景调研**<br>横向对比 Claude Code、Codex、OpenCode、Aider 等本地命令行 Agent 的架构与差异。 |
| [ai-cli-mcp-research-verification.md](ai-cli-mcp-research-verification.md) | **AI CLI MCP 调研验证报告**<br>针对 MCP 工具调用、协议握手与上下文传递的端到端实测验证。 |
| [mcp-2026-07-28-delta.md](mcp-2026-07-28-delta.md) | **MCP 增量演进分析（2026-07-28）**<br>跟踪 Model Context Protocol 最新规范变动、新特性与迁移指南。 |
| [subagent-pipeline-tools-research.md](subagent-pipeline-tools-research.md) | **Subagent 流水线工具链调研**<br>分析多子代理流水线编排、上下文交接与任务分解工具链。 |
| [agent-session-handoff-research.md](agent-session-handoff-research.md) | **Agent 会话交接（Session Handoff）机制调研**<br>跨模型、跨工具会话无缝交接与状态持久化架构方案。 |
| [fill-in-the-middle-research.md](fill-in-the-middle-research.md) | **Fill-in-the-Middle (FIM) 代码补全技术调研**<br>剖析大模型中间填充代码生成的 Prompt 构造与工程实践。 |
| [Qwen3.8-27B 本地部署配置调研.md](Qwen3.8-27B%20本地部署配置调研.md) | **Qwen3.8-27B 本地部署与配置调研**<br>针对显存分配、量化策略（GGUF/AWQ）与推理后端的实测调优。 |

---

## 二、系统架构、网络协议与方法论调研

覆盖系统底座、微服务架构、网络协议与代码工程方法论：

| 文档 | 核心主题与摘要 |
|---|---|
| [K8S 核心声明式调和链路原理剖析与自研架构设计.md](K8S%20核心声明式调和链路原理剖析与自研架构设计.md) | **K8S 声明式调和链路与自研控制器架构**<br>深入解析 Informer、DeltaFIFO、WorkQueue、Reconciliation Loop 机制与 Mini 框架实现。 |
| [MQTT 与 WebSocket 协议.md](MQTT%20与%20WebSocket%20协议.md) | **MQTT 与 WebSocket 协议选型对比**<br>评估双向流式通信、轻量长连接与高并发场景下的协议差异与落地策略。 |
| [nosql-vs-rdbms-architecture-research.md](nosql-vs-rdbms-architecture-research.md) | **NoSQL vs RDBMS 架构选型调研**<br>针对多范式数据存储、ACID 事务与水平扩展场景的技术选型指南。 |
| [jupyterlab-overview-and-architecture-research.md](jupyterlab-overview-and-architecture-research.md) | **JupyterLab 架构全景与扩展机制调研**<br>分析 Lumino 界面组件模型、Kernel 通信协议与扩展开发体系。 |
| [Python 模块结构与常量放置规范调研.md](Python%20模块结构与常量放置规范调研.md) | **Python 模块结构与常量放置规范调研**<br>统一单文件 Python 骨架与常量集中置顶（打开即见）的规范来源依据。 |
| [docs 阅读体验调研：SQLite 存档 vs Markdown 源 + 静态站点.md](docs%20阅读体验调研：SQLite%20存档%20vs%20Markdown%20源%20+%20静态站点.md) | **文档阅读体验方案调研**<br>对比本地 SQLite 全文检索与 Markdown + Material for MkDocs 静态站架构。 |
| [media-storage-abuse-research.md](media-storage-abuse-research.md) | **媒资存储滥用与防护机制调研**<br>分析对象存储防刷、CDN 鉴权与防盗链治理方案。 |
| [douyin-ai-philosophy-video-creation-research.md](douyin-ai-philosophy-video-creation-research.md) | **抖音 AI 哲学视频创作自动化调研**<br>从脚本生成、配音到画面的自动化视频流水线全链路调研。 |
| [源码阅读方法调研.md](源码阅读方法调研.md) | **源码阅读方法论调研**<br>从宏观全景、调用链路到动态追踪的源码认知模型。 |

---

## 三、仓库基础设施、配置与工程规范

| 文档 | 核心主题与摘要 |
|---|---|
| [Git 子模块分支机制.md](Git%20子模块分支机制.md) | **Git 子模块分支机制与多端同步规范**<br>规范 Monorepo 中多个语言子仓与 skills 子模块的指针跟踪机制。 |
| [Git 子模块临时注销（native、rust）.md](Git%20子模块临时注销（native、rust）.md) | **Git 子模块临时注销与轻量拉取指南**<br>高频开发时对重型或暂不使用的语言子仓进行局部注销与环境瘦身。 |
| [AutoHotkey 极速应用切换与 Toggle 自动化配置指南.md](AutoHotkey%20极速应用切换与%20Toggle%20自动化配置指南.md) | **AutoHotkey 极速应用切换与 Toggle 自动化配置指南**<br>单手盲切多开发工具与无痛多桌面切换的实战配置。 |
| [参考-鱼皮-7个神级技巧去AI味.md](参考-鱼皮-7个神级技巧去AI味.md) | **参考：7 个神级技巧去 AI 味**<br>提升人机协作产出自然度、摆脱模板化表达的文案与前端设计技巧。 |
