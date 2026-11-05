# 归档说明

- **归档日期**：2026-11-06
- **原路径**：`go_projects/termhub`
- **归档原因**：停更，不再继续维护；源码与文档整体随父仓归档留档。

## 内容范围

- 归档副本仅包含 git 跟踪的源码、脚本与前端源码；镜像文档在 `docs/`（含实施计划与终端管理器规格）。
- **未归档**：`bin/`、根目录 `termhub.exe`、`node_modules/` 等构建产物与依赖缓存。

## 恢复方式

```powershell
Move-Item -LiteralPath D:\Users\language_projects\.archived\projects\go_projects\termhub `
  -Destination D:\Users\language_projects\go_projects\termhub
```

恢复后先 `npm install` 再按 `README.md` 构建；`docs/` 应迁移回父仓 `docs/projects/go_projects/termhub/`。
