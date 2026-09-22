---
name: thirdparty-clone
description: 把第三方开源项目（GitHub 上别人的仓库）克隆进 language_projects 仓库做参考、学习或二次开发的完整工作流：.thirdparty/ 点前缀目录 + .gitignore 忽略 + 可选 remote 推自己 fork，默认不用 git submodule。当用户要求"克隆/拉取某个开源项目到仓库里看看"、"把 xxx 项目弄下来参考"、"clone 一个 GitHub 项目进来"、"fork 下来改改推自己仓库"、"参考项目应该放哪"，或纠结"第三方项目要不要挂成 submodule"时使用本指南——即使没说出 .thirdparty，只要意图是把外部仓库放进本仓都应触发。涵盖 submodule 与普通 clone 的选型判断、防止父仓误收嵌套 git 仓库、上游 push 安全性说明与自有 remote 配置。
---

# Skill: thirdparty-clone

# 第三方项目克隆（外部仓库 → 父仓库 .thirdparty/）

## 概述

本仓库（`language_projects`）五个语言子仓只收自己的项目，`.archived/` 只收自己的停更项目——第三方参考项目两者都不沾，统一放父仓根 `.thirdparty/<项目名>/` 点前缀目录，gitignore 掉，与父仓完全解耦。上游仓库天然推不动（无写权限），要推送就额外配一个指向自己 fork 的 remote。

## 触发与豁免

**触发**：克隆外部开源仓库进本仓，无论用途是纯阅读、跑起来试、还是改造后推自己仓库。

**豁免**（不走本流程）：
- 归档**自己的**停更项目 → 走 [GUIDE-ARCHIVE.md](GUIDE-ARCHIVE.md)；
- 往语言子仓新增**自己的**项目 → 直接在子仓建子目录，见 AGENTS.md「仓库结构说明」；
- 只需要读代码不需要本地仓库 → 不必 clone，直接看 GitHub 即可。

## 核心纪律

理解规则背后的原因，比死记步骤更重要：

1. **只放 `.thirdparty/` 点前缀目录**。本仓点前缀目录 = 基础设施层（`.archived`/`.scripts`/`.zed` 同层）；塞进语言子仓会污染子仓历史、违反"子仓只收自己项目"的约定，放进 `.archived/` 则语义错位（那是自己项目的坟墓，不是别人项目的展厅）。
2. **gitignore 一行是保险，不是可选项**。嵌套 git 仓库被 `git add` 会生成 gitlink（embedded repo）悬空指针，他人克隆父仓时无法解析；`.gitignore` 先行可杜绝误收事故。
3. **submodule 默认不用**。submodule 的价值是"父仓精确记住第三方停在哪个 commit + 多机 `--recurse-submodules` 恢复"，代价是内部每次提交都要更新父仓指针、还要遵守本仓 `.gitmodules` 约定（`branch` + `ignore = all`）。参考/学习场景零收益高成本；仅当用户明确要求"版本锁定/多机同步"才考虑。
4. **上游 origin 不用动，也不必担心误推**。push 需要写权限，clone 下来的仓库 origin 指向对方时 push 会被 GitHub 直接拒绝（403）。"我不会 push 到他的仓库"是天然成立的，无需任何处理。
5. **要推自己仓库就 `remote add`，保持推拉分离**。保留 origin 指向上游才能随时 `git pull` 同步更新；`myfork` 只承担推送。改掉 origin 反而丢掉免费的上游更新通道。

## 分阶段工作流

### 阶段 0：选型确认（只读）

对照三个问题，答案都在上文「核心纪律」里找依据：

1. 用途是什么？纯参考 / 改造后推自己仓库 → 走本流程；要父仓跟踪版本 → 再谈 submodule（默认劝退）。
2. 父仓 `.gitignore` 是否已有 `.thirdparty/` 规则？没有则阶段 1 一并追加。
3. 仓库大小与网络？超大仓库（含视频/大二进制）可 `--depth 1` 浅克隆；**但计划推自己 fork 并保留完整历史的必须完整克隆**（浅克隆推送历史不完整）。

选型对照表（向犹豫的用户展示）：

| | gitignore + 普通 clone（本流程） | submodule |
|---|---|---|
| 父仓是否跟踪 | 否，互不干扰 | 记录 commit 指针，内部每次提交都要更新父仓指针 |
| 多机/重新克隆 | 手动重新 clone | `--recurse-submodules` 可恢复 |
| 维护成本 | 零 | 指针提交 + `.gitmodules` 约定（branch + ignore=all） |

### 阶段 1：克隆 + 忽略

产物：`.thirdparty/<项目名>/` 本地仓库 + 生效的忽略规则。

```powershell
cd D:\Users\language_projects
git clone git@github.com:abi/screenshot-to-code.git .thirdparty/screenshot-to-code
```

- 本机 GitHub SSH 已配置好（sh-github-coexist 产物），SSH 克隆通常比 HTTPS 稳定；公开仓库用 HTTPS 也行。大仓库把 timeout 调到 10 分钟。
- 检查父仓 `.gitignore`：无 `.thirdparty/` 规则则追加（仿既有条目风格带中文注释）：

```gitignore
# 第三方参考项目克隆（点前缀基础设施层，不入库）
.thirdparty/
```

### 阶段 2（可选）：配置推送到自己仓库

前置：GitHub 上已 fork 或新建空仓库。

```powershell
cd .thirdparty/screenshot-to-code
git remote add myfork git@github.com:shihao-hub/screenshot-to-code.git
git push -u myfork main
```

- 同步上游更新：仍用 `git pull`（origin 未动）。
- 替代方案：`git remote set-url --push origin <fork-url>` 让 push 走 fork、pull 走上游；与 myfork 方案二选一，别两套混用。

### 收尾验证

```powershell
git check-ignore -v .thirdparty/<项目名>   # 命中 .gitignore 规则才算忽略生效
git status --short                          # 父仓输出中 .thirdparty 不应出现
```

父仓 `.gitignore` 若有改动，单独一次 chore 提交。

## 示例

**示例 1：**
Input: 克隆 abi/screenshot-to-code 进仓库做前端代码生成参考，不修改
Output: 完整克隆到 `.thirdparty/screenshot-to-code`，`.gitignore` 追加 `.thirdparty/`，remote 保持 origin 不动

**示例 2：**
Input: 克隆某项目，打算改造后推到自己仓库 shihao-hub/xxx
Output: 完整克隆 + gitignore + `git remote add myfork git@github.com:shihao-hub/xxx.git` + `git push -u myfork main`

**示例 3：**
Input: 用户问"要不要挂成 submodule 方便跟踪版本"
Output: 用阶段 0 对照表说明成本后默认劝退；仅当明确要多机同步版本指针时 `git submodule add`，并按仓库约定补 `branch` + `ignore = all` + 父仓指针提交

## 提交信息格式

**示例 1：**
Input: 父仓库 .gitignore 新增 .thirdparty/ 忽略规则
Output: `chore: 忽略第三方参考项目目录`

**示例 2：**
Input: 沉淀本指南到 docs/guides/
Output: `docs: 新增第三方项目克隆 GUIDE`

## 陷阱速查

| 陷阱 | 规避 |
|---|---|
| 嵌套仓库被 git add 成 gitlink 悬空指针 | `.gitignore` 规则先行；提交前 `git status --short` 核对 |
| 放错位置（`.archived/` 或语言子仓内） | `.archived` 只收自己的停更项目；子仓只收自己的项目 |
| 浅克隆后推 fork 丢历史 | 计划推送就完整克隆，或事后 `git fetch --unshallow` |
| 担心误推上游仓库 | 无写权限 push 直接被拒，origin 不用动 |
| 大仓库 clone 超时 | SSH 优先、timeout 放宽到 10 分钟、超大仓库 `--depth 1` |
| `check-ignore` 用相对路径误判 | 在父仓根目录执行，或用绝对路径 |
