# postgres_transactions —— 并发扣减与事务隔离

> 代码：`apps/postgres_transactions` ｜ 依赖：PostgreSQL ｜ 驱动：psycopg3（同步，便于精确控制事务时序）

## 一、这组实验解决什么问题

「秒杀抢 5 个名额，结果 6 个人都成功了」「同一用户重复提交，扣了两次」「两个事务互相等对方，谁也动不了」——这些不是概率性玄学，而是**并发访问共享数据时可以精确复现的时序问题**。本组实验用两个数据库连接手动编排事务交错，把每一个经典事故现场演出来看，再逐一给出正确写法与适用边界。

贯穿全篇的一个心智模型：**数据库事务给你的不是「隔离的并发」，而是一组必须显式选择的隔离与锁机制**。写并发代码的每一个决策，本质都是在回答「我依赖的是哪一层保证」。

## 二、核心原理

### 2.1 快照与锁：Read Committed 下的世界

PostgreSQL 默认隔离级别 Read Committed 的语义是：**事务内每条语句开始时获取一份新的快照**。这意味着：

- 普通 `SELECT` 读到的是「这条语句开始时已提交的最新值」；
- 两个并发事务可以同时读到**相同的旧值**，各自计算后先后写回——后写者覆盖前写者，这就是**丢失更新（lost update）**；
- 「读到的值」随时可能过期，它是快照不是锁。

因此铁律一：**不要在应用层做「读→算→写」三步来修改共享行**。要么把算术下推进单条 SQL（场景 2），要么先锁再读（场景 3）。

### 2.2 行锁的三个来源

| 写法 | 锁语义 | 适用 |
|---|---|---|
| `UPDATE ... WHERE cond` | 写时对命中行加行锁，整个 SET+WHERE 原子执行 | 计数器、库存扣减的第一选择 |
| `SELECT ... FOR UPDATE` | 读时即加行锁，后续计算在锁内 | 必须在应用层计算时 |
| `SELECT ... FOR UPDATE NOWAIT` | 拿不到锁立即报错 | 快速失败、避免堆积 |

### 2.3 唯一约束：最后的幂等防线

应用层「先查再插」在并发下有竞态窗口（两个请求都查到「不存在」然后都插入）。`UNIQUE` 约束让重复插入在**索引层面**直接失败，且因为扣减与插入在同一事务，被拒绝的请求不会留下「名额已扣但没有记录」的脏状态。

### 2.4 死锁与重试

死锁无法彻底消灭（业务复杂度决定），治本手段是**固定顺序访问资源**；治标手段是把 `DeadlockDetected` / `SerializationFailure` 当作**可重试错误**——回滚整个事务、退避、重来。任何「多行写」的代码都值得问一句：加锁顺序固定吗？

### 2.5 隔离级别的取舍

- **Read Committed**（默认）：每条语句新快照，吞吐最好；代价是同一事务内两次读可以不同（不可重复读）。
- **Repeatable Read**：事务开始时固定快照，读到一致视图；代价是**写冲突会抛 40001**，调用方必须把整个事务当作可重试单元。

没有银弹：隔离级别越高、一致性越强，重试与冲突的成本就越高。

## 三、场景详解

### 场景 1：lost-update —— 读-算-写的必然结局

时序（实验用两个连接手动编排，真实并发里随时发生）：

```
T1: SELECT remaining -> 5
T2: SELECT remaining -> 5        # 读到 T1 提交前的值
T1: UPDATE remaining = 5-1 = 4; COMMIT
T2: UPDATE remaining = 5-1 = 4; COMMIT   # 用过期快照整体覆盖
最终：remaining=4，但两人都"成功"，正确答案应为 3
```

要点：T2 的 UPDATE 不是「增量修改」而是「把算好的绝对值写回去」，它覆盖了 T1 的写入。**根因是计算发生在数据库之外，基于一个随时过期的快照。**

### 场景 2：atomic-update —— 条件 UPDATE

```sql
UPDATE redemption_codes
SET remaining = remaining - 1
WHERE id = %s AND remaining >= 1
RETURNING remaining;
```

`WHERE remaining >= 1` 与 `SET remaining = remaining - 1` 在数据库内部对同一行加行锁后串行执行，不存在「读到旧值再覆盖」的窗口。30 个线程抢 5 个名额，恰好 5 人成功。**这是秒杀/库存扣减的第一选择**：无显式锁、无重试、天然原子。

注意 `RETURNING`：它告诉你扣减后的值，且返回 0 行即「没抢到」，不需要再 SELECT 一次。

### 场景 3：select-for-update —— 显式行锁

什么时候不得不用 `FOR UPDATE`？当「算」无法下推进 SQL（业务规则复杂、需要读多行后再决定写什么）。实验演示两个变体：

- `NOWAIT`：拿不到锁立刻抛 `LockNotAvailable`——适合「快速失败」，例如防止请求堆积拖垮数据库；
- 普通等待：T2 阻塞直到 T1 commit，**T2 读到的一定是 T1 提交后的新值**（锁保证了这一点）。

代价：并发度下降、持锁事务必须短。所以场景 2 的条件 UPDATE 仍是首选。

### 场景 4：unique-constraint —— 数据库层面的幂等

同一用户重复提交（网络重试、前端双击）：第一次成功，第二次被 `UNIQUE(code_id, user_id)` 拒绝——且**扣减与插入同事务，第二次的扣减随事务一起回滚**。并发 10 个相同请求也只有一条落库。

### 场景 5：deadlock —— 交叉加锁与重试模式

T1 锁 A 等 B，T2 锁 B 等 A：PostgreSQL 的死锁检测器（默认 `deadlock_timeout=1s`）会牺牲一个事务打破环。实验先复现「一个事务被强制回滚」，再演示生产写法：

```python
while True:
    try:
        with connect() as conn:
            transfer_both(conn)   # 内部按固定顺序 (1, 2) 加锁
        break
    except (DeadlockDetected, SerializationFailure):
        backoff(); continue       # 整个事务重试
```

### 场景 6：isolation-levels —— 两种隔离级别同台

同一时序（T1 读 → T2 改并提交 → T1 再读 → T1 写）：

- Read Committed：T1 两次读到不同值（不可重复读是常态，不是 bug）；
- Repeatable Read：T1 两次读到相同值（快照固定），但 T1 尝试写时收到 `could not serialize access`（40001）——数据库拒绝让你基于旧快照覆盖别人的写入。

## 四、运行方式

```powershell
docker compose up -d postgres
uv run python -m apps.postgres_transactions --list
uv run python -m apps.postgres_transactions                        # 全部 6 个场景
uv run python -m apps.postgres_transactions --scenario deadlock    # 单跑死锁
```

## 五、面试高频问答

- **Q：怎么防止超卖？** A：首选条件 UPDATE（`WHERE stock >= n` + 原子自减）；需要复杂校验时 `FOR UPDATE` 串行化；Redis 预扣（Lua 原子）适合超高并发但要处理与 DB 的最终一致。
- **Q：丢失更新是什么？RC/RR/Serializable 各能防什么？** A：RC 防脏读；RR（PG 实现）防不可重复读与丢失更新（写冲突抛 40001）；Serializable 最强但冲突率最高。
- **Q：唯一约束和应用层查重怎么选？** A：应用层查重只是体验优化（提前给用户报错），唯一约束才是正确性保证，两者不冲突、必须都有。
- **Q：死锁怎么办？** A：固定加锁顺序（治本）+ 短事务 + 把死锁当可重试错误（治标）。

## 六、生产对照（creativault）

生产代码的兑换码核销（`redemption_service`）正是这套组合：`find_code_by_id_for_update`（行锁）+ 原子递增核销计数 + 唯一约束防重复兑换 + 「积分发放命中 0 行就抛异常整体回滚」。教学版去掉了业务复杂度，保留了全部机制骨架。
