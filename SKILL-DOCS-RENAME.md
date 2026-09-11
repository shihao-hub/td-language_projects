---
name: docs-rename
description: 把父仓库 docs/ 目录下的英文命名 Markdown 文档批量整改为中文名，并同步修复所有交叉引用。当用户要求「docs 整改」「文档改中文名」「批量重命名 markdown」「文档命名规范化」「修正文档引用链接」时使用，即使只说「把这些 md 改成中文名」也应触发。核心价值：改名前先盘点引用链，改名时区分 git 跟踪状态选对工具，改名后反查旧名残留清零。
---

# docs 文档中文命名整改工作流

## 适用场景

父仓库 `docs/<lang>/` 镜像布局下的 Markdown 文档，由英文命名（kebab-case / 单词直拼）整改为中文命名。核心特征：文档之间存在交叉引用（索引表、互见链接、裸文件名提及），改名必须连同引用一起修，否则链接全断。

## 工作流五步

### ① 盘点

- `glob docs/**/*.md` 列出全部文件；
- `grep "^# "` 提取每个文件的一级标题，作为中文名的命名依据（标题通常就是现成的中文主题）；
- `grep "\\]\\([^)]+\\.md"` 找出所有 `](xxx.md)` 形式的链接引用，画出引用关系。

### ② 分类决策（先问用户，再动手）

必须明确哪些改、哪些不改：

- **保留不动**：`specs/` 三件套（requirements.md / design.md / tasks.md，spec 工作流的标准文件名）、`README.md`（GitHub 自动渲染惯例）、子模块内全大写文档；
- **已是中文命名**：跳过；
- **子仓内对本仓 docs 的引用**：属跨仓库改动，默认不修，向用户说明后由用户决定；
- 全局配置中的旧命名规则（如 kebab-case 约定）：是否同步更新，先问。

### ③ 改名执行（关键：先判断 git 跟踪状态）

改名前用 `git ls-files -- <目录>` 或 `git status` 确认：

- **已跟踪文件**：必须用 `git mv 旧名 "新名.md"`，保留历史；
- **untracked 文件**：`git mv` 会报 `fatal: not under version control`，改用 PowerShell `Rename-Item`，后续 `git add` 时作为新文件入库。

注意：

- PowerShell 下含中文/空格的路径一律双引号包裹；
- PowerShell 5.1 控制台显示中文文件名会乱码（GBK codepage 显示问题），文件名本身是正确的，用 `glob` 工具验证真实文件名，不要被乱码误导而反复重命名。

### ④ 引用同步

改名完成后，在 docs 范围内 `grep` 所有旧文件名，逐一处理两类残留：

- 链接形式 `[slug](old-name.md)`：链接文字保留英文 slug，仅改括号内目标为新中文名；
- 裸提及形式（反引号或正文中直接写 `old-name.md`）：同样替换为新名。

### ⑤ 验证与提交

- 再次 `grep` 全部旧文件名，docs 内命中必须清零（保留项除外）；
- `git status` 确认：已跟踪文件显示 `R`（rename），untracked 目录显示 `??` 正常；
- 父仓库一次 commit，message 形如 `docs: 整改文档命名为中文命名`。

## 命名风格约定

英文前缀 + 空格 + 中文主题，与既有中文文档（`go 知识点.md`、`taskmon 源码阅读三方法.md`）保持一致：

| 旧名示例 | 新名示例 |
|---|---|
| `clictl.md` | `clictl 使用指南.md` |
| `transactional-outbox.md` | `事务发件箱.md` |
| `001-taskmon-process-tree.md` | `001-进程树检测.md`（保留编号前缀） |

## 已知边界与坑

- untracked 目录（如新迁移尚未提交的 `docs/<lang>/xxx/`）内文件只能 Rename-Item，没有历史可保留；
- 子仓内引用（clictl / zedhub / django-lab 的 README 等）指向父仓 docs 路径，改名后失效，需进各子仓分别提交修复，不混入本次父仓库提交；
- README 索引表格中的链接目标列与「实验代码」列（如 `apps/xxx`）是两回事，只改前者。

## 实施记录

- **2026-09-11**：首次整改。18 个文件改名（docs 根 1、go_projects 3、python_projects 13、rust_projects 1、typescript_projects 1），同步引用 24 处（README 索引表 11 + 教程互引 11 + 裸提及 2）。踩坑：`tech_learning_room/` 与 `rust_projects/` 为 untracked 目录，`git mv` 失败后改用 `Rename-Item`；specs 三件套与 README.md 按用户决策保留；子仓内 5 处失效引用未修，待另行处理。
