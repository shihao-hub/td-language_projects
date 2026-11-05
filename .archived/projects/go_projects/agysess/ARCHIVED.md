# 归档说明

- **归档日期**：2026-11-06
- **原路径**：`go_projects/agysess`
- **归档原因**：停更，不再继续维护；源码与文档整体随父仓归档留档。

## 内容范围

- 归档副本仅包含 git 跟踪的源码与脚本；镜像文档在 `docs/`（含实施计划）。
- **未归档**：`bin/`（构建产物）。

## 恢复方式

```powershell
Move-Item -LiteralPath D:\Users\language_projects\.archived\projects\go_projects\agysess `
  -Destination D:\Users\language_projects\go_projects\agysess
```

恢复后按 `README.md` 重新构建；`docs/` 应迁移回父仓 `docs/projects/go_projects/agysess/`。
