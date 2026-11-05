# Plan: glmquotawatch-gui 主窗横向化 + 横窗布局适配

## 问题陈述

主窗默认 480×760（竖版），监控内容置顶后下方大片留白，观感差（用户反馈"太竖着了"）。改横向默认几何，并让前端布局在横窗下合理铺开。前案 01 只动了前端；本案按用户新反馈扩展到 Go 侧窗口几何。

## 需求（用户反馈，2026-09-25）

- 窗口不再竖长，默认横向
- 内容在横窗下不挤在窄列里（布局随宽度铺开）

## 背景

- 窗口几何唯一出处：`internal/guiapp/app.go` `buildWindow()`（93-100 行）：`Width: 480, Height: 760`，`BackgroundColour` 仍为旧主题蓝黑 `rgb(15,18,25)`
- Wails v3 `WebviewWindowOptions` 支持 `MinWidth` / `MinHeight`（已 go doc 确认）
- `ensureMainWindow` 销毁兜底重建复用 `buildWindow`，改一处即全一致
- 前端现状：Dashboard/History 容器 `max-w-2xl`（672px），横窗下左右留白过大；UsageCard 为纵向单列堆叠

## 方案

- 窗口：`Width 480→920`、`Height 760→560`（约 16:10 横版）；`MinWidth: 720`、`MinHeight: 460`；`BackgroundColour` 改 `NewRGB(9,12,10)`（对齐新主题 `#090c0a`，消除启动闪色）
- Dashboard：容器 `max-w-2xl→max-w-3xl`；窗口卡片改 CSS grid `repeat(auto-fit, minmax(300px,1fr))`——单卡自动占满整行，≥2 卡自动两列（现仅 5h 窗口单卡，二期多窗口后自动受益）
- History：容器 `max-w-2xl→max-w-3xl`，图表 `h-72→h-80`（横窗下图表更宽更高）
- Settings：保持 `max-w-xl` 居中（表单不宜拉宽）

## 任务分解

- [x] Task 1: 主窗几何横向化 完成
  - 文件：`internal/guiapp/app.go`
  - 实现：`buildWindow()` 内 Width/Height 改 920/560，补 MinWidth/MinHeight 720/460，BackgroundColour 改 `application.NewRGB(9, 12, 10)`
  - 验证（备用，默认不跑）：`go build ./...` 零错误
  - Demo：`wails3 build` 后启动即为横版窗口，启动瞬间无旧蓝黑闪屏
- [x] Task 2: 前端横窗布局适配 完成
  - 文件：`frontend/src/pages/Dashboard.vue`、`frontend/src/pages/History.vue`
  - 实现：Dashboard 容器 max-w-3xl + 卡片 auto-fit 网格；History 容器 max-w-3xl + 图表 h-80
  - 验证（备用，默认不跑）：`cd frontend && npm run build` 零错误
  - Demo：横窗下仪表盘内容铺满中栏，多窗口数据时卡片自动两列

依赖关系：Task 2 不依赖 Task 1（可独立构建），但目验需两者合力。

## 实施说明（2026-09-25 执行完毕）

- 两个任务完成；用户要求构建，`wails3 build` 由默认跳过改为实际执行
- Dashboard 卡片网格用任意值 `grid-cols-[repeat(auto-fit,minmax(300px,1fr))]`，单卡占满整行、多卡自动两列

---
**最后更新：** 2026-09-25
**作者：** AI & User
**版本：** v1.1（实施完成）
