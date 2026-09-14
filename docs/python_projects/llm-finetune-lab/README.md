# llm-finetune-lab 学习教程总览

以「让小模型强约束于一份制度文档」为最终目标，在手写代码（transformers + peft + trl + bitsandbytes）的过程中掌握本地微调全流程。每个实验对应子仓 `python_projects/llm-finetune-lab/apps/` 下一个 app，先跑通再拆原理。

本教程所有「实测」数字均来自本项目开发机：RTX 5050 Laptop 8GB（Blackwell sm_120）+ 24GB 内存 + torch 2.11.0+cu128。

## 推荐学习顺序

| # | 教程 | 实验目录 | 依赖 | 一句话主题 |
|---|---|---|---|---|
| 01 | [环境与显存预算](01%20环境与显存预算.md) | `apps/env_baseline` | GPU | sm_120 验证 / 显存公式 / 理论表 vs 实测 |
| 02 | [数据工厂](02%20数据工厂.md) | `apps/data_factory` | GPU + Ollama | Word → 分块 → QA 合成 → 防泄漏切分 |
| 03 | [LoRA 微调](03%20LoRA%20微调.md) | `apps/lora_sft` | GPU | 手写训练闭环 / loss 与过拟合 |
| 04 | [QLoRA 与 4B](04%20QLoRA%20与%204B.md) | `apps/qlora_4b` | GPU | nf4 量化 / 8GB 显存调优 |
| 05 | [评测方法](05%20评测方法.md) | `apps/eval_lab` | GPU + Ollama | QA 准确率 / 拒答正确率 / 幻觉率 |
| 06 | [导出 Ollama 部署](06%20导出%20Ollama%20部署.md) | `apps/export_ollama` | GPU + Ollama | merge → GGUF → ollama run |
| 07 | [RAG 对照](07%20RAG%20对照.md) | `apps/rag_compare` | GPU + Ollama | 四方对比与最终方案 |

## 快速开始（项目根 `python_projects/llm-finetune-lab/` 下执行）

```powershell
uv sync                                    # torch 走 cu128 索引（RTX 50 系必须）
uv run python main.py doctor               # 环境自检
uv run python main.py download qwen3-0.6b --source modelscope   # 国内推荐源
uv run python main.py list                 # 实验目录
```

制度文档（Word）放到 `%APPDATA%\language_projects\llm-finetune-lab\corpus\` 后：

```powershell
uv run python -m apps.data_factory --scenario all        # 提取 + 分块
uv run python -m apps.data_factory --scenario generate --limit 20   # 试点 20 块
uv run python -m apps.data_factory --scenario generate   # 全量（可中断续跑）
uv run python -m apps.data_factory --scenario assemble; uv run python -m apps.data_factory --scenario split; uv run python -m apps.data_factory --scenario qc
uv run python -m apps.lora_sft --scenario train          # 0.6B 起步
uv run python -m apps.qlora_4b --scenario train          # 4B 正式版
uv run python -m apps.eval_lab --scenario compare --model qwen3-4b --load 4bit --adapter <adapter路径>
uv run python -m apps.export_ollama --scenario deploy --model qwen3-4b --quantize q4_K_M
uv run python -m apps.rag_compare --scenario prepare; uv run python -m apps.rag_compare --scenario index
uv run python -m apps.rag_compare --scenario compare
```

## 三条贯穿全项目的心智主线

1. **显存预算**：每一步（加载/训练/推理/评测）都先问「显存去哪了」，实验 01 建立的公式贯穿始终；
2. **行为 vs 事实**：微调教的是行为（拒答、引用格式、口径），事实召回靠数据重复 + RAG 兜底，实验 05/07 用数字验证；
3. **一致性**：system prompt、chat template、量化方式在训练/评测/部署三处保持一致，否则行为漂移。

## 约定

- 所有运行时数据（corpus / 模型缓存 / 数据集 / 输出 / 日志 / 工具）只放 `%APPDATA%\language_projects\llm-finetune-lab\`，代码自动建目录；
- 制度文档不出本机：QA 合成、训练、评测、裁判全部走本地 Ollama；
- 依赖不可用显式报错退出，不静默降级；
- 单元测试不依赖 GPU / Ollama：`uv run pytest`。
