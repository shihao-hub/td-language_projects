---
name: submodule-split
description: 把 language_projects 子仓（go/python/rust/typescript/native 等 monorepo）内部的独立子项目拆分为独立 Git 仓库并作为 Submodule 重新挂载的完整操作手册（二级嵌套 Submodule 规范）。当用户要求"将子项目转为 submodule"、"把项目拆成独立仓库挂载"、"subtree split 拆分项目"、"拆子仓"、"新建 submodule 并挂载"、"项目独立建仓并作为 submodule 引入"时使用本指南。涵盖 GitHub 建仓、subtree split 历史无损切分、目录清理、本地构建缓存备份迁移、Windows 运行中进程占用避坑、.gitmodules 降噪配置（branch + ignore=all）以及父仓指针同步全流程。
---

# Skill: submodule-split

# 子项目拆分为独立 Submodule（Monorepo 子目录 → 独立仓库 + 嵌套挂载）

## 概述

本仓库（`language_projects`）采用 Git Submodules 结构管理多个语言子仓（一级 Submodule，如 `go_projects`）。各子仓内部通常以 monorepo 形式平铺子项目。

当某个子项目满足**独立发版/独立 CI/独立授权开源/多工作区共享**等条件时，需将其从平铺子目录拆分为独立 Git 仓库，并在原位置以**二级 Submodule**形式重新挂载（方案 A）。

```
language_projects (父仓库, Monorepo / Submodules)
  └── <lang>_projects (一级 Submodule: td-<lang>_projects)
        └── <project_name> (二级 Submodule: td-<lang>_projects-<project_name>)
```

本工作流确保：
1. **历史无损**：提交历史通过 `git subtree split` 完整平移，新仓库根目录即为项目根目录；
2. **路径透明**：工作区相对路径不变，外部脚本与 IDE 引用零破坏；
3. **防噪降噪**：严格配置 `branch` 与 `ignore = all`，日常开发不污染父级。

## 触发与豁免

**触发**：
- 用户要求将某个语言子仓内的子项目独立建仓并作为 submodule 重新挂载。
- 用户提到 `subtree split` 拆分项目并保留历史。

**豁免**：
- 废弃/停更的项目移出子仓 → 走 [GUIDE-项目归档.md](GUIDE-项目归档.md)；
- 引入外部第三方开源项目 → 走 [GUIDE-第三方项目克隆.md](GUIDE-第三方项目克隆.md)；
- 新增常规练习或通用 CLI 工具 → 默认直接在子仓新建子目录，无需 submodule。

## 核心纪律

1. **先推子仓，再提父仓指针**。子模块 commit 必须先推送到远端，父级（无论是 `go_projects` 还是 `language_projects`）才能提交指针，否则他人 `clone --recurse-submodules` 会报悬空指针错误。
2. **`.gitmodules` 必须配 `ignore = all` 与 `branch`**。未配 `ignore = all` 会导致子项目内部任何日常代码变动直接在父级 `git status` 产生 `modified: <project>` 噪音；`branch` 指定主跟踪分支便于自动化脚本维护。
3. **父仓更新指针必须 `--force`**。由于 `.gitmodules` 配置了 `ignore = all`，普通的 `git add <submodule>` 会被拦截，必须执行 `git add --force <submodule>`。
4. **优先保护本地缓存**。现代工程（如 Wails、Node、Rust）通常含有重型缓存（`node_modules`、`bin`、`dist`、`.task` 等），物理清理前必须先安全迁移到 Temp，挂载后再还原，避免重新安装的巨大耗时。
5. **严密排查 Windows 进程锁**。带 GUI 或常驻托盘（Tray）的程序，其二进制可执行文件往往被正在运行的进程句柄锁定。在 `git rm` 或删除目录前必须先排查并终止相关进程。

---

## 分阶段工作流

### 阶段 0：前置调研（全部只读）

在正式动代码前，必须执行以下 5 项只读检查：

1. **依赖解耦检查**：
   - 检查目标项目根目录（如 `go.mod`、`package.json`、`Cargo.toml`）是否完全自包含；
   - 确认无指向父目录或兄弟目录的硬编码相对路径（如 Go `replace ../`）。
2. **提交历史整洁度**：
   - 在子仓运行 `git log --oneline -- <project_name>`；
   - 检查提交是否规范（是否有与其他项目混在一起的提交，评估 subtree split 的有效性）。
3. **工作区状态与进程占用**：
   - 检查目标项目工作区是否有未提交修改；
   - 检查是否有同名进程正在运行：
     ```powershell
     Get-Process | Where-Object { $_.ProcessName -like "*<project_name>*" }
     ```
4. **命名与远端权限确认**：
   - 确认 GitHub CLI 状态：`gh auth status`；
   - 拟定仓库名，遵循组织约定（如 `td-<lang>_projects-<project_name>`）。
5. **向用户出具实施计划**：
   - 按照轻量规划工作流，计划落盘至 `docs/plans/{NN}-{feature_name}.md` 并获批。

---

### 阶段 1：创建远端独立仓库

在子仓目录下，通过 `gh` CLI 创建对应的远端公开（或私有）仓库：

```powershell
gh repo create shihao-hub/td-<lang>_projects-<project_name> --public --description "<项目描述>"
```

验证远端仓库创建成功：
```powershell
gh repo view shihao-hub/td-<lang>_projects-<project_name>
```

---

### 阶段 2：提取历史并推送新远端

利用 `git subtree split` 提取只属于该子目录的提交树，生成独立分支并推送到新远端：

```powershell
# 1. 在子仓根目录切分历史
git subtree split -P <project_name> -b split/<project_name>

# 2. 查看切分后的历史，确认纯净
git log -n 5 --oneline split/<project_name>

# 3. 推送至独立远端仓库的 main 分支
git push git@github.com:shihao-hub/td-<lang>_projects-<project_name>.git split/<project_name>:main

# 4. 删除本地临时切分分支
git branch -D split/<project_name>

# 5. 校验远端 HEAD 与 refs
git ls-remote git@github.com:shihao-hub/td-<lang>_projects-<project_name>.git
```

---

### 阶段 3：缓存保护与原目录安全清理

在子仓 monorepo 中摘除原目录，并处理构建缓存与文件锁：

1. **备份未跟踪缓存文件（Temp 中转）**：
   ```powershell
   $tmpCache = Join-Path $env:TEMP "<project_name>_cache"
   if (Test-Path $tmpCache) { Remove-Item -Recurse -Force $tmpCache }
   New-Item -ItemType Directory -Path $tmpCache

   # 按需转移 node_modules, bin, dist, .task 等
   if (Test-Path "<project_name>\frontend\node_modules") {
       Move-Item "<project_name>\frontend\node_modules" "$tmpCache\node_modules"
   }
   if (Test-Path "<project_name>\bin") {
       Move-Item "<project_name>\bin" "$tmpCache\bin"
   }
   ```

2. **终止常驻进程（解除 Windows 文件句柄占用）**：
   ```powershell
   Get-Process | Where-Object { $_.ProcessName -like "*<project_name>*" } | Stop-Process -Force
   ```

3. **从子仓 Git 树移除并提交**：
   ```powershell
   git rm -r <project_name>
   git commit -m "<project_name>:refactor: 拆分为独立 submodule 仓库"
   ```

4. **确保本地物理目录已空**：
   ```powershell
   if (Test-Path <project_name>) { Remove-Item -Recurse -Force <project_name> }
   ```

---

### 阶段 4：挂载 Submodule 并配置降噪

重新将新仓库作为子模块挂载回原路径，并配置忽略规则：

```powershell
# 1. 添加子模块（如果由于文件系统占用残留空目录，可直接在空目录内 clone，或直接 add）
git submodule add git@github.com:shihao-hub/td-<lang>_projects-<project_name>.git <project_name>

# 2. 严格补充 branch 与 ignore 降噪配置（写入 .gitmodules）
git config -f .gitmodules submodule.<project_name>.branch main
git config -f .gitmodules submodule.<project_name>.ignore all

# 3. 还原缓存文件（从 Temp 迁回）
$tmpCache = Join-Path $env:TEMP "<project_name>_cache"
if (Test-Path "$tmpCache\node_modules") {
    Move-Item "$tmpCache\node_modules" "<project_name>\frontend\node_modules"
}
if (Test-Path "$tmpCache\bin") {
    Move-Item "$tmpCache\bin" "<project_name>\bin"
}
Remove-Item -Recurse -Force $tmpCache

# 4. 提交挂载与 .gitmodules 变更，并推送子仓
git add .gitmodules <project_name>
git commit -m "chore: 挂载 <project_name> submodule"
git push origin main
```

---

### 阶段 5：更新文档与同步父仓指针

1. **更新子仓 `SUBMODULES.md` 记录**：
   - 在子仓的 `SUBMODULES.md` 中记录该项目已拆分迁移的事实与远端地址。
   - 提交并推送子仓。
2. **父仓更新一级子模块指针**：
   ```powershell
   # 回到父仓库根目录 language_projects
   cd D:\Users\language_projects

   # 必须使用 --force，避免 ignore = all 拦截
   git add --force <lang>_projects
   git commit -m "chore(<lang>_projects): 更新 <lang>_projects 指针（拆分 <project_name> 为 submodule）"
   ```

---

## 陷阱速查与避坑

| 陷阱场景 | 根本原因 | 规避与处理方案 |
|---|---|---|
| `git rm -r` 报错 `PermissionDenied / Access to the path ... is denied` | Windows 下 exe/dll 被后台常驻或托盘进程锁定 | 使用 `Get-Process` 找到匹配进程并执行 `Stop-Process -Force`，再清理目录 |
| `git submodule add` 报错 `'<dir>' already exists and is not a valid git repo` | 文件系统残留了空目录或未完全释放的句柄 | 先 `cd <dir>; git clone <remote> .`，然后再执行 `git submodule add <remote> <dir>`，Git 会直接识别现存仓库为 index 条目 |
| `git add <submodule>` 没有任何反应，指针未暂存 | `.gitmodules` 配置了 `ignore = all` 拦截了常规暂存 | 必须使用 `git add --force <submodule>` 强制暂存指针变动 |
| 克隆父仓后子模块内容为空 | Git 嵌套子模块未递归拉取 | 执行 `git submodule update --init --recursive`，或使用仓库内置脚本 `uv run .scripts/init-submodules.py` |
| 切分历史后包含其他目录的提交 | 原 monorepo 历史上存在跨项目的混合 commit | 提前排查 `git log`，`subtree split` 仅提取改动影响到该目录的提交，尽量在日常保持一个 commit 对应一个 scope |

---

## 验证清单（收尾核对）

- [ ] **新远端仓库**：GitHub 上能查看完整的代码历史，`HEAD` 指向 `main` 分支。
- [ ] **子仓 `.gitmodules`**：包含 `branch = main` 与 `ignore = all` 配置。
- [ ] **子仓状态**：`git submodule status` 显示正常 commit 哈希，无 `U`（未合并）或异常符号。
- [ ] **本地可构建**：工程内 `bin/`、依赖或构建脚本能正常工作。
- [ ] **父仓指针同步**：父仓执行 `git status` 干净，指针已对齐。
