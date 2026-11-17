# 计划：sync_skills.py 新增 Kimi Code 同步支持

## Context（背景与动机）

- 用户今天（2026-11-18）安装了 Moonshot 的编码 CLI **Kimi Code**（`~/.kimi-code/`，主程序 `~/.kimi-code/bin/kimi.exe`，尚未登录）。
- 希望 `.agents/skills` 技能源能同步给 Kimi Code 使用，问怎么加进 `sync_skills.py`。
- `sync_skills.py` 是唯一的多 agent 分发器（其余 `sync_lark_skills.py` 等是各自技能族的内部工具，无需联动）。

### 本机探明的 Kimi Code 事实（二进制字符串取证，非猜测）

| 项 | 事实 |
| --- | --- |
| 用户级 skills 目录 | `~/.kimi-code/skills/`（自动发现；`--skills-dir` 可覆盖） |
| 环境变量 | `KIMI_CODE_HOME` 可改根目录（本机**未设置** → 默认 `~/.kimi-code`） |
| 技能格式 | 与 Claude/Codex 相同：目录束 `<name>/SKILL.md`，散装 `<name>.md` 忽略 |
| 保留目录 | 无（不像 codex 有 `.system`）；且 `~/.kimi-code/skills` 当前不存在，整目录 junction 零风险 |
| 项目级目录 | `<project root>/.kimi-code/skills/`，与本脚本无关 |

## 方案：并入 "整目录 junction" 组（与 claude/cursor 同策略）

单文件改动：`.agents/skills/sync_skills.py`（真身在 language_projects 的 `.agents/skills` 子模块，junction 到 `~/.agents/skills`）。

### 改动点

1. **`AGENTS` 字典加一条**（约 `sync_skills.py:44`），并尊重其真实解析规则：
   ```python
   "kimi": Path(os.environ.get("KIMI_CODE_HOME") or Path.home() / ".kimi-code") / "skills",
   ```
   - link 模式自动走 `sync_link_whole`（整目录 junction，改源即时生效）；copy 模式自动走 `sync_copy_whole`——无需新增任何分支。
   - `--agent kimi` / `all` 由 `argparse` 的 `choices=[*AGENTS, ...]` 自动生效，无需改参数定义。
2. **docstring 头部**（`sync_skills.py:5-21`）：agent 列表加 "Kimi Code"；用法行 `--agent` 枚举补 `kimi`。
3. **`sync_link_whole` / `sync_copy_whole` 的 docstring**：`claude / opencode / gemini / cursor` → 补 `kimi`。

不加 RESERVED（无内置保留目录）；不进 NATIVE_AGENTS（kimi 不会自己读 `~/.agents/skills`）。

## 验证

1. `uv run .agents/skills/sync_skills.py --agent kimi --check` → 预期打印 `LINK C:\Users\29580\.kimi-code\skills -> C:\Users\29580\.agents\skills`
2. 真跑 `--agent kimi` → `cmd //c dir C:\Users\29580\.kimi-code` 确认 `<JUNCTION>` 指向源
3. 回归：`uv run .agents/skills/sync_skills.py --agent all --check` → 其余 6 个 agent 动作不变（已链接者为 SKIP）
4. 抽验加载：`kimi doctor` 通过；登录后由用户在 Kimi Code TUI 里确认技能列表（本会话不代登录）

## 提交（两段，均直接执行，无需再确认）

- **skills 子仓**（只暂存 `sync_skills.py`，严禁混入工作区已有的 kb-engineering-notes / sh-transcript-reader 等未提交改动）：
  - 标题沿用先例 `90c7660` 的风格：`chore: sync_skills 增加 kimi code skills 目录同步支持`
  - Body 用 `- ` 列表说明，末尾加 `Co-Authored-By: Claude Code <noreply@anthropic.com>`
- **父仓**：子模块指针 + 本计划文件各自独立提交（`**/plans/**` 强制单文件独占）：
  - `chore: 更新 .agents/skills 子模块指针（sync_skills 支持 kimi）`
  - `docs(plans): 新增 sync_skills 支持 kimi code 计划`

### 未决问题与阻塞确认清单
- [ ] `KIMI_CODE_HOME` 环境变量支持是否保留（已按"忠实于 kimi 真实解析规则、仅一行"倾向保留；不想要可去掉，退化为硬编码 `Path.home()/.kimi-code`）
- [ ] Kimi Code 对整目录 junction 的实际加载表现需登录后由用户实测（Node fs 对 junction 透明，cursor 有同款先例，风险低）
