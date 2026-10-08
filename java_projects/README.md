# java_projects：大厂 Java 后端与 Agent 工程师成长复刻路线

> **面向对象**：大学刚毕业、写了几个月 Java，想要系统性复刻大厂核心交易、对账与智能体架构路线的学习者。
> **设计理念**：从最基础的语言特性、数据结构与 Spring 机制出发，一步一个脚印，将简历中每一个听起来高大上的设计（如动态老化算法、配置化状态机、两阶段路由）在基础代码中找到最本真、最纯粹的根基。

---

## 路线规划

1. **01-career-starter-basics（当前就绪）**：Java 17+ Record、密封接口、Stream API、优先队列与 Aging 动态老化算法、策略模式、Spring 容器与动态 Bean 状态机。
2. **02-middleware-and-cache（规划中）**：Redis 7.3 ZSet 滑动窗口探活、Caffeine 本地多级缓存、Kafka 基础生产消费与幂等。
3. **03-reconciliation-stream（规划中）**：Apache Flink 流流 Join（三流合一）、状态 TTL、复式记账法明细追溯。
4. **04-agent-diagnostic-engine（规划中）**：OpenEuler witty-diagnosis-agent 架构、Skill Tree 两级路由、RAG 知识闭环。

---

## 当前子项目：01-career-starter-basics

### 模块结构与知识映射

- module01_modern_java：
  - PaymentEventRecord.java：Record 不可变流水对象（浅不可变、内置紧凑构造校验）
  - OrderStatus.java：Sealed 密封接口（精确受控状态集合 + switch 模式匹配）
  - ReconciliationStreamDemo.java：Stream API 常见对账操作（filter, groupingBy, reduce）
- module02_concurrent_basics：
  - AgingPayTask.java：任务载体（初始分 P0=100 / P2=10 + 入队时间戳）
  - DynamicAgingScheduler.java：优先队列 + 动态老化算法（彻底解决 P2 任务长期饥饿被饿死问题）
- module03_design_patterns：
  - RefundContext.java / RefundStrategy.java：退款策略契约
  - BalanceRefundAction.java / BankCardRefundAction.java：具体退款渠道实现
  - SimpleRefundDispatcher.java：策略分发注册表（以 Map 查找取代嵌套 if-else）
- module04_spring_basics：
  - ction/OrderAction.java / NotifyMerchantAction.java / DispatchRiderAction.java / AutoRefundAction.java：动作组件
  - DynamicStateMachineEngine.java：核心引擎，模拟数据库配置表，通过 pplicationContext.getBean(actionBeanName) 动态执行动作
  - controller/CareerDemoController.java：对外 REST 控制器，提供 HTTP 端点用于测试观察
- src/test/java/.../StarterAllModulesTest.java：JUnit 5 单元测试覆盖
