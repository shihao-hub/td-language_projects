# 子模块/仓库运维命令速查（自根 AGENTS.md §九.1 迁出 · 按需引用）

> **触发**：执行子模块/仓库运维操作时参考。本文件不在规则自动加载目录（`.agents/rules/`）内，由根 `AGENTS.md` 触发器指引按需读取。

- 完整克隆：`git clone --recurse-submodules <URL>`
- 克隆后初始化并切换子模块到跟踪分支：`uv run .scripts/init-submodules.py`（初始化 + 按 `.gitmodules` 的 `branch` 字段切分支，解决子模块默认 detached HEAD）
- 初始化/补格子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`
