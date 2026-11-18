# Plan 31: glmquotawatch-gui 托盘双击显示主窗与托盘菜单打开 exe 目录

## 目标描述
为 `glmquotawatch-gui` 托盘模块增加两个交互能力：
1. **托盘图标双击显示主窗**：用户双击任务栏右下角系统托盘中的用量监控图标时，直接唤醒并置顶显示主窗口。
2. **托盘菜单新增「打开 exe 目录」**：右键点击托盘图标弹出菜单，点击「打开 exe 目录」菜单项后，调用 Windows 资源管理器（Explorer）自动打开当前可执行文件所在目录。

## 需要用户审阅
> [!NOTE]
> - 本次变更属于无破坏性扩展，不影响现有配置结构、CLI 命令行和前端渲染逻辑。
> - 托盘菜单新增菜单项「打开 exe 目录」将排在「显示主窗」之后、「立即采样」之前，符合窗口/资源查看类操作聚拢的交互习惯。

## 待澄清问题
用户已在会话中确认：
1. 需求 1 的操作场景确认为双击右下角系统托盘图标（Tray Icon）呼出主窗口。
2. 需求 2 的托盘菜单文案选定为「打开 exe 目录」。

---

## 变更方案

### [guiapp / 托盘交互]
在 `internal/guiapp/tray.go` 中：
1. 为 `a.tray` 增加 `OnDoubleClick` 事件回调，调用 `a.ensureMainWindow()`。
2. 封装 `openExeDir()` 函数，通过 `os.Executable()` 获取当前运行二进制路径并取得父目录，调用操作系统文件管理器打开（Windows 下调用 `explorer.exe <dir>`，兼顾其他平台）；若执行失败调用 `a.rt.ui.NotifyError` 弹出错误提示。
3. 在 `menu.Add("显示主窗")` 之后添加 `menu.Add("打开 exe 目录")` 菜单项。

#### [MODIFY] internal/guiapp/tray.go

```go
// ... 引入 os, os/exec, path/filepath, runtime ...

func (a *App) buildTray() {
	a.tray = a.app.SystemTray.New()
	a.tray.SetIcon(a.icon)
	a.tray.SetTooltip("GLM 用量监控")

	// 注册双击托盘图标事件：显示/唤出主窗口
	a.tray.OnDoubleClick(func() {
		a.ensureMainWindow()
	})

	menu := a.app.NewMenu()
	menu.Add("显示主窗").OnClick(func(*application.Context) { a.ensureMainWindow() })
	menu.Add("打开 exe 目录").OnClick(func(*application.Context) {
		if err := openExeDir(); err != nil {
			a.rt.ui.NotifyError("打开目录失败", err.Error())
		}
	})
	menu.Add("立即采样").OnClick(func(*application.Context) {
// ...
```

```go
// openExeDir 使用资源管理器打开当前可执行文件所在目录。
func openExeDir() error {
	exe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("获取可执行文件路径失败: %w", err)
	}
	dir := filepath.Dir(exe)
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("explorer.exe", dir)
	case "darwin":
		cmd = exec.Command("open", dir)
	default:
		cmd = exec.Command("xdg-open", dir)
	}
	return cmd.Start()
}
```

## 验证方案

### 自动化测试
1. 执行现有单元测试集验证回归：
   ```powershell
   cd D:\Users\language_projects\go_projects\glmquotawatch-gui
   go test ./...
   ```
2. 执行开发构建验证编译通过与符号解析：
   ```powershell
   cd D:\Users\language_projects\go_projects\glmquotawatch-gui
   go build -o bin/glmquotawatch-gui.exe .
   ```

### 人工验证
1. 启动应用并进入托盘：
   - 运行 `bin\glmquotawatch-gui.exe`。
   - 关闭主窗口使其最小化至托盘。
2. 验证双击唤醒：
   - 在任务栏系统托盘中找到 GLM 用量监控图标，鼠标左键双击。
   - 检查主窗口是否立刻显示并获得焦点。
3. 验证打开 exe 目录：
   - 右键点击托盘图标展开托盘菜单，查看是否存在「打开 exe 目录」。
   - 点击「打开 exe 目录」，确认系统资源管理器窗口弹出并正确展示 `bin` 所在目录。
   - 通过托盘菜单点击「退出」，确认进程干净退出。
