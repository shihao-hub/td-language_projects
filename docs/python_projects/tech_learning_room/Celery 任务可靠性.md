# celery_task_reliability —— 重试、幂等、进度账本与孤儿恢复

> 代码：`apps/celery_task_reliability` ｜ 依赖：PostgreSQL + Redis（broker/backend）｜ 前 4 个场景无需启动 worker

## 一、这组实验解决什么问题

异步任务系统的可靠性问题集中在四类：瞬时故障要不要重试、重试/重投导致的重复执行怎么挡、跑到一半崩了从哪继续、怎么发现「已经死透但状态还停在 processing」的孤儿任务。本组实验围绕一条核心认知展开：**Celery 只是触发通道，恢复的真相在数据库**。

## 二、核心原理

### 2.1 可靠性参数矩阵（broker=Redis 时尤其重要）

| 参数 | 含义 | 事故场景 |
|---|---|---|
| `task_acks_late=True` | 执行**完成后**才 ack | 配合下面两项实现至少一次 |
| `task_reject_on_worker_lost=True` | worker 进程崩溃时消息重回队列 | 否则崩溃=消息丢失 |
| `broker_transport_options.visibility_timeout` | Redis broker 的可见性超时 | **必须大于最长任务耗时**：长任务还在跑、unacked 消息超时被其他 worker 重投 → 任务双活（经典事故） |
| `worker_prefetch_multiplier=1` | 一次只领一个任务 | 公平调度，防止快 worker 囤积饿死长任务 |
| `worker_max_tasks_per_child=N` | 子进程定期轮换 | 防内存泄漏 |

**阈值链必须严格单调**：软超时 < 硬超时 < visibility_timeout < 孤儿判定时间。任何一环倒挂都会产生重复投递或误杀。

### 2.2 重试的圈定：什么值得重试

`autoretry_for=(ConnectionError,)` 圈定「瞬时故障」——网络抖动、下游暂时不可用。**参数错误、余额不足这类确定性失败不该重试**：盲目 `for=(Exception,)` 会把 bug 刷成告警风暴，还可能打死刚恢复的下游。`retry_backoff=True` 让间隔指数增长（1s/2s/4s...），给下游喘息。

### 2.3 业务幂等：至少一次的配套

acks_late + 重试 + 重投都意味着**同一业务动作可能执行多次**。「至少一次投递 + 业务幂等键」是标准组合：

- 幂等键 = 业务唯一标识（订单号+动作），存进唯一约束；
- **幂等记录与业务写同事务**：失败一起回滚（不占键，可安全重试），成功一起提交（占键，重放被短路）；
- 「先占键再处理且不回滚」是隐蔽 bug：故障把键烧掉，之后永远 duplicate 却从未生效。

### 2.4 进度账本：断点续跑

批处理任务的进度不依赖 result backend，而是落在业务表：每条一个状态、逐条 commit 心跳。任务重投/恢复后**只处理 `pending` 条目**——已 sent 的天然跳过。这就是「状态账本外置」。

### 2.5 孤儿恢复：自愈扫描模式

acks_late 的边界：任务被 SIGKILL（硬超时/OOM）时消息虽会重回队列，但**业务表状态已停在 processing 且心跳停止**。兜底是一个周期扫描任务：

```
Beat 每 5 分钟 → 扫描 status='processing' AND updated_at < now() - 孤儿阈值
  ├─ recovery_count < 3 → 计数+1 + commit 占位 + 重投任务（断点续跑）
  └─ recovery_count >= 3 → 标 failed + 告警（防"必败任务"无限重投）
```

生产上还配 Redis SETNX 锁防多实例双投。这是「Beat 周期扫描非终态 + 超时判定 + 有界重派」的通用自愈范式，可用于卡住的工单、超时的回调、丢失的通知。

## 三、场景详解

| 场景 | 依赖 | 演示 |
|---|---|---|
| idempotency | 仅 PG | 同 idem_key 两次扣费：charged / duplicate，表里只有一条 |
| idempotency-crash | 仅 PG | 失败回滚不占键 → 重试按新请求成功 |
| batch-resume | 仅 PG | 造「发到第 4 条崩溃」现场 → 重跑只补发 4 条 pending |
| orphan-recovery | 仅 PG | 活跃任务不动 / 孤儿重投+1 / 超限标 failed |
| retry-backoff | PG+Redis+worker | 真实 worker：前两次失败第三次成功，总耗时体现 1+2s 退避 |

前 4 个场景用 `.run(...)` 本地直调任务函数（绕过 broker，专注任务体逻辑）；retry-backoff 走完整链路。

## 四、运行方式

```powershell
docker compose up -d postgres redis

# 无需 worker 的 4 个场景
uv run python -m apps.celery_task_reliability --scenario idempotency

# 真实 worker 演示（Windows 必须 solo pool）
uv run celery -A apps.celery_task_reliability.celery_lab worker --pool=solo -l info
uv run python -m apps.celery_task_reliability --scenario retry-backoff
```

## 五、面试高频问答

- **Q：任务重复执行怎么防？** A：三层：acks_late 只保证「至少一次」不保证「恰好一次」；业务幂等键（唯一约束+同事务）是正确性防线；对账任务是发现性兜底。
- **Q：visibility_timeout 是什么？** A：Redis broker 没有AMQP 的 per-message ack，靠「可见性超时」模拟：unacked 消息超时后可被重投。必须大于最长任务耗时，否则双活。
- **Q：任务卡在 processing 怎么办？** A：孤儿恢复扫描（超时阈值 > 硬超时，重投有界，先 commit 占位防双投）；根因排查看 SIGKILL（OOM/硬超时）。
- **Q：批量任务跑到一半 worker 重启？** A：进度账本（逐条 commit）+ 重投后只做 pending → 断点续跑。千万别把「全部完成」只存在内存或 result backend。
- **Q：什么异常该自动重试？** A：瞬时故障（网络、限流、锁冲突）；确定性失败直接失败并告警。重试必须有界+退避。

## 六、生产对照（creativault）

生产版 `recover_orphan_batch_jobs` 与本实验同构：孤儿阈值 70min 严格大于任务硬超时 65min、恢复上限 3、Redis SETNX 锁 TTL 300s、`max_retries=0`（把全部恢复责任交给孤儿机制，避免两套重试叠加）。此外生产还有 Redbeat 分布式调度（多 Pod 单 Beat）与代码-Redis 调度对账（防任务改名后幽灵调度），属于规模化的同思想延伸。
