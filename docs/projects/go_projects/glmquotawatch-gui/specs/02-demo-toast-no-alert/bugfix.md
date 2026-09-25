# Bug Fix Document

## Summary

Demo 模式跨过阈值后，主窗口和 `state.json` 已把档位记录为“已告警”，但用户未观察到 Windows Toast；当前证据不能区分 `Notify` 返回错误还是 OS 抑制展示，应用也没有暴露任何通知结果状态。

## Reproduction

1. 启动 `glmquotawatch-gui`，通过托盘菜单或 `--demo` 进入演示模式。
2. 保持 5 秒采样间隔，观察百分比从 0% 增长。
3. 在 50%、60%、80%、90% 附近观察系统通知中心。
4. 当前实测状态为 `TOKENS_LIMIT:3:5` 已记录 `[50,60,80,90]`，但通知中心没有出现对应告警；应用也没有显示 Toast 发送失败。

## Root Cause

阈值状态机本身正确：`api.DemoFetcher` 会生成单调增长百分比，`quota.Evaluate` 会返回 `Notify=true`，当前 demo 的 `state.json` 也证明 50/60/80/90 均已被评估。

本次排查不能确认 Toast API 已返回失败；能确认的是应用层没有可靠的交付确认与失败反馈。问题在告警交付链路：

- `Service.SampleOnce` 在 daemon 发送通知前就调用 `SaveState(next)`，把本轮命中的档位提前标记为“已通知”。
- `RunDaemon` 随后调用 `Notifier.Notify`；发送失败时只调用 `log.Warn`。
- `MonitorRuntime.logger()` 明确把日志写入 `io.Discard`，`toastNotifier` 和 GUI 都没有错误回调，所以 Toast 创建、注册或系统投递失败被完全吞掉。
- 结果是应用层面永远显示“已告警”，即使用户从未收到 Toast；后续采样也会因为已记账而不再重试。

Windows 自身的“专注助手/请勿打扰”可能导致应用收到成功返回但仍不展示横幅；这类 OS 侧抑制不可由当前 API 直接判定，不属于本次应用内修复范围。

## Impact

- Demo 模式无法可靠演示阈值 Toast，也不能发现通知发送失败。
- 正常模式存在同一缺陷：阈值在 `state.json` 中提前成为已通知档位，Toast 失败后不会重试，也没有可见错误。
- CLI `status` 的现有“采样并推进状态、不通知”语义保持不变。

## Fix Acceptance Criteria

### AC-1

WHEN demo 或 normal daemon 采样首次命中未通知阈值且 `Notifier.Notify` 返回 `nil`，修复后应用发送一条 Windows Toast，并在通知发送成功后把该轮命中的全部档位持久化到 `state.json`。

### AC-2

WHEN `Notifier.Notify` 返回错误，修复后该轮新命中的档位不得写入 `state.json`，GUI 必须显示稳定的 `notify_failed` 错误信息；同一窗口在下一轮采样时重试未确认档位。

### AC-3

WHEN 同一轮采样一次越过多个阈值后首次重试成功，修复后只发送一条合并通知并报告本轮当前仍待确认的最高档；成功后将这些待确认档位一并记账。

### AC-4

WHEN demo 从 0% 顺序增长到 100% 且每次 Toast 调用成功，修复后在 50%、60%、80%、90% 分别产生一次 Toast，主窗口、托盘状态和 demo 目录数据继续更新，真实模式数据目录不受影响。

### AC-5

WHEN 用户通过 CLI 执行 `status`，修复后仍保持立即采样、推进 `state.json`、不发送 Toast 的既有契约。

## Out of Scope

- 不修改 Windows 专注助手、请勿打扰、系统通知权限或注册表设置。
- 不新增第三方通知库或系统托盘气泡作为替代告警。
- 不重做界面视觉样式。
- 不实现 TIME_LIMIT 窗口告警。
