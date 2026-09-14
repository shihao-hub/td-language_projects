# 06 导出 Ollama 部署

对应实验：`apps/export_ollama`。训练产物是 adapter「补丁」，日常使用要变成 `ollama run` 里能对话的模型。

```powershell
uv run python -m apps.export_ollama --scenario deploy --model qwen3-4b --quantize q4_K_M
ollama run policy-qwen3-4b
```

（0.6B/1.7B 可以不量化：`--scenario deploy --model qwen3-1.7b`）

## 一、四步流水线

```
adapter + 基座 ──merge──▶ 完整 HF 模型 ──convert──▶ GGUF(f16) ──ollama create──▶ 本机模型
   (CPU, ~2min)         (safetensors)   (~1min)     (--quantize 可再量化)      policy-qwen3-4b
```

1. **merge**：`merge_and_unload()` 把 LoRA 权重折进基座。在 **CPU** 上做——4B bf16 要 8GB，走 24GB 内存而不是 8GB 显存；
2. **GGUF 转换**：llama.cpp 的 `convert_hf_to_gguf.py`（自动 sparse clone 到数据目录 `tools/llama.cpp`，约 2MB）；
3. **Modelfile**：`FROM <gguf>` + `SYSTEM`（训练同款 system prompt）+ 参数（temperature 0.1 / num_ctx 4096）；
4. **ollama create**：`--quantize q4_K_M` 在导入时量化（4B f16 GGUF 8GB → q4 约 2.5GB，8GB 显存装下）。

## 二、为什么绕 GGUF（本机实测的坑）

直接 `FROM <safetensors目录>` 会报：

```
Error: unsupported architecture "Qwen3ForCausalLM"
```

本机 Ollama 0.17.1 的 safetensors 导入器不支持 Qwen3 架构（registry 里的 qwen3 能跑是因为官方已转好 GGUF——导入器与运行时是两条代码路径）。所以固定走 llama.cpp 转换。

转换器版本一致性也有讲究：master 的 `conversion/` 包与 pip 的 `gguf` 包常量不同步（实测报 `MODEL_ARCH has no attribute DFLASH`），所以 clone 时连仓内 `gguf-py` 一起拉，脚本会优先用本地版本。

## 三、Modelfile 的 SYSTEM 为什么还要写

微调已经把行为训进权重了，SYSTEM 再写一遍是**双保险**：部署环境（别人拷走模型、接入其他客户端）不保证带 system prompt 时，模型仍有基准约束。两处 prompt 必须一字不差（都在 `apps/common/prompts.py`，单一事实源）。

## 四、部署验收

`deploy` 最后自动调 Ollama API 问一道制度题 + 一道越界题。冒烟实测（欠训练的 0.6B 冒烟 adapter）：

```
问题: 迟到超过三十分钟怎么处理？
回答: （模型开始自由发挥——正常，adapter 只训了 16 条样本）
```

**验收标准**（正式 4B 模型）：制度问题引用条款、越界问题拒答、无「课堂迟到」这种领域漂移。

## 五、日常使用

```powershell
ollama run policy-qwen3-4b          # 终端对话
# 或任何支持 Ollama 的客户端（API http://127.0.0.1:11434）
```

模型更新流程：重新训练 → deploy 同名覆盖 → `ollama run` 即新版。
