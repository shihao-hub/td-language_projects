# Task List

前提：项目为全新 Go module `github.com/shihao-hub/liteconf`（go 1.22+），零第三方依赖，全部使用标准库（`net/http`、`encoding/json`、`log/slog`、`sync/atomic`、`os`）。目录结构与模块职责见同目录 `design.md`。所有命令均在 `go_projects/liteconf/` 目录内执行。

- [x] 1. 初始化项目骨架
  - 创建 `go_projects/liteconf/go.mod`：`go mod init github.com/shihao-hub/liteconf`，`go 1.22`
  - 创建空目录：`cmd/liteconf-server/`、`internal/server/`、`client/`
  - Run and validate: `go build ./...`
  - Ref: REQ-1

- [x] 2. 实现统一响应包络与业务错误
  - 创建 `go_projects/liteconf/internal/server/errors.go`
  - 定义稳定错误 code 常量：`CodeOK = "ok"`、`CodeNotFound = "not_found"`、`CodeInvalidName = "invalid_name"`、`CodeInvalidJSON = "invalid_json"`、`CodeInternal = "internal"`
  - 定义响应包络 `type Response struct { Code string; Message string; Data any }`，JSON tag 分别为 `code`、`message,omitempty`、`data,omitempty`
  - 提供 `WriteJSON(w http.ResponseWriter, status int, code, msg string, data any)` 与 `WriteErr(w, status, code, msg)` 助手（统一设置 `Content-Type: application/json`）
  - 提供 `validName(s string) bool`：正则 `^[a-zA-Z0-9_-]+$` 校验 `app`/`env` 名称（防目录穿越）
  - Run and validate: `go build ./...`
  - Ref: REQ-2, REQ-3

- [x] 3. 实现存储层 store.go
  - 创建 `go_projects/liteconf/internal/server/store.go`
  - 定义 `type key struct { App, Env string }`；`type meta struct { Version uint64; Hash string; ModTime time.Time; Raw json.RawMessage }`
  - 定义 `type Store struct { mu sync.RWMutex; root string; items map[key]*meta; onChanged func(key) }`，广播通过注入 `onChanged` 回调解耦（store 不依赖 watch 包）
  - `NewStore(root string, onChanged func(key)) (*Store, error)`：`MkdirAll` 配置根目录，调用 `LoadAll`
  - `LoadAll()`：遍历 `configs/{app}/{env}.json` 两级目录；名称不合法的目录/文件跳过并告警；非法 JSON 文件跳过并告警；合法项注册 `Version = 1`、计算内容 hash
  - `Get(k key) (json.RawMessage, uint64, bool)`：读锁返回内容与版本的拷贝
  - `List() []Entry`：返回全部 `{app, env, version}` 供发现接口
  - `Put(app, env string, body []byte) (uint64, error)`：`validName` 校验 → `json.Unmarshal` 到 `map[string]any` 校验顶层 JSON 对象 → 同目录写临时文件（`os.CreateTemp(dir, "*.tmp")`）→ `os.Rename` 原子覆盖 → 版本 = 旧值 + 1（新建则 1）→ 更新内存 meta → 调用 `onChanged(key)` → 返回新版本；任一步失败文件与版本保持不变
  - `Reload(k key) (bool, error)`：读文件当前 mtime 与 hash；未变化返回 `false` 不动内存；非法 JSON 返回错误且保留旧版本；合法变化则版本 +1、更新内存、调用 `onChanged`
  - 设计决策：文件被外部删除时内存旧版本保留、继续服务（由 poller 告警）
  - Run and validate: `go build ./...`、`go vet ./...`
  - Ref: REQ-1, REQ-3, REQ-4

- [x] 4. 实现长轮询广播 watch.go
  - 创建 `go_projects/liteconf/internal/server/watch.go`
  - 定义 `type Broadcaster struct { mu sync.Mutex; keys map[key]*bc }`，其中 `type bc struct { mu sync.Mutex; ch chan struct{} }`
  - `Notify(k key)`：close-broadcast 惯用法——`close(b.ch)` 后换新 `make(chan struct{})`，唤醒所有等待者
  - `Wait(r *http.Request, k key, timeout time.Duration)`：select 三路——`<-ch`（版本变化）、`<-time.After(timeout)`（超时）、`<-r.Context().Done()`（客户端断开）
  - handler 将 `store.onChanged` 注入为 `Notify`；每 key 的 bc 懒创建
  - Run and validate: `go build ./...`
  - Ref: REQ-3, REQ-5

- [x] 5. 实现 HTTP API handler.go
  - 创建 `go_projects/liteconf/internal/server/handler.go`
  - `NewMux(st *store.Store, bc *Broadcaster) *http.ServeMux`，使用 Go 1.22 路由模式注册：
    - `GET /api/{app}/{env}`：返回 `{"code":"ok","data":{"content":{...},"version":N}}`；不存在返回 404 + `not_found`
    - `PUT /api/{app}/{env}`：body 即配置 JSON 对象，成功返回 `{"code":"ok","data":{"version":新版本}}`；非法名称 → 400 + `invalid_name`，非法 JSON/非顶层对象 → 400 + `invalid_json`
    - `GET /api/discovery`：返回 `{"code":"ok","data":{"apps":[{"app":"x","envs":[{"env":"dev","version":N}]}]}}`
    - `GET /api/watch/{app}/{env}?version=N`：长轮询；`version` 解析失败按 0 处理；当前版本 != N 时立即返回最新（版本已更新立即返回，首次订阅 N=0 亦立即返回）；相等则 `Broadcaster.Wait` 挂起，超时默认 30s（query `timeout` 可覆盖，上限 120s，单位秒）；唤醒/超时后返回与读取接口相同的响应
  - 所有路由入口统一 `validName` 校验 `app`/`env` 路径参数
  - Run and validate: `go build ./...`、`go vet ./...`
  - Ref: REQ-2, REQ-3, REQ-5

- [x] 6. 实现外部编辑检测 poller.go
  - 创建 `go_projects/liteconf/internal/server/poller.go`
  - `type Poller struct { st *store.Store; interval time.Duration }`，`Run(ctx context.Context)`：`time.Ticker` 循环（默认 5s，ctx 取消退出）
  - 每轮扫描配置根目录：新出现的合法 `{app}/{env}.json` 调用 `Reload` 注册（version 1）；已存在 key 先比对 `ModTime`，mtime 变化才算内容 hash 并调用 `Reload`
  - 文件消失：`slog` 告警并保留内存旧版本；`Reload` 返回非法 JSON 错误：`slog` 告警并保留旧版本继续服务
  - Run and validate: `go build ./...`
  - Ref: REQ-4

- [x] 7. 实现 server 入口 main.go
  - 创建 `go_projects/liteconf/cmd/liteconf-server/main.go`
  - flags：`-addr`（默认 `":8646"`）、`-root`（配置根目录）、`-poll`（检测间隔，默认 `5s`）
  - `-root` 默认值解析：`os.UserConfigDir()` 取 `%APPDATA%` → `filepath.Join(configDir, "language_projects", "liteconf", "configs")`；出错回退 `os.UserHomeDir()` + `~/.language_projects/liteconf/configs`
  - 日志：`slog.NewTextHandler` 写 `io.MultiWriter(os.Stderr, logFile)`，logFile 位于 `%APPDATA%\language_projects\liteconf\logs\liteconf-server.log`（`O_APPEND|O_CREATE|O_WRONLY`），目录不存在先 `MkdirAll` 完整目录链
  - 启动时打印警告：无鉴权、HTTP 明文，仅限内网/本机可信环境使用
  - `signal.NotifyContext` 优雅退出：`http.Server.Shutdown` + cancel poller ctx
  - Run and validate: `go build ./...`，然后 `go run ./cmd/liteconf-server` 手动确认启动日志与端口监听
  - Ref: REQ-10

- [x] 8. server 编译与静态检查
  - 在 `go_projects/liteconf/` 执行 `go build ./...`、`go vet ./...` 全绿
  - Run and validate: `go build ./...`、`go vet ./...`
  - Ref: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5, REQ-10

- [x] 9. 实现 SDK 初始化与读取（client.go + cache.go）
  - 创建 `go_projects/liteconf/client/client.go`、`go_projects/liteconf/client/cache.go`
  - `type Config struct { ServerURL, App, Env string; RequestTimeout time.Duration }`（`RequestTimeout` 零值默认 35s，须大于 server 端 30s 长轮询超时）
  - `New(cfg Config) (*Client, error)`：规范化 ServerURL（去掉尾部 `/`）→ 同步 `GET /api/{app}/{env}` 拉取 → 失败返回明确错误（message 含「请检查 server 地址与网络后重试」），不返回空配置伪装成功 → 解析 `data.content` 与 `data.version` 写入缓存
  - 缓存：`atomic.Pointer[map[string]any]` 存 copy-on-write 快照，读路径无锁；`swap(content map[string]any, version uint64)`
  - `Get(path string) (json.RawMessage, bool)`：path 按 `.` 切分逐级下钻 `map[string]any`，任一层非 map 或不存在返回 `false`（存在性标识，非静默零值）；空 path 返回整份配置
  - `Snapshot() map[string]any`：返回缓存浅拷贝（防调用方污染内部状态）
  - `Unmarshal(path string, v any) error`：`Get` 结果 `json.Unmarshal` 到调用方 struct；path 为空解码整份配置
  - `Version() uint64`：返回本地已知版本（供 poll.go 使用）
  - Run and validate: `go build ./...`
  - Ref: REQ-6, REQ-9

- [x] 10. 实现 OnChange 异步派发 callback.go
  - 创建 `go_projects/liteconf/client/callback.go`
  - 注册表 `slice []func(old, new map[string]any)` + `sync.Mutex`；`OnChange(fn func(old, new map[string]any))` 追加注册
  - `dispatch(old, new map[string]any)`：锁内拷贝回调快照，解锁后逐个 `go func() { defer func() { _ = recover() }(); fn(old, new) }()`——单回调 panic/阻塞不影响其他回调与主轮询循环；不保证回调间顺序
  - Run and validate: `go build ./...`
  - Ref: REQ-7

- [x] 11. 实现长轮询循环与退避重连 poll.go
  - 创建 `go_projects/liteconf/client/poll.go`
  - `run(ctx context.Context)`：循环体——`GET /api/watch/{app}/{env}?version=N`（server 端默认挂起 30s）→ 2xx 且版本变化：再 `GET /api/{app}/{env}` 拉最新 → `swap` 缓存 → `dispatch(old, new)` → 退避重置为 1s → 立即下一轮；版本未变（超时响应）直接下一轮
  - 失败处理：网络错误/非 2xx → `slog` 告警 → 指数退避（1s 起步、×2、上限 30s）+ 随机抖动后重试；期间 `Get`/`Snapshot` 继续返回最后缓存（无锁读不受影响）
  - ctx 取消即退出；`Close()` 用 `sync.Once` 保证幂等：cancel ctx + 等待 goroutine 退出
  - Run and validate: `go build ./...`、`go vet ./...`
  - Ref: REQ-7, REQ-8

- [x] 12. SDK 编译与静态检查
  - 在 `go_projects/liteconf/` 执行 `go build ./...`、`go vet ./...` 全绿
  - Run and validate: `go build ./...`、`go vet ./...`
  - Ref: REQ-6, REQ-7, REQ-8, REQ-9

- [x] 13. 端到端联调
  - 起服务：`go run ./cmd/liteconf-server -addr :8646 -root <临时目录>`（另开终端）
  - 写入：`curl.exe -X PUT http://localhost:8646/api/app1/dev -H "Content-Type: application/json" -d "{\"db\":{\"host\":\"127.0.0.1\"}}"` → 返回 `"version":1`
  - 读取：`curl.exe http://localhost:8646/api/app1/dev` → 返回内容与版本；`curl.exe http://localhost:8646/api/app1/nope` → `not_found`
  - 发现：`curl.exe http://localhost:8646/api/discovery`
  - 长轮询：终端 A `curl.exe "http://localhost:8646/api/watch/app1/dev?version=1"` 挂起 → 终端 B 再 PUT 一次 → A 立即返回新版本
  - 外部编辑：直接改 `<临时目录>/app1/dev.json` → 5 秒内 watch 侧感知新版本；改成非法 JSON → 旧版本仍可读、日志出现告警
  - SDK 联测：临时 `main` 中 `client.New` 后 `OnChange` 打印、`Get("db.host")` 取值，重复写入验证回调触发
  - Run and validate: 上述 curl.exe 命令序列 + `go run` 临时程序
  - Ref: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5, REQ-6, REQ-7

- [ ] 14. server 集成测试 [test]
  - 创建 `go_projects/liteconf/internal/server/server_test.go`
  - 用 `httptest.NewServer(NewMux(...))` 覆盖：启动加载已有目录 → PUT/GET/discovery 正常流 → not_found/invalid_name/invalid_json 错误流 → 长轮询版本已更新立即返回、挂起后写入即唤醒、超时返回当前版本 → 注入 `onChanged` 验证 Put 触发广播 → `Reload` 对外部修改/非法 JSON/文件删除的三种行为
  - Run and validate: `go test ./internal/server/`
  - Ref: REQ-1, REQ-2, REQ-3, REQ-4, REQ-5

- [ ] 15. client 单元测试 [test]
  - 创建 `go_projects/liteconf/client/client_test.go`
  - 用 `httptest` 假 server 覆盖：`New` 成功初始化与失败报错（不含空配置成功）→ `Get` 点路径命中/未命中/中间层非 map → `Snapshot` 拷贝隔离 → `Unmarshal` 到 struct 与错误返回 → OnChange 多回调异步触发、单回调 panic 不影响其他回调 → 断连后退避重试、server 恢复后自动追上最新版本
  - Run and validate: `go test ./client/`，最终 `go test ./...` 全绿
  - Ref: REQ-6, REQ-7, REQ-8, REQ-9
