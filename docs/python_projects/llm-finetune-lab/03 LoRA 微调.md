# 03 LoRA 微调

对应实验：`apps/lora_sft`。手写 `peft + trl` 全闭环，不用任何「一键训练」工具。

```powershell
uv run python -m apps.lora_sft --scenario train --model qwen3-0.6b              # 默认超参
uv run python -m apps.lora_sft --scenario train --model qwen3-1.7b --epochs 3
uv run python -m apps.lora_sft --scenario chat --model qwen3-0.6b --question "住宿费上限多少？"
```

## 一、LoRA 在做什么

微调的本质还是梯度下降，只是全参微调要更新全部 P 个参数，LoRA 只给每个线性层旁边加一对低秩矩阵：

```
h = W·x  →  h = W·x + (α/r)·B·A·x      A: r×d, B: d×r, 原始 W 冻结
```

`LoraConfig` 三个关键参数：

| 参数 | 默认 | 作用 | 调法 |
|---|---|---|---|
| `r` | 16 | 低秩维度，决定「新知识容量」 | 数据少/只改风格 8~16；领域知识多 32~64 |
| `lora_alpha` | 32 | 缩放系数 α/r，等效学习强度 | 经验值 α = 2r |
| `target_modules` | all-linear | 插到哪些层 | 至少覆盖 attention 的 q/v + FFN 的 gate/up/down |

实测 0.6B：**可训练参数 10,092,544 / 606,142,464（1.67%）**——1.67% 的参数承载了全部「制度人格」。

## 二、训练配置逐行解读（8GB 显存公式）

```python
per_device_train_batch_size = 1      # 物理批只能 1：激活值是显存大头
gradient_accumulation_steps = 8      # 累积 8 步 = 等效 batch 8，省显存不省效果
learning_rate = 2e-4                 # LoRA 专用：比全参（1e-5 级）大一个数量级
lr_scheduler_type = "cosine"         # 余弦退火 + 5% 预热
bf16 = True                          # Blackwell 原生 bf16
gradient_checkpointing = True        # 用重算换显存：激活峰值降一个量级
assistant_only_loss = True           # 只对 assistant 段算 loss
max_length = 1024                    # 序列预算：覆盖 system+QA 全文即可
```

`assistant_only_loss` 值得单独说：不做 mask 时模型同时学「怎么问」和「怎么答」——问题文本对「答」没有任何贡献，还会稀释梯度。trl 对会话式数据自动生成 assistant 掩码。

## 三、chat template 一致性（隐蔽但致命）

Qwen3 的 chat template 会自动给 assistant 回复插入 `<think>\n\n</think>\n\n` 前缀，训练与推理（`enable_thinking=False`）自动对齐——**前提是两处都走 template**。如果哪天手拼 prompt 字符串，行为会立刻漂移。本项目训练（trl 内部 template）、推理（`scenario_chat`）、部署（Modelfile）三处统一。

## 四、看懂训练输出

冒烟实测（16 条样本 × 2 epoch）：

```
eval loss: 2.0131 → 1.7331       # 在学
显存峰值: 1.84 GB                # 0.6B LoRA 非常宽裕
train loss: 1.41 → 1.41          # 样本太少，仅供参考
```

正式训练看三件事：

1. **train loss 该降**：不降 → 学习率太小 / 数据太乱；
2. **eval loss 先降后升 = 过拟合**：制度文档 QA 数据量小时很常见，减 epoch（3→2）或加数据；
3. **eval loss 降但对话变差**：过拟合到「背题」，看 qc 样本有没有泄漏进 val。

每个训练目录都有 `train_report.json`（超参、loss 历史、显存峰值、耗时），横向对比实验全靠它。

## 五、常见坑（本机实测踩过）

| 症状 | 原因 | 解法 |
|---|---|---|
| `unexpected keyword argument 'warmup_ratio'` | transformers 5.x 合并进 `warmup_steps`（支持小数比例） | 用 `warmup_steps=0.05` |
| `'torch_dtype'` 不生效/告警 | transformers 5.x 改名 `dtype` | `dtype=torch.bfloat16` |
| 训练时 OOM | batch/seq 超预算 | bs=1、降 max_length、开梯度检查点 |
| 微调后一律拒答 | refusal 样本占比过高 | 调数据配比（见实验 02） |
| Ollama 与训练抢显存 | 两者都在 GPU | 训练时别跑 Ollama；评测先生成后判分（见实验 05） |
