# Requirements Document

## Summary

agyquota 现为按 v1《CLI 工具开发标准》构建的进程内分层 CLI：`internal/service`（业务核心）被 `internal/cli` 与 `internal/mcp` 两个壳直接调用，单进程即完成全部功能。本次按 2026-09-25 发布的 [v2《CLI 工具开发标准（daemon 架构）》](<../../../CLI 工具开发标准 v2.md>) 做全面 daemon 化改造：**Service 只编译进 daemon，HTTP+JSON API 成为唯一业务契约，CLI 与 MCP 退化为薄客户端**；单二进制双角色（`agyquota serve` + 客户端）、地址发现与生产构建自动拉起、buildID 握手、git tag 发布流。

改造以「外部可感知行为不变」为前提：人读输出、JSON 包络、业务错误码、退出码、MCP 工具与 `schema` 目录、数据目录约定全部保持；内部则把业务逻辑收口到唯一 daemon 进程。契约细节（JSON 包络、错误、`--schema`、MCP 协议核对、验收矩阵）继续按 v1 执行。

显式假设（请求未明说，按 v2 推断；供设计评审兜底）：

- A1：新增 `agyquota stop` 子命令用于停止 daemon（v2 错误文案引用了 `mytool stop`）。默认端口、地址文件名、HTTP 路径等具体值留给 design.md 定义。
- A2：`serve` 保留前台开发形态（终端日志、Ctrl+C 退出）；Windows 生产自动拉起用 `DETACHED_PROCESS`，全程不产生可见窗口与焦点干扰（延续 01-window-focus-steal 的既有成果）。
- A3：GUI 不在本次范围（当前无 GUI 实现）。
- A4：不改动数据源抓取协议本身（agy 静默 runner/凭据路径、zed 直连、token 缓存与降级抖动校准），只做分层与进程模型搬迁。

## Functional Requirements

### FR-1 daemon 与单二进制双角色

- `agyquota serve` 启动唯一业务进程 daemon；开发形态为前台运行、日志输出在当前终端、Ctrl+C 优雅退出。
- daemon 生命周期：自动拉起的 daemon 在无在途请求且空闲超过 30 分钟后优雅退出并清理/失效地址文件（v2.1 空闲策略）；前台 `agyquota serve` 不设空闲退出，由操作者 Ctrl+C 管理。生产环境其余终止途径：显式 `agyquota stop`、OS 重启/注销、进程被手动结束、异常崩溃；自动拉起的 daemon 为独立 detached 进程，不随启动它的终端关闭而退出。请求级取消/超时只终止该请求的在途操作（含 agy 子进程），不终止 daemon，且空闲计时不因在途长查询触发退出；例外：同源请求被 singleflight 合并期间，取消 leader 会终止共享取数，joined 请求随之失败（本地单用户场景可接受）。
- 一个构建产物（`agyquota.exe`）两种角色：`serve` 为服务端，其余子命令（`quota`、`mcp`、`schema`、`stop`、`--help`、`--version`）为客户端或桥。
- 依赖方向硬约束：`internal/cli` 与 `internal/mcp` 不得 import `internal/service`（壳内只有 API client / DTO）；`internal/service` 仅被 daemon 组装路径引用。可用 `go list -deps` 验证。

### FR-2 HTTP+JSON 唯一契约

- daemon 在回环地址监听 HTTP；业务 API 覆盖现有用例：配额查询（`source=agy|zed`、`tokenFile`）与原始响应获取（`--raw` 对应）。
- 响应沿用 v1 包络：成功 `{"ok":true,"data":…}`；失败 `{"ok":false,"error":{"code","message","suggestions"?}}`。原 5 个业务错误码（`source_required`、`agy_not_found`、`agy_execute_failed`、`zed_execute_failed`、`response_parse_failed`）语义与触发条件不变；新增 daemon 连接类稳定错误码（连通失败、自动拉起失败、buildID 不一致等）。
- 查询进度/诊断经 SSE（或等价流式通道）从 daemon 回传；CLI 转写 stderr，MCP 桥保持静默或按协议有界输出，stdout 数据流不被污染。
- 默认仅绑定 `127.0.0.1`，不带鉴权（本地信任模型，对标 ollama/docker）；不提供远程访问形态。

### FR-3 地址发现与自动拉起

- 地址发现优先级固定为：`--host` 参数 → `AGYQUOTA_HOST` 环境变量 → 地址文件 → 内置默认端口。
- 生产构建（buildID 的 describe 部分为干净 tag，如 `v1.2.3`）且未显式指定地址：连不上时用自身 exe 路径自动 spawn daemon（Windows `DETACHED_PROCESS` 脱离父子关系、无窗口），有界等待就绪后重试请求；自动拉起须防止并发重复启动（锁文件/地址文件互斥，发现已有可用实例或端口被占用时放弃拉起、直接改连）。
- 显式指定地址（`--host`/环境变量）连不上时：报错，**绝不本地拉起**。
- 开发构建（describe 带 `-g<hash>` 或 `-dirty`）：任意情况下不自动拉起，报错提示先运行 `agyquota serve`（开发者走双终端工作流）。
- daemon 启动时将地址与 buildID/pid 等校验信息写入地址文件；地址文件位于项目数据目录 `%APPDATA%\language_projects\agyquota\`（取不到 APPDATA 时回退 `~/.language_projects/agyquota/`，写前创建完整目录链）；须能识别并处理陈旧地址文件（daemon 已死/端口被占）。

### FR-4 buildID 构建指纹握手

- 构建时经 `-ldflags` 注入 buildID = `git describe --tags --always --dirty` + 时间戳；`--version` 输出 describe 结果。
- 客户端连上 daemon 后核对双方 buildID：相等放行；不等返回明确错误（含双方指纹与「重启后重试」提示），用于捕获「改了协议只重启一边」「升级后旧 daemon 在跑」。

### FR-5 薄客户端改造

- CLI 职责收敛为三段：参数解析 → HTTP 调用 → 输出渲染；业务规则、数据源调用、缓存与错误分类全部在 daemon 内。
- `agyquota mcp` 成为 stdio(MCP) ↔ HTTP 桥：继续提供 `agyquota.quota.get`（`source`/`tokenFile` 参数与输出结构不变），业务失败仍映射为 `isError` 工具结果；桥不 import service。
- `schema`、`--help`、`--version` 保持离线自描述：不启动/连接 daemon，不触发网络与业务文件 I/O；`schema` 目录与实际 MCP 注册同源。
- 新增 `stop`：请求 daemon 优雅退出并清理地址文件（推断项 A1）。

### FR-6 业务行为与数据保持

- 两条数据源语义与 0.2.3 一致：`--agy` 走本地 agy（保留静默 runner 与进程树回收机制）、`--zed` 走 Zed 凭据 + Google 直连 + 约 58 分钟 token 缓存 + 降级抖动校准；`--raw`、`--token-file` 行为不变。
- 运行数据只落 `%APPDATA%\language_projects\agyquota\`（缓存、地址文件、日志等）；Zed 凭据目录只读，唯一例外是既有的历史误写缓存清理（固定文件名精确匹配，不触碰其他文件）。
- daemon 内并发请求安全：token 刷新/agy 查询单飞（single-flight），不重复 spawn 进程、不写坏缓存；关闭时释放句柄、终止在途 agy 进程。

### FR-7 发布流

- 引入 git tag 驱动的发布流：annotated tag（形态 `agyquota/vX.Y.Z`，父仓多项目共存避免冲突）→ 干净检出构建；版本与 buildID 同一个 describe 来源（buildID 附时间戳用于区分 dirty 多次构建），四用（开发指纹、握手凭据、`--version`、升级检测）。
- 构建脚本支持注入 buildID；本地发布构建对 `-dirty` 直接拒绝。

### FR-8 文档同步

- 更新 `go_projects/agyquota/README.md` 与父仓库镜像文档：`serve`/`stop`、端口与地址文件、环境变量、开发双终端工作流、生产自动拉起与兼容说明、数据目录清单。

## Non-Functional Requirements

- **兼容性**：原调用方式（`agyquota --agy|--zed`、`quota`、`mcp`、`schema`、`--json`、`--raw`、退出码 0/1/2）全部保持可用；新增 `--host` 为增量参数。跨平台可交叉编译，Windows 专属逻辑（detach、agy 静默 runner）保持 build tag 隔离，非 Windows 保持可构建。
- **安全**：daemon 默认只监听回环；不新增网络暴露面；凭据内容不落日志、不进 JSON 信封。
- **时效**：自动拉起为有界等待（超时给出可操作错误）；单次查询端到端耗时与 0.2.3 同量级（agy 执行耗时主导）；daemon 存活期间的重复查询不引入额外冷启动，空闲退出后的下一次查询包含一次有界拉起开销。
- **数据目录**：daemon 全部自产文件（地址文件、锁、日志、缓存）遵守仓库强约束，禁止跟随外部程序目录。
- **可验证**：验证以 `go build ./...`、`go vet ./...`、`go test ./...` 与真实入口冒烟为主。

## Acceptance Criteria

### AC-1（双角色与依赖方向）

`go build ./...` 产出单个 `agyquota.exe`；`agyquota serve` 前台启动并在回环地址监听、写出地址文件；`go list -deps ./internal/cli` 与 `./internal/mcp` 的结果中不含 `agyquota/internal/service`。

### AC-2（生产自动拉起）

在无未提交改动的检出上，用临时 annotated tag 模拟生产构建（`git tag -a agyquota/v0.0.0 -m test && .\scripts\build.ps1 && git tag -d agyquota/v0.0.0`，buildID 由脚本经 `git describe --tags --always --dirty` + ldflags 注入）：未指定地址时执行 `agyquota --agy --json`，客户端自动拉起 daemon、等待就绪并返回与 0.2.3 结构一致的 JSON 信封；实测无窗口/焦点干扰、无多余控制台进程。

### AC-3（开发构建不拉起）

无 tag 构建下执行 `agyquota --agy --json`：退出码 1，错误信息提示先运行 `agyquota serve`，系统中不出现 daemon 进程。

### AC-4（显式地址语义）

`--host`/`AGYQUOTA_HOST` 指向不存在的实例时：退出码 1、错误码明确，且不本地拉起任何 daemon 进程。

### AC-5（buildID 握手）

daemon 运行中替换为另一 buildID 的客户端（旧/新构建）：请求被拒绝，错误信息包含双方 buildID 与重启提示；`agyquota stop` 后重启 daemon 再试成功。

### AC-6（CLI 契约回归）

同账号下 `agyquota --agy|--zed` 的人读输出、`--json` 信封、`--raw` 输出、退出码（0/1/2）与 0.2.3 一致；`source_required`、`agy_not_found`、`agy_execute_failed`、`zed_execute_failed`、`response_parse_failed` 的触发条件与内容不变。

### AC-7（MCP 与 schema）

`agyquota mcp` 真实进程启动可被客户端完成初始化与 `tools/list`（发现 `agyquota.quota.get`），成功调用与业务失败 `isError` 行为与 0.2.3 一致；`agyquota schema` 与 `tools/list` 同源、除版本号外字段与 0.2.3 对照一致，且在无 daemon 环境下离线导出成功。

### AC-8（离线自描述）

`--help`、`--version`、`schema` 执行后不出现 daemon 进程、不发起业务网络请求（agy/zed 均不被触发）。

### AC-9（数据与只读边界）

运行后新增/修改的文件只出现在 `%APPDATA%\language_projects\agyquota\`；Zed 凭据目录内无任何本工具写入；地址文件、缓存、日志均可按文档清单核对。

### AC-10（并发与收尾）

并发发起两个查询：agy 进程不重复 spawn、token 缓存不损坏、两请求结果正确；`agyquota stop` 后无残留 daemon 与 agy 后代进程、地址文件按设计处理（删除或标记失效）。

### AC-11（发布流）

在无未提交改动的检出上打临时 annotated tag（`agyquota/v0.0.0`）后以 `.\scripts\build.ps1` 构建：`--version` 输出 describe 本身、握手 buildID 的 describe 段为干净 tag 形态（其后附时间戳，二者不要求逐字相等）；带未提交改动（describe 含 `-dirty`）时 `.\scripts\build.ps1 -Release` 拒绝。

### AC-12（构建与检查）

`go build ./...`、`go vet ./...`、`go test ./...` 通过；`GOOS=linux go build ./...` 交叉编译通过。

### AC-13（空闲退出、取消与自愈）

自动拉起的 daemon 在无在途请求且空闲超过 30 分钟后自动退出并清理/失效地址文件；前台 `agyquota serve` 不因空闲退出。单次 `--agy` 查询在执行中取消/超时后，agy 子进程被回收而 daemon 仍在；daemon 空闲退出或被手动结束后，生产构建下一次调用能完成「识别失效地址 → 自动重新拉起 → 查询成功」，开发构建则以「先运行 `agyquota serve`」报错。

## Out of Scope

- GUI / Web 控制台实现（无现存需求）。
- gRPC、远程多机访问、鉴权与 API 版本协商（v2 暂缓项，由 buildID 相等检查替代）。
- Windows 服务注册/开机自启。
- 用户可见的 `--data-root` 数据隔离与产品级测试框架/自起 daemon 能力（v2 暂缓）；`go test` 内部测试接缝（临时数据目录、临时端口）不属产品能力，不受此限。
- 数据源协议本身的改造（agy 抓取、zed 直连与缓存策略除分层搬迁外不动）。
