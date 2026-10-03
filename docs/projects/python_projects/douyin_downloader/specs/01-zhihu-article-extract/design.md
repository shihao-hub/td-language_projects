# Design Document

## Overview

在 `douyin_dl.py` 单文件四层结构（契约 / 基础设施 / Service / CLI 适配）内新增知乎提取链路：CDP 登录态校验 → 页面导航与正文渲染等待 → 浏览器内 JS 返回正文 innerHTML → Python 侧下载原图 → bs4 清洗 → html2text 组装 Markdown 落盘。与抖音/B 站链路在 Service 层并行，由四分类编排。

## Context

- 30 号计划（B 站支持）已落地（提交 eadee1f / 90615eb / a2734d1，VERSION 2.4.0），以下基础设施均已核实可用：`cdp_get_cookies(port, url)`（:620）、`http_get_json(url, headers)`（:814）、`open_tab(target_url, port, host_filter, navigate=True)`（:784）、`download_stream(video_url, output_path, headers)`（:836）、`page_title(ws_url)`（:1236）、`is_bilibili_url`（:1058）、`ExtractResult` 三分类（:983）、`ERROR_MESSAGES`（:79）。
- 新增依赖 `beautifulsoup4` + `html2text`（均纯 Python）：HTML→Markdown 是成熟问题，交给库而非手写转换；PEP 723 声明后 `uv run` 自动准备，Nuitka 打包按 NUITKA.md 实测验证一次（体积预期 +1MB 级）。
- 匿名直连 zhihu.com 实测 403（2026-10-02，curl 真实 UA），纯 HTTP 抓取路线不可行。
- 知乎登录态关键 cookie `z_c0` 为 HttpOnly，只能经 CDP `Network.getCookies` 读取。
- 知乎页面为富文本渲染，正文容器 `.Post-RichTextContainer`（新版）或 `.RichContent-inner`（老版）；图片为 `<figure><img>` 多清晰度候选（`data-actualsrc` / `data-original` / `srcset` / `src`）懒加载。

## Goals and Non-Goals

- Goals：回答与专栏文章两类 URL 的原封不动提取（文字 + 原图）；登录门与 B 站同构；转换逻辑复用成熟库；契约与实现一致。
- Non-Goals：见 requirements.md Out of Scope（多回答、评论、公式还原、卡片等）。

## Detailed Design

### 契约层

- `UPDATED` `douyin_dl.py`
  - **Purpose** 错误码、JSON 包络、schema 定义
  - **Changes** `ERROR_MESSAGES` 新增 `zhihu_not_logged_in`、`zhihu_extract_failed`；`_schema_response_property` 增 `extracted` 数组（item：`input_url`/`article_url`/`article_id`/`ok`/`title`/`path`/`images_total`/`images_failed`/`error`），`summary` 增 `extracted`；`build_schema` 更新 description/summary/constraints/`side_effects.network`（加 zhihu.com、zhimg.com）/`side_effects.filesystem`（加 `{output_dir}/zhihu`）/VERSION=2.5.0
  - **Complexity** Low

### 基础设施层

- `CREATED` `http_get_bytes(url, headers) -> bytes`（`douyin_dl.py`）
  - **Purpose** 通用字节下载（图片用），与 30 号 `http_get_json` 并列
  - **Changes** UA + 自定义头、60s 超时、非 2xx 抛异常；实现与 `download_stream` 相同风格但不打印进度
  - **Complexity** Low
- `UPDATED` `unique_path(directory, stem, suffix=".mp4")`
  - **Purpose** 输出路径防覆盖
  - **Changes** 无改动（知乎落盘时对**目录名**做同款唯一化：候选 `{标题}` 已存在则 `_1`、`_2` 顺延，逻辑内联在 `extract_zhihu_one`；目录内文件名固定，不再调用本函数）
  - **Complexity** Low

### Service 层

- `CREATED` `is_zhihu_url(url) -> bool`（`douyin_dl.py`）
  - **Purpose** zhihu.com 域判断
  - **Changes** hostname 去 www 前缀后判断等于 `zhihu.com` 或以 `.zhihu.com` 结尾（含 zhuanlan 子域），模式仿 30 号 `is_bilibili_url`
  - **Complexity** Low
- `CREATED` `resolve_zhihu_url(url) -> tuple[str, str]`（返回 `(article_url, article_id)`）
  - **Purpose** 归一化并提取 aid/pid
  - **Changes** 正则 `/answer/(\d+)` → article_id=aid；`/p/(\d+)` → pid；均无 → `invalid_url`；返回时保留原 URL 作为 article_url（知乎无需短链重定向）
  - **Complexity** Low
- `CREATED` `check_zhihu_login(port) -> bool`（`douyin_dl.py`）
  - **Purpose** 登录门
  - **Changes** 复用 30 号 `cdp_get_cookies(port, "https://www.zhihu.com")`，校验 `z_c0` 非空；异常时返回 False（不抛，由编排层转 `zhihu_not_logged_in`）
  - **Complexity** Low
- `CREATED` `ZHIHU_EXTRACT_JS`（模块级字符串常量）
  - **Purpose** 浏览器内提取脚本（仅采集原始 HTML，转换交给库）
  - **Changes** 逻辑：① 分段滚动到底再回顶（每段 `window.innerHeight`，间隔 300ms）触发懒加载；② 定位正文容器：依次查 `.Post-RichTextContainer`、`.RichContent-inner`、`.RichText`，取第一个非空；③ 返回 JSON 字符串（含 title、author、正文容器 `innerHTML`）；正文容器缺失返回 `null`。不再在 JS 内做 DOM→块数组转换（该逻辑由 bs4 + html2text 承担）
  - **Complexity** Low
- `CREATED` `extract_zhihu_article(ws_url, url) -> (title, author, html)`（`douyin_dl.py`）
  - **Purpose** 页面加载与提取编排
  - **Changes** 导航（复用 `navigate_page`）→ 轮询 `eval_cdp` 检查正文容器出现（30 次 × 1s，超时抛 `zhihu_extract_failed`，detail 带页面标题与正文候选区文本量统计便于定位改版）→ 执行 `ZHIHU_EXTRACT_JS`；标题复用 `page_title()` 并清洗「 - 知乎」后缀，失败 fallback article_id；作者缺失置空字符串（元信息不致命）
  - **Complexity** Medium
- `CREATED` `download_zhihu_images(image_urls, images_dir, cookie_header) -> dict[str, str]`（`douyin_dl.py`）
  - **Purpose** 原图下载，返回「绝对 URL → 本地文件名」映射
  - **Changes** 输入为去重后的图片 URL 清单（键=绝对 URL）；按出现顺序命名 `image_001.ext` 起，扩展名从 URL path 后缀推断（`jpg/jpeg/png/gif/webp` 白名单，其他/无后缀默认 `.jpg`）；`http_get_bytes` 带 `Referer: https://www.zhihu.com/` + `Cookie`；单张异常捕获后 `images_failed += 1`，该 URL 不进入映射（清洗阶段保留原 URL 引用）
  - **Complexity** Low
- `CREATED` `clean_zhihu_html(html, images_map) -> str`（`douyin_dl.py`，BeautifulSoup 预处理）
  - **Purpose** 把知乎正文 HTML 清洗为可转换形态并本地化图片
  - **Changes** 遍历 `img`：按 `data-actualsrc` → `data-original` → `srcset` 最大候选 → `src` 取候选、`new URL(x, "https://www.zhihu.com")` 绝对化、跳过 `data:` 占位图；URL 命中 `images_map` 时把 `src` 替换为相对路径 `images/image_00N.ext`（md 与 images 同级）并补 alt（`图N`）；剥掉投票/广告等无关壳元素与冗余 `noscript` 包裹；返回清洗后的 HTML 字符串
  - **Complexity** Medium
- `CREATED` `render_zhihu_markdown(title, author, article_url, clean_html, fetched_at) -> str`（`douyin_dl.py`）
  - **Purpose** 清洗后 HTML → Markdown 文本
  - **Changes** `html2text.HTML2Text` 配置 `body_width=0`（中文不断行）、`ignore_images=False`，转换 `clean_html`；头部 `# {title}` + 元信息引用块（`> 来源: article_url`、`> 作者: author`、`> 提取时间: ISO8601`）；对转换结果做轻量后处理（图注 figcaption 斜体行、残留占位清理）
  - **Complexity** Low
- `CREATED` `extract_zhihu_one(input_url, ...) -> ExtractRecord`（`douyin_dl.py`）
  - **Purpose** 单条知乎提取编排
  - **Changes** 登录门（无 z_c0 → `zhihu_not_logged_in` 失败，emit 指引；headed 且未登录时自动 `open_tab` 打开 zhihu.com）→ resolve → `open_tab(port, url, host_filter="zhihu.com")` → extract → 建文章目录 `{output_dir}/zhihu/{标题}/`（`os.makedirs` 含 zhihu 层；目录名唯一化：已存在则 `_1`、`_2` 顺延）→ bs4 提取图片清单并 `download_zhihu_images` 落盘该目录 `images/` → `clean_zhihu_html` 本地化 → `render_zhihu_markdown` → 写入 `article.md`（UTF-8）→ 填 `ExtractRecord`（path 指向 article.md）
  - **Complexity** Medium
- `UPDATED` `ExtractResult` / `extract_links` / `RunResult` / `to_data`（`douyin_dl.py`）
  - **Purpose** 四分类与结果承载
  - **Changes** `ExtractResult` 增 `zhihu: list[str]`；`extract_links` 增 zhihu 分支（`is_zhihu_url`）；新增 `ExtractRecord` dataclass（`input_url`/`article_url`/`article_id`/`ok`/`title`/`path`/`images_total`/`images_failed`/`error_*`/`to_json()`）；`RunResult` 增 `extracted: list[ExtractRecord]` 与 `extracted` 计数属性；`to_data` 输出增 `extracted` 数组与 `summary.extracted`
  - **Complexity** Low
- `UPDATED` `run_downloads`（`douyin_dl.py`）
  - **Purpose** 编排接入
  - **Changes** zhihu 队列串行处理（复用 emit 进度、同一 Chrome 会话）；Chrome 启动失败等入口级错误行为不变
  - **Complexity** Low

### CLI 适配层

- `UPDATED` `render_text` / `build_parser` / `main`（`douyin_dl.py`）
  - **Purpose** 人读渲染与参数
  - **Changes** `render_text` 增 extracted 条目渲染（`[OK]/[FAIL]` + md 路径 + 图片计数）；`build_parser` description/epilog 提及知乎提取；`main` 退出码逻辑复用（有失败项 → 1）
  - **Complexity** Low

### Module Collaboration and Data Flow

```
run_downloads(text)
  → extract_links 四分类（douyin / bilibili / zhihu / skipped）
  → ensure_chrome_running（复用同一 profile）
  → for url in zhihu 队列:
      check_zhihu_login(port)          # cdp_get_cookies → z_c0
      ├─ 无登录态 → ExtractRecord(zhihu_not_logged_in)，headed 时 open_tab 开 zhihu.com
      └─ 有登录态 → resolve_zhihu_url → open_tab(host_filter=zhihu.com)
                    → extract_zhihu_article: navigate → 轮询正文容器 → ZHIHU_EXTRACT_JS(innerHTML)
                    → 建 {output_dir}/zhihu/{标题}/（目录名唯一化）
                    → download_zhihu_images: http_get_bytes(Referer+Cookie) → images/
                    → clean_zhihu_html(bs4) → render_zhihu_markdown(html2text)
                    → article.md 落盘 UTF-8
```

- 依赖方向：CLI 适配层 → Service 层 → 基础设施层 → 外部资源（Chrome CDP / 知乎页面 / zhimg CDN）；契约层零依赖。
- 组装顺序：先建文章目录 `{output_dir}/zhihu/{标题}/` 与其 `images/` 子目录，Markdown 中图片引用 `images/image_00N.ext` 相对路径。
- 并发模型：全部串行；知乎 tab 与抖音 tab 在同一 Chrome 实例并存（`open_tab` 按 host 过滤复用，不跨域导航）。

### Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | `extract_links` 四分类 + `ExtractResult.zhihu` |
| AC-2 | `check_zhihu_login` + `extract_zhihu_one` 登录门 |
| AC-3 | `extract_zhihu_article` + `ZHIHU_EXTRACT_JS` + `download_zhihu_images` + `clean_zhihu_html` + `render_zhihu_markdown` |
| AC-4 | `resolve_zhihu_url`（/p/<pid> 分支）+ 上述链路 |
| AC-5 | `download_zhihu_images` 失败不致命策略 |
| AC-6 | `build_schema` + VERSION=2.5.0 |

## Design Review Notes

以下为按零上下文视角自审本设计的发现与处理：

- **HIGH（已修复）** 手写 HTML→Markdown 转换器是重复造轮子：白名单写死导致表格/实体转义/嵌套引用丢失，且"未知元素降级"仍需自维护分支 → 改用 bs4 清洗 + html2text 转换，JS 端只采集 innerHTML；未知元素降级由库承担（用户评审意见）。
- **MEDIUM（已修复）** 知乎 tab 与抖音/B 站 tab 在 `get_targets` 中如何区分未说明 → 明确 `open_tab` 按 host_filter 过滤复用各自 tab，不跨域导航。
- **MEDIUM（已修复）** 公式图片 src 为相对路径 `/equation?tex=...`，直接下载会失败 → `clean_zhihu_html` 中所有图片 URL 以 `new URL(x, "https://www.zhihu.com")` 绝对化。
- **MEDIUM（已修复）** 图片去重键与命名规则含糊 → 明确键为绝对 URL、按出现顺序 `image_001.ext` 编号，同 URL 复用同一文件（映射表驱动）。
- **MEDIUM（已修复）** 标题为空时文件名未定义 → 明确 fallback 为 article_id（复用 `clean_title` 的空值回退机制，标题轮询复用 `page_title`）。
- **NIT** 图片大小与超时未设上限：原封不动原则下不设大小上限，60s 超时沿用既有下载实现。
- **已核实** 基础设施锚点（`cdp_get_cookies` / `http_get_json` / `open_tab` / `page_title` 等）已对照 2.4.0 源码确认，非假设。
- **未验证假设（挂起，执行时实测校准）**：① 图片清晰度候选顺序 `data-actualsrc → data-original → srcset → src` 为经验假设，Task 3 实测该回答页后校准；② 正文容器选择器集合为当前版本实测候选，若页面结构变动则补充选择器；③ 图片 CDN 对 Referer 的要求强度（可能仅需 Referer 或需 cookie），以实测为准调整头组合；④ html2text 对知乎正文的转换效果（表格/图注/换行）需 Task 3 用 AC-3 基准回答实测后微调配置。
