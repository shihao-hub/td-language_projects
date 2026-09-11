# sqlalchemy_session_lifecycle —— 连接池、Session 边界与工作单元

> 代码：`apps/sqlalchemy_session_lifecycle` ｜ 依赖：PostgreSQL ｜ 栈：SQLAlchemy 2.0 async + asyncpg

## 一、这组实验解决什么问题

「接口偶尔整体超时，重启就好」「Celery 任务报 Future attached to a different loop」「commit 之后访问属性炸了 DetachedInstanceError」——这三个生产高频故障的根源都在 **Session 与连接的生命周期管理**。本组实验把连接池刻意调小（`pool_size=2, pool_timeout=2s`），让故障在笔记本上两秒内复现。

## 二、核心原理

### 2.1 连接池的本质：事务持续时间的上限

连接池容量 = **同时在途事务数**的上限。每条规则都从这里推导：

- 池满时新请求排队（`pool_timeout` 后抛 `TimeoutError`）——**报错的是无辜的后来者，元凶是前面的长事务**；
- 「长事务」的判定不看 SQL 数量，看**事务持有多久**：一次 `SELECT` 后夹着 3 秒的外部 HTTP 调用再 `UPDATE`，就是 3 秒的长事务；
- 池耗尽的故障特征极具迷惑性：日志里超时的接口与真正的元凶毫无调用关系。

### 2.2 短事务 + DTO 模式

正确姿势是把「等外部 IO」从事务里拆出去：

```
BEGIN → 读快照(显式列) → COMMIT     # 短事务 1：立刻归还连接
        （等待外部 API —— 不占任何连接）
BEGIN → UPDATE 结果 → COMMIT        # 短事务 2
```

「快照」必须是纯数据（DTO / dataclass），不能是 ORM 对象——因为 ORM 对象与 Session 绑定（见 2.3）。

### 2.3 expire_on_commit 与 DetachedInstanceError

SQLAlchemy 默认 `expire_on_commit=True`：commit 时把对象全部属性标记过期，**下次访问触发隐式 SELECT 刷新**。两个后果：

1. 它是 N+1 的隐形来源（看似只是读属性，实际发了 SQL）；
2. 对象离开 Session（close 之后）再访问属性 → `DetachedInstanceError`。

异步项目常设 `expire_on_commit=False` 消除隐式刷新；但更根本的纪律是：**跨层/跨会话/跨进程只传 DTO**，ORM 对象的生命周期不超出 Session。

### 2.4 工作单元（Unit of Work）：事务边界的归属

分层约定（与 [fastapi-layered-api](FastAPI 分层与事务边界.md) 呼应）：

- **Repository**：只 `flush()` 不 `commit()`——flush 把变更推到数据库但不结束事务，能拿到自增 id；
- **Service**：编排多个 Repository 的写入，统一决定 `commit()` / `rollback()`；
- （FastAPI 场景下 Router/依赖注入层持有 Session 生命周期）。

收益：「一个请求 = 一个事务」边界清晰可测，跨仓储写入天然原子。

### 2.5 生产环境边界（未做成实验但要记住）

- **Celery + asyncio**：solo pool 下每次 `asyncio.run()` 新建 loop，asyncpg 连接池绑定在已关闭的 loop 上复用即报错——生产解法是「进程级持久 loop」或 loop 指纹检测后强制重建（`force_recreate=True`）；
- **`pool_pre_ping` + `pool_recycle`**：对抗服务端空闲超时杀连接（如 Hologres `idle_session_timeout=600s`，客户端提前到 500s 回收）。

## 三、场景详解

| 场景 | 演示 | 关键观察 |
|---|---|---|
| pool-exhausted | 3 个任务并发「拿连接睡 1.5s」 | 第 3 个 2s 后 `TimeoutError`；池状态 `inuse=2` |
| short-txn-dto | 同样并发 5 个任务改两段短事务 | 全部成功；等待期间 `pool.status()` 显示连接已归还 |
| detached-instance | 默认 vs `expire_on_commit=False` | commit 后访问属性：隐式刷新 / close 后 DetachedInstanceError；DTO 无此问题 |
| unit-of-work | Service 编排 task+audit 双写 | 业务失败 → 两表零残留；成功 → 同时落库 |

## 四、运行方式

```powershell
docker compose up -d postgres
uv run python -m apps.sqlalchemy_session_lifecycle
uv run python -m apps.sqlalchemy_session_lifecycle --scenario pool-exhausted
```

## 五、面试高频问答

- **Q：连接池打满怎么排查？** A：先看 `engine.pool.status()` / pg 的 `pg_stat_activity`（`state='idle in transaction'` 的会话就是元凶）；再看是否外部 IO 被包进事务；临时扩 `max_overflow` 只是止血。
- **Q：Session 是线程安全的吗？** A：不是。`AsyncSession` 同一时刻只允许一个任务操作；并发任务各自开 Session（sessionmaker 工厂 + `async with`）。官方文档明确：并发共享一个 Session 是未定义行为。
- **Q：flush 和 commit 的区别？** A：flush 把 pending 变更推送到数据库（SQL 已发、事务未定、可 rollback 撤销）；commit = flush + 结束事务。Repository 层只 flush，让上层决定事务边界。
- **Q：DetachedInstanceError 怎么来的？** A：commit 后属性过期 + 对象脱离 Session，访问属性需要刷新却没有会话。预防：跨边界传 DTO；`expire_on_commit=False` 只能消隐式刷新，不能让对象跨会话存活。
- **Q：为什么要「一个请求一个事务」？** A：事务边界清晰可测；跨仓储写原子；连接持有时间最短。拆成三个小事务会出现「钱包扣了但订单没落库」的部分成功。

## 六、生产对照（creativault）

生产侧 `DatabaseConnection.get_session()` 的事务性生成器、`register_after_commit_callback()`（提交后副作用，回滚丢弃）、Celery 生存适配（`ensure_tec_business_db` 的 loop 漂移检测重建）是本篇 2.2/2.4/2.5 的完整形态。教学版保留判断力主干，省略多库路由与 Apollo 配置分发。
