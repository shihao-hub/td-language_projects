# 实施计划 - zedhub 外部发现 Agent 归一化、下线管理范围控件（路线 B）与 Pi 数据源补全

**问题陈述**：
1. **外部 Agent 命名碎拆**：OpenCode 本地数据库将内部角色模式（`build`、`plan`、`explore`、`general`）记录在 `session.agent` 列，检索层在构建外部会话时直接透传，导致前端「外部发现」分组被炸碎成 5 个伪 Agent，与外部独立工具平级，造成分类繁杂；
2. **管理范围与 Agent 维度冲突**：当前 UI 同时存在「管理范围」下拉框与「Agent」下拉框的 `<optgroup>`（Zed 管理 / 外部发现）分组，存在概念冗余与打架：
   - 两组内同名 `value="opencode"`，选中外部发现的 opencode 时因范围是全部会话，后端混出大量 Zed 管理会话；
   - 互相联动脆弱易错；
   - 用户决定采纳**路线 B**：彻底砍掉冗余的「管理范围」下拉控件，由「Agent」下拉框直接承载范围与角色的联合选择。
3. **外部数据源遗漏 Pi**：`src/zedhub/api.py` 的全局检索接口 `_search` 硬编码外部源列表为 `("opencode", "claude-code", "codex", "antigravity")`，漏掉了 `"pi"`，导致本地 87 条 Pi 会话在外部发现中完全不可见；
4. **归档边界明确**：归档功能仅服务 Zed 管理会话，外部文件源暂不扩展。

**需求**：
1. **外部 OpenCode 会话归一化**：
   - 外部 OpenCode 会话 `agent_id` 统一归一化为 `"opencode"`，原内部模式（`build`/`plan`/`explore`/`general`）转为 `mode` 字段透传，前端在卡片上以模式徽标展示；
2. **下线管理范围控件并升级 Agent 下拉框（路线 B）**：
   - `index.html` 移除独立的「管理范围」`<select>` 控件；
   - `app.js` Agent 下拉框结构升级为三层复合表达：
     - 顶层选项：
       - `all:all`：`全部会话`
       - `scope:zed`：`全部 Zed 管理会话`（默认选中项，保障默认看 Zed 的体验）
       - `scope:external`：`全部外部发现会话`
     - `<optgroup label="Zed 管理 (ACP)">`：
       - 每个选项 value 形如 `zed:<agent_id>`，显示如 `opencode (326)`
     - `<optgroup label="外部发现">`：
       - 每个选项 value 形如 `external:<agent_id>`，显示如 `opencode (226)`
   - 前端发起 `/search` 请求时，根据选中的复合 value 精准解析 `scope` 与 `agent`：
     - `scope:zed` → `scope="zed", agent=None`
     - `scope:external` → `scope="external", agent=None`
     - `all:all` → `scope="all", agent=None`
     - `zed:<aid>` → `scope="zed", agent=aid`
     - `external:<aid>` → `scope="external", agent=aid`
   - URL 状态同步（`syncUrl` / `restoreFromUrl`）支持复合状态存取，且默认 `scope:zed` 时省略该参数保持 URL 洁净；
3. **补全 Pi 外部数据源**：
   - `api.py` 的 `_search` 数据源列表补上 `"pi"`，对齐 `_sessions_list` 口径；
4. **测试套件保障**：
   - 更新前端契约测试与后端范围检索测试，确保全部测试通过。

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

- [ ] Task 3: 下线管理范围控件与 Agent 复合下拉重构（路线 B）
  - 文件：`src/zedhub/webui/index.html`, `src/zedhub/webui/app.js`
  - 实现：
    - `index.html`：移除 `#scope-select` 及其父容器；
    - `app.js`：重构 `loadOptions` 中 `el.agent` 的生成逻辑（`all:all`、`scope:zed`、`scope:external`、`zed:<aid>`、`external:<aid>`）；
    - `readState` / `runSearch`：从选中的复合 value 解析出 `scope` 和 `agent` 请求后端；
    - `syncUrl` / `restoreFromUrl`：维护 URL 兼容与干净；
    - `renderHit`：渲染 `hit.mode` 徽标。
  - 验证：运行 `uv run pytest tests/test_ui_app.py`。
  - Demo：界面更精简，选外部发现的 opencode 时只会精准展示外部会话，选 Zed 管理的 opencode 时只会展示 Zed 管理会话，默认默认展示 Zed 管理全部会话。

- [ ] Task 4: 单测补充与全量回归
  - 文件：`tests/test_search_scope.py`, `tests/test_ui_app.py`
  - 实现：更新 `test_ui_app.py` 适配下线 scope-select 后的行为，补充复合选项解析测试与 mode 徽标测试。
  - 验证：运行 `uv run pytest`。
  - Demo：ZedHub 全部测试通过。

---
**最后更新：** 2026-10-09
**作者：** AI & User
**版本：** v2.0
