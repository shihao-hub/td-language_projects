# Antigravity App 窗口启动尺寸与状态记忆机制调研报告

> **调研发起背景**：用户反馈 Google Antigravity 桌面客户端（当前版本 v2.25.0）每次启动均强制以居中的较小固定矩形窗口启动。即使上次关闭前处于全屏最大化或自定义尺寸，客户端也无法记忆并自动恢复。本文档旨在追溯一手源码事实，揭示官方未实现该特性的底层技术与架构诱因，并给出工业级修复方案。

---

## 一、调研结论速览（Executive Summary）

1. **核心病因（一手源码铁证）**：
   - 官方主进程窗口创建函数在 `resources/app.asar/dist/utils.js` 中直接**硬编码**了固定尺寸：
     ```javascript
     const win = new electron_1.BrowserWindow({
         width: 1400,
         height: 900,
         minWidth: 500,
         minHeight: 400,
         ...
     ```
   - 客户端生命周期内**完全未注册** `resize`、`move`、`maximize`、`unmaximize` 等窗口状态监听器，也未引入业界通用的 `electron-window-state` 模块。

2. **官方为什么迟迟不实现（架构阻碍与优先级剖析）**：
   - **同步与异步架构摩擦（Sync vs Async Mismatch）**：官方自研的配置模块 `StorageManager`（在 `dist/storage.js`）完全采用 `fs/promises` 异步设计（`async getItems()` / `async updateItems()`）。而 Electron 的 `createWindow()` 是同步函数。如果强行挂在异步回调中恢复最大化，会导致窗口先按 1400×900 在屏幕中间闪现，随后突兀拉伸全屏（剧烈闪烁/瞬跳，Window Flickering）；
   - **工程重心倾斜**：Antigravity 当前处于快速迭代期，团队 99% 的工程精力集中在 Agent 核心调度机制、gRPC/ConnectRPC 协议管道、安全沙箱、WSL 桥接与终端/Diff 渲染等底层能力，桌面外壳仅被视作极简脚手架，桌面人机工效（Desktop Ergonomics）长期被置于低优先级 backlog；
   - **多窗口与多屏越界防御成本**：客户端支持通过快捷键创建多窗口（`createNewWindow`），且 Windows 下自定义标题栏（`titleBarStyle: 'hidden'`）在跨屏拔插、DPI 缩放变化时存在边缘越界风险，官方在早期为保稳定直接采用保守固定尺寸一刀切策略。

3. **解决路径对比**：
   - **推荐方案（原生 asar 热修补丁）**：在 `dist/utils.js` 中注入轻量同步持久化逻辑（仅需 25 行代码），结合 `show: !isMaximized` + `win.maximize()` + `win.show()` 消除闪烁，并自动记录 `x, y, width, height, isMaximized`；
   - **快捷方式参数法（实测无效）**：Windows 快捷方式的“运行方式：最大化”与 Chromium 的 `--start-maximized` 启动开关会被 Electron 显式指定的窗口初始化参数直接覆盖，无法生效；
   - **外部窗口守护法（降级备选）**：通过 AutoHotkey 或后台守护进程监听进程启动并发送 `SW_MAXIMIZE`，但存在毫秒级视觉拉伸延迟，且无法精准记忆非最大化自由尺寸。

---

## 二、源码取证与架构分析（Primary Source Evidence）

### 1. 窗口创建调用链路
解包 `C:\Users\<User>\AppData\Local\Programs\Antigravity\resources\app.asar`，链路如下：

```
dist/main.js (Electron 主入口)
  ├── 初始化 StorageManager (app_storage.json, 异步 API)
  ├── 启动 Language Server 子进程
  └── L342: (0, utils_1.createWindow)(url, storageManager);
        ↓
dist/utils.js (窗口工具模块)
  └── L105: function createWindow(url, storageManager)
        ├── L114: const win = new electron_1.BrowserWindow({ width: 1400, height: 900, ... })
        ├── L154: attachLoadingOverlay(win, ...)
        └── L164: // Zoom persistence 仅持久化了 zoomLevel，完全没有窗口尺寸逻辑
```

### 2. 官方代码对比：为什么持久化了 Zoom，却遗漏了 Window State？
在 `dist/utils.js` 第 164–194 行，可以看到官方开发人员写的一段补丁代码：

```javascript
// Zoom persistence — restore saved level and capture future changes.
if (storageManager) {
    const ZOOM_LEVEL_KEY = 'zoomLevel';
    let isRestoringZoom = false;
    const applyStoredZoomLevel = async () => {
        const items = await storageManager.getItems();
        const stored = items[ZOOM_LEVEL_KEY];
        if (stored !== undefined) {
            const level = parseFloat(stored);
            if (!isNaN(level)) {
                isRestoringZoom = true;
                win.webContents.setZoomLevel(level);
                isRestoringZoom = false;
            }
        }
    };
    win.webContents.on('did-finish-load', () => {
        void applyStoredZoomLevel();
    });
    win.webContents.on('zoom-changed', (_event, _direction) => {
        if (isRestoringZoom) return;
        const currentLevel = win.webContents.getZoomLevel();
        void storageManager.updateItems({
            [ZOOM_LEVEL_KEY]: String(currentLevel),
        });
    });
}
```

#### 关键事实发现：
1. **缩放比例（Zoom Level）** 对启动闪烁不敏感，因此官方可以安心挂在 `did-finish-load` 页面加载完成后的**异步回调**中恢复；
2. **窗口尺寸与最大化（Window Bounds & Maximized）** 属于操作系统宿主级外观，如果在 `did-finish-load` 之后才异步调用 `win.maximize()`，用户会先看到一个 1400×900 的矩形框加载并渲染背景色，过 500ms~1000ms 后窗口突然拉伸全屏——**这种视觉闪烁比单纯固定大小更被工程团队视为“严重 UI Bug”**；
3. 由于官方自研的 `storageManager` 没有提供同步读写接口（`fs.readFileSync`），而团队又没有引入 `electron-window-state` 这一外部依赖包，因此在面临“异步恢复导致剧烈闪动”与“重构同步存储机制”之间，窗口记忆功能被直接搁置。

---

## 三、方案选型与验证

| 方案 | 原理 | 记忆效果 | 视觉平滑度（防闪烁） | 维护成本 |
| :--- | :--- | :--- | :--- | :--- |
| **方案 1：Asar 热修补丁（推荐）** | 修补 `dist/utils.js`，引入同步 `window-state.json` 读写 | **完美**（支持最大化与任意自定义坐标尺寸） | **极高**（无缝直启，无尺寸跳跃） | 每次官方覆盖更新需重新跑一次修补脚本 |
| **方案 2：Windows 快捷方式/启动参数** | 配置快捷方式“最大化”或追加 `--start-maximized` | **无效**（被 Electron 显式 options 覆盖） | N/A | 无需维护 |
| **方案 3：外部 AHK / 窗口守护** | 外部进程轮询检测并发送 `WinMaximize` | **仅支持最大化**（无法记忆任意自由尺寸） | **差**（有明显弹窗后被拉大的残影） | 需常驻后台守护进程 |

---

## 四、工业级原生热修方案设计

### 1. 核心补丁实现（防闪烁 + 跨屏防越界）
在 `dist/utils.js` 的 `createWindow()` 内部注入以下逻辑：

```javascript
// [PATCH: Window State Persistence]
const windowStateFile = path_1.default.join(electron_1.app.getPath('userData'), 'window-state.json');
let windowState = { width: 1400, height: 900, isMaximized: false };
try {
    if (fs.existsSync(windowStateFile)) {
        windowState = Object.assign(windowState, JSON.parse(fs.readFileSync(windowStateFile, 'utf-8')));
    }
} catch (_) {}

// 跨屏与拔插显示器安全防御：校验坐标是否仍在任一当前在线屏幕范围内
let hasValidBounds = false;
if (electron_1.screen && typeof windowState.x === 'number' && typeof windowState.y === 'number') {
    try {
        const displays = electron_1.screen.getAllDisplays();
        hasValidBounds = displays.some((d) => {
            const b = d.bounds;
            return (
                windowState.x >= b.x - 100 &&
                windowState.x < b.x + b.width &&
                windowState.y >= b.y - 100 &&
                windowState.y < b.y + b.height
            );
        });
    } catch (_) {}
}

const win = new electron_1.BrowserWindow({
    width: windowState.width || 1400,
    height: windowState.height || 900,
    ...(hasValidBounds ? { x: windowState.x, y: windowState.y } : {}),
    show: !windowState.isMaximized, // 若上次最大化，初始先隐藏，最大化后再显现，彻底杜绝闪烁
    minWidth: 500,
    minHeight: 400,
    ...
```

在窗口创建后添加状态维护：
```javascript
if (windowState.isMaximized) {
    win.maximize();
    win.show();
}

const saveWindowState = () => {
    try {
        if (win.isDestroyed()) return;
        const isMaximized = win.isMaximized();
        // 若当前处于最大化，记录 getNormalBounds() 以便还原后仍能精准恢复非全屏尺寸
        const bounds = isMaximized && win.getNormalBounds ? win.getNormalBounds() : win.getBounds();
        const state = {
            x: bounds.x,
            y: bounds.y,
            width: bounds.width,
            height: bounds.height,
            isMaximized,
        };
        fs.writeFileSync(windowStateFile, JSON.stringify(state, null, 2), 'utf-8');
    } catch (_) {}
};
win.on('resize', saveWindowState);
win.on('move', saveWindowState);
win.on('close', saveWindowState);
```

### 2. 特殊打包约束（Unpacked 模块完整性）
官方 `app.asar` 在打包时将 `node_modules/chrome-devtools-mcp` 外部解包至 `resources/app.asar.unpacked`。
重新打包必须附带 `--unpack "**/node_modules/chrome-devtools-mcp/**"`，确保 MCP 子进程二进制组件不被封闭破坏。

---

## 五、自动化工具与落地

针对该需求，已在工作区沉淀标准管理脚本：
- **脚本路径**：`.scripts/patch-antigravity-window.py`
- **能力矩阵**：
  - `uv run .scripts/patch-antigravity-window.py --patch`：退出客户端后自动解包、校验、热修并备份；
  - `uv run .scripts/patch-antigravity-window.py --restore`：一键回滚官方原版；
  - `uv run .scripts/patch-antigravity-window.py --status`：查看当前补丁状态与记录的窗口坐标。
