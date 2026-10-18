# 归档与文档布局约定（自根 AGENTS.md §七 迁出 · 按需引用）

> **触发**：创建任何文档/计划/规格前必读。本文件不在规则自动加载目录（`.agents/rules/`）内，由根 `AGENTS.md` 触发器指引按需读取。

- **文档只允许放在父仓库**：子模块内的项目目录中**一律禁止**出现任何文档目录与文档内容（`docs/`、`docs/specs/`、`docs/plans/`、`spec/`、`specs/`、`plans/` 等均不允许）。
- **`docs/` 根目录不放散装文件**，各归其位：
  - `docs/projects/<lang>/`：项目镜像文档；
  - `docs/guides/`：AI 工作指南（GUIDE 系列）；
  - `docs/plans/`：**仅限父仓级/跨语言全局运维开发计划**（如全仓多子模块提交、跨项目工具链升级、MkDocs 根站点配置等全仓任务；单子项目计划**严禁**放此目录）；
  - `docs/repo/`：仓库自身文档与通用技术知识沉淀（git 子模块机制说明、与项目无关的技术介绍等）；
  - `docs/assets/projects/<lang>/`：跨项目二进制资源（如默认图标）；
  - `.archived/` 同理，跨项目内容收入 `.archived/projects/<lang>/` 分层。
- **例外且硬规则：`docs/index.md` 是站点入口页，禁止删除**（它是站点首页而非散装文件；mkdocs 的 `docs_dir` 根目录必须有它才能生成首页，删了产物无 `index.html`、根路径 404）。
- 所有**项目相关**文档（spec、plan、设计说明、项目知识沉淀等）统一放父仓库 `docs/projects/<lang>/` 下，按子模块内相对路径**镜像层级命名**，并去掉中间冗余的 `docs/` 一层：
  - 例：`go_projects/a/b.md` → `docs/projects/go_projects/a/b.md`；
  - 例：`typescript_projects/taskmon/docs/x.md` → `docs/projects/typescript_projects/taskmon/x.md`。
- 例外：子模块内全大写命名的文档（如 `README.md`、`SUBMODULES.md`）与子仓根级说明文件无需迁移，可原地保留。
- **方法论文档与 AI agent 工作指南**（跨项目、不归属单个子项目，如 `docs/projects/go_projects/CLI 工具开发标准.md`）：放 `docs/projects/<lang>/` 语言层目录，不镜像子仓路径；跨语言标准维护单一文件，其他语言引用同一标准；指南引用的项目实现/文档仍按 `docs/projects/<lang>/<项目>/` 存放。
- **父仓级 AI 工作指南（GUIDE 系列）**：当用户要求“把流程沉淀下来 / 写个操作手册 / 沉淀成 GUIDE”，或一次任务中出现可复用的多阶段工作流（分阶段执行、有人工确认点、有踩坑记录）值得沉淀时，按《[GUIDE 编写规范](docs/guides/README.md)》产出 `docs/guides/GUIDE-<中文主题>.md`（专有名词保留英文，如 `GUIDE-AOCI安装配置.md`）；GUIDE 仿 skill 规范编写但**不注册为 skill**，禁止放入任何 skills 目录。
- **通用技术知识文档**（与任何项目无关的知识介绍/沉淀，如协议介绍、技术调研）：放 `docs/repo/`；`docs/projects/<lang>/` 只收项目相关文档与语言层方法论文档，禁止把此类文档放语言层根目录或任何项目目录。
- 归档项目统一放 `.archived/projects/<lang>/<项目名>/`；语言通用文档放 `docs/projects/<lang>/`。
- 子仓内不再维护各自的 `.archived/`、`docs/`、`.zed/` 与 `.zcode/`。

- **AI 计划与规格落盘强制路由（防呆铁律，执行 sh-plan / sh-spec / kiro / specs 先决检查）**：
  - **子项目计划/规格归属**：任何针对具体子模块或工程（如 `python_projects/zedhub`、`go_projects/agyquota`、`typescript_projects/taskmon` 等）的功能开发、重构或缺陷修复，其 `plans/` 与 `specs/` **一律且必须**落盘在父仓 `docs/projects/<lang>/<subproject>/plans/` 与 `docs/projects/<lang>/<subproject>/specs/` 下，序号从 `01` 独立起编，严禁污染父仓根级目录。
  - **父仓级 `docs/plans/` 严格白名单**：仅用于全仓多语言批量构建、全局 Submodule 运维、根级站点冲突等纯父仓级任务。凡涉及具体代码工程改动的，一律不得将计划落盘在父仓根级 `docs/plans/`。
  - **编号自包含隔离**：子项目的计划编号（`01-xxx.md`）自成闭环，取号时只扫描该子项目自己的 `plans/` 目录，禁止参考或递增父仓 `docs/plans/` 下的全局编号。
