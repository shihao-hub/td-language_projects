# Design Document

## Overview

在 `douyin_dl.py` 单文件四层结构（契约 / 基础设施 / Service / CLI 适配）内新增知乎提取链路：CDP 登录态校验 → 页面导航与正文渲染等待 → 浏览器内 JS 把正文 DOM 转为块数组 → Python 侧下载原图 → 组装 Markdown 落盘。与抖音/B 站链路在 Service 层并行，由四分类编排。

## Context

- 30 号计划（B 站支持）已落地，提供 `http_get_json(url, headers)`、`cdp_get_cookies(port, url)`、`open_tab(port, url, host_filter)`、三分类骨架与 `not_supported` skip reason。
- 匿名直连 zhihu.com 实测 403（2026-10-02，curl 真实 UA），纯 HTTP 抓取路线不可行。
- 知乎登录态关键 cookie `z_c0` 为 HttpOnly，只能经 CDP `Network.getCookies` 读取。
- 知乎页面为富文本渲染，正文容器 `.Post-RichTextContainer`（新版）或 `.RichContent-inner`（老版）；图片为 `<figure><img>` 多清晰度候选（`data-actualsrc` / `data-original` / `srcset` / `src`）懒加载。

## Goals and Non-Goals

- Goals：回答与专栏文章两类 URL 的原封不动提取（文字 + 原图）；登录门与 B 站同构；零新依赖；契约与实现一致。
- Non-Goals：见 requirements.md Out of Scope（多回答、评论、公式还原、卡片等）。

## Detailed Design

### 契约层

- `UPDATED` `douyin_dl.py`
  - **Purpose** 错误码、JSON 包络、schema 定义
  - **Changes** `ERROR_MESSAGES` 新增 `zhihu_not_logged_in`、`zhihu_extract_failed`；`_schema_response_property` 增 `extracted` 数组（item：`input_url`/`article_url`/`article_id`/`ok`/`title`/`path`/`images_total`/`images_failed`/`error`），`summary` 增 `extracted`；`build_schema` 更新 description/summary/constraints/`side_effects.network`（加 zhihu.com、zhimg.com）/VERSION=2.3.0
  - **Complexity** Low

### 基础设施层

- `CREATED` `http_get_bytes(url, headers) -> bytes`（`douyin_dl.py`）
  - **Purpose** 通用字节下载（图片用），与 30 号 `http_get_json` 并列
  - **Changes** UA + 自定义头、60s 超时、非 2xx 抛异常；实现与 `download_stream` 相同风格但不打印进度
  - **Complexity** Low
- `UPDATED` `unique_path(directory, stem, suffix=".mp4")`
  - **Purpose** 输出路径防覆盖
  - **Changes** 无改动（md 落盘时以 `.md` 后缀调用；`_images` 目录由调用方 `os.makedirs` 创建）
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
  - **Purpose** 浏览器内提取脚本
  - **Changes** 逻辑：① 分段滚动到底再回顶（每段 `window.innerHeight`，间隔 300ms）触发懒加载；② 定位正文容器：依次查 `.Post-RichTextContainer`、`.RichContent-inner`、`.RichText`，取第一个非空；③ 递归遍历 childNodes 输出块数组 `[{type, text?, src?, items?}]`：块级 `h1-h3`/`p`/`blockquote`/`pre`/`ul`/`ol`/`li`/`img`/`figcaption`；行内 `b|strong→**`、`i|em→*`、`code→\``、`a→[text](href)`（还原 `/link?target=` 参数）、`br→\n`；④ 图片块取值顺序 `data-actualsrc` → `data-original` → `srcset` 最大候选 → `src`，一律 `new URL(x, location.href).href` 绝对化，跳过 `data:image` 占位图；⑤ 返回 JSON 字符串（含 title、author、blocks）；正文容器缺失返回 `null`
  - **Complexity** Medium
- `CREATED` `extract_zhihu_article(ws_url, url) -> (title, author, blocks)`（`douyin_dl.py`）
  - **Purpose** 页面加载与提取编排
  - **Changes** 导航（复用 `navigate_page`）→ 轮询 `eval_cdp` 检查正文容器出现（30 次 × 1s，超时抛 `zhihu_extract_failed`）→ 执行 `ZHIHU_EXTRACT_JS`；标题取 `document.title` 清洗「 - 知乎」后缀，失败 fallback article_id；作者缺失置空字符串（元信息不致命）
  - **Complexity** Medium
- `CREATED` `download_zhihu_images(blocks, images_dir, cookie_header) -> (images_total, images_failed)`（`douyin_dl.py`）
  - **Purpose** 原图下载
  - **Changes** 按出现顺序去重（键=绝对 URL）；扩展名从 URL path 后缀推断（`jpg/jpeg/png/gif/webp` 白名单，其他/无后缀默认 `.jpg`）；`http_get_bytes` 带 `Referer: https://www.zhihu.com/` + `Cookie`；单张异常捕获后 `images_failed += 1` 并在该 img 块标记 `failed=True`（保留原 URL）
  - **Complexity** Low
- `CREATED` `render_zhihu_markdown(title, author, article_url, blocks, images_dir_name, fetched_at) -> str`（`douyin_dl.py`）
  - **Purpose** 块数组 → Markdown 文本
  - **Changes** 头部 `# {title}` + 元信息引用块（`> 来源: article_url`、`> 作者: author`、`> 提取时间: ISO8601`）；块映射：标题 `#`/`##`/`###`，`p` 段落，`blockquote` 每行 `> ` 前缀，`pre` 代码围栏，`ul`/`ol` 嵌套列表（`li` 用 `- ` 与 `1. `），`img` 成功图 `![图N]({images_dir_name}/image_00N.ext)`、失败图 `![图N](原始URL)`，`figcaption` 斜体行
  - **Complexity** Medium
- `CREATED` `extract_zhihu_one(input_url, ...) -> ExtractRecord`（`douyin_dl.py`）
  - **Purpose** 单条知乎提取编排
  - **Changes** 登录门（无 z_c0 → `zhihu_not_logged_in` 失败，emit 指引；headed 且未登录时自动 `open_tab` 打开 zhihu.com）→ resolve → `open_tab(port, url, host_filter="zhihu.com")`（30 号泛化产物）→ extract → 下载图片到 `{output_dir}/{标题}_images/` → render → `unique_path(output_dir, 标题, ".md")` 写入 UTF-8 → 填 `ExtractRecord`
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
                    → extract_zhihu_article: navigate → 轮询正文容器 → ZHIHU_EXTRACT_JS
                    → download_zhihu_images: http_get_bytes(Referer+Cookie)
                    → render_zhihu_markdown → unique_path(.md) 落盘 UTF-8
```

- 依赖方向：CLI 适配层 → Service 层 → 基础设施层 → 外部资源（Chrome CDP / 知乎页面 / zhimg CDN）；契约层零依赖。
- 组装顺序：图片目录先建（`os.makedirs`），Markdown 引用其相对目录名 `{标题}_images`。
- 并发模型：全部串行；知乎 tab 与抖音 tab 在同一 Chrome 实例并存（`open_tab` 按 host 过滤复用，不跨域导航）。

### Acceptance Criteria Mapping

| AC ID | Design Component |
|---|---|
| AC-1 | `extract_links` 四分类 + `ExtractResult.zhihu` |
| AC-2 | `check_zhihu_login` + `extract_zhihu_one` 登录门 |
| AC-3 | `extract_zhihu_article` + `ZHIHU_EXTRACT_JS` + `download_zhihu_images` + `render_zhihu_markdown` |
| AC-4 | `resolve_zhihu_url`（/p/<pid> 分支）+ 上述链路 |
| AC-5 | `download_zhihu_images` 失败不致命策略 |
| AC-6 | `build_schema` + VERSION=2.3.0 |

## Design Review Notes

以下为按零上下文视角自审本设计的发现与处理：

- **MEDIUM（已修复）** 知乎 tab 与抖音/B 站 tab 在 `get_targets` 中如何区分未说明 → 明确 `open_tab` 按 host_filter 过滤复用各自 tab，不跨域导航。
- **MEDIUM（已修复）** 公式图片 src 为相对路径 `/equation?tex=...`，直接下载会失败 → JS 提取时所有图片 URL 经 `new URL(x, location.href).href` 绝对化。
- **MEDIUM（已修复）** 图片去重键与命名规则含糊 → 明确键为绝对 URL、按出现顺序 `image_001.ext` 编号，同 URL 复用同一文件。
- **MEDIUM（已修复）** 标题为空时文件名未定义 → 明确 fallback 为 article_id（复用 `clean_title` 的空值回退机制）。
- **NIT** 图片大小与超时未设上限：原封不动原则下不设大小上限，60s 超时沿用既有下载实现。
- **未验证假设（挂起，执行时实测校准）**：① 图片清晰度候选顺序 `data-actualsrc → data-original → srcset → src` 为经验假设，Task 3 实测该回答页后校准；② 正文容器选择器集合为当前版本实测候选，若页面结构变动则补充选择器；③ 图片 CDN 对 Referer 的要求强度（可能仅需 Referer 或需 cookie），以实测为准调整头组合。
