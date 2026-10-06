# Plan for: 知乎文章提取进阶——抓取前几页评论

## 问题陈述

当前知乎提取链路（v2.6.0）只产出正文 `article.md` + `images/`，评论区数据完全丢弃。本次进阶：在正文提取完成后，于同一页面继续抓取评论区**前几页一级评论**（含每条下直接可见的回复），结构化落盘到文章目录，供后续 AI 分析使用。

**范围边界**：不逆向 `x-zse-96` 签名、不直连评论 API（`comment_v5` 强制签名头，缺失即 403，实现易碎且与本项目"真实浏览器"架构相悖）；不抓问题页多回答、不动抖音/B 站链路。

## 需求

澄清阶段确认（2026-01-27）：

1. **深度**：默认抓 3 页（约 60 条一级评论），新增 CLI 参数 `--zhihu-comments N` 可调，`0` 为关闭。
2. **楼中楼**：只抓一级评论 + 每条下**直接可见**的回复；不点"查看全部回复"展开；但必须**提示未展开**（记录"另有 N 条回复未展开"）。
3. **产出**：`comments.md`（人读，层级化渲染）+ `comments.json`（结构化，供程序化分析）双落盘；"分析"由 AI 会话基于文件做，exe 不内置分析逻辑。

## 背景

- 架构现状：`douyin_dl.py` 单文件四层（契约 / 基础设施 / Service / CLI），知乎链路 = CDP 登录门（`z_c0`，:1768-1778）→ `open_tab`（navigate=False，:2104）→ `extract_zhihu_article`（导航 + 轮询正文容器 + `ZHIHU_EXTRACT_JS` 滚动取 innerHTML，:2012）→ Python 侧图片下载 / bs4 清洗 / html2text → `article.md`。
- 可复用基础设施：`eval_cdp(ws_url, expression, timeout)`（:633，支持 awaitPromise）、`page_title`、`emit` 进度约定、`unique_dir`、`ExtractRecord`（:1107）。
- 调研结论（2026-01-27 web 调研）：
  - 评论 API 直连需 `x-zse-96` 动态签名（请求路径 + 查询参数 + 时间戳 + `d_c0` 多轮摘要），社区逆向资料（CSDN 145641103、cv-cat/ZhihuApis）均确认缺失即 403 → 排除；
  - 评论区为登录后懒加载：需滚动到评论区位置才挂载；评论项选择器 `.CommentItemV2 .CommentRichText`（site-pattern 2026-05 记录，仍有效）；翻页靠"查看更多评论"按钮，楼中楼靠"查看全部 N 条回复"按钮；
  - 知乎评论区类名存在 css-xxx 随机化风险 → 翻页/展开按钮一律用**文案匹配**定位，评论项选择器准备候选集合。
- 风控红线：知乎对短时高频敏感（历史 40362 事件）；本功能同页翻页点击需间隔（脚本内 sleep），一次一篇不变。

## 方案

浏览器 DOM 路线，与正文提取完全同构，全部动作在一个新的浏览器内脚本 `ZHIHU_COMMENTS_JS` 中完成（`eval_cdp` + awaitPromise，一次执行）：

```
extract_zhihu_one（现有流程不变）
  → 正文提取 + article.md + images/（现状）
  → 若 comment_pages > 0：
      fetch_zhihu_comments(tab_ws_url, comment_pages)
        → ZHIHU_COMMENTS_JS：
            ① 滚动到评论区（评论区懒加载挂载）
            ② 轮询评论项出现（超时则返回 found=false，评论区可能已关闭）
            ③ 读页头总评论数（"N 条评论"）
            ④ 翻页：文案匹配"查看更多评论"按钮点击，等评论数增长，
               至多 pages-1 次或按钮消失提前停；点击间隔 ~1.5s
            ⑤ 遍历评论项：作者/内容/赞数/时间/直接可见回复（同结构）/
               collapsed_reply_count（从"查看全部 N 条回复"文案提数，无则 0）
            ⑥ 返回 JSON 字符串
      → comments.json（ensure_ascii=False, indent=2）
      → comments.md（Python 侧从结构化数据渲染，不走 html2text）
```

- **失败不致命**：评论抓取失败 / 评论区关闭 / `--zhihu-comments 0` → 正文与图片照常产出，`record.comments_error` 记原因（空 = 成功或未开启）；与"单图下载失败不致命"同模式。
- **产物**：`{output_dir}/zhihu/{标题}/` 新增 `comments.md`、`comments.json`，目录结构与唯一化策略不变。
- **契约**：`VERSION` 2.6.0 → 2.7.0；`extracted[]` 记录新增 `comments_total` / `comments_pages` / `comments_error`。
- **数据模型（comments.json 顶层）**：

```json
{
  "fetched_at": "ISO8601",
  "pages_requested": 3,
  "pages_fetched": 3,
  "total_hint": "1234",
  "order": "default",
  "comments": [
    {
      "index": 1,
      "author": "张三",
      "content": "评论全文……",
      "likes": "1.2 万",
      "time": "01-26",
      "replies": [{ "author": "李四", "content": "……", "likes": "12", "time": "01-26" }],
      "collapsed_reply_count": 15
    }
  ]
}
```

（赞数/时间保留知乎原始展示文案；`collapsed_reply_count` 即"未展开回复数"，同时渲染进 md。）

## 任务分解

- [ ] Task 1: 浏览器侧评论抓取脚本与服务函数
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`（知乎 Service 区，:1645-1743 常量区与 :2012 提取函数之后）
  - 实现：新增模块级常量 `ZHIHU_COMMENTS_JS`（async IIFE 返回 Promise[JSON 字符串]，模板占位 `__PAGES__` / `__CLICK_GAP_MS__`，逻辑按方案①-⑥；按钮定位用文案正则候选集合，评论项选择器候选集合，楼中楼容器相对每个评论项查找）；新增 `fetch_zhihu_comments(ws_url, pages) -> dict`：模板替换 → `eval_cdp`（超时给足：3 页翻页 + 渲染约需 30-60s，设 120s）→ `json.loads` 容错 → 返回结构化 dict（found / total_hint / pages_fetched / comments）
  - 验证：`uv run douyin_dl.py --schema` 正常输出（语法完整性）；功能验证集中在 Task 4
  - Demo：尚无可演示行为（脚本已就位，等 Task 3 接线）

- [ ] Task 2: 结构化落盘与 Markdown 渲染
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`
  - 实现：新增 `render_zhihu_comments_markdown(payload: dict) -> str`：`# 评论` 标题 + 元信息块（总评论数 / 实抓页数与条数 / 排序说明 / "回复未完全展开"总说明）+ 逐条渲染（`## N. 作者（赞 X · 时间）` + 内容 + 缩进引用回复 + `> 另有 N 条回复未展开`）；`ExtractRecord` 增 `comments_total: int = 0`、`comments_pages: int = 0`、`comments_error: str = ""` 三字段并同步 `to_json`
  - 验证：`uv run python -c "import ast; ast.parse(open('douyin_dl.py', encoding='utf-8').read())"` 通过
  - Demo：本地用固定 payload 调 `render_zhihu_comments_markdown` 输出样例 md（临时脚本，不入库）

- [ ] Task 3: CLI 参数、编排接线与契约更新
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`、`python_projects/douyin_downloader/README.md`
  - 实现：`build_parser` 增 `--zhihu-comments`（type=int，default=3，help 说明 0=关闭）；`main` → `run_downloads(..., zhihu_comments=...)` → 知乎队列 `extract_zhihu_one(..., comment_pages=zhihu_comments)`；`extract_zhihu_one` 在 `article.md` 落盘后、`record.ok = True` 前调 `fetch_zhihu_comments` 并写 `comments.json` / `comments.md`（任何异常捕获 → `emit` 警告 + `record.comments_error`，不影响 `record.ok`；评论文件缺失时不留半成品——只删评论相关文件，article 目录保留）；`build_schema`：`zhihu_comments` 参数定义、`extract_item` 增三字段、constraints/notes 提评论行为与失败策略、`side_effects.filesystem` 补 comments 文件、`VERSION = "2.7.0"`；`render_text` extracted 成功行增评论计数；README 用法与产物说明同步
  - 验证：`uv run douyin_dl.py --help` 显示新参数；`uv run douyin_dl.py --schema` 为合法 JSON 且含 zhihu_comments 与新字段
  - Demo：`--zhihu-comments 0` 跑一个知乎链接，行为与 v2.6.0 一致（不抓评论、无 comments 文件）

- [ ] Task 4: 端到端实测与选择器校准
  - 文件：`python_projects/douyin_downloader/douyin_dl.py`（仅校准修正，不改结构）
  - 实现：选一个评论数 > 40 的真实知乎回答，`--headed --output-dir $OUT` 实跑：核对 `.CommentItemV2` 候选、翻页按钮文案、楼中楼未展开文案提数、赞数/时间文本格式；有出入则回改常量并复测（一次一篇，遵守频率红线）；检查产物三件套内容合理（评论数 ≈ 页数 × 20、未展开标记生效、json 可被 json.loads）
  - 验证：`--json` 输出中 `extracted[0]` 含 `comments_total >= 40`、`comments_pages == 3`、`comments_error == ""`；产物目录含 article.md / comments.md / comments.json / images/
  - Demo：`comments.md` 人读可读、`comments.json` 结构符合方案中的数据模型

- [ ] Task 5: 重建 exe 与 skill 文档同步（接线收尾）
  - 文件：`python_projects/douyin_downloader/dist/douyin_dl.exe`（构建产物）、`C:\Users\29580\.agents\skills\sh-zhangshihao-douyin-dl\SKILL.md`（skill 基目录下技能文档）
  - 实现：`uv run scripts\build_exe.py` 重建（版本 2.7.0，校验 `douyin_dl.exe --version`）；skill 文档知乎节同步：产物结构加 comments.md/json、`--zhihu-comments` 参数、失败策略、"不提取"清单移除"评论"、版本对应关系补 v2.7.0；实测跑通新 exe 后 `--close-browser` 收尾
  - 验证：`dist\douyin_dl.exe --version` 报 2.7.0；skill 文档与实际行为一致
  - Demo：直接用新 exe 按 skill 用法跑一条知乎链接，评论文件随正文一起产出

## 页脚

- **最后更新**：2026-01-27
- **作者**：AI & User
- **版本**：v1.0（初版，待批准）
