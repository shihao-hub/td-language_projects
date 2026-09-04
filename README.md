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

## 日常更新

- 拉取子仓库各自远端的最新提交：

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
