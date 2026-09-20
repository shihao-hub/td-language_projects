# Requirements Document

## Introduction

本项目 `rag_lab` 是 `python_projects` 子仓的第一个项目，定位为**学习型知识库（RAG）实验项目**：通过亲手搭建一条完整可运行的 RAG 链路，系统学习信息检索基础（BM25、向量检索、ANN 索引、混合检索、重排、生成、评估）。

已与用户确认的关键决策：

- **路线**：框架流快速搭建（LlamaIndex），阶段 1/2 核心算法手写以理解原理，不追求造轮子到生产级
- **embedding**：本地模型（sentence-transformers + BGE 中文模型）
- **范围**：5 个阶段全做
- **向量存储**：本机 PostgreSQL 18.1（EDB 安装版，Windows 服务 `postgresql-x64-18`）+ pgvector 为主线，FAISS 做原理对比
- **生成模型**：智谱 GLM API

假设与边界（明确标注）：

- 本项目是**学习实验项目，不是对外发布的 CLI 工具**，不适用《CLI 工具开发标准》的 MCP / `--json` / `schema` 导出要求；各阶段提供可运行的脚本入口即可
- 文档格式范围：Markdown 与纯文本为必做，PDF 解析为可选增强
- rerank 优先使用开源本地模型（BGE-reranker）；环境不允许时降级为 LLM 重排或跳过，不阻塞主链路

## Requirements

### Requirement 1: 项目基础设施与配置管理

项目位于 `python_projects/rag_lab/`，使用 uv 管理依赖（子项目内 `pyproject.toml`），运行期数据严格存放于 `%APPDATA%\language_projects\rag_lab\`。

#### Scenario 1.1: 首次运行初始化数据目录

- **WHEN** 程序首次写入运行期数据（索引文件、日志、导出结果等）
- **THE SYSTEM SHALL** 自动创建 `%APPDATA%\language_projects\rag_lab\` 完整目录链（含 `language_projects` 一层）后再写入

#### Scenario 1.2: APPDATA 不可用时的回退

- **IF** 取不到 `APPDATA` 环境变量
- **THE SYSTEM SHALL** 回退使用 `~/.language_projects/rag_lab/` 并自动创建目录

#### Scenario 1.3: 敏感配置隔离

- **WHEN** 程序需要 GLM API Key 等敏感配置
- **THE SYSTEM SHALL** 从 `.env` 读取，且仓库内只提交 `.env.example` 示例文件，绝不提交真实 `.env`

### Requirement 2: 阶段一 — BM25 经典检索

纯 Python 手写 TF-IDF 与 BM25 打分器，配合中文分词，在小型中文语料上完成关键词检索，建立"相关性打分"的基础认知。

#### Scenario 2.1: 关键词检索

- **WHEN** 用户运行 BM25 检索脚本并输入查询词
- **THE SYSTEM SHALL** 输出按 BM25 得分排序的 Top-K 文档列表（含文档名与得分）

#### Scenario 2.2: 算法对比

- **WHEN** 运行 TF-IDF 与 BM25 对比入口
- **THE SYSTEM SHALL** 对同一查询分别输出两种算法的排序结果，供观察两者排序差异

### Requirement 3: 阶段二 — 向量检索

使用本地 embedding 模型（BGE 中文模型）将语料向量化，先手写暴力余弦检索理解原理，再用 FAISS 体验 ANN 索引的收益与代价。

#### Scenario 3.1: 暴力向量检索

- **WHEN** 用户运行暴力检索脚本并输入查询
- **THE SYSTEM SHALL** 对全量向量逐一计算余弦相似度，输出 Top-K 结果与总耗时

#### Scenario 3.2: FAISS 对比

- **WHEN** 运行 FAISS 对比入口（至少对比 Flat 精确索引与 HNSW/IVF 近似索引中的一种）
- **THE SYSTEM SHALL** 输出各索引类型的 Top-K 结果、召回重合度与查询耗时，与暴力检索形成对比结论

#### Scenario 3.3: 模型本地加载

- **WHEN** 首次运行 embedding 相关脚本
- **THE SYSTEM SHALL** 自动下载 BGE 模型并缓存至约定缓存目录，后续运行直接从本地加载，不再重复下载

### Requirement 4: 阶段三 — pgvector 持久化与混合检索

在本机 PostgreSQL 18 上安装 pgvector 扩展，将语料向量持久化入库，建立 HNSW 索引，并实现关键词 + 向量的混合检索。

#### Scenario 4.1: 环境前置

- **WHEN** 执行阶段三初始化
- **THE SYSTEM SHALL** 先检测 pgvector 扩展是否可用（`CREATE EXTENSION vector`），不可用时给出明确的安装指引（Windows / MSVC 编译或预编译包）并在安装后可重试

#### Scenario 4.2: 入库

- **WHEN** 运行入库脚本
- **THE SYSTEM SHALL** 将文档切分、向量化后写入 pg 表（向量列 + 全文检索列，不使用 JSONB，字段显式定义），并确保 HNSW 索引存在

#### Scenario 4.3: 混合检索

- **WHEN** 用户执行混合检索查询
- **THE SYSTEM SHALL** 同时执行关键词路径（tsvector 全文检索）与向量相似度路径，并以融合排序（如 RRF）输出统一 Top-K 结果

### Requirement 5: 阶段四 — 完整 RAG 链路

基于 LlamaIndex 组装"加载 → 切分 → 检索 → （重排）→ 生成"完整链路，检索后端对接阶段三的 pgvector，生成端接智谱 GLM，回答必须带出处引用。

#### Scenario 5.1: 带引用的问答

- **WHEN** 用户对知识库提问
- **THE SYSTEM SHALL** 检索相关 chunk 并调用 GLM 生成回答，回答中附带出处（文档名 / chunk 位置）

#### Scenario 5.2: 切分策略可切换

- **WHEN** 入库时指定切分策略参数（固定大小 / 按结构切分，至少两种）
- **THE SYSTEM SHALL** 按指定策略切分入库，且同一问题在不同切分策略下可对比检索效果

#### Scenario 5.3: API 异常处理

- **IF** GLM API 调用失败（网络错误 / Key 无效 / 限流）
- **THE SYSTEM SHALL** 输出明确的错误原因提示并正常退出，不崩溃、不输出半截误导性答案

### Requirement 6: 阶段五 — Agentic 检索与评估

将检索升级为 Agentic 模式（LLM 自主决定是否检索、改写查询、多轮检索），并建立最小评估体系量化检索质量。

#### Scenario 6.1: 自主多轮检索

- **WHEN** 用户以 Agentic 模式提问
- **THE SYSTEM SHALL** 由 LLM 决策是否需要检索与查询改写，支持至少两轮"检索 → 反思 → 再检索"，并将每轮决策记录到日志

#### Scenario 6.2: 检索质量评估

- **WHEN** 运行评估脚本
- **THE SYSTEM SHALL** 在自建 QA 评估集（不少于 10 条）上输出检索 Recall@K 与 MRR 指标，支持对比 BM25 / 向量 / 混合三种检索路径

### Requirement 7: 学习文档沉淀

每个阶段完成后沉淀学习笔记，全部存放于父仓库 `docs/projects/python_projects/rag_lab/`。

#### Scenario 7.1: 阶段笔记

- **WHEN** 任一阶段开发完成
- **THE SYSTEM SHALL** 在 `docs/projects/python_projects/rag_lab/` 下存在对应阶段的学习笔记（原理要点、对比结论、踩坑记录）
