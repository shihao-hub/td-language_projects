# Git 子模块临时注销（native、rust）

## 背景与当前状态

暂时只关注 `python_projects`、`go_projects`、`typescript_projects`；`native_projects`、`rust_projects` 暂停维护（仅暂时，未来继续）。为保持工作目录清爽，本仓库选择**本地注销**这两个子模块，而不是从 `.gitmodules` / 远端移除。

时间线：

- 2026-09-15：`native_projects`、`rust_projects` 一起本地注销；
- 2026-09-21 前后：`rust_projects` 因 whoholds 项目开发被临时恢复（期间产生提交 `b260a91` 等）；
- 2026-09-26：`rust_projects` 再次本地注销（`native_projects` 始终保持注销状态）。

注销前推送状态核验（`git ls-remote` 实测）：

| 核验日期 | 子仓 | 本地 main | 远端 main | 结论 |
|---|---|---|---|---|
| 2026-09-15 | native_projects | c9c1ee8 | c9c1ee8（td-native_projects.git） | 已全部推送，工作区干净 |
| 2026-09-15 | rust_projects | 4abf191 | 4abf191（td-rust_projects.git） | 已全部推送，工作区干净 |
| 2026-09-26 | rust_projects | b260a91 | b260a91（td-rust_projects.git） | 已全部推送，工作区干净 |

结论：代码完整存在于远端，本地注销零丢失风险。

已知历史遗留：

- **native gitlink 已被静默移除**：`native_projects` 的 gitlink（`089db15`）在 2026-09-19 的提交 `a134f32`（docs: 修正目录迁移后的相对路径链接）中一并消失——因 `.gitmodules` 配置 `ignore = all`，`git status` / `git diff` 均不显示此类子模块变化，删除未被察觉。`.gitmodules` 中 native 条目仍在，但 HEAD/index 已无 gitlink，恢复时不能直接 `git submodule update --init`，需按「恢复」一节重建。
- **rust gitlink 当前在 HEAD/index 中**：值为 `b260a913`（本次注销前与分支一致）。同样因 `ignore = all`，未来提交时避免 `git add -A` / `git add .` 类操作把已注销子模块的 gitlink 静默删除。

## 本目录注销操作（已执行）

2026-09-15 批量注销：

```powershell
git submodule deinit -f native_projects rust_projects
```

2026-09-26 rust 再次注销（native 始终保持注销状态）：

```powershell
git submodule deinit -f rust_projects
```

该命令做了什么 / 没做什么：

- 移除了子模块的工作区内容，并从 `.git/config` 注销（残留空目录已手工删除）；
- **未改动** `.gitmodules`（条目仍在，父仓库无需任何提交）；
- **未触碰**远端，也未删除 `.git/modules/native_projects`、`.git/modules/rust_projects`（本地完整 git 库与分支引用保留）；
- 父仓库 `git status` 对这两个路径无任何变化。

验证命令与预期结果（2026-09-26 实测）：

```powershell
git submodule status                     # rust_projects 显示 '-' 前缀（未初始化）；native_projects 因 gitlink 已移除而不出现
git status --short -- native_projects rust_projects   # 无输出（干净）
Test-Path .git\modules\native_projects   # True（git 库保留）
Test-Path .git\modules\rust_projects     # True（git 库保留）
```

## 脚本操作（推荐）

上述手工步骤已封装为 `.scripts/submodule-toggle.py`（见 README「仓库脚本」表），新接手的 AI 会话可直接按脚本内注释帮助与示例使用：

```powershell
# 只读体检（不修改任何东西）：注销状态、gitlink、工作区与未推送情况
uv run .scripts/submodule-toggle.py -Action status  -Name native_projects,rust_projects

# 临时注销：等价于手工 deinit -f + 清理残留 + 验证；
# 子模块有未提交改动或未推送提交时整批拒绝，已注销的自动跳过（幂等）
uv run .scripts/submodule-toggle.py -Action deinit  -Name native_projects,rust_projects

# 恢复：update --init + 切换 .gitmodules 声明的跟踪分支；
# native 的 gitlink 缺失会被自动处理（回溯历史提交重建 + git add --force），
# 结束后按提示提交父仓库指针即可
uv run .scripts/submodule-toggle.py -Action restore -Name rust_projects
```

与手工操作的对应关系：

- deinit ≈ 「本目录注销操作」一节的手工步骤（deinit -f + 清残留 + 验证），并新增「未提交 / 未推送即拒绝」的前置检查；
- restore（rust）≈ 「恢复」一节 rust 的手工步骤（update --init + switch main）；
- restore（native）≈ 「恢复」一节方案 A（从历史提交取回 gitlink → update --init → switch main → git add --force），历史提交由脚本动态回溯，无需硬编码 hash。

脚本安全边界：不改 `.gitmodules`、不删 `.git/modules/<name>`、不动远端；绝不自动 commit / push。

## 在新目录克隆并保持"注销"状态

推荐流程（全程不拉取 native/rust）：

```powershell
git clone git@github.com:shihao-hub/language_projects.git
cd language_projects
git submodule update --init go_projects python_projects typescript_projects
```

再对已初始化的子模块切换跟踪分支（与 `init-submodules.py` 第 2 步同款命令，只会作用于已初始化的子模块）：

```powershell
git submodule foreach 'branch=$(git config -f $toplevel/.gitmodules submodule.$name.branch); if [ -z "$branch" ]; then branch=main; fi; git switch "$branch" 2>/dev/null || git switch main'
```

注意：

- **不要直接运行 `uv run .scripts/init-submodules.py`**：它会初始化 `git submodule status` 中所有 `-` 前缀的子模块（含 native/rust）；
- `git submodule update --init`（不带路径）同样会拉取全部子模块，必须显式列出三个路径；
- 备选做法：正常 `git clone --recurse-submodules` + `uv run .scripts/init-submodules.py` 拉全五个，然后回到本文档「本目录注销操作」再次注销这两个。

## 恢复（未来继续做 native/rust 时）

**rust_projects**（HEAD/index 中 gitlink 仍在，可直接恢复）：

```powershell
git submodule update --init rust_projects
git -C rust_projects switch main
```

- `update --init` 先 checkout 父仓库记录的 gitlink `b260a913`；`switch main` 后回到分支最新。
- 或一步到位取远端最新：`git submodule update --init --remote rust_projects`。
- 恢复后 `.git/config` 的注册条目会自动重建，其余子模块不受影响。

**native_projects**（gitlink 已于 `a134f32` 被静默移除，需先重建 gitlink）：

```powershell
# 方案 A：从历史提交取回 gitlink 后更新（gitlink 先回到 3536014 记录的旧值 089db15）
git checkout 3536014 -- native_projects
git submodule update --init native_projects
git -C native_projects switch main
git add native_projects
# 完成后按仓库规范提交父仓库指针变更

# 方案 B：用 submodule add 重建（会同步 .gitmodules）
git submodule add -f git@github.com:shihao-hub/td-native_projects.git native_projects
git -C native_projects switch main
```

- 两方案均未实测（native 恢复时再验证）；若报错按提示修正，核心目标是让 HEAD/index 重新出现 `160000` gitlink 并让 `.gitmodules` 条目与之对应。
- 与 rust 不同，native 恢复后**需要提交父仓库指针变更**（因为 gitlink 缺失是一次未提交的历史错误）。
- 切换分支后若 `git submodule status` 显示 `+` 前缀（领先父仓记录的指针）属正常中间态，机制见 `docs/repo/Git 子模块分支机制.md`。

## 相关文档

- `docs/repo/Git 子模块分支机制.md`：子模块 detached HEAD、`+`/`-` 前缀、`branch` 字段等机制说明。
