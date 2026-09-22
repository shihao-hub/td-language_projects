# Fill-in-the-Middle (FIM) 技术原理解析与各家模型实现调研

> 调研日期：2026-09-22
> 核心主题：自回归代码语言模型的 Fill-in-the-Middle (FIM) 补全与中间填充机制
> 一手信源：OpenAI 原创论文 (arXiv:2207.14255)、BigCode StarCoder (arXiv:2305.06161 / arXiv:2402.19173)、Meta Code Llama (arXiv:2308.12950)、DeepSeek-Coder (arXiv:2401.14196 / arXiv:2406.11931)、Qwen2.5-Coder (arXiv:2409.12186)、Mistral Codestral 官方发布、vLLM / llama.cpp 官方规范与接口

---

## 1. 概述与核心背景

在代码补全与实时辅助编辑场景（如 GitHub Copilot、Cursor、Continue.dev、Zed Edit Prediction）中，开发者大多数时候并不是单纯在文件最末尾“从左到右追加文本”，而是在已有代码的**中间位置**进行插入、重构、修改函数实现或填补参数。

传统的因果自回归语言模型（Causal Decoder-only Transformers，如 GPT-2、GPT-3）依赖标准从左向右（Left-to-Right, L2R）的因果注意力掩码，天然只能感知光标前文（Prefix），无法感知光标后文（Suffix），导致生成的代码极易与下文已有的闭合括号、变量名或返回语句产生语义冲突与重复。

**Fill-in-the-Middle (FIM)** 技术通过在数据预训练/微调阶段进行确定性的上下文片段置换（Data Transformation），**在完全不改动因果自回归模型架构、不需要任何双向 Encoder、不需要定制注意力掩码（Attention Mask）的前提下**，使单向自回归模型获得了强大的双向上下文填充（Infilling）能力。

---

## 2. 基础理论与数学机制 (Foundations)

### 2.1 一手论文与起源
- **核心奠基论文**：OpenAI 团队发表于 2022 年 7 月的论文：
  * *Efficient Training of Language Models to Fill in the Middle* (Mohammad Bavarian\*, Heewoo Jun\*, Nikolas Tezak, John Schulman, Christine McLeavey, Jerry Tworek, Mark Chen)
  * arXiv: [arXiv:2207.14255](https://arxiv.org/abs/2207.14255)
- **前置探索**：
  * Donahue et al. (2020), *Enabling Language Models to Fill in the Blanks* ([arXiv:2005.05339](https://arxiv.org/abs/2005.05339))：早期在小规模 GPT-2 上提出的 Infilling by Language Modeling (ILM)；
  * Raffel et al. (2020), T5 ([arXiv:1910.10683](https://arxiv.org/abs/1910.10683))：基于 Encoder-Decoder 架构的掩码跨度破坏（Span Corruption）。

### 2.2 工作原理：将双向填充映射为单向自回归
设原始文档 $D$ 由 Token 序列组成，在切分点 $u, v$ ($0 \le u \le v \le |D|$) 处将文档划分为三个连续片段：
1. **前缀 (Prefix, $P$)**：光标前的代码片段 $[x_1, \dots, x_u]$
2. **中间待补全内容 (Middle, $M$)**：光标处的缺失代码 $[x_{u+1}, \dots, x_v]$
3. **后缀 (Suffix, $S$)**：光标后的已有代码 $[x_{v+1}, \dots, x_N]$

FIM 在词表中引入三个哨兵特殊 Token（Delimiter Tokens）：
- $\tau_{\text{pre}}$（如 `<fim_prefix>`, `<PRE>` 等）
- $\tau_{\text{suf}}$（如 `<fim_suffix>`, `<SUF>` 等）
- $\tau_{\text{mid}}$（如 `<fim_middle>`, `<MID>` 等）
- 终止标识 $\tau_{\text{eot}}$（如 `<EOT>`, `<|endoftext|>` 等）

通过重新排列序列，将 Middle 放置于整个序列的最末端：

```text
原始代码文档：
[---------------- Prefix (P) ----------------][---- Middle (M) ----][---------------- Suffix (S) ----------------]

PSM 排列变换：
<PRE> [-------- Prefix (P) --------] <SUF> [-------- Suffix (S) --------] <MID> [---- Middle (M) ----] <EOT>

SPM 排列变换：
<SUF> [-------- Suffix (S) --------] <PRE> [-------- Prefix (P) --------] <MID> [---- Middle (M) ----] <EOT>
```

在标准的下三角因果注意力机制下：
- $P$ 中的 Token 仅依赖前置的前缀 Token；
- $S$ 中的 Token 能注意到 $P$（在 PSM 格式下）；
- **关键机制**：末尾生成的 $M$ 中的每一个 Token，因果注意力都能完整覆盖前方的 $P$ 与 $S$。模型自然而然地学会在已知前文与后文的联合约束下逐步预测中间缺失代码。

### 2.3 PSM 与 SPM 变换模式对比
Bavarian et al. (2022) 形式化定义了两种对偶排列：
1. **Prefix-Suffix-Middle (PSM)**：
   $$T_{\text{PSM}}(D) = \tau_{\text{pre}} \circ P \circ \tau_{\text{suf}} \circ S \circ \tau_{\text{mid}} \circ M \circ \tau_{\text{eot}}$$
2. **Suffix-Prefix-Middle (SPM)**：
   $$T_{\text{SPM}}(D) = \tau_{\text{suf}} \circ S \circ \tau_{\text{pre}} \circ P \circ \tau_{\text{mid}} \circ M \circ \tau_{\text{eot}}$$

#### 采样超参数配置（经验法则）
- **FIM 数据变换概率 ($p_{\text{fim}}$)**：通常取 **0.5**。即预训练语料中有 50% 保持原始从左到右因果序列，另外 50% 进行 FIM 打乱。
- **模式混合概率 ($p_{\text{spm}}$)**：在进入 FIM 变换的样本中，通常 50% 为 PSM，50% 为 SPM，让模型同时具备两种格式的泛化能力。
- **切分点均匀分布**：$u \sim \mathcal{U}(0, |D|)$，$v \sim \mathcal{U}(u, |D|)$，这使得切出的 $M$ 长度天然覆盖单 Token、单行表达式、跨多行循环直至整段函数体。

### 2.4 "FIM for Free"（免费午餐特性）
OpenAI 论文中最为著名的实验结论是 **"FIM for free"**：
- 在 50% 的 FIM 变换率下（$p_{\text{fim}} = 0.5$），模型不仅获得了双向补全能力，而且在标准的左向右因果文本生成评估（如 HumanEval、MBPP 代码生成及通用语言模型困惑度 Perplexity）上，**完全没有性能退化**。
- 这意味着无需增加模型参数，无需定制两套模型，代码大语言模型在预训练阶段天然就应该加入 FIM。

### 2.5 文档级切分 vs. 上下文窗口级切分 (Document-level vs Context-level)
- **Document-Level FIM**：先对单个源码文件执行 FIM 变换，再做定长打包（Context Packing）。缺点是当文件长度超过上下文窗口时，滑动截断容易导致 Middle 片段与对应的 Prefix/Suffix 分离到不同 chunk 中，破坏因果依赖。
- **Context-Level / Chunk-Level FIM**：先将文件切分/拼装到模型固定上下文窗口内（如 4K/8K tokens），在窗口边界内部再做 FIM 切分与置换。保证了每个 Middle 一定能在当前上下文中看到其对应的 Prefix 和 Suffix。Bavarian 等人证明 Context-level 在实际大模型训练中收敛显著更稳定。

---

## 3. 主流代码大模型 FIM 格式与 Token 定义矩阵

各主流实验室在大模型中对 FIM 哨兵 Token 的命名与格式规范存在明显差异，如下表所示：

| 模型家族 | 代表模型 | 核心文献 / 源码出处 | 前缀 Token | 后缀 Token | 中间 Token | 结束 Token | 默认排列 | 关键注意事项 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenAI** | `code-cushman-001`, `code-davinci-002`, `text-davinci-002/003` | Bavarian et al. (arXiv:2207.14255, 2022) | `<|fim_prefix|>` | `<|fim_suffix|>` | `<|fim_middle|>` | `<|endoftext|>` | PSM / SPM 均支持 | 在 OpenAI Legacy API 中通过 `/v1/completions` 的 `suffix` 字段调用 |
| **BigCode** | StarCoder, StarCoder2, SantaCoder | Li et al. (arXiv:2305.06161, 2023); Lozhkov et al. (arXiv:2402.19173, 2024) | `<fim_prefix>` | `<fim_suffix>` | `<fim_middle>` | `<|endoftext|>` | PSM (50%) + SPM (50%) | 引入 `<fim_pad>`；早期 SantaCoder 曾使用带短横线的 `<fim-prefix>` |
| **Meta** | Code Llama (7B, 13B, 70B) | Rozière et al. (arXiv:2308.12950, 2023) | `<PRE>` | `<SUF>` | `<MID>` | `<EOT>` | PSM (为主) / SPM | **重大避坑点**：官方明确指出 **Code Llama 34B 没有训练 FIM**，仅 7B/13B/70B 支持 |
| **DeepSeek** | DeepSeek-Coder, DeepSeek-Coder-V2 | Guo et al. (arXiv:2401.14196, 2024); DeepSeek-AI (arXiv:2406.11931, 2024) | `<｜fim begin｜>` | `<｜fim hole｜>` | `<｜fim end｜>` | `<｜end of sentence｜>` | PSM | **字符坑**：中间使用**全角竖线** `｜` (`U+FF5C`)，直接复制半角竖线 `|` 会导致分词错误 |
| **Qwen** | Qwen2.5-Coder (0.5B ~ 32B) | Hui et al. (arXiv:2409.12186, 2024) | `<|fim_prefix|>` | `<|fim_suffix|>` | `<|fim_middle|>` | `<|endoftext|>` | PSM | 原生支持仓级别多文件 Token：`<|repo_name|>`, `<|file_sep|>` |
| **Mistral** | Codestral 22B | Mistral AI 官方文档 (2024-05-29) | `[PREFIX]` | `[SUFFIX]` | `[MIDDLE]` | `</s>` | **严格 SPM** | 提示词构造为 `<s>[SUFFIX]{suf}[PREFIX]{pre}`，且提供专门的 `/v1/fim/completions` 端点 |

---

## 4. 详细格式规范与代码构造

### 4.1 StarCoder / StarCoder2 (BigCode)
```python
# PSM 构造
prompt = f"<fim_prefix>{code_prefix}<fim_suffix>{code_suffix}<fim_middle>"

# SPM 构造
prompt = f"<fim_suffix>{code_suffix}<fim_prefix>{code_prefix}<fim_middle>"
```

### 4.2 Meta Code Llama
```text
# 规范 PSM 格式（注意空格敏感）
 <PRE> {code_prefix} <SUF>{code_suffix} <MID>
```
*Code Llama 官方仓库源码 `codellama/generation.py` 中预置了标准的 format 工具函数。*

### 4.3 DeepSeek-Coder (V1 & V2)
```python
# 必须使用 Unicode 全角竖线 U+FF5C: '｜'
FIM_BEGIN = "<｜fim begin｜>"
FIM_HOLE  = "<｜fim hole｜>"
FIM_END   = "<｜fim end｜>"

prompt = f"{FIM_BEGIN}{code_prefix}{FIM_HOLE}{code_suffix}{FIM_END}"
```

### 4.4 Qwen2.5-Coder
```text
# 单文件补全格式 (PSM)
<|fim_prefix|>{code_prefix}<|fim_suffix|>{code_suffix}<|fim_middle|>

# 仓库级 (Repo-level) 多文件上下文扩展补全格式
<|repo_name|>{repo_name}
<|file_sep|>{dependency_file_path}
{dependency_file_content}
<|file_sep|>{active_file_path}
<|fim_prefix|>{code_prefix}<|fim_suffix|>{code_suffix}<|fim_middle|>
```

### 4.5 Mistral Codestral
Codestral 默认采用 **SPM（Suffix-Prefix-Middle）** 风格构建：
```text
<s>[SUFFIX]{code_suffix}[PREFIX]{code_prefix}
```
官方 `mistral-common` Python SDK 示例：
```python
from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
from mistral_common.tokens.tokenizers.base import FIMRequest

tokenizer = MistralTokenizer.v3()
req = FIMRequest(prompt=code_prefix, suffix=code_suffix)
tokenized = tokenizer.encode_fim(req)
```

---

## 5. 工程落地与推理优化关键考量

### 5.1 光标上下文预算分配（Context Window Budgeting）
在编辑器 IDE 行内补全时，要求极低的端到端延迟（TTFT < 100ms），通常不会把 8K/32K 窗口塞满，而是截取光标周围 2K~4K Tokens：
- **前缀 (Prefix)**：占据 65% ~ 80% 的预算（从光标位置向前截取，越靠近光标权重越高）；
- **后缀 (Suffix)**：占据 20% ~ 35% 的预算（从光标位置向后截取，保留下文的闭合结构和调用）；
- **截断策略**：前缀从文件头方向向上丢弃，保留紧贴光标的代码行；后缀从文件尾方向向下丢弃，保留紧贴光标的下方代码行。

### 5.2 后缀重复生成问题（Suffix Duplication / Suffix Regeneration）
- **现象**：因果模型在生成完预期的中间缺失代码后，由于自然语言顺承性，往往会“停不下来”，开始把 `code_suffix` 里的前几行原封不动重新输出一遍，直到命中最大 Token 上限。
- **治理手段**：
  1. **严格配置 Stop Tokens**：必须将模型的原生终止符（如 `<EOT>`, `<|endoftext|>`, `<｜end of sentence｜>`）加入推理引擎的 stop 列表；
  2. **客户端滑动窗口匹配（Sliding-window Suffix Truncation）**：流式接收补全结果时，实时与 `code_suffix` 的首行非空字符进行滑动比对，一旦重合立即在前端截断或中止请求；
  3. **基于语法作用域/缩进判定**：针对单行补全限制 `stop=["\n"]`；针对多行代码块，利用 Tree-sitter 或缩进层级在退回同级/外层缩进时提前截断。

### 5.3 连续键入下的 KV Cache 复用与 SPM 优势 (Prompt Caching)
在现代高并发推理引擎（如 vLLM Automatic Prefix Caching, SGLang RadixAttention）以及本地编辑场景下，开发者连续敲击键盘（如依次输入 `c` -> `ca` -> `car`）：
- **PSM 格式的痛点**：
  - 序列为 `[Prefix] [Suffix] [Middle]`；
  - 每次光标处敲击，`Prefix` 的尾部都在改变；
  - 在基于因果位置编码（如 RoPE）的 Transformer 中，前面的 Token 发生改动，**后续所有位置的 KV Cache 全部失效**！因此 `Suffix` 的 KV Cache 每次都要全部重新计算。
- **SPM 格式的工程优势**：
  - 序列为 `[Suffix] [Prefix] [Middle]`；
  - 在开发者敲击键盘时，光标下方的代码 `Suffix` 保持完全静止，且位于序列最前方（位置索引 0 到 $K$）；
  - 推理引擎能够**100% 命中并复用 `Suffix` 的整段 KV Cache**，只需对变化的光标前缀做增量 Prefill 计算，大幅削减连续输入时的首字延迟（TTFT）。这也是为什么 Codestral 等新一代模型在端到端补全中极度推崇 SPM 格式。

### 5.4 跨文件/仓库级上下文注入 (Repo-level Context)
根据 RepoCoder (arXiv:2303.12570) 和 CrossCodeEval (arXiv:2310.11248) 的最佳实践：
- 通过 LSP 定义跳转、cscope/ctags 或 BM25/向量检索召回的跨文件相关定义，通常格式化为注释或专门的 `<|file_sep|>` 分块，**全部置于前缀之前**（或者作为全局 Prompt 前置）；
- 当前正在编辑的文件作为最后一个上下文块，光标位置切分成 FIM 的 Prefix 与 Suffix。

---

## 6. 推理服务引擎调用参考

### 6.1 vLLM
vLLM 的 OpenAI 兼容接口支持传入包含 FIM 特殊 Token 的 Prompt，同时开启 Prefix Caching：
```bash
# 启动 vLLM 并开启 KV 缓存共享
vllm serve Qwen/Qwen2.5-Coder-7B --enable-prefix-caching
```
Python 请求代码：
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
response = client.completions.create(
    model="Qwen/Qwen2.5-Coder-7B",
    prompt="<|fim_prefix|>def add(a, b):\n    <|fim_suffix|>\n    return c<|fim_middle|>",
    max_tokens=64,
    stop=["<|endoftext|>", "\n\n"]
)
print(response.choices[0].text)
```

### 6.2 llama.cpp (`llama-server` 原生 Infill 端点)
llama.cpp 内置专门针对 FIM 场景优化的 `/infill` HTTP 端点：
```bash
curl http://127.0.0.1:8080/infill \
  -H "Content-Type: application/json" \
  -d '{
    "input_prefix": "def fibonacci(n):\n    ",
    "input_suffix": "\n    return seq",
    "n_predict": 64,
    "temperature": 0.2,
    "stop": ["\n\n", "<|endoftext|>"]
  }'
```

### 6.3 Ollama
Ollama 在 `Modelfile` 中通过模板动态适配 `Prompt` 与 `Suffix`：
```dockerfile
TEMPLATE """{{ if .Suffix }}<|fim_prefix|>{{ .Prompt }}<|fim_suffix|>{{ .Suffix }}<|fim_middle|>{{ else }}{{ .Prompt }}{{ end }}"""
```
API 调用：
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:7b",
  "prompt": "def multiply(x, y):\n    ",
  "suffix": "\n    return result",
  "stream": false
}'
```

---

## 7. 一手信源文献索引

1. **OpenAI FIM 原著**：Bavarian, M., Jun, H., Tezak, N., Schulman, J., McLeavey, C., Tworek, J., & Chen, M. (2022). *Efficient Training of Language Models to Fill in the Middle*. [arXiv:2207.14255](https://arxiv.org/abs/2207.14255).
2. **BigCode StarCoder**：Li, R., Allal, L. B., Zi, Y., Muennighoff, N., et al. (2023). *StarCoder: may the source be with you!*. [arXiv:2305.06161](https://arxiv.org/abs/2305.06161).
3. **BigCode StarCoder2**：Lozhkov, A., Li, R., Cassano, L. V., Beeching, E., et al. (2024). *StarCoder 2 and The Stack v2: The Next Generation*. [arXiv:2402.19173](https://arxiv.org/abs/2402.19173).
4. **Meta Code Llama**：Rozière, B., Gehring, J., Gloeckle, F., Sootla, S., Gat, I., et al. (2023). *Code Llama: Open Foundation Models for Code*. [arXiv:2308.12950](https://arxiv.org/abs/2308.12950).
5. **DeepSeek-Coder**：Guo, D., Zhu, Q., Yang, D., Xie, Z., Dong, K., et al. (2024). *DeepSeek-Coder: When the Large Language Model Meets Programming -- The Rise of Code Intelligence*. [arXiv:2401.14196](https://arxiv.org/abs/2401.14196).
6. **DeepSeek-Coder-V2**：DeepSeek-AI. (2024). *DeepSeek-Coder-V2: Breaking the Barrier of Closed-Source Models in Code Intelligence*. [arXiv:2406.11931](https://arxiv.org/abs/2406.11931).
7. **Qwen2.5-Coder**：Hui, B., Yang, J., Cui, Z., Yang, J., Liu, D., et al. (2024). *Qwen2.5-Coder Technical Report*. [arXiv:2409.12186](https://arxiv.org/abs/2409.12186).
8. **Mistral AI Codestral**：Mistral AI. (2024). *Codestral: Hello, World!*. [https://mistral.ai/news/codestral/](https://mistral.ai/news/codestral/).
9. **RepoCoder**：Zhang, F., Chen, B., Zhang, Y., Liu, J., Zan, D., et al. (2023). *RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation*. [arXiv:2303.12570](https://arxiv.org/abs/2303.12570).
10. **CrossCodeEval**：Ding, Y., Wang, Z., Ahmad, W. U., Ding, P., Tan, S., et al. (2023). *CrossCodeEval: A Diverse and Multilingual Benchmark for Cross-File Code Completion*. NeurIPS 2023. [arXiv:2310.11248](https://arxiv.org/abs/2310.11248).
