# docs 阅读体验调研：SQLite 存档 vs Markdown 源 + 静态站点

> 调研发起：用户议题链"项目文档沉淀到 sqlite.db → AI 用 litecli 读 → 浏览器编辑器式阅读/实时刷新 → RAG/搜索 → git 二进制膨胀怎么办 → sqlite 取代文件系统？ → 不用浏览器/不起端口 → 不用 rust 的多语言协同（exe + 管道，unix 理念）"。
>
> 结论先行：**不要让 SQLite 取代文件系统，要分层——Markdown 源文件（git 管）→ 静态 HTML 构建产物（人读，不入库）→ 可选派生索引（人搜用 Pagefind / mkdocs 内置搜索，agent 用 FTS5 或 AOCI 既有机制）**。面向本仓库的首选工具是 Material for MkDocs。

---

## 1. 本仓库 docs/ 现状（2026-09 盘点）

| 项 | 现状 | 对选型的影响 |
|---|---|---|
| 规模 | 66 个 `.md`，另有少量 `.yml/.sql/.html/.ico` | 规模小，任何 SSG 构建都是秒级 |
| 层级 | 最深 5 层：`projects/<lang>/<项目>/specs/<NN>/design.md` | **必须"目录即导航"**，手动维护 SUMMARY/导航不可接受 |
| 文件名 | 中文为主（如《CLI 工具开发标准.md》） | 考验中文搜索分词、URL 编码、导航生成 |
| 现有布局 | `docs/` 根有 guides/plans/projects/repo/assets 五区 | 理想方案应原地渲染，不搬迁源文件 |
| git 归属 | 全部在父仓库，随 git 分发 | 构建产物必须可 `.gitignore`，否则仓库膨胀 |

痛点：**人类阅读体验差**——层级深、中文文件名，在文件管理器/编辑器里逐层点开很费劲；无全文搜索；无目录树总览。

## 2. 核心架构判断：分层，不是取代

```
┌─ 源层（唯一事实源）──────────── md 文件 + git
│    AI 的 read/grep/edit 原生工具链全兼容；diff/review 天然可用
├─ 阅读层（构建产物，不入库）──── 静态 HTML 站点
│    mkdocs/zola/mdbook build 产出；.gitignore 掉；随时重建
├─ 搜索层（派生索引，面向人）──── SSG 内置搜索 或 Pagefind 后处理
└─ 认知层（派生索引，面向 agent）─ AOCI（已在使用）/ 可选 sqlite FTS5
```

### 2.1 为什么"文档只存 SQLite"不成立

- **AI 侧逆训练分布**：agent 的训练与工具链（read/grep/glob/edit）全部以文本文件为中心。换 SQLite 后每步交互变成"拼 SQL → 起 CLI 进程 → 解析表格输出"，token 成本与出错率都升，**写入（文档迭代）尤其不自然**——没有"编辑第 37 行"这种增量操作，只有整字段重写。
- **litecli 定位错误**：litecli 是给人用的交互式 REPL（自动补全/表格美化），agent 场景该用 `sqlite3 -json` 或 MCP sqlite server；但这只是缓解接口问题，不改变上面的根本问题。
- **git 侧膨胀真实存在**：SQLite 页式存储，任何小改动都重写页；二进制 diff 无意义，仓库体积单调增长。git-lfs 是专门工具，但设计目标是"大文件、低频变更"，与"文档小改频繁"完全错配。
- **两个现成参照**：
  - **Fossil**（SQLite 作者的 VCS，2026-03 发布 2.28）：仓库本身就是 SQLite 单文件，原子事务 + 自校验 + 内置 web UI。证明"sqlite 当版本库"技术可行且有 20 年实践，但生态与 git 世界隔离，对本仓库无迁移价值——仅作为该路线的完整性证明。
  - **AOCI**（本仓库在用）：`aoci.txt` 人类可读文本索引 + `.aoci/` 内 SQLite 账本。"语义留文本、机器数据进库"正是分层的活实践。
  - **zread**：LLM 从代码生成 wiki 到 `.zread/wiki/`（markdown 产物，agent 直接读文件而不是查库）——同样是"最后回到文本"。

### 2.2 分层后各议题的落点

| 原始议题 | 分层方案下的落点 |
|---|---|
| AI 用 litecli 读库 | 不需要。AI 继续用 read/grep 直读 md；要结构化检索时查派生 FTS5 索引（只读，构建产物） |
| 浏览器编辑器式阅读 + 实时刷新 | `mkdocs serve`/`zola serve` 写作时热刷新（本地端口仅写作期用）；日常阅读直接开构建产物 |
| 不想开端口/开浏览器 | 构建产物支持 `file://` 直开（见 3.5 兼容性矩阵） |
| RAG / 搜索 | 人搜：SSG 内置搜索或 Pagefind；agent 检索：FTS5 索引或 AOCI 既有机制 |
| git 膨胀 | 构建产物全部 `.gitignore`，git 里只有纯文本 md，零膨胀 |
| sqlite 取代文件系统 | 不取代，降级为"派生索引"角色 |

## 3. 候选方案对比

### 3.1 总表

| 方案 | 形态 | 依赖 | 目录即导航 | 中文搜索 | `file://` 直开 | 写作热刷新 | 源文件是否要搬家 |
|---|---|---|---|---|---|---|---|
| **Material for MkDocs** | 静态构建 | Python + pip（本仓库有 uv，等于零成本） | ✅ 插件自动（awesome-pages / literate-nav） | ⚠️ 需配置（lunr-languages + jieba） | ✅（`use_directory_urls: false` + 内置搜索 JS 内嵌） | ✅ `mkdocs serve` | 否（`docs_dir` 指向 `docs/`） |
| **Zola** | 静态构建 | 单二进制，零依赖 | ✅ 内容目录即结构 | ❌ 内置 elasticlunr 无中文分词（硬伤） | ✅ | ✅ `zola serve` | 基本否，但节页面要补 `_index.md` |
| **mdBook** 0.5.4 | 静态"书" | 单二进制 | ❌ `SUMMARY.md` 手动维护 66 项×5 层 | ⚠️ CJK 分词弱 | ✅ | ✅ `mdbook serve` | 是（内容须进 `src/`，配置可绕） |
| **docsify** | 运行时渲染 | 零构建，但页面全靠浏览器 JS | ✅ 侧边栏文件 | ⚠️ 需插件 | ❌ 本地需起服务 | ✅ LiveReload | 否 |
| **Pagefind** 1.5.0 | 任意静态站的搜索后处理 | 单二进制（索引期）| —（不生成导航） | ⚠️ CJK 需实测 | ❌ 搜索索引靠 fetch，`file://` 受限 | — | —（挂在其他 SSG 之后） |
| **Fossil** | sqlite VCS + 内置 web UI | 单二进制 | ✅ | —（wiki 自带搜索） | ❌ 需起 `fossil ui` | — | 是（整体换 VCS，不可行） |
| **SQLite 唯一源 + 自研 UI** | 全定制 | 自研 | 自研 | 自研 FTS5 | 自研 | 自研 | 是（且 AI/git 双输，见 2.1） |

### 3.2 各方案要点

**Material for MkDocs**（`squidfunk/mkdocs-material`，MIT，5 万+ 组织在用，FastAPI 文档即它）
- 最成熟的"知识库"形态：多级侧边栏、页面级搜索（可搜代码块）、tags、离线可用、60+ 语言。
- 本仓库适配点：`mkdocs.yml` 里 `docs_dir: docs`（注意排除 assets/ico 等非文档资源）；导航用 `awesome-pages` 插件按目录自动生成，中文文件名直接变中文导航标题；搜索插件配置 `lang: zh`（依赖 lunr-languages + 结巴分词，官方有中文搜索支持文档）。
- Python 生态对本仓库零负担（uv 已就位，PEP 723 内联依赖即可跑构建脚本，不产生工程文件——注意与仓库"禁止根级 pyproject/venv"约束兼容：用 `uv run --with mkdocs-material mkdocs build` 一类方式或 `.scripts/` PEP 723 脚本）。

**Zola**：最符合"rust 理念、单二进制、秒级构建、零依赖"，使用者完全不碰 rust。败在中文搜索：内置搜索基于 elasticlunr.js，无中文分词，对中文标题/正文的检索质量不可接受——本仓库中文文件名为主，直接出局为备选。

**mdBook**：为"线性书"设计，`SUMMARY.md` 手动目录与"66 个文件、5 层、随项目增删"的现实冲突最大；CJK 搜索同样偏弱。不推荐。

**docsify**：运行时渲染（浏览器拉 md 现场渲染），零构建但牺牲静态性、离线性与 `file://` 能力，与"构建产物"方向相反。仅记录为对照。

**Pagefind**：思路与"sqlite 派生索引"同源（构建后为静态 HTML 建分片索引，浏览器端按需加载，万页级站点总载荷 <300KB），且**与 SSG 完全解耦**——将来若 mkdocs 内置搜索中文效果不佳，可在 `mkdocs build` 之后追加 `pagefind` 一道工序，不动其他环节。注意其浏览器端搜索依赖 fetch 索引分片，`file://` 直开场景受限，需起本地静态服务（如 `python -m http.server`）才可用。

**Fossil / SQLite 唯一源 / 自研**：见 2.1，分别因生态隔离、AI+git 双输、成本不成比例而不取。

### 3.3 写作期实时刷新与日常阅读的分工

- **写作期**：`mkdocs serve`（localhost 端口 + 保存即刷新）。端口仅存在于写作会话，不常驻——回应"不想每项目挂一个服务"。
- **日常阅读**：`mkdocs build` 产物（`site/`，`.gitignore`），双击 `index.html` 以 `file://` 浏览；需要搜索时再起一次性静态服务。构建命令收敛为一个 `.scripts/` PEP 723 脚本（如 `uv run .scripts/build-docs.py`），与仓库既有脚本约定一致。

## 4. 推荐组合（面向本仓库）

1. **主线**：Material for MkDocs + awesome-pages 自动导航 + 内置搜索（配置中文分词）+ `site/` 不入库。
2. **备选修正**：若中文搜索实测不达标 → 追加 Pagefind 后处理（仅牺牲 `file://` 直开搜索）；若彻底想脱离 Python → Zola（需自认中文搜索缺陷）。
3. **agent 侧不动**：AI 继续用 read/grep 直读 md（现状已最优）；结构化检索需求已由 AOCI 覆盖（`aoci.txt` 即认知索引），无需再建 FTS5——等真有"跨 66 文档语义检索"的刚需再议。
4. **不做**：文档迁 SQLite、自研 UI、迁 Fossil。

预期收益：导航树 + 全文搜索 + 移动端可读 + 写作热刷新；git 零膨胀；AI 工作流零改动。

## 5. 附注：多语言协同与 unix 理念（议题链尾部）

- **"rust 理念但不用 rust"完全成立**：zola/mdbook/pagefind 都是 rust 写的单二进制，使用者只拿 exe，不碰工具链；同理 Go 有 charm 栈（glow/bubbletea）。选工具看产物形态，不看实现语言。
- **exe + 管道交互 = stdio JSON 协议**，已有三个规模化先例：LSP（编辑器↔语言服务器）、MCP（agent↔工具）、zread `--stdio`（JSON-line 机器协议，供程序间驱动）。将来任何自研工具走这条路径都是正路。
- 本调研结论不涉及自研；若日后做通用工具项目（go_projects 下 CLI），再按《CLI 工具开发标准》立项。

## 6. 遗留问题

| # | 问题 | 消解方式 |
|---|---|---|
| 1 | mkdocs 内置搜索对中文文件名/正文 的实际效果 | 实施前用 10 篇样例实测（jieba 配置后） |
| 2 | `file://` 直开时 mkdocs 相对路径细节（`use_directory_urls: false` 等） | 实施时验证 |
| 3 | docs/ 中非 md 资源（.yml/.sql/.ico）在站点中的呈现策略 | 实施时决定（排除或作为附件） |
| 4 | 是否值得做 | 待用户决策；实施走 plans/ 计划流程 |

---

**最后更新**：2026-09-21
**作者**：AI（opencode，GLM）调研产出
**性质**：调研笔记（未立项，未实施）
