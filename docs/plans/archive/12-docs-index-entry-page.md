# Plan：恢复站点入口页 docs/index.md（并立规矩不许再删）

> 起因：`23fe983 docs: 移除冗余静态站点入口页` 删掉了 `docs/index.md`，站点首页随之消失（构建产物无 `index.html`、根路径 404）。用户确认：「可以，AGENTS.md 也补一下，index.md 这个文件不能删」。

## 问题陈述

`docs/index.md` 被当作「docs 根目录的散装文件」清掉，但它实际是 mkdocs 的站点入口页：`docs_dir` 根目录没有 `index.md` 就生成不出 `index.html`，`build` 产物无法双击打开、`serve` 根路径 404，只能用侧边栏或手敲子路径进入。

同时，站点用法（三条 `build_docs.py` 命令 + 中文搜索说明 + `file://` 限制）此前只写在这个入口页里，删掉后仓库内除计划文档外再无记录。

## 方案

1. **`docs/index.md` 恢复但瘦身**：只保留「站点定位 + 一句话指向 README + 分区导览表」，删掉与 README 重复的维护命令段；表内补齐此前遗漏的 `specs/`、`memories/`；
2. **`README.md` 新增「文档站点」一节**：承接维护命令、入口页不可删、中文搜索与 `file://` 限制、serve 的资源开销提示；
3. **`AGENTS.md` 在文档布局约定里立规矩**：`docs/index.md` 是站点入口页，属「docs 根不放散装文件」的例外，禁止删除；
4. 重新构建产物并验证：`index.html` 生成、各分区链接目标存在、用户正在跑的 serve 实例根路径恢复 200。

## 任务分解

- **Task 1**：新增 `docs/plans/15-docs-index-entry-page.md`（本文件）；
- **Task 2**：写回瘦身版 `docs/index.md`；
- **Task 3**：`README.md` 增补「文档站点」节（置于「仓库脚本」与「数据文件存放规范」之间）；
- **Task 4**：`AGENTS.md` 归档与文档布局约定节增补入口页禁删条目；
- **Task 5**：`uv run .scripts/build_docs.py build --strict` + 校验 `.mkdocs-site/index.html` 与 6 个分区链接产物存在 + 探测 http://127.0.0.1:8765/ 返回 200。

## 执行编排

## Stage 1: 落地 ✅
- [x] Task 1~4：四份文件改完。

## Stage 2: 验证 ✅
- [x] Task 5：strict 构建 exit=0；`.mkdocs-site/index.html` 与 `guides|plans|projects|specs|repo|memories` 各链接产物均存在；serve 实例根路径 200。

---

**最后更新**：2026-09-23
**作者**：AI & User
**版本**：v1.0
