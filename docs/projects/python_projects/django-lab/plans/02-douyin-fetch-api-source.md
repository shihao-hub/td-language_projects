# Plan for: "douyinnotify — 抓取数据源修订（抓取失败止血 + 页面内 API 取数）"

## 概述

**问题陈述**：计划 01 的 Task 9 端到端受阻——未登录无头 Chrome 拿到的不是博主作品列表，而是页脚「推荐」链接（随机、每轮不重叠）。后果有二：① 真实更新**永远检出不了**（每轮 7-8 条"新增"全部被判为抖动而抑制）；② 一旦某轮只返回 ≤3 条未见过的随机 id，就会推送一条内容完全无关的**假通知**。定时任务已临时卸载防止空转。

**用户决策**：先 **D**（止血：抓不到就判失败，绝不污染 state、绝不推送），再 **B**（换数据源）。

**需求**（澄清结论）：

- 数据源必须是博主**真实作品列表**，可重复、newest-first，能稳定判定"新视频"
- 不引入需要额外常驻服务（Node/RSSHub）或需要用户长期维护账号 cookie 的第三方依赖
- 抓取异常一律判失败：不写 state、不推送、记 error 日志、退出码 1（沿用既有语义）
- 现有 CLI / MCP / `schema` 契约不变（本修订只动抓取层与其失败语义，不动 `report` / `notifier` / `scheduler` / `detector` 接口）
- 验收以"端到端收到一条真实推送"为准，不以"命令不报错"为准

**背景**（调研实证，2026-09-22，只读探测）：

- **计划 01 的 DOM 路径已证伪**：`[data-e2e="user-post-list"]` 内部是空的 `<ul data-e2e="scroll-list">` + `<div>服务异常，重新刷新拉取数据</div>`；`anchorsOutsideFooter = 0`，即页面里**一条真实作品锚点都没有**。那 8 个 `a[href*="/video/"]` 全部位于 `FOOTER[data-e2e="page-footer"]`，是页脚推荐流。实测两轮抓取交集为 **0/7 与 0/8**，且 15 条 id **全部不在** `state.json` 的 39 条 `seen` 里——`seen` 里的 39 条其实全是历次抓到的随机推荐 id
- **`iesdouyin` 备选源均死**：`/web/api/v2/aweme/post/` 返回 HTTP 200 但 **0 字节**；`/share/user/<sec_uid>` 返回 `jsvmprt` 风控挑战页（与纯 HTTP 走 web 站同款挑战）
- **RSSHub 不采纳**：`lib/routes/douyin/user.ts` 仍在维护，但做法与本项目同源（Playwright 启动浏览器 + 拦截 `/web/aweme/post` 响应），路由标记 `requirePuppeteer: true` / `antiCrawler: true`，失败时抛 `Empty post data. The request may be filtered by WAF.`。自建 RSSHub 需要 Node + Playwright 常驻服务，成本高于收益
- **采纳方案（实证通过）**：保留现有无头 Chrome + 裸 CDP，只把取数方式从"DOM 锚点"换成**页面内 `fetch()` 调 `/aweme/v1/web/aweme/post/`**。关键实证：
  - 页面自身发起的该 XHR，用 CDP `Network.getResponseBody` 取回的 body **恒为 0 字节**（与计划 01 的结论一致，也是当初转向 DOM 的原因）；
  - 但在**同一页面上下文**里用 `Runtime.evaluate`（`awaitPromise: true`）执行 `fetch()` 同一接口，可拿到**完整 JSON**：`{"status_code":0,"max_cursor":1754989206000,"has_more":1,"aweme_list":[...]}`，18 条、newest-first，含 `desc` 与 `create_time`；
  - **连跑 3 轮结果完全一致**（同 18 条、同序，首条为「7 分钟学会使用 Pi，现在最好的 agent（之一）」），彻底消除抖动；
  - **全新 profile（无 ttwid）**下第 1 次尝试（0.6s）返回空体、第 2 次（约 4.4s）即成功 → 重试轮询设计可行，`PAGE_TIMEOUT = 45s` 充裕；
  - 无需 `a_bogus` 签名——请求由页面自身 origin 发出，自带 ttwid 与页面环境
- 顺带收益：`Aweme.created_at` 从"DOM 不可得恒为 None"变为可填 `create_time`；`fetcher` 从"解析不可测"变为"解析纯函数可离线测"

**方案**：

- 分两步落地，对应"先 D 再 B"，各自独立可验收：
  - **D（Task 1）止血**：DOM 提取限定在作品列表容器内（排除页脚推荐）；结果为空（容器缺失/为空/超时）由"静默返回空列表"改为**抛 `FetchError`**；抖动阈值 3 → 10。此步之后工具**不会再撒谎**（宁可不推，不推假的）
  - **B（Task 2）换源**：`fetcher` 改为页面内 API 取数，删除 DOM 提取代码；`created_at` 落地；`seen` 一次性迁移
- 失败语义（D 的核心，B 沿用）：HTTP 非 200 / `status_code != 0` / JSON 解析失败 / 缺 `aweme_list` 键 / `aweme_list` 为空 → 抛 `FetchError`。`checker` 既有行为已满足"失败不破坏 state"，本修订确保**失败能被正确识别**，而不是被误当成"抓到了 8 条作品"
- 模块影响面：`fetcher.py`（重写取数与解析）、`detector.py`（仅阈值常量）、`checker.py`（不改逻辑，仅确保异常语义）、`README.md`（实现要点与已知限制）；`browser.py` / `state.py` / `watchlist.py` / `report.py` / `notifier.py` / `scheduler.py` / `cli.py` 契约不变
- 关键决策与假设（批准门可推翻）：
  1. **不保留 DOM 锚点兜底**：该路径正是假通知来源，"失败"比"猜"更符合无人值守场景
  2. 抖动阈值取 10（而非直接取消）：数据源已可信，但保留一层"异常放大"保护——应对 `seen` 被误删/清空导致的一次性大量"新增"
  3. 切换数据源时**清空该博主的 `seen`**，使首次 API 抓取走既有"首检基线不推送"分支，保证切换零打扰（旧 39 条随机推荐 id 保留无意义，但清空更干净、可解释）
  4. 仍不写测试（沿用计划 01 约定），质量门槛为 `pyright` 0 错误 + 真实端到端验收
  5. `--notify` 的"先原子写 state 再发消息"取舍不变

## 任务分解

> 执行规范说明：按用户约定默认连续执行、不写测试不跑测试；各任务的"验证"为备用信息，涉及"编写测试"的子项跳过并在汇报中说明。

- [x] Task 1（D：止血）: 抓取失败语义硬化 + 阈值调整
  - 文件：`python_projects\douyinnotify\src\douyinnotify\fetcher.py`、`src\douyinnotify\detector.py`、`src\douyinnotify\cli.py`
  - 实现：`_DOM_EXTRACT_EXPRESSION` 的查询根从 `document` 收窄到 `[data-e2e="user-post-list"]`，杜绝页脚推荐混入；`fetch_blogger_videos` 在超时仍未取到任何作品时抛 `FetchError`（新增异常类型，替代当前的“静默返回空列表”）；`MAX_NEWS_PER_CHECK` 由 3 调整为 10 并更新注释（说明理由：数据源可信后该值只作异常放大保护）；**实施期新发现并顺手修复**：`check --json` 在“全部博主抓取失败”时仍输出 `ok:true` 且退出码 0，与文本路径（退出码 1）口径不一致——把 `all_failed` 判定提前，JSON 包络改写为 `ok:false` + `error:"全部博主抓取失败"` 并退出码 1
  - 验证：`uv run pyright` 0 错误；`uv run douyinnotify check --json --no-save` 输出 `ok:false` + 该博主 `error` 非空（而非“抓取到 8 条作品”）；`uv run douyinnotify check` 退出码 1；`state.json` 的 `last_check` 与 `seen` **均不变**
  - Demo：一条“抓取失败”的检查结果 + state 未被污染的对比证据
  - **实施说明（2026-09-22）**：pyright 0 错误；`check --json --no-save` → `{"ok": false, "data": {..."ok": false, "error": "作品列表为空（45s 内未取到任何作品锚点）..."}, "error": "全部博主抓取失败"}`，退出码 1；文本路径同样退出码 1 并打印 `[Hucci写代码] 抓取失败: ...`；`state.json` md5 前后一致（`ba46ef17311ee8ea98a0d5648d14d51`）；日志落 `ERROR 博主 ... 抓取失败: ...`。本步之后工具处于“只会如实报失败、不会撒谎”的中间态（等 Task 2 恢复抓取能力）

- [x] Task 2（B：换源）: 页面内 API 取数替换 DOM 提取
  - 文件：`src\douyinnotify\fetcher.py`、`src\douyinnotify\detector.py`、`python_projects\douyinnotify\README.md`
  - 实现：`fetcher` 改为——导航博主主页（保持）→ 在 `PAGE_TIMEOUT` 内轮询 `Runtime.evaluate`（`awaitPromise: true`, `returnByValue: true`）执行页面内 `fetch('/aweme/v1/web/aweme/post/?...')`；表达式内做 `try/catch` + `JSON.parse` + **字段裁剪**（仅回传 `aweme_id` / `desc` / `create_time`，避免 1.6MB 经 CDP 回传）；Python 侧 `_parse_api_items`（纯函数）把紧凑 JSON 解析为 `list[Aweme]`，`created_at` 填 `create_time`；失败条件按上文"失败语义"抛 `FetchError`（本轮不写 state、不推送、记 error 日志）；删除 `_DOM_EXTRACT_EXPRESSION` / `_VIDEO_HREF_RE` / `_parse_dom_items` 及页脚兜底；`state.json` 一次性清空该博主 `seen`（走首检基线不推送）；README 更新"实现要点"（DOM 锚点 → 页面内 API）、"已知限制"第 2 条（抖动抑制改为异常放大保护、阈值 10）、第 7 条，并删除已失效的"未登录看不到内容"表述
  - 验证：`uv run pyright` 0 错误；`uv run douyinnotify check --json --no-save` 返回 18 条真实作品且**连跑 3 次结果一致**（id 与顺序相同）；`uv run douyinnotify list` 显示 `seen` 已重置为首检基线
  - Demo：`check --json` 输出真实作品 id/标题/`created_at`，三次一致
  - **实施说明（2026-09-22）**：`fetcher.py` 全量重写（新增 `_POST_API_PATH` / `_FETCH_EXPRESSION_TEMPLATE` / `_build_fetch_expression` / `_fetch_app_videos` / `_parse_api_payload`，删除 `_DOM_EXTRACT_EXPRESSION` / `_VIDEO_HREF_RE` / `_extract_dom_videos` / `_parse_dom_items`）；`_fetch_with_connection` 去掉了原本未使用的 `chrome` 形参。实测：`check --json --no-save` 连跑 3 次，均 `fetched_count=18`、id 序列 md5 完全相同（`80101d7f...`），首条为真实新作「7 分钟学会使用 Pi，现在最好的 agent（之一）」，并落日志 `博主 ... 取到 18 条作品`。`seen` 迁移：手动清空该博主 39 条旧 id → 普通 `check` 建立新基线，输出 `[Hucci写代码] 18 条作品，首检基线 18 条（不推送）`，退出码 0，零打扰。pyright 0 错误。**偏差记录**：① `Aweme.created_at` 已填真实 `create_time`，但 `report.render_json` / MCP 输出仍不暴露该字段（计划约定 report 契约不变），仅作 DTO 内部修正；② 顺带修正 `detector.py` 模块 docstring 里已失效的“抽样抖动”描述；③ README 同步修正了三处旧字段/旧行为描述（能力表 `check_interval_minutes` → `check_interval_hours`、快速开始“20 分钟” → “6 小时”、已知限制 2/6/7），并新增限制 8（接口非官方契约）

- [x] Task 3: 端到端验收与交付收尾
  - 文件：`python_projects\douyinnotify\README.md`、（如需）本计划文件回填实施说明
  - 实现：改 `state.json` 模拟新视频（从首检基线中移除 1-2 条 id）→ `uv run douyinnotify check --notify` → 飞书收到真实推送 → 恢复 state 为基线（补跑一次普通 `check` 吸收最新作品，避免残留误报）→ 迁移已完成（`check_interval_hours: 6` + `schedule_start: "09:00"`）→ 重装计划任务 `install_schedule` 并校验
  - 验证：飞书收到含真实视频标题的推送；`schtasks /query /tn douyinnotify_check /v /fo LIST` 显示下次运行时间为 09:00/15:00/21:00/03:00；`schtasks /run /tn douyinnotify_check` 手动触发一次后日志新增一条检查记录且未产生假通知
  - Demo：飞书推送截图/消息 + 日志行 + 计划任务查询结果三项证据
  - **实施说明（2026-09-22）**：全部通过。① 模拟新视频：从基线 18 条中摘掉最新作品 `7681561699970747699` → `check --notify` 真实推送，退出码 0，日志 `飞书通知已发送 message_id=om_x100b641cf79068a0dee8ab74fa112d2`；② 推送后发现并修复一个渲染缺陷：接口 `desc` 含换行（正文 + `#话题`），换行落在 `render_lark` 的 60 字截断窗口内，会把飞书 markdown 列表项截断并把 `#话题` 渲染成一行大标题——修在数据源处（`fetcher` 建 `Aweme.title` 时把 `desc` 压成单行），修后 `--dry-run` 验证消息体为单行；③ `seen` 自愈：摘掉的 id 被下一轮 fetch 全量并入回填（18 条），无需人工恢复；④ 重装计划任务：`已创建计划任务: douyinnotify_check（09:00 起每 6 小时）`，`schtasks /query` 显示下次运行 `2026/9/23 3:00:00`、命令为 `pythonw.exe -m douyinnotify --notify`；⑤ 手动 `schtasks /run` 验证无人值守路径：上次结果 `0`，日志新增 3 行（`取到 18 条作品` / `检出 0 条新视频` / `无新视频，静默不发`），无假通知，且无残留 Chrome / pythonw 进程

---

**最后更新：** 2026-09-22
**作者：** AI & User
**版本：** v1.1.0
