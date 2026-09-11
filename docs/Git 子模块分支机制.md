# Git 子模块的分支机制与本仓库方案

## 现象与原理

克隆含子模块的仓库后，`git status` 在子模块里显示 `HEAD (no branch)`——**detached HEAD，没有本地分支**。

这是子模块的设计行为而非异常：父仓库记录的是一个**钉死的 commit SHA（gitlink，mode 160000）**，`git clone --recurse-submodules` / `git submodule update --init` 只会 checkout 那个 SHA，checkout 单个 commit 不需要也不产生分支引用。

判断指针是否正常：`git submodule status` 输出无任何前缀 = 子模块 HEAD 与父仓库记录完全一致；`+` 前缀 = 子模块 HEAD 与记录不一致（如领先于指针）；`-` 前缀 = 子模块未初始化。

## 三种"挂分支"机制辨析

| 机制 | 作用范围 | 是否真正切到本地分支 |
|---|---|---|
| `.gitmodules` 的 `branch` 字段 | 仅被 `git submodule update --remote` / `--remote-submodules` 读取，声明追踪哪个**远端**分支；常规 `update --init` 完全无视它 | 否 |
| `git clone --recurse-submodules --remote-submodules`（Git ≥ 2.23） | 改变 checkout 的 commit 来源：取 `branch` 字段（缺省 HEAD）的远端**最新**，而非父仓库记录的 SHA | 否（仍 detached） |
| `git submodule foreach 'git switch ...'` | clone/init 后手动把每个子模块切到本地分支（本地无同名分支时 `git switch` 自动创建并跟踪 `origin/<branch>`） | 是 |

结论：**git 没有任何单一开关能让 clone 直接"站在本地分支上"**；文档（AGENTS.md/README）也无法约束普通用户的 clone 行为。可行做法是仓库自带初始化脚本。

## 本仓库方案

1. `.gitmodules` 为每个子模块声明 `branch` 字段（go/rust = `main`，python/typescript = `master`），作为声明性数据源；
2. 父仓库根 `init-submodules.ps1`：
   - 仅初始化 status 前缀为 `-` 的子模块（不把领先指针的本地 checkout 拽回旧 commit）；
   - `git submodule foreach` 按 `branch` 字段切换本地分支，缺省回退 `master` 再回退 `main`；
3. README「克隆」与 AGENTS「常用命令」引导 clone 后执行一次 `./init-submodules.ps1`。

## 权衡与注意

- **分支最新 ≠ 父仓库指针**：切上分支后代码为远端最新，指针落后时 `git submodule status` 显示 `+` 前缀；要严格对齐历史版本，`git submodule update --init` 回到指针 commit 即可。
- **`--remote` 系列与"父仓库只跟踪 commit 指针"的约定冲突**：`--remote-submodules` / `update --remote` 绕过钉死的指针取远端最新，克隆出的版本可能与父仓库记录不一致，本仓库仅用于「日常更新」流程（更新后需提交新指针）。
- 子模块领先指针是正常中间态：子模块内 commit + push 后，回父仓库 `git add --force <子模块名>` 提交新指针即可消除 `+`。
- 新增子模块时记得在 `.gitmodules` 条目补 `branch = <默认分支>` 与 `ignore = all`，保证脚本对它生效。
