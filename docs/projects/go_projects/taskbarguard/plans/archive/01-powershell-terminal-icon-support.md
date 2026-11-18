# TaskbarGuard 新增 PowerShell / Windows Terminal 图标守卫实施计划

## 一、需求背景
解决 Windows Terminal (`wt.exe`) / PowerShell 在 Windows 任务栏上默认扁平灰底窗口图标与整体暗黑黑曜石/钛金属质感任务栏风格不一致的痛点，提供统一的 Squircle 圆角方块质感图标并实现自动守卫恢复。

## 二、架构设计与实施步骤
1. **视觉资产与多尺寸图标库 (`scripts/powershell/`)**：
   - 设计 5 款匹配任务栏质感的预设款式：
     - `underlit_chrome`：环形底光通透款 ⭐ (首选)
     - `dark_blue`：经典 PowerShell 科技蓝微光款 ⭐
     - `titanium`：极客银白 / 钛金属微雕款
     - `cyan_matrix`：极光青蓝款 (匹配 Sublime Merge 风格)
     - `pure_dark`：极简深黑哑光款
   - 编写 `build_powershell_icons.py`：基于 SVG 矢量模板通过无头 Edge 渲染高保真 PNG，再由 Pillow 编译为包含 `[16, 24, 32, 48, 64, 128, 256]` 的标准 ICO 文件。
   - 编写 `preview.py` 并生成款式对比图 `comparison_preview.png`。
2. **核心补丁脚本 (`scripts/powershell/patch_powershell_icon.py`)**：
   - 自动检测并定位快捷方式（任务栏 Pinned、开始菜单、桌面）。
   - 自动检测独立版 `WindowsTerminal.exe` / `pwsh.exe`，支持 PE 图标注入。
   - 智能创建并维护任务栏与开始菜单中的 `Windows Terminal.lnk` / `PowerShell.lnk`。
   - 官方原生外壳零风险刷新三连击（`os.utime` + `ie4uinit.exe -show` + `SHChangeNotify`）。
3. **Go CLI 调度引擎升级 (`main.go` & `config.go`)**：
   - `main.go`：支持别名解析（`powershell`、`wt`、`terminal` 等效互通）。
   - `config.go`：在默认配置中加入 `powershell`（默认款式 `underlit_chrome`）。
   - `config.json`：持久化 `powershell` 偏好配置。
4. **测试与构建验证**：
   - 编写/更新单元测试，确保 `go test ./...` 100% 通过。
   - 运行 `build.py` 验证开发构建。
   - 调度实际补丁并验证外壳更新效果。

### 未决问题与阻塞确认清单
- [x] 图标风格是否延续黑曜石圆角方块底板（Squircle）：是，已对齐 Zed/Sublime/DeepSeek 视觉语言。
- [x] 是否需要强制终止 explorer.exe：否，严格遵循零风险外壳刷新三连击，绝不杀进程。

## 三、实施成果与勾选清单
- [x] **视觉资产库与构建流水线完成**：生成 5 款包含 `[16, 24, 32, 48, 64, 128, 256]` 的多尺寸 ICO 及对比图。
- [x] **补丁与守卫引擎完成**：`patch_powershell_icon.py` 自动化维护任务栏及开始菜单快捷方式，支持独立 PE 注入及安全外壳刷新三连击。
- [x] **Go CLI 调度与配置中心完成**：`main.go` 支持 `powershell`、`wt`、`terminal` 别名互通，`config.go` 默认持久化配置。
- [x] **测试与构建通过**：所有 11 个单元测试 100% 通过，`build.py --dev` 验证顺利。

