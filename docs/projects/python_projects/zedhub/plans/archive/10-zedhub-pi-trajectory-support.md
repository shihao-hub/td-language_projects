# 实施计划 - zedhub 支持 Pi 会话轨迹解析

**问题陈述**：
在 Web UI 会话详情页中，选择 Pi 会话并切换到「轨迹」Tab 时，页面显示为 `轨迹 · pi · 0 步 · `，无法展示 Pi 的思考过程（thinking）、工具调用（toolCall）及执行结果（toolResult）。
根本原因在于 [`src/zedhub/core/trajectory.py`](file:///d:/Users/language_projects/python_projects/zedhub/src/zedhub/core/trajectory.py) 的 `load_trajectory` 分派器仅处理了 `claude-code`、`codex`、`antigravity` 和 `opencode`，未实现 Pi 的解析器 `parse_pi_file`，也未接入 `pi` 分支。

**需求**：
1. 在 `trajectory.py` 中实现 `parse_pi_file(path: Path, *, limit: int = 2000) -> list[TimelineEvent]`：
   - 提取 `session` 的初始 cwd 等系统信息（`role="system"`）；
   - 提取 `model_change` 与 `thinking_level_change`（`role="system"`）；
   - 提取 `message` (user) 的文本输入（`role="user"`）；
   - 提取 `message` (assistant) 的思考过程（`role="thinking"`）、回答文本（`role="assistant"`）及工具调用（`role="tool_call"`）；
   - 提取 `message` (toolResult) 的工具执行结果（`role="tool_result"`）；
2. 在 `load_trajectory` 中增加 `elif source in ("pi", "pi-acp"):` 分派支持；
3. 补充单元测试，验证 Pi 轨迹解析器各事件解析与 `load_trajectory` 链路。

**任务分解**：
- [x] Task 1: 实现 Pi 轨迹解析器 `parse_pi_file` 与分派接入
  - 文件：`src/zedhub/core/trajectory.py`
  - 实现：编写 `parse_pi_file` 函数逐行解析 Pi 会话 JSONL，并在 `load_trajectory` 中接入 `pi` 与 `pi-acp` 分派。
  - 验证：运行 `uv run pytest tests/test_trajectory.py`。
  - Demo：调用 `load_trajectory(source="pi", files=[...])` 返回包含 thinking、tool_call 等事件的完整轨迹。

- [x] Task 2: 补充单测并全量回归
  - 文件：`tests/test_trajectory.py`
  - 实现：构造覆盖 session / model_change / user / thinking / toolCall / toolResult 的测试用例，断言事件结构与字段截断。
  - 验证：运行 `uv run pytest`。
  - Demo：全量单元测试通过。

---
**最后更新：** 2026-10-10
**作者：** AI & User
**版本：** v1.1 (已完成)
