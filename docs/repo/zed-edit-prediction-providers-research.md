# Zed 编辑器内置代码补全（Edit Prediction）工具调研与对比

> 调研日期：2026-09-22
> 适用环境：Zed Editor (Edit Prediction / Inline Completion)

---

## 1. 概述与背景

在 Zed 编辑器中，行内代码补全被命名为 **Edit Prediction（编辑预测）**。不同于传统仅在光标位置向后“追加文本”的代码补全，Zed 的 Edit Prediction 采用类似“预测下一步编辑动作”的机制，能够支持行内多处改动、多行重构甚至行内代码的删除与替换。

在 Zed 的设置界面（`Settings -> Edit Prediction`）中，用户可以看到多个主流补全提供商：
1. **GitHub Copilot**
2. **Mercury**（Inception Labs）
3. **Codestral**（Mistral AI）

三者在**技术架构（自回归 vs 扩散模型）**、**响应延迟（防抖时长）**、**计费模式（固定订阅 vs Token 计量）**等方面存在显著差异。

---

## 2. 三大提供商深度剖析

### 2.1 GitHub Copilot (GitHub / Microsoft / OpenAI)

#### 核心定位与背景
GitHub 与 OpenAI 联合推出的商业化 AI 代码辅助服务，是全球目前生态最成熟、用户量最大的代码补全工具。

#### 技术架构与工作原理
- **模型架构**：基于 OpenAI 定制优化的自回归 Transformer 模型（GPT-4o/mini 针对代码补全微调分支）。
- **FIM 与上下文感知**：深度集成 **Fill-in-the-Middle (FIM)** 技术，不仅感知光标前缀代码（Prefix），还结合光标后代码（Suffix）；同时通过后台 Context Engine，抓取当前工程中打开的文件、最近编辑的历史与语言结构生成动态 prompt。
- **默认防抖时长（Prediction Debounce）**：**75ms**。在敲击键盘暂停 75ms 后触发网络请求，平衡响应速度与请求开销。

#### 接入方式与计费
- **接入方式**：在 Zed 中点击 `Sign in to GitHub` 完成 OAuth 授权即可。
- **计费模式**：**纯订阅制（包月/包年，不限 Token）**
  - **Copilot Individual**：$10 / 月 或 $100 / 年（面向个人，学生/知名开源维护者有免费名额）；
  - **Copilot Business / Enterprise**：$19~$39 / 用户 / 月。
- **适合特点**：高频编写代码、不希望产生“Token 焦虑”的开发者。

#### 优缺点分析
- **优点**：
  - 语料覆盖最广泛，主流与非主流语言均能准确预测；
  - 订阅制成本固定，写代码无论多少次触发都不会额外计费；
  - 企业级合规与安全性控制完备。
- **缺点**：
  - 黑盒机制，无法调整模型参数、上下文窗口或切换自定义端点；
  - 在国内直连 GitHub API 可能会偶发网络不稳定，需要稳定的代理网络。

---

### 2.2 Mercury (Inception Labs)

#### 核心定位与背景
由 AI 新兴实验室 **Inception Labs** 开发的实时智能代码补全方案。它在补全领域引入了革命性的**扩散大语言模型（Diffusion-based LLM, dLLM）**。

#### 技术架构与工作原理
- **模型架构**：**Diffusion LLM（dLLM）**，而非传统的自回归（Auto-regressive）逐 Token 顺序生成。
- **并行生成与超高吞吐**：
  - 传统 Transformer 是“一个 Token 一个 Token 地往后吐”，串行依赖导致首字延迟（TTFT）和长文本耗时较高；
  - Mercury 采用扩散架构并行去噪与细化 Tokens，在主流标准 GPU 上能达到 **1,100+ tokens/s** 的极速吞吐；
- **默认防抖时长（Prediction Debounce）**：**0ms**！
  - 正因为其推理延迟极低，Zed 默认将其防抖设置为 0ms，实现“键盘停下即出建议”的极致跟手体验。
- **上下文能力**：Mercury 2.5 原生支持高达 **260K** 的长上下文窗口。

#### 接入方式与计费
- **接入方式**：在 Inception Labs 平台控制台生成 API Key，或通过环境变量 `MERCURY_AI_TOKEN` 配置并重启 Zed。
- **计费模式**：**API 按量计费（Pay-as-you-go）**
  - **输入价格**：约 $0.20 / 1M Tokens（缓存输入低至 $0.02 / 1M）；
  - **输出价格**：约 $0.75 / 1M Tokens；
  - （平台新注册通常赠送 1,000 万测试 Token）。

#### 优缺点分析
- **优点**：
  - **速度极致**：端到端延迟极低，补全极为丝滑流畅；
  - 超大上下文（260K），适合大型项目的复杂文件；
  - 创新扩散算法在小范围即时改写中响应迅速。
- **缺点**：
  - 按量计费，高频快速编写代码时持续产生 Token 消耗；
  - 作为新兴架构，在极其冷门/长链路逻辑推理的特定场景上，综合质量与传统千亿级大模型仍处于持续迭代期。

---

### 2.3 Codestral (Mistral AI)

#### 核心定位与背景
由欧洲顶级 AI 独角兽 **Mistral AI** 专为代码生成与研发场景打造的专用大语言模型（如 Codestral 22B 系列）。

#### 技术架构与工作原理
- **模型架构**：精细微调的高参数量自回归 Transformer 代码专用模型。
- **原生 Fill-in-the-Middle (FIM)**：Mistral 在训练期间就专门针对中间填空进行了深度强化，其在行内插值、结构性替换（中间修改函数体内实现）上逻辑极为严密。
- **语言支持**：专攻 80+ 种主流及现代编程语言（Python、Rust、Go、TypeScript、C++、Java 等）。
- **上下文窗口**：32k ~ 256k tokens。
- **默认防抖时长（Prediction Debounce）**：**150ms**。因模型参数量较大（22B级别），为避免频繁并发请求造成算力浪费和打断，预设了 150ms 缓冲。

#### 接入方式与计费
- **接入方式**：访问 Mistral 控制台（La Plateforme）获取 API Key，或设置环境变量 `CODESTRAL_API_KEY`；使用官方独立低延迟端点 `https://codestral.mistral.ai`。
- **计费模式**：**API 按量计费（极具性价比）**
  - **输入价格**：$0.30 / 1M Tokens；
  - **输出价格**：$0.90 / 1M Tokens；
  - （注意：Mistral 的 Le Chat Pro 订阅不涵盖此 API，需单独充值 API 账户）。
- **本地化拓展**：Codestral 开放了模型权重，如果具备本地高性能 GPU（如 24G+ 显存显卡），还可以通过 Ollama / vLLM 本地完全离线部署运行。

#### 优缺点分析
- **优点**：
  - **代码推理与准确度顶尖**：在代码补全的严谨性、语法正确率上综合表现极佳；
  - 原生 FIM 支持，特别适合在已有大段代码的中间穿插修改；
  - 开放权重，具备本地离线私有化运行的灵活性。
- **缺点**：
  - 推理延迟相比扩散模型稍慢，需要 150ms 防抖；
  - 依赖海外 API 访问，国内直连需要保证网络通畅。

---

## 3. 三大工具横向对比矩阵

| 维度 | GitHub Copilot | Mercury (Inception Labs) | Codestral (Mistral AI) |
| :--- | :--- | :--- | :--- |
| **所属机构** | GitHub (微软) / OpenAI | Inception Labs | Mistral AI |
| **核心底层架构** | 自回归 Transformer 代码定制版 | **扩散模型 (Diffusion LLM)** | 自回归 22B 代码专用大模型 |
| **生成机制** | 逐 Token 串行生成 + FIM | **并行生成与去噪优化** | 强化 FIM 逐 Token 生成 |
| **Zed 默认防抖** | **75ms** | **0ms**（零感知延迟） | **150ms** |
| **端到端生成速度**| 较快 | **极快**（>1,100 tokens/s） | 中等偏快 |
| **上下文窗口** | 依赖 Copilot 客户端策略（通常较小） | **260K Tokens** | **32K ~ 256K Tokens** |
| **计费方案** | **固定月费/年费**（$10/月起，无限量） | **按 Token 计费**（~$0.20/$0.75 每百万） | **按 Token 计费**（~$0.30/$0.90 每百万） |
| **接入门槛** | 需 GitHub 账号 + 付费订阅 / 教育包 | 需 Inception Labs 账户及 API Key | 需 Mistral 账户及 API Key |
| **离线/私有部署** | 不支持 | 不支持 | **支持**（开源权重，可配合 Ollama） |
| **国内网络适配** | 需代理或网络通畅 | 需代理或海外直连 | 需代理或海外直连 |

---

## 4. 选型建议与场景推荐

1. **选择 GitHub Copilot，如果**：
   - 你已经拥有 GitHub Copilot 订阅（或享受学生/开源维护者免费福利）；
   - 你是全天候高频编码者，希望固定费用封顶，不想担心 Token 消耗；
   - 追求最成熟稳定的生态与开箱即用的多文件上下文支持。

2. **选择 Mercury，如果**：
   - 你对补全的**延迟极其敏感**，追求“停手即见”的丝滑补全（0ms 防抖）；
   - 想要尝试最新一代基于**扩散模型（Diffusion LLM）**的革新技术；
   - 编写大型项目，需要 260K 超大上下文感知的代码编辑支持。

3. **选择 Codestral，如果**：
   - 你对**代码质量、逻辑复杂度和语法严谨性**要求极高（如 Rust、Go、现代 C++ 等严苛类型语言）；
   - 经常需要在已有函数或逻辑片段中间进行插入式修改（发挥其强大的 FIM 能力）；
   - 或者你拥有本地高性能硬件（如 RTX 3090/4090/Mac Studio），希望后续能通过 Ollama 做到完全离线运行。

---

## 5. 参考文献与官方数据源

- [Zed 官方文档 - Edit Prediction Providers](https://zed.dev/docs/edit-prediction)
- [Inception Labs 官方发布 - Mercury 2.5: Parallel Token Diffusion for Code](https://inceptionlabs.ai)
- [Mistral AI 官方文档 - Codestral & FIM API Reference](https://docs.mistral.ai/capabilities/code_generation/)
- [GitHub Copilot 官方定价与功能说明](https://github.com/features/copilot)
