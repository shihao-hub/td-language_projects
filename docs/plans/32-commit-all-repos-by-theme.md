# 32 - 全仓（父仓与各子仓）逐主题提交与推送

## 目标描述

把父仓 `language_projects` 与三个已检出子仓（`go_projects`、`python_projects`、`typescript_projects`）工作区内的**全部改动**，按「一个主题一笔提交、一笔提交一个范围」的纪律拆干净并推送到 `origin main`。

范围与纪律（依据 `AGENTS.md` 与《sh-monorepo-commit-push》）：

- 父仓自身文件、每个子仓根目录、每个子项目分别成范围，禁止跨范围混提；
- `**/plans/**`、`**/specs/**` 文件一律单独成笔，不与代码/配置混提；
- 子模块内改动在子模块提交并推送，父仓只提交指针（`ignore = all` 须 `git add --force`）；
- 全程禁止 `git add -A` / `git add .`（会把 `rust_projects` 的未检出删除态一并暂存）；
- `rust_projects`（目录未检出）与 `native_projects`（未注册）本次不触碰。

## 需要用户审阅

> [!IMPORTANT]
> 1. **推送范围**：父仓 `main` 已领先 `origin/main` 23 个提交，本次连同全部新拆提交一并推送（用户已确认）。
> 2. **行为变更**：`python_projects/zedhub` 的 `sessions link` 查重语义由「opencode 全局 session_id 去重」改为「全源 `(agent_id, session_id, 目标目录)` 三元组去重」，同会话可在多目录再挂入口；本次一并把 README 中矛盾的旧描述改齐。
> 3. **超大产物不入库**：`typescript_projects/ai-philosophy-reel/output/` 合计 143.31 MB，其中 `plato-cave-full-2min-reel.mp4` 单文件 114.21 MB，超 GitHub 100 MB 上限，push 必被拒；用项目 `.gitignore` 排除。
> 4. **AOCI 不做维护**：本仓 AOCI 治理状态为 `blocked (149 findings)`；CLI 的 `status --deep` / `index inventory` 被 rc14 的 volumes-v1 兼容写路径拒绝，MCP 路径未在本次范围内。本次只提交已改动的 AOCI 文件，遗留另记。

## 待澄清问题

无。范围、归属与排除清单均已与用户确认。

---

## 变更方案

### [子仓: go_projects]

- [x] **变动摘要**：仓根 `.gitignore` 增加 `ComfyUI/` 排除（agy 下载产物落在仓根），并补文件末尾换行。
- [x] **文件范围**：`.gitignore`
- [x] **Commit**：`chore: 忽略 agy 下载到仓根的 ComfyUI 目录`
- [x] **Push**：`git push origin main`

### [子仓: python_projects]

- [x] **批次 1 变动摘要**：`zedhub` 的 `sessions link` 新增 `--exact` 精确目录匹配，查重统一为三元组，空 title 从 Zed 索引回填；补 `SESSIONS.md` 会话模型手册并修正 README 中与代码矛盾的查重描述。
- [x] **批次 1 文件范围**：`zedhub/src/zedhub/api.py`、`zedhub/src/zedhub/cli.py`、`zedhub/src/zedhub/contract.py`、`zedhub/src/zedhub/core/linking.py`、`zedhub/SESSIONS.md`（新增）、`zedhub/README.md`
- [x] **批次 1 Commit**：`zedhub:feat: sessions link 支持精确匹配与三元组查重`
- [x] **批次 2 变动摘要**：仓根 `.gitignore` 增加 `*.db` 排除并补末尾换行。
- [x] **批次 2 文件范围**：`.gitignore`
- [x] **批次 2 Commit**：`chore: 忽略本地 *.db 数据库文件`
- [x] **Push**：`git push origin main`

### [子仓: typescript_projects]

- [x] **变动摘要**：新增 `ai-philosophy-reel` 哲学短视频渲染流水线（Playwright + FFmpeg 直推），收录源码与输入素材；新增项目 `.gitignore` 排除 `node_modules/`、`output/` 成品与音频中间产物。
- [x] **文件范围**：
  - 源码：`ai-philosophy-reel/package.json`、`scripts/render.ts`、`src/main.js`、`index.html`、`generate_2min_scenes.py`
  - 素材：`assets_2min/*.jpg`（8）、`audio_scenes/*.mp3`（8）、`bgm.aac`、`output_2min_narration.aac`、`bg.jpg`、`cave_bg.jpg`、`cave_outside.jpg`
  - 新增：`ai-philosophy-reel/.gitignore`
- [x] **Commit**：`ai-philosophy-reel:feat: 收录哲学短视频渲染流水线与素材`
- [x] **Push**：`git push origin main`

### [父仓: language_projects]

> 顺序约束：先落盘被引用的调研文档，再提交引用它们的《CLI 工具开发标准》，避免中间提交出现死链。

- [x] **批次 1**：`docs(repo): 收录 MCP 2026-07-28 相对 2025-11-25 变更清单`（`docs/repo/mcp-2026-07-28-delta.md`）
- [x] **批次 2**：`docs(repo): 收录 AI CLI 与 MCP 生态一手调研及来源校验报告`（`ai-cli-mcp-research.md`、`ai-cli-mcp-research-verification.md`）
- [x] **批次 3**：`docs(repo): 收录本机 Agent CLI 非交互接口实测盘点`（`ai-cli-mcp-local-agent-cli-survey.md`）
- [x] **批次 4**：`docs(cli-standard): CLI 工具开发标准升级至 v1.1`（`docs/projects/go_projects/CLI 工具开发标准.md`）
- [x] **批次 5**：`docs(repo): 收录媒体平台当作云盘的可行性调研`（`media-storage-abuse-research.md`）
- [x] **批次 6**：`docs(repo): 收录抖音 AI 哲学短视频创作与商业化调研`（`douyin-ai-philosophy-video-creation-research.md`）
- [x] **批次 7**：`docs(plans): 归档 31 号托盘交互计划与验证总结`（`31-glmquotawatch-tray-doubleclick-open-dir.md` + `walkthrough-31-…md`）
- [x] **批次 8**：`chore(aoci): 同步索引描述与基线指纹`（`aoci.code.txt`、`.aoci/baseline.json`）
- [x] **批次 9**：`docs: AGENTS.md 补充 python_projects exe 图标约定`（`AGENTS.md` 新增 `### python_projects` 小节）
- [x] **批次 10**：`docs: 新增 python_projects exe 默认图标约定与资源`（`python exe 默认图标.md`、`docs/assets/projects/python_projects/python-default.ico`）
- [x] **批次 11**：`chore(scripts): 新增 Python 双蛇标志源图生成脚本`（`.scripts/gen_python_logo.py`）
- [x] **批次 12**：`docs(plansql): 添加 plansql 设计说明`（`docs/projects/go_projects/plansql/设计说明.md`）
- [x] **批次 13**：`chore(plansql): 添加 Plan/Spec 状态追加流文件`（`plans_status.sql`）
- [x] **批次 14**：`chore: 新增 CRAP 复杂度检查脚本与 Zed 任务`（`.scripts/calc_crap.py` 补 PEP 723、`.zed/tasks.json`）
- [x] **批次 15**：`chore(agents): 建立 .agents 规则目录骨架`（`.agents/{hooks,rules,skills}/.gitkeep`）
- [x] **批次 16**：`chore(scripts): 新增子模块 AGENTS.md 硬链接分发脚本`（`.scripts/link-submodule-agents.py`）
- [x] **批次 17**：`chore(claude): 配置 Claude Code 计划目录`（`.claude/settings.json`）
- [x] **批次 18**：`docs(plans): 归档 Claude Code 构建脚本文档统一计划`（`.claude/plans/build-uv-run-build-py-prancy-mountain.md`）
- [x] **批次 19**：`docs(plans): 归档 Claude Code zedhub 会话补登计划`（`.claude/plans/staged-inventing-salamander.md`）
- [x] **批次 20**：`chore(scripts): 收录四群群头像生成方案、脚本与成品图`（`.scripts/group_avatars/**`，新增 `.gitignore` 排除 `test_*`/`temp_*`，4 个脚本补 PEP 723，README 修正失效路径）
- [x] **批次 21**：`chore: 忽略 agy 下载到仓根的 ComfyUI 目录`（`.gitignore`，补末尾换行）
- [x] **批次 22**：`chore(zed): 收紧文件扫描排除并调整语言服务器白名单`（`.zed/settings.json`）
- [x] **批次 23**：`docs(zedhub): 补充会话检索页与 /ui 壳的对接说明`（`docs/projects/python_projects/zedhub/zedhub 对接协议.md`）
- [x] **批次 24**：`chore(submodule): 更新 go_projects 子模块指针`（`git add --force go_projects`）
- [x] **批次 25**：`chore(submodule): 更新 python_projects 子模块指针`（`git add --force python_projects`）
- [x] **批次 26**：`chore(submodule): 更新 typescript_projects 子模块指针`（`git add --force typescript_projects`）
- [x] **每笔提交后**：`git push origin main`

**不提交清单**：`rust_projects`、`native_projects`、`.thirdparty/`、`.mkdocs-site/`、各 `node_modules`/`.venv`/`.pytest_cache`、`plansql.exe`、`ai-philosophy-reel/output/`、`group_avatars` 的 `test_*`/`temp_*`、reel 音频中间产物。

## 验证方案

### 自动化测试与命令验证

- [x] `go_projects`：`git diff --check`（仅 .gitignore 变更，无构建需求）。
- [x] `python_projects/zedhub`：`uv run zedhub sessions link --help`（应出现 `--exact`）、`uv run zedhub schema`（契约含 `exact` / `match_mode`）。该模块无测试套件（无 `tests/`），如实记录为「未配置测试」。
- [x] `typescript_projects/ai-philosophy-reel`：`bun build scripts/render.ts --target=bun`（编译检查，输出到临时目录）；`git check-ignore -v output/plato-cave-full-2min-reel.mp4` 确认忽略生效。不重跑渲染（依赖 NVENC/Chrome/ffmpeg）。
- [x] 父仓：`uv run .scripts/build_docs.py build`（MkDocs 构建，验证新增文档与图标资源可渲染）。
- [x] 收尾：四仓分别 `git status --short --branch`（clean、无 ahead）、`git log origin/main..HEAD`（空）、`git submodule status`（三个指针无 `+` 前缀）。

### 人工验证

- [x] 检查 GitHub 远端，确认新提交与子模块引用正常展示（已用 `git ls-remote refs/heads/main` 复核四仓远端 ref 与本地 HEAD 一致）。
- [ ] 打开 `.scripts/group_avatars/preview.html`，确认 8 张成品图未损坏（未执行，留待人工）。

## 遗留事项（本次不做，另行交接）

- **AOCI 治理**：`aoci check` 报 `blocked (149 findings)`（69 missing + 69 unbaselined + 10 stale + 1 observed_pending）；`.aoci/baseline.json` 中 `AGENTS.md` 指纹已过期；CLI 的 deep/inventory 路径被 rc14 的 volumes-v1 兼容限制拒绝，需走 MCP 的 `aoci_maintain` / `aoci_update_entry` 分批撰写语义。
- **plans_status.sql** 目前只登记了 28 号计划，31/32 号未登记（如需可另跑 `plansql set`）。
