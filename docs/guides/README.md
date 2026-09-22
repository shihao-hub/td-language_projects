# GUIDE 编写规范

> `docs/guides/` 收录**父仓级 AI 工作指南**：跨项目、可直接交给 AI agent 执行的操作手册，是知识沉淀，不是笔记。
> 仿照 skill 规范编写，但**不注册为 skill**——禁止放入 `~/.config/opencode/skills/`、`.opencode/skills/` 等任何 skills 目录。

## 定位：什么时候写 GUIDE

满足任一条即值得沉淀为 GUIDE：

- 用户明确要求："把这个流程沉淀下来"、"写个操作手册"、"沉淀成 GUIDE"；
- 一次任务中出现了**可复用的多阶段工作流**：分阶段执行、有人工确认点、有踩坑记录、下次大概率还会做（如项目归档、文档批量改名、MCP 调试接入）。

反面例子（不要写成 GUIDE）：一次性问题的排查过程、只对单个项目有意义的说明（那属于 `docs/projects/<lang>/<项目>/`）、纯知识点罗列（那是笔记不是操作手册）。

## 三级披露：AI 如何发现与使用

1. **AGENTS.md 一句话入口**（常驻上下文）：告诉 agent "什么时候该沉淀 GUIDE、去哪找规范"；
2. **本规范**（`docs/guides/README.md`）：告诉 agent "怎么写"；
3. **具体指南的 frontmatter `description`**：告诉 agent "当前任务该翻哪一份"。

因此每份 GUIDE 的 `description` 必须按触发式写法（见下），否则第 3 级失效。

## 目录与命名

| 指南范围 | 位置 | 命名 |
|---|---|---|
| 父仓级（归档、盘点、跨项目工具链等） | `docs/guides/` | `GUIDE-<kebab-case 英文名>.md` |
| 语言专属（go exe 图标等） | `docs/projects/<lang>/` | 同上（如 `docs/projects/go_projects/GUIDE-GO-EXE-ICON.md`） |

- 文件名 = `GUIDE-` 前缀 + kebab-case 英文标识，与 frontmatter `name` 对应（`GUIDE-GO-EXE-ICON.md` ↔ `name: go-exe-icon`）。
- 一份 GUIDE 只沉淀一个工作流；多个相关流程分文件，互链即可。

## 文件结构

### frontmatter（必需）

```yaml
---
name: kebab-case-name
description: 做什么 + 何时该翻这份指南。用触发式写法列举真实说法（"当用户说 A / B / C，或要做 X 时使用"），宁"推"勿"收"——仿 skill description 防漏触发的思路。
---
```

`description` 是一级索引：agent 扫描 `docs/guides/` 目录时凭它判断相关性。只写"是什么手册"不写"什么时候用"，等于没有索引。

### 正文骨架（按需取舍，顺序建议固定）

1. **概述**：这段流程解决什么问题，2~3 句；
2. **触发与豁免**：何时进入本流程，何种情况明确跳过；
3. **核心纪律**：3~6 条，每条**解释 why**（规则背后的原因比步骤本身更防错）；
4. **分阶段工作流**：祈使句（"列出"、"对照"、"向用户展示"），每个阶段写清输入、动作、产物；
5. **示例**：用 `Input:` / `Output:` 格式给 1~3 个真实场景；
6. **陷阱速查 / 验证**：踩过的坑列成表；能脚本验证的给出可直接粘贴的 PowerShell 片段。

## 写作风格（源自 skill-creator）

- **解释 why，不堆 MUST**：全大写 ALWAYS/NEVER 是危险信号；LLM 理解了原因才能举一反三，死记硬背的规则一遇到变体就失效。
- **祈使句写指令**：指南的读者是执行者（AI 或人），"先做 X 再做 Y"，不要写"我们会考虑先做 X"。
- **渐进式披露**：单文件 < 500 行；快超限时把细节拆成同目录姊妹文件并留明确跳转指引，不要无限膨胀单文件。
- **示例给足上下文**：Input/Output 示例用真实项目名和真实场景，抽象占位符示例没有校准价值。
- **引用带路径**：提到其他文档一律写仓库相对路径（如 `docs/guides/GUIDE-ARCHIVE.md`），裸文件名无法定位。

## 改名与迁移纪律

GUIDE 会被其他文档、子仓 README 交叉引用，**改名/移动是高危操作**：

1. 迁移前先全仓 grep 旧文件名，列出全部引用点；
2. 引用修复必须覆盖：父仓自有文档、**子仓内 README**（跨仓改动须用户确认，且在子仓单独提交）、指南之间的互链；
3. 迁移后再次 grep 旧名，**清零才算完成**（git 内部文件与历史提交除外）。

## 现有清单

| 文件 | 主题 |
|---|---|
| [GUIDE-ARCHIVE.md](GUIDE-ARCHIVE.md) | 子仓项目归档到 `.archived/projects/<lang>/` |
| [GUIDE-RESTORE.md](GUIDE-RESTORE.md) | 归档项目恢复回子仓（归档逆操作） |
| [GUIDE-INVENTORY.md](GUIDE-INVENTORY.md) | MONOREPO.md 项目价值盘点表维护 |
| [GUIDE-DOCS-RENAME.md](GUIDE-DOCS-RENAME.md) | docs 下英文命名文档批量改中文名并修引用 |
| [GUIDE-AOCI-SETUP.md](GUIDE-AOCI-SETUP.md) | AOCI-CODE 仓库认知索引的安装与配置 |
| [GUIDE-MCP-INSPECTOR.md](GUIDE-MCP-INSPECTOR.md) | MCP Inspector 测试调试自定义 stdio MCP server |
| [GUIDE-THIRDPARTY-CLONE.md](GUIDE-THIRDPARTY-CLONE.md) | 第三方开源项目克隆到 .thirdparty/（gitignore + 自有 remote，不用 submodule） |
| [GUIDE-LLM-PROVIDER-COMPAT.md](GUIDE-LLM-PROVIDER-COMPAT.md) | 把只支持 OpenAI/Anthropic/Gemini 的外部工具接到自己的模型上（探针先行 + 最小补丁 + 双层验证） |
| [../projects/go_projects/GUIDE-GO-EXE-ICON.md](../projects/go_projects/GUIDE-GO-EXE-ICON.md) | go_projects exe 默认地鼠图标（语言专属） |
