package app

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"runtime/debug"
	"sync"
	"sync/atomic"
	"time"

	"glmquotawatch/frontend"
	"glmquotawatch/internal/guiapp"

	"github.com/wailsapp/wails/v3/pkg/application"
	"github.com/wailsapp/wails/v3/pkg/events"
	"github.com/wailsapp/wails/v3/pkg/services/notifications"
	"github.com/wailsapp/wails/v3/pkg/w32"
)

type App struct {
	app         *application.App
	rt          *guiapp.MonitorRuntime
	winMu       sync.Mutex
	win         *application.WebviewWindow
	ensureMu    sync.Mutex
	exiting     atomic.Bool
	tray        *application.SystemTray
	silentItem  *application.MenuItem
	autostartIt *application.MenuItem
	demoItem    *application.MenuItem

	stateMu    sync.Mutex
	stateTimer *time.Timer
	winState   windowState
}

// SingleInstanceID 返回单例互斥 ID。
func SingleInstanceID() string {
	if !IsRelease() {
		return "shihao.langproj.glmquotawatch.gui.dev"
	}
	return "shihao.langproj.glmquotawatch.gui"
}

// WindowTitle 返回主窗口标题。
func WindowTitle() string {
	if !IsRelease() {
		return "GLM 用量监控 [DEV]"
	}
	return "GLM 用量监控"
}

// LaunchGUI 启动 WebUI + Wails 桌面壳。
func LaunchGUI(hidden bool, demo bool) error {
	bindings := &guiapp.BindingsService{}
	ns := notifications.New()

	var appInstance *App

	singleID := SingleInstanceID()
	logf("启动 GLM 用量监控 GUI: version=%s, mode=%s, singleID=%s, hidden=%v, demo=%v", Version, BuildMode, singleID, hidden, demo)

	wailsApp := application.New(application.Options{
		Logger:      wailsLogger(),
		Name:        "glmquotawatch",
		Description: "GLM 编码套餐用量监控（托盘常驻 + 阈值 Toast 告警）",
		Icon:        IconICO,
		Services: []application.Service{
			application.NewService(bindings),
			application.NewService(ns),
		},
		Assets: application.AssetOptions{
			Handler: application.AssetFileServerFS(frontend.Dist),
		},
		Windows: application.WindowsOptions{
			DisableQuitOnLastWindowClosed: true,
			WebviewUserDataPath:           webviewDataPath(),
			AdditionalBrowserArgs: []string{
				"--disable-gpu",
				"--disable-gpu-compositing",
				"--disable-software-rasterizer",
				"--renderer-process-limit=1",
				"--disable-features=NetworkServiceOutOfProcess",
			},
		},
		SingleInstance: &application.SingleInstanceOptions{
			UniqueID: singleID,
			ExitCode: 0,
			OnSecondInstanceLaunch: func(data application.SecondInstanceData) {
				if appInstance != nil {
					for _, arg := range data.Args {
						if arg == "--demo" {
							go func() { _ = appInstance.rt.EnterDemo() }()
						}
					}
					appInstance.ensureMainWindow()
				}
			},
		},
	})

	appInstance = &App{
		app:      wailsApp,
		winState: loadWindowState(),
	}

	appInstance.rt = guiapp.NewMonitorRuntime(wailsApp, ns)
	bindings.SetRuntime(appInstance.rt)

	appInstance.buildTray()
	appInstance.rt.SetUI(appInstance)
	appInstance.rt.Start(demo)

	if !hidden {
		appInstance.ensureMainWindow()
	}

	return wailsApp.Run()
}

func (a *App) buildWindowLocked(hidden bool) {
	state := a.currentWindowState()
	opts := application.WebviewWindowOptions{
		Title:            WindowTitle(),
		Width:            state.Width,
		Height:           state.Height,
		MinWidth:         minWindowWidth,
		MinHeight:        minWindowHeight,
		Hidden:           hidden,
		URL:              "/",
		BackgroundColour: application.NewRGB(246, 248, 247),
	}
	if state.HasPos {
		opts.InitialPosition = application.WindowXY
		opts.X, opts.Y = state.X, state.Y
	}
	win := a.app.Window.NewWithOptions(opts)
	a.win = win

	win.RegisterHook(events.Windows.WindowShow, func(*application.WindowEvent) {
		a.applyWindowIcon(win)
		a.ensureWindowOnScreen(win)
	})
	win.RegisterHook(events.Windows.WindowActive, func(*application.WindowEvent) {
		a.applyWindowIcon(win)
	})

	for _, evt := range []events.WindowEventType{
		events.Common.WindowDidResize,
		events.Common.WindowDidMove,
		events.Common.WindowMaximise,
		events.Common.WindowUnMaximise,
	} {
		win.OnWindowEvent(evt, func(*application.WindowEvent) {
			a.scheduleSaveWindowState(win)
		})
	}

	win.RegisterHook(events.Common.WindowClosing, func(*application.WindowEvent) {
		if a.exiting.Load() {
			return
		}
		a.stopWindowStateTimer()
		a.saveWindowState(win)

		a.winMu.Lock()
		if a.win == win {
			a.win = nil
		}
		a.winMu.Unlock()

		go func() {
			time.Sleep(250 * time.Millisecond)
			runtime.GC()
			debug.FreeOSMemory()
		}()
	})
}

func (a *App) applyWindowIcon(win *application.WebviewWindow) {
	if win == nil || len(IconICO) == 0 {
		return
	}
	hwnd := w32.HWND(win.NativeWindow())
	if hwnd == 0 {
		return
	}
	if hBig, err := w32.CreateLargeHIconFromImage(IconICO); err == nil && hBig != 0 {
		w32.SendMessage(hwnd, w32.WM_SETICON, w32.ICON_BIG, uintptr(hBig))
		w32.SetApplicationIcon(uintptr(hwnd), hBig)
	}
	if hSmall, err := w32.CreateSmallHIconFromImage(IconICO); err == nil && hSmall != 0 {
		w32.SetWindowIcon(hwnd, hSmall)
	}
}

func (a *App) currentWindowState() windowState {
	a.stateMu.Lock()
	defer a.stateMu.Unlock()
	return a.winState
}

func (a *App) scheduleSaveWindowState(win *application.WebviewWindow) {
	a.stateMu.Lock()
	defer a.stateMu.Unlock()

	if a.stateTimer != nil {
		a.stateTimer.Stop()
	}
	a.stateTimer = time.AfterFunc(time.Duration(windowStateSaveDelay)*time.Millisecond, func() {
		a.saveWindowState(win)
	})
}

func (a *App) stopWindowStateTimer() {
	a.stateMu.Lock()
	defer a.stateMu.Unlock()
	if a.stateTimer != nil {
		a.stateTimer.Stop()
		a.stateTimer = nil
	}
}

func (a *App) saveWindowState(win *application.WebviewWindow) {
	if win == nil {
		return
	}
	state := a.currentWindowState()
	switch {
	case win.IsMinimised(), win.IsFullscreen():
		return
	case win.IsMaximised():
		state.Maximised = true
	default:
		w, h := win.Size()
		if w < minWindowWidth || h < minWindowHeight {
			return
		}
		x, y := win.Position()
		state.Width, state.Height = w, h
		state.X, state.Y, state.HasPos = x, y, true
		state.Maximised = false
	}

	a.stateMu.Lock()
	changed := state != a.winState
	a.winState = state
	a.stateMu.Unlock()

	if changed {
		if err := writeWindowState(state); err != nil {
			logf("保存窗口状态失败: %v", err)
		}
	}
}

func (a *App) ensureWindowOnScreen(win *application.WebviewWindow) {
	screens := a.app.Screen.GetAll()
	if len(screens) == 0 {
		return
	}
	x, y := win.Position()
	w, h := win.Size()
	cx, cy := x+w/2, y+h/2
	for _, s := range screens {
		area := s.WorkArea
		if cx >= area.X && cx < area.X+area.Width && cy >= area.Y && cy < area.Y+area.Height {
			return
		}
	}
	logf("窗口中心不在任何屏幕工作区内，重置到主屏居中")
	win.Center()
	a.scheduleSaveWindowState(win)
}

func (a *App) ensureMainWindow() {
	go a.showMainWindow()
}

func (a *App) showMainWindow() {
	a.ensureMu.Lock()
	defer a.ensureMu.Unlock()

	if a.exiting.Load() {
		return
	}

	a.winMu.Lock()
	win := a.win
	if win != nil {
		if _, exists := a.app.Window.GetByID(win.ID()); !exists {
			a.win = nil
			win = nil
		}
	}
	a.winMu.Unlock()

	if win != nil {
		if win.IsMinimised() {
			win.UnMinimise()
		}
		win.Show()
		win.Focus()
		a.applyWindowIcon(win)
		return
	}

	state := a.currentWindowState()
	a.winMu.Lock()
	a.buildWindowLocked(false)
	win = a.win
	a.winMu.Unlock()

	if win != nil {
		win.Show()
		if state.Maximised {
			win.Maximise()
		}
		win.Focus()
		a.applyWindowIcon(win)
	}
}

func (a *App) buildTray() {
	a.tray = a.app.SystemTray.New()
	if len(IconICO) > 0 {
		a.tray.SetIcon(IconICO)
	}
	a.tray.SetTooltip("GLM 用量监控")
	a.tray.OnClick(a.ensureMainWindow)
	a.tray.OnDoubleClick(a.ensureMainWindow)

	menu := a.app.NewMenu()
	menu.Add("打开工作台").OnClick(func(*application.Context) { a.ensureMainWindow() })
	menu.Add("打开 exe 目录").OnClick(func(*application.Context) {
		if err := openExeDir(); err != nil {
			a.NotifyError("打开目录失败", err.Error())
		}
	})
	menu.Add("立即采样").OnClick(func(*application.Context) {
		if _, err := a.rt.SampleNow(); err != nil {
			a.NotifyError("立即采样失败", err.Error())
		}
	})
	a.silentItem = menu.AddCheckbox("静音通知", false)
	a.silentItem.OnClick(func(*application.Context) {
		if err := a.rt.ToggleSilent(); err != nil {
			a.NotifyError("切换静音失败", err.Error())
		}
	})

	if IsRelease() {
		a.autostartIt = menu.AddCheckbox("开机自启", a.autostartEnabled())
		a.autostartIt.OnClick(func(*application.Context) {
			enabled := a.autostartEnabled()
			if err := a.setAutostart(!enabled); err != nil {
				logf("设置开机自启失败: %v", err)
				a.NotifyError("设置开机自启失败", err.Error())
			} else {
				a.autostartIt.SetChecked(!enabled)
			}
		})
	} else {
		disabledItem := menu.AddCheckbox("开机自启 (开发版已禁用)", false)
		disabledItem.SetEnabled(false)
	}

	a.demoItem = menu.Add("进入演示模式")
	a.demoItem.OnClick(func(*application.Context) {
		if a.rt.Mode() == "demo" {
			if err := a.rt.ExitDemo(); err != nil {
				a.NotifyError("退出演示失败", err.Error())
			}
			return
		}
		if err := a.rt.EnterDemo(); err != nil {
			a.NotifyError("进入演示失败", err.Error())
		}
	})
	menu.AddSeparator()
	menu.Add("彻底退出").OnClick(func(*application.Context) {
		go a.quit()
	})
	a.tray.SetMenu(menu)

	if IsRelease() && a.autostartIt != nil {
		a.autostartIt.SetChecked(a.autostartEnabled())
	}
}

func (a *App) autostartEnabled() bool {
	return AutostartEnabled(a.app)
}

func (a *App) setAutostart(enabled bool) error {
	return SetAutostart(a.app, enabled)
}

func (a *App) quit() {
	a.exiting.Store(true)
	a.rt.Stop()

	a.winMu.Lock()
	win := a.win
	a.win = nil
	a.winMu.Unlock()

	if win != nil {
		win.Close()
	}
	a.app.Quit()
}

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

// UIBridge 实现
func (a *App) SetTooltip(text string) {
	if a.tray != nil {
		a.tray.SetTooltip(text)
	}
}

func (a *App) SetSilentChecked(checked bool) {
	if a.silentItem != nil {
		a.silentItem.SetChecked(checked)
	}
}

func (a *App) SetAutostartChecked(checked bool) {
	if a.autostartIt != nil {
		a.autostartIt.SetChecked(checked)
	}
}

func (a *App) SetDemoMode(demo bool) {
	if a.demoItem != nil {
		if demo {
			a.demoItem.SetLabel("退出演示模式")
		} else {
			a.demoItem.SetLabel("进入演示模式")
		}
	}
	if a.silentItem != nil {
		a.silentItem.SetEnabled(!demo)
	}
}

func (a *App) NotifyError(title, message string) {
	a.app.Dialog.Error().SetTitle(title).SetMessage(message).Show()
}

func (a *App) SetAutostart(enabled bool) error {
	return a.setAutostart(enabled)
}

func (a *App) AutostartEnabled() bool {
	return a.autostartEnabled()
}
