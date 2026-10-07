Plan for: "zedhub 非 opencode 会话可加载全文：轨迹 ID 映射（a 先行，b 后续）"

**问题陈述**：Zed 索引线程的 session_id 与 claude-code/codex/antigravity 本地文件 sid 是两套 ID，按文件名精确匹配找不到文件，所以非 opencode 会话没有可用的“加载原文”入口。opencode 能用是因为两边是同一套 id。
**需求**：1=并非加载报错，而是缺入口（用户原话）；2=a 先实现 ID 映射（cwd+时间辅助），b（按目录浏览源文件，覆盖非 Zed 创建的会话）作为后续目标，不在本计划内。
**背景**：实测 `3fc675bd…`（claude）与 `68ac24ee…`（antigravity）在各自数据根下无同名文件；codex `01a0f758…` 文件名存在但 Zed 侧 id 未必一致。现状：`api._trajectory` 只调 `locate_session_files(source,[sid])` 精确匹配，miss 即抛 InvalidParamsError；`core/agent_sessions.py` 已有各源 cwd/标题/时间扫描能力可复用。
**方案**：trajectory.show 加 fallback 映射层：精确 sid 命中直接用；miss 时查 Zed 线程（项目目录+创建时间）→ 扫描该源全会话元数据 → 按归一化目录相等优先、时间最接近决胜，选出唯一文件；有多候选或零候选时返回带候选列表的 not_found（前端提示换条件），不猜测写入。前端：zed_thread 详情保留「查看轨迹」按钮（即“加载原文”入口），miss 时展示可读提示。

**任务分解**：
- [x] Task 1: 映射层 + trajectory.show 接入 fallback
  - 文件：python_projects/zedhub/src/zedhub/core/trajectory.py, python_projects/zedhub/src/zedhub/api.py
  - 实现：新增 resolve_by_directory(source, directory, near_ts)：复用 scan_agent_sessions 取全量，按 normpath 目录全等过滤、updated/created 时间差最小取唯一；阈值外视为无匹配；api miss 时调它，找到则 load_trajectory，找不到返回 not_found 含候选数
  - 验证：uv run pytest python_projects/zedhub/tests/test_trajectory.py -q（备用，执行期默认不跑），预期 taskbarguard 等已知 claude/codex 线程能映射到真实文件
  - Demo：点 claude-acp/codex-acp/antigravity-acp 的 Zed 线程「查看轨迹」能渲染出全文轨迹
- [x] Task 2: 前端提示与空态收尾（依赖 Task 1）
  - 文件：python_projects/zedhub/src/zedhub/webui/app.js
  - 实现：not_found 时在轨迹 tab 显示“未找到本地源文件（可能终端直跑未进索引），后续支持按目录浏览”；成功路径不变
  - 验证：打开无源文件线程目检提示（备用，执行期默认不跑）
  - Demo：有文件渲染轨迹，无文件显示可读提示而非报错堆栈

后续（不在本计划）：b 按目录浏览源文件直选（覆盖非 Zed 创建会话）。

**增补（用户新需求：antigravity 二进制必须可读）**：只读探针已证实 `steps.step_payload` 可用无依赖 raw protobuf walk 解开（`protoc` 不可用、`protobuf` 包未安装，手写 varint 解析即可），实测映射：
- user 文本 `/20/3`（step_type 15 步），工具调用 id/名称/参数 JSON `/20/7/1,2,3`（回声位于 `/5/4/1,2,3`）
- assistant 文本 `/140/2/1`，工具结果回声 `/140/1/*` 与 `/140/2/6/2/…`（内含 `type.googleapis.com/gemini_coder.Step` Any 包络）
- 字段号为启发式（无公开 .proto），解不出时保留降级占位，绝不抛错丢步

**任务分解**（增补）：
- [x] Task 3: antigravity payload 解码（依赖 Task 1 的文件定位）
  - 文件：python_projects/zedhub/src/zedhub/core/trajectory.py
  - 实现：内置 raw protobuf walk（varint/tag/length-delimited，无第三方依赖）；按上式映射抽 user/assistant/tool_call/tool_result 事件；未知结构回退占位；ACP 与桌面版同形共用
  - 验证：uv run pytest python_projects/zedhub/tests/test_trajectory.py -q（备用，执行期默认不跑），预期真实 .db 无 binary 占位、思考/调用/结果三段俱全
  - Demo：截图中的 antigravity 会话轨迹显示真实文本而非 7KB binary

---
**最后更新：** 2026-10-06
**作者：** AI & User
**版本：** v1.0
