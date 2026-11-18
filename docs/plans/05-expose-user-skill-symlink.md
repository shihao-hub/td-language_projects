Plan for: "新建 expose_user_skill.py，把 sh-user-skills 子技能全量软链暴露到 skills 顶层"

**问题陈述**：`sh-user-skills/<name>/` 下子技能核心文件叫 `README.md`，不会被 Agent 全局递归探测。用户要点名 1-2 个（首批 `sh-plan-driven-development`、`sh-spec-driven-development`）暴露到 `skills/<name>/SKILL.md` 实现自动发现，且附带目录（`references/` 等）不断链。目录级软链接改不了内部文件名，此计划只做文件级混合软链脚本。
**需求**：单文件 uv 脚本 `.agents/skills/expose_user_skill.py`，`uv run` 直接跑，无第三方依赖；头 docstring 与 `--help` 首句强调只做全量软链+改名一件事；用法 `uv run expose_user_skill.py <name> [--check] [--force>`；目录建不出 symlink 回退 `mklink /J`；本机生效，顶层链接目录不入库，用 `.gitkeep` 占位说明指向（用户决策 3=a+占位符）。
**背景**：`sync_skills.py` 已有 junction/复制两种同步范式，本脚本复用其 `is_link/remove_path/make_junction` 思路；源 `sh-user-skills/<name>` 为真身，目标 `skills/<name>` 为真实目录+全链接；`SKILL.md` 相对链到 `../sh-user-skills/<name>/README.md`；子目录用目录链接保证相对引用不断。
**方案**：目标目录真实存在，内容全是链接；`README.md` 改名链出为 `SKILL.md`，其余顶层文件逐个文件 symlink，子目录目录链接；幂等重跑跳过，`--check` 预览，`--force` 重建；`.gitkeep` 占位写明指向源。

**任务分解**：
- [x] Task 1: 新建 expose_user_skill.py 单文件脚本
  - 文件：`.agents/skills/expose_user_skill.py`（新建唯一文件）
  - 实现：argparse 接 `<name> [--check] [--force]`；源=`sh-user-skills/<name>`、目标=`skills/<name>` 写死相对脚本目录，不接受任意路径；建目标真实目录；遍历源顶层条目，`README.md` 链为 `SKILL.md`，其余文件 symlink、子目录 symlink 失败回退 junction；写 `.gitkeep` 占位说明；`--check` 只打印，`--force` 先清重建，已对齐则跳过
  - 验证：跑 `uv run .agents/skills/expose_user_skill.py --help` 首行即约束声明（备用信息，执行期默认不跑）
  - Demo：脚本 `--help` 与 `--check` 能预览将建的链接清单
- [ ] Task 2: 用两个验收技能验证暴露与不断链
  - 文件：`.agents/skills/sh-plan-driven-development/SKILL.md`、`.agents/skills/sh-spec-driven-development/SKILL.md`（链接产物）及各自 `references` 链接
  - 实现：依次跑脚本点名两个技能；确认 `SKILL.md` 可读且与 `../sh-user-skills/<name>/README.md` 同内容；确认 `references/` 可进入且相对引用不断；确认 `.gitkeep` 占位存在；第二遍重跑全跳过
  - 验证：用只读方式打开顶层 `SKILL.md` 前 10 行与真身一致（备用信息，执行期默认不跑）
  - Demo：harness/任一 Agent 可直接点名加载顶层两个 skill

---
**最后更新：** 2026-10-09
**作者：** AI & User
**版本：** v1
