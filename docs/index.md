# language_projects 文档库

`docs/` 下 Markdown 源文件的本地浏览站点（Material for MkDocs，左侧导航树与目录层级一致）；构建与启动方式见仓库根 [README.md](../README.md) 的「文档站点」一节。

> **本文件是站点入口页，不要删除**：mkdocs 的 `docs_dir` 根目录必须有 `index.md` 才能生成站点首页，删掉后构建产物里没有 `index.html`、站点根路径 404。

## 分区导览

| 分区 | 内容 |
|---|---|
| [guides](guides/README.md) | 父仓级 AI 工作指南（GUIDE 系列）与 GUIDE 编写规范 |
| [plans](plans/01-lark-group-bridge.md) | 父仓级开发计划 |
| [projects](projects/go_projects/GUIDE-GO-EXE-ICON.md) | 各语言子仓的项目文档，按 `projects/<语言子仓>/<项目>/` 镜像层级组织；语言级方法论文档（如《CLI 工具开发标准》）放在语言层目录 |
| [specs](specs/01-web-archive-skill/index.md) | spec 驱动开发产出（需求 / 设计 / 任务清单） |
| [repo](repo/Git%20子模块分支机制.md) | 仓库自身文档（git 子模块机制、迁移记录、技术调研） |
| [memories](memories/README.md) | 记忆与经验沉淀 |

`assets/` 是文档引用的二进制资源（图标等），不产出页面。
