# 实施计划 - zedhub Antigravity 会话正文气泡提取（方案 A+C 混合）

**问题陈述**：
Antigravity (agy) 是 zedhub 支持的六大 Agent 中唯一尚未接入正文气泡查看的数据源。其会话存储在 `~/.gemini/antigravity-acp/conversations/<id>.db`（SQLite）的 `steps.step_payload` 字段中，以 Google Protocol Buffers 二进制格式序列化，无公开 `.proto` Schema。在 Plan 48 中已完成逆向剖析，揭示了关键的 `step_type` 枚举与 Protobuf 字段映射。

**技术路径选型（Plan 48 结论）**：
采用 **方案 A（启发式 Proto 提取）+ 方案 C（Brain 日志复用）混合策略**：
- **方案 C 优先**：当前 IDE 产生的 agy 会话在 `~/.gemini/antigravity/brain/<conversation-id>/.system_generated/logs/transcript.jsonl` 中有原生 JSON 文本镜像，零成本读取；
- **方案 A 兜底**：其他来源（VS Code 插件、Cursor 等）产生的 agy 会话仅存在 SQLite+Proto 格式，通过 30 行 Varint 解码器启发式提取 `step_type=14(User, Field#19)` 与 `step_type=15(Assistant, Field#20.Sub#1)`；
- **方案 B 排除**：逆向官方 Protobuf Descriptor 投入产出比最差，版本耦合高，可能触碰合规边界。

**需求**：
1. **Protobuf Varint 解码器**：实现纯 Python 标准库的 Proto Wire Format 递归解码器（~30-50 行），解析 `step_payload` BLOB 为字段树；
2. **Transcript JSONL 解析器**：解析 `transcript.jsonl` 中 `USER_INPUT`/`PLANNER_RESPONSE` 步骤，提取纯文本对话气泡；
3. **混合提取策略**：优先尝试方案 C（transcript.jsonl），不存在时回退方案 A（SQLite+Proto）；
4. **FileSource 接入**：在 `file_sources.py` 中为 `antigravity` 数据源声明 `Capability.CONTENT` 并实现 `get_content`；
5. **Web UI 打通**：前端 agy 会话卡片启用【加载正文】按钮；
6. **单测覆盖**：覆盖 Varint 解码器正确性、混合路径回退逻辑、提取纯净度。

**任务分解**：
- [ ] Task 1: 实现 Protobuf Wire Format 启发式解码器（message_extractor.py 或新模块 proto_decoder.py）
- [ ] Task 2: 实现 transcript.jsonl 解析器（方案 C 路径）
- [ ] Task 3: 实现混合提取策略——方案 C 优先、方案 A 兜底，统一输出 SessionContent
- [ ] Task 4: FileSource 接入与 Web UI 打通（file_sources.py, app.js）
- [ ] Task 5: 单测补充与全量回归验证

---
**最后更新：** 2026-10-07
**作者：** AI & User
**版本：** v1.0
