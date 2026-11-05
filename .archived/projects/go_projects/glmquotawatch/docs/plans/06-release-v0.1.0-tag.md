# 实施计划 - glmquotawatch-gui 发布 v0.1.0 版本 tag

**问题陈述**：
glmquotawatch-gui 已完成 Wails v3 托盘 GUI + 恒 JSON CLI 的首轮开发（仓库共 9 个提交），版本号在三处（`build/config.yml`、`build/windows/Taskfile.yml`、`scripts/build-prod.py`）统一为 0.1.0，但仓库尚无任何 tag；同时工作区存在未跟踪的 `bin/` 构建产物目录（`glmquotawatch-gui.exe~` 备份文件未被 .gitignore 覆盖），需要以干净状态发布首个版本 tag，并推送到远端。

**需求**（含用户澄清决策）：
1. 澄清决策 `1=a`：tag 打在 glmquotawatch-gui 独立仓库内，名为 `v0.1.0`；
2. 澄清决策 `2=a`：补 .gitignore 忽略 `bin/`，先提交该 chore，再打 tag；
3. 澄清决策 `3=a`：只处理 glmquotawatch-gui 自身（提交 + tag + 推 origin），不更新 go_projects 二级指针与父仓指针；
4. tag 采用 annotated tag（带说明消息，发布版本惯例）。

**背景**（只读调研结论）：
- glmquotawatch-gui 是 go_projects 的二级子模块（独立仓库 `td-go_projects-glmquotawatch-gui`，remote origin 已配置，SSH 可访问）；
- 当前分支 `feat/fyne-rewrite` 与本地 `main`、`origin/main` 均指向同一提交 `1b0a618`；远端无任何 tag；
- 工作区无源码改动，唯一未跟踪项为 `bin/`：其中 prod/dev exe 已被 `*.exe` 规则忽略，但 `glmquotawatch-gui.exe~` 备份未匹配任何规则；独立仓库不继承 go_projects 根 .gitignore 中的 `*.exe~` 规则；
- 提交身份已配置（shihao-hub / 2958017271@qq.com）；
- 版本号来源：`build/config.yml` 的 `info.version: 0.1.0`、`build/windows/Taskfile.yml` 的 `-X glmquotawatch-gui/internal/cli.Version=0.1.0`、`scripts/build-prod.py` 的 `version = "0.1.0"`，三者一致。

**方案**：
1. 切到 `main` 分支（与 `feat/fyne-rewrite` 同指针，发布操作落在 main 上）；
2. 在项目 `.gitignore` 的「项目特有规则」区追加 `*.exe~` 与 `bin/`，使 `bin/` 构建产物目录整体不再显示为未跟踪；
3. 提交一条 chore：`glmquotawatch-gui:chore: gitignore 忽略 bin 构建产物目录`；
4. 创建 annotated tag `v0.1.0`（消息：`glmquotawatch-gui v0.1.0`）；
5. 推送 `main` 分支与 `v0.1.0` tag 到 origin。

**任务分解**：

- [x] Task 1: 补 .gitignore 忽略 bin/ 并提交
  - 文件：`go_projects/glmquotawatch-gui/.gitignore`
  - 实现：`git switch main`；在「子仓根 .gitignore 已覆盖 *.exe 等通用产物；此处补充项目特有规则」区追加 `*.exe~` 与 `bin/`；提交 `glmquotawatch-gui:chore: gitignore 忽略 bin 构建产物目录`
  - 验证：`git -C go_projects/glmquotawatch-gui status --short` 输出为空（bin/ 不再显示未跟踪）
  - Demo：工作区干净，`git log -1` 显示新 chore 提交

- [x] Task 2: 打 annotated tag v0.1.0 并推送
  - 文件：无（git 元数据操作）
  - 实现：`git tag -a v0.1.0 -m "glmquotawatch-gui v0.1.0"`；`git push origin main v0.1.0`
  - 验证：`git ls-remote --tags origin` 出现 `refs/tags/v0.1.0`；`git ls-remote --heads origin` 中 main 指向新提交
  - Demo：GitHub 远端可见 v0.1.0 tag，clone 后可检出该版本

**边界说明**：
- 不修改任何源码、不动版本号（保持 0.1.0）；
- 不更新 go_projects 内记录的二级指针，不触碰父仓库指针与 typeai 等无关改动；
- `bin/` 内 exe 产物不提交入库（符合 README「构建产物不入库」约定）。

---
**最后更新：** 2026-09-29
**作者：** AI & User
**版本：** v1.1（已完成）
