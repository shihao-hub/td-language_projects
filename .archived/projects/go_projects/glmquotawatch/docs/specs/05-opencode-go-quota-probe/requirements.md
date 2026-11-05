# Requirements Document: OpenCode Go 额度探测快速实现

## Summary

`glmquotawatch-gui` 当前专注于智谱 GLM（bigmodel）编码套餐用量监控。随着多 AI 编程平台的日常高频使用，用户需要在一个统一的轻量级工具中快速查看 OpenCode Go 套餐的额度情况。

第一步实施目标为**快速实现核心探测与即时查看**：完成 OpenCode Go 官方用量 API 适配，提供本地 Token 安全存储，在 CLI 增加独立的 `opencode` 命令组，并在 GUI 顶部提供 Provider 切换（GLM / OpenCode Go）及 OpenCode Go 专属仪表盘（展示滑动窗口、周窗口、月窗口的当前百分比、重置时间和健康状态），并支持一键「立即采样」。后台持续轮询告警与历史曲线归并至后续迭代。

OpenCode Go 视图的视觉语言对标 **OpenCode 官方 console**（`opencode.ai/console` 的 Go 用量页，见用户提供截图）：暗色、扁平、等宽字体、1px 直角边、去装饰。该项目在 GitHub 开源，其设计令牌与组件样式可直接作为落地依据（源码坐标见「视觉规范」章节）。**风格作用域与交互对齐原则（已确认）**：OpenCode Provider 视图的交互骨架与 GLM 视图完全一致——导航仅走应用顶栏（视图内不新增导航行）、Provider 切换器常驻顶栏、控制条与采样按钮同位同交互、空状态同结构；暗色 console 语言仅作为**皮肤层**（色彩、等宽排版、细条与状态点形态）作用于内容区。GLM 视图与全局外壳维持既有浅色 Raycast/Linear 语言。

## Functional Requirements

- **FR-1 OpenCode Go 探测客户端**：
  - 调用官方端点 `GET https://opencode.ai/zen/go/v1/usage`，携带请求头 `Authorization: Bearer <API_KEY>`。
  - 解析上游响应的 `usage` 字段，提取 `rolling`（滑动窗口）、`weekly`（周窗口）、`monthly`（月窗口）的 `status`（"ok" 或 "rate-limited"）、`percent`（整数/浮点百分比）以及 `resetsAt`（ISO 8601 重置时间戳）。
  - 支持通过环境变量 `OPENCODE_GO_API_BASE` 覆盖基地址（用于单元测试与本地 Mock）。
- **FR-2 本地凭证持久化（Token 管理）**：
  - `store.Config` 扩展支持 `opencode_token` 字段，持久化于现有 `%APPDATA%\language_projects\glmquotawatch-gui\<dev|prod>\config.json` 中。
  - 保持配置双向兼容：旧配置文件无此字段时解析为空，不影响既有 GLM 配置。
  - 所有展示出口（CLI JSON、GUI 绑定、日志）恒脱敏（`前4…后4`），禁止暴露明文。
  - 支持通过环境变量 `OPENCODE_API_KEY` 作为临时回退源（当本地配置为空时）。
- **FR-3 独立 CLI 命令命名空间（`opencode`）**：
  - 新增顶级子命令 `opencode`，与现有 GLM 命令完全解耦、互不影响。
  - `opencode token set <key>`：设置并保存 OpenCode API Key。
  - `opencode token show`：查看脱敏后的 Key 及配置状态。
  - `opencode token remove`：清除本地保存的 OpenCode Key（幂等）。
  - `opencode status`：立即触发一次探测，stdout 恒输出统一 JSON 信封（包含 3 个窗口的详细用量）。
  - `schema` 导出同步包含 `opencode` 完整子命令契约（无网络 I/O）。
- **FR-4 GUI 导航与 Provider 切换**：
  - 应用顶栏增加常驻 Provider 切换组件（GLM / OpenCode Go），位置与形态在两个 Provider 视图下完全一致，切换时不移位、不隐藏。
  - 切换至 OpenCode Go 时，仪表盘与 GLM 视图同骨架：顶部控制条（左标题、右操作）+ 滑动/周/月 3 个额度窗口；仅皮肤为暗色 console。
  - 每个额度窗口清晰展示细进度条（不使用用量圆环，见视觉规范反模式禁令）、百分比、下次重置倒计时（例如 "3小时25分后"）以及状态指示灯。
  - 控制条右侧配备「立即采样」按钮（与 GLM 控制条同位同交互：刷新图标 + 加载旋转反馈），点击立即发起探测并刷新视图；上次采样时间戳置于按钮左侧弱文本。
  - 若未配置 Token，展示居中引导卡片（与 GLM 未绑定状态同结构），一键跳转到设置页。
  - **OpenCode Go 视图的视觉与交互风格必须逐条满足下文《视觉规范：OpenCode Console 风格》**（含色彩令牌映射、字体与数字排版、扁平结构、额度条范式、动效与响应式以及反模式禁令）。
  - 数字排版硬约束：百分比、倒计时、时间戳、采样计量一律使用等宽字体栈 + `tabular-nums`，保证每秒刷新时字符宽度不跳动（对齐 OpenCode console 的 `font-variant-numeric: tabular-nums` + 等宽 `--font-mono` 实践）。
- **FR-5 GUI 设置页支持 OpenCode Key 维护**：
  - 设置页面增加 OpenCode Go 配置卡片，支持查看脱敏 Token、输入新 Token 保存、清除 Token。
- **FR-6 历史走势页的 Provider 语境一致性**：
  - 历史走势为 GLM 专属数据页；当 Provider 为 OpenCode Go 时，页面展示明确的空状态说明（第一步不记录 OpenCode 历史，历史轨迹属后续迭代），不得继续渲染 GLM 历史曲线造成语境混淆。

## 视觉规范：OpenCode Console 风格（FR-4 落地依据）

### 风格定位

暗色、扁平、等宽、去装饰的**控制台质感**：无卡片堆叠、无重阴影、无渐变装饰，靠 1px 细线、字重与灰阶层次建立结构；一切色彩只承载状态语义（正常 / 告警 / 限流），不做视觉点缀。基准参考为用户提供的 `opencode.ai/console` Go 用量页截图，落地依据为 OpenCode 开源仓库中的设计令牌与组件样式。复刻范围限于**皮肤**（色彩、排版、细条与状态点形态）；信息架构与交互骨架（导航、切换器、控制条、按钮位置、空状态结构）一律与应用既有 GLM 视图对齐，视图内不复制 console 的页签导航与按钮位。

### 参考来源（GitHub 开源，`sst/opencode`，默认分支 `dev`）

| 参考物 | 仓库内路径 | 用途 |
|---|---|---|
| console 应用设计令牌（色彩） | `packages/console/app/src/style/token/color.css` | 亮/暗双主题语义色 |
| console 应用设计令牌（字体/间距） | `packages/console/app/src/style/token/font.css`、`.../space.css` | 字号阶、行高、4px 基数间距、≤8px 圆角 |
| console 按钮范式 | `packages/console/app/src/style/component/button.css` | 扁平按钮、状态聚焦环、小尺寸档 |
| Go 页额度条与图表视觉 | `packages/console/app/src/component/go-plan-chart.css`、`.../limits-graph.css` | 细进度条、虚线网格线、tabular-nums、聚焦轮廓 |
| UI 灰阶与语义色原值 | `packages/ui/src/styles/tokens/colors.css` | `--v2-grey-*`、`--v2-yellow-*` 等 Hex 原值 |
| console workspace 暗色页面骨架 | `packages/console/app/src/routes/black/workspace.css` | 纯黑底、1px `#303030` 描边、顶部柔光渐变 |

> 说明：`opencode.ai/console` 的工作区概览页属线上部署前端（顶栏 `Overview / Logs / Audit / Go / Models / Providers / Controls / Integrations / Settings`、卡片式用量面板），其页面代码**未**随开源仓库发布；因此以**截图定结构、上表令牌定数值**的方式落地，不臆造未公开源码。

### 色彩令牌映射（作用域：`.oc-console` 根容器，不污染全局浅色令牌）

| 语义 | OpenCode console | 本项目 OpenCode 视图取值 |
|---|---|---|
| 页面底 | `--v2-grey-1000` `#242424` | `#242424` |
| 平面 / 卡面 | `--v2-grey-900` `#2e2e2e` | `#2e2e2e` |
| 进度条轨道 | `--v2-grey-800` `#3a3a3a` | `#3a3a3a` |
| 描边（1px） | `--v2-alpha-light-8` `#ffffff14` | `#ffffff14` |
| 主文本 | `--v2-grey-200` `#f2f2f2` | `#f2f2f2` |
| 次文本 | `--v2-grey-500` `#aeaeae` | `#aeaeae` |
| 弱文本 / 轴标 | `--v2-grey-600` `#808080` | `#808080` |
| 正常（填充） | 灰阶填充 | `#aeaeae`（0–59% 低占用一律灰，不用绿色抢眼） |
| 告警（填充/文字） | `--v2-yellow-500` `#f2cf76` | `--v2-yellow-500` `#f2cf76`（≥60% 起提示） |
| 严重（填充/文字） | `--v2-orange-500` `#ffa478` | `--v2-orange-500` `#ffa478`（≥85%） |
| 限流失效 | `--v2-red-600` `#f1484f` | `--v2-red-600` `#f1484f`（`status = rate-limited`） |
| 顶部柔光 | `linear-gradient(180deg, rgba(255,255,255,.16), transparent)` | 同式，铺于视图顶部 |

### 排版与尺度

- 字体：等宽字体栈用于数字、标签、计数与标题（`"Berkeley Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace`）；中文正文与说明句保留现有系统无衬线（`Segoe UI` / `PingFang SC`），避免长中文在等宽下观感发硬。
- 数字：百分比、倒计时、`HH:MM:SS` 时间戳一律 `font-variant-numeric: tabular-nums`，且不得因刷新产生宽度抖动。
- 字号阶：11 / 12 / 13 / 15 / 18 / 24px；正文行高 1.25rem 量级；标题 15px 字重 530，标签 11px 字重 440。
- 间距：4px 基数（4 / 8 / 12 / 16 / 24 / 32 / 48）；圆角仅 3 / 5 / 6px（`--border-radius-sm|md|lg`），严禁胶囊化大圆角。

### 结构范式

1. **顶部导航**：沿用应用顶栏 Tab（仪表盘 / 历史走势 / 偏好配置），OpenCode 视图内**不新增**独立导航行；顶栏选中态样式维持应用既有范式。
2. **Provider 切换器**：常驻应用顶栏右侧（浅色外壳令牌），GLM / OpenCode 两视图下位置、形态与交互完全一致，不随切换移位或隐藏；切换动画 ≤150ms。
3. **内容列**：左对齐、最大宽度约 900px 的单列，模块间距 24–28px；不使用多列瀑布流。
4. **额度条范式（核心）**：每个窗口（滚动 / 周 / 月）为一行——
   - 左侧：窗口名（13px，如「滑动窗口」）+ 其下 11px 弱文本重置时间（`重置 · 3小时25分后`）；
   - 右侧：百分比（13px 等宽数字，右对齐）+ 状态点（4–6px 圆点，仅此处用语义色）+ `rate-limited` 时追加文字标签；
   - 下方：通栏 6px 高细条，轨道 `#3a3a3a`，填充按上表阈值取色，圆角 ≤2px；
   - 卡片底部：`上次采样 HH:MM:SS`（弱文本）与「立即采样」操作同行右对齐。
5. **「立即采样」按钮**：位于内容区顶部控制条右侧（与 GLM「即刻核对用量」同位置、同刷新图标与加载旋转、同按压反馈）；皮肤为扁平描边（`1px solid #ffffff14`、透明或 `#2e2e2e` 平面、文字 `#f2f2f2`），悬停 `background: #2e2e2e`，聚焦 `outline: 2px solid currentColor; outline-offset: 3px`；不使用实心品牌色大按钮。
6. **空状态引导卡**：居中结构（与 GLM 未绑定引导卡一致：图标 + 标题 + 说明 + 按钮），点击跳转设置页并聚焦 OpenCode Token 输入框；皮肤取暗色平面（`#2e2e2e` + 1px 描边、不用 box-shadow）。

### 动效与响应式

- 进度条填充 400–700ms `cubic-bezier(0.22,1,0.36,1)`；采样后百分比与条形同步过渡，不整屏闪烁重排。
- 悬停仅改背景色（120–180ms）；`prefers-reduced-motion: reduce` 时禁用条形与数字动画。
- 窗口窄于约 640px 时额度条三段式布局堆叠（标签行占整行、进度条与数值次行），字号降一档，不出现横向滚动。

### 反模式禁令（不得出现）

- 卡片堆叠 + 重阴影 + 12–16px 大圆角（现有浅色 Raycast 风格的视觉重音不得带入本视图）。
- 用量**圆环 / 仪表盘指针 / 拟物表头**等装饰组件；额度只用细条形表达。
- 彩色滥用：仅状态点、进度条填充与 `rate-limited` 文案可着色，其余一律灰阶。
- 渐变、辉光、投影、图标堆砌与营销风大字标题。
- 强行对齐大字号数字导致标签与数值间出现大段留白；数字列必须等宽且紧凑。

## Non-Functional Requirements

- **NFR-1 隔离性与零破坏**：GLM 的既有 CLI 命令、GUI 仪表盘、采样 daemon、历史存储和 Windows Toast 告警逻辑不受任何破坏。
- **NFR-2 零冗余依赖**：Go 后端完全复用标准库 `net/http` 与 `encoding/json`，不引入任何第三方网络或辅助依赖。
- **NFR-3 严格超时与错误分类**：探测请求强制 10 秒超时；清晰识别并映射网络超时、HTTP 401（密钥失效/未授权）、HTTP 403（未订阅 Go 套餐）及上游 5xx 故障。
- **NFR-4 数据目录强约束**：严格遵循父仓统一规范，所有配置只落盘在 `%APPDATA%\language_projects\glmquotawatch-gui\<dev|prod>\`，严禁在外部目录散落临时文件。

## Acceptance Criteria

### AC-1
WHEN 用户在终端执行 `glmquotawatch-gui.exe opencode token set oc_sk_...` 时，THEN 写入 `config.json` 的 `opencode_token`，且执行 `glmquotawatch-gui.exe opencode token show` 返回 JSON 信封中的 token 为 `前4…后4` 脱敏格式。

### AC-2
WHEN 用户在终端执行 `glmquotawatch-gui.exe opencode status` 且已配置有效 Token，THEN stdout 输出 `{"ok":true,"data":{...}}`，包含 `rolling`、`weekly`、`monthly` 三个窗口各自的 `status`、`percent` 和 `resets_at`。

### AC-3
WHEN 传入无效的 API Key 执行 `opencode status`，THEN 返回 `{"ok":false,"error":{"code":"auth_error","message":"..."}}`，进程退出码为 1。

### AC-4
WHEN 用户在 GUI 界面顶部点击切换到 OpenCode Go，THEN 主界面切换为 OpenCode Go 仪表盘；点击「立即采样」后，各卡片百分比与重置倒计时立即更新为最新探测值。

### AC-5
WHEN 整个功能上线后，THEN 既有 GLM 的 `status`、`token`、Toast 告警和主界面仪表盘保持完全一致，无任何行为回归。

### AC-6
WHEN 切换到 OpenCode Go 视图并静态检查该视图的样式时，THEN 视图底色为 `#242424`、卡面 `#2e2e2e`、描边恒为 1px `#ffffff14`、无任何 box-shadow 阴影，额度条高度为 6px 且圆角不超过 2px，页面不出现圆环类用量组件。

### AC-7
WHEN 用户在 GLM 与 OpenCode Go 之间反复切换 Provider 时，THEN 暗色 console 令牌只作用于 OpenCode 视图（`.oc-console` 根容器），GLM 视图与顶栏/页脚外壳仍是既有浅色 Raycast 令牌与布局，无样式串色或全局 `color-scheme` 翻转。

### AC-8
WHEN 页面每秒刷新倒计时、或用户点击「立即采样」触发数值变化时，THEN 百分比、倒计时与时间戳因 `tabular-nums` + 等宽字体栈而字符宽度稳定不抖动；且在系统开启 `prefers-reduced-motion: reduce` 时，额度条填充与数值过渡动画被禁用。

### AC-9
WHEN 用户在 GLM 与 OpenCode Go 之间来回切换时，THEN 两视图的交互骨架完全一致——导航仅存在于应用顶栏（视图内无第二套导航）、Provider 切换器始终在顶栏原位、控制条与采样按钮位于同一位置、空状态为同一居中结构，任一视图均不出现重复导航或重复切换器。

### AC-10
WHEN Provider 为 OpenCode Go 且用户打开历史走势页时，THEN 页面展示「OpenCode Go 暂未记录历史走势」空状态说明与返回仪表盘的入口，不再渲染 GLM 的窗口历史曲线；WHEN Provider 为 GLM 时，历史曲线保持既有行为零改动。

## Out of Scope

- OpenCode Go 的后台常驻定时轮询采样与 Windows Toast 阈值告警（第一步快速交付只聚焦即时探测，告警放后续迭代）。
- OpenCode Go 采样历史（`samples-*.jsonl`）与 24h/7d 趋势折线图（放后续迭代）。
- 演示模式（Demo mode）下的 OpenCode Go 虚拟回放（仅针对真实网络探测）。
- 将 OpenCode console 的暗色风格推广到 GLM 视图、历史走势页与全局外壳（本次仅 OpenCode Provider 视图内生效），亦不实现整套暗色主题与明暗自动切换。
- 复刻 console 的完整信息架构（Logs / Audit / Providers / Controls / Integrations 等页签）与任何营销型页面视觉。
