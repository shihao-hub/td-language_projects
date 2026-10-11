# java_projects：校招 Java 与智能运维 Agent 工程师实战全景

> **定位**：专为应届生求职打造的 Java 21 + Spring Boot 3 深度实践路线。
> **原则**：拒绝脱离业务的死记硬背，直击大厂高频面试核心架构。从“Java 21 语法与并发底座”到“滴滴国际化支付出海清结算”，再到“openEuler Witty 智能运维 Agent”，麻雀虽小、五脏俱全，所有模块均包含真实业务场景与 100% 跑通的单元测试。

---

## 一、全量工程构建与验证

全工程通过根目录父 POM 统一纳管，严格收敛于 `java_projects` 单一 monorepo 目录结构：

```powershell
# 在 java_projects 根目录下执行全量编译与单测
cd D:\Users\language_projects\java_projects
cmd /c "set JAVA_HOME=D:\Users\java\jdk-21&& D:\Users\java\maven\bin\mvn.cmd test"
```

**测试结果状态**：
- `java-projects-parent`：SUCCESS
- `career-starter-basics`：SUCCESS（8/8 单元测试通过）
- `career-payment-saas`：SUCCESS（2/2 单元测试通过）
- `career-agent-diagnose`：SUCCESS（2/2 单元测试通过）
- **汇总**：全部通过，0 错误，0 失败。

---

## 二、子模块架构与知识图谱

### 1. `career-starter-basics`（现代 Java 21 与架构底座）
- **核心定位**：从 JDK 8/11 思维跃迁至 JDK 21，打破“面向注解黑盒”迷茫，掌握设计模式与并发调度。
- **模块目录**：
  - `module01_modern_java`：
    - `PaymentEventRecord.java`：Record 声明不可变数据载体，内置紧凑型校验。
    - `OrderStatus.java`：Sealed 密封接口（限定 4 种状态）+ Switch 模式匹配穷尽检查。
    - `Java21FeaturesDemo.java`：Record Pattern 模式解构提取字段，Sequenced Collections（`getFirst`/`getLast`）。
    - `ReconciliationStreamDemo.java`：Stream API 过滤、金额统计、渠道分组（`filter`, `reduce`, `groupingBy`）。
  - `module02_concurrent_basics`：
    - `VirtualThreadsDemo.java`：Java 21 虚拟线程 API 与并发调度吞吐测试。
    - `AgingPayTask.java` / `DynamicAgingScheduler.java`：基于 `PriorityQueue` 的动态老化调度算法（低优先级 P2 任务随等待时间加权反超高优先级 P0，解决并发任务饥饿）。
  - `module03_design_patterns`：
    - `RefundStrategy.java` / `BalanceRefundAction.java` / `BankCardRefundAction.java`：策略模式解耦多渠道退款。
    - `SimpleRefundDispatcher.java`：基于 `Map<String, RefundStrategy>` 查表分发，彻底消灭嵌套 `if-else`。
  - `module04_spring_basics`：
    - `DynamicStateMachineEngine.java`：状态转移矩阵 + `ApplicationContext.getBean(name, type)` 动态拉取执行动作 Bean。
    - `action/`：`NotifyMerchantAction`、`DispatchRiderAction`、`AutoRefundAction`。
    - `controller/CareerDemoController.java`：暴露 `/api/demo/*` 演示端点（端口 `8080`）。
- **测试入口**：`src/test/java/.../StarterAllModulesTest.java`

---

### 2. `career-payment-saas`（滴滴国际化支付与清结算 SaaS）
- **核心定位**：复刻真实出海支付场景（拉美 PIX、SPEI、OXXO），解决跨国网络抖动与复杂资金对账。
- **模块目录**：
  - `channel/DynamicPaymentRouter.java`：
    - 针对跨国网络延迟高、易熔断痛点，建立通道健康度动态算分模型：
      $$\text{Score} = \text{SuccessRate} \times 70 + \frac{\max(0, 1000 - \text{Latency})}{1000} \times 30 + \text{BaseWeight}$$
    - 低于 50% 成功率硬熔断，动态调度最优可用渠道。
  - `ledger/SettlementLedgerEngine.java`：
    - 金融级**复式记账试算平衡引擎**，严格遵循会计恒等式“有借必有贷，借贷必相等”。
    - 流水包括：银行渠道借记清算款，对应贷记商户应付款、平台技术抽成、代扣增值税、骑手配送费。
  - `controller/PaymentDemoController.java`：
    - `/api/payment/route-best`：实时选出最高评分健康渠道。
    - `/api/payment/settle-order`：输入订单金额，输出完整复式记账平衡明细凭证（端口 `8081`）。
- **测试入口**：`src/test/java/.../PaymentModulesTest.java`

---

### 3. `career-agent-diagnose`（Witty 智能运维与 Skill 树路由）
- **核心定位**：对齐 openEuler Witty 智能运维架构与大模型智能体（Agent）工程落地。
- **模块目录**：
  - `alert/AlertStormSynthesizer.java`：
    - 微服务突发雪崩时（每秒几千条细碎警报），按 `ServiceName + ErrorCode` 自动收敛为单一高阶事故（Incident），提取受影响 Pod 列表，降低 90% 告警噪音。
  - `skill/SkillTreeRouter.java`：
    - 解决 Agent 挂载海量工具（200+）时大模型选路迷茫与 Token 爆炸问题。
    - 引入**两阶段剪枝路由**：
      1. **粗排**：推导故障领域（`INFRA` / `BUSINESS` / `NETWORK`）；
      2. **精排**：仅在目标子树内进行模式匹配，将候选工具集压缩至 Top-3。
  - `controller/AgentDemoController.java`：
    - `/api/agent/synthesize-alerts`：模拟海量 Pod 告警风暴实时收敛。
    - `/api/agent/route-skill`：输入故障症状自然语言，输出两阶段精准召回的排障 Skill（端口 `8082`）。
- **测试入口**：`src/test/java/.../AgentModulesTest.java`

---

## 三、各服务本地启动体验

| 子模块 | 独立启动命令 | 默认端口 | 核心体验接口 |
| :--- | :--- | :--- | :--- |
| `career-starter-basics` | `mvn spring-boot:run` | `8080` | `http://localhost:8080/api/demo/health`<br/>`http://localhost:8080/api/demo/aging-queue/simulate` |
| `career-payment-saas` | `mvn spring-boot:run` | `8081` | `http://localhost:8081/api/payment/route-best`<br/>`http://localhost:8081/api/payment/settle-order` |
| `career-agent-diagnose` | `mvn spring-boot:run` | `8082` | `http://localhost:8082/api/agent/synthesize-alerts`<br/>`http://localhost:8082/api/agent/route-skill` |
