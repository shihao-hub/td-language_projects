# Walkthrough 32: 全仓（父仓与各子仓）逐主题提交与推送

## 任务背景与执行概览

本次针对父仓 `language_projects` 与三个已检出子仓（`go_projects`、`python_projects`、`typescript_projects`）的全部工作区改动，按「一个主题一笔提交、一笔提交一个范围」的纪律拆分为 32 笔提交并全量推送。父仓原有 23 笔本地积压提交（含上一会话的 `b93f0e5`）随本次一并上推。

执行中严格遵守的约束：

- 全程未使用 `git add -A` / `git add .`，一律显式列路径；子模块指针用 `git add --force`；
- `rust_projects`（目录未检出）与 `native_projects`（未注册）全程未触碰，`ignore = all` 使其删除态未进入任何提交；
- `**/plans/**` 文件（含 `.claude/plans/`）一律单独成笔；
- 子模块内改动在子模块提交并推送，父仓只提交指针。

## 提交与推送详情清单

### 1. 子仓 `go_projects`（1 笔）

| 哈希 | 提交信息 | 内容 |
|---|---|---|
| `fc89f1d` | `chore: 忽略 agy 下载到仓根的 ComfyUI 目录` | `.gitignore` 增加 `ComfyUI/` 并补末尾换行 |

推送：`1d4b86b..fc89f1d main -> main`

### 2. 子仓 `python_projects`（3 笔）

| 哈希 | 提交信息 | 内容 |
|---|---|---|
| `320879c` | `zedhub:feat: sessions link 支持精确匹配与三元组查重` | `linking.py` 统一三元组查重并新增 `--exact`、空 title 回填；`api/cli/contract.py` 透传；新增 `SESSIONS.md`；README 与 CLI help 同步语义 |
| `be42037` | `chore: 忽略本地 *.db 数据库文件` | `.gitignore` 增加 `*.db` |
| `ef854ac` | `style: 移除 .gitignore 末尾多余空行` | 修正上一笔遗留的末尾空行 |

推送：`a2734d1..be42037`、`be42037..ef854ac main -> main`

**行为变更提示**：`sessions link` 的查重由「opencode 全局 session_id 去重」改为「全源 `(agent_id, session_id, 目标目录)` 三元组去重」，同会话现在可以在多个工作区目录各挂一份入口（原入口保留）。README 中与此矛盾的旧描述已同步改齐。

### 3. 子仓 `typescript_projects`（1 笔）

| 哈希 | 提交信息 | 内容 |
|---|---|---|
| `6c2f641` | `ai-philosophy-reel:feat: 收录哲学短视频渲染流水线与素材` | 27 个文件：源码 5 项 + 素材 22 项（`assets_2min/*.jpg`、`audio_scenes/*.mp3`、`bgm.aac`、`output_2min_narration.aac`、背景图 3 张）+ 新增 `.gitignore` |

推送：`5d1a024..6c2f641 main -> main`

**体积控制**：项目目录总计 181.73 MB，其中 `output/` 成品 143.31 MB（`plato-cave-full-2min-reel.mp4` 单文件 114.21 MB，超 GitHub 100 MB 上限），已由新增 `.gitignore` 排除；实际入库 8.82 MB 素材 + 源码。

### 4. 父仓 `language_projects`（27 笔）

| # | 哈希 | 提交信息 |
|---|---|---|
| 1 | `7c9d272` | `docs(plans): 新增全仓逐主题提交与推送实施计划` |
| 2 | `a4af1bb` | `docs(repo): 收录 MCP 2026-07-28 相对 2025-11-25 变更清单` |
| 3 | `9c3d1fd` | `docs(repo): 收录 AI CLI 与 MCP 生态一手调研及来源校验报告` |
| 4 | `7d0e0c1` | `docs(repo): 收录本机 Agent CLI 非交互接口实测盘点` |
| 5 | `240b2e9` | `docs(cli-standard): CLI 工具开发标准升级至 v1.1` |
| 6 | `5fe7d40` | `docs(repo): 收录媒体平台当作云盘的可行性调研` |
| 7 | `520b026` | `docs(repo): 收录抖音 AI 哲学短视频创作与商业化调研` |
| 8 | `c63361b` | `docs(plans): 归档 31 号托盘交互计划与验证总结` |
| 9 | `18b1d7c` | `chore(aoci): 同步索引描述与基线指纹` |
| 10 | `b579286` | `docs: 新增 python_projects exe 默认图标约定与资源` |
| 11 | `f1969e4` | `chore(scripts): 新增 Python 双蛇标志源图生成脚本` |
| 12 | `1523c89` | `docs: AGENTS.md 补充 python_projects exe 图标约定` |
| 13 | `820dbda` | `docs(plansql): 添加 plansql 设计说明` |
| 14 | `2c0097c` | `chore(plansql): 添加 Plan/Spec 状态追加流文件` |
| 15 | `9860d7b` | `chore: 新增 CRAP 复杂度检查脚本与 Zed 任务` |
| 16 | `081f2b2` | `chore(agents): 建立 .agents 规则目录骨架` |
| 17 | `060deee` | `chore(scripts): 新增子模块 AGENTS.md 硬链接分发脚本` |
| 18 | `230e9f3` | `chore(claude): 配置 Claude Code 计划目录` |
| 19 | `ddc9117` | `docs(plans): 归档 Claude Code 构建脚本文档统一计划` |
| 20 | `eaca33f` | `docs(plans): 归档 Claude Code zedhub 会话补登计划` |
| 21 | `84982d9` | `chore(scripts): 收录四群群头像生成方案、脚本与成品图` |
| 22 | `9ec908e` | `chore: 忽略 agy 下载到仓根的 ComfyUI 目录` |
| 23 | `3fef73e` | `chore(zed): 收紧文件扫描排除并调整语言服务器白名单` |
| 24 | `cceb598` | `docs(zedhub): 补充会话检索页与 /ui 壳的对接说明` |
| 25 | `01a077c` | `chore(submodule): 更新 go_projects 子模块指针` |
| 26 | `e98c77b` | `chore(submodule): 更新 python_projects 子模块指针` |
| 27 | `b70ccf6` | `chore(submodule): 更新 typescript_projects 子模块指针` |

推送：`5a42650..7c9d272`（含 23 笔积压提交）、`7c9d272..b70ccf6 main -> main`

**顺带修复的既有缺陷**（均属对应主题，未单开无关提交）：

- `.zed/settings.json`：语言服务器列表重排后 `"Lua"` 成了末项却仍带尾逗号，严格 JSON 会解析失败，已移除；
- `.scripts/group_avatars/`：三个生成脚本的输出目录仍指向迁移前的仓根旧路径（`D:\Users\language_projects\group_avatars`），运行会在仓根重建目录污染仓库，已改为脚本自身目录；README 中失效的旧路径链接同步修正；
- `.scripts/calc_crap.py`：补 PEP 723 元数据（依赖 `radon`），`uv run` 可直接执行，不再提示 `pip install`；
- `AGENTS.md`：新增 `### python_projects` 小节，补齐 python exe 默认图标约定（此前只有 go_projects 有）。

## 验证与测试结果

| 范围 | 命令 | 结果 |
|---|---|---|
| go_projects | `git diff --check` | 无空白告警 |
| zedhub | `uv run zedhub sessions link --help` | 输出含 `--exact` 与「Dedupe per (agent, session, target dir)」 |
| zedhub | `uv run zedhub schema` | 契约含 `exact` 字段（`match_mode` 属响应字段，不在输入契约中，符合预期） |
| zedhub | 测试套件 | **未配置测试**（项目无 `tests/` 目录），如实记录，未以「测试通过」表述 |
| ai-philosophy-reel | `bun build scripts/render.ts --target=bun --no-bundle` + `node --check` | 转译与语法检查通过 |
| ai-philosophy-reel | `git check-ignore -v output/plato-cave-full-2min-reel.mp4` | 忽略生效 |
| ai-philosophy-reel | `bun build`（完整打包） | **失败**：`playwright-core` 的可选依赖 `chromium-bidi` 未安装（`node_modules` 由 pnpm 安装）；与本次入库文件无关，未重跑渲染（依赖 NVENC/Chrome/ffmpeg） |
| calc_crap.py | `uv run .scripts/calc_crap.py --help` | PEP 723 生效，自动安装 radon 并输出帮助 |
| group_avatars | `ast.parse` × 4 脚本 | 语法通过，PEP 723 块齐备 |
| 父仓 | `uv run .scripts/build_docs.py build` | `Documentation built in 14.00 seconds`；INFO 级锚点告警集中在 K8S 文档与 `mcp-2026-07-28-delta.md` 的**逐字英文引用**（原文自带的 `#_meta`、`#terminology` 等链接），属引用保真的必然结果，不改写 |
| 四仓 | `git status --short --branch` | 全部 clean，`## main...origin/main` 无 ahead/behind |
| 四仓 | `git ls-remote refs/heads/main` vs 本地 HEAD | 四个仓库全部一致 |
| 父仓 | `git submodule status` | 三个子模块指针无 `+` 前缀，`rust_projects` 保持 `-`（未检出，未触碰） |

空白告警说明：`git diff --check` 在新增文档上报告的行尾空格，均为 Markdown 硬换行（行尾双空格）或归档 Walkthrough 代码块内的原始缩进，非误入的空白，未做改写。

## 遗留事项

### AOCI 认知索引（本次未维护，需另行处理）

- **治理状态**：`aoci check` → `ok=false, exit_code=1, governance_aligned=false, next_action=blocked`，共 **149 findings**：
  - `code_missing` **69**：磁盘上存在但 `aoci.code.txt`（192 条 Entry）中没有 Entry 的对象，含 `docs/plans/28/29/30`、`glmquotawatch-gui` 的 specs/plans、zedhub specs、`.claude/plans/*`、`.scripts/group_avatars/**`、`.zed/tasks.json`、本次新收录的 6 篇 `docs/repo` 文档等；
  - `code_unbaselined` **69**：同一批对象无基线指纹；
  - `code_stale` **10**：已入索引但内容已变，含 `.gitignore`、`.zed/settings.json`、`AGENTS.md`、`CLI 工具开发标准.md`、clictl/sourcecount 使用指南、zedhub specs 三件套与对接协议；
  - `observed_pending` **1**：治理策略要求人工复核的新观察对象 2 个（`group_avatars/test_chrome.py`、`test_script.py`，已被新增 `.gitignore` 排除）。
- **基线时间戳**：`.aoci/baseline.json` 仍为 `2026-09-27T08:56:16Z`；其中 `AGENTS.md` 的指纹（`13690dea…`）与实际（`ef4b8ada…`）不一致。
- **工具限制**：本机 `aoci.exe` 为 `0.1.0-rc14`，本仓布局为 `volumes-v1`；CLI 的 `status --deep`、`index inventory` 报 `This command or compatibility write path cannot modify Volumes v1 formal cognition`。9 个 MCP 工具（`aoci_rules` / `aoci_header` / `aoci_overview` / `aoci_search` / `aoci_get_entries` / `aoci_maintain` / `aoci_update_entry` / `aoci_remove_entry` / `aoci_report`）中，`aoci_maintain` 与 `aoci_update_entry` 的描述明确支持 Volumes v1，**MCP 路径才是本仓的正规维护入口**（本次未执行，因需按批撰写 69+10 条语义并人工审阅）。
- **修复路径**：`aoci_maintain` 取机器候选（默认 20/批）→ Host 依据证据撰写完整 Entry（tag + F/R/A/S）→ `aoci_update_entry` 原子提交 → `remaining` 非零则继续下一批。注意 `aoci.txt` 也未收录 `.claude/`、`.agents/`、`group_avatars` 等新对象。

### 其他

- `plans_status.sql` 目前只登记 28 号计划；31、32 号计划未登记，如需可另跑 `plansql set` 追加。
- `ai-philosophy-reel` 未提交 `package-lock`/`pnpm-lock`（项目内不存在锁文件），依赖版本未固定；`bun install` 时留意 `playwright-core` 的可选依赖。
- `group_avatars/preview.html` 的浏览器渲染效果未做人工确认（需本地打开查看）。
- `rust_projects` 仍处未检出状态；如需恢复用 `.scripts/submodule-toggle.py`。

## 终态验证结果

- 父仓：`## main...origin/main`（无 ahead/behind），工作树 clean，未推送提交 0；HEAD `b70ccf6` 与远端一致；
- `go_projects`：HEAD `fc89f1d`，clean，未推送 0；
- `python_projects`：HEAD `ef854ac`，clean，未推送 0；
- `typescript_projects`：HEAD `6c2f641`，clean，未推送 0；
- 子模块指针：go `fc89f1d`、python `ef854ac`、typescript `6c2f641`，无漂移。
