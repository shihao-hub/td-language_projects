# Plan：docs 站点「热刷新 + 中文搜索」合一（serve 能力核查）

> 起点：用户问「`.scripts\docs-preview.bat` 不能热更新，哪个脚本能同时支持热更新和搜索？」
> 关联：《[02-docs-static-site.md](02-docs-static-site.md)》（站点搭建与本轮结论的旧前提）。

## 问题陈述

站点此前被描述为「能力分叉」：`docs-serve.bat`（`mkdocs serve`）热刷新但中文搜索差，`docs-preview.bat`（构建 + 静态服务）中文搜索可用但无热刷新。用户希望有一个入口同时具备两者。

实际核查后发现这个「分叉」是**误判**：中文搜索不来自 `build_docs.py` 里那道构建后 jieba 后处理，而来自 mkdocs-material 搜索插件自带的 CJK 处理链路，`build` / `serve` / `preview` 三个入口行为本就一致。

## 结论（先行）

- `docs-serve.bat` **本来就同时支持热刷新与中文搜索**，不需要新增任何东西；
- `build_docs.py` 里原有的「构建后 jieba 预分词 search_index.json」是**冗余工序**，实测对搜索结果零影响，已删除；
- `docs-preview.bat` 保留，定位改为「一次性静态服务 + 自动开浏览器」的只读浏览入口；
- 三个入口（build / serve / preview）行为完全一致，不再有「哪个入口搜得准」的分叉。

## 背景：中文搜索到底由谁实现

mkdocs-material 9.7.7 的搜索插件（`material/plugins/search/plugin.py`）里：

1. `try: import jieba`——jieba 可导入时，构建期对每个条目的 title/text 调 `_segment_chinese()`：把连续汉字段按 `jieba.cut` 切词，词间插入**零宽空格 `\u200b`**（源码注释写明「surround with zero-width whitespace for efficient indexing」）；jieba 缺失则静默跳过；
2. zh 语言包的 `search.config.separator` 是 `[\s\u200b\u3000\-、。，．？！；]+`——把 `\u200b` 与空白都算分隔符，于是索引里的 token 就是 jieba 词；
3. 查询侧 worker 的 `segment()`（`integrations/search/query/segment/index.ts`）拿倒排索引词典对查询串做**贪心最长匹配**切分，再按 AND 检索——所以查询切分是「跟着索引词表走」的，索引里有什么词就按什么词切。

因此：**只要 jieba 可导入，中文搜索就开箱即用**。本仓库 `.scripts/build_docs.py` 的 PEP 723 依赖里一直声明着 `jieba`，这条链路一直是通的——这才是「搜索能用」的真正原因；原后处理工序只是恰好做了同一件事的另一半（把词用空格连起来，而 zh 分隔符同样认空白），属于重复劳动。

原误判的由来：02 号计划的调研只看了浏览器端 worker（确认其无中文分词器）就推断「索引侧缺分词器」，未注意到 Python 侧 material 已用 jieba 切分并插 `\u200b`；而「离线模拟 worker 全链路」的验证是在自己构造的索引上做的，恰好掩盖了这一点。

## 验证方法（可复现）

不依赖浏览器，直接在 Node 里跑站点自带的搜索 worker 对真实索引做端到端查询：

1. `vm.runInThisContext` 加载 `.mkdocs-site/assets/javascripts/workers/search.*.min.js`，垫片提供 `self` / `addEventListener` / `postMessage` / `importScripts`（后者同步读站点里的 `assets/javascripts/lunr/**` 语言包）；
2. 发 `{type: 0}`（SETUP）消息，payload 取 `search/search_index.json` 的 `{config, docs}`；
3. 依次发 `{type: 2}`（QUERY）消息，统计 `data.items` 条数与高亮标题。

对比两份产物（除分词工序外完全相同，同一批文档）：

| 查询 | 后处理版（空格） | 纯 material 版（`\u200b`） | 另加专名词典版 |
|---|---|---|---|
| 子模块 | 58 | 58 | 58 |
| 模块 | 32 | 32 | 23 |
| 飞书 | 8 | 8 | 8 |
| 多维表格 | 54 | 54 | 83 |
| 表格 | 54 | 54 | 53 |
| 子进程 | 74 | 74 | 74 |
| 进程 | 56 | 56 | 56 |
| 微调 | 12 | 12 | 12 |
| 规范 | 19 | 19 | 19 |
| GUIDE | 10 | 10 | 10 |

**关键结论**：前两列 10 个查询**命中数完全一致**——后处理只是把 `\u200b` 两侧补了空格，token 集合没变，搜索行为等价。它唯一实际改变的是索引体积与构建耗时（每次构建多跑一遍 jieba，serve 模式每次热重建都要付这笔钱）。

## 方案取舍

| 方案 | 判断 |
|---|---|
| **A. 保留后处理 + 改成 ZWSP 感知**（先剥 `\u200b` 再 jieba 切词） | 否。收益仅在于能补专名词典，而专名词实测无收益（见下） |
| **B. 引入构建钩子（`hooks:` + `on_post_build`）让 serve 也分词** | 否。目标本就已达成，钩子只增加一份自维护代码与 `__pycache__` 噪声 |
| **C. 用上游 `search.jieba_dict_user` 补专名词典** | 否。实测混合结果：`模块` 32→23 召回变少、`多维表格` 54→83 噪声变多，无稳定收益 |
| **D. 删除后处理，依赖 material 内置链路（采用）** | 是。代码更少、构建更快、行为与上游一致；`jieba` 依赖保留并在注释里写明是它触发中文切分 |

关于 D 的风险与兜底：万一将来 material 去掉 CJK 处理，中文搜索会退化——因此在 `mkdocs.yml` 与 `build_docs.py` 的注释里写明了这条依赖关系与退化表现，便于排查；真到那天再按方案 C（上游词典选项）或 A 处理。

## 变更清单

- `.scripts/build_docs.py`：删除 `segment_search_index()` 及其三处调用（`json` / `re` 导入一并移除），docstring 改为说明「中文搜索由 material + jieba 提供，三入口一致」；保留 `jieba` 依赖；
- `mkdocs.yml`：搜索插件注释改写成「material 内置 jieba 切分 + `\u200b` 分隔符 + 查询侧贪心切分」，并注明补词可用 `jieba_dict_user`；
- `docs/index.md`：站点维护段落补 `preview` 入口与「三入口一致 / `file://` 下搜索不可用」的说明；
- 未新增任何钩子文件、未新增词典文件（中途创建过 `.scripts/mkdocs_hooks.py`，验证后删除，`__pycache__` 一并清理）；
- 三个 `.bat` 均无需改动。

## 执行编排

## Stage 1: 核查「serve 是否真的搜不了中文」 ✅
- [x] 读 material 搜索插件源码，定位 `_segment_chinese`（jieba + `\u200b`）与 zh 语言包 separator；
- [x] 读 worker 源码（source map 里的 TS 原文），确认查询侧 `segment()` 按索引词表贪心切分；
- [x] 在 Node 里跑真实 worker + 真实索引，10 个中文/英文查询端到端验证。

## Stage 2: 对比实验 ✅
- [x] 构建「无后处理」与「有后处理」两份产物并逐查询对比 → 10 个查询命中数全部一致，确认后处理是 no-op；
- [x] 另测 `jieba_dict_user` 专名词典变体（飞书/子模块/多维表格/子进程）→ 无稳定收益，放弃。

## Stage 3: 落地 ✅
- [x] 删除后处理与钩子文件，改注释与文档；
- [x] 复验 `build` / `serve` 两个入口：strict 构建 exit=0、索引含 jieba 词（`子\u200b模块` 在 HTTP 响应的索引里出现 62 次）、serve 热重建后新小节进入索引；确认无残留进程与临时目录（清理了 2 个 `mkdocs_*` 残留）。

## 附：serve 模式的两个实现细节（本轮实测）

1. **serve 不写 `.mkdocs-site`**：`mkdocs serve` 把站点构建到临时目录（`tempfile.mkdtemp(prefix='mkdocs_')`，Windows 下即 `%TEMP%\mkdocs_xxxx\`），退出时删除。因此排查 serve 的搜索问题要看**临时目录或 HTTP 响应**，盯 `.mkdocs-site/search/search_index.json` 的 mtime 会得出错误结论（本轮就踩过这个坑）。强制 kill 会跳过清理，留下 `mkdocs_*` 残留目录，需手动删。
2. **热重建会刷新搜索索引**：向 `docs/index.md` 追加一个带标记的小节后，热重建使页面 HTML 立即含新内容，搜索索引里也出现了新条目（`index.html#<新小节锚点>`）——索引里的文字同样经过 jieba 切分，所以用「连续中文标记串」去 grep 索引会误判为「没更新」（本轮第二个坑：标记被切成 `热\u200b更新\u200b标记\u200b…`）。

本轮验证用的一次性脚本（Node 搜索 harness、serve 热重建探针）放在 `%TEMP%` 未入库，按「验证方法」与上述两节描述即可快速重建。

---

**最后更新**：2026-09-23
**作者**：AI & User
**版本**：v1.0（结论：serve 本就同时具备热刷新与中文搜索；冗余的 jieba 后处理已删除）
