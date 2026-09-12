# language_projects —— 语言项目总仓

按编程语言划分的项目工作区集合，父仓库以 **git submodules** 挂载各语言 monorepo，只跟踪子仓库的 commit 指针，代码本体在各自远端仓库。

## 结构

| 子模块 | 内容 | 语言 |
|---|---|---|
| `go_projects/` | Go 项目 monorepo | Go |
| `python_projects/` | Python 项目 monorepo | Python |
| `rust_projects/` | Rust 项目 monorepo | Rust |
| `typescript_projects/` | TypeScript 项目 monorepo | TypeScript |

新增语言时：在 GitHub 建对应 `td-<lang>_projects` 仓库后，在父仓库执行 `git submodule add <URL> <lang>_projects`，并在 `.gitmodules` 该条目补 `ignore = all`。

## 克隆

```bash
git clone --recurse-submodules git@github.com:shihao-hub/td-language_projects.git
```

已克隆但没拉子模块的，补一句：

```bash
git submodule update --init --recursive
```

## 切换子模块到跟踪分支（推荐）

git 子模块默认以 **detached HEAD** checkout 父仓库记录的 commit（这是子模块的设计行为，不是异常）。若希望各子模块直接站在 `main`/`master` 本地分支上，克隆后在仓库根执行一次：

```powershell
./init-submodules.ps1
```

脚本做两件事：初始化子模块 → 按 `.gitmodules` 中各子模块的 `branch` 字段切换到对应本地分支（`git switch` 会在本地无同名分支时自动创建并跟踪 `origin/<branch>`）。

注意：切上分支后子模块代码为**远端分支最新**，可能与父仓库记录的指针 commit 不一致（指针落后时 `git submodule status` 会显示 `+` 前缀）；需要严格对齐历史版本时，用 `git submodule update --init` 回到指针 commit 即可。

## 日常更新

- 拉取子仓库各自远端的最新提交（`.gitmodules` 已为各子模块声明 `branch` 字段，`--remote` 按声明的分支拉取）：

  ```bash
  git submodule update --remote
  ```

- 之后若希望新克隆也能拿到新指针，需提交指针变更并 push。注意 `ignore = all` 会拦截普通 `git add`，必须加 `--force`：

  ```bash
  git add --force go_projects python_projects typescript_projects
  git commit -m "chore: 更新子模块指针"
  git push
  ```

## 日常开发

开发在子仓库内进行，提交链路是两步：

1. 子仓库内 commit + push；
2. 需要时回到父仓库更新指针（`git submodule update --remote` 后 commit）。

## 子仓约定

- **go_projects / rust_projects 只收录 CLI 工具**：GUI/托盘类项目不做，已有者已迁出（CLI 替代版见子仓内各项目）。选 CLI 的核心原因是**跨平台**：无 GUI 框架依赖，单二进制交叉编译分发即可覆盖 Windows / Linux / macOS。
- **跨平台是 go 与 rust 项目的统一方向**：新项目设计时核心逻辑与平台层分离；存量项目（如 rust 的 `minieverything` 依赖 NTFS/USN、`whoholds` 依赖 Windows 句柄枚举）未来均计划逐步跨平台化改造。
- **项目命名单词直接连写，不用连字符**（如 `filesync`、`minieverything`）：目录名即 CLI 命令名，无连字符在 shell 中调用、补全与传参更顺手；也不加语言后缀（不写 `-go`、`-rs`）。go_projects 与 rust_projects 通用。

## 项目归档

项目停更后移出子仓、归档到父仓库根目录 `.archived/<lang>/`，完整流程（前置调研、范围隔离提交、子模块指针更新）见 [SKILL-ARCHIVE.md](SKILL-ARCHIVE.md)。

## 项目盘点

各项目（含归档）的摘要、状态、源码阅读情况与价值评估见 [MONOREPO.md](MONOREPO.md)；盘点表的维护规则与联动纪律见 [SKILL-INVENTORY.md](SKILL-INVENTORY.md)。
