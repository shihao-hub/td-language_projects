# postgres_query_tuning —— EXPLAIN、索引与分页的量化对照

> 代码：`apps/postgres_query_tuning` ｜ 依赖：PostgreSQL ｜ 数据：1 万用户 / 10 万订单 / 20 万日志

## 一、这组实验解决什么问题

「这个查询慢」是一个需要翻译的症状：慢在全表扫描？排序？深分页？还是网络往返？本组实验用 `EXPLAIN (ANALYZE, BUFFERS)` 把每类慢查询的执行计划摊开对照——**同一个业务需求，索引列序不同、分页策略不同，代价差一个数量级以上**。

## 二、核心原理

### 2.1 怎么读 EXPLAIN

`EXPLAIN (ANALYZE, BUFFERS)` 输出的关键行：

- **Node Type**：`Seq Scan`（全表扫）/ `Index Scan` / `Index Only Scan` / `Sort`——扫描方式决定了 IO 模式；
- **rows=**：估算行数 vs `actual time... rows=` 实际行数，两者差距大说明统计信息过期（`ANALYZE` 表）；
- **Buffers: shared hit/read**：命中缓冲池 / 从磁盘读的页数——**比 Execution Time 更稳定的代价指标**（不受缓存冷热与机器负载干扰）；
- **Execution Time**：仅供参考，同机对照才有意义。

两条纪律：优化前后用**同一查询文本**对照；先看 `Buffers` 再看时间。

### 2.2 索引的选择性法则

优化器在「走索引」与「全表扫」之间做成本比较，核心变量是**选择性**（满足条件的行占比）：

- 高选择性条件（`user_id = 4242` 命中 10 万行中的 10 行）：索引完胜；
- 低选择性条件（`status = 'done'` 占 2/3）：走索引反而更慢（随机 IO + 回表），优化器会**正确地**选择 Seq Scan——这不是索引坏了，是这个条件不适合索引。

### 2.3 联合索引：最左前缀与列序

B 树索引按「列序」排序：`(status, created_at)` 先按 status 等值定位区间，区间内天然按 created_at 有序——**等值列在前、范围/排序列在后**。反过来的 `(created_at, status)` 对 status 等值毫无帮助（第一列就是范围），退化成扫全时间轴再逐行过滤，还得额外 Sort。

### 2.4 OFFSET 深分页 vs 游标分页

`OFFSET 99980 LIMIT 20` 必须产出并丢弃前 99980 行——**页越深越慢**，且插入新数据会导致翻页错行。游标（keyset）分页：

```sql
WHERE (created_at, id) < (%s, %s)   -- 行比较：上一页最后一行的值
ORDER BY created_at DESC, id DESC LIMIT 20
```

直接从 B 树定位起点，代价与页深无关、结果稳定。代价：不能随机跳页——只适合信息流类顺序浏览。

### 2.5 N+1 的本质是网络往返

100 个用户各查一次订单数：SQL 本身不慢，**慢在 100 次往返**。本地测试 RTT≈0.1ms 感觉不到；生产内网 RTT 0.5~1ms 时就是 50~100ms 纯等待，跨可用区更糟。修法：`WHERE user_id = ANY(...)` + `GROUP BY` 一次聚合，或 ORM 的 `selectinload`（IN 批量）/ `joinedload`（JOIN）。

### 2.6 部分索引

`CREATE INDEX ... ON t (created_at DESC) WHERE level = 'error'`：只为满足谓词的 0.25% 行建 B 树——更小、写入维护更便宜、扫描行数更少。适合状态机查询（pending/failed 工单、未读消息）：**终态占绝大多数、非终态极少时收益最大**。

## 三、场景速览

| 场景 | 对照 | 观察点 |
|---|---|---|
| seq-vs-index | 无索引 vs `(user_id)` | Seq Scan 10 万行 vs Index Scan 数行；Buffers 差距 |
| composite-index | `(created_at, status)` vs `(status, created_at)` | 后者消除 Sort 节点、扫描行数骤降 |
| offset-vs-keyset | OFFSET 99980 vs 游标定位 | EXPLAIN 行数 + 50 次平均耗时 |
| n-plus-one | 循环 100 次 vs 一条聚合 | 查询次数、总耗时、放大倍数 |
| partial-index | 普通联合索引 vs 部分索引 | `pg_relation_size` 大小 + 扫描行数 |

## 四、运行方式

```powershell
docker compose up -d postgres
uv run python -m apps.postgres_query_tuning                 # 建表+造数+全部场景（首次约 10s 造数）
uv run python -m apps.postgres_query_tuning --keep-data     # 复用已造数据
uv run python -m apps.postgres_query_tuning --scenario n-plus-1
```

## 五、面试高频问答

- **Q：一条 SQL 慢怎么排查？** A：`EXPLAIN (ANALYZE, BUFFERS)` → 看扫描方式与实际行数 → 判断是否缺索引/索引失效（函数包裹列、隐式类型转换、低选择性）→ 统计信息是否过期。
- **Q：联合索引 (a,b,c)，`WHERE b=? AND c=?` 能用上吗？** A：不能完整用上（最左前缀从 b 开始缺失）；`WHERE a=? ORDER BY c` 能用到 a 的等值 + 部分消除排序，取决于中间列。
- **Q：深分页怎么优化？** A：游标分页（首选、常数代价）；不允许改接口时用「延迟关联」：`WHERE id IN (SELECT id ... OFFSET n)` 先在覆盖索引上翻页再回表。
- **Q：N+1 怎么发现的？** A：SQL 日志/计数、ORM 的 lazy-load 警告、APM 的 trace 里同形状 SQL 重复出现。修法 selectinload/joinedload/手动聚合，注意 joinedload 在一对多上会产生笛卡尔积需要 dedup。
- **Q：为什么索引不总是更好？** A：低选择性条件走全表更快；索引有写放大（每次写维护 B 树）与空间成本。「加索引」永远是成本决策。

## 六、生产对照（creativault）

生产仓库的复杂只读查询抽取到 `infrastructure/orm/query/` 文本模板 + builder（可直接复制到客户端复现）、Repository 的 `@track_query_time` 计时装饰器、`ENABLE_SQL_TRACE_COMMENT` 把 trace_id 注入 SQL 注释——都是「让慢查询可观测、可复现」的同一思想。本实验聚焦判断力本身：给你一份计划，你能不能说出它为什么慢。
