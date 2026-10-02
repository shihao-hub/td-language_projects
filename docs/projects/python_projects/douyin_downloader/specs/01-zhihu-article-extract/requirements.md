# Requirements Document

## Summary

`douyin_downloader`（CLI 名 `douyin_dl`）在抖音下载、B 站下载（30 号计划）之外，新增知乎回答/专栏文章的提取能力：真实浏览器 + 登录态打开页面，把正文的文字、图片等原封不动提取为 Markdown 文件 + 本地原图目录。与抖音/B 站链接可在同一命令中按域名分流混吃；项目名与命令名不变。本功能依赖 30 号计划（B 站支持）已落地。

## Functional Requirements

- FR-1 **链接识别**：`extract_links` 增加 zhihu 队列，识别 `zhihu.com` 域（含 `www`、`zhuanlan` 子域）链接，按域名四分类（douyin / bilibili / zhihu / skipped）。
- FR-2 **URL 归一化**：从回答链接（`/question/<qid>/answer/<aid>`）提取 `aid`、从专栏文章链接（`/p/<pid>`）提取 `pid` 作为 article_id；两类之外的知乎链接按 `invalid_url` 失败。
- FR-3 **登录门**：知乎链接处理前经 CDP 读 Chrome profile 的 `.zhihu.com` cookie 并校验 `z_c0` 存在；缺失时按 `zhihu_not_logged_in` 结构化失败，错误消息指导 `--headed` 重跑并人工登录；`--headed` 模式下自动打开 zhihu.com 页面。
- FR-4 **页面提取**：复用同一 Chrome 会话打开目标 URL，等待正文容器（`.Post-RichTextContainer` / `.RichContent-inner` / `.RichText`）渲染完成后，浏览器内 JS 先滚动触发懒加载，再把正文 DOM 转为结构化块数组（标题/段落/引用/代码块/列表/图注/图片），行内加粗/斜体/行内代码/链接保留语义。
- FR-5 **图片原图下载**：块数组中的图片 URL 绝对化、去重后逐个下载到 `{标题}_images/` 目录（命名 `image_001.ext` 起），请求携带 `Referer: https://www.zhihu.com/` 与全量知乎 cookie；Markdown 中用相对路径引用。
- FR-6 **图片失败不致命**：单张图片下载失败不影响任务成功，失败图片在 Markdown 中保留原始 URL 引用，失败数记入结果字段 `images_failed`。
- FR-7 **Markdown 组装**：`{标题}.md` 以 `# {标题}` 开头，附来源 URL、作者、抓取时间的元信息引用块；标题清洗「 - 知乎」后缀与非法字符；同名文件自动 `_1` 后缀防覆盖。
- FR-8 **结果记录**：新增 `ExtractRecord` 与 `RunResult.extracted`；JSON 输出新增 `extracted` 数组与 `summary.extracted` 计数，旧字段不变。
- FR-9 **契约同步**：`build_schema` 增加知乎提取描述、新错误码 enum（`zhihu_not_logged_in`、`zhihu_extract_failed`）、`side_effects.network` 加 zhihu.com / zhimg.com；版本号升 2.3.0。

## Non-Functional Requirements

- 无新第三方依赖：JS 提取脚本内嵌为字符串常量，Python 侧仅标准库；Nuitka 打包流程零改动。
- 串行执行、单条失败不中断整批；复用同一 Chrome 实例与 profile（与抖音/B 站链路一致）。
- Markdown 文件与图片均使用 UTF-8；Windows 文件名非法字符清洗与既有 `clean_title` 行为一致。

## Acceptance Criteria

### AC-1 链接分类
WHEN 输入同时含抖音、B 站、知乎（回答与专栏文章各一）、无关链接的文本，THEN JSON 输出的四个队列各归其位（zhihu 链接进入 zhihu 队列处理，无关链接 skipped）。

### AC-2 未登录失败
WHEN 无 `z_c0` 登录态时运行含知乎链接的命令，THEN 该链接按 `zhihu_not_logged_in` 结构化失败，错误消息包含 `--headed` 登录指引，进程不崩溃。

### AC-3 回答提取成功
WHEN 登录态下运行命令提取 https://www.zhihu.com/question/1923534024288236685/answer/2021258227166319271 ，THEN `~/Downloads` 出现 `{标题}.md` 与 `{标题}_images/`；Markdown 中正文文字与网页一致（段落/引用/代码块/列表/加粗斜体保留），图片为原图且相对路径可打开。

### AC-4 专栏文章提取成功
WHEN 登录态下运行命令提取任一 `zhuanlan.zhihu.com/p/<pid>` 链接，THEN 产出同上（md + 本地图片），article_id 为 pid。

### AC-5 图片部分失败
WHEN 提取过程中某张图片下载失败，THEN 任务仍记为成功，`images_failed` 计数正确，Markdown 中该图保留原始 URL 引用。

### AC-6 契约与版本
WHEN 运行 `uv run douyin_dl.py schema`，THEN 输出合法 JSON：含 `extracted` 数组定义、新错误码 enum、`summary.extracted`、版本 2.3.0、side_effects 含知乎域名。

## Out of Scope

- 问题页整页多回答（只提取 URL 指向的回答）；想法（`zhihu.com/pin/`）、收藏夹、评论与赞同数。
- 知乎视频、内嵌第三方卡片、外链预览卡（正文中遇卡片降级为链接或不渲染）。
- 公式 LaTeX 还原（公式以渲染图片形式保存）；提取结果转 PDF/HTML/飞书文档等格式。
