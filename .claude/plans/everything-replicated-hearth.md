# Everything 常驻实例排查收尾：idle_exit 永生漏洞修复 + 排障笔记沉淀

## Context

10-10 16:45:49 一个无参数的 Everything.exe（PID 28856）由 explorer 拉起后驻留 8.6 小时，直到 10-11 01:24 会话重登才随旧会话消失。本会话已完成取证：自动机制穷尽排除（Run 键 / 计划任务自启动 / 右键集成 / Nilesoft 菜单 / Win+R / Win+E 接管 / 崩溃恢复），收敛结论为「经 shell 的手动/半手动启动（Win+S 或开始菜单），用完即忘」。驻留的根因是技能 `sh-everything-search` 的 `idle_exit.ps1:40` 保护条件（实例启动时间 > 最后技能活动 → 视为手动实例，永不清理）**没有时效上限**，导致被遗忘的手动实例永生。用户已确认：修复漏洞 + 沉淀排障笔记。

## 改动 1：idle_exit.ps1 给手动保护加时效上限

文件：`.agents/skills/sh-user-skills/sh-everything-search/scripts/idle_exit.ps1`（td-agents-skills 子模块）

- 顶部参数区（`$idleMinutes` 旁，约 22 行）新增 `$protectHours = 2`：手动实例保护仅在其「年龄」小于该值时生效。
- 第 39-41 行保护判定改为：`StartTime > lastUse` **且** 实例运行时长 `< $protectHours` 才退出（保护）；超龄实例继续走 `es.exe -exit` 流程。
- 头部注释（7-13 行退出条件清单）第 12-13 行同步更新，说明保护有时效。
- 第 46 行日志追加区分标记：保护过期的实例记录 `(protect expired)` 后缀，便于下次排障。
- 计划任务无需重新注册（任务只是定时跑脚本）。

不修 `es_query.ps1` 竞态（启动→写时间戳 ~20s 窗口）：该窗口被 idle_exit.ps1:32 的「es 进程在飞即退出」天然覆盖，残余风险极低，仅在笔记中记录。

## 改动 2：沉淀 kb-engineering-notes 第 46 号笔记

新文件：`.agents/skills/kb-engineering-notes/46-Windows进程启动来源取证与Everything闲置退出保护永生实例漏洞排障指南.md`（编号自包含，接续现有 45 号；格式参照 `SKILL-DRAFT.md` 与现有条目）

内容提纲：
- 现象与完整时间线（03:25 idle_exit 退出记录 → 04:00 最后技能活动 → 16:45 explorer 拉起 → 01:24 User32 7001 会话重登终止实例）
- 取证手段清单与各自结论：注册表 Run 键、计划任务式自启动、`context_menu_type` 右键集成、Nilesoft Shell 配置、Win+R RunMRU、Win+E 接管（1.4.1 不支持，1.5 才有）、事件日志（Application 1000 崩溃 / System 7001 登录）、`last_use.txt` + `idle_exit.log` 交叉验证
- 关键教训：UserAssist `{CEBFF5CD}` 键已被清空 → shell 启动取证能力缺失；Prefetch 需管理员权限
- 结论模式：explorer 父进程 + 无参数 ≠ 直接证据「手动」，只有排除法收敛价值
- 漏洞与修复：idle_exit 保护永生实例 + 修复方案；es_query 竞态盲区说明

## 改动 3：README 同步

检查 `sh-everything-search/README.md`：若有描述 idle 行为/保护策略的段落，同步补充「手动实例保护 2 小时上限」；无则跳过。

## 验证

1. 语法：PowerShell `Parser::ParseFile` 解析 idle_exit.ps1，零报错。
2. 运行烟测：手动触发一次脚本（当前无桌面实例，应走第 29 行静默 exit 0，验证可执行）。
3. 边界逻辑：内联表达式验证 2.1h（应退出）/ 1.9h（应保护）两分支布尔结果。
4. 自然验证（不阻塞）：下次技能使用后 15 分钟观察 `idle_exit.log` 正常退出记录照旧。

## Git 提交（按仓库规范执行）

- 子模块 td-agents-skills 两笔：
  - `fix(everything-search): 闲置退出保护加时效上限防永生实例`
  - `docs(kb): 新增进程启动来源取证排障笔记`
  - 子模块内 `git commit` + `git push`（子模块改动必须子模块内推送）
- 父仓一笔：`git add --force .agents/skills` 更新指针 → `chore: 更新 skills 子模块指针` + push

### 未决问题与阻塞确认清单
- [ ] 保护上限默认 **2 小时**（无窗口 + 闲置 15min + 运行 >2h 才杀手动实例）是否接受？可选 24h 或其他值
- [ ] `idle_exit.log` 对过期实例追加 `(protect expired)` 后缀（改变日志行格式）是否接受？
- [ ] 子模块与父仓的 push 按上述计划执行，是否同意？
