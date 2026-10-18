# 仓库运维脚本约定（自根 AGENTS.md §六 迁出 · 按需引用）

> **触发**：新建/修改 `.scripts` 脚本前必读。本文件不在规则自动加载目录（`.agents/rules/`）内，由根 `AGENTS.md` 触发器指引按需读取。

- 仓库运维脚本统一放 `.scripts/`（点前缀目录，与 `.archived`/`.zed` 同属仓库基础设施层）；项目自有脚本随各自子仓，不入该目录。
- 脚本语言**统一 Python**（PEP 723 + uv 单文件），**禁止新增 ps1/bat**：历史 ps1/bat 已全部迁移删除，双击入口一并放弃；typescript_projects 子仓内部脚本用 TS（Bun）。
- 例外：`docs/assets/projects/` 目录存放跨项目二进制资源（当前仅 go 默认图标），不属于脚本约束范围。
- **一个脚本只做一件事**：单一职责，禁止膨胀为万能工具脚本。
- Python 脚本**必须**带 PEP 723 内联元数据（`# /// script` 块）声明 `requires-python` 与 `dependencies`；无第三方依赖也要保留该块（形式统一），统一在仓库根用 `uv run .scripts/<脚本> <args>` 执行。
- **禁止**在仓库根或 `.scripts/` 内创建 `pyproject.toml`、`uv.lock`、`.venv`、`requirements.txt`；依赖一律走 PEP 723 + uv 全局缓存。
