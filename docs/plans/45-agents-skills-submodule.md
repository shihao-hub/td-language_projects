# 45 · `.agents/skills` 子模块化（td-agents-skills）并链接回 `~/.agents/skills`

## 背景

`C:\Users\29580\.agents` 整个目录消失，导致全机 **333 个 junction** 指向 `~/.agents/skills\...`
的链接全部断链（Claude Code / Codex / opencode / Gemini / Cursor / pi / zcode / Trae / Qoder /
iFlow / Kiro / Reasonix / CodeBuddy 以及本仓 `.cursor/skills`）。

**根因（2026-10-07 更正）**：不是"被某个 AI/软件删除"。用户于 2026-10-07 01:50 前后把
`~/.agents` **自行剪切**到了 `D:\Users\study_projects\older\.agents`（同时剪切的还有 5 个
`study-*` 项目），所以回收站无痕（移动语义）——原有的 skills 真身（一份 `td-agents-skills`
克隆，含两笔未推送的本地提交）**完好地留在该副本里**。

但"剪切真身"暴露了真正的结构性风险：**真身只存在于家目录/散落目录，搬移一次就让全机 333 个链接
集体失效，且无人知情**。因此确立长期策略：把重要资产以 **git submodule** 形式放在最重要的本仓
（`D:\Users\language_projects`），再用 junction 链接到各使用位置（家目录/各工具）。
本文是该策略的**第一步**。

## 目标与结果

| 项 | 结果 |
| --- | --- |
| 真身位置 | `D:\Users\language_projects\.agents\skills`（父仓子模块，远端 `shihao-hub/td-agents-skills@main`） |
| 使用位置 | `C:\Users\29580\.agents\skills` → **Junction** → 真身 |
| 恢复情况 | 333 个既有链接中 **109 个可用**；**224 个仍断**（28 个 `lark-*` 散装形态，见下节） |
| 子模块指针 | `f1bbaf9`（`main`，含 `book-stevens-ipc` 恢复提交），登记 `branch = main` + `ignore = all` |
| 技能内容 | 79 个技能目录 + `.archived`（含恢复回来的 `book-stevens-ipc`、`book-to-skill`） |

## 链接拓扑

```text
D:\Users\language_projects\.agents\skills        <- 子模块真身（td-agents-skills@main，79 个技能目录 + .archived）
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
   （更新写法见「残余风险与对策」末条）。`sync_skills.py` 等脚本以
   "脚本所在目录"为准绳，经 junction 访问与经 D: 访问等价（`Path(__file__).resolve()` 会还原真身）。

## 验证证据

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 子模块登记 | `git submodule status` | `.agents/skills f1bbaf9 (heads/main)` |
| 联接类型 | `Get-Item $env:USERPROFILE\.agents\skills` | `LinkType=Junction`，`Target=D:\Users\language_projects\.agents\skills` |
| 内容完整 | `(Get-ChildItem $env:USERPROFILE\.agents\skills -Directory).Count` | **81**（79 个技能目录 + `.archived`；含恢复回来的 `book-stevens-ipc`、`book-to-skill`） |
| 链路可读 | 抽查 `code-review` / `sh-web-archive` / `tdd` / `zread` / `book-stevens-ipc` / `book-to-skill` 的 `SKILL.md` | 经 `.claude`、`.codex`、`.config\opencode`、`.cursor`、`.pi`、`.gemini` 等全部可读 |
| 链接体检 | `uv run sync_skills.py --check`（skills 仓库自带同步器，只读 dry-run） | 源 **80 skills**；**86 SKIP（均已指向真身）、0 RELINK/REPLACE**；仅 1 项建议 REMOVE（`.codex\skills\.git`，本次不执行） |
| 全机复扫 | reparse point 全量复扫 | 333 个链接中 **109 健康 / 224 断层**（28 个目标名，全部是 `lark-*` 散装形态） |

逐工具明细（total / 仍断）：

| 工具 | total | 仍断 | 说明 |
| --- | --- | --- | --- |
| `.claude\skills` | 1 | 0 | 整目录 junction |
| `.codex\skills` | 81 | 0 | 整目录为真实目录，逐技能 junction；`book-stevens-ipc`、`book-to-bto-skill` 均已复活；另含 `.git`（语义特殊）、`.archived` |
| `.cursor\skills` | 1 | 0 | 整目录 junction |
| `.config\opencode\skills` | 1 | 0 | 整目录 junction |
| `.gemini\config\skills` | 1 | 0 | 整目录 junction |
| `.pi\agent\skills` | 29 | 28 | 仅 28 个 `lark-*` 散装残留（pi 原生读 `~/.agents/skills`，本目录非必需） |
| `.zcode` / `.trae` / `.kiro` / `.reasonix` / `.codebuddy` | 各 31 | 各 28 | 同 `.pi` |
| `.qoder` / `.iflow` | 各 32 | 各 28 | 同 `.pi` |
| 本仓 `.cursor\skills` | —— | —— | Junction（`.gitignore` 已排除），随链恢复 |

## 仍缺口项（29 项：28 个 `lark-*` + 1 个特殊项）

> 口径：全机复扫按"链接目标路径是否存在"判定，得 224 个断层 / 28 个缺失目标名（都是 `lark-*`）；
> 另有 `.codex\skills\.git` 一项，其目标是 gitdir **文件**（`Test-Path` 为真，故不计入扫描），
> 但语义上已不可用，合计 29 项。

1. **28 个 `lark-*` 根级散装目录**
   上游以**路由形态** `sh-lark-skills/<domain>/` 完整收录（28 个子目录均在库内，能力未丢），
   因此根级散装 junction 仍断是**预期现象**，与上游现行设计一致。
   如需真恢复根级散装：`lark-cli update` 重新释放后跑 `python sync_lark_skills.py`（收归路由）；
   或 `python sync_lark_skills.py --restore`（会把路由目录移回根目录，导致 skills 仓工作区变脏，不推荐）。
2. **`.codex\skills\.git`**
   指向 `~/.agents/skills\.git`；子模块化后该处是 **gitdir 指针文件**（不是目录），junction
   语义上无法恢复。对 Codex 无实际用途，属无害残留。

> 上述 224 个断层**刻意保留**，它们同时充当"缺口清单"证据；如要清理，
> `uv run sync_skills.py`（真实执行）会自动移除"源中不存在"的条目（保留 Codex 的 `.system`）。

## `older\.agents` 搬迁清单（2026-10-07 完成）

旧位置 `D:\Users\study_projects\older\.agents`（用户自行剪切的目的地）→ 新位置
`D:\Users\language_projects\.agents`（父仓）+ `~/.agents`（使用位置）：

| 内容 | 处置 | 状态 |
| --- | --- | --- |
| `skills\` 已跟踪内容（HEAD `f1bbaf9`） | 经 `git push` + 子模块 `merge --ff-only` 归位 | ✅ 已完成（含 `book-stevens-ipc`） |
| `skills\book-to-skill\` 本体（120 文件 / 1.82 MB，内嵌上游仓库 `c108d25`） | 复制到 `D:\Users\language_projects\.agents\skills\book-to-skill`，**排除 `.venv`**，保留 `.git`；在新子模块 gitdir 的 `info/exclude` 恢复 `/book-to-skill/`（维持"不入库"原设计） | ✅ 已完成（9 个工具链接复活） |
| `skills\book-to-skill\.venv`（约 356.7 MB） | **按用户要求不搬**；重建方式：`uv venv`/`python -m venv` + 装依赖（上游 `pyproject.toml` 在），或重新执行 `book-to-skill-setup.md` 的安装步骤 | ⏸ 留在旧位置（可删） |
| `skills` 根 3 个散落未跟踪文件 `_child.md`、`test_xml.py`、`update_subdoc.py` | 复制到新真身根，保持未跟踪（内容分别为 AutoHotkey 指南、飞书文档 HTML 处理脚本 ×2） | ✅ 已复制，去留待定 |
| `skills\**\__pycache__` | 字节码缓存，不搬 | ⏭ 跳过 |
| `.skill-lock.json`（31 KB，**技能安装台账**：37 项，含来源 URL）+ `.skill-lock.json.bak-before-booktoskill-removal`（18 KB） | 复制回 `~/.agents\`（原位，供安装器读写）+ 在父仓 `.agents\` 存一份入库快照（防丢、可 diff） | ✅ 已完成 |
| `.gitignore`（198 B，旧 `~/.agents` 的 OS/编辑器忽略清单） | 复制回 `~/.agents\`；**不入父仓**（避免父仓 `.agents/.gitignore` 反向影响父仓忽略规则） | ✅ 已完成 |

### 台账核对发现

- 台账 37 项中：28 个 `lark-*` 已在 `sh-lark-skills/` 路由形态内（能力未丢）；
  **`huashu-md-to-pdf`（来源 `https://github.com/alchaincyf/huashu-skills.git`）全盘找不到，是真正的缺口**
  （无任何工具链接它）——可一条命令重装，或确认不需要后从台账移除。
- 反向：当前库有 79 个技能目录，其中 51 个（`sh-*` 自研、`book-*` 书籍库等）不在该台账内
  —— 说明台账只覆盖"通过安装器装的第三方技能"，自研技能是直接写文件 + git 提交的。

### 配套文档回收命令（`book-to-skill-setup.md`，尚未执行）

```powershell
$t = "$env:TEMP\rec"; git init --bare $t
git -C $t fetch git@github.com:shihao-hub/td-agents-skills.git f8e96258721db2b0b3ede5381b3ca857652a44ae
git -C $t show f8e9625:book-to-skill-setup.md   # 97 行：安装方式、取舍、换机重建步骤
```

## `book-stevens-ipc` 恢复记录（2026-10-07，已完成）

- 线索来源：DSH 会话存档（`~/.dsh/storages/session_projcache/sessions/*.json`）里的自述文本
  提到本地提交 `f1bbaf9`；GitHub 按 SHA 查得 `f8e9625` 存在、`f1bbaf9` 不在。
- 定位到旧副本 `D:\Users\study_projects\older\.agents\skills`（同一远端仓库的克隆，
  `main` HEAD=`f1bbaf9`，其父恰为远端当时的 `df6a589`，即"只多一笔未推送提交"）。
- 恢复动作（两步，均已完成）：
  ```powershell
  git -C "D:\Users\study_projects\older\.agents\skills" push origin main   # df6a589 -> f1bbaf9
  git -C "D:\Users\language_projects\.agents\skills" fetch origin main
  git -C "D:\Users\language_projects\.agents\skills" merge --ff-only origin/main
  ```
- 结果：远端 `main` = `f1bbaf9`；子模块同步；22 个文件 / 2263 行回归；`.codex\skills\book-stevens-ipc`
  断链复活（断链 234 → 233）。
- 教训：**搬移真身必须同步链接**。本次事故的真实成因是"剪切 `.agents` 到
  `D:\Users\study_projects\older`"（2026-10-07 01:50 前后，同时搬走 5 个 `study-*` 项目），而非
  某个 AI/软件乱删；回收站无痕正是移动语义。


## 残余风险与对策

- **真身被再次搬移/误删**：链接会再断，但**数据不再丢**（真身在 D: 仓内）。重建只需一条命令：
  ```powershell
  cmd /c mklink /J "C:\Users\29580\.agents\skills" "D:\Users\language_projects\.agents\skills"
  ```
- **某工具把 `~/.agents/skills` 删掉后重建为真实目录**：链接被顶掉，表现为"改动看似生效但没写进仓库"。
  用 `Get-Item $env:USERPROFILE\.agents\skills` 看 `LinkType` 即可判别，重建命令同上。
- **搬移真身必须同步链接（本次事故教训）**：任何 `~/.agents\skills` 的移动/改名都要同步重建 junction，
  否则全机 333 个链接静默失效；搬移前先 `Get-Item` 确认 `LinkType`，搬移后立即重建并抽查。
- **`~/.agents` 下的 hooks / rules**：本仓 `.agents/hooks`、`.agents/rules` 目前仅占位（`.gitkeep`），
  旧副本 `older\.agents` 中也没有这两个目录（只有 `skills`、`.gitignore`、`.skill-lock.json`），
  且未发现任何工具引用，本次不涉及。
- **不影响父仓工作区**：`.agents/skills` 登记 `ignore = all`；父仓 `git status` 只显示子模块指针。
  注意：`ignore = all` 会让父仓 `git status/diff` 看不见指针变化，更新指针时用
  `git -c submodule..agents/skills.ignore=none ...` 或低层 `git update-index` 显式操作，**不要**用
  `git add --force .agents/skills`（索引里没有 gitlink 时会把子模块内容当普通文件加入）。

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

1. **`huashu-md-to-pdf`**（台账记录、磁盘已无）：按来源重装
   ```powershell
   # 来源：https://github.com/alchaincyf/huashu-skills.git（skillPath: huashu-md-to-pdf/SKILL.md）
   ```
   或确认不需要后从台账 `.skill-lock.json` 移除。
2. `book-to-skill-setup.md`：可从 GitHub 不可达对象 `f8e9625` 取回后入子模块，作为换机重建手册
   （命令见「配套文档回收命令」节）。
3. `book-to-skill/.venv`（约 356.7 MB）按用户要求未搬迁，仍留在
   `D:\Users\study_projects\older\.agents\skills\book-to-skill\.venv`；确认不需要后即可删除，
   需要时按上游 `pyproject.toml` 重建。注意 User 级环境变量 `PYTHON_BIN` 若仍指向旧路径需更新。
4. **3 个散落文件去留**：新真身根的 `_child.md`（AutoHotkey 指南）、`test_xml.py`、`update_subdoc.py`
   （飞书文档 HTML 处理脚本），目前是未跟踪状态，会让子模块 `git status` 一直脏——建议归档或删除。
5. 清理 224 个 `lark-*` 散装断层（`uv run sync_skills.py`，或手工删各工具的 28 个 lark junction）。
6. `~/.agents/hooks`、`~/.agents/rules` 的资产化与链接（旧副本里也没有这两个目录）。
7. **旧副本区治理**：`D:\Users\study_projects\older`（本次剪切目的地）还收着 5 个 `study-*` 项目，
   且同样只在本机；建议按"真身入仓 + 链接"策略逐项处理，避免下次搬移再次造成大面积静默断链。
8. 把"本仓子模块 + 家目录 junction"固化为可复用流程/脚本（本次只做 skills 一例，避免过早抽象）。
