Plan for: "zedhub /ui 美化：左窄右宽 + 右侧横向 tab + 轨迹 markdown 渲染"

**问题陈述**：左侧列表太宽挤压详情，轨迹偏下需滚动很久才看到；要 DSH 式布局：左筛选上会话下，右横向 tab（元数据/轨迹），轨迹 markdown 渲染。
**需求**：筛选功能不动；左 280px；右 tab 默认元数据；轨迹 markdown 渲染；antigravity 二进制保持降级占位+注明。
**背景**：见 docs/plans/37-uilib-markdown-research.md；webui 零构建链约束，只能手写 CSS + 原生 tab + 内联轻量 markdown 解析（不 vendor 外部库，避免体积与许可负担）。
**方案**：index.html 改 Grid 两列；style.css 加 tab 与 tstep 样式；app.js 加 renderTabs 与 mdToHtml（转义后处理代码块/标题/粗体/列表/换行）。

**任务分解**：
- [x] Task 1: 布局 Grid + 右侧 tab
  - 文件：python_projects/zedhub/src/zedhub/webui/index.html, style.css, app.js
  - 实现：左列筛选+列表，右列 tab（元数据/轨迹/原始）；会话点击默认元数据 tab
  - 验证：uv run zedhub serve 后 /ui 目检（备用，执行期默认不跑）
  - Demo：左窄右宽，tab 切换正常
- [x] Task 2: 轨迹 markdown 渲染 + antigravity 注明（依赖 Task 1）
  - 文件：python_projects/zedhub/src/zedhub/webui/app.js, style.css
  - 实现：mdToHtml 渲染轨迹文本，失败回退 pre；桌面版/ACP 步加降级徽标说明
  - 验证：打开 claude/codex/antigravity 轨迹目检（备用）
  - Demo：轨迹含标题/代码块正常排版，二进制步显示说明而非裸 binary

---
**最后更新：** 2026-10-06
**作者：** AI & User
**版本：** v1.0
