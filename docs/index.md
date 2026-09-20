# language_projects 文档库

本站由 `docs/` 下的 Markdown 源文件构建（Material for MkDocs），左侧导航树与 `docs/` 目录层级一致。

## 分区导览

| 分区 | 内容 |
|---|---|
| [guides](guides/README.md) | 父仓级 AI 工作指南（GUIDE 系列）与 GUIDE 编写规范 |
| [plans](plans/01-lark-group-bridge.md) | 父仓级开发计划 |
| [projects](projects/go_projects/GUIDE-GO-EXE-ICON.md) | 各语言子仓的项目文档，按 `projects/<语言子仓>/<项目>/` 镜像层级组织；语言级方法论文档（如《CLI 工具开发标准》）直接放在语言层目录 |
| [repo](repo/Git%20子模块分支机制.md) | 仓库自身文档（git 子模块机制、迁移记录、调研笔记） |

## 站点维护

```powershell
uv run .scripts/build_docs.py build   # 构建 .mkdocs-site/（双击其中 index.html 以 file:// 浏览）
uv run .scripts/build_docs.py serve   # 写作期热刷新 / 搜索（http://127.0.0.1:8765）
```

`docs/` 下的 Markdown 是唯一事实源（随 git 管理）；`.mkdocs-site/` 为构建产物，不入 git，随时删除重建。
