# Bug Fix Document

## Summary

`agyquota --agy` 调用本机 `agy -p "/usage" --output-format json` 时，Google 配额接口短暂返回 `EOF`，`agy` 以非零退出码结束；agyquota 当前只执行一次命令，导致本可恢复的瞬态网络/上游故障直接暴露为 `agy_execute_failed`，查询失败。

## Reproduction

前置条件：

- 已安装并可执行 `C:\Users\29580\AppData\Local\agy\bin\agy.exe`；
- `agy` 已登录，且独立执行命令通常能够返回配额 JSON。

触发步骤：

1. 在 PowerShell 中执行 `.\agyquota.exe --agy`；
2. 当 `agy` 调用 `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` 时遇到瞬态连接中断，观察到：
   `error: /usage failed: retrieving quota summary: Post "https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary": EOF`；
3. 当前版本立即输出 `agy_execute_failed` 并退出，不会在同一次查询中重试。
4. 稍后独立执行 `agy -p "/usage" --output-format json` 可以成功返回 `status=SUCCESS` 和配额数据，证明该现象不是命令缺失或固定的响应解析错误。

## Root Cause

根因由外部瞬态故障与调用方缺少恢复策略共同造成：

1. `internal/agapi/client.go` 的 `Client.FetchUsage` 每次只启动一个 `agy` 进程；当进程以非零退出码结束时，直接把 stderr 包装为错误返回。
2. `agy` 的 stderr 已明确表明失败发生在 `retrieveUserQuotaSummary` 的 HTTP `POST`，属于可能恢复的网络/上游 `EOF`，而不是 `agy` 未安装、命令参数错误或响应格式不可解析。
3. `internal/service/service.go` 统一把该错误映射为 `agy_execute_failed`，当前建议文案主要要求确认安装并手工执行命令，无法体现“命令存在但本次上游请求暂时失败”的诊断，也没有给底层调用提供重试机会。

## Impact

- 受影响：所有通过 `agy` 数据源取数的入口，包括人读 CLI、`--json`、`--raw`、daemon API 及 MCP；它们最终都经过 `internal/agapi.Client`。
- 不受影响：`--zed` 数据源及其凭据、HTTP 请求和缓存逻辑。
- 当前风险：瞬态 `EOF` 会造成整次查询失败；若盲目重试所有错误，又可能掩盖认证失败、命令缺失、参数错误或永久性响应变化，因此修复必须限制重试条件和次数。

## Fix Acceptance Criteria

### AC-1

WHEN `agy` 因 `retrieveUserQuotaSummary` 请求出现可恢复的网络/上游瞬态错误（至少覆盖报告中的 `EOF`），THEN `agyquota --agy` 在同一次查询中执行有界重试，并在后续尝试成功时返回正常配额结果，不要求用户手工重复运行命令。

### AC-2

WHEN 所有允许的重试尝试仍失败，THEN 程序返回既有 `agy_execute_failed` 错误码，保留最后一次底层失败原因，并给出“检查网络/代理并稍后重试”的准确建议；不得把已确认存在的 `agy` 命令误报为未安装。

### AC-3

WHEN 失败属于命令不存在、进程启动失败、参数/权限错误、认证失败或输出 JSON/业务状态不可解析等非瞬态错误，THEN 修复不得因通用重试而重复执行该命令，保持原有错误路径和错误码语义。

### AC-4

WHEN 查询上下文被取消或达到现有超时时限，THEN 当前尝试及后续重试立即停止，既有进程树回收保证继续生效，不残留 `agy` 或其子进程。

### AC-5

WHEN 通过 `--zed` 查询或调用既有 Zed 相关接口时，THEN 修复不改变其请求、缓存、错误处理和输出行为。

### AC-6

WHEN 通过人读 CLI、`--json`、`--raw`、daemon API 或 MCP 调用 `agy` 数据源时，THEN 成功响应、原始响应、错误包络、退出码和 stdout/stderr 分流契约保持兼容；重试诊断只能出现在既有进度/诊断通道，不污染 JSON 数据输出。




## Fix Approach

在 `internal/agapi` 内把一次 `agy` 执行与重试编排分开，选择小范围、有界、失败即停的方案：

1. 从 `Client.FetchUsage` 抽取一次执行逻辑，保留现有 stdout/stderr 收集、退出码判断、JSON 校验和进程回收行为。
2. 外层最多执行 3 次总尝试，首次失败后分别等待 250ms、750ms。
3. 只有 stderr 同时包含 `retrieve user quota summary` 和已知瞬态标识（至少覆盖 `EOF`，并兼容连接中断、超时、`429/502/503/504`）时才重试。
4. 命令缺失、进程启动失败、认证/参数错误、JSON 解析失败和非成功业务状态不重试。
5. 等待重试期间监听 `ctx.Done()`；取消或超时立即结束，不启动新进程。每次尝试返回前沿用现有进程树回收逻辑。
6. 重试耗尽时返回最后一次底层错误，保留 `agy_execute_failed` 错误码；将 service 建议改为同时提示检查 `agy` 可执行性与网络/代理，而不是只提示安装命令。
7. 不修改 `--zed`、daemon、`agy_silent.exe`、PE Subsystem 和 Windows 进程启动逻辑。

## Tasks

- [x] 1. 为 `agy` 配额查询增加瞬态错误分类与有界重试
  - Files: `go_projects/agyquota/internal/agapi/client.go`
  - 实现细节：抽取单次执行函数；增加最多 3 次总尝试、250ms/750ms 等待、stderr 白名单分类、重试诊断日志和上下文取消检查；失败后返回最后一次错误；不得改变已有进程回收和成功 JSON 解析流程。
  - Verify: `go build ./...` 与 `go vet ./...`；预期无编译或静态检查错误，已有 `agy` 成功响应结构不变。
  - Ref: AC-1、AC-3、AC-4、AC-6

- [x] 2. 修正 agy 执行失败建议，保持业务错误契约兼容
  - Files: `go_projects/agyquota/internal/service/service.go`
  - 实现细节：保持 `agy_execute_failed` 错误码、错误主消息和 Zed 分支不变；建议同时覆盖命令可执行性、网络/代理和稍后重试，避免把已启动成功但上游暂时失败的 `agy` 误报为未安装。
  - Verify: `go build ./...` 与 `go vet ./...`；预期 agy/zed 两条服务路径均可编译，错误包络字段保持原契约。
  - Ref: AC-2、AC-5、AC-6

- [ ] 3. 使用真实命令确认瞬态失败后的恢复行为
  - Files: `go_projects/agyquota/internal/agapi/client.go`、`go_projects/agyquota/internal/service/service.go`
  - 实现细节：构建后运行 `.\agyquota.exe --agy`；确认正常查询仍返回配额，重试诊断只出现在 stderr；若再次遇到报告中的 `retrieveUserQuotaSummary ... EOF`，确认后续尝试能够成功或最终保留最后一次底层错误。
  - Verify: `go build ./...` 后执行 `.\agyquota.exe --agy`；预期成功时 stdout 保持原格式，失败时错误码仍为 `agy_execute_failed` 且建议包含网络/代理重试指引。
  - Ref: AC-1、AC-2、AC-6
## Implementation Notes

- Task 1、Task 2 已完成：代码增加了 agy 瞬态配额错误的有界重试，并修正了失败建议文案。
- Task 3 暂保持未勾选：按默认执行规则未主动运行 `go build`、`go vet` 或真实 `agyquota --agy` 验证命令；该验证可在用户明确要求执行测试/验收时补做。