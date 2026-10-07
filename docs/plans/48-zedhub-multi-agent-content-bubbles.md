# 实施计划 - zedhub 多 Agent 对话正文气泡提取与 agy 载荷剖析

**问题陈述**：
1. 当前 zedhub 仅 OpenCode 支持“加载正文”（人机对话聊天气泡，类似微信/Slack，过滤掉内部工具调用与思考过程）；Claude Code、Codex、Pi 会话虽有本地文件或索引，但前端与后端均显示“无结构化正文源”，只能看复杂轨迹而无法快速阅览纯粹人机对话；
2. Antigravity (agy) 的会话存储在 SQLite `steps.step_payload`（二进制 Protobuf BLOB）中，缺乏公开 Schema，解析困难，需要对底层存储机制和逆向解开方案进行深入调研与样本剖析。

**需求**：
1. **Claude Code 正文气泡**：解析 `~/.claude/projects/*/<sid>.jsonl`，提取 `type == "user"` 与 `type == "assistant"` 的文本消息，过滤 `tool_use`/`tool_result`，组装为标准 `SessionContent`；
2. **Codex 正文气泡**：解析 `~/.codex/sessions/*/*/*/rollout-*-<sid>.jsonl`，提取 `response_item.payload.type == "message"` 中的文本消息，过滤 `reasoning`/`function_call`，组装为标准 `SessionContent`；
3. **Pi 正文气泡**：解析 `~/.pi/agent/sessions/*/*<sid>*.jsonl`，提取 `role in ("user", "assistant")` 的纯文本消息，过滤 `thinking`/`toolCall`/`toolResult`，并在数据源体系中建立支持；
4. **统一前端体验**：Web UI 解除仅限 OpenCode 的硬编码限制，对上述所有具备正文能力的 Agent 提供【加载正文】按钮，无缝复用气泡渲染器；
5. **单测覆盖**：新增单测确保多 Agent 正文提取的纯净度（无思考、无工具代码）；
6. **agy 载荷深度剖析**：提取本地真实的 Antigravity `step_payload` 样本，解析其物理格式与反序列化切入点，交付供审阅的技术报告。

**任务分解**：
- [x] Task 1: Claude Code 与 Codex 正文气泡提取与 FileSource 支持（file_sources.py, agent_paths.py, message_extractor.py）
- [x] Task 2: Pi (pi-acp) 会话文件定位、解析器与数据源接入（base.py, file_sources.py, agent_sessions.py）
- [x] Task 3: 后端接口适配与 Web UI 正文加载打通（api.py, app.js）
- [x] Task 4: 单测补充与全量回归验证（test_session_content.py, pytest 100% 通过）
- [x] Task 5: Antigravity (agy) 真实二进制载荷提取与逆向分析报告

---
**最后更新：** 2026-10-07
**作者：** AI & User
**版本：** v1.0

