# 跨 Agent 会话交接调研：把当前会话交给"另一个 agent"

> 调研日期：2026-09-23
> 调研对象：pi 0.87.0、Claude Code、opencode、Agent Client Protocol (ACP) v1、Zed
> 实证环境：Windows 11、Zed + `pi-acp`
> **前提（关键）**：接收方是**另一个 agent**（例如 pi → Claude Code，或 Zed 里的 antigravity → opencode）。
> 不是"同一个 agent 换一个会话窗口"——那种情况下本文档的结论完全不同（见 §2）。

---

## 1. 结论速览

前提一旦是"换 agent"，原生的续接与分叉就**全部失效**：每个 agent 的会话存储都是自己私有的，
`--continue` / `--resume` / `/fork` / `/clone` / `/branch` / ACP `session/load` 都是"让**这个** agent
回到**它自己**的会话"，没有一个能跨 agent 生效。

所以跨 agent 交接实际只剩两条路，外加一个实用变体：

| | **路线一：整份转录搬过去** | **路线二：先总结成简报** | **变体：简报 + 关键原始片段** |
|---|---|---|---|
| 信息保真 | 全量，但夹带噪声 | 有损，取决于提问质量 | 有损主干 + 无损关键点 |
| 通常体积 | 极大（几十 KB ~ 数 MB） | 小（1~5 KB） | 中 |
| 谁做提炼 | 接收方（读得慢、重点靠猜） | **发送方**（手上有完整上下文） | 发送方 |
| 需要预处理 | **需要**（JSONL → 可读文本） | 不需要（本身就是文本） | 少量 |
| 跨 agent 可靠性 | 中（格式私有、工具语义会丢） | 高（纯 Markdown） | 高 |
| 成本 | 高，常常直接触发接收方 auto-compact | 低 | 中 |
| 适合 | 仅限审计/复盘/含非文本资产 | 日常交接（默认） | 路线二的配件 |
| **本档定位** | ❌ 降级方案，跨 agent 场景基本不该用 | ✅ **主干，每次都做** | ⚙️ 不是第三条路线，见 §5 |

**一句话结论**：**只做路线二**。由**发送方 agent**做总结（它还没丢上下文），产出 Markdown 简报。
第三列不是另外一条路，而是路线二内部一个可选的 `## 原始片段` 段落（见 §5）。
路线一仅在审计/复盘或含非文本资产时降级使用，日常交接不要用——它的产物是私有格式且体积巨大，
拿不到手也没法粘。

具体到可执行命令，两条路都能用同一招实现——**用非交互模式驱动旧会话，让它把内容重新组织成你要的格式**：

```powershell
# pi（--session 指定旧会话，-p 非交互）
pi --session 01a0cdc1 -p "把本次会话整理成交接简报，写入 .pi/handoff.md" > $null

# Claude Code（官方文档给出的脚本接口）
claude -p --resume <session-id> --output-format json "summarize what we changed" | jq -r '.result'

# opencode
opencode run --session <session-id> "把本次会话整理成交接简报，写入 .pi/handoff.md"
```

这三条**都用不着解析任何 JSONL**，也就绕开了"格式是各 agent 内部实现"这个最大的坑。

---

## 2. 为什么跨 agent 时"原生续接"这条捷径不存在

先排除掉所有看起来能用、实则在跨 agent 场景下无效的机制，避免被误导：

| 机制 | 实际语义 | 为什么跨 agent 无效 |
|---|---|---|
| pi `--fork` / `/clone` / `/tree` | 复制 **pi 自己的** JSONL 树 | 产物仍是 pi 的会话文件，别的 agent 读不懂 |
| Claude Code `--fork-session` / `/branch` | 复制 **Claude 自己的**转录 | 同上 |
| opencode `--fork` | 复制 **opencode 自己的**会话 | 同上 |
| ACP `session/load`（重放）/ `session/resume` | 让**同一个 Agent Server** 重放/恢复它自己的会话 | 是"换客户端接管同一 agent"，不是"换 agent" |
| ACP `session/list` | 列出该 Agent 自己的会话 | 同上 |

各 agent 的会话存储是**互不相通的私有实现**：

- pi：`~/.pi/agent/sessions/--<cwd 转换后>--/<ts>_<id>.jsonl`（树结构，`id`/`parentId`）
- Claude Code：`~/.claude/projects/<project>/<session-id>.jsonl`
- opencode：自身存储，需经 `opencode export` 才拿到 JSON
- Zed：本地 SQLite `sidebar_threads` 只存**元数据**（`thread_id` / `agent_id` / `session_id` / `folder_paths`），正文在各 agent 自己那

**因此跨 agent 的交接物只能是"文本"。** 这也解释了为什么本文档的落点是"怎么产出好文本"，而不是"用哪个命令接管会话"。

---

## 3. 路线一：整份转录搬过去

### 3.1 各 agent 怎么取原文

| agent | 结构化原文 | 人类可读导出 |
|---|---|---|
| pi | `%PI_SESSION_FILE%`（当前会话绝对路径）；或 `~/.pi/agent/sessions/...` | `pi --export out.html` |
| Claude Code | `~/.claude/projects/<project>/<session-id>.jsonl` | `/export`（可复制到剪贴板或存纯文本） |
| opencode | `opencode export [sessionID]` → JSON | 同上 |
| Zed 面板里的其他 agent | 需回到该 agent 自己的存储 | — |

### 3.2 为什么不建议把 JSONL 原样贴过去

1. **格式是内部实现，会变**。Claude Code 官方原文：该 JSONL "is internal to Claude Code and changes
   between versions, so scripts that parse these files directly can break on any release"。
   → 自己写解析器迟早会坏，**正确做法是让发送方 agent 自己导出**（§3.3）。
2. **噪声多**：system prompt 分片、工具声明、thinking、扩展自定义条目都在里面，接收方要花大量 token 穿过这些。
3. **可能已被截断**：pi 在序列化会话做摘要时会把 tool 结果截断到 2000 字符——也就是说**原文里就有失真**，
   不能假设"整份复制 = 无损"。
4. **会压垮接收方**：体积动辄数百 KB，接收方要么直接爆窗口，要么立刻触发 auto-compact
   （pi 的阈值是 `contextTokens > contextWindow - reserveTokens`，默认 `reserveTokens = 16384`），
   结果就是"你没交接，它自己先压了一遍，而且压得更差"。
5. **工具调用语义丢失**：不同 agent 的工具名、参数 schema 不同，转录里的 `toolCall` 对方无法重放。

### 3.3 推荐的"复制"姿态：让发送方按需导出可读文本

不要复制文件，而是**驱动旧会话重新输出**。三条命令见 §1，本质都是：旧会话仍有完整上下文，
让它在非交互模式下把内容重组为 Markdown 并落盘。

优势：

- 保真度接近原文（它读的是自己的完整历史），但输出是你指定的可读格式；
- 可以按目标 agent 定制（比如"输出成 Claude Code 习惯的 markdown 清单"）；
- 不依赖任何私有 JSONL schema，**不会随版本失效**。

Claude Code 的官方文档把这条路径写得很明确：

```bash theme={null}
claude -p --resume <session-id> --output-format json "summarize what we changed" | jq -r '.result'
```

### 3.4 什么时候真的需要整份搬

- 会话里有大量**非文本资产**（图片、二进制、外部链接的抓取结果）；
- 需要精确到标点地传递**代码 diff / 报错堆栈 / 日志**；
- 交接后要**审计**这段历史（合规、复盘），而不只是继续干活。

即便这些场景，也建议先做 §3.3 的导出，而不是直接给 JSONL。

---

## 4. 路线二：交接简报（推荐默认）

### 4.1 谁做总结，这一点决定了质量上限

| 谁总结 | 结果 |
|---|---|
| **发送方**（旧 agent） | ✅ 手上有完整上下文、知道哪些决策是反复权衡过的 → 重点抓得准 |
| 接收方（新 agent） | ❌ 只能读到你给的文本；若给的是全量转录，它还得花一次昂贵的阅读 + 自己压一遍，重点是猜的 |

**结论：总结必须由发送方完成。** 这也是 §1 那三条命令存在的理由——它们是"让旧会话自己写交接简报"的入口。

### 4.2 简报模板（可直接照抄）

这份骨架来自 pi 的 compaction / branch-summarization 结构化格式（两个机制共用同一模板），
它在实际使用中已经被验证够用：

```markdown
## Goal
[这次要达成什么]

## Constraints & Preferences
- [用户明确提出的约束、偏好、不可动的边界]

## Progress
### Done
- [x] ...
### In Progress
- [ ] ...（说明卡在哪一步）
### Blocked
- [阻塞点，以及已经排除过的方案]

## Key Decisions
- **[决策]**：[理由]（尤其是"试过 X 不行才选 Y"这类信息，新 agent 无法从代码里推出）

## Next Steps
1. [接下来该做什么，按优先级]

## Critical Context
- [继续干活必需的数据：路径、ID、命令、环境前提]

## 原始片段（可选，见 §5）
- [diff / 报错原文 / 接口签名]

<read-files>
绝对或仓库相对路径，每行一个
</read-files>
<modified-files>
绝对或仓库相对路径，每行一个
</modified-files>
```

注意最后两个块不是装饰：**给路径 = 让新 agent 自己重读文件**，这比把文件内容复制进简报便宜得多，
也不会有内容过期问题（新 agent 读到的是磁盘上最新的版本）。

### 4.3 怎么交给新 agent

| 方式 | 命令/操作 | 说明 |
|---|---|---|
| 文件引用（首选） | pi：`pi "@.pi/handoff.md 按这份简报继续"`；Claude Code：`@.pi/handoff.md` | 简报留在仓库里，可追溯、可 diff |
| 追加进 system prompt | `pi --append-system-prompt .pi/handoff.md` | 适合"开场就必须知道"的内容 |
| 直接粘贴 | 任何 agent | 最短路径，但简报不进仓库，事后无法查 |
| 不提简报、只提路径 | "先读 `docs/plans/14-xxx.md`，再继续" | 适合简报本身已落盘且新 agent 有文件工具时 |

**落盘位置优先选仓库内既有的交接产物目录**：`docs/plans/<NN>-<topic>.md`（父仓级计划）、
`docs/specs/<NN>-<feature>/`（需求/设计/任务）、`docs/repo/`（技术调研）。临时性的可放 `.pi/handoff.md`
（注意按仓库约定，`.pi/` 属项目本地配置，不宜提交）。

### 4.4 简报自检清单

交给新 agent 前，用新 agent 的视角反问：

- [ ] 只看这份简报，我能说清"为什么做这件事"吗？（不能 → `Goal` + `Key Decisions` 不够）
- [ ] 我知道现在卡在哪一步、下一步动哪个文件吗？（不能 → `Progress` + `Next Steps` 不够）
- [ ] 简报里出现的每个文件路径，我能自己打开吗？（不能 → 缺 `<read-files>`/`<modified-files>`）
- [ ] 有没有"试过不行"的方案没写？（这是最高频的返工来源）
- [ ] 有没有环境前提（分支、依赖、服务、凭据位置）没写？

---

## 5. 路线二的配件：关键原始片段（不是第三条路线）

本节不是独立方案，而是 §4.2 模板里那个可选段落 `## 原始片段` 的填写规则。
主干骨架始终是 §4.2，不要因为本节而改变主流程。

纯摘要会丢精确事实，但把整份转录搬过来又太贵。所以规则是：
**摘要负责"为什么、到哪了"，原始片段只负责"必须逐字精确的东西"**。

**只有在以下三种情况下才贴原文**（其余一律只写路径）：

1. 未提交的 `git diff`；
2. 报错堆栈 / 失败测试输出（贴原文，不要转述）；
3. 接口签名、SQL、正则、配置片段——差一个字符就错的内容。

其余事实如果在仓库里（改动、日志、配置），**只写路径**：新 agent 有工具能自己读，
而且读到的必然是最新版，还省 token。

---

## 6. 比交接更划算的一层：开新 agent 时的"预置"

以下机制**不需要任何交接动作**，新 agent 一启动就生效。它们解决的是"认识这个仓库"，
不解决"这次任务做到哪了"（后者仍需 §4 的简报）。

| 机制 | 位置 | 效果 |
|---|---|---|
| `AGENTS.md` / `CLAUDE.md` | pi：`~/.pi/agent/AGENTS.md` + 项目各级目录；Claude Code：支持两者并用 | 项目约定、命令、安全规则自动注入 |
| 本仓现状（实证） | 根 `CLAUDE.md` 仅一行 `@AGENTS.md` | **pi 与 Claude Code 共享同一份 `AGENTS.md`**，写一次两个 agent 都吃到 |
| AOCI 认知层 | `aoci.txt`（卷清单）+ `aoci.meta.txt`、`aoci.code.txt`（约 49 KB） | 为每个受管对象记录职责/关系/契约/约束，新 agent 可快速建立系统级理解 |
| Claude Code auto memory | `~/.claude/projects/<project>/memory/MEMORY.md` + 主题文件 | `MEMORY.md` 前 200 行/25KB 每次会话自动加载；`type` 分 user/feedback/project/reference |
| 交接产物目录 | `docs/plans/`、`docs/specs/` | 收尾写文档 = 为下一个会话预置上下文 |

口诀：**`AGENTS.md` 是规矩，AOCI 是地图，`docs/plans`/`docs/specs` 是当前战役。**

---

## 7. 落地形态：文件放哪、怎么粘（定型）

### 7.0 场景总览

| 场景 | 做法 |
|---|---|
| **默认（日常交接）** | **路线二**：发送方写交接简报文件 → 把**绝对路径**粘给新 agent |
| 有 diff / 报错原文 / 接口签名要精确传 | 在简报内补 `## 原始片段`（§5，只限三类内容） |
| 新 agent 无文件系统（网页版） | 改为让旧会话直接吐正文，粘贴 |
| 审计/复盘、含非文本资产 | 降级用路线一：先让发送方**导出为 Markdown**，绝不手抄 JSONL |
| 收尾 | 值得长期保留的结论**提升**到 `docs/plans`/`docs/specs`；维护 AOCI |

### 7.1 文件位置：放 `%APPDATA%`，不要放仓库、也不要放临时目录

交接简报是**传输介质**，不是项目文档。三个理由：

1. **放仓库会污染工作区**：出现在 `git status` 里；monorepo + submodule 结构下更容易误提交，而 AGENTS.md 明确禁止跨范围混提。
2. **放 `%TEMP%` 有丢失风险**：临时目录会被系统清理，交接正在进行时文件消失就很麻烦。
3. **本仓已有"出仓库但受管"的现成根目录**：`%APPDATA%\language_projects\<项目名>\`（AGENTS.md 强约束）。本机实证该目录已存在，下有 20 个子项目目录（`clictl`、`taskmon`、`liteconf` …），目前尚无 `handoff` 子目录。

推荐路径：

```text
%APPDATA%\language_projects\<项目名>\handoff\<YYYYMMDD>-<HHmm>-<主题slug>.md
# 本机展开：C:\Users\29580\AppData\Roaming\language_projects\<项目名>\handoff\20260923-1830-xxx.md
```

`<项目名>` 取**你实际在改的那个项目**（子仓内的子项目，如 `taskmon`）。
父仓级/跨项目的工作（例如本文件这次调研），用 `language_projects` 作为 `<项目名>`。

> 备注：AGENTS.md 那条约束列举的是"运行时状态文件"（JSON 数据库、SQLite db、缓存、锁、日志、会话存储、settings），
> 交接简报严格说不在列举范围内。若想让仓库规则更干净，可新增一个跨项目伪目录 `_handoff` 并在 AGENTS.md 补一句授权；
> **默认先按上面的 `<项目名>` 方案走，不额外发明约定。**

### 7.2 在旧会话里发的指令（让它自己写文件并回路径）

```text
生成一份交接简报，供另一个 AI agent 接手本任务。

1. 先创建目录（若不存在）：
   C:\Users\29580\AppData\Roaming\language_projects\<项目名>\handoff\
2. 写入文件（绝对路径）：
   ...\<YYYYMMDD>-<HHmm>-<主题slug>.md

正文严格用以下结构（Markdown，不要寒暄、不要前后废话）：
## Goal
## Constraints & Preferences
## Progress（Done / In Progress / Blocked）
## Key Decisions（决策 + 理由，必须包含"试过但不行的方案"）
## Next Steps
## Critical Context
## Referenced Files（绝对路径，每行一个，标注 read / modified）

要求：
- 自包含：新 agent 不需要读本次会话历史即可继续
- 不要复述已被压缩过的原始对话
- 优先给文件路径，不要粘贴文件内容；只有 diff / 报错原文 / 接口签名这类"必须精确"的内容才贴原文
- 全文控制在 150 行以内
- 完成后单独输出一行，便于我直接复制：
  HANDOFF: <绝对路径>
```

若 `pi -p` / `claude -p --resume` 在非交互模式下**工具写入被拦**，让它改为直接输出正文（不写文件），你自己落盘即可——不要为了写文件去放宽权限。

### 7.3 粘给新 agent 的话

你原来的写法可用，建议做两处微调：把"任务"放最后（模型对末尾内容注意力更强），并补一句读取约束（否则新 agent 常会反问一堆上下文中已有的信息）。

```text
请参考下面的上下文继续思考。

【上下文】
<粘贴简报正文，或写：绝对路径 C:\Users\29580\AppData\Roaming\language_projects\<项目名>\handoff\20260923-1830-xxx.md>

【要解决的问题】
<你的问题>

要求：若上面给的是路径，先完整读取该文件再回答；不要重复询问上下文中已有的信息；
路径无法访问时直接告诉我，不要自行猜测内容。
```

三条要点：

- **路径必须写绝对路径**。新 agent 的 cwd 与你不同，相对路径必然找不到。
- 新 agent 是网页版/无文件系统时，只能用"粘贴正文"这一分支。
- CLI agent 读外部绝对路径时可能弹一次文件读取授权，属正常。

### 7.4 生命周期

| 阶段 | 动作 |
|---|---|
| 生成 | 旧会话写文件，并输出 `HANDOFF: <绝对路径>` 供复制 |
| 使用 | 把该绝对路径（或正文）粘给新 agent |
| 收尾 | 结论值得长期保留就**提升**为 `docs/plans/<NN>-<topic>.md`；不需要就留在 APPDATA |
| 清理 | `handoff/` 目录可整体删除，不影响任何仓库内容与 git 状态 |

关键区分：**APPDATA 里的是一次性传输件，`docs/plans/` 里的是项目资产。**

---

## 8. 坑与反模式

1. **手写 JSONL 解析器**。Claude Code 官方明确警告该格式跨版本会变；同理适用于任何 agent。
   → 让发送方 agent 自己导出，别碰 schema。
2. **把整份 JSONL / HTML 导出贴给新 agent**。`/export`、`pi --export` 的产物是**给人看的**，
   不是给模型看的。
3. **指望接收方自己总结**。既贵又准不了；总结必须由还有上下文的发送方做。
4. **忘记转录本身可能已被截断**。pi 在摘要序列化时把 tool 结果截到 2000 字符，
   所以"整份复制 = 无损"这个前提本身不成立。
5. **简报只写"改了什么"不写路径**。新 agent 无法重读文件，只能凭描述猜。
6. **无视 prompt cache**。跨 agent 必然换模型/换 provider，缓存 100% 重算，
   所以精简的简报比全量转录**同时省钱又提速**——这是路线二在成本上的第二个理由。
7. **以为跨 agent 可以无损**。除"整份原文 + 接收方能解析私有格式"（基本不现实）外，
   任何跨 agent 交接都是有损的；能做的是把损失控制在"不影响继续干活"的范围内。
8. **把"同 agent 换会话"的经验直接套过来**。`/clone`、`--fork`、`session/load` 在这里一律无效。
9. **把交接简报写进当前项目目录**（如 `./handoff.md`、`.pi/handoff.md`）。会污染 `git status`，
   在 submodule 里还容易跨范围误提交。→ 按 §7.1 放 `%APPDATA%`。

---

## 9. 未验证 / 待办

- ⚠️ **没有任何 agent 提供"面向 agent 的结构化交接导出"**：Claude Code `/export` 是给人读的文本、
  opencode `export` 是 JSON（仍需自己解析）、pi `--export` 是 HTML。这正是"简报"必须存在的原因，
  但也意味着目前没有一条官方标准化的跨 agent 通道。**尚未逐版本复核这三个导出命令的确切输出形态。**
- ⚠️ **`opencode run --session <id> "..."` 能否直接写文件**：未实测它是纯 stdout 输出还是具备工具能力；
  若只输出到 stdout，需要重定向到文件。
- ⚠️ **`claude -p --resume --output-format json` 在超长会话上的行为**：若旧会话已接近窗口上限，
  这条总结请求本身可能触发 compact，从而损失精度。未实测。
- ⚠️ **本仓 `docs/memories/` 为空**（仅一句"参考 claude code 的记忆功能..."）：是否值得改成
  "每任务一条 memory + 索引"的形态，尚未决定。
- ⚠️ **非交互模式下写 APPDATA 是否会被工具权限拦截**：`pi -p` / `claude -p` 无人工确认时能否写入
  工作目录之外，未实测。§7.2 已给降级方案（只输出正文，人工落盘）。
- ⚠️ **`_handoff` 伪目录方案是否要写进 AGENTS.md**：目前默认不发明新约定，用 `<项目名>`；
  若你希望交接件与项目运行时数据彻底分开，需要补一句仓库规则。

---

## 10. 参考来源

**pi（本地安装 v0.87.0；`D:\Users\29580\AppData\Local\nvm\v24.10.0\node_modules\@earendil-works\pi-coding-agent\`）**

- `docs/sessions.md` — 会话存储布局、`/resume`、`/fork`、`/clone`、`/compact`、`/export`、分支摘要
- `docs/session-format.md` — JSONL 树结构、entry 类型、`parentSession` 字段、版本迁移
- `docs/compaction.md` — 触发阈值 `contextTokens > contextWindow - reserveTokens`（默认 `reserveTokens=16384`）、
  结构化摘要模板（Goal/Constraints/Progress/Key Decisions/Next Steps/Critical Context + read/modified-files）、
  tool 结果序列化截断 2000 字符、文件操作累积跟踪
- `docs/usage.md` — `AGENTS.md`/`CLAUDE.md`/`AGENTS.override.md` 加载规则、`/reload`
- `docs/environment-variables.md` — `PI_SESSION_ID`、`PI_SESSION_FILE`
- `docs/extensions.md` — `session_before_compact`、`ctx.newSession`/`withSession`
- `examples/extensions/handoff.ts` — `/handoff <goal>`（**注意：解决的是"同一个 pi 下的新旧会话"，不解决跨 agent**；
  其摘要骨架与序列化策略可复用）
- `pi --help` — `--session`、`--print/-p`、`--fork`、`--export`、`--append-system-prompt`

**Claude Code**

- 会话管理（`--continue`/`--resume`/`--fork-session`/`/branch`/`/export`；**脚本接口**
  `claude -p --resume <session-id> --output-format json "..." | jq -r '.result'`；
  转录路径 `~/.claude/projects/<project>/<session-id>.jsonl` 与"内部格式会变"警告）：
  <https://code.claude.com/docs/en/sessions.md>
- 记忆机制（`CLAUDE.md`/`AGENTS.md`、`@import`、auto memory 与 `MEMORY.md` 200 行/25KB 限制）：
  <https://code.claude.com/docs/en/memory.md>
- 上下文窗口与 `/compact` 后保留什么：<https://code.claude.com/docs/en/context-window.md>

**opencode**

- CLI（`run [message..]` 非交互、`--continue`/`--session`/`--fork`、`session list`、
  `export`/`import`、ACP server）：<https://opencode.ai/docs/cli>

**ACP**

- 会话生命周期（`session/new`、`session/load` 重放、`session/resume`、`session/list`、capability 强制检查）：
  <https://agentclientprotocol.com/protocol/session-setup>

**本仓库实证**

- `D:\Users\language_projects\CLAUDE.md`（内容为 `@AGENTS.md`）、`AGENTS.md`
- `aoci.txt` / `aoci.meta.txt` / `aoci.code.txt`
- `docs/plans/`、`docs/specs/`、`docs/memories/README.md`
- `C:\Users\29580\.pi\pi-acp\session-map.json`（ACP `sessionId` ↔ pi `sessionFile`）
- `C:\Users\29580\AppData\Roaming\Zed\settings.json`（`pi-acp` 以 `type: registry` 注册）
- 关联调研：`docs/repo/zed-multi-session-agent-architecture-research.md`
