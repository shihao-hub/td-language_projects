# 实施计划 - zedhub 默认管理范围改造与 Agent 层级化展示

**问题陈述**：
1. 当前 Web UI 管理范围默认是全部会话（`all`），用户期望默认管理范围是 `Zed 管理`（`zed`）；
2. Agent 下拉列表将 Zed 管理的 ACP 与外部发现的 Agent 混在同一平铺列表里，且外部发现 Agent 的会话计数在前端被硬编码为 `(1)`，造成数字严重失真；用户无法直观区分哪个是 ACP 哪个是外部 Agent，且在筛选时缺乏层级与合理的范围联动。

**需求**：
1. 默认管理范围改为 `Zed 管理`：
   - `index.html` 下拉项默认选中 `Zed 管理`（`value="zed"` 置首并设 `selected`）；
   - `app.js` 在 URL 无 `scope` 参数时默认使用 `zed`；
   - URL 同步逻辑在 `scope` 为默认 `zed` 时省略该参数，非 `zed` 时写入 URL。
2. Agent 下拉列表层级化展示：
   - 采用原生 `<optgroup>` 分组展示，一级包含「Zed 管理 (ACP)」和「外部发现」两个层级分组；
   - 彻底修复数字统计：在全量检索数据中分别累加 `hit.management === "zed"` 与 `hit.management === "external"` 的真实条数，消除假 `(1)`。
3. Agent 与管理范围智能联动：
   - 用户在 Agent 菜单选择外部发现分组的 Agent 且当前范围为 `zed` 时，自动联动将管理范围切至 `external` 并检索；
   - 用户在 Agent 菜单选择 Zed 管理分组的 Agent 且当前范围为 `external` 时，自动联动将管理范围切至 `zed` 并检索；
   - 用户在管理范围下拉框中切换范围且当前选中的 Agent 与新范围冲突时，将 Agent 平滑重置为全部。
4. 保持轻量与零依赖设计，保证测试全绿。

**任务分解**：
- [ ] Task 1: Web UI 默认管理范围改为 Zed 管理（index.html, app.js）
- [ ] Task 2: Agent 下拉层级化展示与真实会话计数修复（app.js）
- [ ] Task 3: Agent 选择与管理范围智能联动处理（app.js）
- [ ] Task 4: 单测补充与回归验证（test_ui_app.py）

---
**最后更新：** 2026-10-07
**作者：** AI & User
**版本：** v1.0
