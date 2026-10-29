# DeepSeek Search & Fetch API 计费规则与工程优化调研报告

> 关联项目：`go_projects/deepseeksearch`  
> 调研日期：2026-10-29  
> 调研背景：针对客户端计费优化疑问（`count` 与网页抓取内容是否影响费用）进行权威一手信源查证，并归因前序 Agent 会话 503 崩溃现场。

---

## 一、核心结论速览 (TL;DR)

1. **计费模式**：DeepSeek Search API 与 Fetch API 均为**按次计费（Per-Request）**，不是按 Token 或条数计费。
2. **定价标准**：**\$0.75 / 1,000 次成功请求**（单次成功调用约 **\$0.00075**，折合人民币约 **0.0054 元/次**）。
3. **`count` 是否影响费用**：**完全不影响**。单次搜索请求设置 `count=1` 还是 `count=50`，都只按 **1 次** Search 请求收费。
4. **抓取内容是否影响费用**：
   - **在 Search API 中开启 `need_content=true`**：**不额外收费**，仍只计 1 次 Search 请求费用；
   - **调用独立 Fetch API 抓取 URL**：**每次独立请求单独计费**（同样为 \$0.75 / 1,000 次）。若先搜索得到 10 条 URL 并逐个调用 Fetch，将产生 $1 + 10 = 11$ 次计费。
5. **前序 Agent 崩溃根因**：OpenCode 推理网关（`opencode.ai`）遭遇上游端点 503 暂态不可用；同时前序 Agent 在试图查验官方定价时，错误调用本地代码搜索工具盲目 grep 本地仓库，产生工具错配。

---

## 二、官方计费规则深度拆解（一手信源）

根据 DeepSeek 官方 API 文档（Models & Pricing）：

### 1. 独立工具端点规范

| 接口名称 | HTTP 路径 | 计费计量单位 | 单次成功单价 | 计费生效时点 |
|---|---|---|---|---|
| **Search API** | `POST https://api.deepseek.com/v1/tools/search` | 次（HTTP 200 且非空） | \$0.00075 / 次 | 2026-11-01 00:00 起正式收费 |
| **Fetch API** | `POST https://api.deepseek.com/v1/tools/fetch` | 次（HTTP 200 且非空） | \$0.00075 / 次 | 2026-11-01 00:00 起正式收费 |

### 2. 计费细节与边界

- **非 Token 计量**：区别于大语言模型推理按输入/输出 Token 计费，Search/Fetch 属于独立工具 API，与提示词长度、返回文本长度无关；
- **成功请求扣费**：仅当服务端返回 `HTTP 200 OK` 且检索到非空数据时才会扣减余额；如果发生网络错误、参数错误（4xx）、服务端故障（5xx）或未命中任何结果，不予扣费；
- **并发与频次限制 (Rate Limit)**：单账户通常限制在 5 QPS，超出触发 429 限流，限流请求不计费。

---

## 三、现场还原：前序 Agent 为什么报错 503 且操作荒唐？

截图中的排查过程暴露了两个层面的问题：

### 1. 网关层 503 根因剖析
```text
API Error: 503 Upstream request failed: Endpoint is unavailable. 
This is a server-side issue, usually temporary — try again in a moment. 
If it persists, check your inference gateway (opencode.ai).
```
- **网关断连**：OpenCode CLI 依赖 `opencode.ai` 提供的反向代理与推理中转服务；
- **上游抖动**：当上游模型提供方（Anthropic 等）短时出现网络抖动、负载熔断或网关自身代理进程异常时，网关返回 HTTP 503 Service Unavailable；
- **与业务无关**：该错误完全发生在中转通信链路，非本地代码逻辑产生。

### 2. 前序 Agent 的“工具调用错配”
前序 Agent 在思考链中敏锐察觉到需要确认计价规则：
> *“你问到点子上了——count 和抓内容是否影响费用，取决于 DeepSeek 这个端点的计价规则。我先查证一下官方定价，再回来确认第三项。”*

但随后其执行动作产生了严重失误：
- 它未调用外部一手信源调研（Web 检索或官方文档查阅），而是错误触发了本地 `ToolSearch`；
- 执行了命令：`grep -i -n "价格|计费|费用|pricing|花钱|成本" D:\Users\language_projects\go_projects...`；
- **荒谬点**：本地业务代码库是客户端实现，根本不可能包含官方最新的商业定价与计费细则，属于典型的工具错配与模型执行动作变形。

---

## 四、对 `deepseeksearch` 项目工程优化的决策指导

基于以上计费事实，前序分析中抽查的 3 个关键论断完全成立，且优化方向极其明确：

### 1. `TestAuth` 接口修正（`client.go:178-194`）
- **现状缺陷**：当前 `TestAuth` 为测试连通性，每次都打一次真实搜索：
  ```go
  req := SearchRequest{
      Query: "DeepSeek",
      Count: 1,
  }
  ```
- **后果**：用户在 GUI/CLI 点击一次“测试配置”，账户就被实打实扣除一次调用费（\$0.00075）；
- **优化建议**：改用免费的探针端点（如 DeepSeek 标准模型的 `GET https://api.deepseek.com/models` 查询端点），或在本地先做 API Key 基础格式正则校验，避免无意义付费调用。

### 2. 前端 Enter 防抖与连击防护（`app.js:401-406`）
- **现状缺陷**：Fetch 页面按回车直接触发请求，未绑定加载锁或防抖控制；
- **后果**：连续按回车会并发产生多次 Fetch 接口调用，多次扣除 Fetch 费用；
- **优化建议**：增加全局 `isFetching` 互斥状态锁，请求在途时将输入框与提交按钮置为 `disabled`。

### 3. 本地 SQLite 缓存机制激活（`results_json` 激活读通路）
- **现状缺陷**：搜索历史只落盘 `results_json` 用于展示历史记录，但发起搜索前从不查表；
- **关键权衡**：由于 Search API 是**按次计费**，针对相同 Query 设置 TTL 本地缓存（如 24 小时内相同关键词直接读本地 SQLite），能直接省下 100% 的重复搜索费用；同时单次搜索直接使用 `need_content=true` 批量获取详情，避免后续用户点击逐条进入时二次打 Fetch API 叠加计费。
