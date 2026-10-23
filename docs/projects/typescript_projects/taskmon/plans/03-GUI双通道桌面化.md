# 03 · taskmon GUI 双通道桌面化（TS 复刻 go-wails 契约）

> 状态：**进行中**（2026-10-23 起草）
> 创建：2026-10-23 · 项目：`typescript_projects/taskmon`

## 背景与目标

taskmon 目前是 TS + Bun 的单文件控制台 TUI（`release/taskmon-v*.exe`）。用户要求参照
`sh-go-wails-desktop` 的双通道架构做桌面化，但技术栈必须留在 TypeScript：

- **`taskmon-cli`**：现有控制台 TUI，行为不变；
- **`taskmon-gui`**：桌面窗口 + 托盘常驻，关闭窗口只销毁窗口、进程留托盘，双击托盘重建；
- 两者共用同一采集核心与同一个 HTTP Handler；GUI 的窗口页面就是 `serve` 托管的 WebUI。

## 选型

| go-wails 契约 | taskmon（TS）实现 |
|---|---|
| `-gui` / `-cli` 双产物 | Electron 45 打包 GUI；Bun `--compile` 产出 CLI 单文件 |
| 托盘、单实例、关窗销毁、双击重建 | Electron `Tray` / `requestSingleInstanceLock` / 窗口 `destroy` / 托盘点击重建 |
| GUI 与 `serve` 共用 Handler | `node:http` 实现 `internal/server`，Electron 与 CLI `serve` 都调用 `createServer()` |
| 窗口几何记忆 | `window.json`（`<dataDir>/window.json`），resize/move 防抖 + 关闭前同步保存 |
| 无控制台排障 | GUI 产物本身无控制台；日志沿用 pino 落盘（`<dataDir>/logs/taskmon.log`） |
| dev/release 五维隔离 | 产物名、版本注入、数据目录 `dev`/`prod`、单实例 ID、图标 |
| 自启门禁 | 仅 release 允许 `app.setLoginItemSettings`；dev 菜单项置灰 |

**Electron 体积代价**：GUI 目录约 200 MB（Electron runtime），换取托盘/窗口生命周期完全可控。
Edge `--app` 方案（知识库 088）体积小但无法感知窗口关闭、托盘需额外原生 sidecar，不满足
「与 go-wails 对齐」，仅作为 Electron 不可用时的降级预案。

## 目录改造

```text
src/
  core/       tasklist.ts cim.ts grouping.ts proctree.ts kill.ts sysmem.ts format.ts types.ts
  core/sampler.ts   单例采样器：tasklist 主频 + CIM 低频，供 TUI 与 HTTP 共用
  server/    server.ts（node:http handler）+ api.ts
  cli/       main.ts render.ts singleton.ts（现有 TUI 入口，新增 serve 子命令）
  shared/    paths.ts channel.ts version.ts logger.ts
  web/       assets.ts（导出 index.html / app.js / app.css 字符串，Bun 与 Electron 共用）
electron/
  main.ts    BrowserWindow + Tray + 单实例 + 窗口几何 + 自启门禁
  tsconfig.json
scripts/
  build-exe.ts       扩展 --gui / --all，CLI 仍为 Bun compile
  build-gui.ts       electron-builder 封装
```

## 任务分解

- [ ] T1 抽 `core/` 与 `sampler.ts`，现有 vitest 全绿，CLI TUI 行为不变
- [ ] T2 实现 `server/`：`GET /api/snapshot`、`POST /api/kill`、`GET /api/health`、`/` 托管 WebUI
- [ ] T3 CLI 新增 `serve --port`，与 GUI 共用 Handler，根路径返回完整工作台
- [ ] T4 Electron 主进程：托盘菜单（打开面板 / 开机自启 / 退出）、单实例、窗口几何、日志
- [ ] T5 WebUI 工作台：分组/树切换、展开折叠、搜索、kill 二次确认、2s 轮询
- [ ] T6 构建与隔离：`build-exe.ts --gui|--all`、electron-builder 目录版、图标、版本注入
- [ ] T7 验收：双产物子系统、托盘重建、窗口记忆、dev/release 并存、`serve` 根路径 200

## 验收清单

| 验证项 | 操作 | 预期 |
|---|---|---|
| GUI 无黑框 | 双击 `taskmon-gui.exe` | 无 CMD 窗口；托盘出现 |
| 关窗常驻 | 关闭窗口 | 进程仍在，托盘图标保留 |
| 托盘重建 | 双击托盘 | 窗口按上次几何恢复 |
| CLI 回显 | `taskmon-cli.exe --version` | 秒退，prompt 正常 |
| GUI 忽略 CLI 参数 | `taskmon-gui.exe --once` | 只开窗口，无控制台输出 |
| 同一 Handler | `taskmon-cli.exe serve` | 根路径完整工作台，`/api/snapshot` 正常 |
| 通道隔离 | dev 与 release 同开 | 各自数据目录、互不唤醒 |
| 窗口记忆 | 移动/缩放 → 关窗 → 托盘重开 | 几何一致；最大化不污染还原尺寸 |
| 自启门禁 | dev 勾选自启 | 菜单置灰，注册表无写入 |
| 日志 | release 启动 5s | `<dataDir>/logs/taskmon.log` 有启动横幅 |

## 未决问题

- [ ] Electron 目录约 200 MB，是否接受（默认接受；不接受则退回 Edge `--app` 降级方案）
- [ ] GUI 是否需要开机自启（默认实现，仅 release 可用）
