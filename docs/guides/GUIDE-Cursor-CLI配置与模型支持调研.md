### 调研结论：Cursor CLI 是否支持自定义 base_url 与自定义模型

经过深入查阅 Cursor 官方文档（docs.cursor.com）、Cursor 官方论坛（forum.cursor.com）讨论、GitHub 社区生态及相关实现，调研结论如下：

**核心结论：Cursor CLI（`agent` / `cursor-agent`）目前【完全不支持】原生的自定义 `base_url`（如 OpenAI-compatible API base URL、Ollama、vLLM、第三方反代端点）以及自定义模型名称。**

以下为针对各关键问题的详细事实与技术剖析：

---

### 1. 官方目前提供的 CLI 工具与能力定位

在 Cursor 生态中，存在两个层面的 CLI 工具，分工完全不同：

#### A. 编辑器管理 CLI（`cursor` 命令）
* **定位**：基于 VS Code 代码库的经典启动与管理脚本（相当于 VS Code 的 `code` 命令）。
* **安装方式**：Cursor GUI 内通过 `Cmd/Ctrl + Shift + P` -> 执行 `Shell Command: Install 'cursor' command in PATH`。
* **支持参数**：
  * 文件与窗口操作：`cursor .`、`cursor -d file1 file2`（diff）、`cursor -g file:line`、`-n`（new window）、`-r`（reuse window）。
  * 扩展管理：`--install-extension <id>`、`--list-extensions` 等。
* **能力限制**：纯编辑器启动器与扩展管理工具，**不具备任何 AI Prompting、Chat 或 Agent 交互功能**。

#### B. 独立终端智能体 CLI（`agent` / `cursor-agent`）
* **定位**：Cursor 官方推出的 Headless / Terminal Agent（类比 Claude Code、Aider、OpenCode）。
* **安装方式**：
  * macOS / Linux / WSL：`curl https://cursor.com/install -fsS | bash`
  * Windows：`irm 'https://cursor.com/install?win32=true' | iex`
* **交互模式与主要参数**：
  * 交互模式：直接运行 `agent`
<truncated 4030 bytes>
本极高、极其脆弱。
2. **反向包装类项目（注意方向）**：
   * 社区中如 [`anyrobert/cursor-api-proxy`](https://github.com/anyrobert/cursor-api-proxy)、`Yuki13929/cursor2api` 等工具，其实是**反向工具**（即把 Cursor CLI 或 Cursor 账号包装成 OpenAI 兼容接口，供给外部工具调用），而非让 Cursor CLI 接入外部模型。
3. **行业主流推荐替代方案**：
   * 如果用户强需求在**终端/命令行（CLI / Headless Agent）**中使用自定义模型、本地模型（Ollama/vLLM）或自定义 OpenAI 兼容 Base URL，目前社区普遍推荐使用原生支持此类配置的开源 CLI Agent：
     * **Aider**：对 `--openai-api-base`、Ollama、OpenRouter、vLLM、LiteLLM 原生一流支持。
     * **OpenCode**：原生支持切换任意 Provider 与自定义 base_url。
     * **Claude Code**：支持配合 LiteLLM / 代理劫持 Anthropic 兼容端点。

---

### 5. 高可信来源与参考链接

* **官方文档**：
  * Cursor CLI 概述：[docs.cursor.com/cli/overview](https://docs.cursor.com/cli/overview)
  * CLI 配置规范（cli-config.json）：[docs.cursor.com/cli/reference/configuration](https://docs.cursor.com/cli/reference/configuration)
  * CLI 参数参考：[docs.cursor.com/cli/reference/parameters](https://docs.cursor.com/cli/reference/parameters)
  * CLI 安装指南：[docs.cursor.com/cli/installation](https://docs.cursor.com/cli/installation)
* **官方论坛讨论与反馈**：
  * [Cursor CLI with Custom API key (Feature Requests)](https://forum.cursor.com/t/cursor-cli-with-custom-api-key/26456)
  * [Cursor CLI - Custom endpoint and api key support](https://forum.cursor.com/t/cursor-cli-custom-endpoint-and-api-key-support/3175)
  * [How to bring my own key with cursor cli](https://forum.cursor.com/t/how-to-bring-my-own-key-with-cursor-cli/23812)
  * [Subagents ignore user's own API key / Custom Base URL](https://forum.cursor.com/t/subagents-ignore-users-own-api-key-always-bill-against-cursor-plan/48202)
</SYSTEM_MESSAGE>