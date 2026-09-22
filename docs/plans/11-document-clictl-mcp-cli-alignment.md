# `clictl` CLI 与 MCP 能力对齐说明文档计划

## 问题陈述

当前 `clictl` 已实现 CLI 与 MCP 双入口，但 `MCP 接口文档.md` 的 CLI ↔ MCP 对照表之前缺少一段总述，未集中说明能力复用原则、`run` 的非交互差异，以及 `clictl mcp` 与 MCP 工具之间的区别。

## 需求

- 在 `clictl` MCP 接口文档中补充 CLI 与 MCP 能力对齐的总述。
- 明确列出当前已覆盖的 CLI 业务能力。
- 标注 `run` 在 MCP 侧不提供 stdin/PTY 透传，而采用非交互收集输出语义。
- 说明 `completion`、`help`、`schema` 不暴露为 MCP 工具的原因。
- 说明 `clictl mcp` 是启动 MCP stdio server 的协议入口，不是 MCP 工具。
- 不修改 Go 代码、工具注册、接口行为或其他项目文件。

## 背景

- 当前文档：`docs/projects/go_projects/clictl/MCP 接口文档.md`
- 现有第 4 节已经提供 CLI 与 MCP 的逐项映射表。
- 现有第 3.9 节已经描述 `clictl.run` 的非交互执行边界。
- 现有第 2 节已经说明 `clictl mcp` 使用 stdio 传输，协议 stdout 与业务日志 stderr 的分工。
- 仓库现行规范位于：`docs/projects/go_projects/CLI 工具开发标准.md`。

## 方案

在 `MCP 接口文档.md` 的第 4 节标题之后、现有对照表之前，增加一段“能力对齐说明”正文。正文使用反引号标记命令和工具名，保持与现有文档风格一致，并明确区分：

1. 业务能力映射；
2. 渠道执行语义差异；
3. CLI 专属或离线契约能力；
4. MCP server 启动入口与 MCP 工具。

## 任务分解

- [ ] Task 1: 补充 `clictl` CLI 与 MCP 能力对齐总述
  - 文件：`docs/projects/go_projects/clictl/MCP 接口文档.md`
  - 实现：在第 4 节现有对照表前插入已确认的说明文字，不调整现有工具定义和对照表内容。
  - 验证：使用 `git diff --check` 检查无空白错误，并检查文档第 4 节包含能力覆盖、`run` 差异、CLI 专属能力和 `clictl mcp` 入口说明；预期检查通过且仅有目标文档发生业务文档变更。
  - Demo：阅读第 4 节即可理解 `clictl mcp` 是 server 启动命令，而 `clictl.list`、`clictl.run` 等才是 MCP 工具，并能看出 `run` 的渠道差异。

---

最后更新：2026-09-21
作者：AI
版本：1.0
