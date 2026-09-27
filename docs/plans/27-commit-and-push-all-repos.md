# 全仓（主仓与各子仓）逐项提交与推送实施计划

## 目标描述

全面审查当前 monorepo 父仓库（`language_projects`）及三个活跃子仓库（`go_projects`、`python_projects`、`typescript_projects`）的工作区修改与未跟踪文件。严格遵循仓库强约束《AGENTS.md》与《sh-monorepo-commit-push》规范，按单一项目、单一主题独立切分 commit，杜绝跨项目混提与代码/文档混提；逐仓完成本地测试验证、提交与远端推送，并在父仓更新子模块指针后完成最终推送。

## 需要用户审阅

> [!IMPORTANT]
> **关于推送范围与远程分支：**
> 1. 父仓库当前本地分支 `main` 已领先 `origin/main` 46 个提交，本次将连同这 46 个历史提交以及后续所有新拆分提交一并推送到 GitHub 远端 `origin main`。
> 2. `go_projects` 当前领先 `origin/main` 2 个本地提交（`agyquota` 与 `typeai`），本次新增 2 个提交后将统一推送到 `origin main`。
> 3. `rust_projects` 与 `native_projects` 当前未在本地检出（无工作区改动），本次保持不动。

> [!WARNING]
> **关于 `ignore = all` 子模块指针：**
> 父仓库 `.gitmodules` 中子模块均配置了 `ignore = all`，更新指针时必须使用 `git add --force <submodule>` 显式暂存。

## 待澄清问题

*暂无阻塞性问题，改动意图与归属清晰。*

## 变更方案

---

### [子仓: python_projects]

- **变动摘要**：`todo_notify` 项目目录与 Python 包重命名为小写规范 `todonotify`，已暂存 16 个文件重命名及模块导出文件。
- **预检验证**：在 `python_projects/todonotify` 运行 `uv run pytest`，30 个单测全部通过。

#### [MODIFY] 提交并推送
- **文件范围**：
  - `todonotify/**`
  - `todo_notify/**`（删除旧路径）
- **Commit 规范**：
  - Message: `todonotify:refactor: 目录与包命名规范化迁移为 todonotify`
  - Body:
    - 统一模块包名为无连字符小写规范 todonotify
    - 更新 pyproject.toml、uv.lock 与所有测试导入路径
- **Push 操作**：`git push origin main`

---

### [子仓: typescript_projects]

- **变动摘要**：新增 `gemini-launcher` 项目（Chrome MV3 扩展与 Native Messaging Host，呼出 Chrome 原生 Gemini 伴侣侧边栏）。

#### [NEW] 提交并推送
- **文件范围**：
  - `gemini-launcher/**`
- **Commit 规范**：
  - Message: `gemini-launcher:feat: 实现 Chrome Gemini 原生图标启动器扩展与 Native Host`
  - Body:
    - 提供极简四角星芒图标 Chrome 扩展
    - 基于 uv 和 Windows ctypes SendInput 模拟 Alt+Shift+G 快捷键
    - 附带 Native Messaging 注册表自动配置脚本与说明
- **Push 操作**：`git push origin main`

---

### [子仓: go_projects]

- **变动摘要**：
  1. 根目录新增 `NOTE.md`（CLI 工具命名规范笔记）。
  2. 新增 `sourcecount` 代码行数统计工具（CLI + MCP Server + Windows 图标资源）。
- **预检验证**：在 `go_projects/sourcecount` 运行 `go test ./...` 及 `go build ./...`，编译测试均正常。

#### [NEW] 批次 1: 提交根目录规范笔记
- **文件范围**：
  - `NOTE.md`
- **Commit 规范**：
  - Message: `docs: 添加 CLI 工具命名连字符规范笔记`

#### [NEW] 批次 2: 提交 sourcecount 项目
- **文件范围**：
  - `sourcecount/**`
- **Commit 规范**：
  - Message: `sourcecount:feat: 初始化代码行数统计 CLI 与 MCP 服务`
  - Body:
    - 实现代码行数与文件分类统计功能
    - 支持表格打印、--json 机器导出与 stdio MCP 服务
    - 嵌入 Windows 默认图标与构建脚本

#### [PUSH] 推送全部提交
- **Push 操作**：`git push origin main`（推送包含此前未推的 2 个提交及本次 2 个新提交）

---

### [父仓: language_projects]

严格遵循 AGENTS.md 的独立提交与隔离纪律，按主题依次提交：

#### [NEW] 批次 1: 计划落盘自举提交（强制规则：新建计划立即独立 commit）
- **文件范围**：`docs/plans/27-commit-and-push-all-repos.md`
- **Commit**：`docs(plans): 新增全仓分别提交与推送实施计划`

#### [MODIFY] 批次 2: 计划文件 Mermaid 格式修复
- **文件范围**：`docs/plans/16-zedagentstats.md`
- **Commit**：`docs(plans): 修复 16-zedagentstats 计划中的 Mermaid 语法与图表转义`

#### [NEW] 批次 3: typeai 规格文档
- **文件范围**：`docs/projects/go_projects/typeai/specs/02-image-blob-and-context-decay/`
- **Commit**：`docs(specs): 添加 typeai 02-image-blob-and-context-decay 规格文档`

#### [MODIFY/NEW] 批次 4: CLI 工具开发标准文档
- **文件范围**：
  - `docs/projects/go_projects/CLI 工具开发标准.md`
  - `docs/projects/go_projects/CLI 工具开发标准 v2.md`
- **Commit**：`docs(cli-standard): 补充 CLI 工具开发标准 v2 草案并更新 v1 协同指引`

#### [MOVE/NEW] 批次 5: 知识库通用调研与参考文档
- **文件范围**：
  - `docs/repo/lark_group_bridge/参考-鱼皮-7个神级技巧去AI味.md`（删除）
  - `docs/repo/参考-鱼皮-7个神级技巧去AI味.md`（新增/移动）
  - `docs/repo/nosql-vs-rdbms-architecture-research.md`（新增）
- **Commit**：`docs(repo): 扁平化整理参考文档并收录 NoSQL 与 RDBMS 深度调研`

#### [NEW] 批次 6: 归档项目教学资源
- **文件范围**：`.archived/projects/python_projects/lele/变式练习7-2_氯气歧化守恒法讲义/`
- **Commit**：`chore(archived): 归档化学变式练习氯气歧化守恒法讲义及教案`

#### [MODIFY/NEW] 批次 7: 文档站点 Mermaid 离线渲染支持
- **文件范围**：
  - `mkdocs.yml`
  - `docs/assets/javascripts/mermaid.min.js`
- **Commit**：`docs: 配置 MkDocs 支持 Mermaid 本地离线渲染`

#### [MODIFY] 批次 8: 编辑器配置调整
- **文件范围**：`.zed/settings.json`
- **Commit**：`chore(zed): 在 settings.json 中忽略虚拟环境路径`

#### [POINTER] 批次 9: 更新 go_projects 子模块指针
- **命令**：`git add --force go_projects`
- **Commit**：`chore(submodule): 更新 go_projects 子模块指针`

#### [POINTER] 批次 10: 更新 python_projects 子模块指针
- **命令**：`git add --force python_projects`
- **Commit**：`chore(submodule): 更新 python_projects 子模块指针`

#### [POINTER] 批次 11: 更新 typescript_projects 子模块指针
- **命令**：`git add --force typescript_projects`
- **Commit**：`chore(submodule): 更新 typescript_projects 子模块指针`

#### [PUSH] 推送父仓
- **命令**：`git push origin main`

## 验证方案

### 自动化测试与命令验证
- `cd python_projects/todonotify; uv run pytest`：确保 30 项单测通过。
- `cd go_projects/sourcecount; go test ./...` 及 `go build ./...`：确保 Go 项目可正常构建。
- `git submodule status`：确认各子模块指针与最新 commit 对齐无漂移。
- `git log origin/main..HEAD`：确认父仓与子仓均无未推送到远端的本地提交。
- `git status`：在父仓与所有子仓分别执行，确保各工作树处于 clean 状态。

### 人工验证
- 检查各仓库 GitHub 远端，确认新 commit 与子模块引用正常展示。
