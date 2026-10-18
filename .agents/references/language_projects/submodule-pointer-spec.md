# 新增语言子模块及规则软链规范（自根 AGENTS.md §八 迁出 · 按需引用）

> **触发**：新增子模块/子项目或调整规则软链前必读。本文件不在规则自动加载目录（`.agents/rules/`）内，由根 `AGENTS.md` 触发器指引按需读取。

### 1. 新增语言子模块（一级子仓）
1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `branch = <默认分支>` 与 `ignore = all`，然后 commit；
4. 运行全仓软链脚本建立规则软链（见下文）。

### 2. 子模块与子项目的 Agent 规则软链规范（强约束与自动同步）
为防止 Submodule 隔离导致 Agent 丢失父仓主规则，全仓实行**单一真理来源（SSOT）相对软链**：
- **拓扑结构**：
  - 一级子仓：`<lang>_projects/AGENTS.md` 与 `CLAUDE.md` 软链接至 `..\AGENTS.md` 与 `..\CLAUDE.md`；
  - 二级子项目：`<lang>_projects/<project>/AGENTS.md` 与 `CLAUDE.md` 软链接至 `..\..\AGENTS.md` 与 `..\..\CLAUDE.md`；
  - 根目录 `AGENTS.md` 与 `CLAUDE.md` 为唯一真身，各级目录均通过相对符号链接透明穿透读取，严禁维护多份割裂副本。
- **一键自动化同步脚本**：
  - 新建任何子仓或子项目后，直接运行运维脚本自动补齐/覆盖软链：
    ```bash
    uv run .scripts/link-subproject-agents.py          # 自动为全仓各级补齐软链
    uv run .scripts/link-subproject-agents.py --check  # 体检各处软链是否完好
    ```
- **提交与推送规范**：
  - 新建的符号链接必须在对应子仓**自己的 Git 仓库中**先行 `git commit` 并 `git push`（文件模式为 `120000`）；
  - 随后在父级仓库中更新对应的 submodule 指针并提交推送。
