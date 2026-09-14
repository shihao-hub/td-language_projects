# 04 QLoRA 与 4B

对应实验：`apps/qlora_4b`。与实验 03 的代码 90% 相同——**差异本身就是 QLoRA 的定义**。

```powershell
uv run python -m apps.qlora_4b --scenario train --model qwen3-4b --max-length 768
uv run python -m apps.qlora_4b --scenario chat --model qwen3-4b --question "住宿费上限多少？"
```

## 一、为什么 8GB 卡必须 QLoRA

4B 模型 bf16 权重 7.45GB，光加载就占满 8GB 显存，训练想都别想。QLoRA 的回答：**把冻结权重压到 4bit 存，计算时反量化回 bf16**。

四个组成（代码里逐一对应）：

```python
BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",        # ① 4bit NormalFloat：正态分布权重的信息论最优量化格
    bnb_4bit_use_double_quant=True,   # ② 量化常数本身再量化，每参数再省约 0.4bit
    bnb_4bit_compute_dtype=torch.bfloat16,  # ③ 算子内反量化成 bf16 再矩阵乘
)
prepare_model_for_kbit_training(model, ...) # ④ 量化模型做梯度检查点前的数值/梯度修正
optim="paged_adamw_8bit"                    # ⑤ 优化器状态分页到统一内存，防瞬时尖峰 OOM
```

nf4 为什么不是普通 int4：神经网络权重近似零均值正态分布，nf4 的量化格点按正态分位数分布，「重要的中间值」分得更密——同样 4bit，量化误差显著更小。

## 二、实测数字（本机 RTX 5050 8GB）

```
nf4 量化后权重:      3.34 GB（bf16 是 7.45GB）
训练显存峰值:        4.56 GB（seq 512, bs 1×8）
可训练参数:          33,030,144 / 4,055,498,240（0.81%）
训练速度:            ~0.46 样本/s（含 4bit 反量化开销）
```

显存峰值 4.56GB 意味着 **seq 可以直接上 1024**，甚至能再加大等效 batch——QLoRA 给 8GB 卡解锁了 4B 模型的完整训练能力。

## 三、序列长度：最灵敏的旋钮

| max_length | 显存趋势 | 适用 |
|---|---|---|
| 512 | 最省 | QA 短问答为主 |
| 768 | 平衡 | 默认推荐 |
| 1024 | 峰值 +1~2GB | 长条文/RAG 上下文场景 |

OOM 的处理顺序：`--max-length 768→512` → `--accum` 加大 → 关掉占用显存的其他程序（Ollama！）。

## 四、质量预期管理

4B QLoRA ≈ 4B 全参的 95%+ 效果（制度问答这种窄域任务差距更小），但**推理速度**比 bf16 慢约一半（反量化开销）。所以项目策略是：

- 训练/实验阶段：4bit QLoRA（省显存）
- 部署阶段：merge 回 bf16 再量化成 q4_K_M GGUF（实验 06，Ollama 的推理量化比训练量化更激进）

## 五、与前序实验的衔接

- 数据：`datasets/train.jsonl`（实验 02 产出，别改切分！）
- 学机制：先跑通实验 03（0.6B LoRA），再来这里对比「同样代码 + 量化」的差异
- 产物：`outputs/qlora/<名>/final/`（adapter）→ 实验 05 评测 → 实验 06 部署
