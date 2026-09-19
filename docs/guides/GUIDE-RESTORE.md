---
name: project-restore
description: 把父仓库 .archived/<lang>/ 下的归档项目恢复回对应语言子仓（go/python/rust/typescript monorepo）的完整工作流，是 project-archive 的逆操作。当用户要求"恢复项目"、"从归档恢复"、"把项目移回子仓"、"unarchive"、"还原 .archived 下的项目"，或说"这个项目我想重新维护了"、"从归档里给我恢复"时必须使用本 skill——即使没说出"恢复"二字，只要意图是把 .archived/ 里的项目迁回子仓都要触发。本流程继承归档三大纪律（提交范围隔离、子模块指针 --force 更新、先子仓 push 再父仓提交指针），另有一个归档没有的独有陷阱：父仓库 .archived/ 下常积攒无关未跟踪文件，必须用精确路径暂存，否则会混入提交。
---

# Skill: project-restore

# 项目恢复（父仓库 .archived/ → 子仓 monorepo）

## 概述

本仓库（`language_projects`）结构：父仓库 + 4 个 git submodule（各语言 monorepo，一个子目录 = 一个项目）。已归档到 `.archived/<lang>/<项目名>/` 的项目要重新维护时，移回对应语言子仓根目录。

恢复的高层流程（与归档互为镜像，提交方向相反）：

1. 只读调研（归档现状、子仓同名占用、脏改动、指针漂移）
2. 向用户呈现发现与计划，等待确认
3. 子仓：移入目录 → 一次提交 → push
4. 父仓库：归档副本移除、子模块指针分别提交 → push
5. 收尾验证并向用户报告

## 你的任务

先判断用户处在哪个阶段，再跳入对应位置：

- 用户给出 `.archived` 下的项目路径要求恢复 → 从「阶段 0」开始
- 用户已确认计划、要求继续 → 从上次中断的阶段继续
- 用户质疑某次恢复结果（指针不对、脏文件混入）→ 对照「陷阱速查」定位

任何阶段都不要跳过调研直接动手——恢复比归档多两类风险：**同名路径冲突**（子仓里可能已有新项目占了同名目录）与 **`.archived` 下的无关未跟踪文件被吸进提交**。

## 核心纪律

前三条与归档共用，后三条是恢复场景的重点，理解原因比死记步骤更重要：

1. **提交范围隔离**。子仓一次提交只属于一个项目；父仓库固定两次提交（副本移除 + 指针）。
2. **子模块指针必须显式更新**。`.gitmodules` 配了 `ignore = all`，普通 `git add` 会被拦截，必须 `git add --force <子模块名>`。指针不更新，新克隆拿到的还是旧子仓 commit，恢复等于没发生。
3. **先子仓 push，再父仓库提交指针**。父仓库指针指向的 commit 必须已存在于子仓远端，否则他人 `clone --recurse-submodules` 直接失败。
4. **父仓库暂存必须用精确路径**。归档时 `git add .archived` 整目录加是安全的（新增的都是已知文件）；恢复时不行——`.archived` 下往往积攒了其他语言的未跟踪目录（后续归档残留、临时产物），整目录暂存会把它们一并吸进提交。必须 `git add -A ".archived/<lang>/<项目名>"`，提交前后 `git status --short` 核对。
5. **push 会带出既有领先提交**。子仓/父仓库本地本就领先远端 N 个提交时，push 必然一并推走，这是既成事实——在计划阶段提前告知用户即可。
6. **全大写文档随项目原样恢复**。项目内的 `README.md`、`STRUCTURE.md` 等全大写文件按仓库约定豁免文档迁移规则，直接随目录回去即可；不要"顺手"把它们拆到 `docs/<lang>/`，那会让恢复结果偏离归档前的原始状态。

## 阶段 0：前置调研（全部只读）

按序检查，任何异常都列入计划让用户确认：

1. **父仓库状态**：`git status`、`git log --oneline -3`。确认 `.archived/<lang>/<项目名>/` 存在且被跟踪（`git ls-files` 数一下文件数）；记录父仓库领先远端几个提交；列出 `.archived` 下所有**无关未跟踪目录**——它们是阶段 2 暂存的防护对象，提前点名。
2. **子仓状态**：对应语言子仓内 `git status`、`git log --oneline -3`。记录脏改动（区分本次相关/无关）、本地领先远端几个提交。
3. **同名占用与归档历史**：子仓内 `Test-Path <项目名>` 与 `git ls-files <项目名>`。同名路径已存在 = 冲突，先停下与用户确认处理方式。另查 `git log --oneline --all -- <项目名>` 找到当年归档移除提交——既确认它曾被跟踪，也为 commit message 措辞提供参照；历史为空说明当年是以未跟踪状态归档的（归档流程跳过了子仓提交），本次恢复提交即为该项目在子仓的首次入库。
4. **嵌套 .git**：`Test-Path ".archived/<lang>/<项目名>/.git"`。monorepo 约定子项目不单独 init；若存在嵌套仓库，先停下与用户确认。
5. **镜像文档**：`docs/<lang>/` 下有无该项目的文档目录。有则说明文档一直在父仓库原地（恢复不动它，两处本就该各归各位）；无则不动。
6. **指针漂移**：父仓库 `git submodule status`，`+` 前缀表示子仓 HEAD 与父仓库记录不一致。不用修复，最终更新指针会一并对齐；在计划里说明即可。

调研完成后向用户呈现：发现 + 分阶段计划 + 待确认问题（至少包括：全大写文档随项目原样恢复、两个仓库 push 各自会带出的既有领先提交、commit message 措辞）。**等待用户确认后再执行。**

## 阶段 1：子仓操作

**1. 物理移入**（PowerShell；目录名可能含空格等特殊字符，一律 `-LiteralPath`；移动后立即用**绝对路径**验证落位——在子仓 workdir 里验证 `.archived\...` 相对路径必然误判）：

```powershell
Move-Item -LiteralPath "D:\Users\language_projects\.archived\go_projects\proj-a" -Destination "D:\Users\language_projects\go_projects\proj-a"
Test-Path -LiteralPath "D:\Users\language_projects\go_projects\proj-a\go.mod"   # 期望 True（源路径期望 False）
```

**2. 暂存 + 提交**（目录已移入，`git add -A <项目名>` 精确暂存整批新增；用 `if ($?)` 保证前一步成功再继续）：

```powershell
git add -A proj-a
if ($?) { git status --short }   # 核对：只有本项目文件入库，无关脏改动留在工作区
git commit -m "proj-a:chore: 从父仓库 .archived 恢复"
```

**3. push**：`git status --short` 确认只剩无关脏改动后 `git push`（会带出既有领先提交），再 `git status -sb` 确认与远端同步。

## 阶段 2：父仓库操作（固定两次提交）

```powershell
# 提交 1：归档副本移除（精确路径！防吸入 .archived 下无关未跟踪目录）
git add -A ".archived/go_projects/proj-a"
git commit -m "chore: 移除已恢复项目 proj-a 的归档副本"

# 提交 2：子模块指针（ignore = all，必须 --force）
git add --force go_projects
git commit -m "chore: 更新 go_projects 子模块指针"

git push   # 会带出既有领先提交
```

副本移除与指针拆开提交：回滚时可以只退指针不动文件（或反之），混提会失去这个自由度。

## 收尾验证与报告

验证三项：父仓库 `git status -sb`（只剩无关改动）、`git submodule status`（目标子仓的 `+` 消失 = 指针对齐）、子仓 `git status -sb` 与远端同步。

ALWAYS 使用此报告结构向用户汇报：

```
| 仓库 | 提交 | 推送 |
|---|---|---|
| <子仓名> | <project>:chore: 从父仓库 .archived 恢复 共 1 次 | ✅（带出既有 N 提交） |
| 父仓库 | 归档副本移除 + 指针更新 共 2 次 | ✅（带出既有 N 提交） |
```

并附说明：未触碰哪些无关改动、全大写文档的处理方式、`docs/<lang>/` 镜像文档是否需要同步。

## 提交信息格式

**示例 1：**
Input: 恢复 go_projects 下项目 sublime-folders
Output: `sublime-folders:chore: 从父仓库 .archived 恢复`

**示例 2：**
Input: 父仓库移除 sublime-folders 归档副本并更新 go_projects 指针
Output: `chore: 移除已恢复项目 sublime-folders 的归档副本` + `chore: 更新 go_projects 子模块指针`

## 陷阱速查

| 陷阱 | 规避 |
|---|---|
| `git add .archived` 吸入无关未跟踪目录 | 用精确路径 `git add -A ".archived/<lang>/<项目名>"`，提交前后核对暂存区 |
| 子仓同名路径已存在 | 调研时 `Test-Path` + `git ls-files` 双查，冲突先停下确认 |
| `git add` 拦截子模块指针 | `ignore = all` 所致，用 `git add --force <子模块名>` |
| 相对路径验证误判 | `Test-Path` 用绝对路径或先确认 workdir |
| push 意外带出旧提交 | 属必然行为，计划阶段提前告知用户 |
| 全大写文档被误拆到 docs/ | 按约定豁免迁移，随项目目录原样恢复 |
| 先提交父仓指针后 push 子仓 | 顺序颠倒产生悬空指针，必须先子仓 push |
