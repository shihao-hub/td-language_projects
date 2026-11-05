# Plan: glmquotawatch-gui 浅色产品化改版（贴近 CC Switch）

## 问题陈述

终端磷光暗色风被用户否决：仍有 AI 味、暗底低对比阅读难受。改版方向以 CC Switch（浅色 + 绿主色 + 圆角卡片 + 状态彩点 + 舒适留白）为基准全面贴近，终端暗色风完全废弃（含扫描线、等宽字体主导、方括号导航、闪烁光标、个性文案）。

## 需求（用户决策，2026-09-25）

- 全面贴近 CC Switch：观感像同一家族的产品
- 终端暗色风完全废弃，不留痕迹（含卸载 JetBrains Mono 字体依赖）
- 承接 02 号计划的横版窗口与自适应布局（保留，不回退）

## 背景

- 现有令牌体系（bg/panel/edge/ink/dim/faint/warn/crit + @theme）**保留令牌名、只换色值**，组件改动面最小；`phos` 更名 `brand`
- CC Switch 视觉语言：白/微绿灰白底、白卡片浅灰边、emerald 绿主色、状态彩点胶囊、系统 UI 字体、信息密度高但留白舒适
- Go 侧仅动 `app.go` 的启动底色（浅色化，消除启动闪黑）

## 方案

浅色调色板（写死）：

| 令牌 | 色值 | 用途 |
|---|---|---|
| bg | `#f6f8f7` | 页面底（微绿灰白） |
| panel | `#ffffff` | 卡片 |
| well | `#eef2f0` | 进度条轨道 / 分段导航底 |
| edge | `#e4e9e6` | 边框 |
| brand | `#10b981` | 填充：进度条/圆点/开关/主按钮 |
| brand-deep | `#059669` | 文字级绿：品牌名/链接/正常态数字 |
| warn | `#d97706` | 50-79 档/演示徽标（文字级） |
| crit | `#dc2626` | ≥80 档/错误 |
| ink | `#1f2937` | 主文字 |
| dim | `#6b7280` | 次级文字 |
| faint | `#9ca3af` | 弱化文字 |

- 字体：回归系统栈 `"Segoe UI", "Microsoft YaHei", system-ui, sans-serif`；`.tnum` 保留做数字等宽
- 形状：卡片 rounded-xl、按钮/输入框 rounded-lg、胶囊/圆点 rounded-full、进度条圆角
- 状态表达：CC Switch 式彩点胶囊（正常态绿点）+ 淡底胶囊标签
- 文案回归朴素专业（"去 AI 味" = 像真实产品，不靠猎奇）：

| 现在（终端风） | 改为 |
|---|---|
| `▮ GLM QUOTAWATCH` | GLM 用量监控（品牌绿加粗） |
| `[仪表盘]` 方括号导航 | 分段胶囊导航（well 底 + 白色活动块） |
| `> 采样` | 立即采样 |
| `DEMO ×60` 徽标 | 演示模式 ×60（琥珀淡底胶囊） |
| 等待首轮采样——上游还没回话 | 正在等待首次采样… |
| 上游没吐窗口数据，下轮再看 | 本次采样未返回窗口数据 |
| 这段时间没有采样点 | 所选时间范围内暂无采样数据 |
| `3时12分 后重置` | 距刷新 3时12分 |
| `[50]` 已告警 | 50% 已告警（琥珀淡底胶囊） |
| `[ 写入 ]` / `[ 移除 ]` | 保存 / 清除 |
| `[ON]/[OFF]` 文本开关 | iOS 胶囊开关（绿色激活） |
| TOKEN / SAMPLER · ALERT / SYSTEM | API Token / 采样与告警 / 系统集成 |

## 任务分解

- [x] Task 1: 基建反转向浅色 完成
  - 文件：`frontend/src/style.css`、`frontend/src/main.ts`、`frontend/package.json`、`frontend/package-lock.json`
  - 实现：npm 卸载 `@fontsource/jetbrains-mono`；main.ts 删字体引入；style.css 全重写——上表令牌、系统字体栈、浅色滚动条/选区，删扫描线/`cursor-blink`/`term-corners`
  - 验证（备用，默认不跑）：`cd frontend && npm install && npm run build` 零错误
  - Demo：全局变白亮浅色底
- [x] Task 2: App.vue 浅色产品化 完成
  - 文件：`frontend/src/App.vue`
  - 实现：品牌绿加粗标题「GLM 用量监控」；分段胶囊导航；演示琥珀胶囊；页脚四段信息保留、浅色化（值用 brand-deep/warn）
  - 验证（备用）：`npm run build` 零错误
  - Demo：顶栏/页脚与 CC Switch 同族的浅色观感
- [x] Task 3: UsageCard 白卡化 完成
  - 文件：`frontend/src/components/UsageCard.vue`
  - 实现：白底 rounded-xl 卡；label 行加状态彩点；百分比大数字用 brand-deep/warn/crit 文字色；圆角进度条 + well 轨道；已告警标签改琥珀淡底胶囊「50% 已告警」；去 `$` 提示符
  - 验证（备用）：`npm run build` 零错误
  - Demo：主卡片与 CC Switch 的供应商卡片同族观感
- [x] Task 4: Dashboard 浅色化与文案回归 完成
  - 文件：`frontend/src/pages/Dashboard.vue`
  - 实现：演示/错误横幅改淡底圆角；token 引导卡白底圆角 + 绿色主按钮；采样按钮绿底白字「立即采样」；空态/横幅文案按对照表替换，去全部 `$`/`>`/`[ ]` 装饰
  - 验证（备用）：`npm run build` 零错误
  - Demo：仪表盘亮堂、信息清爽
- [x] Task 5: History 图表浅色化 完成
  - 文件：`frontend/src/pages/History.vue`
  - 实现：`option()` 配色换浅色系（线 brand、淡绿面积渐变、轴/分割线浅灰、tooltip 白底圆角阴影）；select/分段切换圆角化；空态文案替换
  - 验证（备用）：`npm run build` 零错误
  - Demo：曲线图融入浅色页面
- [x] Task 6: Settings 浅色化收尾接线 + 启动底色 完成
  - 文件：`frontend/src/pages/Settings.vue`、`internal/guiapp/app.go`
  - 实现：卡片白底圆角；输入框圆角浅边；主按钮绿底白字「保存」、次按钮白底「清除」；iOS 胶囊开关回归（brand 激活）；区块标题恢复中文；`app.go` `BackgroundColour` 改 `NewRGB(246, 248, 247)`；grep 确认 `phos|term-corners|cursor-blink|jetbrains` 零残留
  - 验证（备用）：`npm run build` + `go build ./...` 零错误
  - Demo：全部页面浅色统一，无终端风残留（接线收尾）
- [x] Task 7: 构建产出 exe 完成
  - 文件：无（构建任务）
  - 实现：项目根执行 `wails3 build`
  - 验证：构建退出码 0，`bin/glmquotawatch-gui.exe` 时间戳更新
  - Demo：运行 exe 即见 CC Switch 同族浅色界面

依赖关系：Task 2-6 依赖 Task 1 令牌；Task 7 收尾依赖全部。

## 实施说明（2026-09-25 执行完毕）

- 7 个任务全部完成；收尾 grep 确认 `phos`/`term-corners`/`cursor-blink`/jetbrains/暗色十六进制值零残留（`bg-well` 为新浅色令牌，保留令牌名换色值策略生效）
- 外部变更保留：App.vue 的 `notify-error` 事件绑定（用户侧新增）在重写中原样保留
- `wails3 build` 实际执行成功，`bin/glmquotawatch-gui.exe` 14.5MB（较终端版减少约 100KB 字体）
- 工作树注：01/02 轮改动未单独提交，本轮提交将合并包含横向化与自适应布局（同属 UI 改版范围）

---
**最后更新：** 2026-09-25
**作者：** AI & User
**版本：** v1.1（实施完成）
