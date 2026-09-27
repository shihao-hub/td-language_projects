# 计划：全仓脚本类文件统一迁移 py / ts

**Plan for: "全仓脚本迁移 py/ts（淘汰 ps1/bat/脚本用途的 Go 与 mjs）"**

## 问题陈述

PowerShell 脚本可读性差、坑多（PS5.1 BOM/编码/chcp、`$LASTEXITCODE` 样板噪音、无内联依赖机制），仓内已有自发迁移趋势（`.scripts/` 四个 py 运转良好、typeai 已自行换 `build.py`）。目标：把全仓第一方"脚本类文件"统一迁移到 **uv + Python 单文件（PEP 723）** 与 **typescript_projects 内部 TS（Bun 体系）**，淘汰全部活跃 ps1/bat、脚本用途的 Go（copy_launcher）与 scripts/ 下的 .mjs。归档区（.archived）按用户决策同样迁移（直译复刻、不测试）。

## 需求（用户已拍板）

- **1=b**：`.archived` 归档区 13 个 ps1 也迁——直接复刻代码、不测试；写错了等项目移出归档时再调。
- **2=a**：按项目生态切分语言——父仓 `.scripts/` 与 go/python/rust 项目脚本全迁 **py**；typescript_projects 内（taskmon、tooldeck，含两个 .mjs）迁 **TS**（用户在学 TS，TS 项目即练兵场）。
- **3=b**：`docs-preview.bat` / `docs-serve.bat` **删除**（放弃双击入口）；pythonlauncher 的 Go 练手脚本 `copy_launcher` **迁 py**。
- 交接简报接管：typeai 的 `build.py`（Antigravity 会话产物，工作区未提交）纳入本计划收尾——补 PEP 723 头。

## 背景（调研结论）

- **盘点**：活跃待迁 = 父仓 `.scripts/` 3 ps1 + 2 bat；go_projects 10 个 ps1（clictl×3、agyquota×2、liteconf、quickask、sublimefolders×2、pythonlauncher、sourcecount）+ typeai 已迁未收尾 + glmquotawatch-gui（嵌套子仓 td-go_projects-glmquotawatch-gui）×2 + copy_launcher（Go，143 行交互式）；python_projects 1 个（sql-pg-sqlalchemy/setup/setup.ps1）；typescript_projects 4 ps1 + 2 mjs；`.archived` 13 ps1。rust/native 无脚本。
- **论点验证**：本仓脚本只做四件事（包装外部命令 / 文本 JSON 处理 / HTTP / 文件操作），py 标准库全覆盖；PEP 723 让单文件自带依赖，PS 无对应机制；编码坑（BOM、chcp、管道中文变 ?）在 py 中天然消失。例外已被用户决策覆盖（双击入口放弃、TS 限子仓内部）。
- **已知偏差顺手修正**：clictl `copy_clictl_to_local_bin.ps1` 硬编码旧目录 `~/.local/bin`，现行约定为 `D:\Users\language_projects_bin`（install_tool.py、agyquota install 同款），迁移时统一；README「可用脚本」表 install_tool 行同样写旧目录，一并修正。
- **坑**：新 py 必须 UTF-8 **无 BOM**（uv 不识别带 BOM 的 PEP 723，build_docs.py 已踩过）；`.gitattributes` 全仓 LF 检出。
- **约束**：glmquotawatch-gui 是嵌套子仓（先在其仓提交，再更新 go_projects 二级指针）；typeai 工作区混有其他未提交修改（specs 02 相关 M 文件），提交须精确隔离只提 `build.py`/`README.md`/删除 `build.ps1`；sourcecount 整体未跟踪，改完即止不涉提交。

## 方案

**语言切分矩阵**：

| 脚本归属 | 目标语言 | 运行方式 |
|---|---|---|
| 父仓 `.scripts/` | Python | `uv run .scripts/xxx.py`（PEP 723，无依赖也带头，形式统一） |
| go_projects / python_projects 各项目 | Python | `uv run xxx.py`（项目根或 scripts/ 内，同名换后缀） |
| `.archived` 各项目 | Python | 直译复刻，不运行 |
| typescript_projects 各项目 | TypeScript | 既有 Bun 模式（`bun scripts/xxx.ts`，参照 taskmon/build-exe.ts） |

**统一形态**：py 脚本 = PEP 723 头 + argparse + subprocess + 中文注释，行为/参数/退出码与原 ps1 严格对齐；旧文件直接 git rm，不保留过渡期；历史 plans/specs 存档文档中的 ps1 字样属历史记录不改，只改活文档（README/AGENTS/STRUCTURE/SPEC/使用指南）。

## 任务分解

- [ ] Task 1: 父仓 .scripts 三个 ps1 迁移 Python 并验证
  - 文件：`.scripts/init-submodules.ps1` → `.scripts/init-submodules.py`；`.scripts/submodule-toggle.ps1` → `.scripts/submodule-toggle.py`；`.scripts/check-agy-upstream.ps1` → `.scripts/check-agy-upstream.py`（删原 ps1）
  - 实现：PEP 723 头（check-agy-upstream 用标准库 urllib 调 HTTP，零三方依赖）；argparse 对齐原参数（`-Action/-Name`、`--only-registry/--query`）；submodule-toggle 保留退出码语义（0 成功含幂等跳过 / 1 参数校验 / 2 前置检查 / 3 执行失败）与三项行为契约（不干净整批拒绝、gitlink 缺失自动重建、-Name 必填）；UTF-8 无 BOM；顺手更新 AGENTS.md/README/docs/repo 两篇 Git 文档中的直接引用
  - 验证：`uv run .scripts/init-submodules.py`（幂等输出 OK）；`uv run .scripts/submodule-toggle.py -Action status -Name rust_projects`（只读体检正常）；`uv run .scripts/check-agy-upstream.py --only-registry`（拉到 Registry 版本）
  - Demo：三条命令输出与原 ps1 等价，ps1 删除
- [ ] Task 2: 父仓 bat 垫片删除与脚本约定规则改写
  - 文件：`.scripts/docs-preview.bat`、`.scripts/docs-serve.bat`（删）；`AGENTS.md`、`README.md`
  - 实现：双击入口移除；AGENTS.md「仓库脚本约定」从「Python / PowerShell」改写为「统一 Python（PEP 723 + uv 单文件），禁止新增 ps1/bat」；README 脚本清单表同步（bat 两行删除、ps1 行改 py、install_tool 行旧目录 `~/.local/bin` 修正为 `D:\Users\language_projects_bin`）
  - 验证：父仓跟踪文件 grep `docs-preview.bat|docs-serve.bat` 零残留
  - Demo：AGENTS/README 与实际脚本清单一致
- [ ] Task 3: go_projects 常规构建脚本迁移（7 项目 10 个 ps1）
  - 文件：`clictl/scripts/build.ps1`、`clictl/scripts/copy_clictl_to_local_bin.ps1`、`clictl/scripts/remove_clictl_from_local_bin.ps1`（目标目录统一 `D:\Users\language_projects_bin`）；`agyquota/scripts/build.ps1`（git describe + buildID 逻辑保留）、`agyquota/scripts/install.ps1`；`liteconf/scripts/build.ps1`（--clean/--version）；`quickask/build.ps1`（双产物）；`sublimefolders/scripts/build-tray.ps1`、`sublimefolders/scripts/build-practice.ps1`；`pythonlauncher/build.ps1`；`sourcecount/scripts/build.ps1`（未跟踪，改完即止）——全部同名换 `.py`
  - 实现：统一 PEP 723 + argparse + subprocess 模式；删旧 ps1；各项目 README/STRUCTURE/SPEC 中的构建命令引用同步；go_projects 子仓内逐项目分别 commit（`<project>:refactor: ...`）
  - 验证：各脚本 `uv run ... --help` 通过；真实构建抽查 clictl 与 agyquota（产物 exe 落位、版本注入正确）
  - Demo：`uv run .\scripts\build.py` 构建出 clictl.exe 并显示版本
- [ ] Task 4: copy_launcher（Go→py）迁移与 typeai 收尾
  - 文件：`pythonlauncher/scripts/copy_launcher/`（main.go、SPEC.md、README.md 整目录删除）→ 新建 `pythonlauncher/scripts/copy_launcher.py`；`typeai/build.py`（补 PEP 723 头，不动逻辑）
  - 实现：143 行交互式 Go 直译为 py（`input()` 三选一交互、`shutil.copyfile`、`Path(__file__)` 上溯定位项目根、覆盖确认）；用法说明收敛进脚本头注释（与仓内其他脚本一致）；typeai 仅补头
  - 验证：`uv run scripts/copy_launcher.py`（无参报用法退出码 2）；`uv run build.py --help`（typeai）
  - Demo：copy_launcher.py 用法提示与原 Go 版一致
- [ ] Task 5: glmquotawatch-gui 嵌套子仓构建脚本迁移
  - 文件：`glmquotawatch-gui/scripts/build-dev.ps1` → `build-dev.py`、`build-prod.ps1` → `build-prod.py`
  - 实现：wails3 三步链（npm 前端 → syso 资源 → go build 生产标签）逐段直译，保留 dev/prod 隔离语义（plan 05 行为契约）；在其独立仓 td-go_projects-glmquotawatch-gui 内提交（`refactor: ...`，无项目维度）
  - 验证：`uv run scripts/build-prod.py --help`；真实跑一次 build-prod 构建出 `bin/glmquotawatch-gui.exe`
  - Demo：生产版构建成功输出产物信息
- [ ] Task 6: python_projects setup 脚本迁移
  - 文件：`sql-pg-sqlalchemy/setup/setup.ps1` → `setup/setup.py`
  - 实现：psql 定位（shutil.which + Program Files 扫描）、密码链（PGPASSWORD > pgpass.conf > getpass 提示）、三步 SQL 执行与验收查询；py 下无需 chcp（UTF-8 默认）；python_projects 子仓内提交（`sql-pg-sqlalchemy:refactor: ...`）
  - 验证：`uv run setup/setup.py --help`；（可选，PG 在运行时）真跑一次完整建库
  - Demo：--help 参数与原 ps1 对齐（DbHost/Port/DbUser/DbName）
- [ ] Task 7: typescript_projects 迁移（4 ps1 + 2 mjs → TS）
  - 文件：`taskmon/scripts/proc-children-mem.ps1` → `proc-children-mem.ts`；`tooldeck/scripts/add-utf8-profile.ps1`、`remove-utf8-profile.ps1` → `.ts`；`cli-json-reel/scripts/render.mjs` → `render.ts`；`text-extractor/scripts/load-into-chrome.mjs` → `load-into-chrome.ts`
  - 实现：照 taskmon 既有 Bun 脚本模式（`import ... from 'node:...'`）；proc-children-mem 经 `powershell -NoProfile -Command "Get-CimInstance Win32_Process ... ConvertTo-Json"` 子进程取进程表（系统查询通道，等价调外部命令）后纯 TS 聚合；utf8-profile 用 node:fs 按 begin/end 标记块幂等增删（编码语义对齐原脚本）；mjs→ts 换后缀加类型；typescript_projects 子仓内逐项目提交（`taskmon:refactor: ...` 等）
  - 验证：`bun scripts/proc-children-mem.ts`（真实输出进程内存表）；`bun scripts/add-utf8-profile.ts` 连跑两次（第二次输出已存在）；render/load-into-chrome 至少 --help/dry
  - Demo：bun 跑 proc-children-mem.ts 输出 sublime_text/zed 子进程统计
- [ ] Task 8: .archived 归档区 13 个 ps1 直译复刻（不测试）
  - 文件：`.archived/projects/go_projects/` 下 file-sync、aiquick、file-sync-native、zread-tray、agent-reaper、console-calculator、mcp-cleanup（×3）、exe-launcher（×2）、instancelock（×2）的 13 个 ps1 → 同名 `.py`
  - 实现：逐函数直译 + PEP 723 头；不运行功能验证（用户决策）；仅 `python -m py_compile` 批量语法自检；归档项目内 README 引用不动（冻结）
  - 验证：批量 py_compile 零报错；归档区 ps1 清零
  - Demo：`git status` 显示 13 删 13 增
- [ ] Task 9: 全仓引用清零兜底
  - 文件：各活文档（AGENTS.md、README.md、docs/repo/*.md、各项目 README/STRUCTURE/SPEC/使用指南、package.json scripts 段）
  - 实现：父仓与各子仓跟踪文件 grep `\.ps1|\.bat` 兜底清零；历史 plans/specs 存档与 .thirdparty/node_modules 除外
  - 验证：grep 输出仅剩历史存档与第三方路径
  - Demo：清零报告
- [ ] Task 10: 分仓提交与父仓指针收尾
  - 文件：typescript_projects、python_projects、glmquotawatch-gui、go_projects、父仓
  - 实现：顺序 = 各子仓业务提交（glmquotawatch-gui 先于 go_projects 二级指针）→ 父仓业务提交（.scripts/、.archived/、docs/、AGENTS.md、README.md）→ 父仓指针提交（`git add --force typescript_projects python_projects go_projects` 后单独 commit）；typeai 提交精确隔离（只含 build.py/README.md/build.ps1 删除，不吸入 specs 02 进行中修改）；每仓提交后立即 push
  - 验证：各仓 `git status` 干净；父仓指针与子仓 HEAD 一致；远端推送成功
  - Demo：逐仓 log 清单
- [ ] Task 11: AOCI 认知维护收尾
  - 文件：aoci 认知资产（aoci.txt、.aoci/）
  - 实现：全部对象达最终稳定态后调 `aoci_maintain` 一次（涉及 .scripts/ 3 删 3 增 + bat 2 删 + AGENTS/README 变更）；按返回候选完整提交 `aoci_update_entry`；父仓单独 chore 提交认知资产
  - 验证：maintain 返回 aligned；认知资产提交入库
  - Demo：AOCI 状态对齐报告

## 执行约定

- 默认连续执行全部任务，不写测试不跑测试；各任务"验证"行中的 `--help`/只读 smoke/真实构建属脚本能否运行的基本确认，执行时照做（归档区除外，用户明确免验）。
- 偏差与新发现先更新本计划再改代码。

---

**最后更新：** 2026-09-27
**作者：** AI & User
**版本：** v1.0
