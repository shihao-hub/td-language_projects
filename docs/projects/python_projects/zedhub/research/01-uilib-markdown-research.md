# 原生 HTML/CSS/JS 组件与 Markdown 渲染调研（zedhub /ui 零构建链约束）

结论：不引入构建链，推荐“手写 CSS 网格布局 + 原生 details/dialog/tab + 单文件 marked.min.js/markdown-it.min.js vendor + highlight.js 可选”。Pico/Shoelace 可参考但不建议整库引入。

## 1. 布局（左窄右宽 + 右侧横向 tab）

- 原生 CSS Grid 两列（280px 1fr）+ 右侧 `<div role=tablist>` 切换 元数据/轨迹/原始 JSON，无需组件库。来源：MDN CSS Grid Layout 与 ARIA tab pattern（https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_grid_layout ， https://www.w3.org/WAI/ARIA/apg/patterns/tabs/）。
- Shoelace 的 Tab Group / Split Panel / Details 语义可直接抄（Web Components，经 CDN 两行即用），但 zedhub 约束是随包分发零构建，整库引入增加体积与主题成本。来源：https://shoelace.style/components/tab-group （MIT，Lit 构建）。
- Pico CSS v2 提供 classless 表单与 Accordion/Card/Modal，但官网已声明不再维护（maintenance 页），不建议新选型。来源：https://picocss.com/docs/maintenance 与 https://picocss.com/docs 。

## 2. Markdown 渲染（单文件 vendor）

- marked（https://github.com/markedjs/marked， MIT）：单文件 `marked.min.js`，`marked.parse(md)` 即可，前端渲染前先做 XSS 过滤（DOMPurify 或只允许 pre/code 白名单）。
- markdown-it（https://github.com/markdown-it/markdown-it， MIT）：同样单文件，插件多但体积更大；只需要 GFM 表格/代码块时 marked 更轻。
- 代码高亮：highlight.js `default.min.css + highlight.min.js` 按需 `hljs.highlightElement`（https://highlightjs.org/ ）。

## 3. Antigravity “二进制”正文能否解开

- ACP（`~/.gemini/antigravity-acp/conversations/*.db`）与桌面版（`~/.gemini/antigravity/conversations/*.db`）的 `steps.step_payload` 是无公开 schema 的 protobuf bytes，官方无文档；README 已记录“归档为整库字节、归档内不可结构化查询”。强解需逆向 proto（protoc --decode_raw 逐字段试），版本一变即碎，不建议做默认解析。
- 建议 UI 策略：优先展示 `render_info/metadata/task_details/error_details` 可读列；payload 只显示类型徽标+长度+hex 预览（当前实现），并在 tab 上注明“桌面版步骤为快照降级显示”。
- 彻底解开的唯一可靠路径是走 Antigravity 自身 UI/ACP 运行时取数，而非离线解析 sqlite。

## 落点（给 zedhub）

- `webui/index.html` 改 Grid：左列筛选（上）+会话列表（下，可滚）；右列 tab（元数据/轨迹）。
- `webui/` 内 vendor `marked.min.js`（MIT）一个文件；轨迹文本按“markdown 优先、失败回退 pre”渲染。
- 不引入 Pico/Shoelace 整库；只借鉴其 tab/details 交互语义。
