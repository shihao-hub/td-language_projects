# Requirements Document

> spec 编号：03 ｜ 项目：`go_projects/clictl` ｜ 日期：2026-10-04

## Summary

clictl 是 Windows 单文件 CLI 工具注册器/启动器，目前只有终端形态，对人类操作不够直观。本项目为其新增 `clictl gui` 子命令：以 `go:embed` 嵌入手写 html/css/js，启动仅绑定 127.0.0.1 的本地 HTTP server 并自动拉起默认浏览器，网页端覆盖四类能力——工具列表与运行状态、后台启停、注册管理（add/rm/set）、非交互捕获运行（看输出）。全部业务逻辑复用现有 `internal/service` 层（clictl 本身即按 CLI/GUI 分离思想设计，本 GUI 是该路线的第一个网页壳），零新增第三方依赖，单文件 exe 特性保持。目标是先用最小成本验证「clictl 值得一个 GUI」，成效好再谈二期（tooldeck 独立前端、MCP 转发等）。

## Functional Requirements

- **FR-1 `clictl gui` 子命令**：`clictl gui [--port N] [--no-open]` 启动 GUI server。默认端口 17630，仅绑定 `127.0.0.1`；启动成功后用系统默认浏览器打开 GUI 页面（Windows 走 `rundll32 url.dll,FileProtocolHandler`）；`--no-open` 跳过自动打开；server 运行日志全部走 stderr，Ctrl+C 优雅退出。
- **FR-2 端口策略**：默认端口已被占用时，先探测是否为已有 clictl gui 实例（探测 `GET /api/version`）——是则直接用浏览器打开旧实例地址后本进程退出（不重复起 server）；否则回退绑定随机可用端口并在 stderr 打印实际地址。`--port 0` 表示直接随机端口。
- **FR-3 工具列表（核心）**：页面以卡片形式展示全部注册工具：name、desc、path、status（active/invalid 徽标）、后台运行状态（运行中徽标 + PIDs）、launch_count、last_launch、meta（source/tags）；支持关键字过滤（匹配 name/desc/path）；手动刷新按钮、每次操作后自动刷新、10s 轻轮询保持运行状态新鲜。
- **FR-4 工具详情**：查看单工具 info——最近 10 条启动记录（时间/耗时/退出码）、累计启动次数与总耗时、当前后台运行状态。
- **FR-5 启停操作（核心）**：对单个工具执行 start（可选透传参数）与 stop；操作结果即时反馈，列表运行状态随之刷新。
- **FR-6 捕获运行**：输入透传参数（每行一个）与超时毫秒数后执行非交互捕获运行：stdin 关闭、服务端收集 stdout/stderr（各 1 MiB 上限、超限截断标记）、展示退出码与耗时；超时或用户点「取消」时终止整棵进程树；交互式程序不适用（无输入能力），UI 需提示此限制。
- **FR-7 注册管理**：add（path 必填 + name/desc/source/tags 可选）、rm（需二次确认，提示级联删除启动记录）、set（编辑 meta，整体替换语义）；路径为手输/粘贴的绝对路径（浏览器无法取得本地文件完整路径，文件选择框不适用）。
- **FR-8 API 与 CLI/MCP 同源**：`/api/*` 返回与 CLI 管理命令一致的 JSON 包络 `{"ok":true,"data":...}` / `{"ok":false,"error":{"code","message","suggestions"?}}`；错误码复用 service 层现有 code（not_found、file_not_found、meta_unknown_key、conflict 等），前端按 ok 分支渲染错误 toast。

## Non-Functional Requirements

- **零新增依赖**：仅用 Go 标准库（net/http、embed）+ 现有依赖；前端纯手写原生 html/css/js，无框架、无构建步骤、无 CDN。
- **单文件保持**：静态资源经 `go:embed` 打进 exe；`scripts/build.py` 构建流程不变。
- **安全基线**：仅绑定回环地址；`/api/*` 校验进程启动时生成的随机 token 请求头（`X-Clictl-Token`，token 注入首页），并校验 Host 头——防御本地 drive-by CSRF 与 DNS rebinding（rm/stop/run 属破坏性操作，不能裸奔）。
- **UI 风格**：浅色亮堂、绿主色、圆角卡片（参照 CC Switch）；信息密度优先，不要暗色终端风与装饰性 gimmick。
- **并发模型**：server 常驻进程复用一个 service 实例（与 `clictl mcp` 同模式）；SQLite WAL + busy_timeout 已保证多进程并发安全；捕获运行期间不长持数据库连接（记账为两条短事务）。

## Acceptance Criteria

### AC-1
WHEN 执行 `clictl gui` THEN server 启动且默认浏览器自动打开 GUI 页面，页面展示的工具列表与 `clictl list` 数据一致（含 status、launch_count、last_launch）。

### AC-2
WHEN 在页面点击某工具「启动」（可填参数）THEN 行为等价 `clictl start <名> [args...]`：后台实例拉起，列表运行徽标刷新并显示 PID；对已注册失效文件返回与 CLI 一致的错误。

### AC-3
WHEN 在页面点击某运行中工具「停止」THEN 行为等价 `clictl stop <名>`：活实例被树杀并闭环记录，运行徽标消失。

### AC-4
WHEN 在页面对非交互工具发起捕获运行 THEN 完成后展示 stdout/stderr/退出码/耗时（超限显示截断标记），且 `clictl info <名>` 能看到本次启动记录；WHEN 超时或点「取消」THEN 进程树被整棵终止，结果带 timed_out/cancelled 标记。

### AC-5
WHEN 在页面注册新 exe（合法路径）THEN `clictl list` 立即可见；WHEN rm 确认后 THEN 工具消失且其 launches 级联删除；WHEN set 修改 meta THEN `clictl info` 反映新值（整体替换语义与 CLI 一致）。

### AC-6
WHEN 输入错误（路径不存在、未注册名、meta 超限/非法等）THEN 页面 toast 展示与 CLI 同 code 的业务错误信息，server 不崩溃、后续请求正常。

### AC-7
WHEN 从其他网页向 `http://127.0.0.1:17630/api/*` 发起跨站请求（无 token 头）THEN 返回 403 被拒；WHEN Host 头非 127.0.0.1/localhost THEN 同样拒绝。

### AC-8
WHEN 默认端口上已有 clictl gui 实例时再次执行 `clictl gui` THEN 新进程探测到旧实例、拉起浏览器指向旧地址后自身退出（exit 0），不产生第二个 server。

## Out of Scope

- `cp`、`completion` 管理不入 GUI（继续走 CLI）；`mcp`/`schema` 入口不变。
- 交互式程序的实时终端透传（GUI 的 run 仅捕获式非交互，语义对齐 `clictl.run` MCP 工具）。
- WebSocket/SSE 实时推送（以 10s 轮询替代）。
- GUI 内调用其他工具的 MCP 转发（tooldeck 完全体，二期再议）。
- WebView 独立窗口打包（浏览器形态足以验证一期成效）。
- 新增自动化测试（现有 `go test ./...` 保持通过即可；验证以构建 + 手工冒烟为准）。
