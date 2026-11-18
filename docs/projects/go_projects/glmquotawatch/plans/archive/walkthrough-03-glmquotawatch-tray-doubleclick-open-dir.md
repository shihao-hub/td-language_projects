# Walkthrough 31: glmquotawatch-gui 托盘双击显示主窗与托盘菜单打开 exe 目录

## 变更内容

1. **托盘双击显示主窗** (`internal/guiapp/tray.go`)：
   - 注册 `a.tray.OnDoubleClick(...)` 事件监听器，当用户在 Windows 任务栏系统托盘（通知区）左键双击用量监控图标时，触发 `a.ensureMainWindow()`，立即显示并置顶主窗口。
2. **托盘菜单新增「打开 exe 目录」** (`internal/guiapp/tray.go`)：
   - 在右键菜单中增加 `menu.Add("打开 exe 目录")` 项（位于「显示主窗」之后、「立即采样」之前）。
   - 封装 `openExeDir()`：通过 `os.Executable()` 获得当前可执行文件的绝对路径并解析目录，利用系统资源管理器（Windows 下 `explorer.exe`，兼顾 cross-platform）打开该目录；若获取或启动失败，调用 `NotifyError` 弹出错误对话框。
3. **文档与表格同步** (`README.md`)：
   - 在 GUI 交互说明表格中补全「托盘双击」与「托盘菜单」中「打开 exe 目录」的说明。

## 验证与测试结果

### 1. 单元测试全量回归
```powershell
cd D:\Users\language_projects\go_projects\glmquotawatch-gui
go test ./...
```
**结果**：全部测试模块通过（`api`、`cli`、`env`、`quota`、`service`、`store` 均 PASS，退出码 0）。

### 2. 生产版可执行文件构建
```powershell
uv run scripts/build-prod.py --skip-frontend
```
**结果**：
- 注入 Windows 图标与资源清单生成 `wails_windows_amd64.syso`；
- 成功编译并输出 `bin\glmquotawatch-gui.exe`（退出码 0，大小 ~14.5MB）。

## 代码 Diff 摘要

```diff
--- a/internal/guiapp/tray.go
+++ b/internal/guiapp/tray.go
@@ -11,8 +17,18 @@ func (a *App) buildTray() {
 	a.tray.SetIcon(a.icon)
 	a.tray.SetTooltip("GLM 用量监控")
 
+	// 注册双击托盘图标事件：显示/唤出主窗口
+	a.tray.OnDoubleClick(func() {
+		a.ensureMainWindow()
+	})
+
 	menu := a.app.NewMenu()
 	menu.Add("显示主窗").OnClick(func(*application.Context) { a.ensureMainWindow() })
+	menu.Add("打开 exe 目录").OnClick(func(*application.Context) {
+		if err := openExeDir(); err != nil {
+			a.rt.ui.NotifyError("打开目录失败", err.Error())
+		}
+	})
 	menu.Add("立即采样").OnClick(func(*application.Context) {
```
