# MkDocs 服务端口冲突修复计划

**问题陈述**：MkDocs `serve` 当前固定监听 `127.0.0.1:8765`，与 Sublime Text 的 MarkdownPreviewEnhance 插件默认端口冲突。按 `Ctrl+Shift+M` 预览 Markdown 时，请求被 MkDocs 接收，浏览器显示 `language_projects 文档库` 首页，而不是当前 Markdown 文件。用户已指定将 MkDocs 端口改为 `12345`。

**需求**：
- 将 `uv run .scripts/build_docs.py serve` 的监听地址改为 `127.0.0.1:12345`。
- 同步更新仓库内面向用户的端口说明，避免命令实现与文档不一致。
- 不改变 `.mkdocs-site` 的构建目录、`build` 行为、`preview` 的 `8766` 端口或 Markdown 内容。
- 保留历史计划文档中对既往 `8765` 验证的记录，不把历史事实改写成当前配置。

**背景**：
- `.scripts/build_docs.py` 在 `serve` 分支中通过 `--dev-addr 127.0.0.1:8765` 固定端口。
- `README.md` 和 `docs/specs/01-web-archive-skill/index.md` 展示了当前 `serve` 地址 `http://127.0.0.1:8765`。
- `preview` 使用 `127.0.0.1:8766`，本次不调整，避免扩大改动范围。
- `mkdocs.yml` 只配置 `site_dir: .mkdocs-site`，不包含开发服务端口，因此无需修改。

**方案**：
1. 修改 `.scripts/build_docs.py` 的 serve 端口及对应中文注释。
2. 修改 `README.md` 与站点维护页中的 serve 地址为 `http://127.0.0.1:12345`。
3. 使用 `git diff --check` 检查改动格式；使用 `uv run .scripts/build_docs.py build --strict` 验证站点构建未受影响；启动一次 serve 并请求 `http://127.0.0.1:12345/`，确认响应为 MkDocs 页面后立即停止临时服务。

## 任务分解

- [x] Task 1: 将 MkDocs serve 端口切换为 12345 完成
  - 文件：`.scripts/build_docs.py`
  - 实现：把 serve 命令的 `--dev-addr` 改为 `127.0.0.1:12345`，同步更新脚本用法注释；不修改 `build`、`preview` 和 `site_dir` 行为。
  - 验证：执行 `git diff --check`；预期无空白错误，且差异只包含 serve 端口相关内容。
  - Demo：执行 `uv run .scripts/build_docs.py serve` 后访问 `http://127.0.0.1:12345/`，能够看到 MkDocs 首页。

- [x] Task 2: 同步更新公开使用说明 完成
  - 文件：`README.md`、`docs/specs/01-web-archive-skill/index.md`
  - 实现：将 serve 示例地址从 `http://127.0.0.1:8765` 更新为 `http://127.0.0.1:12345`，保留 preview 的 `8766` 说明；不修改历史计划文档中的历史验证记录。
  - 验证：执行 `rg -n "127\\.0\\.0\\.1:12345|127\\.0\\.0\\.1:8765" README.md docs/specs/01-web-archive-skill/index.md .scripts/build_docs.py`；预期当前说明和实现均只指向 `12345`，历史计划中的旧端口不作为当前说明使用。
  - Demo：用户按 README 命令启动后，可根据文档打开 `http://127.0.0.1:12345`，且不会再占用 MarkdownPreviewEnhance 的 `8765`。

- [x] Task 3: 完成构建与端口冒烟验证 完成
  - 文件：`.scripts/build_docs.py`、`README.md`、`docs/specs/01-web-archive-skill/index.md`
  - 实现：执行严格构建，并启动临时 serve 实例验证新端口；验证完成后停止该实例，不遗留后台进程或临时服务。
  - 验证：`uv run .scripts/build_docs.py build --strict` 应退出码为 0；启动 serve 后请求 `http://127.0.0.1:12345/` 应返回 HTTP 200 且页面包含 `language_projects 文档库`；停止服务后 12345 不再监听。
  - Demo：MkDocs 文档站点仍可构建和热刷新，同时 MarkdownPreviewEnhance 可以继续使用其默认的 8765 端口。

---

**执行记录**：
- 已将 `serve` 端口从 `8765` 改为 `12345`，并同步更新两处当前使用说明。
- `uv run .scripts/build_docs.py build --strict` 退出码为 0；构建过程中保留了既有的无效锚点提示，但未阻断构建。
- 临时启动 `serve` 后，`http://127.0.0.1:12345/` 返回 HTTP 200 且响应包含 `language_projects`；验证完成后已停止服务，未遗留 12345 监听进程。

**最后更新**：2026-09-25
**作者**：AI
**版本**：v1
