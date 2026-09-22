---
name: llm-provider-compat
description: 把一个只内置 OpenAI / Anthropic / Gemini 的开源或第三方工具，跑在你手上的别家模型上（GLM 智谱、DeepSeek、Kimi、通义、本地 Ollama 等），或用某厂商的「Anthropic 兼容 / OpenAI 兼容」端点替换原生 SDK 的完整工作流。当用户说"我有 xx 的 key，怎么让它跑起来""这个开源项目能不能用国产模型""接一下兼容端点""换了 key 之后工具报错 / 模型不认 / 参数不支持 / 工具调用不生效"，或问某个外部工具能不能用自己手上的模型时使用——即使没说出 provider、兼容端点，只要意图是让外部工具用上非原生模型就应触发。涵盖接入点定位、探针先行的参数兼容矩阵、最小补丁与本地分支隔离、协议层 + UI 层双重验证、收尾清理。
---

# LLM Provider 兼容接入

## 概述

开源工具往往把可用模型硬编码成几家（`llm.py` 里一张枚举 + 一张 provider 映射表），你手上却只有别家的 key。本流程负责把这类工具接上你的模型，核心是**先探针、后补丁**：厂商兼容端点通常是为承接 Claude Code / 类似客户端而实现的，会主动容忍大量原生专有参数，凭猜测剥离参数往往白改一轮；而真正的硬门槛（多模态、工具调用）又不体现在错误信息里，只体现在效果上。

## 触发与豁免

**触发**：把外部工具从原生 provider 迁到你的 provider；用兼容端点替换原生 SDK；排查"key 明明有却跑不通"的接入问题。

**豁免**：
- 工具本身就支持你的 provider（如已支持 Ollama / OpenAI 兼容）→ 直接配环境变量，不需要本流程；
- 你自己从零写的项目 → 直接按目标 provider 的 SDK 写，没有兼容包袱；
- 纯读代码、不改不跑 → 不必走流程。

## 核心纪律

1. **探针先行，探针脚本先于补丁存在**。一次探针能覆盖端点、鉴权、模型名、多模态、工具调用、专有参数、流式事件七项，成本是一次 HTTP 调用；跳过它就得靠"改代码→跑→看报错"反复试，慢且容易改偏。
2. **优先找零代码改动杠杆**。官方 SDK 普遍支持从环境变量读 base URL（Anthropic 的 `ANTHROPIC_BASE_URL`、OpenAI 的 `OPENAI_BASE_URL`），所以大多数"改 client 构造"的需求其实不用改代码。先读建 client 那几行，确认它有没有显式传 `base_url`——没传就等于送你一个免费开关。
3. **通道选型看 API 形态，不看厂商名**。同一个厂商可能同时提供 Chat Completions 兼容和 Anthropic 兼容；而工具内部可能用的是 **Responses API** 或 **Messages API**。拿 Chat Completions 端点去接一个走 Responses API 的实现，是重写 provider，不是接兼容端点——**先确认工具实际调用的是哪个 API**，再决定走哪条兼容通道。
4. **多模态是硬门槛，要第一个测**。图像/音视频类工具换纯文本模型必然失败，且失败形态是"模型开始胡编"而不是清晰报错。尽早测出没有视觉能力，就能及时改推别的方案，而不是在补丁上越陷越深。
5. **补丁改映射层，不改架构**。最小补丁通常只有"模型名改写"一处；不要顺手改前端下拉、provider 选择逻辑、提示词，那些都会放大与上游的 diff，让以后 `git pull` 冲突不断。
6. **补丁放进本地分支 + 环境变量开关**。分支隔离让上游主线永远干净（`git checkout main && git pull`），env 开关让补丁在没配 key 的环境里等于不存在，两份代码共用一套源码。
7. **验证分两层：协议层先证通，UI 层再证可用**。协议层（WS / HTTP 脚本）排掉 provider 兼容问题，UI 层（真实浏览器）排掉前端接线问题。只做一层，出问题时无法定位是哪一层的锅。

## 分阶段工作流

### 阶段 0：定位接入点（只读）

产物：一份"接入点清单"，写清补丁该落在哪几行。

1. 找到 **provider 映射表**，确认工具把哪些模型名归到哪个 provider（别靠模型名字符串猜：`claude-*` 未必走 Anthropic 通道，`gpt-*` 未必走 OpenAI 通道）；
2. 找到 **建 client 的位置**，检查是否显式传了 `base_url`；
3. 找到 **请求组装的位置**，逐条抄下工具会发出的**专有参数**（thinking / reasoning effort / cache control / max_tokens 上限 / 工具级扩展字段）；
4. 找到 **实际调用的 API**（`responses.create`？`chat.completions`？`messages.stream`？），这决定阶段 1 探针打哪个端点；
5. 确认**成本/配额相关逻辑**对未知模型的行为（很多工具按定价表算钱、超限中止；未定价模型可能被直接跳过，也可能报错——查代码，别假设）；
6. 找一圈**前端的模型选择 UI**：有些工具的模型下拉是摆设，真实模型由后端按可用 key 自动选（`ANTHROPIC_ONLY_MODELS` 之类），这种反而更好接。

### 阶段 1：探针（先验证，再改代码）

产物：**参数兼容矩阵**——哪几项要剥、哪几项必须留、上限多少、有没有硬门槛不满足。

写一个一次性脚本（放系统临时目录，别进仓库），按顺序打七枪，每枪只加一个变量，便于归因：

| # | 探针 | 看什么 |
|---|---|---|
| 1 | 最小文本请求 | 端点地址、鉴权方式、模型名是否被接受 |
| 2 | 图片 / 音频输入 | **多模态硬门槛** |
| 3 | 工具定义 + 要求必须调用工具 | 工具调用是否生效（看返回里有没有工具调用块） |
| 4 | 工具结果回传（含媒体，如截图） | 多轮工具循环是否成立 |
| 5 | 阶段 0 抄下来的每个专有参数 | 逐项加，看是容忍、忽略还是报错 |
| 6 | 工具的最大 `max_tokens` | 是否超限，实际上限多少 |
| 7 | `stream=true` | 事件序列是否是 SDK 期待的标准序列 |

判读要点：
- **200 不等于兼容**。第 3、4 枪必须看返回体里**真的有没有工具调用块**，而不是看 HTTP 状态码；
- 报错信息里的字段名直接指向要剥的参数，比猜快得多；
- 厂商常为承接第三方客户端而**原样放行**大量专有参数（包括顶层 cache control），第 5 枪大概率全绿——**这就是不要预先剥离的原因**。

**止损点**：第 2 枪失败（无多模态）就直接停下来向用户说明，改推其他方案，不要再往下做补丁。

### 阶段 2：最小补丁 + 隔离

产物：一个本地分支上的一个提交，diff 控制在十行内。

1. 在克隆/检出目录内 `git checkout -b <local-分支名>`，**不要动上游 remote**；
2. 在配置模块加一个开关变量（如 `XXX_MODEL_OVERRIDE`），由环境变量注入；
3. 在**模型名映射函数**里加旁路：开关开启时直接返回你自己的模型名，其它逻辑（参数组装、provider 选择、前端）一律不动；
4. **按探针矩阵决定是否剥参数**——矩阵全绿就一行都别剥；
5. 用脚本验证补丁生效：打印各原始模型名映射后的结果、SDK client 的 base_url、成本逻辑对未知模型的行为。

配置文件（`.env` 之类）通常已在 `.gitignore` 内，密钥只写在那里，**绝不进任何提交、文档或对话摘录**。

### 阶段 3：端到端验证（两层）

产物：可复现的成功证据。

**协议层**：写脚本直接打工具的对外协议（WebSocket / HTTP），走完整业务链路，观察
- 是否所有并行任务都完成、有没有静默失败；
- **工具调用序列**是否出现（说明 agent 循环真的跑起来了，而不只是返回了文本）；
- 中间状态（思考、写文件、渲染预览）是否按预期出现。

**UI 层**：用 Playwright 驱动真实浏览器（浏览器装在工具自己的 venv 里最省事），
- 用 `localStorage` 预置前端设置，**别去点自定义下拉组件**——那是脆弱的自动化，而设置项本身能直接写；
- 上传输入 → 触发 → 轮询到状态空闲（等待条件用"忙碌标记消失"，不要用"检测到输出"，输出在流式过程中就会出现，容易误判为完成）；
- 截图留证，并捕获 `console` / `pageerror`。

判定成功：并行任务全部完成、无未捕获异常、产物与输入语义一致。

### 阶段 4：清理与落库

1. 终止进程：**按命令行特征过滤，不要按进程名杀**（同名进程可能包括你自己）；注意工具自身可能派生浏览器子进程，一并收掉；
2. **复查端口真的释放**——杀完不复查等于没清理；
3. 提交补丁（提交信息写清"为什么只需要改这一处"，把探针结论写进 body，未来看 diff 的人才知道那些参数为什么没剥）；
4. 删掉临时目录里的探针脚本与产物，或明确告知用户位置。

## 示例

**实战：screenshot-to-code（FastAPI + React）接 GLM Coding Plan**

- 阶段 0 发现：provider 映射表硬编码 OpenAI / Anthropic / Gemini；请求组装会发 `cache_control`、`thinking:{type:adaptive}`、`output_config:{effort}`、`max_tokens=50000`，还带工具级扩展字段；OpenAI 通道走 **Responses API**（`client.responses.create`），Anthropic 通道走 `messages.stream`；建 client 时**未显式传 `base_url`**（→ 免费杠杆）；前端模型下拉在真实生成路径里**不生效**（模型由后端按可用 key 自动选）。
- 阶段 1 结论：智谱 Anthropic 兼容端点（`https://open.bigmodel.cn/api/anthropic`，`api.z.ai` 同源）接受 `glm-5.3-flash`，多模态可正确读图，工具调用与工具结果回传成立，专有参数**全部原样放行**，`max_tokens=50000` 与五档 effort 均被接受，流式事件序列标准 → **无需剥离任何参数**。
- 阶段 2 补丁：`config.py` 加 `GLM_MODEL_OVERRIDE`（4 行），模型名映射函数加 3 行旁路。**共 2 文件 8 行**，前端零改动，走 `ANTHROPIC_BASE_URL` 环境变量重定向，`factory.py` 一行未动。
- 阶段 3 验证：协议层 4 个并行任务全部完成，工具序列 `create_file → screenshot_preview → edit_file` 出现；UI 层 4 个变体 39 秒内完成、无控制台异常、渲染结果与输入截图一致、追加指令被采纳。
- 参考实现：本地克隆 `.thirdparty/screenshot-to-code` 的 `local-glm` 分支（该目录不入父仓版本控制，仅本机可见）。

## 陷阱速查

| 陷阱 | 规避 |
|---|---|
| 以为兼容端点会拒绝原生专有参数，提前大改 | 第 5 枪单独测；这类端点常为承接官方客户端而主动容忍 |
| 靠模型名猜 provider | 读代码里的 provider 映射表 |
| 拿 Chat Completions 端点接 Responses API 实现 | 阶段 0 先确认实际 API 形态，形态不符就换通道或放弃该工具 |
| 只测文本、不测多模态 | 图像类工具第 2 枪必须先测，失败即止损 |
| 只测 HTTP 200，不看返回体结构 | 工具调用这类能力只能从返回体里看出来 |
| 顺手改前端 / 架构 | 补丁只碰映射层，diff 越小 `git pull` 越太平 |
| 假设未定价模型会被成本上限拦死 | 读代码确认（常见实现是 `None` 直接跳过上限检查） |
| 轮询 UI 时用"检测到输出"当完成条件 | 流式输出早期就会出现；要用"忙碌标记消失" |
| 自动化去点自定义下拉 | 用 `localStorage` 直接写设置项 |
| Windows 下 Python 写 `/tmp/xxx` | 那是 git bash 的虚拟路径，Python 看不到；用 `os.environ["TEMP"]` |
| 脚本从 stdin 跑时 `load_dotenv()` 报 AssertionError | `find_dotenv()` 依赖调用栈；显式传路径 `load_dotenv(".env")` |
| 按进程名杀进程 / 杀完不复查端口 | 按命令行特征过滤；杀完用 `Get-NetTCPConnection` 复查 |

## 验证片段

```powershell
# 端口是否真的释放
foreach ($port in 7001, 5173) {
  $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($c) { "占用: $port (pid $($c[0].OwningProcess))" } else { "已释放: $port" }
}
```

```powershell
# 按命令行特征清理（先只列不杀，确认无误再 Stop-Process）
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -and ($_.CommandLine -like '*uvicorn*main:app*' -or $_.CommandLine -like '*<项目目录>*') } |
  Select-Object ProcessId, Name, CommandLine
```

```bash
# 最小探针：先确认端点、鉴权、模型名
curl -s -m 40 -w "\n[HTTP %{http_code}]\n" "$BASE/v1/messages" \
  -H "x-api-key: $KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
  -d '{"model":"<你的模型>","max_tokens":64,"messages":[{"role":"user","content":"reply ok"}]}'
```
