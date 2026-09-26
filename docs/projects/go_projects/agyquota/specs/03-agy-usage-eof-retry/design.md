# Design Document

## Overview

在不改变 `agy` 官方 CLI 调用路线、不触碰 `--zed` 和静默进程方案的前提下，为 `agy -p "/usage" --output-format json` 增加**仅针对已识别瞬态配额请求失败的有界重试**。

重试逻辑放在 `internal/agapi` 的单次 `agy` 进程调用之上，使 CLI、`--json`、`--raw`、daemon API 和 MCP 自动共享同一行为；业务错误码继续由 `internal/service` 统一映射，仍使用 `agy_execute_failed`。

## Context

当前调用链为：

```text
CLI / MCP
  -> internal/client（daemon HTTP 客户端）
  -> internal/daemon
  -> internal/service.Service
  -> internal/agapi.Client.FetchUsage
  -> startAgyProcess
  -> agy -p /usage --output-format json
```

`Client.FetchUsage` 当前把一次进程执行、stdout/stderr 收集、退出码判断和 JSON 外层校验放在同一个函数中；`agy` 非零退出时立即返回错误。报告中的错误发生在 `retrieveUserQuotaSummary` HTTP 请求，stderr 同时包含配额接口标识和 `EOF`，而后续再次运行能够成功，因此适合在 `internal/agapi` 做失败分类与重试。

本设计明确不处理另一个独立问题：`agy_silent.exe` 的生成、PE Subsystem、Windows 窗口/焦点、daemon 启停和进程启动回退策略均不在本次范围内。

## Goals and Non-Goals

### Goals

- 对报告中的 `retrieveUserQuotaSummary ... EOF` 在同一次查询内自动恢复。
- 只重试可识别的上游/网络瞬态错误，不重试命令缺失、启动失败、认证失败、参数错误、解析失败等永久性错误。
- 保留现有 `agy_execute_failed` 错误码、错误包络、退出码和 stdout/stderr 分流。
- 尊重现有 `context.Context` 取消和超时，重试等待不得阻塞到上下文结束之后。
- 让所有 agy 入口共享同一重试逻辑；不改变 `--zed`。
- 保留可测试的纯错误分类和重试调度接缝。

### Non-Goals

- 不改为 Google API 直连，不读取或新增 agy 凭据缓存。
- 不对所有非零退出码进行通用重试。
- 不重试 `--zed` 的 HTTP 请求。
- 不修改 `agy_silent.exe`、PE 补丁、Windows `CreateProcess` 标志或 daemon 架构。
- 不把上一次成功配额作为本次失败时的伪成功结果。

## Detailed Design

### 1. `internal/agapi/client.go`：拆分单次执行与重试编排

- `UPDATED` `go_projects/agyquota/internal/agapi/client.go`
    - **Purpose**：保留现有 agy 进程执行和响应校验语义，在外层增加受控重试。
    - **Changes**：
        1. 将当前 `FetchUsage` 的一次进程执行主体抽取为私有 `fetchUsageOnce(ctx)`；该方法负责调用现有 `startAgyProcess`、并发排空 stdout/stderr、等待退出、回收进程树、判断退出码、解析外层 JSON 以及校验 `status`。
        2. `FetchUsage` 只负责调用 `fetchUsageOnce` 并执行重试编排。固定最多 **3 次总尝试**（首次执行 + 2 次重试）；两次重试前分别等待 **250ms**、**750ms**。
        3. 每次重试等待使用 `time.NewTimer` 和 `select` 同时监听 timer 与 `ctx.Done()`；上下文取消时立即停止，不启动下一次 `agy`。
        4. 每次尝试结束后先完成现有 `shutdown` 和管道排空，再进入等待，禁止并发保留多个 `agy` 进程。
        5. 增加私有结构化执行错误，例如 `agyExecutionError`，记录底层错误文本及 `retryable` 标志；仅将进程非零退出且 stderr 命中瞬态分类的错误标记为可重试，进程启动失败、等待失败、上下文取消、JSON 解析失败和非成功业务状态均不可重试。
        6. 瞬态分类采用大小写不敏感的白名单规则：stderr 必须包含 `retrieve user quota summary`（或去空格后的等价文本），并且还要包含至少一个网络瞬态标识：`EOF`、`connection reset`、`connection refused`、`broken pipe`、`timeout`、`temporarily unavailable`、HTTP `429/502/503/504`。只满足单个通用词（例如仅有 `EOF`）不得重试，避免误重试无关错误。
        7. 所有尝试失败后返回最后一次尝试的底层错误；不返回早期错误覆盖最终原因，也不伪造成功数据。
        8. 通过既有 `Logf` 输出重试诊断，例如“第 1 次尝试失败，检测为配额接口瞬态错误，250ms 后重试”。日志只能进入已有进度/诊断通道，不写 stdout。
    - **Complexity**：Medium

### 2. `internal/service/service.go`：修正 agy 错误建议

- `UPDATED` `go_projects/agyquota/internal/service/service.go`
    - **Purpose**：让重试耗尽后的用户建议同时覆盖安装问题与网络/上游瞬态问题，避免把已成功启动的 `agy` 误导为“未安装”。
    - **Changes**：
        - 保持错误码 `api.ErrAgyExecute` 和错误主消息结构不变；将建议改为同时包含“确认 `agy` 可执行”和“检查网络/代理、稍后重试”两部分。
        - 不在 service 层重复实现瞬态分类，也不根据历史缓存生成成功响应。
    - **Complexity**：Low

### 3. 重试接缝与单元验证

- `CREATED` `go_projects/agyquota/internal/agapi/client_test.go`
    - **Purpose**：验证错误分类和重试次数，不依赖真实 Google 网络或本机登录状态。
    - **Changes**：
        - 为瞬态 stderr、认证失败、命令启动失败、仅有通用 `EOF`、解析失败分别建立表驱动断言。
        - 通过抽取的重试调度接缝注入 fake attempt，验证：首次失败后成功时总执行次数为 2；三次瞬态失败时总次数为 3 且返回最后错误；非瞬态失败时总次数为 1；上下文取消时不开始下一次尝试。
        - 验证重试等待可被测试上下文/短延迟接缝控制，生产常量仍固定为 250ms/750ms。
    - **Complexity**：Medium

- `CREATED` `go_projects/agyquota/internal/service/service_test.go`
    - **Purpose**：确认 agy 业务错误仍为 `agy_execute_failed`，建议文案包含网络/代理重试指引，且不改变 Zed 错误码。
    - **Changes**：使用现有 `Service.Fetcher` 接缝注入错误，验证错误映射和建议字段。
    - **Complexity**：Low

### 4. 错误处理矩阵

| 场景 | 是否重试 | 本次尝试动作 | 最终调用方结果 |
|---|---:|---|---|
| `retrieve user quota summary` + `EOF`/连接中断/502/503 等白名单标识 | 是，最多 2 次 | 回收当前进程，按 250ms/750ms 等待后重新启动 agy | 后续成功则正常返回；全部失败则返回最后一次 `agy_execute_failed` |
| `agy` 不存在、路径不可执行、`CreateProcess` 失败 | 否 | 保持当前错误路径 | 立即返回 `agy_execute_failed`，不重复拉起 |
| 参数、权限、认证失败 | 否 | 保持当前错误路径 | 立即返回 `agy_execute_failed` |
| 进程成功退出但 JSON 无效或 `status` 非成功 | 否 | 保持当前解析/业务状态错误 | 立即按现有 agy 取数错误路径返回 `agy_execute_failed` |
| 当前查询上下文取消/超时 | 否 | 终止当前进程并释放句柄 | 立即返回上下文错误，不进入下一轮 |
| `--zed` 查询 | 不适用 | 不触碰 Zed 路径 | 维持现有行为 |

### Module Collaboration and Data Flow

1. `internal/client` 和 `internal/mcp` 不感知重试细节，只通过既有 daemon API 获取最终结果或错误包络。
2. `internal/daemon` 对每个 HTTP/SSE 请求继续调用 `Service.GetQuota` 或 `Service.FetchRaw`；重试发生在 service 调用的 `agapi.FetchUsage` 内部。
3. 同源并发仍由 `Service` 现有 `singleflight` 合并；只有 leader 的 agy 调用执行重试，joined 请求共享最终成功结果或最终错误，不会为每个请求各自重试。
4. 每一轮 retry 都是新的 `startAgyProcess`，但上一轮在返回前已经执行完整的 `shutdown`，因此不存在多轮进程并存或句柄累积。
5. 成功 JSON 的解析和归一化路径不变；`--raw` 只返回成功尝试的原始 JSON，不附加诊断文本。

### External Inputs and Invariants

- **上下文**：唯一外部控制输入；必须遵守取消和截止时间，不能在 `ctx.Done()` 后创建新进程。
- **agy stderr**：非结构化外部输入，只能通过大小写不敏感、白名单标识判断是否可重试；不能从路径、文件名或退出码单独推断瞬态性质。
- **重试预算**：每次 `FetchUsage` 固定最多 3 次尝试；任何调用方不得通过请求参数扩大次数。
- **进程收尾不变量**：每次 `fetchUsageOnce` 返回前，stdout/stderr 读取完成且 `agyProcess.shutdown()` 已执行；由 `internal/agapi` 负责。
- **契约不变量**：`api.ErrAgyExecute`、成功 JSON、原始 JSON、CLI 退出码和 MCP 错误映射不因重试次数改变。

### Testability

- 纯错误分类函数可在无 Windows 环境、无 `agy.exe`、无网络下单元测试。
- 重试编排通过 attempt 函数接缝测试，不需要启动真实进程；可验证次数、最后错误、上下文取消和日志回调。
- 真正的 `agy` 进程树回收、stdout/stderr 捕获和 API 瞬态行为属于集成/手工验证，不作为单元测试前置条件。
- `--zed` 不应被本次单元测试触达；现有 Zed 行为仅做回归验证。

## Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | §1 的 `fetchUsageOnce`/重试编排、瞬态白名单、3 次总尝试 |
| AC-2 | §1 最后错误保留、§2 网络/代理建议、错误码保持 `agy_execute_failed` |
| AC-3 | §1 结构化错误和白名单分类、§4 非瞬态错误矩阵 |
| AC-4 | §1 timer/context 选择、§4 上下文取消行、进程收尾不变量 |
| AC-5 | §2 仅修改 agy 建议，§4 `--zed` 不适用行 |
| AC-6 | §1 诊断走 `Logf`、§ Module Collaboration and Data Flow、§2 错误包络兼容 |

## Design Review Notes

本设计已按零上下文视角自审：

- **HIGH：0**
- **MEDIUM：0**
- **NIT：2**
  - NIT-1：上游未来若更换 stderr 文案且不包含白名单标识，将按非瞬态失败快速返回；这是故意的 fail-closed 选择，避免误重试认证或参数错误，后续可基于新证据扩展白名单。
  - NIT-2：设计不承诺每次 `agy` 查询都成功，只承诺在可识别瞬态故障预算内自动恢复；网络持续不可用时仍应返回真实错误。

已验证假设：

- 当前 `FetchUsage` 只执行一次 agy 进程，非零退出直接返回；
- `Service` 已是所有 agy 入口的公共业务路径；
- CLI 查询上下文已有 2 分钟上限；
- `startAgyProcess` 已负责当前进程树回收，重试只重复调用该接缝。

未采用的方案：

- 不使用上一次配额缓存伪装成功，避免展示过期用量；
- 不在 daemon/client 层盲目重试 HTTP 请求，避免与 agy 内部调用重复重试；
- 不把 EOF 视为所有场景都可重试，必须同时匹配配额接口标识。

