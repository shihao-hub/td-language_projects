# python_asyncio_concurrency —— 事件循环、并发原语与取消语义

> 代码：`apps/python_asyncio_concurrency` ｜ 依赖：无（纯标准库）

## 一、这组实验解决什么问题

FastAPI/asyncpg 的异步栈把事件循环藏在了框架后面，导致很多问题被误判：「加了 async 为什么没变快」「接口偶尔集体卡死」「任务取消了但连接没释放」。本组实验掀开盖子直接操作事件循环，把五个核心机制的现象与原理对应起来。**这是后面所有异步实验的地基**。

## 二、核心原理

### 2.1 await 的本质

`await` 不是「并行执行」，而是「等待时挂起自己、把循环让给别人」。推论：

- **串行 await = 同步代码**：10 个 `await io()` 依次执行，总耗时=总和；
- `asyncio.gather` / `TaskGroup` 才真正铺开并发：总耗时≈最慢者；
- 加 async 不加速 CPU 密集任务（单线程还是那个单线程），只加速「等待型 IO」。

### 2.2 事件循环是单线程的

任何一个协程阻塞（`time.sleep`、`requests`、同步 DB 驱动、重 CPU），**所有协程一起停摆**——包括与它毫无关系的心跳、健康检查。生产表现：整个进程 P99 飙高、超时雪崩，但看每个协程的代码都「没问题」。

处方：async 生态库（httpx/asyncpg/redis.asyncio）+ `asyncio.to_thread` 兜底同步代码（FastAPI 的 `def` 路由同理走线程池）。

### 2.3 TaskGroup：结构化并发（3.11+）

```python
async with asyncio.TaskGroup() as tg:
    tg.create_task(a()); tg.create_task(b()); tg.create_task(c())
# 离开 with 时：要么全部成功，要么异常向上冒泡且兄弟任务全被取消
```

对比 `gather`：默认等**所有**任务跑完才抛第一个异常——失败后兄弟还在空转（浪费连接/配额）。`except*` 语法按「异常组」过滤捕获。写新代码优先 TaskGroup。

### 2.4 超时与取消：CancelledError 是控制流

`wait_for(coro, timeout)` 的超时实现是**向协程注入 `CancelledError`**：协程在下一个 await 点被唤醒并抛出。两个纪律：

1. 资源清理写在 `finally` 或 `except asyncio.CancelledError` 里——被取消的任务也要干净退出；
2. 捕获 `CancelledError` 后**必须 re-raise**，否则外层以为任务正常结束（吞取消信号是「关不掉的任务」的根源）。

这是优雅停机（SIGTERM → 取消所有在途任务 → 等待清理 → 退出）的原型。

### 2.5 并发上限与背压

- `asyncio.Semaphore(3)`：限制「同时在跑」的数量——保护下游（DB 连接池、第三方配额）不被瞬时打爆；
- `asyncio.Queue(maxsize=5)`：生产快消费慢时，`put` 在队列满处挂起——**把压力反推给生产者（背压），保护内存**。无界队列=把内存当无限资源，是流水线系统的隐形炸弹。

## 三、场景速览

| 场景 | 现象 |
|---|---|
| serial-vs-concurrent | 10×1s IO：串行 ~10s，gather/TaskGroup ~1s |
| blocking-loop | `time.sleep(2)` 期间心跳最大间隔 2.1s（全场冻结）；`to_thread` 后恢复 0.2s |
| taskgroup | bad 1s 抛错 → slow 被取消（cancelled 事件）、quick 已完成不受影响、总耗时 ~1s 而非 3s |
| timeout-cancel | 1s 超时 → 清理动作执行（resource-released）→ TimeoutError 上抛 |
| semaphore-bounded | 10 任务限并发 3：峰值恰好 3；有界队列：消费不领走生产者就挂起在 put |

## 四、运行方式

```powershell
uv run python -m apps.python_asyncio_concurrency            # 全部场景，无需任何外部服务
uv run python -m apps.python_asyncio_concurrency --scenario taskgroup
```

## 五、面试高频问答

- **Q：asyncio 为什么快？** A：不快，是「省」：单线程内协作式调度，等待 IO 时让出线程跑别的协程，省掉线程/进程切换与内存开销。适合 IO 密集；CPU 密集用进程池。
- **Q：事件循环里能跑 requests 吗？** A：能跑但会冻结整个循环（同步阻塞）。换 httpx.AsyncClient，或 `asyncio.to_thread` 包一层。
- **Q：gather 和 TaskGroup 选哪个？** A：新代码 TaskGroup：异常时自动取消兄弟、ExceptionGroup 语义清晰；gather 适合「收集结果、允许失败」（return_exceptions=True）的场景。
- **Q：CancelledError 要不要捕获？** A：为了清理可以捕，捕完必须 re-raise。吞掉它=任务拒绝被取消，优雅停机会卡死。
- **Q：怎么限制并发数？** A：Semaphore（同时跑的数量）；限速率用令牌桶/滑动窗口（见 redis-four-roles 的限流器）；队列积压控制用有界 Queue。

## 六、与后续实验的关系

- Celery worker 里跑 async 栈的「持久事件循环」问题：[celery-task-reliability](Celery 任务可靠性.md)；
- Redis asyncio 连接池与 event loop 绑定的漂移问题：[redis-four-roles](Redis 四种角色.md)；
- FastAPI 异步路由下「一个请求一个任务」的并发模型：[fastapi-layered-api](FastAPI 分层与事务边界.md)。
