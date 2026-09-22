# Monorepo 项目逐项提交推送 Skill 计划

## 概述

### 问题陈述

当前仓库采用父仓库 + 语言子仓库 + 子项目的多层 Git 结构。常规 Git 操作容易把多个项目混入同一个 commit，或在子仓库尚未 push 前先提交父仓库子模块指针。需要把本次验证过的“逐项目审查、逐 commit、逐次 push、最后更新指针”流程沉淀为可点名使用的 skill。

### 已确认需求

- Skill 安装到 `C:\Users\29580\.agents\skills\sh-monorepo-commit-push\`。
- 只处理用户明确授权的仓库范围，不默认提交所有未跟踪内容。
- 运行时产物（`.venv/`、缓存、`__pycache__`、数据库、日志等）必须排除。
- 每个逻辑项目单独 commit，commit 后立即 push。
- 子仓库先完成 commit + push，父仓库最后只提交子模块指针。
- Skill 为任务型 skill，采用“点名使用”描述，不主动接管普通 Git 操作。
- 按 `SKILL-AUTHORING-RULES.md` 通过 `skill-creator` 产出正文与 evals。

## 方案

Skill 只沉淀通用流程，不写入本次仓库的具体项目名、commit 哈希、固定测试命令或 AOCI 结果。正文控制在 250 行以内，采用 SOP 结构：

1. 识别仓库层级和用户授权范围
2. 建立父仓库、子仓库和项目级状态基线
3. 识别并清理不应入库的运行时产物
4. 按项目审查代码和真实验证命令
5. 精确暂存一个项目并检查 staged diff
6. commit 后立即 push，确认远端同步
7. 子仓库全部完成后更新父仓库指针
8. 父仓库自身内容按主题继续拆分提交
9. 最终检查 clean、ahead/behind、子模块状态
10. 失败时停止在当前边界，不批量回滚或继续提交

不在 skill 中包含自动化脚本，避免把项目识别、测试命令和清理策略硬编码；必要的命令模板直接放在正文中即可。

## 任务分解

- [x] **Task 1：起草符合规范的 `SKILL.md`**
  - 文件：`C:\Users\29580\.agents\skills\sh-monorepo-commit-push\SKILL.md`
  - 实现：补充合法 frontmatter、短 description、仓库边界规则、逐项提交 SOP、停止条件、PowerShell 命令模板和 commit message 规则；正文使用中文，标识符与命令保留英文。
  - 验证：检查目录名与 frontmatter `name` 一致、name 满足正则、description 单行且以“点名使用”结尾、正文不超过 250 行。
  - Demo：用户说“把几个子项目分别提交并 push”时，skill 能指导先盘点范围而不是执行 `git add .`。

- [x] **Task 2：编写任务式 evals**
  - 文件：`C:\Users\29580\.agents\skills\sh-monorepo-commit-push\evals\evals.json`
  - 实现：编写 3 个用户视角测试用例，覆盖多子仓项目提交、含运行时产物的工作区、父仓库子模块指针收尾；expected_output 描述应达到的流程结果，不写触发断言。
  - 验证：JSON 可解析，每个用例包含 `id`、`prompt`、`expected_output`、`files`，测试用例不要求对当前真实仓库执行 push。
  - Demo：评测输入能检验 skill 是否坚持范围隔离、逐 commit push 和失败停机。

- [x] **Task 3：完成静态自审并按 authoring rules 收尾**
  - 文件：上述 `SKILL.md` 与 `evals/evals.json`
  - 实现：对照 `SKILL-AUTHORING-RULES.md` 复核 description 长度、点名触发、正文长度、渐进披露和安全边界；如无可用 subagent，不对真实仓库执行危险评测，保留 evals 作为后续评测输入。
  - 验证：执行 JSON 解析、frontmatter 检查、行数检查和关键安全条款检查；预期所有结构检查通过。
  - Demo：输出 skill 路径、触发边界、评测用例摘要和未执行真实 push 评测的原因。

## 完成标准

- Skill 位于指定目录且能被一层扫描发现。
- description 简短、以“点名使用”结尾，不包含触发词军备竞赛。
- 正文明确禁止跨项目混提，并包含子仓库先 push、父仓库后更新指针的顺序。
- 提供 3 个任务式 eval 用例。
- 不因评测而修改或 push 当前业务仓库。

---

最后更新：2026-09-23
作者：AI
版本：1.0
