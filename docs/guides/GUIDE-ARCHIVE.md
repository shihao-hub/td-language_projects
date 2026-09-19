---
name: project-archive
description: 把 language_projects 子仓（go/python/rust/typescript monorepo）内的项目归档到父仓库 .archived/<lang>/ 的完整工作流。当用户要求"归档项目"、"移动到 .archived"、"停更项目下线"、"把项目移出子仓"，或说"这几个项目不维护了，收起来"、"移到归档目录"时必须使用本 skill——即使没说出"归档"二字，只要意图是把子仓内项目迁到父仓库 .archived/ 都要触发。本流程涉及 git submodules 指针更新（--force）、子仓与父仓库分层提交、提交范围隔离三大纪律，漏掉任何一步都会留下脏状态或产生他人无法克隆的悬空指针。
---

# Skill: project-archive

# 项目归档（子仓 monorepo → 父仓库 .archived/）

## 概述

本仓库（`language_projects`）结构：父仓库 + 4 个 git submodule（各语言 monorepo，一个子目录 = 一个项目）。项目停更后要移出子仓、落入父仓库根目录 `.archived/<lang>/<项目名>/`。

归档的高层流程：

1. 只读调研（跟踪状态、脏改动、专属文档、指针漂移）
2. 向用户呈现发现与计划，等待确认
3. 逐子仓：移动目录 → 逐项目提交 → push
4. 父仓库：归档文件、子模块指针分别提交 → push
5. 收尾验证并向用户报告

## 你的任务

先判断用户处在哪个阶段，再跳入对应位置：

- 用户给出一批项目路径，要求归档 → 从「阶段 0」开始
- 用户已确认计划、要求继续 → 从上次中断的阶段继续
- 用户质疑某次归档结果（指针不对、脏文件混入）→ 对照「陷阱速查」定位

任何阶段都不要跳过调研直接动手——本流程一半的错误源于把未跟踪项目当被跟踪项目处理、或把无关脏改动混进提交。

## 核心纪律

理解这些规则背后的原因，比死记步骤更重要：

1. **提交范围隔离**。子仓内一次提交只允许属于一个范围——单个项目，或子仓根级文件。归档 5 个项目就是 5 次提交。混提会丢失回滚粒度、让历史难以审阅。
2. **子模块指针必须显式更新**。`.gitmodules` 配了 `ignore = all`，普通 `git add` 会被拦截，必须 `git add --force <子模块名>`。指针不更新，新克隆拿到的还是旧子仓 commit，归档等于没发生。
3. **先子仓 push，再父仓库提交指针**。父仓库指针指向的 commit 必须已存在于子仓远端，否则他人 `clone --recurse-submodules` 直接失败。
4. **无关脏改动零接触**。子仓/父仓库常有与本次无关的未提交改动，一律精确 `git add -A <目标路径>`，提交前后用 `git status --short` 核对暂存区。
5. **push 会带出既有领先提交**。若某仓库本地本就领先远端 N 个提交，push 必然一并推走，这是既成事实，无法只推本次提交——在计划阶段提前告知用户即可。

## 阶段 0：前置调研（全部只读）

按序检查，任何异常都列入计划让用户确认：

1. **三层仓库状态**：父仓库与涉及子仓各自 `git status`、`git log --oneline -3`。记录：脏改动内容（区分本次相关/无关）、本地领先远端几个提交。
2. **目标项目是否被跟踪**：`git ls-files <项目名>`。
   - 输出为空 = 完全未跟踪 → 移动它**无需子仓提交**，只是父仓库新增文件；入库前必须检查内容（垃圾/大二进制/敏感文件）。
   - 有输出 = 被跟踪 → 移动后子仓要提交删除。
3. **嵌套 .git**：`Test-Path <项目>\.git`。monorepo 约定子项目不单独 init；若存在嵌套仓库，先停下与用户确认处理方式。
4. **子仓根级文档是否为待归档项目专属**：用 Select-String 在子仓根级文件（README/STRUCTURE 等）中 grep 项目名。整篇讲某个待归档项目的文档（如曾经的 `STRUCTURE.md` 之于 sublime-folders）不属于任何单个项目范围，需用户决定去留——默认建议随项目迁入 `.archived`，子仓单独一次提交。
5. **镜像文档与引用**：`docs/<lang>/` 下有无该项目的文档目录；父/子仓 README 是否列项目清单。有则列入计划同步处理，无则不动。
6. **`.archived/<lang>/` 目录存在性**：不存在则创建。
7. **子模块指针漂移**：`git submodule status` 中 `+` 前缀表示子仓 HEAD 与父仓库记录不一致。不用修复，最终更新指针会一并对齐；在计划里说明即可。

调研完成后向用户呈现：发现 + 分阶段计划 + 待确认问题（至少包括：根级专属文档去留、父仓库提交拆分方式、commit message 措辞）。**等待用户确认后再执行。**

## 阶段 1：子仓操作（逐语言执行）

**1. 物理移动**（PowerShell；目录名可能含空格等特殊字符，一律 `-LiteralPath`）：

```powershell
$dest = "D:\Users\language_projects\.archived\go_projects"
foreach ($p in @('proj-a','proj-b')) { Move-Item -LiteralPath $p -Destination "$dest\$p" }
```

移动后立即验证落位。注意相对路径陷阱：`Test-Path` 要么用绝对路径，要么先确认当前 workdir（在子仓内验证 `.archived\...` 相对路径必然误判为 False）。

**2. 未跟踪项目先清垃圾**：`__pycache__`、构建产物、下载缓存（如 `vsixs/`）物理删除。项目自带的 `.gitignore` 通常已忽略它们，但入父仓库前删掉最干净。

**3. 逐项目提交**（目录已移走，`git add -A <路径>` 会 stage 整个删除；用 `if ($?)` 保证前一步成功再继续）：

```powershell
git add -A proj-a
if ($?) { git commit -m "proj-a:chore: 归档移除至父仓库 .archived" }
```

一个项目一次提交，串行执行。根级专属文档最后单独一次：

```powershell
git add -A STRUCTURE.md
if ($?) { git commit -m "chore: 移除 proj-x 专属 STRUCTURE.md 随项目归档" }
```

**4. push**：`git status --short` 确认只剩无关脏改动后 `git push`，再 `git status -sb` 确认与远端同步。

## 阶段 2：父仓库操作（固定两次提交）

```powershell
# 提交 1：归档文件本体（含从未跟踪项目迁来的新文件）
git add .archived
git commit -m "chore: 归档 go 与 python 共 N 个停更项目"

# 提交 2：子模块指针（ignore = all，必须 --force）
git add --force go_projects python_projects
git commit -m "chore: 更新 go_projects 与 python_projects 子模块指针"

git push
```

归档文件与指针拆开提交：回滚时可以只退指针不动文件（或反之），混提会失去这个自由度。

## 收尾验证与报告

验证三项：父仓库 `git status -sb`（只剩无关改动）、`git submodule status`（`+` 消失 = 指针对齐）、各子仓与远端同步。

ALWAYS 使用此报告结构向用户汇报：

```
| 仓库 | 提交 | 推送 |
|---|---|---|
| <子仓名> | <每个项目一次 + 根级文档 N 次> 共 N 次 | ✅/❌ |
| <子仓名> | ... | ... |
| 父仓库 | 归档文件 + 指针共 2 次 | ✅/❌ |
```

并附说明：清理了什么垃圾、未触碰哪些无关改动、README 是否需要同步。

## 提交信息格式

**示例 1：**
Input: 归档 go_projects 下项目 agent-reaper
Output: `agent-reaper:chore: 归档移除至父仓库 .archived`

**示例 2：**
Input: 移除子仓根级专属文档 STRUCTURE.md（随 sublime-folders 归档）
Output: `chore: 移除 sublime-folders 专属 STRUCTURE.md 随项目归档`

**示例 3：**
Input: 父仓库归档 go 与 python 共 7 个项目，随后更新两个子模块指针
Output: `chore: 归档 go 与 python 共 7 个停更项目` + `chore: 更新 go_projects 与 python_projects 子模块指针`

## 陷阱速查

| 陷阱 | 规避 |
|---|---|
| `git add` 拦截子模块指针 | `ignore = all` 所致，用 `git add --force <子模块名>` |
| 未跟踪项目被当被跟踪处理 | 先 `git ls-files` 确认；未跟踪则跳过子仓提交 |
| 无关脏改动混入提交 | 只 `git add -A <精确路径>`，提交前后 `git status --short` 核对 |
| 根级专属文档被遗忘 | 调研时 grep 子仓根级文件中项目名的出现 |
| 归档目录带垃圾入库 | 未跟踪项目入库前删 `__pycache__`/产物/缓存 |
| push 意外带出旧提交 | 属必然行为，计划阶段提前告知用户 |
| 相对路径验证误判 | `Test-Path` 用绝对路径或先确认 workdir |
