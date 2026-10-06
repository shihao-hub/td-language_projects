# 45 · `.agents/skills` 子模块化（td-agents-skills）并链接回 `~/.agents/skills`

## 背景

`C:\Users\29580\.agents` 整个目录被某未知工具/AI **永久删除**（回收站无痕迹），导致全机
**333 个 junction** 指向 `~/.agents/skills\...` 的链接全部断链（Claude Code / Codex / opencode /
Gemini / Cursor / pi / zcode / Trae / Qoder / iFlow / Kiro / Reasonix / CodeBuddy 以及本仓
`.cursor/skills`）。

根因不是"链接坏了"，而是**真身只存在于用户主目录**——主目录被清即资产全失。因此确立长期策略：
把重要资产以 **git submodule** 形式放在最重要的本仓（`D:\Users\language_projects`），再用 junction
链接到各使用位置（家目录/各工具）。本文是该策略的**第一步**。

## 目标与结果

| 项 | 结果 |
| --- | --- |
| 真身位置 | `D:\Users\language_projects\.agents\skills`（父仓子模块，远端 `shihao-hub/td-agents-skills@main`） |
| 使用位置 | `C:\Users\29580\.agents\skills` → **Junction** → 真身 |
| 恢复情况 | 333 个既有链接中 **99 个恢复可用**；**234 个仍断**，涉及 **31 个不同目标名**（见下节） |
| 子模块指针 | `df6a589`（`main`），登记 `branch = main` + `ignore = all` |

## 链接拓扑

```text
D:\Users\language_projects\.agents\skills        <- 子模块真身（td-agents-skills@main，78 个顶层目录）
        ^
        |  Junction
C:\Users\29580\.agents\skills                    <- 统一入口（历史文档/工具均引用此路径，保持不变）
        ^
        |  既有 333 个 junction 继续指向上游的 C:\Users\29580\.agents\skills\<name>
   .claude\skills / .codex\skills\<skill> / .cursor\skills / .config\opencode\skills /
   .gemini\config\skills / .pi\agent\skills\<skill> / .zcode / .trae / .qoder /
   .iflow / .kiro / .reasonix / .codebuddy / 本仓 .cursor\skills
```

- 采用 **目录联接（`mklink /J`）而非符号链接**：当前账号无 `SeCreateSymbolicLinkPrivilege`
  （非管理员、未开开发者模式），符号链接必然失败；junction 无权限门槛，且既有链接本身就是 junction。
- 既有下游链接**不做修改**：它们经 `~/.agents/skills` 这一跳自动解析到真身，全部保留原写法，
  历史文档里 `C:\Users\29580\.agents\skills\...` 的引用继续有效。

## 实施步骤（本次）

1. `git rm .agents/skills/.gitkeep`（清掉占位文件，原占位仅用于保持空目录）。
2. `git submodule add -b main git@github.com:shihao-hub/td-agents-skills.git .agents/skills`
   （URL 用 SSH，与其它子模块一致；SSH 访问已验证可用）。
3. `.gitmodules` 新条目补 `ignore = all`，与既有五个子模块保持一致。
4. 建链接：
   ```powershell
   New-Item -ItemType Directory -Force -Path "C:\Users\29580\.agents" | Out-Null
   cmd /c mklink /J "C:\Users\29580\.agents\skills" "D:\Users\language_projects\.agents\skills"
   ```
5. 同步意识：子模块化后，目录真身变更需**在子模块内**提交推送；父仓只跟踪指针
   （`git add --force .agents/skills` → commit → push）。`sync_skills.py` 等脚本以
   "脚本所在目录"为准绳，经 junction 访问与经 D: 访问等价（`Path(__file__).resolve()` 会还原真身）。

## 验证证据

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 子模块登记 | `git submodule status` | `.agents/skills df6a589 (heads/main)` |
| 联接类型 | `Get-Item $env:USERPROFILE\.agents\skills` | `LinkType=Junction`，`Target=D:\Users\language_projects\.agents\skills` |
| 内容完整 | `(Get-ChildItem $env:USERPROFILE\.agents\skills -Directory).Count` | **78**（77 个技能目录 + `.archived`） |
| 链路可读 | 抽查 `code-review` / `sh-web-archive` / `tdd` / `zread` 的 `SKILL.md` | 经 `.claude`、`.codex`、`.config\opencode`、`.cursor`、`.pi` 全部可读 |
| 链接体检 | `uv run sync_skills.py --check`（skills 仓库自带同步器，只读 dry-run） | 源 78 skills；**84 SKIP（均已指向真身）、0 RELINK/REPLACE**；仅 3 项建议 REMOVE（本次不执行） |
| 理论校验 | 全机 reparse point 复扫 | 333 个链接中 99 健康 / 234 目标缺失（31 个目标名） |

逐工具明细（total / 仍断）：

| 工具 | total | 仍断 | 说明 |
| --- | --- | --- | --- |
| `.claude\skills` | 1 | 0 | 整目录 junction |
| `.codex\skills` | 81 | 2 | 整目录为真实目录，逐技能 junction；另含 `.git`、`.archived` |
| `.cursor\skills` | 1 | 0 | 整目录 junction |
| `.config\opencode\skills` | 1 | 0 | 整目录 junction |
| `.gemini\config\skills` | 1 | 0 | 整目录 junction |
| `.pi\agent\skills` | 29 | 29 | pi 原生读取 `~/.agents/skills`，此处仅历史逐技能残留 |
| `.zcode` / `.trae` / `.kiro` / `.reasonix` / `.codebuddy` | 各 31 | 各 29 | |
| `.qoder` / `.iflow` | 各 32 | 各 29 | |
| 本仓 `.cursor\skills` | —— | —— | Junction（`.gitignore` 已排除），随链恢复 |

## 仍缺失的 31 个目标名

1. **`book-to-skill`、`book-stevens-ipc`（不可由远端补回）**
   两者只存在于被删克隆的**本地提交**（历史会话记录 commit `f1bbaf9` / `f8e9625`），未推到
   `td-agents-skills@main`，回收站亦无痕迹 → 永久丢失。恢复途径：
   - `book-to-skill`：项目本身来自 GitHub，可重新安装（`C:\Users\29580\.venvs\book-to-skill` 仍存在）；
   - `book-stevens-ipc`：按 `sh-book2skill-sop` 重跑 OCR + 章节摘要重新生成（耗时）。
2. **28 个 `lark-*` 根级散装目录**
   上游以**路由形态** `sh-lark-skills/<domain>/` 完整收录（28 个子目录均在库内，能力未丢），
   因此根级散装 junction 仍断是**预期现象**，与上游现行设计一致。
   如需真恢复根级散装：`lark-cli update` 重新释放后跑 `python sync_lark_skills.py`（收归路由）；
   或 `python sync_lark_skills.py --restore`（会把路由目录移回根目录，导致 skills 仓工作区变脏，不推荐）。
3. **`.codex\skills\.git`**
   指向 `~/.agents/skills\.git`；子模块化后该处是 **gitdir 指针文件**（不是目录），junction
   语义上无法恢复。对 Codex 无实际用途，属无害残留。

> 上述 234 个断链**本次刻意保留**，它们同时充当"缺失清单"证据；如要清理，
> `uv run sync_skills.py`（真实执行）会自动移除"源中不存在"的条目（保留 Codex 的 `.system`）。

## 残余风险与对策

- **主目录再次被删**：链接会再断，但**数据不再丢**（真身在 D: 仓内）。重建只需一条命令：
  ```powershell
  cmd /c mklink /J "C:\Users\29580\.agents\skills" "D:\Users\language_projects\.agents\skills"
  ```
- **某工具把 `~/.agents/skills` 删掉后重建为真实目录**：链接被顶掉，表现为"改动看似生效但没写进仓库"。
  用 `Get-Item $env:USERPROFILE\.agents\skills` 看 `LinkType` 即可判别，重建命令同上。
- **`~/.agents` 下的 hooks / rules**：本仓 `.agents/hooks`、`.agents/rules` 目前仅占位（`.gitkeep`），
  且未发现任何工具引用，本次不涉及。
- **不影响父仓工作区**：`.agents/skills` 登记 `ignore = all`；父仓 `git status` 只显示子模块指针。

## 回滚

```powershell
cmd /c rmdir "C:\Users\29580\.agents\skills"                  # 只解除链接，不动真身
cd D:\Users\language_projects
git submodule deinit -f .agents/skills
git rm -f .agents/skills
Remove-Item -Recurse -Force .git\modules\.agents\skills
git checkout -- .gitmodules
New-Item -ItemType File -Force -Path .agents\skills\.gitkeep   # 还原占位
```

## 后续可选（未做）

1. 重建 `book-to-skill`、`book-stevens-ipc`。
2. 清理 234 个已知断链（`uv run sync_skills.py`，或手工删 `.codex\skills\.git` 与各 lark 散装项）。
3. `~/.agents/hooks`、`~/.agents/rules` 的资产化与链接。
4. 把"本仓子模块 + 家目录 junction"固化为可复用流程/脚本（本次只做 skills 一例，避免过早抽象）。
