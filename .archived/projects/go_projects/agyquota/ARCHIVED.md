# 归档说明

- **归档日期**：2026-11-06
- **原路径**：`go_projects/agyquota`
- **归档原因**：停更，不再继续维护；源码与文档整体随父仓归档留档。

## 内容范围

- 归档副本仅包含 git 跟踪的源码、脚本与文档（`docs/` 含 `plans/`、`specs/` 与设计说明）。
- **未归档**：`bin/`（构建产物）、运行期生成的静默 `agy_silent.exe` 等缓存副本。

## 恢复方式

```powershell
Move-Item -LiteralPath D:\Users\language_projects\.archived\projects\go_projects\agyquota `
  -Destination D:\Users\language_projects\go_projects\agyquota
```

恢复后按 `README.md` 重新构建；`docs/` 应迁移回父仓 `docs/projects/go_projects/agyquota/`。

## 备注

- 曾于 2026-09 归档后经 `09-restore-agyquota` 计划复活过一次，本次为第二次归档。
