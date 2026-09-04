# AGENTS.md

## 仓库结构说明

本仓库（`language_projects`）是按语言划分的项目总仓，采用 **git submodules** 结构：

- 四个子目录（`go_projects`、`python_projects`、`rust_projects`、`typescript_projects`）各自是独立 Git 仓库，父仓库只跟踪它们的 commit 指针（`.gitmodules` 中 `ignore = all`）。
- 在本仓库下工作时，先确认目标项目所在子模块与子目录，再**进入对应子模块目录**执行构建、测试等操作。
- 不要试图从父仓库提交子模块内部的改动：子模块内的变更必须在子模块自己的仓库里 commit + push。
- 父仓库层面可见的变更只有：`.gitmodules`、子模块指针、README/AGENTS 等自有文件。

## 新增语言子模块

1. 在 GitHub 创建 `td-<lang>_projects` 仓库并推送内容；
2. 父仓库执行 `git submodule add git@github.com:shihao-hub/td-<lang>_projects.git <lang>_projects`；
3. 在 `.gitmodules` 该条目补 `ignore = all`，然后 commit。

## 常用命令

- 完整克隆：`git clone --recurse-submodules <URL>`
- 初始化/补拉子模块：`git submodule update --init --recursive`
- 跟进子仓库远端新提交：`git submodule update --remote`
