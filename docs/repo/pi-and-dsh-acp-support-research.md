# Pi Agent 与 DSH 对 Zed ACP 协议支持现状与计划调研

> **元信息**
> - **调研主题**：Pi Agent（Mario Zechner / Earendil Works）与 DSH（DeepSeek Harness）在 Zed 及 ACP Registry 中的支持现状与规划
> - **调研更新时间**：2026-10-11
> - **落盘路径**：`docs/repo/pi-and-dsh-acp-support-research.md`
> - **权威主源**：Zed 官方 ACP Registry 实时清单 (`https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json`)、`agentclientprotocol/registry` 仓库、`@deepseek-ai/dsh` (npm 0.2.0-rc.2)、`earendil-works/pi` 讨论区

---

## 0. 核心结论与用户疑虑解答 (TL;DR)

用户的观察是完全准确的：
1. **Pi 在 Zed ACP Registry 中确实没有“官方”支持**：
   - 注册表中唯一的条目是 **`pi-acp`**（显示名称为 `pi ACP`，v0.0.34），由社区开发者 **Sergii Kozak** 维护，本质是一个**第三方适配器**（桥接 `pi --mode rpc`）。
   - Pi 官方（Mario Zechner / Earendil Works）秉持极简核心哲学，**目前并未官方内置 ACP 协议，也未官方提交注册表**。
2. **DSH 在 Zed ACP Registry 中确实完全搜不到**：
   - 官方 ACP Registry 全量 41 款 Agent 清单中，**未收录任何 `dsh` 或 `deepseek` 条目**。
   - 虽然 `@deepseek-ai/dsh`（当前最新为 `0.2.0-rc.2`）已经在底层依赖并实现了 `@deepseek-ai/dsh-acp-app`，但官方**尚未向 Zed / ACP 官方 Registry 提交上架 PR**，因此在图形化商店中无法直接检索到。

---

## 1. 官方 ACP Registry 实测清单核验 (2026-10-11)

抓取 `https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json`，当前全量已上架的 41 个 Agent 包括：
`agoragentic-acp`, `amp-acp`, `antigravity-acp`, `auggie`, `autohand`, `claude-acp`, `cline`, `codebuddy-code`, `codex-acp`, `cortex-code`, `corust-agent`, `crow-cli`, `cursor`, `deepagents`, `devin`, `dimcode`, `dirac`, `factory-droid`, `fast-agent`, `gemini`, `github-copilot-cli`, `glm-acp-agent`, `goose`, `grok-build`, `harn`, `junie`, `kilo`, `kimchi`, `kimi`, `minimax-code`, `minion-code`, `mistral-vibe`, `nova`, `opencode`, **`pi-acp`**, `poolside`, `qoder`, `qwen-code`, `sigit`, `stakpak`, `vtcode`。

### 1.1 Pi 的收录详情
- **ID**: `pi-acp`
- **Name**: `pi ACP`
- **Description**: `ACP adapter for pi coding agent`
- **Author**: `Sergii Kozak <svkozak@gmail.com>`
- **Repository**: `https://github.com/svkozak/pi-acp`
- **性质**: **纯社区包装层**，通过 `npx pi-acp` 启动。

### 1.2 DSH 的收录情况
- **无匹配条目**（仅有 LangChain 的 `deepagents`）。

---

## 2. 详细原因与官方规划

### 2.1 Pi Agent（Mario Zechner / Earendil Works）
- **官方态度**：在 `earendil-works/pi` 的 GitHub Issue #175 和 Discussion #4444 中，Mario Zechner（`@badlogic`）指出：
  - Pi 核心必须保持极度轻量与无状态，避免绑定任何特定 IDE 交互协议的快速迭代。
  - Pi 原生只提供基于 stdio 的 JSON-lines RPC 接口（`pi --mode rpc`）。
  - 编辑器生态（如 Zed、JetBrains）的适配交给社区适配器（即 `pi-acp`）完成。
  - 因此，**短期内 Pi 官方不会在核心库中原生支持 ACP，也不会作为官方主体上架 Zed Registry**。

### 2.2 DSH（DeepSeek Harness）
- **代码层现状**：
  - npm 上的 `@deepseek-ai/dsh`（v0.2.0-rc.2）明确包含 `@deepseek-ai/dsh-acp-app` 依赖。
  - 架构上支持通过 `dsh --profile acp` 启动 ACP 服务模式。
- **为何 Zed 搜不到**：
  - 目前 DSH 仍处于 `0.2.x` 预览/候选发布阶段（RC 阶段）。
  - DeepSeek 团队尚未将 DSH 打包向 `agentclientprotocol/registry` 发起收录申告，且 Zed 图形界面直接与官方 Registry 同步，因此在 UI 里搜索不到。

---

## 3. 在 Zed 中使用两者的替代方式

如果需要在 Zed 中驱动这两款 Agent，无法通过图形界面“一键安装”，必须通过 Zed 的 `settings.json` 进行手动定义：

```json
{
  "agent": {
    "external_agents": {
      "pi": {
        "command": "npx",
        "args": ["-y", "pi-acp"]
      },
      "dsh": {
        "command": "dsh",
        "args": ["--profile", "acp"]
      }
    }
  }
}
```
*(注：DSH 需本机环境已全局安装 `@deepseek-ai/dsh`)*。
---

## 7. 深入调研：DSH 官方 ACP 功能为何感觉“非常有限”？

根据官方包 `@deepseek-ai/dsh-acp` 与 `@deepseek-ai/dsh-acp-app` (v0.2.0-rc.2) 源码与设计文档（`2026-07-23-acp-automation-only-protocol.zh.md`），DSH 对 ACP 的定位存在极强的官方设计取舍：

### 7.1 核心设计定位：“仅面向自动化的精简协议”（Automation-Only Protocol）
DeepSeek 官方在设计 `dsh-acp` 时，**根本没有将其定位为一个全功能的 IDE 交互外挂**，而是定位为**受控自动化管道、测试运行器（Test Runner）以及跨进程 Subagent 编排通道**。

官方文档明确标注了使用准则：
> **何时选择**：当脚本、测试运行器或另一个 harness 需要通过标准自动化协议端到端运行 agent 工作时选择它。
> **何时避开**：**当人类需要 DSH 专用呈现卡片、计划（Plan）、标题、Todo 清单、终端视图或 elicitation（反向提问交互）时请避开**；本服务器刻意只提供标准 ACP v1 最小界面。

### 7.2 官方明确阉割与缺失的四大能力清单
在官方 README 的“已知限制与延期工作”（Known Limitations）章节中明确列出：
1. **彻底关闭所有交互式扩展**：
   - 禁用 Plan 模式（`dsh-plan-mode` 被剥离）；
   - 禁用 Todo 清单展示（`dsh-tool-todo` 不向客户端投射）；
   - 禁用会话标题智能生成（`session-title-llm` 被强行 disabled）；
   - 禁用热模块替换（HMR disabled）。
2. **缺失富呈现与文件系统委托**：
   - 不向 Zed 发送客户端文件系统操作与精细 Diff 呈现卡片；
   - 不支持 transcript 回放、fork 会话或删除会话；
   - 仅支持单一主 workspace，不支持多目录/多项目聚合。
3. **MCP 消费受限**：
   - 仅支持基础 MCP Tool 桥接，不支持 MCP Resource 与 Prompt 模板。
4. **单向静态管道**：
   - 仅发送标准已提交消息、思维链（Thought）与工具起止事件；任何原始提供方重试尝试、中间富状态完全被静默过滤。

### 7.3 对比结论
| 维度 | DSH 原生（Web UI / TUI / 终端模式） | DSH 接入 Zed ACP (`dsh --profile acp`) |
| :--- | :--- | :--- |
| **工作流支持** | 完整支持 Plan 模式、Todo 拆解、Subagent 群组编排 | **完全剥离**，退化为单一的 Prompt-Response 问答 |
| **交互卡片** | 丰富的专用卡片、终端内嵌、反向提问 (elicitation) | **纯文本** JSON-RPC 消息流，无任何富呈现 |
| **会话控制** | 支持 Fork、历史回放、热重载插件 | 仅支持基础会话恢复，不支持 Fork 与分支树 |
| **定位用途** | 人机协同深度工程助手 | **机器对机器（M2M）的纯自动化执行管道** |