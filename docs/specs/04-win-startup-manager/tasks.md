# Tasks: Windows 开机自启可视化管理工具 (WinStartupManager)

- [ ] 1. 项目基础脚手架与构建体系搭建
  - Files:
    - go_projects/winstartupmanager/go.mod
    - go_projects/winstartupmanager/build.py
    - go_projects/winstartupmanager/scripts/render_icon.py
    - go_projects/winstartupmanager/internal/env/env.go
    - go_projects/winstartupmanager/internal/store/store.go
  - 实现细节：配置 Go 1.23+ 模块、uv build.py 统一构建脚本（支持 dev/release 判定与 syso 图标注入）、icon 渲染流水线、%APPDATA% 规范路径隔离与单例 ID 管理。
  - Verify: go build ./...
  - Ref: AC-1, NFR-1

- [ ] 2. 核心注册表引擎与 StartupApproved 契约实现
  - Files:
    - go_projects/winstartupmanager/internal/model/model.go
    - go_projects/winstartupmanager/internal/engine/registry.go
    - go_projects/winstartupmanager/internal/engine/startup_approved.go
    - go_projects/winstartupmanager/internal/engine/cmdline.go
    - go_projects/winstartupmanager/internal/engine/signature.go
    - go_projects/winstartupmanager/internal/engine/backup.go
    - go_projects/winstartupmanager/internal/engine/system.go
  - 实现细节：基于 golang.org/x/sys/windows/registry 实现 4 个注册表物理位置扫描；对齐任务管理器 StartupApproved\Run 12 字节二进制位翻转；命令行安全拆解；文件存在性探测；发布者签名/版本信息提取；预删除自动生成 .reg 备份到 %LOCALAPPDATA%\WinStartupManager\backups\；资源管理器与注册表编辑器精准定位；管理员权限探测与一键提权重启。
  - Verify: go test -v ./internal/engine/...
  - Ref: FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, AC-1, AC-2, AC-4

- [ ] 3. 辅助只读看板引擎（启动文件夹与计划任务）
  - Files:
    - go_projects/winstartupmanager/internal/engine/folders.go
    - go_projects/winstartupmanager/internal/engine/tasks.go
  - 实现细节：只读扫描当前用户与公共用户 Startup 目录（解析快捷方式目标路径与状态）；通过 Task Scheduler Win32 COM / PowerShell 接口只读获取开机/登录触发的任务列表。
  - Verify: go test -v ./internal/engine/...
  - Ref: FR-8

- [ ] 4. Wails v3 组装层与低内存生命周期重构
  - Files:
    - go_projects/winstartupmanager/main.go
    - go_projects/winstartupmanager/internal/guiapp/app.go
    - go_projects/winstartupmanager/internal/guiapp/tray.go
    - go_projects/winstartupmanager/internal/guiapp/bindings.go
  - 实现细节：落地手记 071 治理方案。Chromium 参数剪枝；DisableQuitOnLastWindowClosed: true；WindowClosing 钩子放行销毁原生窗口与 WebView2，置空引用并异步触发 runtime.GC 与 debug.FreeOSMemory；系统托盘双击按需重建；支持 --hidden 开机静默启动零 Chromium 实例；导出 Wails Bindings 服务。
  - Verify: go build .
  - Ref: NFR-1, AC-3

- [ ] 5. 前端现代化界面开发 (Vue 3 + Vite + TailwindCSS)
  - Files:
    - go_projects/winstartupmanager/frontend/package.json
    - go_projects/winstartupmanager/frontend/vite.config.ts
    - go_projects/winstartupmanager/frontend/tailwind.config.js
    - go_projects/winstartupmanager/frontend/src/App.vue
    - go_projects/winstartupmanager/frontend/src/components/*
  - 实现细节：现代浅色科技风格、圆角卡片、高信息密度表格。注册表自启项 Switch 无损启停、添加/编辑弹窗、删除二次确认与备份提示、无效残留项警示；搜索与筛选（按来源、状态、有效性）；系统定位（文件管理器、注册表编辑器）；整仓备份与恢复；启动文件夹与计划任务只读看板；非管理员运行时 HKLM 提权提示与一键重启按钮。
  - Verify: npm run build
  - Ref: FR-1 ~ FR-8, AC-1 ~ AC-4

- [ ] 6. 整合构建、打包验证与端到端测试
  - Files:
    - go_projects/winstartupmanager/build.py
  - 实现细节：使用 uv run build.py --dev 完整构建前端与 Go 产物，验证生成 winstartupmanager-dev.exe；校验静态资产嵌入与二进制运行表现。
  - Verify: uv run build.py --dev
  - Ref: AC-1, AC-2, AC-3, AC-4