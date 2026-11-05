# 归档说明

- **归档日期**：2026-09-24（本次 2026-11-06 更名补档）
- **原名**：`.archived/projects/go_projects/glmquotawatch`
- **现名**：`glmquotawatch-cli` —— 为给后续归档的 Wails GUI 版腾出 `glmquotawatch` 名称，本目录更名为 `-cli` 后缀。
- **身份**：GLM（bigmodel）编码套餐用量监控的**纯 CLI + MCP 版**（`gqw.*` 工具集），已被 GUI 复活版取代。
- **文档**：原 `docs/projects/go_projects/glmquotawatch/` 已迁入本目录 `docs/`（使用指南 + schema 可移植性计划）。

## 恢复方式

```powershell
Move-Item -LiteralPath D:\Users\language_projects\.archived\projects\go_projects\glmquotawatch-cli `
  -Destination D:\Users\language_projects\go_projects\glmquotawatch
```

`docs/` 应迁移回父仓 `docs/projects/go_projects/glmquotawatch/`。
