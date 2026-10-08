# 实施计划 - zedhub 外部发现 Agent 归一化、联动加固与 Pi 数据源补全

**问题陈述**：
1. **外部 Agent 命名碎拆**：OpenCode 本地数据库将内部角色模式（`build`、`plan`、`explore`、`general`）记录在 `session.agent` 列，检索层在构建外部会话时直接透传，导致前端「外部发现」分组被炸碎成 5 个伪 Agent，与外部独立工具平级，造成分类繁杂；
2. **管理范围联动失效**：`<optgroup>` 两个分组下同名 `value="opencode"`。当管理范围为「全部会话」（`scope="all"`）时，用户在下拉框专门点击外部发现的 `opencode`，前端联动未覆盖 `scope="all"`，导致未切换范围；后端仅匹配 `agent_id="opencode"`，将 Zed 管理的 326 条最新会话与外部 30 条混出并排在前面，使得“选了外部发现却展示 Zed 管理”；
3. **外部数据源遗漏 Pi**：`src/zedhub/api.py` 的全局检索接口 `_search` 硬编码外部源列表为 `("opencode", "claude-code", "codex", "antigravity")`，漏掉了 `"pi"`，导致本地 87 条 Pi 会话在外部发现中完全不可见；
4. **归档范围明确**：本期明确归档功能仅服务 Zed 管理会话，外部文件源暂不扩展归档子目录扫描。

**需求**：
1. 外部 OpenCode 会话 `agent_id` 统一归一化为 `"opencode"`，原内部模式（`build`/`plan`/`explore`/`general`）转为 `mode` 字段透传，前端以模式徽标展示；
2. Agent 下拉菜单与管理范围强绑定联动：
   - 选中「外部发现」分组的选项时，无论当前 scope 为何（含 `zed` 与 `all`），均强绑定自动切换为 `scope="external"`；
   - 选中「Zed 管理 (ACP)」分组的选项时，无论当前 scope 为何（含 `external` 与 `all`），均强绑定自动切换为 `scope="zed"`；
   - 切换管理范围（`scope`）且当前选中的 Agent 与新范围不兼容时，平滑重置 Agent 为全部；
3. `api.py` 的 `_search` 数据源列表补上 `"pi"`，对齐 `_sessions_list` 口径；
4. 完善单元测试，确保现有及新增契约测试全绿。

**任务分解**：
- [ ] Task 1: 外部 OpenCode 会话 agent 归一化与 mode 透传
  - 文件：`src/zedhub/core/model.py`, `src/zedhub/core/search.py`
  - 实现：`SearchHit` 增加 `mode: str | None = None` 字段；`search.py` 构建 `external_session` 时，当 `s.source_id == "opencode"` 时固定 `agent_id = "opencode"`，并将原本的 `s.agent` 赋给 `mode`。
  - 验证：运行 `uv run pytest tests/test_search_scope.py`。
  - Demo：检索返回的未进 Zed 索引 OpenCode 会话 `agent_id` 统一为 `opencode`，且包含对应的 `mode`。

- [ ] Task 2: 全局检索补全 Pi 外部数据源
  - 文件：`src/zedhub/api.py`
  - 实现：在 `_search` 函数的数据源列表中加入 `"pi"`，使其与 `_sessions_list` 保持一致，能正常扫描和检索外部 Pi 会话。
  - 验证：运行 `uv run python -c "from zedhub.api import _search; ..."`。
  - Demo：外部发现列表中能够显示 `pi` 及其会话条目。

- [ ] Task 3: 前端 Agent 选择强绑定联动与模式徽标渲染
  - 文件：`src/zedhub/webui/app.js`
  - 实现：加固 `el.agent` 的 `change` 事件监听器，当选中项的 `data-management` 为 `external` 时，强制设置 `el.scope.value = "external"`（覆盖原本仅判断 `scope === 'zed'` 的逻辑）；选中项为 `zed` 时，强制设置 `el.scope.value = "zed"`；在 `renderHit` 中，若存在 `hit.mode`，渲染对应的卡片徽标（如 `badge(hit.mode, "mode")`）。
  - 验证：运行 `uv run pytest tests/test_ui_app.py`。
  - Demo：在全部会话或任何状态下点击外部发现的 opencode，管理范围自动切至外部发现，结果仅展示外部发现会话，且会话卡片上显示 build/plan 等模式徽标。

- [ ] Task 4: 单测补充与全量回归
  - 文件：`tests/test_search_scope.py`, `tests/test_ui_app.py`
  - 实现：补充对外部 OpenCode agent 归一化、mode 字段、Pi 外部检索及前端 JS 联动逻辑的断言测试。
  - 验证：运行 `uv run pytest`。
  - Demo：ZedHub 既有及新增测试全部通过。

---
**最后更新：** 2026-10-09
**作者：** AI & User
**版本：** v1.0
