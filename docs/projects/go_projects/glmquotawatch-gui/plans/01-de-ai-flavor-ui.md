# Plan: glmquotawatch-gui 前端"去 AI 味"重构（终端磷光风）

## 问题陈述

当前界面是典型"AI 深色仪表盘"：zinc 灰系 + sky 蓝强调 + rounded-xl 圆角卡片 + iOS 胶囊开关，干净但千篇一律（参考文档所称"求稳"产物）。目标是参考《7 个神级技巧去 AI 味》，用强约束让界面形成明确的风格主张，仅动前端视觉与文案，功能逻辑零变更。

## 需求（用户决策，2026-09-25）

- 范围：仅前端视觉与文案层（1=a），Go 后端、 bindings、store/api 逻辑不动
- 风格：终端/极客监控风（2=a）——等宽数字字体、硬朗边框、克制的单色高亮
- 依赖：允许轻量引入（3=b）——字体文件随包分发可接受；图标库按风格判断可不引入（终端字符字形更贴题）

## 背景

- 技术栈：Vue 3 + Tailwind CSS 4（@tailwindcss/vite）+ ECharts 5，Wails v3 壳
- 前端文件：`frontend/src/{App.vue,style.css,store.ts,api.ts,main.ts}`、`pages/{Dashboard,History,Settings}.vue`、`components/UsageCard.vue`
- ECharts 配色硬编码在 `History.vue` 的 `option()` 内（sky 线条 + zinc 轴色），需同步切换
- 构建命令：`cd frontend && npm run build`（vue-tsc + vite）；整包 `wails3 build`
- 参考文档落地方法：方法 4（反向提示、拒绝空洞文案）、方法 7（自主配色，色值写死）；"背景禁纯平"以全局扫描线纹理满足

## 方案

设计主张：**CRT 磷光终端监控台**。

自主配色（写死，全面禁用 Tailwind 默认色板）：

| 语义 | 色值 | 用途 |
|---|---|---|
| 背景 bg | `#090c0a` | 全局底色（微绿近黑） |
| 面板 panel | `#0e1310` | 卡片/输入框底 |
| 凹槽 well | `#101812` | 进度条轨道 |
| 边框 edge | `#1e2a22` | 1px 实线，直角 |
| 磷光绿 phos | `#3fe081` | 主强调/健康态/交互 |
| 琥珀 warn | `#e0a832` | 50-79 档/阈值线/DEMO |
| 红 crit | `#e05252` | ≥80 档/错误 |
| 文字 ink | `#c9d4cc` | 主文字（微绿灰白） |
| 次级 dim | `#7f8d85` | 标签/辅助 |
| 弱化 faint | `#55625b` | 占位/最弱 |

- 通过 Tailwind 4 `@theme` 注册为工具类色（`bg-panel`、`border-edge`、`text-phos` 等）
- 背景：`repeating-linear-gradient` 3px 周期扫描线（禁纯平）；滚动条、选区色同步换
- 字体：`@fontsource/jetbrains-mono`（仅 latin 400/700，约 200KB）+ `"Microsoft YaHei"` 中文回退；`.tnum` 保留
- 形状：全部直角（rounded-none）；卡片阴影禁用；UsageCard 加四角短括号标记（伪元素）
- 顶栏：`▮ GLM QUOTAWATCH`（闪烁光标）+ tab 改方括号样式
- 新增 tmux 风格页脚状态栏：MODE / INTERVAL / LAST（上次采样）/ TOKEN 四段，数据全部来自现有 `store.state`
- 开关：iOS 胶囊 → 文本开关 `[ON]`/`[OFF]`（等宽定宽防跳动）
- UsageCard 状态三色映射：emerald→phos、amber→warn、red→crit

文案对照（终端口吻、具体化，拒绝空洞）：

| 旧 | 新 |
|---|---|
| 演示模式 | `DEMO ×60` |
| 立即采样 / 采样中… | `> 采样` / `> 采样中` |
| 正在等待首次采样… | 等待首轮采样——上游还没回话 |
| 本次采样未返回 token 窗口数据 | 上游没吐窗口数据，下轮再看 |
| 距刷新 3时12分 | 3时12分 后重置 |
| 无已告警档位 / 50% 已告警 | 无告警记录 / `[50]` 已告警 |
| 所选时间范围内没有采样数据 | 这段时间没有采样点 |
| 保存 / 清除 | 写入 / 移除 |
| 设置区块标题（API Token 等） | `TOKEN`、`SAMPLER · ALERT`、`SYSTEM` |

拒绝清单（反向提示，执行时逐条对照）：

- 禁 zinc/slate/gray/sky/blue 等 Tailwind 默认色板类
- 禁大圆角（rounded-lg/xl/full，统一直角）
- 禁胶囊开关、禁 emoji 图标、禁纯平背景、禁阴影
- 禁空洞文案（"加载中…"类改有性格的终端口吻，但保留功能可读性）

## 任务分解

- [ ] Task 1: 设计令牌与字体基建 待办
  - 文件：`frontend/package.json`、`frontend/package-lock.json`、`frontend/src/style.css`、`frontend/src/main.ts`
  - 实现：npm 安装 `@fontsource/jetbrains-mono`（main.ts 引 latin-400/700）；style.css 用 `@theme` 注册上表色板、写 body 扫描线背景/字体栈/光标闪烁/角括号工具类，清空旧 zinc 时代样式
  - 验证（备用，默认不跑）：`cd frontend && npm install && npm run build` 零错误
  - Demo：全局底色变墨绿近黑 + 等宽字体 + 扫描线纹理可见
- [ ] Task 2: App.vue 顶栏终端化 + 页脚状态栏 待办
  - 文件：`frontend/src/App.vue`
  - 实现：标题 `▮ GLM QUOTAWATCH` 闪烁光标；DEMO 徽标 `DEMO ×60`；tab 方括号样式；底部新增四段状态栏（MODE/INTERVAL/LAST/TOKEN），Task 1 的令牌类
  - 验证（备用）：`npm run build` 零错误
  - Demo：窗口出现 tmux 式底栏，tab 变方括号高亮
- [ ] Task 3: UsageCard 直角终端卡片 待办
  - 文件：`frontend/src/components/UsageCard.vue`
  - 实现：直角 + 角括号标记；`$` 提示符前缀 + label；百分比大数字 phos/warn/crit 三档；直角进度条 + well 轨道 + 阈值刻度；档位标签 `[50]` 已告警
  - 验证（备用）：`npm run build` 零错误
  - Demo：主仪表卡片完全脱离圆角卡片观感，数字变磷光绿等宽
- [ ] Task 4: Dashboard 横幅/引导/空态/文案 待办
  - 文件：`frontend/src/pages/Dashboard.vue`
  - 实现：DEMO/错误横幅换 warn/crit 色 + 直角；token 引导卡终端化；采样按钮 `> 采样`；采样时间移入页脚（概览行只留套餐徽标 + 按钮）；空态文案按对照表替换
  - 验证（备用）：`npm run build` 零错误
  - Demo：空态与横幅均为终端口吻 + 磷光配色
- [ ] Task 5: History 图表与选择器换肤 待办
  - 文件：`frontend/src/pages/History.vue`
  - 实现：`option()` 内全部硬编码色换新调色板（线 phos、面积渐变同色、阈值线 warn 虚线、轴/分割线/tooltip 用 edge/dim/panel）；select 与 24h/7d 切换方括号化；空态文案替换
  - 验证（备用）：`npm run build` 零错误
  - Demo：曲线变磷光绿，图表与页面浑然一体
- [ ] Task 6: Settings 表单终端化收尾接线 待办
  - 文件：`frontend/src/pages/Settings.vue`
  - 实现：区块标题大写宽字距；输入框直角 + focus 描边 phos；主按钮 `[ 写入 ]` 次按钮 `[ 移除 ]`；胶囊开关改 `[ON]/[OFF]` 文本开关；demo 只读横幅换 warn 色
  - 验证（备用）：`cd frontend && npm run build` 零错误；整包 `wails3 build` 产出 exe
  - Demo：设置页全部控件终端化，与前三页风格统一（接线收尾：所有页面共享同一令牌，无遗留 zinc/sky 类）

依赖关系：Task 2-6 均依赖 Task 1 的令牌与字体；Task 6 为收尾接线任务（全局 grep 确认无残留旧色类）。

---
**最后更新：** 2026-09-25
**作者：** AI & User
**版本：** v1.0
