# AGENTS.md

## 仓库结构说明

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **git submodules** 结构：

- 四个子目录（`go_projects`、`python_projects`、`rust_projects`、`typescript_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 各语言子仓内部为 monorepo：每个子目录都是一个独立项目，彼此互不依赖归属关系，各自维护自己的依赖与配置；新增项目时直接建新的子目录，不要在子项目内单独 `git init`。
- 已归档项目与通用文档集中放在**父仓库根目录**，按语言加嵌套路径（由各子仓迁移而来）：
  - `.archived/<lang>/`：归档停更的项目（如 `.archived/go_projects/file-sync`、`.archived/python_projects/lele`）；
  - `docs/<lang>/`：各语言通用文档（如 `docs/go_projects/go 知识点.md`、`docs/typescript_projects/plans/`）。
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

## 归档与文档布局约定

- 归档项目统一放父仓库根目录 `.archived/<lang>/<项目名>/`；语言通用文档放 `docs/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。
- 后续新增归档项目时，同样按 `<lang>` 嵌套放入根目录对应位置。

## 新增语言子模块

1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `ignore = all`，然后 commit。

## 常用命令

- 完整克隆：`git clone --recurse-submodules <URL>`
- 初始化/补拉子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
- 提交指针变更：`git add --force <子模块名>`（`ignore = all` 会拦截普通 `git add`，必须 `--force`）→ `git commit` → `git push`
