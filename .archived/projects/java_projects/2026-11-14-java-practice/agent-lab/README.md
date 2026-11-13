# agent-lab

手写 ReAct 故障诊断 Agent 的练习项目。第一层是纯 Java 21 内核（不依赖 Spring），
第二层用 Spring Boot 暴露 Web 接口。目标是把 Agent 的核心机制写透，而不是调框架。

## 当前进度

- [x] T01 骨架 + 双通道模型客户端 + `query_metric` 工具 + CLI
- [ ] T02 四类工具 + 5 场景数据集
- [ ] T03 多轮循环 + 证据链 + 结构化报告
- [ ] T04 Skill 化
- [ ] T05 告警三级收敛
- [ ] T06 RAG 案例库
- [ ] T07 Spring Boot Web + HTML
- [ ] T08 调优与收口

## 目录

```
src/main/java/com/shihao/agent/lab/
├── config/     配置加载（环境变量 > config.json > 默认 Ollama）
├── llm/        模型接缝：LlmClient / OpenAI 兼容客户端
├── agent/      ReAct 解析、工具注册表、诊断主循环
├── telemetry/  数据接缝：TelemetryRepository 与文件实现
├── tool/       query_metric
└── LabCli.java CLI 入口
src/main/resources/dataset/<scenarioId>/  只读故障场景数据
```

## 配置

运行时配置读取 `%APPDATA%\language_projects\agent-lab\<dev|prod>\config.json`：

```json
{
  "base_url": "https://opencode.ai/inference/go/openai/v1",
  "model": "deepseek-v4.1-flash",
  "api_key": "oc_sk_xxx",
  "channel": "opencode"
}
```

也可用环境变量覆盖：`LAB_BASE_URL`、`LAB_MODEL`、`LAB_API_KEY`、`LAB_ENV`。
文件不存在时默认连接本地 Ollama（`http://localhost:11434/v1`，`qwen2.5:7b`）。

## 运行

```powershell
cd D:\Users\language_projects\java_projects\agent-lab
$env:JAVA_HOME="D:\Users\java\jdk-21"
D:\Users\java\maven\bin\mvn.cmd test
D:\Users\java\maven\bin\mvn.cmd -q exec:java "-Dexec.args=diagnose --scenario s1-payment-success-drop --query payment_success_rate_dropped"
```

切到本地 Ollama：

```powershell
$env:LAB_BASE_URL="http://localhost:11434/v1"
$env:LAB_MODEL="qwen2.5:7b"
$env:LAB_API_KEY="ollama"
```

## 已知限制

- T01 只有指标工具，日志/链路/案例工具在 T02 补齐。
- `qwen2.5:7b` 能跑通协议但诊断质量明显弱于云端模型，适合验证离线链路，不适合看效果。
- 当前输出是自然语言结论，结构化报告在 T03 落地。
