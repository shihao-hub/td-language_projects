# Task List: Anatomy Manager

- [x] 1. 初始化 Go 模块与目录架构
  - Files: `go_projects/anatomymanager/go.mod`, 基础目录规划
  - Verify: `go version`, `go.mod` 成功生成
  - Ref: AC-1

- [x] 2. 领域模型与纯 Go SQLite 存储层实现
  - Files: `internal/model/model.go`, `internal/storage/sqlite.go`
  - Verify: 依赖 `modernc.org/sqlite` 纯 Go 驱动，自动建表与 BLOB 二进制快照存取
  - Ref: AC-1

- [x] 3. CLI 命令行实现与 JSON Schema 契约支持
  - Files: `cmd/anatomymanager/main.go`
  - Verify: `anatomymanager ingest`, `list`, `get`, `schema`, `export`, `serve` 支持 `--json` 输出
  - Ref: AC-1, AC-2

- [x] 4. 内嵌原生 WebUI 与 HTTP 静态流式服务
  - Files: `internal/web/assets/index.html`, `style.css`, `app.js`, `embed.go`, `internal/api/server.go`
  - Verify: 零 npm 依赖，`//go:embed` 打包，支持日/夜主题切换与 iframe 交互渲染
  - Ref: AC-3

- [x] 5. 编译单文件二进制与真实会话产物实测
  - Files: `anatomymanager.exe`
  - Verify: 摄取会话 `6970a9e0-1c38-4f75-bd66-ec8a26d10e6a` 的 `rate-limiter` 产物，6 个文件全量入库，HTTP 200 流式渲染通过
  - Ref: AC-1, AC-3
