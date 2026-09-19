# kafka_delivery_semantics —— 分区、消费组、提交语义与死信

> 代码：`apps/kafka_delivery_semantics` ｜ 依赖：Kafka（aiokafka）

## 一、这组实验解决什么问题

Kafka 的可靠性问题几乎全部浓缩在两个选择上：**生产端 key 怎么选**（决定顺序与并行）与**消费端 offset 什么时候提交**（决定丢消息还是重放）。本组实验用真实的 broker 把这两组选择的后果演出来——丢的那条消息去哪了、重放的那条怎么被认出来、毒丸如何卡住整个分区。

## 二、核心原理

### 2.1 分区：顺序与并行的同一个旋钮

- 生产者按 `hash(key) % 分区数` 路由：**同 key 必同分区，分区内严格有序**；
- 不同 key 被摊到多个分区：分区数=理想并行度。

推论：要「同一实体的消息有序」（订单状态流转），用实体 id 做 key；要吞吐优先就散 key。**Kafka 只保证分区内有序，跨分区无任何顺序承诺。**

### 2.2 消费组：分区级负载均衡

一个 consumer group 内，每个分区同一时刻只分配给一个消费者：

- 消费者数 < 分区数 → 有消费者身兼多分区；相等 → 刚好一一对应；**超出分区数的消费者完全闲置**（扩容消费者前先看分区数）；
- 成员变化触发再均衡（rebalance）：期间短暂停止消费——这就是「处理到一半的任务」必须能应对重平衡的原因。

### 2.3 提交语义：offset 提交时机决定一切

消费组的位置信息（committed offset）由消费者显式/自动提交。**提交语义完全由「处理与提交的先后」决定**：

| 顺序 | 语义 | 崩溃后果 | 适用 |
|---|---|---|---|
| 先 commit 再处理 | at-most-once | 处理前崩溃 → **消息永久丢失** | 日志、指标（丢一条无妨） |
| 先处理再 commit | at-least-once | 处理后、提交前崩溃 → **重放** | 绝大多数业务（配幂等） |

注意「丢失」的机制：offset 已提交，重启后 broker 认为你消费过了，**那条消息永远不会再来**——没有任何日志会提醒你。

### 2.4 重放与幂等

at-least-once 的重放窗口 = 处理完成到提交成功之间（进程崩溃、rebalance 收回分区都触发）。配套必须是**消费端幂等**：message_id + 业务写 + 幂等标记同事务。工程默认都选这套：**丢失往往无法找回，重复可以靠幂等消解**。

### 2.5 毒丸与死信

一条格式错误/触发 bug 的消息（poison pill），如果处理失败后**不提交 offset**，会在重启后再次被拉取、再次失败——**永远卡住同一分区的后续消息**。标准处理：

```
重试有界（N 次）→ 仍失败：投递到死信 topic + 提交主流 offset（跳过）
                → 人工修复后从死信重放
```

死信是「延迟处理 + 可观测」的缓冲区，不是垃圾桶：死信 topic 里出现消息必须告警。

## 三、场景详解

| 场景 | 演示 |
|---|---|
| partition-order | 同 key 10 条 → 全落同一分区且按序到达；多 key → 摊到 3 个分区 |
| consumer-group | 两个消费者加入同 group → 打印各自 assignment（3 分区被瓜分不重叠） |
| at-most-once | seq=1「先 commit 后处理」，处理前崩溃 → 重启后从 seq=2 开始，seq=1 永久丢失 |
| at-least-once | seq=1 处理完成（业务表已生效）但未提交崩溃 → 重启重放 seq=1 → 幂等表 duplicate |
| dead-letter | 毒丸卡分区（good → **bad** → good，bad 不提交则 good 永远处理不到）→ 重试 3 次后死信 + 提交，good-2 终于通过 |

## 四、运行方式

```powershell
docker compose up -d kafka
uv run python -m apps.kafka_delivery_semantics
uv run python -m apps.kafka_delivery_semantics --scenario at-least-once
```

## 五、面试高频问答

- **Q：怎么保证消息顺序？** A：需要有序的实体用同一 key（同分区）；全局有序只能单分区（牺牲并行）。消费端单分区串行处理，多分区有界并发。
- **Q：怎么保证不丢消息？** A：三分段回答——生产端 `acks=all` + 重试；broker 端副本 `min.insync.replicas>=2`；消费端**先处理再提交** + 提交失败重试。
- **Q：怎么保证不重复消费？** A：保证不了，只能让重复无害：message_id 幂等表与业务写同事务；或把消费写入幂等存储（按主键 upsert）。
- **Q：rebalance 时在途消息怎么办？** A：分区被收回时停止该分区的处理、提交已完成部分；未提交的 offset 会被新主人重放——又是幂等的责任。`max_poll_interval_ms` 调大可减少处理超时误判引发的 rebalance。
- **Q：消费 lag 怎么监控？** A：`kafka-consumer-groups --describe` 或 Burrow/exporter 看 lag 指标；lag 持续增长=消费能力不足（扩消费者受限于分区数）。

## 六、生产对照（creativault）

生产侧 Kafka 投递语义分层（`send` 吞异常 / `send_strict` 等待 ACK 失败上抛 / fire-and-forget）对应本篇的语义选择；延迟队列 Dispatcher 选用 strict 档、失败留给 reclaim 超时裁决，与「死信+重试」思想同源。教学版聚焦语义本身，省略 SASL/多环境配置。
