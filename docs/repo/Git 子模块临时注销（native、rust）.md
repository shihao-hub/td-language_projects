# Git 子模块临时注销（native、rust）

## 背景与当前状态

暂时只关注 `python_projects`、`go_projects`、`typescript_projects`；`native_projects`、`rust_projects` 暂停维护（仅暂时，未来继续）。为保持工作目录清爽，本仓库选择**本地注销**这两个子模块，而不是从 `.gitmodules` / 远端移除。

注销前推送状态核验（2026-09-15，`git ls-remote` 实测）：

| 子仓 | 本地 main | 远端 main | 结论 |
|---|---|---|---|
| native_projects | c9c1ee8 | c9c1ee8（td-native_projects.git） | 已全部推送，工作区干净 |
| rust_projects | 4abf191 | 4abf191（td-rust_projects.git） | 已全部推送，工作区干净 |

结论：代码完整存在于远端，本地注销零丢失风险。

已知指针漂移：父仓库 index 中记录的 `native_projects` gitlink 为旧值 `089db15`，而当时实际检出为 `c9c1ee8`。因 `.gitmodules` 配置了 `ignore = all`，父仓库 `git status` 不显示该差异；恢复时切回 `main` 分支即可拿回最新代码。

## 本目录注销操作（已执行）

```powershell
git submodule deinit -f native_projects rust_projects
```

该命令做了什么 / 没做什么：

- 移除了两个子模块的工作区内容，并从 `.git/config` 注销（残留空目录已手工删除）；
- **未改动** `.gitmodules`（条目仍在，父仓库无需任何提交）；
- **未触碰**远端，也未删除 `.git/modules/native_projects`、`.git/modules/rust_projects`（本地完整 git 库与分支引用保留）；
- 父仓库 `git status` 对这两个路径无任何变化。

验证命令与预期结果：

```powershell
git submodule status                     # native_projects、rust_projects 显示 '-' 前缀（未初始化）
git status --short -- native_projects rust_projects   # 无输出（干净）
Test-Path .git\modules\native_projects   # True（git 库保留）
Test-Path .git\modules\rust_projects     # True（git 库保留）
```

## 在新目录克隆并保持"注销"状态

推荐流程（全程不拉取 native/rust）：

```powershell
git clone git@github.com:shihao-hub/language_projects.git
cd language_projects
git submodule update --init go_projects python_projects typescript_projects
```

再对已初始化的子模块切换跟踪分支（与 `init-submodules.ps1` 第 2 步同款命令，只会作用于已初始化的子模块）：

```powershell
git submodule foreach 'branch=$(git config -f $toplevel/.gitmodules submodule.$name.branch); if [ -z "$branch" ]; then branch=main; fi; git switch "$branch" 2>/dev/null || git switch main'
```

注意：

- **不要直接运行 `./init-submodules.ps1`**：它会初始化 `git submodule status` 中所有 `-` 前缀的子模块（含 native/rust）；
- `git submodule update --init`（不带路径）同样会拉取全部子模块，必须显式列出三个路径；
- 备选做法：正常 `git clone --recurse-submodules` + `./init-submodules.ps1` 拉全五个，然后回到本文档「本目录注销操作」再次注销这两个。

## 恢复（未来继续做 native/rust 时）

```powershell
git submodule update --init native_projects rust_projects
git -C native_projects switch main
git -C rust_projects switch main
```

- `update --init` 先 checkout 的是父仓库记录的 gitlink：native 为旧值 `089db15`、rust 为 `4abf191`；`switch main` 后回到分支最新（native `c9c1ee8`）。
- 切到分支后 `git submodule status` 对 native 显示 `+` 前缀（领先父仓记录的指针）属正常中间态，机制见 `docs/repo/Git 子模块分支机制.md`。
- 或一步到位取远端最新：`git submodule update --init --remote native_projects rust_projects`。
- 恢复后 `.git/config` 的注册条目会自动重建，其余子模块不受影响。

## 相关文档

- `docs/repo/Git 子模块分支机制.md`：子模块 detached HEAD、`+`/`-` 前缀、`branch` 字段等机制说明。
