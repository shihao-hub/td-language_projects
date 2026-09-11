# tech_learning_room 学习教程总览

面向「Python 后端为主、兼顾全栈」的跳槽准备：以可运行的实验复现后端工程中的经典机制与故障现场。每个实验都遵循同一套方法论——**先看事故如何发生，再看正确方案为什么有效**。

教程目录（父仓库 `docs/python_projects/tech_learning_room/`），代码在子仓 `python_projects/tech_learning_room/apps/` 下对应 app。

## 推荐学习顺序（按后端面试优先级排列）

| 优先级 | 教程 | 实验代码 | 依赖服务 | 一句话主题 |
|---|---|---|---|---|
| ★★★ | [postgres-transactions](PG 并发扣减与事务隔离.md) | `apps/postgres_transactions` | PG | 丢失更新 / 条件 UPDATE / 行锁 / 唯一约束 / 死锁 / 隔离级别 |
| ★★★ | [redis-cache-consistency](Redis 缓存一致性.md) | `apps/redis_cache_consistency` | Redis | 击穿 / 穿透 / 雪崩 / 失效竞态 / 分布式锁 |
| ★★★ | [postgres-query-tuning](PG 查询调优.md) | `apps/postgres_query_tuning` | PG | EXPLAIN / 联合索引 / 游标分页 / N+1 / 部分索引 |
| ★★★ | [sqlalchemy-session-lifecycle](SQLAlchemy Session 生命周期.md) | `apps/sqlalchemy_session_lifecycle` | PG | 连接池耗尽 / 短事务+DTO / Detached 实例 / 工作单元 |
| ★★☆ | [transactional-outbox](事务发件箱.md) | `apps/transactional_outbox` | PG（Kafka 场景可选） | 双写问题 / 同事务发件箱 / 租约 / 消费幂等 |
| ★★☆ | [celery-task-reliability](Celery 任务可靠性.md) | `apps/celery_task_reliability` | PG + Redis | 重试退避 / 幂等键 / 进度账本 / 孤儿恢复 |
| ★★☆ | [kafka-delivery-semantics](Kafka 投递语义.md) | `apps/kafka_delivery_semantics` | Kafka | 分区顺序 / 消费组 / 提交语义 / 死信 |
| ★☆☆ | [billing-compensation](计费补偿与对账.md) | `apps/billing_compensation` | PG | Decimal 金额 / 幂等扣费 / 补偿配对 / 对账 |
| ★☆☆ | [fastapi-layered-api](FastAPI 分层与事务边界.md) | `apps/fastapi_layered_api` | PG | Router→Service→Repository / DI / 统一响应 / 事务回滚 |
| 基础 | [python-asyncio-concurrency](Python asyncio 并发.md) | `apps/python_asyncio_concurrency` | 无 | 事件循环 / TaskGroup / 超时取消 / 信号量 |
| 参考 | [redis-four-roles](Redis 四种角色.md) | `apps/redis_four_roles` | Redis | 一个 Redis 的四种角色（缓存/broker/延迟队列/限流） |
| 参考 | — | `apps/distributed_transaction` | 无 | 2PC / 3PC 对照演示 |

## 环境准备

```powershell
# 项目根（python_projects/tech_learning_room/）
cp .env.example .env          # 按需修改连接串
uv sync                       # 安装全部依赖

# 外部服务（docker-compose.yml，按需启动，可不同时开）
docker compose up -d postgres # localhost:55432
docker compose up -d redis    # localhost:6380
docker compose up -d kafka    # localhost:29092

uv run python main.py doctor  # 连通性自检
uv run python main.py list    # 查看全部实验
uv run python main.py run postgres_transactions --scenario lost-update
```

依赖不可用时实验会**显式报错退出**，绝不静默降级成模拟实现——这是刻意的工程约定。

## 约定

- 每个实验独立 schema（`tlr_txn` / `tlr_tune` / ...）、独立 Redis key 前缀、独立 Kafka topic 前缀，互不污染，可反复重跑。
- 所有 SQL 显式列出字段；数据库表不使用 JSONB；金额一律 `NUMERIC` + `Decimal`。
- 每个场景输出 `[OK]` / `[NG]` 断言与「结论」段——实验结束时应能脱离教程向别人复述结论。

## 与 creativault 生产实现的对照

多数实验主题（Session 生命周期、Celery 可靠性、Outbox、计费补偿、三层架构）源自 creativault 生产代码的教学化重写：保留了机制与取舍，替换了业务与基础设施（Apollo/Hologres 等替换为 .env + PostgreSQL）。各教程末尾的「生产对照」一节标注了对应关系与简化点。
