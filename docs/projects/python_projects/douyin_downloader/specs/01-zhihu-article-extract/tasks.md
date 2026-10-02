# Task List

> 前置：30 号计划（B 站支持）全部任务完成（`http_get_json` / `cdp_get_cookies` / `open_tab` / 三分类骨架 / `not_supported` 就位）。

- [ ] 1. 基础设施扩展：新增通用字节下载函数与知乎域名识别
  - Files: `python_projects/douyin_downloader/douyin_dl.py`
  - 实现细节：新增 `http_get_bytes(url, headers)`（UA + 自定义头、60s 超时、返回 bytes、非 2xx 抛异常；与 30 号 `http_get_json` 并列于基础设施层，不打印进度）；新增 `is_zhihu_url(url)`（去 www 前缀后等于 `zhihu.com` 或以 `.zhihu.com` 结尾，含 zhuanlan 子域，模式仿 `is_bilibili_url`）
  - Verify: `uv run douyin_dl.py schema` 输出合法 JSON 且退出码 0（行为不变、可构建）
  - Ref: FR-1, FR-5

- [ ] 2. 知乎 Service 函数族 + 四分类接线 + 数据模型
  - Files: `python_projects/douyin_downloader/douyin_dl.py`
  - 实现细节：`ZHIHU_EXTRACT_JS` 常量（滚动加载 + 正文块数组提取，图片 URL 绝对化，返回 JSON 字符串）；`resolve_zhihu_url(url)`（answer/<aid> 与 /p/<pid> 提取，失败抛 `invalid_url`）；`check_zhihu_login(port)`（复用 `cdp_get_cookies` 校验 `z_c0`）；`extract_zhihu_article(ws_url, url)`（导航 + 轮询正文容器 30s 超时 + 执行提取 JS + 标题清洗，失败抛 `zhihu_extract_failed`）；`download_zhihu_images(blocks, images_dir, cookie_header)`（去重下载、`images_failed` 计数、失败标记保留原 URL）；`render_zhihu_markdown(...)`（块数组 → Markdown，含元信息引用块）；`ExtractRecord` dataclass 与 `RunResult.extracted`、`to_data` 扩展；`ExtractResult.zhihu` 与 `extract_links` 四分类；`run_downloads` 暂把 zhihu 队列按 skipped 记录（行为不退化，任务 3 换真实现）
  - Verify: `uv run douyin_dl.py --json "https://www.zhihu.com/question/1923534024288236685/answer/2021258227166319271"` → 该链接进入 skipped；既有抖音链接行为不变
  - Ref: FR-1, FR-2, FR-8, AC-1

- [ ] 3. 知乎提取编排 + 登录门 + 落盘（核心功能）
  - Files: `python_projects/douyin_downloader/douyin_dl.py`
  - 实现细节：`extract_zhihu_one(input_url, ...)`（登录门：无 z_c0 → `zhihu_not_logged_in` 失败并 emit 登录指引，headed 模式自动开 zhihu.com；resolve → `open_tab(port, url, host_filter="zhihu.com")` → extract → `download_zhihu_images` 落盘 `{output_dir}/{标题}_images/` → render → `unique_path(output_dir, 标题, ".md")` UTF-8 写入）；`run_downloads` 真接入 zhihu 队列（串行、复用 emit 进度与同一 Chrome 会话）；实测校准设计评审中的未验证假设（图片候选顺序 / 正文容器选择器 / CDN Referer 要求）
  - Verify: 未登录首跑 → 知乎链接按 `zhihu_not_logged_in` 结构化失败并给出指引；`--headed` 登录知乎后重跑 → `~/Downloads` 出现 `{标题}.md` 与 `{标题}_images/`，正文文字与网页一致、图片为原图且相对引用可打开
  - Ref: FR-3, FR-4, FR-5, FR-6, FR-7, AC-2, AC-3, AC-4, AC-5

- [ ] 4. 契约与文档收尾
  - Files: `python_projects/douyin_downloader/douyin_dl.py`、`python_projects/douyin_downloader/README.md`
  - 实现细节：`build_schema` 更新（description/summary/constraints 加知乎提取与登录态说明；`side_effects.network` 加 zhihu.com、zhimg.com；response 增 `extracted` 数组与 `summary.extracted`；新错误码进 enum）；版本号 2.3.0；README 增加知乎提取说明、`--headed` 首次登录引导、用法示例、已知限制（不做多回答/评论/公式还原）
  - Verify: `uv run douyin_dl.py schema` 输出新契约（含 extracted、新错误码、2.3.0）；`uv run douyin_dl.py "<抖音文案> <B站链接> <知乎链接>"` 混合输入三类链接均成功
  - Ref: FR-9, AC-6
