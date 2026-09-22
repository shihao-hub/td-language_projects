# Qwen3.8-27B 本地部署配置调研

> 调研日期：2026-09-22。本文为只读技术调研，所有关键论断均标注来源 URL；未标注"估算"的计算值为理论推算，未标注"未经官方确认"的内容均来自一手来源。
>
> **核心提示**：Qwen3.8-27B **不是纯文本 LLM，而是原生视觉-语言模型（VLM，Image-Text-to-Text）**，架构为 Gated DeltaNet（线性注意力）+ Gated Attention 混合结构，KV cache 显存占用显著低于传统 64 层全注意力模型。

---

## 1. 结论速览

总参数量 28B（HF Safetensors 统计，含 vision tower 与 MTP head；语言模型部分 27B）。

| 精度 | 权重显存（估算） | 单卡可跑上下文（batch=1，估算） | 推荐硬件 |
|---|---|---|---|
| BF16 / FP16 原生 | ~56 GB | 80GB 卡：~128K-256K；256K 需留足余量 | 1× A100/A800/H100 80GB 起步；2× 48GB（TP2）；生产推荐 2× 80GB |
| FP8（官方 `Qwen/Qwen3.8-27B-FP8`） | ~28-29 GB（实测 28.6 GiB） | 48GB 卡：~256K；80GB H100：可达 1M | H100/H200/H20、RTX 50 系（Blackwell sm120 原生 FP8）；Ascend 950PR 原生 FP8 |
| INT8（w8a8） | ~28-30 GB | 同 FP8 量级 | Ascend 950PR（ModelSlim w8a8 实测）；NVIDIA 卡无官方 INT8 检查点 |
| NVFP4（4-bit 浮点，Blackwell 原生） | ~21-25 GB（实测每卡 10.6-12.0 GiB @TP2） | **1× RTX 5090 32GB 实测可行（32K 上下文，需 `--enforce-eager`）**；2× 5090 实测 256K | RTX 5090 / 5080 等 Blackwell 消费卡；B200/GB300 |
| INT4（GPTQ/AWQ/GGUF 社区量化） | ~14-16 GB | 24GB 卡（RTX 4090/3090）：~32K 级别 | RTX 4090/3090 24GB（社区 GGUF/GPTQ，llama.cpp/Unsloth 生态） |

> 上下文长度与 KV cache 的关系见第 4 节；表中"可跑上下文"为 batch=1 的估算值。vLLM 官方 recipe 的结论口径：**"Fits one Blackwell GPU in every precision: NVFP4 in 24.6 GiB, 6.6M KV tokens at 1M context"**（所有精度都能装进一张 Blackwell GPU：NVFP4 占 24.6 GiB，1M 上下文可容纳 660 万 KV token）。来源：https://recipes.vllm.ai/Qwen/Qwen3.8-27B

---

## 2. 模型存在性与官方命名验证

**结论：`Qwen3.8-27B` 命名准确，真实存在**，用户询问的名称与官方命名一致。

一手来源验证链：

1. **Hugging Face 官方组织页**（https://huggingface.co/Qwen ）模型列表可见 `Qwen/Qwen3.8-27B`（Image-Text-to-Text • 28B • Updated Aug 14 • 7.15M 下载）与 `Qwen/Qwen3.8-27B-FP8`；官方 Collection "Qwen3.8" 包含 4 个模型。
2. **GitHub 官方仓库**（https://github.com/QwenLM/Qwen3.8 ）News 明确记载：**2026-08-14 Qwen3.8-27B 发布于 Hugging Face Hub 与 ModelScope**；同系列还有 2026-08-12 发布的 `Qwen3.8-2.4T-A95B`（2.4T MoE 旗舰）与 `Qwen3.8-Flash-Next`（180B）。仓库 README 原文："For the first time, Qwen3.8 brings a Qwen-Max-class model to open release."
3. **官方博客**：发布文标题《Qwen3.8-Max: A New Bar for Coding and Cowork》，URL 为 https://qwen.ai/blog?id=qwen3.8 （2026 年 8 月，见模型卡 Citation 区）。⚠️ 该页面为 JS 渲染，本次调研无法抓取正文，标题与日期以模型卡/GitHub 引用为准。
4. 许可证：Apache-2.0（模型卡页标注 https://huggingface.co/Qwen/Qwen3.8 ）。

同系列官方发布清单（HF 组织页 + GitHub News 交叉确认）：

| 模型 | 规格 | 备注 |
|---|---|---|
| Qwen3.8-27B | 27B dense VLM | 本次调研对象 |
| Qwen3.8-27B-FP8 | 同上 FP8 量化 | 官方量化版 |
| Qwen3.8-2.4T-A95B（-FP8） | 2.4T 总参 / A95B MoE | 旗舰，本地部署门槛极高 |
| Qwen3.8-Flash-Next（-FP8） | 180B | Image-Text-to-Text |

**注意**：HF 官方组织未发布 27B 的 GPTQ/AWQ INT4 版本；INT4 生态为社区量化（模型树显示 1195 个衍生量化模型，https://huggingface.co/Qwen/Qwen3.8-27B?launcher=false 页面 "Quantizations" 区）与 NVIDIA 官方 NVFP4 版（`nvidia/Qwen3.8-27B-NVFP4`，见 vLLM recipe References）。

---

## 3. 模型基本信息

以下参数全部来自官方 config.json（一手来源）：https://huggingface.co/Qwen/Qwen3.8-27B/raw/main/config.json

| 项目 | 值 |
|---|---|
| 架构类 | `Qwen3_5ForConditionalGeneration`（model_type: `qwen3_5`），原生多模态（含 `vision_config`） |
| 语言模型参数 | 27B；Safetensors 总计 28B params（含 vision tower + MTP head），BF16 |
| hidden_size | 5120 |
| 层数 | 64，其中**全注意力层仅 16 层**（`full_attention_interval: 4`），**线性注意力层 48 层**（Gated DeltaNet） |
| 层布局 | 16 × (3 × (Gated DeltaNet → FFN) → 1 × (Gated Attention → FFN))（模型卡 Model Overview） |
| Gated Attention | Q 头 24 / KV 头 4（GQA 6:1），head_dim 256，partial_rotary_factor 0.25，RoPE theta 1e7，mrope |
| Gated DeltaNet | 线性注意力：QK 头 16 / V 头 48，head_dim 128，conv kernel 4；`mamba_ssm_dtype: float32` |
| FFN intermediate | 17,408 |
| 词表 | 248,320（padded），`tie_word_embeddings: false` |
| MTP | `mtp_num_hidden_layers: 1`（Multi-Token Prediction 草稿头，可做投机解码） |
| Vision tower | 27 层、hidden 1152、patch 16、spatial_merge 2（约 0.4B 参数，估算值） |
| 上下文长度 | **原生 262,144（256K）**，YaRN（factor 4.0）可扩展至 **1,000,000** |
| transformers 版本记录 | `5.8.0.dev0`（写入 config 的版本） |

来源补充：模型卡 Model Overview 章节（https://huggingface.co/Qwen/Qwen3.8#model-overview ）；vLLM recipe 概述（"Only 16 of the 64 layers run full attention; the other 48 run linear attention with a constant recurrent state"，https://recipes.vllm.ai/Qwen/Qwen3.8-27B ）。

---

## 4. 显存估算过程

### 4.1 权重占用

权重显存 ≈ 参数量 × 每参数字节数（+量化 scale 开销）。以 Safetensors 报告的 28B 总参数为基数：

| 精度 | 计算 | 权重显存 |
|---|---|---|
| BF16 / FP16 | 28 × 10⁹ × 2 B | ≈ 56 GB |
| FP8（官方 e4m3 dynamic） | 28 × 10⁹ × 1 B + scale | ≈ 28-29 GB。**实测对照**：vLLM recipe 在 2×RTX 5090 TP2 报告 `Qwen/Qwen3.8-27B-FP8` 每卡权重 14.28 GiB → 合计 28.56 GiB，与理论吻合 |
| INT8 w8a8 | 28 × 10⁹ × 1 B | ≈ 28-30 GB（未单独实测，估算） |
| NVFP4 | 28 × 10⁹ × 0.5 B + scale | 理论 ~14 GB；**实测**（含未量化 embedding/视觉层/scale）TP2 每卡 10.64-12.02 GiB → 合计 21-24 GiB；官方口径单卡 24.6 GiB |
| INT4 GPTQ/AWQ/GGUF | ≈ 4.5-4.8 bit/参数（Q4_K_M 等） | ≈ 15-17 GB（估算，社区量化无官方数字） |

### 4.2 KV cache（混合架构优势是重点）

标准公式：`2 × 层数 × KV头数 × head_dim × 上下文长度 × batch × 每元素字节`。

**关键：只有 16 层全注意力层产生 KV cache**（config.json `layer_types` 数组可数出 16 个 `full_attention`），KV 头 4、head_dim 256：

```
每 token KV（BF16）= 2 × 16 层 × 4 头 × 256 × 2 B = 65,536 B ≈ 64 KiB/token
```

对比：传统 64 层全注意力 27B 级模型（64 层 × 8KV头 × 128 dim × 2 × 2B = 256 KiB/token）的 **1/4**。

| 上下文长度 | KV cache（BF16） | KV cache（FP8，`--kv-cache-dtype fp8`） |
|---|---|---|
| 8K | 0.5 GB | 0.25 GB |
| 32K | 2 GB | 1 GB |
| 128K | 8 GB | 4 GB |
| 256K（原生满配） | 16 GB | 8 GB |
| 1M（YaRN 扩展） | 64 GB | 32 GB |

（以上为单并发 batch=1 估算值，随 batch 线性增长。）

**实测对照**（vLLM recipe，一手）：2×RTX 5090 TP2、256K 上下文、FP8 KV 下，KV pool 为 37.7 万（官方 FP8）/44.6 万（Inferact NVFP4）/92 万 token（unsloth 混合精度版）；32K 上下文单张 5090 KV pool 91,022 token（FP8 KV）/ 76,458（BF16 KV）——反向印证 32K × 64 KiB ≈ 2 GB 理论值与实测余量一致。

### 4.3 线性注意力 recurrent state（本架构特有开销）

Gated DeltaNet 层不存 KV cache，但每序列持有常量 recurrent state。按每层 16 K头 × 128 × 128 元素、FP32 存储（`mamba_ssm_dtype: float32`）估算：

```
48 层 × 16 × 128 × 128 × 4 B ≈ 48 MiB / 每并发序列
```

**与序列长度无关**（这是长上下文显存友好的根源），但随并发 batch 数线性增长。此为按 config 推算的估算值，未见官方文档单独说明。

### 4.4 激活与框架开销

- CUDA graph 捕获需约 0.8-1 GB 额外显存：recipe 实测单张 5090 上 NVFP4 权重+KV 占满预算后，graph capture 申请 784 MiB 失败 OOM，必须 `--enforce-eager` 规避（一手实测，https://recipes.vllm.ai/Qwen/Qwen3.8-27B ）。
- 激活值、视觉编码器中间张量与临时缓冲：通常再预留 2-4 GB（估算，随 batch/图像分辨率变化）。视频输入可膨胀至 224K video token（模型卡 Best Practices：`longest_edge` 469,762,048 对应 224k video token，https://huggingface.co/Qwen/Qwen3.8#best-practices ），显存需求需按对应上下文长度重新估算。

### 4.5 典型场景显存合计（batch=1，估算）

| 场景 | 权重 | KV cache | 框架开销 | 建议显存 |
|---|---|---|---|---|
| BF16 + 32K | 56 GB | 2 GB | ~4 GB | ≥ 64 GB |
| BF16 + 256K | 56 GB | 16 GB | ~4 GB | ≥ 80 GB（紧张，建议 FP8 KV 或 2 卡 TP） |
| FP8 + 128K | 29 GB | 4 GB | ~4 GB | ≥ 40 GB（48GB 卡舒适） |
| FP8 + 1M | 29 GB | 32 GB | ~4 GB | ≥ 68 GB（80GB 卡可跑单并发） |
| NVFP4 + 32K | 22-25 GB | 1-2 GB | ~1 GB（enforce-eager） | **32 GB 卡实测可行**（5090） |
| NVFP4 + 256K | 21-24 GB（TP2） | 8 GB（FP8 KV） | ~4 GB | 2× 32 GB 实测可行（5090 TP2） |
| INT4 GGUF + 32K | 15-17 GB | 2 GB | ~2 GB | 24 GB 卡可行（估算） |

---

## 5. 推荐硬件配置

### 5.1 消费级

| 硬件 | 精度 | 上下文 | 依据 |
|---|---|---|---|
| 1× RTX 5090 32GB | NVFP4 | 32K（`--enforce-eager`，KV pool ~9.1 万 token） | vLLM recipe 实测章节 "1x RTX 5090"（一手） |
| 2× RTX 5090 TP2 | NVFP4 / FP8 | 256K（KV pool 37.7 万-92 万 token，MTP 验收率 0.75-0.90） | vLLM recipe "2x RTX 5090 (consumer Blackwell, sm120)" 实测（一手） |
| 1× RTX 4090 24GB | 社区 INT4（GGUF/GPTQ/AWQ） | ~32K（估算） | 官方无 24GB 卡方案；llama.cpp 官方 README 确认支持该系列 GGUF（text & vision）；24GB 放不下 NVFP4 实测占用 24.6 GiB |
| Apple Silicon（MLX） | MLX 量化 | 视统一内存容量 | GitHub 官方 README："both mlx-lm (text-only) and mlx-vlm (vision + text) support the Qwen3.5 open model series"（一手） |

注意事项（一手，vLLM recipe）：
- **MXFP4 量化在 NVIDIA 设备上当前不可用**（缺 linear method 支持），NVIDIA 上请用 NVFP4；
- NVFP4 内核为 Blackwell（sm120）cutlass 路径，Ada/Ampere 卡（4090/A100）无 FP4 硬件加速，应改用 INT4/GGUF 社区量化或 BF16。

### 5.2 数据中心级

| 硬件 | 精度 | 说明 |
|---|---|---|
| A100/A800 80GB | BF16（或社区 INT8/INT4） | 1× 80GB：32K-128K 舒适，256K 紧张；Ampere 无 FP8/FP4 硬件 |
| H100/H800 80GB | FP8（官方检查点） | 1× 80GB：256K-1M（FP8 KV）单并发可跑（估算）；TP4 为官方 README 示例配置 |
| H200 141GB / H20 96GB / B200 / GB300 | FP8 / NVFP4 | recipe 示例 "FP8, TP4 (one GB300 tray) for the largest KV cache"；1M 上下文 6.6M KV token 容量（一手） |
| Huawei Ascend 950PR | w8a8 INT8（ModelSlim）或原生 FP8 | vLLM Ascend 0.23.0 实测，单卡 TP1，64 tok/s（2048-token 补全，MTP 开启）；FP8 原生支持需 vllm-ascend PR #14852（2026-08-26 合入，尚无正式发版包含）（一手，https://recipes.vllm.ai/Qwen/Qwen3.8-27B ） |

多卡并行：官方 README 的 vLLM/SGLang/TokenSpeed 示例统一使用 `--tensor-parallel-size 4` / `--tp-size 4` + 262144 上下文（一手，https://github.com/QwenLM/Qwen3.8#deployment ）。

---

## 6. 软件栈要求

| 框架 | 版本要求 | 来源 |
|---|---|---|
| transformers | **≥ 5.8.0**（与 config.json 写入版本 5.8.0.dev0 匹配；架构 `Qwen3_5ForConditionalGeneration`） | vLLM recipe Prerequisites（一手）；config.json |
| vLLM | **≥ 0.17.0**（recipe 徽章）；NVFP4 消费卡方案验证于 0.26.1rc1.dev；DFlash2 投机解码需 ≥ 0.28.0（PR #52816） | https://recipes.vllm.ai/Qwen/Qwen3.8-27B （一手） |
| SGLang | 支持；官方 Cookbook：https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B ；最低版本号未能确认 | 模型卡 + GitHub README（一手）；版本号未确认 |
| TokenSpeed | 支持，官方 recipe：https://lightseek.org/tokenspeed/recipes/models#qwen3-8 | 模型卡 + GitHub README（一手） |
| llama.cpp | 支持（"llama.cpp supports the Qwen3.5 open model series (text & vision)"），使用 HF 上 GGUF 结尾模型；最低版本未确认 | GitHub README（一手） |
| MLX / mlx-vlm | 支持（Apple Silicon） | GitHub README（一手） |
| Unsloth | 支持，官方指南 https://unsloth.ai/docs/models/qwen3.8 （含量化运行） | GitHub README（一手） |
| vLLM Ascend | ≥ 0.23.0（Ascend 950PR） | vLLM recipe（一手） |

官方启动示例（GitHub README，一手）：

```bash
# vLLM
vllm serve Qwen/Qwen3.8-27B --port 8000 --tensor-parallel-size 4 \
  --max-model-len 262144 --reasoning-parser qwen3 \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder

# SGLang
sglang serve --model-path Qwen/Qwen3.8-27B --port 8000 --tp-size 4 \
  --context-length 262144 --reasoning-parser qwen3 --tool-call-parser qwen3_coder

# transformers（含 serving）
transformers serve Qwen/Qwen3.8-27B --port 8000 --continuous-batching
```

投机解码：检查点内置 MTP head，vLLM 加 `--speculative-config '{"method":"mtp","num_speculative_tokens":3}'`，各精度下实测验收率 0.75-0.90（vLLM recipe，一手）。

超长上下文（1M）：按模型卡通过 `--hf-overrides` 写入 YaRN rope 参数（factor 4.0，`original_max_position_embeddings: 262144`），vLLM 需 `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`；静态 YaRN 会影响短文本性能，仅在需要时开启（模型卡 Best Practices，一手）。

---

## 7. 其他

- **磁盘空间**（按权重文件体积估算）：BF16 ~56 GB；FP8 ~29 GB；NVFP4 ~15-25 GB；GGUF Q4 ~15-17 GB。未从 HF Files 页面逐文件核对，标注为估算。
- **系统内存**：加载与 CPU offload 建议准备 ≥ 权重体积的空闲 RAM（通用经验值，未经官方确认）。
- **CPU 推理**：官方无 CPU 专用发布；llama.cpp GGUF 路线天然支持纯 CPU / CPU+GPU 混合（GitHub README 确认 llama.cpp 支持，一手；纯 CPU 速度未实测）。Gated DeltaNet 线性注意力在 CPU 后端的 kernel 支持情况**未经官方确认**。
- **端侧部署**：27B 级别无手机端侧方案；官方"本地"方案下限为消费级 GPU（NVFP4@32GB 卡）与 Apple Silicon MLX（一手来源未提及更小端侧形态）。
- **官方部署示例**：齐备——模型卡 Quickstart/Best Practices、vLLM recipe（含 5 种硬件实测）、SGLang Cookbook、TokenSpeed recipe、Unsloth 指南（均为一手）。
- **官方显存估算工具**：**未见 Qwen 官方专用估算工具**（未经官方确认不存在，仅本次调研未发现）。可用替代：vLLM 启动日志打印实际 KV pool 容量（recipe 数据即来源于此）；HF `accelerate` 通用估算器为第三方工具。
- **托管服务**：模型卡称 Qwen Cloud 将提供 1M 上下文托管版（"coming soon"）（一手）。

---

## 8. 未能确认的信息点

1. **qwen.ai 官方博客正文**（https://qwen.ai/blog?id=qwen3.8 ）：JS 渲染无法抓取，发布文内容以 HF 模型卡与 GitHub README 交叉印证；博客标题/日期引自模型卡 Citation。
2. **SGLang 支持的最低版本号**：官方 Cookbook 存在但本次未抓取详情页确认版本门槛。
3. **官方 GPTQ/AWQ INT4 检查点**：HF 官方组织未发布（组织页模型列表只有 BF16 与 FP8）；INT4 需用社区量化（GGUF 1195 个衍生量化）或 NVIDIA 官方 NVFP4。
4. **llama.cpp / GGUF 对 qwen3_5 混合架构（Gated DeltaNet）的最低支持版本**及纯 CPU 性能数据。
5. **A100（Ampere）上官方 FP8 检查点的可用性**：未找到官方逐硬件支持矩阵；FP8/FP4 硬件收益以 Hopper/Blackwell/Ada 为准为一般性判断。
6. **vision tower 精确参数量**：仅知总计 28B（Safetensors），vision 部分约 0.4B 为按 config 推算。
7. 官方是否存在专用显存估算工具：未发现，但无法证明不存在。

---

## 9. 参考来源

### 一手来源（官方）

| # | 来源 | URL |
|---|---|---|
| 1 | HF 官方组织页（模型列表/Collection 验证） | https://huggingface.co/Qwen |
| 2 | Qwen3.8-27B 模型卡 | https://huggingface.co/Qwen/Qwen3.8 |
| 3 | Qwen3.8-27B config.json（架构参数） | https://huggingface.co/Qwen/Qwen3.8/raw/main/config.json |
| 4 | Qwen3.8-27B-FP8 config.json（FP8 量化配置） | https://huggingface.co/Qwen/Qwen3.8-27B-FP8/raw/main/config.json |
| 5 | GitHub 官方仓库 README（发布时间/部署指南/llama.cpp/MLX/Unsloth） | https://github.com/QwenLM/Qwen3.8 |
| 6 | vLLM 官方 recipe（硬件实测/版本要求/KV pool 数据） | https://recipes.vllm.ai/Qwen/Qwen3.8-27B |
| 7 | SGLang 官方 Cookbook 入口 | https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-27B |
| 8 | TokenSpeed 官方 recipe 入口 | https://lightseek.org/tokenspeed/recipes/models#qwen3-8 |

### 二手/社区来源（补充，已标注）

| # | 来源 | 用途 |
|---|---|---|
| 9 | nvidia/Qwen3.8-27B-NVFP4（HF，NVIDIA 官方发布但非 Qwen 团队） | NVFP4 检查点存在性（经 vLLM recipe 转引） |
| 10 | unsloth/Qwen3.8-27B-NVFP4、Inferact/Qwen3.8-27B-NVFP4、Eco-Tech/Qwen3.8-27B-w8a8（ModelScope） | 社区/硬件伙伴量化版（经 vLLM recipe 转引） |
| 11 | qwenlm.github.io/blog/ | 确认旧博客站停更于 2025-09（Qwen3Guard），新博客在 qwen.ai（正文未能抓取） |

### 计算口径声明

第 4 节权重/KV/线性注意力 state 数值为按 config.json 参数的理论估算（KV 公式：`2 × 16 层 × 4 KV头 × 256 head_dim × 上下文 × batch × 字节数`）；与 vLLM recipe 实测值（权重 14.28 GiB/卡@FP8-TP2、KV pool token 数、NVFP4 24.6 GiB）已做交叉对照并在文中标注。所有"估算"字样内容不应作为采购依据，建议部署前以目标框架启动日志的实际显存报告为准。
