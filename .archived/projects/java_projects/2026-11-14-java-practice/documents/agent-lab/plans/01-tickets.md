# Tickets: agent-lab 垂直切片看板

> 源规范：`../specs/01-agent-lab-spec.md`
> 推进纪律：一次只做一个切片，做完即 `/clear` 或新开会话再进下一个。

## 依赖图 (DAG)

```
T01 ──> T02 ──> T03 ──┬──> T04 ──┐
  │                    ├──> T06 ──┤
  │                    └──> T07 ──┤
  └──> T05 ───────────────────────┴──> T08
```

---

## T01 曳光弹：骨架 + 双通道模型 + 单工具 + 单轮 ReAct + CLI

**核心交付**：终端输入一句症状，真实模型返回一次工具调用请求，系统读到文件数据后把观察结果回传模型，模型输出初步结论。端到端一圈打通。

**测试接缝**：`AgentRuntime.run(DiagnosisRequest)`（注入 `FakeLlmClient`）；`LlmClient.chat` 的请求构造单独测。

**Blocked by**：None

**验收条件**：
- [x] `agent-lab` 作为子模块加入父 POM，`mvn -pl agent-lab test` 全绿
- [x] 配置从 `%APPDATA%\language_projects\agent-lab\dev\config.json` 或环境变量读取，缺失时给出可操作报错
- [x] Ollama 与 opencode go 双通道均可完成一次对话（opencode go 带 `x-opencode-session` 头）
- [x] `query_metric` 工具能读取 S1 场景指标文件并返回结构化结果
- [x] CLI 打印 Thought / Action / Observation / 结论四段
- [x] `FakeLlmClient` 驱动的单测覆盖"解析工具调用 → 执行 → 回填"路径

---

## T02 工具层补全 + 5 场景数据集

**核心交付**：四类工具（指标 / 日志 / 链路 / 案例）齐备，5 个场景的数据文件可被按场景 ID 加载，每个工具在 CLI 中可单独验证。

**测试接缝**：`TelemetryRepository` 文件实现；`ToolRegistry.execute(name, args)`。

**Blocked by**：T01

**验收条件**：
- [ ] `resources/dataset/` 下 5 个场景，每个含 `scenario.json` + `metrics.json` + `app.log` + `trace.json`
- [ ] 每个场景在 `scenario.json` 中标注标准根因与干扰项
- [ ] 4 类工具均注册进 `ToolRegistry`，非法参数返回明确错误而非抛栈
- [ ] 工具层单测覆盖：正常查询、时间窗过滤、场景不存在、字段缺失
- [ ] CLI 提供 `tools` 子命令逐个调用工具查看原始返回

---

## T03 多轮循环控制 + 证据链 + 结构化报告

**核心交付**：Agent 能自主多轮查证（≤8 轮），累积证据链并排除干扰项，最终输出 Markdown/JSON 诊断报告；5 个场景至少 4 个根因正确。

**测试接缝**：`AgentRuntime.run(DiagnosisRequest)`。

**Blocked by**：T02

**验收条件**：
- [ ] 轮次上限、非法工具名、JSON 解析失败均有确定行为（重试/终止/降级）
- [ ] 报告含：根因、证据链（工具+观察+排除理由）、修复建议、置信度
- [ ] `FakeLlmClient` 脚本化测试覆盖：正常收敛、超轮次、幻觉工具、解析失败
- [ ] 5 场景实跑，≥4 个根因正确，同一场景 3 次一致率 ≥2/3

---

## T04 Skill 化：诊断套路封装

**核心交付**：把"支付成功率骤降"等排障路径写成可复用 Skill 定义，Agent 加载后按步骤推进；新增 Skill 不需要改主循环。

**测试接缝**：`SkillLoader` + `AgentRuntime.run`。

**Blocked by**：T03

**验收条件**：
- [ ] Skill 定义包含：适用症状、步骤、判断条件、可用工具、终止条件
- [ ] 加载器能发现并解析多个 Skill，非法 Skill 给出可定位错误
- [ ] Agent 能根据症状匹配 Skill 并按其步骤执行
- [ ] 新增第 6 个 Skill 仅新增文件，主循环零改动（有测试证明）

---

## T05 告警三级收敛

**核心交付**：输入原始告警列表，输出单一 Incident（含聚合结果、被抑制告警及原因、疑似根因候选），CLI 可演示。

**测试接缝**：`AlertConverger.converge(List<RawAlert>)`。

**Blocked by**：T01（可与 T02/T03 并行）

**验收条件**：
- [ ] 同服务/同错误码/同地域聚合为一条
- [ ] 上游根因告警抑制下游派生告警，并记录抑制原因
- [ ] 时间窗内密集告警合并，跨时区统一 UTC
- [ ] 单测覆盖：纯聚合、纯抑制、时间窗、混合场景、空输入

---

## T06 RAG 案例库

**核心交付**：诊断结束自动沉淀案例；新故障输入时语义召回 Top-K 历史案例并在报告中引用。

**测试接缝**：`CaseRetriever.retrieve(query, k)`；`CaseRepository.save(report)`。

**Blocked by**：T03

**验收条件**：
- [ ] 案例写入 `%APPDATA%\language_projects\agent-lab\<env>\cases\`，格式含向量与原文
- [ ] embedding 调用走裸 HTTP，失败自动降级关键词检索且主流程不中断
- [ ] 余弦相似度手写实现，有已知向量对的单测
- [ ] 相似案例达到阈值时报告标注"参考历史案例 XXX"
- [ ] 同场景二次诊断能召回首次案例

---

## T07 Spring Boot Web + 单文件 HTML

**核心交付**：`POST /api/diagnose` 返回结构化报告；`GET /` 页面可选场景、发起诊断、展示过程与报告。

**测试接缝**：`POST /api/diagnose`（MockMvc）。

**Blocked by**：T03

**验收条件**：
- [ ] 非法请求返回 400 且不触发 LLM
- [ ] 正常请求返回规范 JSON（根因/证据链/建议/置信度）
- [ ] 单文件 HTML 无构建链，可在浏览器完成一次完整诊断
- [ ] 端口 8083，与现有服务并存不冲突
- [ ] 内核仍可脱离 Spring 独立运行（`main()` 冒烟）

---

## T08 准确率调优 + 演示收口

**核心交付**：5 场景稳定达标，双通道冒烟通过，项目 README 与演示脚本就绪。

**测试接缝**：`AgentRuntime.run`（回归集）+ 全量 `mvn test`。

**Blocked by**：T03, T04, T05, T06, T07

**验收条件**：
- [ ] 5 场景 × 3 次实跑结果记录在案，达标线满足 spec §2.1
- [ ] Ollama 与 opencode go 各跑通 1 个场景
- [ ] 全量测试全绿，无 flaky
- [ ] README 含架构图、启动命令、5 场景演示步骤、已知限制
- [ ] 工作区无临时脚本/残留进程
