# 归档说明

- **归档日期**：2026-11-06
- **原路径**：`go_projects/acp-title-proxy`
- **归档原因**：停更，不再继续维护；源码与文档整体随父仓归档留档。

## 内容范围

- 归档副本仅包含 git 跟踪的源码、脚本与文档（`docs/` 内含子仓时期的 research 与 share 设计文档）。
- **未归档**：`bin/`（构建产物）、`config.json`（本地实例配置，**含真实 API key，已排除**）；需要实例配置时参照 `config.example.json` 重建。

## 恢复方式

```powershell
Move-Item -LiteralPath D:\Users\language_projects\.archived\projects\go_projects\acp-title-proxy `
  -Destination D:\Users\language_projects\go_projects\acp-title-proxy
```

恢复后按 `README.md` 重新构建；`docs/` 应迁移回父仓 `docs/projects/go_projects/acp-title-proxy/`。

## 关联影响

- `agyapptitle` 的配置加载会回退读取 `go_projects/acp-title-proxy/config.json`（另有 `%APPDATA%\language_projects\acp-title-proxy\config.json` 回退），归档后该路径解析失败但不会中断启动。
