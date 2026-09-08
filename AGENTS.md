# AGENTS.md

## 强约束规则

- 所有 AI 回复必须使用中文。
- 所有 spec / plan 类设计文档（requirements.md、design.md、tasks.md、plans/01-plan.md 等）必须使用中文描述。
- 代码注释推荐使用中文；变量名、函数名、类名等代码标识符一律使用英文。
- 专业术语（API、HTTP、TypeScript、React 等）、框架名称、命令行指令、文件路径保留英文原文。
- Git Commit Message 格式：
  - 子模块内（monorepo，一目录一项目）：`<project>:<type>: <subject>`，如 `taskmon:feat: 添加进程树过滤`；需更细范围用 `<project>:<type>(<scope>): <subject>`；
  - 父仓库（无项目维度）：`<type>: <subject>`，如 `docs: 更新仓库约定`；
  - type 限：`feat`（新功能）、`fix`（Bug 修复）、`docs`（文档）、`style`（格式）、`refactor`（重构）、`perf`（性能）、`test`（测试）、`chore`（构建/工具）、`ci`（CI/CD）、`revert`（回滚）；
  - Subject：中文描述，≤ 50 字符，不以句号结尾；祈使语气（添加、修复、优化、重构、移除、更新）；
  - Body：中文，每行 ≤ 72 字符，说明是什么和为什么，`-` 列表格式。
- Git 提交范围隔离：一次提交的文件只能属于同一范围——父仓库自身、某个子仓库根目录、或某个子仓库内的单个子项目；禁止跨范围混提（如多个子项目的改动混在一次提交，或子项目文件与子仓根目录文件混提）。
- 代码修改完成后，向用户展示改动摘要，并给出可直接在 PowerShell 下执行的 git commit 命令。
- 禁止 `SELECT *`：任何 ORM 查询与手写 SQL 一律显式列出所需字段。

### 开发约束（手工编写）

- pg 数据库表尽量避免使用 JSONB，如果一定要使用请说明原因，而且该字段要设置最大容量
- 在 python 项目的 fastapi + sqlalchemy + celery 框架中：
  - 要考虑如何避免一个数据库连接被某个长任务长期持有
  - sqlalchemy 的 BaseModel 类首次创建、增减字段、修改字段时，在任务完成后，需要人工参与审阅，避免出现 N+1、隐式级联操作等问题，所以记得任务完成后提示
  - celery 应该只负责轻任务，重任务可以给 kafka（待定）

## 仓库结构说明

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **git submodules** 结构：

- 四个子目录（`go_projects`、`python_projects`、`rust_projects`、`typescript_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 各语言子仓内部为 monorepo：**一个子目录 = 一个项目**，每个子目录都是一个独立项目，彼此互不依赖归属关系，各自维护自己的依赖与配置；新增项目时直接建新的子目录，不要在子项目内单独 `git init`。
- 已归档项目与通用文档集中放在**父仓库根目录**，按语言加嵌套路径（由各子仓迁移而来）：
  - `.archived/<lang>/`：归档停更的项目（如 `.archived/go_projects/file-sync`、`.archived/python_projects/lele`）；
  - `docs/<lang>/`：各语言通用文档与项目文档（如 `docs/go_projects/go 知识点.md`、`docs/typescript_projects/plans/`），详见下方「归档与文档布局约定」。
- 编辑器配置同样集中在父仓库根目录 `.zed/settings.json`（入库，随仓库分发），子仓内不再各自维护。
- AI 会话产物（`.zcode/`）同样集中在父仓库根目录，子仓内不再各自维护。
- 在本仓库下工作时，先确认目标所在位置（子仓内项目、根 `.archived/`、根 `docs/`），再进入对应目录执行构建、测试等操作。
- 不要试图从父仓库提交子模块内部的改动：子模块内的变更必须在子模块自己的仓库里 commit + push。
- 父仓库层面可见的变更有：`.gitmodules`、子模块指针、README/AGENTS 等自有文件，以及根目录的 `.archived/` 与 `docs/`。

## 隔离性原则（重要）

- 各项目（无论在子仓内还是 `.archived` 内）之间**基本上无任何关联**：没有共享代码、共享依赖或隐含约定，不要假设对一个项目的改动需要另一个项目"配合"。
- 开发某个项目时，**只在该项目目录范围内工作**，不要想着顺带修改另一个项目的事情。
- 即使认为其他项目似乎也需要相应改动，也不要自行跨项目修改；先向用户说明情况，由用户决定是否另行处理。

## 各语言子仓约定

### go_projects

- 曾计划采用 git submodules 管理子项目，后因维护成本退回 monorepo；背景与操作方案见子仓内 `SUBMODULES.md`。

### rust_projects

- 使用 rustup 管理的 stable-x86_64-pc-windows-msvc 工具链，链接器来自 VS Build Tools 2022。
- rustup/cargo 均已配置 rsproxy.cn 国内镜像（环境变量 `RUSTUP_DIST_SERVER` / `RUSTUP_UPDATE_ROOT` + `~/.cargo/config.toml`）。
- cargo 命令均在子项目目录内运行。

### typescript_projects

- 子仓根目录**不创建** `pnpm-workspace.yaml` 和根 `package.json`，子项目之间不做 workspace 关联。

## 归档与文档布局约定（重要）

- **文档只允许放在父仓库**：子模块内的项目目录中**一律禁止**出现任何文档目录与文档内容（`docs/`、`docs/specs/`、`docs/plans/`、`spec/`、`specs/`、`plans/` 等均不允许）。
- 所有项目文档（知识沉淀、spec、plan、设计说明等）统一放父仓库根目录 `docs/<lang>/` 下，按子模块内相对路径**镜像层级命名**，并去掉中间冗余的 `docs/` 一层：
  - 例：`go_projects/a/b.md` → `docs/go_projects/a/b.md`；
  - 例：`typescript_projects/taskmon/docs/x.md` → `docs/typescript_projects/taskmon/x.md`。
- 子仓根级说明文件（如 `go_projects/SUBMODULES.md`）不在此列，可保留。
- 归档项目统一放父仓库根目录 `.archived/<lang>/<项目名>/`；语言通用文档放 `docs/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。
- 后续新增归档项目时，同样按 `<lang>` 嵌套放入根目录对应位置。

## 新增语言子模块

1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `branch = <默认分支>` 与 `ignore = all`，然后 commit。

## 常用命令

- 完整克隆：`git clone --recurse-submodules <URL>`
- 克隆后初始化并切换子模块到跟踪分支：`./init-submodules.ps1`（初始化 + 按 `.gitmodules` 的 `branch` 字段切分支，解决子模块默认 detached HEAD）
- 初始化/补拉子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`
