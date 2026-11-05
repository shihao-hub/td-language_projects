# acp-title-proxy worker 回收与透明重连设计

状态：待确认
日期：2026-11-01
关联：`internal/mux/serve.go`、`internal/mux/daemon.go`、`internal/config/config.go`

## 1. 背景

实测结论（本次调研）：

- `session/load` 每加载一个会话，agy_acp_server 就拉起一个 `localharness_external.exe`，占用 105~143MB；
- 会话 idle 后 harness 不退出；client 断开后 daemon 只发 `session/cancel`，harness 仍在；
- `session/close` 方法存在且返回 `{}`，但**不回收进程**；没有池化复用，重新 load 会再新建一个；
- 唯一能回收 harness 的手段是重启 worker 进程。

但现行实现下重启 worker 会直接暴露给用户：

```
worker 退出 → daemon.OnExit 关闭所有 client 连接
           → serve.splice 返回 → RunServe 返回 → main 退出
           → Zed 显示 Retry
```

用户明确不接受 Retry 面板（点击后若 daemon 未就绪会走 `fallback_direct`，变成独立进程）。

## 2. 目标

1. daemon 可主动重启 worker 回收 harness，Zed 无感知（不出现 Retry、不重复渲染历史）；
2. 用户切回已被回收的会话并继续对话时，自动恢复，无需手动操作；
3. 不改变 ACP 对外协议，不影响直连回退。

## 3. 非目标

- 不保证在途 `session/prompt` 不丢失（worker 重启必然中断，用条件规避而非保存）；
- 不做跨进程会话持久化（会话历史仍由 agy 自身落盘）；
- 不改动 agy 内部实现。

## 4. 方案

### 4.1 serve：断线重连而非退出

现 `serve.splice` 是两个 `io.Copy`，任一端断开即返回。改为：

- serve 启动时生成 `instance_id`（随机串，进程生命周期内固定）；
- attach 握手扩展为 `{"cmd":"attach","proto":1,"instance":"<id>"}`；
- 转发改为按行的双向循环（`bufio.Reader.ReadBytes('\n')`，单行上限沿用 4MB）；
- daemon 连接断开时：
  - 不退出，进入重连循环（200ms 间隔，总计 30s）；
  - 期间 client→daemon 的行进入内存队列（设上限，例如 200 行或 8MB，超出则断开并退出，交给 Zed 处理）；
  - 重连成功后用**同一个 instance_id** 重新 attach，再按序发送队列；
  - 30s 仍失败才返回错误（此时 Zed 必然 Retry，属于 daemon 整体不可用，可接受）。

服务端→client 方向在重连期间没有消息，无需缓存。

### 4.2 daemon：识别重连并迁移会话

- `Client` 增加 `instanceID` 字段；
- attach 时若已存在同 `instanceID` 的旧连接：
  - 关闭旧连接；
  - 把 `d.sessions` 中 owner 为旧 client 的条目改指向新 client；
  - **不发送** `session/cancel`，不删除 `sessionActivity` / `sessionMeta`；
- 新连接的 client id 变化不影响 session 路由。

### 4.3 daemon：会话元数据

新增 `sessionMeta map[string]sessionMeta`：

```go
type sessionMeta struct {
    cwd        string
    mcpServers json.RawMessage
    generation uint64 // 该会话最后一次成功 load 时的 worker 代次
}
```

- `session/new`、`session/load` 转发前，从 params 提取 `cwd` / `mcpServers` 记录；
- `session/new` 成功后同样记录（后续恢复用）；
- `removeClient` 时随 sessions 一并清理。

### 4.4 daemon：worker 代次与静默重放

- `Daemon.workerGeneration uint64`，每次 `startBackend` 成功后 +1；
- worker 重启时（`OnExit` 或主动回收）：
  - **保留** `d.sessions` / `sessionMeta` / `sessionActivity`（不再整表清空）；
  - 新 worker 起来后，对"活跃窗口内"的会话逐个补发 `session/load`（带记录的 cwd/mcpServers）；
  - 补发期间设置 `silentReplay[sid] = true`：丢弃该会话的 `session/update`，避免 Zed 重复渲染历史；收到 load 响应后清除标记并写入 `sessionMeta.generation`；
  - 活跃窗口外的会话不补发，等待按需恢复。

### 4.5 daemon：按需恢复

`session/prompt` 转发前检查：

```
if sessionMeta[sid].generation < workerGeneration 且 session 有元数据:
    先向 worker 发 session/load（同步等待）
    成功后再转发 prompt
```

这样即使用户切回一个已被回收的会话，也不需要 Zed 重新 load。

### 4.6 回收触发

新增配置 `share.reclaim_idle_minutes`（默认 30，0 表示关闭）。

daemon 每 5 分钟检查一次，满足全部条件才回收：

- `len(d.pending) == 0`（没有在途请求）；
- 所有会话的 `lastActiveAt` 均超过 `reclaim_idle_minutes`；
- 当前 `len(d.sessions) > 0`（没有会话就无需回收）。

回收动作：`KillTree(worker)` → `startBackend()`。

> 注意：worker 进程本身常驻约 200MB（agy_acp_server 主体），不在回收范围；回收的只是各会话的 harness。

## 5. 关键时序

```
用户 30 分钟没操作
  → daemon 判定可回收，KillTree(worker)
  → serve 收到 TCP 断开，进入重连队列（Zed 无感知）
  → daemon 启动新 worker（generation +1）
  → serve 重连，attach(instance=同 id)
  → daemon 迁移 client，对活跃会话静默重放 load
  → 用户切回旧会话发 prompt
  → daemon 发现 generation 落后，先 load 再转发
```

## 6. 风险

| 风险 | 处理 |
| :--- | :--- |
| 重放期间 Zed 重复显示历史 | `silentReplay` 丢弃 update，只等 load 响应 |
| 重连窗口内 client 请求积压 | 队列上限 200 行 / 8MB，超出主动断开 |
| 多 panel 同时重连 | 各自 instance_id 独立迁移；initialize 只转发一次（daemon 已有缓存逻辑） |
| prompt 在重启瞬间到达 | 回收条件要求 `pending == 0`，且 prompt 前有 generation 检查兜底 |
| daemon 进程本身崩溃 | 无法透明，30s 后 serve 退出，Zed Retry（与现状一致） |
| 重放 load 自身耗时 | 只重放活跃会话；日志记录实际耗时 |

## 7. 验收

1. 手动 `kill` worker 进程，Zed 面板不出现 Retry，日志显示 serve 重连成功；
2. 回收后 `localharness_external` 数量归零；
3. 切回旧会话发 prompt，能正常回复，且不重复显示历史；
4. 两个 panel 同时在线时回收，两个都不掉线；
5. 空闲 30 分钟后自动回收，harness 数下降；
6. `go test ./...` 全绿，新增覆盖：重连迁移、按需 load、静默重放、回收条件判定。

## 8. 未决问题与阻塞确认清单

- [ ] 问题 1：`reclaim_idle_minutes` 默认 30 是否合适？还是 15 分钟？
- [ ] 问题 2：重连窗口 30s 是否够？是否需要可配置？
- [ ] 问题 3：是否接受"回收后再发 prompt 会多一次历史回放延迟"（约 1-3 秒）？
- [ ] 问题 4：是否需要同时修正 `max_sessions` 的计量口径（回到按会话总数，还是保持按活跃数）？
- [ ] 问题 5：是否需要把实测得到的 105MB/harness 写进 README，替换错误的 190MB/会话描述？
