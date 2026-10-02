# Plan for: douyin_downloader 扩展知乎文章提取支持

## 问题陈述

`douyin_downloader`（CLI 名 `douyin_dl`）目前处理抖音链接，30 号计划正在扩展 B 站视频下载（同一命令按域名分流）。用户进一步要求：**把知乎回答/文章里的文字、图片等原封不动提取出来**，保存到本地。实例链接：

> 如何看待王垠对 Cursor 等 AI 编程的评价「不懂计算机科学的人用好 AI 编程是妄想」？ - 王勃的回答 - 知乎
> https://www.zhihu.com/question/1923534024288236685/answer/2021258227166319271

本次在同一工具、同一命令内新增知乎提取能力（按域名四分类：douyin / bilibili / zhihu / skipped）；**项目名与命令名不变**（用户明确）。本计划**依赖 30 号计划（B 站支持）已落地**：复用其 `http_get_json`、`cdp_get_cookies`（含 HttpOnly）、`open_tab` 泛化、三分类骨架等产出。

## 需求（澄清确认）

1. 范围：**回答 + 专栏文章**两类 URL（`/question/<qid>/answer/<aid>`、`zhuanlan.zhihu.com/p/<pid>`）；问题页只提取链接指向的那一个回答，不做整页多回答。
2. 路线：**CDP 登录态 + 页面 DOM 提取**——真实浏览器（复用既有 profile）渲染页面后，在浏览器内用 JS 把正文 DOM 转成结构化块数组，Python 侧组装 Markdown；不走知乎 API（免 `x-zse-96` 签名），不做纯 HTTP HTML 解析（匿名实测 403）。
3. 输出：**Markdown + 本地图片**——正文文字（段落/标题/引用/代码块/列表/加粗斜体/链接）转 Markdown；图片**原图**下载到 `{标题}_images/` 子目录，Markdown 内相对路径引用；图注保留为图片下斜体行。
4. CLI 形态：**同一命令自动识别**——按域名分流，知乎链接走提取流程，与抖音/B 站链接可一条命令混吃。
5. 登录态：**复用 B 站同款登录门**——知乎链接处理前经 CDP 读 profile cookie 校验 `z_c0` 存在；无登录态按 `zhihu_not_logged_in` 结构化失败并给出 `--headed` 登录指引；`--headed` 模式下自动打开 zhihu.com 页面便于登录。

## 背景（探索发现）

- 本机匿名直连 `www.zhihu.com` 实测 **403 Forbidden**（BLB 网关风控，curl 带真实 UA 亦 403）→ 纯 HTTP 抓取路线不可行，必须真实浏览器 + 登录态。
- 30 号计划已提供/将提供：`http_get_json(url, headers)`、`cdp_get_cookies(port, url)`（浏览器级 `Network.getCookies` 可读 HttpOnly）、`open_tab(port, url, host_filter)`（原 `open_douyin_tab` 泛化）、`extract_links` 多分类骨架 → 知乎链路直接复用，无需重复建设。
- 知乎页面结构（当前版本）：回答正文容器为 `.RichContent-inner`（老版）或 `.Post-RichTextContainer`（新版）；专栏文章同为富文本容器（`.Post-RichTextContainer` / `.RichText`）；正文元素为 `p` / `h1-h6` / `blockquote` / `pre` / `ul` / `ol` / `figure(figcaption)`；图片为 `<figure><img>`，多清晰度候选分布于 `data-actualsrc` / `data-original` / `srcset` / `src`，懒加载未滚动时 `src` 可能是占位图。
- 图片 CDN 域 `pic*.zhimg.com`，下载需带 `Referer: https://www.zhihu.com/`（与 B 站 CDN 同模式），登录 cookie 一并携带更稳。
- 知乎登录态关键 cookie 为 **`z_c0`**（HttpOnly，只能经 CDP 读取）。
- `document.title` 形如「{标题} - 知乎」，文件名需清洗后缀。
- 现有代码相关锚点（`douyin_dl.py`，B 站任务落地前）：`extract_links`(:688)、`is_douyin_url`(:680)、`open_douyin_tab`(:542)、`eval_cdp`(:505)、`navigate_page`(:530)、`download_stream`(:576)、`unique_path`(:561)、`clean_title`(:731)、`build_schema`(:160)、`run_downloads`(:825)、`DownloadRecord`(:622)、`RunResult`(:654)。30 号计划落地后锚点以届时实际行为准。

## 方案

单文件四层结构不变（契约 / 基础设施 / Service / CLI 适配）。新增知乎处理链路与抖音/B 站链路在 Service 层并行，由 `extract_links` 四分类后分别编排；页面提取复用同一 Chrome 会话与 profile：

```mermaid
flowchart LR
    A[输入文本] --> B[extract_links 四分类]
    B -->|douyin 队列| C[既有 CDP 流程]
    B -->|bilibili 队列| D[30 号计划 B 站链路]
    B -->|zhihu 队列| E[CDP 读 profile cookie<br/>校验 z_c0]
    E -->|无登录态| X[zhihu_not_logged_in<br/>失败并提示登录方法]
    E -->|有登录态| F[open_tab 打开知乎页<br/>等待正文容器渲染]
    F --> G[JS 提取正文为块数组<br/>滚动触发懒加载后提取]
    G --> H[Python 侧下载原图<br/>Referer + cookie]
    H --> I[组装 Markdown<br/>图片改相对路径引用]
    I --> J[{标题}.md + {标题}_images/ 落盘]
    B -->|其他| K[skipped]
    C --> L[mp4 落盘]
    D --> L
```

关键设计决策：

- **前置依赖**：本计划在 30 号计划全部任务完成后执行；其 `http_get_json` / `cdp_get_cookies` / `open_tab` / 三分类 / `not_supported` skip reason / ERROR_MESSAGES 扩充均直接复用。若执行时 30 号尚未落地，先完成 30 号再启动本计划。
- **登录门**：zhihu 队列处理前经 CDP 读 `.zhihu.com` cookie 并校验 `z_c0` 存在；缺失时该批知乎链接按 `zhihu_not_logged_in` 失败，错误消息指导"加 `--headed` 重跑、在弹出的 Chrome 窗口登录 zhihu.com"；`--headed` 模式下自动打开 zhihu.com 页面便于直接登录。与 B 站登录门同构，两条链路共用 profile。
- **页面加载**：`open_tab` 泛化（host_filter=zhihu.com）导航到目标 URL 后，轮询 `eval_cdp` 检查正文容器（`.Post-RichTextContainer` / `.RichContent-inner` / `.RichText`）出现，超时 30s 报 `zhihu_extract_failed`（含"可能需要登录"提示）。
- **正文提取（浏览器内 JS，Python 字符串常量内嵌，不新增文件）**：先 `window.scrollTo` 分段滚到页面底部再回顶（每段 wait 约 300ms，触发懒加载），然后递归遍历正文容器 childNodes，输出块数组 JSON：`{"type":"h1|h2|h3|p|blockquote|pre|ul|ol|li|img|figcaption","text":...,"src":...,"items":[...]}`。行内元素映射：`b/strong→**`、`i/em→*`、`code→\``、`a→[text](href)`（站内链接还原 `target` 参数）；`br` 转硬换行。图片块取清晰度最高候选：优先 `data-actualsrc`，其次 `data-original`，再次 `srcset` 最大者，最后 `src`；跳过占位图与头像/图标（限制在正文容器 + figure 内）。
- **图片下载（Python 侧）**：块数组中的图片 URL 按出现顺序去重（同 URL 复用同一本地文件），命名 `image_001.ext` 起（扩展名从 URL 路径后缀推断，无后缀默认 `.jpg`）；请求带 `Referer: https://www.zhihu.com/` + 全量知乎 cookie（新增通用字节下载函数 `http_get_bytes(url, headers)`，与 30 号 `http_get_json` 并列）；落盘 `{output_dir}/{标题}_images/`。
- **图片失败不致命**：单张图片下载失败记入 `images_failed`，Markdown 中该图保留原始 URL 引用（文字正文仍完整交付）；任务记录仍为成功。图片全部失败亦不升级为任务失败。
- **Markdown 组装（Python 侧，零新依赖）**：文件以 `# {标题}` 开头，下方元信息引用块（来源 URL、作者、抓取时间），随后正文；标题取 `document.title` 清洗「 - 知乎」后缀与非法字符（复用 `clean_title`）；`{标题}.md` 经 `unique_path` 防覆盖（冲突自动 `_1` 后缀，md 后缀参数化）。
- **数据模型**：新增 `ExtractRecord`（input_url / article_url / article_id / title / path / images_total / images_failed / error_*），`RunResult` 增 `extracted` 列表；`to_data` 输出新增 `extracted` 数组（与 `downloaded` 并列，旧消费者不受影响），`summary` 增 `extracted` 计数。不复用 `DownloadRecord`（video/bytes 语义不适用，避免字段污染）。
- **article_id**：回答取 `answer/<aid>` 中的 aid，文章取 `/p/<pid>` 中的 pid；URL 无法提取时 `invalid_url` 失败。
- **错误码**：新增 `zhihu_not_logged_in`（无 z_c0）、`zhihu_extract_failed`（页面加载失败/正文容器缺失/JS 提取异常）；复用 `invalid_url`（URL 类型不识别）。图片失败不设错误码（见上）。
- **契约**：`build_schema` 更新（description / summary / constraints 加知乎提取说明 / `side_effects.network` 加 zhihu.com 与 zhimg.com / response item 增 `extracted` 数组定义 / 新错误码进 enum）。
- **版本**：`2.2.0`（30 号完成后）→ `2.3.0`。
- **打包**：无新第三方依赖（JS 提取脚本内嵌字符串常量，Python 侧仅标准库），Nuitka 流程零改动。

## Out of Scope（明确不做）

- 问题页整页多回答（只提取 URL 指向的回答）；
- 想法（`zhihu.com/pin/...`）、收藏夹、评论、赞同/评论数抓取；
- 知乎视频、内嵌第三方卡片（bilibili 卡片等）、外链预览卡——正文中遇卡片降级为链接或不渲染；
- 公式 LaTeX 还原：公式以知乎渲染后的图片形式下载保存（原封不动，不做文本化）；
- 提取结果转 PDF/HTML/飞书文档等其他格式。

## 任务分解

> 前置：30 号计划全部任务完成（`http_get_json` / `cdp_get_cookies` / `open_tab` / 四分类前的三分类骨架 / `not_supported` 就位）。

- [ ] Task 1: 基础设施扩展——通用字节下载 + 知乎 URL 识别
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`
  - 实现：新增 `http_get_bytes(url, headers)`（UA + 自定义头、超时、返回字节串；与 30 号 `http_get_json` 并列）；新增 `is_zhihu_url(url)`（zhihu.com 域判断，含 zhuanlan 子域，模式仿 `is_bilibili_url`）
  - 验证：`uv run douyin_dl.py schema` 输出合法 JSON 且退出码 0（行为不变、可构建）
  - Demo：无用户可见变化，为后续任务供能

- [ ] Task 2: 知乎 Service 函数族 + 四分类接线 + 数据模型
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`
  - 实现：`ZHIHU_EXTRACT_JS` 常量（滚动加载 + 正文块数组提取脚本，返回 JSON 字符串）；`resolve_zhihu_url(url)`（归一化并提取 article_id：answer/<aid> 或 /p/<pid>，失败抛 `invalid_url`）；`check_zhihu_login(port)`（CDP 读 cookie 校验 z_c0）；`extract_zhihu_article(ws_url, url)`（导航 + 等待正文容器 + 执行提取 JS + 标题清洗，返回 (title, blocks, author)）；`download_zhihu_images(blocks, images_dir, cookies)`（去重下载、返回 images_total/images_failed，失败保留原 URL）；`render_zhihu_markdown(...)`（块数组 → Markdown 文本）；`ExtractRecord` dataclass 与 `RunResult.extracted`、`to_data` 扩展；`extract_links` 增加 zhihu 队列；`run_downloads` 暂把 zhihu 队列按 skipped 记录（行为不退化，Task 3 换真实现）
  - 验证：`uv run douyin_dl.py --json "https://www.zhihu.com/question/1923534024288236685/answer/2021258227166319271"` → 该链接进入 skipped；既有抖音链接行为不变
  - Demo：混合文本输入时 JSON 输出分类正确（douyin / bilibili / zhihu / skipped 各归其位）

- [ ] Task 3: 知乎提取编排 + 登录门 + 落盘（核心功能）
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`
  - 实现：`extract_zhihu_one(input_url, ...)`（登录门：无 z_c0 → `zhihu_not_logged_in` 失败并给登录指引，headed 模式自动开 zhihu.com；resolve → open_tab 导航 → 等待渲染 → JS 提取 → 下载图片 → 组装 Markdown → `unique_path` 落盘，返回 `ExtractRecord`）；`run_downloads` 真接入 zhihu 队列（串行、复用 emit 进度、复用同一 Chrome 会话与 profile）；错误码 `zhihu_not_logged_in`、`zhihu_extract_failed`
  - 验证：未登录首跑 → 知乎链接按 `zhihu_not_logged_in` 结构化失败并给出指引；`--headed` 登录知乎后重跑 → `~/Downloads` 出现《…》.md 与同名 `_images/` 目录，正文文字与网页一致、图片为原图且相对引用
  - Demo：命令行提取给定王勃回答链接，文字、图片原封不动落盘

- [ ] Task 4: 契约与文档收尾
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`、`python_projects/douyin_downloader/README.md`
  - 实现：`build_schema` 更新（description / summary / constraints 加"知乎需登录态，无 z_c0 时失败"说明 / `side_effects.network` 加知乎域名 / response 增 `extracted` 数组与 `summary.extracted` / 新错误码进 enum）；版本号 2.3.0；README 增加知乎提取说明、首次登录引导（`--headed` 人工登录一次）、用法示例、已知限制（不做多回答/评论/公式还原）
  - 验证：`uv run douyin_dl.py schema` 输出新契约；`uv run douyin_dl.py "<抖音文案> https://b23.tv/xxx <知乎链接>"` 混合输入三类链接均成功
  - Demo：一条命令混吃抖音 + B 站 + 知乎链接，schema 契约与实现一致

## 记录

- 澄清决策：范围=回答+文章（1=a）、路线=CDP 登录态+DOM 提取（2=a）、输出=Markdown+本地图片（3=a）、CLI=同一命令自动识别（4=a）。
- 匿名直连知乎实测 403（2026-10-02，curl 真实 UA），纯 HTTP 路线否决。
- 本计划依赖 30 号计划产物；若届时 30 号未完成，先执行 30 号。

---
**最后更新：** 2026-10-02
**作者：** AI & User
**版本：** v1.0.0
