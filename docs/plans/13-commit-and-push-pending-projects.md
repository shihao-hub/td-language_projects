# 待提交项目整改与逐项推送计划

## 概述

### 问题陈述

当前父仓库和 `python_projects` 子仓库同时存在多组未提交内容，且包含虚拟环境、缓存和运行时数据库等不应入库的产物。需要先完成项目代码整改与提交前审查，再严格按仓库边界和逻辑项目拆分 commit，并在每个 commit 完成后立即 push，避免跨项目混提或一次性提交全部变更。

### 已确认需求

- 范围包含当前发现的全部待提交内容。
- `.venv/`、`__pycache__/`、`.pytest_cache/` 和运行时数据库等产物排除并清理，不提交。
- 按建议执行逐项流程：每个逻辑项目单独 commit，commit 后立即 push。
- `python_projects` 子项目先在子仓库内 commit + push，最后父仓库单独提交子模块指针并 push。
- 父仓库现有本地 commit `a3e7b56` 先单独 push，不与后续改动合并。

### 背景与边界

- 父仓库与 `python_projects` 是独立 Git 仓库，不能跨仓库混合提交。
- Python 子仓库当前有三个未跟踪项目：`douyinnotify`、`hucci-registration-use-case-layered`、`zed-pi-stats`。
- 父仓库还有脚本、AOCI、Zed 配置、指南、研究文档、计划/spec 和 HTML 文档等待提交内容；执行时按实际内容再次分类，避免把不同主题混成一个 commit。
- 当前只处理本次已发现的工作区内容，不主动修改其他子仓库或无关项目。

## 执行任务

- [x] **Task 1：建立安全基线并清理运行时产物**
  - 文件：`python_projects/douyinnotify/`、`python_projects/hucci-registration-use-case-layered/`、`python_projects/zed-pi-stats/`、`python_projects/zed-opencode-sessions/sql-pg-sqlalchemy.db`
  - 实现：确认各项目的源码、配置、文档与锁文件；删除或排除 `.venv/`、`__pycache__/`、`.pytest_cache/`、运行时数据库等产物；保留有意提交的源码和必要资源。
  - 验证：分别执行两个仓库的 `git status --short` 与 `git diff --check`，预期不再出现运行时产物，且不存在空白错误。
  - Demo：展示每个待提交项目的干净文件清单和明确的提交边界。

- [x] **Task 2：整改并验证 `douyinnotify`**
  - 文件：`python_projects/douyinnotify/` 下实际源码、配置与文档文件
  - 实现：审查 CLI、MCP、schema、数据目录、异常处理、类型契约和 Windows 计划任务相关代码；仅在发现问题时修复，保持项目既有约定。
  - 验证：在项目目录执行 `uv run pyright` 和 `uv run pytest`，预期类型检查无错误、测试全部通过；再执行 `git diff --check`。
  - Demo：能够说明该项目的源码和必要配置已可独立提交，且不含虚拟环境和缓存。

- [x] **Task 3：整改并提交推送 `douyinnotify`**
  - 文件：`python_projects/douyinnotify/` 下 Task 2 确认的文件
  - 实现：仅暂存该项目文件，提交符合约定的中文 commit message，提交完成后立即 push 到 `python_projects` 当前跟踪分支。
  - 验证：提交前后分别检查 `git diff --cached`、`git status --short --branch` 和远端同步状态；预期该项目变更已在一个独立 commit 中推送，其他项目仍未被暂存。
  - Demo：给出 commit 哈希、推送结果和剩余工作区状态。

- [x] **Task 4：整改并提交推送 `hucci-registration-use-case-layered`**
  - 文件：`python_projects/hucci-registration-use-case-layered/` 下实际源码、文档和必要资源
  - 实现：审查四层示例的模块边界、依赖声明、测试入口和不应入库的生成物；仅在发现问题时修复；将该项目作为独立逻辑项目提交并立即 push。
  - 验证：在项目目录执行项目声明的真实验证命令（优先 `uv run pytest` 或项目内测试入口），并执行 `git diff --check`；预期验证通过且 commit 不包含 `.venv/`、缓存和临时文件。
  - Demo：给出该项目独立 commit 哈希、推送结果和验证结论。

- [x] **Task 5：整改并提交推送 `zed-pi-stats`**
  - 文件：`python_projects/zed-pi-stats/` 下实际源码、配置与文档文件
  - 实现：审查 CLI、JSON/schema 输出、Zed 与 pi 数据读取、路径安全、只读副本处理和错误输出；仅在发现问题时修复；将该项目独立提交并立即 push。
  - 验证：执行项目可用的 `uv run zed-pi-stats --json`、`uv run zed-pi-stats --schema` 或等价无副作用检查，并执行 `git diff --check`；预期命令成功且不在仓库内生成运行时数据。
  - Demo：给出该项目独立 commit 哈希、推送结果和验证结论。

- [x] **Task 6：单独推送父仓库现有 commit**
  - 文件：父仓库 Git 引用，不修改业务文件
  - 实现：在确认工作区变更不会影响已存在 commit 的前提下，单独 push `a3e7b56`，不 amend、不 squash、不与后续内容合并。
  - 验证：执行父仓库 `git push origin main` 和 `git status --short --branch`；预期 `a3e7b56` 已到达 `origin/main`。
  - Demo：给出远端确认结果。

- [x] **Task 7：按逻辑主题逐项提交并推送父仓库剩余内容**
  - 文件：父仓库当前剩余的脚本、配置、AOCI、指南、研究文档、计划/spec 与 HTML 文档
  - 实现：逐项复核内容归属，按父仓库边界和逻辑主题拆成多个独立 commit；每次只暂存一个主题，提交后立即 push；不提交 Python 子项目源码本体。
  - 验证：每个 commit 前执行 `git diff --cached --check` 并复核暂存文件列表，每次 push 后检查 `git status --short --branch`；预期每个 commit 只包含一个逻辑主题且远端同步。
  - Demo：列出父仓库每个 commit 的哈希、主题、文件范围和 push 结果。

- [ ] **Task 8：更新并提交父仓库子模块指针**
  - 文件：父仓库对应 `python_projects` 子模块指针
  - 实现：确认 Python 子仓库的目标 commit 均已 push 后，回到父仓库更新子模块指针；仅提交指针变更，完成后立即 push。
  - 验证：执行 `git submodule status`、父仓库 `git diff --cached`、`git status --short --branch`；预期父仓库指针与远端 Python 子仓库提交一致，工作区清洁。
  - Demo：给出最终父仓库 commit、子仓库 commit 对应关系和所有远端分支状态。

## 完成标准

- 所有纳入范围的源码和文档均已按仓库边界提交。
- 每个逻辑项目和主题均有独立 commit，未把多个项目一次性混提。
- 每个 commit 均已立即 push，父仓库与子仓库均无未推送提交。
- 虚拟环境、缓存、运行时数据库等产物未进入 commit。
- 最终父仓库和 `python_projects` 工作区均无未处理的意外改动。

---

最后更新：2026-09-22
作者：AI
版本：1.0
