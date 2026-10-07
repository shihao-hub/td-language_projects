# DeepSeek Harness (DSH) 暴露为 MCP Server 作为 Subagent 委派调用的技术调研

## 一、背景与核心概念辨析

### 1. 为什么“把 DSH 当作 Subagent 委派调用”？
在目前（2026年）的多 Agent 协作体系中，开发者通常在终端使用 **Claude Code**，或在编辑器中使用 **Cursor / Antigravity / Codex** 作为主力驾驶员（Orchestrator）。
然而，DeepSeek Harness (dsh) 作为 DeepSeek 开源的 Agent 底盘系统，具有主力 Agent 不具备的独特价值：

1. **底盘模型多样且可控**：
   DSH 是一个模型中立底盘（Model-Agnostic Chassis），本地配置了如 `glm-5.3`（`reasoningEffort: max`）、`zai-coding-cn` 等高阶大模型，且调用成本与本地化程度高。
2. **专属沙箱环境与运行时隔离**：
   DSH 内置了隔离的 Python 3.12、Node.js 运行时（如 `dsh-primary-runtime`）与专属第三方依赖环境。主力 Agent 遇到风险脚本、复杂数据分析、文档处理时，无需污染主机环境。
3. **长期记忆与轨迹透明性（Full Trajectory Transparency）**：
   DSH 的设计哲学是“模型可见即记录”，自带 Session 快照、`ThoughtDAG` 思维有向无环图、本地知识与技能面板（`@local/skills-panel`）。
4. **Harness 本行：自动化评测夹具与批处理**：
   DSH 天然是一个测试与仿真夹具，适合作为后台子智能体自主跑测试、跑 E2E、生成评测报告。

### 2. 所谓“Subagent 委派”的交互全景
```
[ 用户 (User) ]
       │
       ▼  提问 / 下发复合开发任务
[ 主力 Agent (Claude Code / Cursor / Antigravity) ]  ─── 主驾驶 / 编排者
       │
       ├─ 普通工作: 文件编辑、终端执行、代码阅读
       │
       └─ 当遇到深度推理 / 沙箱评测 / 记忆检索 / 独立子任务时:
              │
              ▼  MCP Tool Call: dsh_spawn_task(prompt, workspace)
       ┌────────────────────────────────────────────────────────┐
       │             dsh-mcp-server (桥接中枢)                   │
       └────────────────────────────────────────────────────────┘
              │  IPC / CLI / Cordis Plugin RPC
              ▼
       [ DeepSeek Harness (dsh) 守护进程 / 隔离沙箱 ] ─── 专属打工人 (Subagent)
              │
              ├─ 独立加载 glm-5.3 / 本地模型进行长思维链推理
              ├─ 在 dsh-primary-runtime 隔离沙箱内跑仿真
              └─ 输出结构化结论、执行日志摘要与产物路径
              │
              ▼  Tool Result (返回精炼结果，防止 Token 爆炸)
[ 主力 Agent 吸收子任务成果，继续推进主线 ]
```

---

## 二、DSH 对外暴露的三种技术路线对比

经过对 DSH 架构（Cordis 微内核、`ds-harness-remote` 远程协议、`dsh` CLI）的深入剖析，主要有以下三种实现路线：

| 维度 | 方案 A：独立 CLI/Headless MCP Server（推荐先行） | 方案 B：Cordis 原生 Plugin 暴露 MCP 端点 | 方案 C：基于 ACP (Agent Client Protocol) 桥接 |
| :--- | :--- | :--- | :--- |
| **工作原理** | 编写轻量 Python/Node 脚本作为标准 MCP Server，内部通过 `dsh` CLI 非交互模式或子进程触发任务 | 在 `dsh-local-plugins` 中开发一个 Cordis 插件，DSH 启动时监听本地端口暴露 MCP SSE/HTTP | 利用 DSH 内部已有的 ACP 模块与远程协议桥接 |
| **接入成本** | **极低**（单个独立文件，无需触碰 DSH 核心包） | 中等（需编写 Cordis 插件并注入生命周期） | 较高（需维护 WebRTC / 双向流连接） |
| **与宿主兼容性** | **100% 兼容**（Claude Code, Cursor, Codex, Pi, Antigravity 均支持 stdio） | 需支持 HTTP/SSE 传输的 Agent 宿主 | 仅支持 ACP 协议的客户端（如 Zed） |
| **上下文隔离性** | **完全隔离**（每次任务为一个独立 sub-session） | 共享当前桌面 DSH 运行态与插件上下文 | 共享当前会话 |
| **推荐阶段** | **Phase 1（立即可用，开箱即用）** | **Phase 2（桌面增强，长连接常驻）** | 作为备用远端同步通道 |

---

## 三、Subagent MCP 的核心工具契约设计

为了让主 Agent 能够清晰、直观、不出错地调度 DSH，MCP Server 应暴露以下核心 Tool：

1. **`dsh_execute(prompt: string, context_files?: string[], model?: string)`**
   - **作用**：向 DSH 下发一个自治任务，DSH 启动思考与工具链，跑完后返回最终结论与产生的文件。
2. **`dsh_eval_suite(suite_path: string)`**
   - **作用**：运行 DSH 自动化评测夹具，对指定代码进行严格的 E2E 或基准测试，返回测试通过率与失败诊断。
3. **`dsh_sandbox_run(code: string, language?: string)`**
   - **作用**：借用 DSH 的隔离 Python/Node 环境执行脚本，防止在主机直接执行高危或依赖缺失的代码。
4. **`dsh_query_trajectory(session_id: string)`**
   - **作用**：按需追溯 DSH 某次子任务的完整思考轨迹（ThoughtDAG / Trajectory），避免在初次返回时因输出过大撑爆主 Agent 窗口。

---

## 四、防 Token 爆炸与防护机制

主 Agent 调用 Subagent 最常遇到的故障是 **“Subagent 输出成千上万行日志，把主 Agent 的上下文瞬间打崩”**。
因此在 DSH MCP Server 设计中必须内置：
1. **Result Summarizer（结果精炼器）**：仅返回 `status`（成功/失败）、`conclusion`（核心结论）、`created_files`（改动文件列表）以及最近 30 行控制台摘要。
2. **Trajectory on Demand（按需拉取轨迹）**：完整思考日志存为本地临时文件或 session db，仅向主 Agent 返回访问路径或 ID。
3. **Timeout Guard（超时守卫）**：单个 Subagent 任务严格限制执行上限（默认 120 秒），防止死循环挂死宿主。
