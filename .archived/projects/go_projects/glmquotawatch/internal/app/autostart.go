package app

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/wailsapp/wails/v3/pkg/application"
)

const autostartIdentifier = "glmquotawatch"

// AutostartEnabled 查询开机自启状态。
func AutostartEnabled(app *application.App) bool {
	if app == nil || app.Autostart == nil {
		return false
	}
	v, err := app.Autostart.IsEnabled()
	return err == nil && v
}

// SetAutostart 设置开机自启；开发版模式严格拒绝写入系统注册表。
func SetAutostart(app *application.App, enabled bool) error {
	if app == nil || app.Autostart == nil {
		return fmt.Errorf("autostart 服务未就绪")
	}
	if !enabled {
		return app.Autostart.Disable()
	}
	if !IsRelease() {
		return fmt.Errorf("dev_mode: 开发版禁止注册开机自启，避免污染系统注册表与生产环境踩踏")
	}
	if err := devExecutableGuard(); err != nil {
		return err
	}
	return app.Autostart.EnableWithOptions(application.AutostartOptions{
		Identifier: autostartIdentifier,
		Arguments:  []string{"--hidden"},
	})
}

// devExecutableGuard 拒绝注册临时构建产物：go run 产物位于系统 Temp 的 go-build* 目录，重启后必然失效。
func devExecutableGuard() error {
	exe, err := os.Executable()
	if err != nil {
		return fmt.Errorf("获取可执行文件路径失败: %w", err)
	}
	cleanExe := filepath.Clean(exe)
	if strings.Contains(cleanExe, "go-build") ||
		strings.HasPrefix(strings.ToLower(cleanExe), strings.ToLower(filepath.Clean(os.TempDir()))) {
		return fmt.Errorf("dev_executable: 当前 exe 为临时构建产物（%s），不可注册开机自启", cleanExe)
	}
	return nil
}
