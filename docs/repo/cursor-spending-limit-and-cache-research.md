# Cursor 额度限制与高级模型缓存未命中调研

日期: 2026-10-07
问题: Cursor 如何设置额度限制？高级模型多轮工具调用 + 缓存未命中导致额度暴涨怎么办？

## 1. 核心结论（先看这个）

1. 个人版（Pro/Pro+/Ultra）防暴涨只有两招：`Dashboard > Spending` 里 **关掉 On-demand usage**，或 **设 Monthly Spend Limit**。关掉后 included usage 用完即停，不会再扣费。
2. Teams 默认开启 on-demand，需管理员在 Dashboard 关或设限。
3. Spend Limit 不是硬截断：强制有延迟，超出的小额部分会以 `spend-limit credit（临时抵免，非退款）` 免掉；但本周期内你一旦上调限额，这部分可能被重新计费。
4. 你遇到的“高级模型多轮工具反复触发 + 缓存没命中”在计费上是最贵组合：以 Claude Fable 5.1 为例，Cache Read 仅 $0.25/M tokens，而 Cache Miss 按 Input $10/M 收，相差 40 倍；Output 更贵 $50/M。每轮工具调用都重发大上下文 + 产生大输出，费用翻倍涨。

## 2. 在哪里设置（第一手路径）

- 入口：`https://cursor.com/dashboard/spending` 下的 Spending Tab。
  - 必须先启用 on-demand 才能看到并设置 spend limit。
  - 改为 `No Limit` 即取消限制；修改即时生效。
  - 来源：https://cursor.com/help/account-and-billing/spend-limits
- 查账单：`https://cursor.com/dashboard` > Billing & Invoices，分为 Included Usage / On-Demand Usage 两栏。on-demand 有独立 invoice 和 line item。
  - 来源：https://cursor.com/help/account-and-billing/overages
- 改支付方式/开发票：`cursor.com/dashboard/billing` > Manage Subscription（跳 Stripe portal）。
  - 来源：https://cursor.com/docs/account/billing

## 3. 计费模型（决定你怎么被扣钱）

- 两个池子，按月随账单周期重置：Cursor Models 池（Grok 4.5/4.6/4.7、Composer 2.5）+ Other Models 池（第三方按 API 价，含 Claude/GPT/Gemini）。
  - 来源：https://cursor.com/docs/account/pricing
- 超出 included 后的两条路：开 on-demand 按同 API 价现付；或升级套餐换更多 included。请求不会被降质/降速。
  - 来源：https://cursor.com/docs/account/pricing#what-happens-when-i-reach-my-limit
- Teams/Enterprise 对第三方模型还要加收 Cursor Token Rate $0.25/M tokens；Grok/Composer 第一方模型免收。Auto 路由到第三方同样收。
  - 来源：https://cursor.com/docs/account/pricing、https://cursor.com/help/account-and-billing/overages

## 4. 防暴涨操作清单（个人用户）

1. 立刻设限：Spending 设一个你能接受的 Monthly Spend Limit，例如 $20/$50。
2. 不想多花一分钱：直接关 on-demand。用完即停，下月自动恢复。
3. 升级只加 included，不解决失控调用；先限流再考虑 Pro+ ($60/mo) / Ultra ($200/mo)。
4. 日常省钱：默认用 Auto Cost / Composer / Grok / Gemini Flash 做多轮工具活，把 Claude Fable/Opus 留到最后决策/难 bug；关闭 Fast 模式和 Max Mode（Max 在老计划按 API 价 +20%）。
   - 来源：Max Mode 加价见 https://cursor.com/docs/account/pricing#max-mode；Auto 三档计费见同页 Auto modes。

## 5. 为什么“多轮工具 + 缓存未命中”这么贵

官方价目（每百万 tokens）：

| 模型 | Input | Cache Write | Cache Read | Output |
|---|---|---|---|---|
| Claude Fable 5.1 | $10 | $12.5 | $0.25 | $50 |
| Claude Opus 5.5 | $4 | $5 | $0.2 | $20 |
| Claude Sonnet 5.5 | $2 | $2.5 | $0.2 | $10 |

来源：https://cursor.com/docs/account/pricing#model-pricing

解读：

- 命中缓存时上下文增量极便宜（Fable 仅 $0.25）；未命中则每次全量按 $10 收。上下文 100k 的多轮 Agent，命中 vs 未命中一轮就差约 $1。
- 任何改动 prompt 前缀/工具结果顺序/系统提示/切换模型/超窗截断都会破坏缓存锚点，导致反复写缓存（$12.5）还享受不到读缓存。
- 工具循环还会同时放大 Output（Fable $50/M），长思考 + 反复修补是最烧钱形态。
- 对策：固定模型、别在中途改 Rules/别来回切 Auto 与指定模型、把任务拆小、让 Agent 一次读全再动手、限制 `max tool iterations`、优先用便宜模型跑循环。

## 6. 官方原文关键句摘录

- `Disable on-demand usage: On Individual plans, turn it off in your spending settings to stop requests once your included usage runs out.`（https://cursor.com/help/account-and-billing/overages）
- `Set a spend limit: Cap how much on-demand usage you're willing to pay that billing cycle.`（同上）
- `Enforcement is not instant, so usage can briefly exceed your spend limit... credited as a temporary spend-limit credit... If you raise the limit in the same cycle, we may bill some or all of that credit.`（https://cursor.com/help/account-and-billing/spend-limits、overages 两页一致）
- `Go to your dashboard under the Spending tab... On-demand usage must be enabled to view and set spend limits`（https://cursor.com/help/account-and-billing/spend-limits）

## 7. 待你确认

- 你的套餐是 Pro 还是 Teams？Teams 需要管理员操作。
- 要我帮你定一个限额数字（如 $30 封顶 + 关 on-demand 兜底）吗？
