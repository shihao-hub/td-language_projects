# Plan：创建 sh-lark-chat-archive skill（聊天区间归档 → HTML → 转发归档 → 撤回）

## 问题陈述

本会话验证过的完整工作流（读飞书聊天区间 → 生成去 AI 味 HTML → 用户批准 → 转发归档 → 撤回原消息）目前散落在临时脚本与会话记忆中，需沉淀为可复用 skill。

## 需求（用户已拍板）

- 触发场景：把聊天内容提取成 HTML 并总结；来源由用户指定
- **读取源三种（2026-09-21 迭代新增话题）**：
  1. 私聊区间（发给我自己的）
  2. 群区间
  3. **会话内话题（thread）**：提取根消息+话题内全部追加内容并总结；话题即范围，无需定区间（区间模式的定区间步骤原样保留）
- **话题模式不做归档与撤回**：话题本身就是沉淀，流程到"读取 → HTML → 总结"为止（用户原话："这种情况话题不需要归档了呀"）
- **归档是区间模式的可选后续，不是固定步骤**：HTML 完全完成并交用户过目后，**由用户确认是否归档**（用户原话："需要完全完成后，让用户确认是否归档"）；确认归档才谈撤回，不归档则流程结束
- 归档方式（若用户确认）：`merge_forward` 合并成一条（1=a）
- 命名与位置：`sh-lark-chat-archive`，sh- 前缀风格（2=b）
- 测试：**简单测试**（2026-09-21 由"不做"升级）——用用户提供的话题消息链接
  `https://applink.feishu.cn/client/message/link/open?token=AmqwpAvvwQzyarCn9ZbAjNU%3D`
  走一遍真实**只读**链路：链接解析 → 定位话题 → mget 展开 → 生成 HTML → 浏览器打开过目；不发消息、不归档、不撤回
- 打包方式：生成逻辑做成 `scripts/build_archive.py` 随 skill 分发（会话中已确认）

## 背景（关键技术事实，已实测）

1. **归档通道（身份能力已实测）**：
   - **用户身份全自动（默认）**：`im +messages-send --as user --file <HTML路径> --chat-id`——把存档 HTML 作为一条文件消息发回原会话，私聊/群通用、零 bot 依赖、零手动操作
   - 群 + bot 在群（可选原生形态）：`lark-cli im messages merge_forward --receive-id-type chat_id` 合并转发回原群；该 API 平台级 bot-only（user token 被拒）
   - 无 bot 且要原生合并形态（末选）：提示用户客户端手动合并转发（本会话 v1 的做法，现降级为兜底）
   - `im messages forward`（user 可用）为逐条转发会刷屏，不入默认路径
2. 撤回：`lark-cli im messages delete --message-id --as user --yes`，仅限自己发的消息、24h 窗口、高危写
3. 会话定位：`im +chat-list --as user --types p2p,group`（p2p 仅 user 身份可见）
4. 读消息/下图命令均已验证（翻页 50/页；下图按 message-id+file-key，temp 缓存按 position 命名可复用）
5. 安装位置：opencode 扫描 `C:\Users\29580\.config\opencode\skills\`（skill-creator 实例证实），sh-plan-driven-development 是该目录到 .agents\skills 的链接个例；新 skill 直接建在 .config\opencode\skills\ 下
6. **话题读取（已验证）**：`im +messages-mget --message-ids <话题根消息>` 自动展开话题全部回复（单批 ≤50 条 om_id，超量分批）；其 `--download-resources` 一次性把消息内图片/文件下到 `./lark-im-resources/`（在工作目录运行即可）——话题模式与区间模式的下图均可优先走此捷径，失败再退回逐张 `+messages-resources-download`

## 方案

```
C:\Users\29580\.config\opencode\skills\sh-lark-chat-archive\
├── SKILL.md                      # 工作流 + 触发词 + 安全门 + 约束（<300 行）
├── scripts\build_archive.py      # 泛化生成器（本会话 build_export.py 参数化重构）
└── references\design-rules.md    # 去 AI 味设计规范 + 编后记/图注写作纪律
```

**职责分离**：脚本管确定性渲染（拉消息/下图/压缩/HTML/lightbox/编辑器），模型管语义（读消息看图、写编后记与图注 JSON、把审批门与高危决策）。

**话题定位（三层递进，均需向用户复述候选并确认后锁定）**：
- **A 首选（链接解析）**，按链接形态分两种（2026-09-21 用真实链接实测）：
  - A1 **网页版消息链接**（飞书网页版 messenger 的 URL，含 oc_/om_ 等 ID）→ 正则提取直接定位，全自动
  - A2 **客户端复制的 applink 链接**（`applink.feishu.cn/client/message/link/open?token=…`）→ **实测不可解析**：落地页仅跳客户端/要求登录（匿名访问无解析 API，token 服务端加密）→ 自动降级 B，并提示用户"给话题里的一个关键词"
- B 关键词搜索：`im +messages-search --query 关键词`（可加 --chat-id 若会话已知；全局搜索结果自带会话信息）→ 从命中识别话题根（mget 验证展开）→ 候选复述（会话名+摘要+楼数）确认；关键词选独特词（数字/专有名词/原句片段）
- C 末选：时间窗内拉消息找 thread 标记列候选

**build_archive.py 接口**（PEP 723）：
- `--chat-id` `--start-position N`（或 `--start-time "2026-09-20 09:13"` 取首个 ≥ 该时间的消息）`--out-dir` `--title`
- `--thread-root om_xxx`：**话题模式**，消息集 = 根消息 + mget 展开的话题回复（与 --start-position 互斥）；图片优先 `mget --download-resources` 批量取
- `--afterword afterword.json`（模型写的总结：[{title, before[], quote?, after[]}]）
- `--captions captions.json`（{position: caption}，模型逐张看图后写）
- 工作目录固定 `%TEMP%\opencode\lark_archive\<chat尾8位>\`，图片缓存按 position 复用
- 质量下限：消息正序、回复锚点还原、图 base64 内嵌（>1600px 压缩）、lightbox（锁滚动+Ctrl 滚轮缩放+拖拽+双击复位）、页内编辑器（删条/删节/改字/保存覆盖）——全部为本会话已验证实现

**SKILL.md 工作流**（七步）：
1. 识别读取源（用户指定）：a) 私聊/群 + 区间起点（**定区间保留**）b) **话题**（用户给根消息链接/消息，或从消息列表的 thread 标记中确认）→ `chat-list` 查 chat_id，歧义则问
2. 拉取与边界确认：区间模式向用户复述"从 X 到 Y 共 N 条、图 M 张"；话题模式复述"该话题共 N 楼、图 M 张"
3. 语义工作（读消息+逐张看图 → 写 afterword.json / captions.json，遵守 design-rules）
4. 生成 HTML（build_archive.py）→ 交用户过目（打开路径）
5. **交付**：HTML 完成交用户过目；**话题模式到此结束**（不归档、不撤回）
6. **可选归档（仅区间模式，用户确认后执行）**：完成后询问是否归档及形态偏好——默认 **HTML 文件以用户身份发回原会话**（全自动）；群+bot 可选 API merge_forward 原生合并消息；无 bot 且要原生形态则提示手动合并转发并等确认；不需要则流程结束
7. **可选撤回（仅在已归档且用户再次确认后）**：列删除清单（N 条 message_id 范围）→ 确认 → 逐条 `delete --yes`（失败记录：非本人消息/超 24h）
   - 全程遵守 AGENTS.md（测试资源清理等）；高危命令 `--yes` 仅在用户批准后出现

## 任务分解

- [x] Task 1: 创建 `SKILL.md`（frontmatter：name/description 触发词含"归档聊天记录/导出飞书聊天成 html/把聊天区间做成网页/转发归档后撤回"等，pushy 风格；正文七步工作流+安全门+命令语法）
  - 文件：`C:\Users\29580\.config\opencode\skills\sh-lark-chat-archive\SKILL.md`
  - 验证：`Select-String` 确认 frontmatter/审批门/merge_forward 分场景路径齐全；行数 <300
  - Demo：新会话说"把昨天到今天的自聊归档成 html"应触发 skill

- [x] Task 2: 创建 `scripts\build_archive.py`（泛化生成器）
  - 文件：同目录 `scripts\build_archive.py`
  - 实现：本会话 build_export.py + inject_captions/inject_editor 合并重构为单文件；新增参数见方案（含 `--thread-root` 话题模式与 `mget --download-resources` 批量下图）；消息快照落盘 `messages.json`（便于重跑与删除阶段取 message_id）
  - 验证：`uv run build_archive.py --help` 正常输出；`py_compile` 通过（3=c 不做功能测试，仅交付物基本健全）
  - Demo：`--help` 即 Demo

- [x] Task 3: 创建 `references\design-rules.md`（去 AI 味规范：禁蓝紫渐变/Inter/卡片阵/居中对称/emoji 图标/空洞文案；纸底噪点/衬线/等宽时间戳/hairline/朱砂批注色/真图全嵌；编后记=主题分组成段+引原话+禁套话；图注=一句话+编号+指向原文关联）
  - 文件：同目录 `references\design-rules.md`
  - 验证：`Select-String` 确认禁用清单与正面规范两节齐全
  - Demo：（规范文档）

- [x] Task 4: AOCI 收尾（仅计划文件本身入索引；skill 在仓库外无 AOCI 债务）
  - 文件：`aoci.code.txt`、`.aoci/baseline.json`
  - 实现：maintain → docs/plans/06 建 Entry → verify/check/guide
  - 验证：三连 aligned
  - Demo：（管理资产）

- [x] Task 5: 简单测试（真实链接，只读链路）
  - 文件：无新文件（产物 HTML 落 skill 工作目录）
  - 实现：用用户给的 applink 链接走真实流程——演示 A2 不可解析 → 降级 B：向用户要话题关键词 → `messages-search` 定位话题根 → mget 展开（--download-resources 下图）→ `build_archive.py --thread-root` 生成 HTML → chrome-devtools 打开人工过目 → **关闭测试页**（AGENTS.md 资源清理）
  - 验证：降级路径顺畅；话题楼数与图数复述正确；HTML 正常渲染；测试页已关闭
  - Demo：话题模式端到端只读链路跑通（含 applink→关键词降级）

## 决策请求

这批计划可以吗？批准后按 Task 1→4 执行（3=c：不做功能测试，仅 Task 2 的 --help 健全性检查）。（已批准，2026-09-21 执行完毕，见下）

## 实施说明（2026-09-21 执行记录）

- **执行顺序调整**：实际按 Task 1→2→3→5→4 执行——Task 5 完成后还要更新本计划文件，若先做 AOCI 收尾会令索引立刻再次 stale；AOCI 契约要求在最终稳定态一次性收尾，故对调。
- **交付物**：`sh-lark-chat-archive`（SKILL.md 73 行 / scripts\build_archive.py / references\design-rules.md），位于 `C:\Users\29580\.config\opencode\skills\`。验证：`--help` 与 `py_compile` 通过；SKILL/规范关键节 Select-String 齐全。
- **测试发现并修复两个真实 bug**：① mget 把 `thread_replies` 嵌套在消息对象里，同一条消息出现多次（stub + 全字段），walk_messages 改为按 message_id 去重、保留字段更全条目；② 话题回复的 `message_position` 恒为 -3（不在主时间线），导致锚点/图片缓存/图注键全部撞车——改用 `thread_message_position`（真实楼层号，根为 -1）排序，非正数 position 一律回退序号兜底。
- **新增能力**：post 富文本内嵌图挂接（content 中 `![Image](img_v3_…)` 标记 → 真图渲染 + 图注，缓存键 `m{pos}e{n}`）；内嵌图与图片消息的图注统一连续编号。
- **图注纪律实测**：无视觉输入的模型按 design-rules 第 4 条不写图注（不脑补）；换视觉模型后逐张看图补齐。此经验已验证纪律可用。
- **测试结论**：applink 实测 200 但落地页无任何消息标识（A2 不可解析成立）→ 降级 B 关键词搜索"学会好理解、好测试、好修改的分层架构"→ 唯一命中群「Hucci写代码」话题根 `om_x100b643e2e2294b4c38b3db9ef81c01`（thread `omt_19d52ec7d78e5b94`）→ 话题共 6 条（根 + 5 楼）、图 2/2 内嵌 → HTML 渲染正常（纸底/衬线/朱砂/图注/编后记/侧栏统计一致）→ 测试页已关闭。话题模式未做归档与撤回（符合需求）。

---
**最后更新：** 2026-09-21
**作者：** AI & User
**版本：** v1.1（执行完毕）
