# 07 RAG 对照

对应实验：`apps/rag_compare`。回答那个最初的问题：**「让模型牢记制度文档」的最优解到底是什么？**

```powershell
uv run python -m apps.rag_compare --scenario prepare    # 拉取 bge-m3 向量模型（约 1.2GB）
uv run python -m apps.rag_compare --scenario index      # 全量块向量化（~1700 块，约 3 分钟）
uv run python -m apps.rag_compare --scenario ask --question "住宿费上限多少？"
uv run python -m apps.rag_compare --scenario compare --sample 50
```

## 一、四方对照设计

| 方案 | 知识来源 | 行为约束 | 预期 |
|---|---|---|---|
| base | 无 | 仅 system prompt | 热心解答 + 大量幻觉 |
| rag | 检索片段（top-3） | system prompt | 事实准确，但引用格式/口径不稳 |
| ft | 微调权重 | 训练出来的 | 口径统一、会拒答，细节记忆有上限 |
| ft-rag | 微调权重 + 检索 | 两者叠加 | **通常的最优解** |

全部走 Ollama（检索用 bge-m3 向量、生成用基座/微调模型、判分用 qwen2.5:7b），互不抢显存。

## 二、轻量 RAG 的实现（60 行 vs 一个向量库）

索引：每块过一遍 `bge-m3` 得 1024 维向量，归一化后存 `npz`。检索就是矩阵乘（余弦 = 归一化点积）：

```python
scores = matrix @ query      # (N,1024) @ (1024,) → N 个相似度
top = np.argsort(-scores)[:3]
```

1700 块的规模根本用不上向量数据库——**先把问题规模想清楚再选工具**，这也是本项目「手写路线」的又一次体现。

## 三、RAG 提示词组装

检索片段进 system（带章节路径），user 保持原始问题：

```
你是《制度文档》的专业问答助手…（约束规则同训练）
【片段 1｜第二章 费用报销 > 一、报销范围】
第五条 因公发生的交通费…
```

ft-rag 用同样组装，只是生成模型换成微调版——它已经知道「只依据片段回答」这个行为。

## 四、怎么读结果

`compare` 输出四行汇总（准确率/答错率/拒答率），典型形态：

```
base     准确率低、答错率高、几乎不拒答
rag      准确率显著抬升（事实在上下文里）
ft       拒答率最高、答错率低，但长尾问题记忆不到
ft-rag   准确率 ≈ rag，且口径与格式统一
```

## 五、最终方案建议（「牢记制度文档」的工程答案）

1. **行为层用微调**：拒答、引用格式、制度口径——这是 prompt 压不住、RAG 给不了的；
2. **事实层用 RAG**：制度会改版，检索索引重建（3 分钟）远比重训（8 小时）敏捷；
3. **改版流程**：新 Word → data_factory 重跑 → index 重建 → 完成，微调模型不动；
4. 微调的记忆能力留给**高频核心条款**（quote 样本反复强化），长尾全部交给检索。

到这一步，「学习微调」的目标完成，「制度助手」也有了可维护的工程架构。
