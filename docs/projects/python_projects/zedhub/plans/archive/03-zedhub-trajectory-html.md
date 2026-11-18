Plan for: "zedhub 轨迹渲染：多源 agent 会话 jsonl/sqlite 统一渲染成类 DeepSeek harness 轨迹 HTML"

**问题陈述**：zedhub 已有会话检索（/ui 元数据列表 + OpenCode 正文），但 claude-code/codex/antigravity 只做字节搬运与浅层元数据扫描，无法回看思考与工具调用和结果。要在 zedhub daemon+Web 架构内加轨迹详情：点会话即渲染，覆盖 claude-code jsonl、codex jsonl、opencode sqlite、antigravity-acp sqlite、antigravity-desktop sqlite（~/.gemini/antigravity/conversations/*.db）。只做三段式（思考折叠/工具调用卡片/结果输出），不做高保真时间线与流式感。

**需求**：1=a 离线文件优先但经由本地服务动态呈现（先拿到会话列表，点击后渲染）；2=b 小型 Web 服务（复用 zedhub serve + /ui，不做单文件 html）；3=a 首批全覆盖五源；4=a 三段式即可；5=由我本机只读探测格式；6=b 桌面版路径我反查（已确认 ~/.gemini/antigravity/conversations/*.db，steps 表 protobuf payload）。

**背景**：架构约束见 python_projects/zedhub/README.md（daemon 唯一业务进程，壳不 import core，原生 HTML/CSS/JS 零构建链，回环 Host 检查，no-store）。现状：src/zedhub/webui/__init__.py 只托管 index.html/app.js/style.css；src/zedhub/core/agent_paths.py 定位三源文件；src/zedhub/core/agent_sessions.py 已摸清 claude 首条真人 user 标题规则、codex session_meta/response_item 规则、ACP .meta 的 cwd 规则；src/zedhub/core/sources/file_sources.py 对三源查询一律 source_not_supported。实测：codex 首行 session_meta 含 cwd/id/model；claude 前几行是 mode/permission-mode 需跳过；桌面版 steps(step_type/status/step_payload blob) 无公开 schema。

**方案**：新增 trajectory 解析层（daemon 内，Service 唯一业务），统一输出 TimelineEvent[user|thinking|tool_call|tool_result|assistant|system|error]，前端只做分组折叠渲染。claude/codex/opencode 走纯文本解析；两类 antigravity sqlite 走“可读列 + blob 安全降级”（render_info/metadata 尝试 utf-8/zlib 解码展示，step_payload 解不出来就显示类型+长度+hex 预览，不引入 protobuf 编译依赖）。API 新增 /api/v1/trajectory/sources、/sessions/{sid}/trajectory?source=xxx（含 path 安全校验：locate_session_files 白名单内才读），/ui 加轨迹抽屉面板。未知行类型永不丢弃，进 collapsed 原始 JSON。

**任务分解**：
- [x] Task 1: 轨迹事件模型 + claude-code 解析器
  - 文件：python_projects/zedhub/src/zedhub/core/trajectory.py, python_projects/zedhub/tests/test_trajectory_claude.py（占位，执行期跳过）
  - 实现：定义 TimelineEvent(role,text,name,status,ts,raw)；跳过 mode/permission-mode/atis-latch 行；user 取 message.content 文本、assistant 取 content text part 拼接为 thinking+assistant 文本、tool_use part 转 tool_call、tool_result 行转 tool_result；超大行流式读不全量 load
  - 验证：uv run pytest python_projects/zedhub/tests/test_trajectory_claude.py -q（备用，执行期默认不跑），预期真人首条标题与 agent_sessions 一致且 tool_call/result 配对
  - Demo：给定 claude jsonl fixture 输出事件序列 JSON，思考/调用/结果三段俱全
- [x] Task 2: codex 解析器 + opencode 读取器（依赖 Task 1 的模型）
  - 文件：python_projects/zedhub/src/zedhub/core/trajectory.py, python_projects/zedhub/src/zedhub/core/opencode_repo.py（只读复用）
  - 实现：codex 解析 session_meta/response_item/function_call/function_call_output/reasoning 明细映射；opencode 从 ~/.local/share/opencode/opencode.db 的 session/message/part 投影为同一事件模型
  - 验证：uv run pytest python_projects/zedhub/tests/test_trajectory_codex.py -q（备用），预期 codex fixture 的 cwd/session_id 与扫描层一致
  - Demo：同一 TimelineEvent 结构同时描述 codex 与 opencode 会话
- [x] Task 3: antigravity 双源降级解析（依赖 Task 1 的模型）
  - 文件：python_projects/zedhub/src/zedhub/core/trajectory.py, python_projects/zedhub/src/zedhub/core/agent_paths.py
  - 实现：ACP（~/.gemini/antigravity-acp/conversations/<sid>.db）与桌面版（~/.gemini/antigravity/conversations/<sid>.db）只读打开（uri mode=ro）；读 steps 按 idx 序，可读列优先，blob 列尝试 utf-8/zlib/json 解码，失败则降级为占位事件；.meta 的 cwd 用于列表锚点
  - 验证：uv run pytest python_projects/zedhub/tests/test_trajectory_antigravity.py -q（备用），预期真实 .db 不抛错且事件数等于 steps 行数
  - Demo：桌面版大库轨迹页显示步骤列表，payload 不可读处显示类型徽标而非空白
- [x] Task 4: daemon API 接线收尾（依赖 Task 1-3）
  - 文件：python_projects/zedhub/src/zedhub/core/service.py, python_projects/zedhub/src/zedhub/http_api.py, python_projects/zedhub/src/zedhub/contract.py, python_projects/zedhub/src/zedhub/webui/index.html, python_projects/zedhub/src/zedhub/webui/app.js, python_projects/zedhub/src/zedhub/webui/style.css
  - 实现：新增 trajectory sources/list/content 端点（path 白名单校验 + 上限分页 + 超大截断）；/ui 详情面板加“轨迹”抽屉，三段式折叠（思考默认折叠、工具卡片含名称+状态色+耗时、结果预格式化+复制按钮）；contract/schema 同步；不 import 破坏 daemon/壳分层
  - 验证：uv run zedhub serve 后打开 /ui 点任一 claude/codex/opencode/antigravity 会话看到轨迹（备用手工验证，执行期默认不跑）
  - Demo：端到端点击五源任一会话均渲染出三段式轨迹页

---
**最后更新：** 2026-10-06
**作者：** AI & User
**版本：** v1.0
