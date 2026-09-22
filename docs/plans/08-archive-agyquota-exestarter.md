# 08 - 归档 agyquota 与 exestarter 到父仓库 .archived

> 工作流依据：`docs/guides/GUIDE-ARCHIVE.md`（project-archive）。

## 问题陈述

`go_projects` 子仓内 `agyquota`、`exestarter` 两个 CLI 项目停更，需移出子仓、归档到父仓库
`.archived/projects/go_projects/`。`agyquota` 因 Antigravity 配额接口的客户端身份校验（非 IDE
请求一律 429）无法落地；`exestarter` 为 exe-launcher 的 CLI 演进版，功能已被 clictl 等覆盖。
范围边界：仅这两个项目 + 其父仓镜像文档与项目清单的同步处理，不触碰仓库内任何无关改动。

## 需求（澄清阶段确认）

- 归档目标：`go_projects/agyquota`、`go_projects/exestarter`
- 目的地：`.archived/projects/go_projects/`
- 遵守四大纪律：提交范围隔离、子模块指针 `--force`、先子仓 push 再父仓提指针、无关脏改动零接触

## 背景（阶段 0 只读调研结论）

| 项 | 结论 |
|---|---|
| 跟踪状态 | 两者均被 go_projects 跟踪（agyquota 15 个文件 / exestarter 19 个文件）；子仓工作区干净 |
| 嵌套 .git | 均无 |
| go_projects 子仓 | 领先远端 1 个提交（`69c2c40 agyquota:feat: 添加 Antigravity 配额查询 CLI`），push 会一并带出 |
| 父仓库 | 领先远端 2 个提交；另有多处**与本次无关**的脏改动（AGENTS.md、.gitignore、aoci.*、docs/guides/README.md 等） |
| 子模块指针 | go_projects 显示 `+`（本地领先导致的漂移），本次指针更新后对齐；其余子模块正常 |
| 构建产物 | `agyquota.exe`(10.7MB)、`exestarter.exe`(3.8MB) 为子仓 ignored 产物；父仓 `.gitignore` **不忽略** `*.exe` |
| 根级专属文档 | go_projects 根级无引用两项目的专属文档（`README.md` 为空、`SUBMODULES.md` 无引用） |
| 镜像文档 | `docs/projects/go_projects/agyquota/`（设计说明.md、plans/01-agyquota-quota-cli.md）、`exestarter/`（接口文档.md）；父仓**均未跟踪** |
| 项目清单 | `MONOREPO.md` 的 go_projects 表列有两个项目；该文件当前**已被无关改动污染** |

## 方案

三段式：子仓逐项目提交删除 → 父仓库归档文件与指针两次提交 → 收尾验证。

```mermaid
flowchart LR
  A[清理 .exe 产物] --> B[移动到 .archived]
  B --> C[子仓逐项目 commit]
  C --> D[子仓 push]
  D --> E[父仓 提交归档文件]
  E --> F[父仓 --force 更新指针]
  F --> G[父仓 push]
  G --> H[验证 status / submodule]
```

## 任务分解

- [x] Task 1：清理构建产物（ignored 的 .exe，可重建）
  - 文件：`go_projects/agyquota/agyquota.exe`、`go_projects/exestarter/exestarter.exe`
  - 实现：物理删除两个 exe，避免迁入父仓后被 `git add .archived` 误纳入（父仓不忽略 *.exe）
  - 验证：`git -C go_projects status --short --ignored agyquota exestarter` 输出为空
  - Demo：两目录只剩被跟踪文件

- [x] Task 2：物理移动到 .archived
  - 文件：`go_projects/agyquota` → `.archived/projects/go_projects/agyquota`；`go_projects/exestarter` → `.archived/projects/go_projects/exestarter`
  - 实现：`Move-Item -LiteralPath`（绝对路径）
  - 验证：`Test-Path` 绝对路径 —— 目的为 True、原路径为 False
  - Demo：`.archived/projects/go_projects/` 下出现两项目

- [x] Task 3：子仓逐项目提交删除（一个项目一次提交）
  - 文件：go_projects 子仓索引
  - 实现：`git add -A agyquota` + `git commit -m "agyquota:chore: 归档移除至父仓库 .archived"`；exestarter 同理
  - 验证：`git -C go_projects status --short` 为空
  - Demo：子仓出现两次范围隔离的删除提交

- [x] Task 4：push 子仓
  - 实现：`git -C go_projects push`（会带出既有领先的 1 个提交）
  - 验证：`git -C go_projects status -sb` 显示与 origin/main 同步
  - Demo：远端包含本次删除提交

- [x] Task 5：父仓库提交归档文件
  - 文件：`.archived/projects/go_projects/agyquota`、`.archived/projects/go_projects/exestarter`
  - 实现：`git add -A <上述两精确路径>` + `git commit -m "chore: 归档 go_projects 下 agyquota 与 exestarter 两个停更项目"`
  - 验证：`git show --stat HEAD` 仅出现这两个项目的文件，无其他路径
  - Demo：父仓一次归档提交

- [x] Task 6：父仓库提交镜像文档（独立提交）
  - 文件：`docs/projects/go_projects/agyquota/`、`docs/projects/go_projects/exestarter/`（当前未跟踪）
  - 实现：`git add -A <两精确路径>` + `git commit -m "docs: 归档 agyquota 与 exestarter 项目文档"`
  - 验证：`git show --stat HEAD` 仅含这两个文档目录
  - Demo：归档项目文档入库

- [x] Task 7：父仓库更新 MONOREPO.md（决策 1=b：接受既有无关改动混入本次提交）
  - 文件：`MONOREPO.md`
  - 实现：从 go_projects 表移除 agyquota/exestarter 两行，追加到 `.archived/projects/go_projects` 表（按字母序）
  - 验证：`grep -n -E "agyquota|exestarter" MONOREPO.md` 命中行落在归档表区间（第 70 行之后）
  - Demo：项目清单与实际归档状态一致

- [x] Task 8：父仓库更新子模块指针
  - 实现：`git add --force go_projects` + `git commit -m "chore: 更新 go_projects 子模块指针"`
  - 验证：`git submodule status go_projects` 前缀 `+` 消失；`git show --stat HEAD` 仅含 gitlink
  - Demo：父仓指针指向删除后的新子仓 commit

- [x] Task 9：push 父仓库
  - 实现：`git push`（会带出既有领先的 2 个提交）
  - 验证：`git status -sb` 只剩无关脏改动；`git submodule status` 各子模块无异常漂移
  - Demo：远端包含归档提交与新指针

- [x] Task 10：收尾验证与报告
  - 实现：核对父仓 `git status -sb`、`git submodule status`、子仓与远端同步，输出报告表
  - 验证：go_projects `+` 消失、两子仓与 origin 同步、父仓只剩无关脏改动
  - Demo：归档完整可复现

## 已确认决策（阶段 0 门禁）

1. `MONOREPO.md`：**b** —— 一并更新，接受把既有无关改动混入本次提交（Task 7）
2. `.exe` 构建产物：**a** —— 删除后归档（Task 1）
3. 镜像文档：**a** —— 本次作为独立 docs 提交入库（Task 6）

## 实施说明（执行期记录）

- Task 1：删除 `agyquota.exe`(10.7MB)、`exestarter.exe`(3.8MB) 两个 ignored 构建产物，未入库。
- Task 6 偏差：`exestarter` 镜像文档 `接口文档.md` 早在 `dd87579` 已入库，本轮仅需提交 `agyquota` 的
  两个文档（设计说明.md、plans/01-agyquota-quota-cli.md）。
- Task 7 偏差（已获用户同意 1=b）：`MONOREPO.md` 提交一并带入该文件此前未提交的其他语言项目清单补充，
  本提交共 28 insertions / 6 deletions。
- push 带出既有领先提交：go_projects 带出 `69c2c40`（＋本次 2 次删除提交）；父仓库带出既有领先 2 个提交
  （＋本次 4 次提交）。
- 未触碰的无关脏改动：`.aoci/baseline.json`、`.gitignore`、`AGENTS.md`、`aoci.code.txt`、
  `docs/guides/README.md`、lark_group_bridge html，以及 `docs/memories/`、`docs/specs/` 等未跟踪目录。

---
**最后更新：** 2026-09-22
**作者：** AI & User
**版本：** v1.1
