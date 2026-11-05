# 归档说明

- **归档日期**：2026-11-06
- **原路径**：`go_projects/glmquotawatch`（**二级 submodule**，非普通目录）
- **来源仓库**：`git@github.com:shihao-hub/td-go_projects-glmquotawatch.git`（远端保留，未删除）
- **归档时分支**：`feat/fyne-rewrite`（commit `fb50b10`，与远端同步）
- **归档原因**：停更，不再继续维护。本目录是 GLM 用量监控的 **Wails v3 GUI + CLI 双通道版**（旧 CLI 版已另档为 `glmquotawatch-cli`）。

## 内容范围

- 归档副本为 submodule 内 **git 跟踪文件**的快照（两处根级 `AGENTS.md`/`CLAUDE.md` 相对软链已剔除），文档在 `docs/`（原 `docs/projects/go_projects/glmquotawatch-gui/`）。
- **未归档**：`bin/`、`build/`、`frontend/dist`、`frontend/node_modules`、`nul`（Windows 重定向空文件）等构建产物与缓存。

## 恢复方式

远端仓库仍在，直接重新挂载为 submodule 即可恢复完整历史：

```powershell
cd D:\Users\language_projects\go_projects
git submodule add -b main git@github.com:shihao-hub/td-go_projects-glmquotawatch.git glmquotawatch
git submodule update --init glmquotawatch
```

并在 `go_projects/.gitmodules` 该条目补 `ignore = all`；多人协作时按仓库惯例把 `branch = main` 写回。若需恢复归档时的工作分支，在 submodule 内 `git checkout feat/fyne-rewrite`。

`docs/` 应迁移回父仓 `docs/projects/go_projects/glmquotawatch-gui/`（或按项目改名后统一）。
