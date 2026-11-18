# Plan for: 将 go_projects\glmquotawatch-gui 拆分为独立 Submodule

**问题陈述**：
当前 `glmquotawatch-gui`（GLM 编码套餐用量监控桌面 GUI 工具）位于 `go_projects` monorepo 内。为了支持独立自动化发版构建、Release 产物发布、CI 隔离以及后续独立分享或开源，需将其拆分为独立 Git 仓库，并在 `go_projects` 中以二级 Submodule 形式重新挂载（方案 A）。

**需求**：
1. 目标仓库名称为 `td-go_projects-glmquotawatch-gui`，托管在 GitHub `shihao-hub` 组织/个人账号下。
2. 采用方案 A（二级嵌套 Submodule）：保留原工程在 `go_projects\glmquotawatch-gui` 的物理工作路径不变，不破坏现有 IDE 路径与脚本。
3. 历史无损提取：将当前 `go_projects` 中关于 `glmquotawatch-gui` 的提交历史完整迁移至新远端。
4. 挂载降噪规范：子模块挂载配置需遵循项目既定规范，声明 `branch = main` 与 `ignore = all`，防止日常开发噪音污染父级。
5. 状态同步：更新 `go_projects/SUBMODULES.md` 与父仓库 `language_projects` 的指针引用。

**背景**：
- `go_projects` 根目录下的 [SUBMODULES.md](file:///D:/Users/language_projects/go_projects/SUBMODULES.md) 已明确定位过 Submodule 迁移时机与参考范式。
- [go.mod](file:///D:/Users/language_projects/go_projects/glmquotawatch-gui/go.mod) 与 [frontend/package.json](file:///D:/Users/language_projects/go_projects/glmquotawatch-gui/frontend/package.json) 均完全自包含，无任何跨目录/跨模块耦合，且当前所有改动均已提交，工作区干净。
- `gh` CLI 已就绪且已登录 `shihao-hub`。

**方案**：
```
language_projects (父仓库, Monorepo / Submodules)
  └── go_projects (一级 Submodule: td-go_projects)
        └── glmquotawatch-gui (二级 Submodule: td-go_projects-glmquotawatch-gui)
```
1. GitHub 建仓：`gh repo create shihao-hub/td-go_projects-glmquotawatch-gui --public`
2. 历史切分：`git subtree split -P glmquotawatch-gui -b split/glmquotawatch-gui` 并推送到 GitHub 新仓库 `main` 分支。
3. 目录清理：在 `go_projects` 中 `git rm -r glmquotawatch-gui` 并提交。
4. 重新挂载：`git submodule add git@github.com:shihao-hub/td-go_projects-glmquotawatch-gui.git glmquotawatch-gui`，并在 `.gitmodules` 补全 `branch` 和 `ignore = all`。
5. 记录更新：修改 `SUBMODULES.md` 标记迁移事实，并在父仓更新 `go_projects` 指针。

**任务分解**：

- [x] Task 1: 创建 GitHub 远端独立仓库
  - 文件：无本地修改
  - 实现：使用 `gh repo create shihao-hub/td-go_projects-glmquotawatch-gui --public --description "GLM 编码套餐用量监控 GUI（Wails v3 + 托盘常驻）"`
  - 验证：`gh repo view shihao-hub/td-go_projects-glmquotawatch-gui` 成功返回仓库信息
  - Demo：GitHub 上已存在空仓库 `shihao-hub/td-go_projects-glmquotawatch-gui`

- [x] Task 2: 提取 glmquotawatch-gui 历史并推送到新远端
  - 文件：`go_projects` 内部临时分支
  - 实现：在 `go_projects` 执行 `git subtree split -P glmquotawatch-gui -b split/glmquotawatch-gui`；推送至 `git@github.com:shihao-hub/td-go_projects-glmquotawatch-gui.git` 的 `main` 分支；清理本地临时分支
  - 验证：`git ls-remote git@github.com:shihao-hub/td-go_projects-glmquotawatch-gui.git` 能查到 `refs/heads/main`
  - Demo：新仓库拥有完整的提交历史与根目录源码结构

- [x] Task 3: 移除 go_projects 内的原生目录并提交
  - 文件：`go_projects/glmquotawatch-gui/`（物理目录移除）
  - 实现：在 `go_projects` 执行 `git rm -r glmquotawatch-gui` 并执行规范提交
  - 验证：`git status` 显示 `deleted: glmquotawatch-gui/...` 全部暂存，提交后工作区干净
  - Demo：`glmquotawatch-gui` 目录在 `go_projects` 历史中被移除并封版

- [x] Task 4: 挂载 td-go_projects-glmquotawatch-gui 为 submodule 并配置降噪
  - 文件：`go_projects/.gitmodules`、`go_projects/glmquotawatch-gui`
  - 实现：执行 `git submodule add git@github.com:shihao-hub/td-go_projects-glmquotawatch-gui.git glmquotawatch-gui`；配置 `submodule.glmquotawatch-gui.branch main` 与 `submodule.glmquotawatch-gui.ignore all`；提交并推送 `go_projects`
  - 验证：`git submodule status` 显示正常指针，`cat .gitmodules` 包含预期配置
  - Demo：`glmquotawatch-gui` 成功恢复到原路径，以 submodule 方式运行且构建正常

- [x] Task 5: 更新文档记录并同步父仓指针
  - 文件：`go_projects/SUBMODULES.md`、`language_projects` 父仓指针
  - 实现：在 `SUBMODULES.md` 中记录 `glmquotawatch-gui` 已完成 submodule 化；提交并推送；回到 `language_projects` 根目录执行 `git add --force go_projects` 并提交父仓变更
  - 验证：父仓 `git status` 干净，`git submodule status` 正常
  - Demo：完成整个迁移闭环，父仓与子仓状态完全对齐

---
**实施说明与偏差**：
- Windows 托盘常驻进程 `glmquotawatch-gui.exe` 和 `glmquotawatch-gui-dev.exe` 会锁定 exe 导致目录移除失败，实施期间已安全终止进程。
- 本地 `node_modules`、`bin`、`dist`、`.task` 等缓存已完整保留并迁回，无需重新 `npm install`。
- 新建远端仓库地址：`https://github.com/shihao-hub/td-go_projects-glmquotawatch-gui`。
- `go_projects` 仓库已提交并推送到 GitHub 远端 `main` 分支。
- 父仓库 `language_projects` 已完成 `go_projects` 指针更新并提交。

**最后更新：** 2026-09-26
**作者：** Antigravity & User
**版本：** v1.0.0
**最终状态：** 全部任务已完成
