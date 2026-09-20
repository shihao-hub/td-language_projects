# glmquotawatch MCP Schema 可移植性修复计划

## 项目概述

消除 MCP Inspector `--strict` 报出的 **6 条 `type-union` warning**（0 error）：go-sdk 底层的 `google/jsonschema-go` v0.4.3 对 Go 切片默认推导 `"type": ["null","array"]`，部分 MCP 客户端把 `type` 当单字符串解析会拒绝工具或丢弃约束。核心需求：

- 6 处 outputSchema 的切片类型全部变为 `"type": "array"` 单字符串形式
- 不改变任何业务行为、工具名、视图字段（两侧同形原则不动）
- `tools/list` 与 `schema` 子命令导出保持同源
- 修复后 Inspector `--strict` 零输出

## 项目结构（全部为改动，无新建代码文件）

```
glmquotawatch/
├── internal/mcp/server.go        # 新增 init()：设置 JSONSCHEMAGODEBUG 兼容开关
├── internal/service/service.go   # view() 的 Thresholds 兜底非 nil（1 行）
├── internal/mcp/mcp_test.go      # TestToolsListed 加 schema 无 type-union 断言
├── internal/service/service_test.go  # 新增 null-thresholds 回归测试
└── （父仓库）docs/projects/go_projects/glmquotawatch/使用指南.md  # 补冒烟复检记录
```

## 核心数据结构

无新增类型。涉及的两个既有改动点：

**internal/mcp/server.go** —— 在 `var Version` 之前插入：

```go
// init 在首次 schema 推导（NewServer→registerTools→AddTool）前设置
// jsonschema-go（go-sdk 的推导引擎，v0.4.3）的兼容开关：切片只推导
// "type":"array"，不产生 ["null","array"] 并集——数组形式 type 会被部分
// MCP 客户端拒绝（Inspector --strict 的 type-union 警告）。该开关为库
// doc.go 明文提供的兼容机制，值按精确字符串匹配（无逗号分隔语法），
// 已设置时尊重用户环境不覆盖。
func init() {
	if os.Getenv("JSONSCHEMAGODEBUG") == "" {
		os.Setenv("JSONSCHEMAGODEBUG", "typeschemasnull=1")
	}
}
```

（需补 `import "os"`）

**internal/service/service.go:209** —— `view()` 中：

```go
// 改前
Thresholds: append([]int(nil), cfg.Thresholds...),
// 改后（手改 config.json 把 thresholds 写成 null 时，视图仍序列化为 [] 而非 null，
// 与 outputSchema 去掉 null 分支后的契约一致；Notified/Windows 已有同款兜底）
Thresholds: append([]int{}, cfg.Thresholds...),
```

## 核心模块设计

**为什么 env 开关必须配 nil 兜底**：go-sdk v1.8.0 在工具返回非 error 结果时，会用 outputSchema 对 `structuredContent` 做校验。Go nil 切片 marshal 为 `null`，若 schema 不再允许 null 而视图偶发 null，SDK 校验直接失败。`Windows`（`[]WindowView{}`）与 `Notified`（`[]int{}`）已兜底，唯一缺口是 `Thresholds`——`LoadConfig` 不 normalize，手改 config.json 写 `"thresholds": null` 即触发。

**测试设计**：

1. `mcp_test.go` 的 `TestToolsListed` 追加断言：把每个 tool 的 `InputSchema`/`OutputSchema` `json.Marshal` 后，不含 `"type":[`——字符串级守卫，对任意嵌套深度（如 `windows.items.properties.notified`）都生效。
2. `service_test.go` 新增 `TestViewThresholdsNeverNull`：`store.Open(t.TempDir())` → 手写 `config.json`（`{"thresholds": null}`）→ `GetConfig()` → `json.Marshal(view)` → 断言含 `"thresholds":[]` 且不含 `"thresholds":null`。

## 实现步骤（分阶段）

### Phase 1：代码修复 + 单元测试

- [x] 1. `internal/mcp/server.go` 加 `init()`（含 `os` import 与注释）
- [x] 2. `internal/service/service.go:209` 改为 `append([]int{}, ...)`
- [x] 3. `mcp_test.go` TestToolsListed 追加无 type-union 断言
- [x] 4. `service_test.go` 新增 `TestViewThresholdsNeverNull`

**验收标准**：

- `go test ./...` 全绿（含新断言与新测试）
- TestToolsListed 在开关生效下通过（若断言失败说明开关未生效）

### Phase 2：端到端验证 + 文档

- [x] 5. `go run . schema` 人工核对：thresholds / windows / notified 三处均为 `"type":"array"`
- [x] 6. 重建 exe 后重跑 `npx --yes @modelcontextprotocol/inspector --cli .\glmquotawatch.exe mcp --method tools/list --strict --format json`，确认无 `schemaFindings` 键、stderr 无摘要行（干净时零输出）
- [x] 7. 使用指南「MCP 接入」冒烟记录下补一行 2026-09-18 记录：--strict 复检 0/0 + 日常检查命令用法

**验收标准**：

- `--strict` 零输出（对比修复前 `0 errors, 6 warnings across 5 tools`）
- 使用指南更新后与实测一致

## 技术依赖

无新增依赖。`jsonschema-go v0.4.3` 已为 go-sdk v1.8.0 的 indirect 依赖（go.mod:13，go.sum 锁定版本，开关语义稳定）。

## 关键技术点

1. **选 env 兼容开关，弃每工具显式注入**：备选方案是给 6 个工具各预计算 `jsonschema.For[T](opts)` 再显式设 `Tool.InputSchema/OutputSchema`——无进程全局副作用，但要 6×2 样板代码、新工具易漏、注册代码复杂化。env 开关 3 行生效、未来工具自动覆盖、`tools/list` 与 `schema` 导出天然同源。代价是进程级 `os.Setenv`——对单进程叶子 CLI 工具可接受。
2. **开关是精确匹配**：库源码判 `os.Getenv(...) != "typeschemasnull=1"`，无逗号分隔语法；因此 init() 只在未设置时写入，已设置（无论何值）一律尊重。
3. **SDK 侧 schema 校验使 nil 修复成为硬要求**而非锦上添花（见核心模块设计）。

## 预计时间

| Phase | 估时 |
|---|---|
| Phase 1 | 20 分钟 |
| Phase 2 | 15 分钟 |
| 总计 | ~35 分钟 |

## 后续扩展（二期）

- 无。类型表达层一次性修复，不涉及业务。

## 注意事项

- 重建 exe 用既有版本注入方式（`-ldflags "-X glmquotawatch/internal/cli.Version=v0.1.1"`），同版本重建，不升版本号。
- 落盘位置：父仓库 `docs/projects/go_projects/glmquotawatch/plans/01-mcp-schema-portability.md`（对齐仓内先例：`clictl/plans/`、`projstat/specs/`，均为父仓库 `docs/projects/<lang>/<项目>/` 镜像路径）。
- 提交范围隔离：代码改动在 go_projects 子仓（`glmquotawatch:fix: ...`），使用指南与本计划文件在父仓库（`docs: ...`），两次提交。

---
**最后更新：** 2026-09-18
**作者：** AI & User
**版本：** v1.1（执行完成，全部验收通过）
