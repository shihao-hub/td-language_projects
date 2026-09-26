# 任务清单

- [ ] 1. 创建 `sourcecount` Go 项目骨架与基础契约
  - Files: `go_projects/sourcecount/go.mod`、`go_projects/sourcecount/cmd/sourcecount/main.go`、`go_projects/sourcecount/internal/contract/types.go`
  - 实现细节：使用 Go 1.25.3；引入 MCP SDK v1.8.0；建立版本变量、公共请求/结果 DTO 和稳定错误类型；保持项目独立，不修改其他 Go 项目。
  - Verify: 在项目目录执行 `go build ./...`，预期所有包构建成功。
  - Ref: AC-8、AC-9、AC-10

- [ ] 2. 实现配置加载、规范化和 Glob 过滤
  - Files: `go_projects/sourcecount/internal/config/config.go`、`go_projects/sourcecount/internal/config/glob.go`
  - 实现细节：实现 `.sourcestats.json` 自动发现、显式路径优先、配置版本校验、后缀规范化、默认排除、include/exclude 优先级和 `**` Glob 语义；暴露纯函数供 Server 和 CLI 复用。
  - Verify: 执行 `go build ./...`，预期配置包无编译错误。
  - Ref: AC-5、AC-6

- [ ] 3. 实现扫描、文件分类和文本统计核心
  - Files: `go_projects/sourcecount/internal/scanner/scanner.go`、`go_projects/sourcecount/internal/scanner/classify.go`、`go_projects/sourcecount/internal/scanner/text.go`
  - 实现细节：使用 `WalkDir`、链接跳过、路径去重、后缀提取、内容探测、二进制大小统计、流式 UTF-8/行统计和单文件错误记录；加入有界 worker 调度所需接口。
  - Verify: 执行 `go build ./...`，预期扫描包构建成功且无未使用依赖。
  - Ref: AC-1、AC-2、AC-3、AC-4、AC-7

- [ ] 4. 实现公共 Server 层与聚合报告
  - Files: `go_projects/sourcecount/internal/service/server.go`、`go_projects/sourcecount/internal/service/aggregate.go`
  - 实现细节：实现 `Scan(ctx, ScanRequest)`，统一处理配置、根路径校验、扫描器调用、并发聚合、稳定排序、部分失败和取消；CLI 与 MCP 不得绕过该层。
  - Verify: 执行 `go build ./...`，预期公共服务与依赖方向构建成功。
  - Ref: AC-1 至 AC-7

- [ ] 5. 实现 CLI 人读输出、JSON 输出、参数和 schema 入口
  - Files: `go_projects/sourcecount/internal/cli/commands.go`、`go_projects/sourcecount/internal/cli/output.go`、`go_projects/sourcecount/internal/cli/schema.go`
  - 实现细节：实现默认当前目录、多根路径、配置/过滤参数、`--json`、人读表格、`schema`、`--help`、`--version` 和退出码映射；schema 分支必须不触发扫描。
  - Verify: 执行 `go build ./...`，预期 CLI 可执行文件构建成功。
  - Ref: AC-8、AC-10

- [ ] 6. 实现 MCP stdio server 与同源工具 Schema
  - Files: `go_projects/sourcecount/internal/mcp/server.go`、`go_projects/sourcecount/internal/mcp/tools.go`、`go_projects/sourcecount/internal/mcp/schema.go`
  - 实现细节：注册 `sourcecount.project.scan`，将输入映射到 Server，复用结构化报告和错误；使用 in-memory transport 导出真实工具定义；stdout 不输出日志。
  - Verify: 执行 `go build ./...`，预期 MCP 包构建成功。
  - Ref: AC-9、AC-10

- [ ] 7. 补充项目使用文档和构建脚本
  - Files: `go_projects/sourcecount/README.md`、`go_projects/sourcecount/scripts/build.ps1`、`docs/projects/go_projects/sourcecount/使用指南.md`
  - 实现细节：记录安装/构建、CLI/MCP 调用、JSON 配置、默认过滤、错误码、Schema 和已知限制；构建脚本支持版本注入并将产物置于项目 build 目录。
  - Verify: 执行 `go build ./...`，预期文档所示构建命令可用。
  - Ref: AC-5、AC-8、AC-9、AC-10

- [ ] 8. [test] 编写并执行核心、CLI 和 MCP 测试
  - Files: `go_projects/sourcecount/internal/config/*_test.go`、`go_projects/sourcecount/internal/scanner/*_test.go`、`go_projects/sourcecount/internal/service/*_test.go`、`go_projects/sourcecount/internal/cli/*_test.go`、`go_projects/sourcecount/internal/mcp/*_test.go`
  - 实现细节：覆盖空文件、换行、Unicode、无效 UTF-8、二进制、混合后缀、Glob、默认排除、多根去重、部分失败、JSON、Schema 和真实 MCP stdio。
  - Verify: 执行 `go vet ./...` 与 `go test ./...`，预期全部通过；并按需要执行 `go test -race ./...`。
  - Ref: AC-1 至 AC-10