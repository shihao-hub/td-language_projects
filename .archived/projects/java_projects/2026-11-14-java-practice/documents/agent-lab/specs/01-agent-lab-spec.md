# Spec: agent-lab — 智能故障诊断 Agent 快速上手项目

> 状态：已确认（源自 grill-me 共识书）
> 范围：教学/练习项目，纯 Java 21 + Spring Boot 3，位于 `java_projects/agent-lab`

## 1. 目标世界长什么样 (The Destination)

运维同学（或面试官）给出一段故障描述或一批原始告警，系统在**无人干预**的情况下：

1. 自主决定去查哪些数据（指标 / 日志 / 链路 / 历史案例），而不是被固定脚本牵着走；
2. 每查一步都能说明"我看到了什么、据此排除了什么"；
3. 最终产出一份结构化诊断报告：**根因 + 证据链 + 修复建议 + 置信度**；
4. 同一份报告自动沉淀进案例库，下次遇到相似故障能直接召回历史排障路径。

外部可感知的改变：**从"人翻十几个系统拼线索"变成"一句话提问 → 一份可复核的诊断报告"**。

## 2. 怎么算验收通过 (Acceptance Criteria & User Stories)

### 2.1 诊断准确性（核心）

| # | 场景 | 标准答案（根因） | 必须排除的干扰项 |
| :--- | :--- | :--- | :--- |
| S1 | 墨西哥支付成功率骤降 | 平台自身风控规则误杀（全渠道） | 单一 PSP 渠道告警最多 |
| S2 | 骑手位置上报延迟 | MQ 消费组积压（GPS 上报通道） | 恶劣天气告警最先出现 |
| S3 | 下单 P99 飙升 | 慢 SQL 导致连接池耗尽 | 连接池打满是结果非原因 |
| S4 | 商家接单超时 | 上游流量突增压垮下游接单服务 | 下游服务自身错误率升高 |
| S5 | 服务 OOM | 缓存击穿引发回源洪峰 | GC 日志指向内存泄漏假象 |

1. **准确性**：5 个场景各独立运行 3 次，**至少 4 个场景根因判定正确**；同一场景 3 次结果一致率 ≥ 2/3。
2. **证据链完整**：报告必须列出实际调用过的工具、每次观察到的关键数据、以及"为什么排除其他候选根因"的推理。
3. **轮次约束**：单次诊断的工具调用轮次 ≤ 8 轮（防止无限循环与 token 爆炸）。
4. **无幻觉工具**：Agent 不得调用未注册的工具；解析失败时必须回退重试，不得把解析错误当成工具结果。

### 2.2 交互与交付

5. **CLI**：`java -jar` 或 Maven exec 启动后，输入自然语言症状描述，逐轮打印 Thought/Action/Observation，最终打印报告。
6. **REST**：`POST /api/diagnose` 接收 `{"query": "...", "scenarioId": "..."}`，返回结构化 JSON 报告；非法输入返回 400 且不触发 LLM 调用。
7. **Web 演示页**：`GET /` 提供一个无构建链的单文件 HTML，可选择场景、发起诊断、流式或分段显示过程与最终报告。
8. **双通道**：只改配置（BaseURL / Model / Key）即可在本地 Ollama 与 opencode go 之间切换，Agent 行为契约不变。

### 2.3 Skill 化与告警收敛

9. **Skill 可扩展**：新增一类故障的排障路径 = 新增一个 Skill 定义（步骤、判断条件、可用工具），**不修改 Agent 主循环**。
10. **告警三级收敛**：输入一批原始告警，输出单一 Incident，包含：同维度聚合、拓扑抑制、时间窗关联三级结果，并给出"疑似根因"候选。
11. **告警收敛可解释**：被抑制的告警必须记录抑制原因（同服务/上游抑制/时间窗）。

### 2.4 RAG 案例库

12. **案例沉淀**：每次诊断结束自动写入案例库（问题描述、根因、证据摘要、排障路径）。
13. **语义召回**：新故障输入时召回 Top-K 相似历史案例；相似度达到阈值时，报告中显式标注"参考历史案例 XXX"。
14. **降级可用**：embedding 服务不可用时自动降级为关键词检索，诊断主流程不中断。

### 2.5 可观测与测试

15. **可观测**：每轮 LLM 调用打印模型名、耗时、输入/输出 token 数、解析结果。
16. **单测覆盖接缝**：解析层、工具层、检索层、收敛层均有单元测试；**禁止**编写依赖真实 LLM 输出内容的断言。
17. **构建**：`mvn -pl agent-lab test` 全绿；作为独立子模块加入父 POM，不修改现有三个项目。

## 3. 测试接缝 (Testing Seams)

- **主接缝（唯一行为观察点）**：`AgentRuntime.run(DiagnosisRequest) → DiagnosisReport`
  - 所有"诊断是否正确、轮次是否超限、证据链是否完整"的行为测试都从这里进、从这里出。
  - 测试时注入 `FakeLlmClient`（按脚本回放 Thought/Action/Observation 序列）与内存版 `TelemetryRepository`，**不启动 Spring、不联网**。
- **模型接缝**：`LlmClient.chat(List<Message>) → String`
  - 用于验证请求构造（URL、鉴权头、`x-opencode-session`）、超时与错误分类。
  - 真实模型只做冒烟验证（人工执行），不进 CI。
- **数据接缝**：`TelemetryRepository`（指标/日志/链路）与 `CaseRetriever`（案例检索）
  - 工具层测试只依赖这两个接口；文件实现与 embedding 实现各自独立测试。
- **Web 接缝**：`POST /api/diagnose`
  - 用 `MockMvc` 做契约测试：字段校验、错误码、响应结构。

**接缝理由**：LLM 输出天然不确定，若把断言写在模型文本上，测试会变成"今天绿明天红"的噪音源。把不确定性关进 `LlmClient` 这一个接口，其余全部确定性化，才能既测行为又不 flaky。

**测试原则**：只从接缝注入输入、捕获输出；严禁 mock 私有方法或断言内部调用顺序。

## 4. 明确不做什么 (Out of Scope)

- 不做自愈执行：只输出修复建议，不自动改配置、不执行脚本、不走审批流。
- 不接真实 Prometheus / Elasticsearch / Jaeger / K8s API。
- 不做多 Agent 并行编排（Planner/Executor/Verifier 的真实调度留作后续演进）。
- 不做用户体系、权限、会话持久化、审计。
- 不做前端工程化（无 npm、无构建链），演示页为单文件 HTML。
- 不做生产级 RAG 调优（不引入 rerank 模型、不做 chunk 策略实验）。
- 不做多语言/多时区/多币种的真实业务逻辑。
- 不修改 `career-starter-basics`、`career-payment-saas`、`career-agent-diagnose`。

## 5. 架构决策与环境依赖 (Architectural Invariants)

**A1. 内核与框架解耦**：第一层纯 Java（仅依赖 JDK + JDK HttpClient），可在无 Spring 环境下通过 `main()` 跑完整诊断；第二层 Spring Boot 只做装配与 HTTP 暴露。

**A2. 模型通道**：
- 默认本地 Ollama：`http://localhost:11434/v1`，`qwen2.5:7b`；
- 云端 opencode go：`https://opencode.ai/inference/go/openai/v1`，`deepseek-v4.1-flash`，需 `x-opencode-session` 头；
- 凭据不硬编码、不入库，从 `%APPDATA%\language_projects\agent-lab\{dev,prod}\config.json` 或环境变量读取。

**A3. 协议选择**：采用**文本 ReAct + 严格 JSON 段解析**，不依赖模型原生 function calling；解析器必须对多余文本、缺字段、非法工具名做容错与重试。

**A4. 数据目录**：运行时数据（案例库、日志、配置）落在 `%APPDATA%\language_projects\agent-lab\<dev|prod>\`；仓库内只保留只读的 `src/main/resources/dataset/`。

**A5. 数据集契约**：场景文件遵循统一结构（`scenario.json` + `metrics.json` + `app.log` + `trace.json`），schema 对标 AIOps Challenge 的 metric/log/trace 三模态与故障标注字段。

**A6. 端口**：`8083`，与现有 8080/8081/8082 不冲突。

**A7. 依赖边界**：不引入 Spring AI；embedding 调用走裸 HTTP；向量计算手写。
