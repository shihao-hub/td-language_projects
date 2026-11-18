# Plan：docs 静态文档站点（Material for MkDocs）

> 调研依据：《docs/repo/docs 阅读体验调研：SQLite 存档 vs Markdown 源 + 静态站点.md》第 4 节推荐组合。

## 问题陈述

本仓库 `docs/` 共 66 个 md 文件、最深 5 层镜像结构、中文文件名为主，人类阅读体验差：无导航树总览、无全文搜索、逐层点开费劲。需要一个静态站点方案改善阅读，同时不动 md 源文件、不让构建产物进 git。

## 需求（含用户原话决策）

- 选型 **Material for MkDocs**（用户已确认："那就用：Material for MkDocs"）
- 阅读形态：静态 HTML 构建产物，**`file://` 直开优先**（用户确认"不想开端口/开浏览器：嗯嗯"）
- 写作期可用本地 serve 热刷新（端口仅写作会话存在）
- 构建产物不入 git（零膨胀）；md 源零搬迁、零改动
- 中文搜索须实测，不达标用 Pagefind 补（主线不变）
- 构建入口统一走 `.scripts/` PEP 723 + uv（仓库脚本约定），不产生任何 Python 工程文件
- 数据文件强约束：uv 缓存在全局缓存，仓库内零运行时数据产生

## 背景

- 调研已对比 mdBook/Zola/docsify/Fossil/Pagefind，mkdocs-material 胜出点：awesome-pages 目录即导航（应对 5 层 66 文件）、Python 生态与 uv 零成本、内置搜索可配中文。
- `.scripts/` 现有 PEP 723 脚本风格（`# /// script` 头 + 中文 docstring + argparse），新脚本沿用。
- 根 `.gitignore` 现有 6 行（Thumbs.db/.DS_Store/.venv/），`site/` 追加即可。
- 已知坑（调研第 6 节）：中文分词效果、`file://` 相对路径（`use_directory_urls: false`）、非 md 资源呈现。

## 方案

```
mkdocs.yml（仓库根，docs_dir=docs, site_dir=site）
└─ .scripts/build_docs.py（PEP 723：mkdocs-material + mkdocs-awesome-pages-plugin）
   ├─ build：uv run .scripts/build_docs.py build  → 产出 site/（gitignore）
   └─ serve：uv run .scripts/build_docs.py serve  → 写作期热刷新
```

- 导航：awesome-pages 插件按目录自动生成，中文文件名即导航标题。
- 搜索：search 插件 `lang: zh` 配置；实测 10 个中文关键词。
- 直开：`use_directory_urls: false` + `site_url` 留空，保证 `file://` 下样式/导航/链接可用。
- 非 md 资源：`.yml/.sql/.ico/.html` 作为静态附件直接拷贝访问，不转换。

## 任务分解

### Task 1: 依赖与最小构建跑通
- 实现：写 `mkdocs.yml`（docs_dir=docs、site_dir=site、language: zh、use_directory_urls: false）；写 `.scripts/build_docs.py`（PEP 723 声明 mkdocs-material、mkdocs-awesome-pages-plugin，subprocess 调 mkdocs build/serve）；跑通首次 build。
- 测试：build 退出码 0，`site/index.html` 生成。
- Demo：浏览器打开 `site/index.html` 能看到文档内容。

### Task 2: 目录即导航树 + 资源排除
- 实现：启用 awesome-pages；确认 5 层结构完整映射（guides/plans/projects/repo）；处理 assets 等 non-doc 资源的 exclude/not_in_nav 配置。
- 测试：导航树条目与 docs 目录一一对应；中文标题无乱码；`docs/repo/lark_group_bridge/*.html` 存档可直接访问。
- Demo：`file://` 打开后侧边栏完整导航树可逐层展开。

### Task 3: 中文搜索配置与实测
- 实现：search 插件 `lang: zh`（jieba/lunr 中文分词链路）；准备 10 个实测关键词（子模块、图标、水印、飞书、Celery、Redis、规范、指南、微调、子进程）在 `file://` 下搜索验证。
- 测试：关键词命中预期文档（标题与正文各覆盖）。
- Demo：`file://` 搜索"子模块"命中《Git 子模块分支机制》等页。
- 失败分支：不达标 → 追加 Pagefind 后处理（构建链加一道索引工序；代价：file:// 下搜索需起一次性静态服务），并在本计划记录决策。

### Task 4: file:// 直开适配定稿 + 构建脚本收尾
- 实现：`use_directory_urls: false` 下全站链接/样式/搜索复验；根 `.gitignore` 追加 `site/`；build_docs.py 加 `--strict` 校验选项（断链检查）。
- 测试：双击 `site/index.html` 全功能可用；`--strict` build 通过；`git status` 无构建产物泄漏。
- Demo：从双击到搜索的零服务完整浏览流。

### Task 5: 集成收尾与全量验证
- 实现：脚本 docstring 写清用法（build/serve/strict）；确认 uv 缓存不落仓库；全量重算一次 build 并抽查 5 层各一个页面。
- 测试：全量 build + strict + git status 三绿。
- Demo：`uv run .scripts/build_docs.py build` 一条命令从干净状态到可浏览站点。

## 执行编排

## Stage 1: 站点骨架 ✅
- [x] Task 1、Task 2（顺序：先跑通再调导航）
- ✅ 2026-09-21 完成：mkdocs.yml + .scripts/build_docs.py 落地；新增 docs/index.md 作为站点首页（docs 根此前无 index，mkdocs 生成不了首页）；awesome-pages 目录即导航验证通过（5 层 71 页，中文标题正常，lark_group_bridge 的 html 存档原样拷贝可直接访问）。

## Stage 2: 中文搜索 ✅
- [x] Task 3（含 Pagefind 条件分支）
- ✅ 2026-09-21 完成，未走 Pagefind 分支，最终方案为 **jieba 构建期预分词后处理**。曲折记录：① mkdocs worker bundle（39KB）无任何 CJK 分词器；② `separator` 零宽断言方案在 lunr tokenizer 的"逐字符 match"架构下恒失败，死路；③ 深入 worker 源码发现 mkdocs 原生设计了查询侧中文机制 `fe()`（基于倒排索引词典的子串匹配 + wildcard），索引侧只缺分词器——jieba 后处理恰好补位。实现：build 后对 search_index.json 的 title/text（标签外文本、仅中文连续段）jieba 分词为空格分隔；补词（飞书/子模块/多维表格）。离线模拟 worker 全链路（索引构建+fe 切分+AND 匹配）验证 8 个中文查询全部正确命中（子模块→33 篇、微调→15 篇、发件箱精确命中、规范→GUIDE/CLI 标准等）。
- ⚠️ 已知限制：`file://` 下浏览/导航/链接全可用，但浏览器安全策略禁止 fetch 索引与 Worker，搜索必须经 http（serve 模式）；serve 模式不跑分词后处理，中文搜索以 build 产物为准。
- 🔧 **2026-09-23 更正**（见《[09-docs-serve-chinese-search.md](09-docs-serve-chinese-search.md)》）：上述「中文分词靠本计划加的 jieba 后处理」是误判——mkdocs-material 搜索插件自带 CJK 处理（jieba 切词 + `\u200b` 分隔），只要 jieba 可导入，**build 与 serve 行为一致、中文搜索开箱即用**；该后处理工序实测对搜索结果零影响，已删除。

## Stage 3: 直开与脚本定稿 ✅
- [x] Task 4
- ✅ 2026-09-21 完成：`use_directory_urls: false` + `site_url: ""` 下 file:// 直开验证通过（浏览器实测渲染完整）；根 .gitignore 追加 `site/`（git status 确认拦截）；`--strict` 通过（validation.links.not_found 设为 ignore——docs 内 md 大量链接仓库源码，file:// 下实际可达，不应按死链误报）。

## Stage 4: 验证 ✅
- [x] Task 5（全量验证 + git 清洁检查）
- ✅ 2026-09-21 完成：strict 全量构建 exit=0 + 1751 字段分词后处理成功 + git status 无构建产物泄漏（site/ 拦截生效）。一条命令从干净状态到可浏览站点：`uv run .scripts/build_docs.py build`。

---

**最后更新**：2026-09-21
**作者**：AI & User
**版本**：v1.1（执行完毕；中文搜索最终方案为 jieba 预分词，Pagefind 备选未启用）
