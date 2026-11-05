package app

import (
	"os"
	"path/filepath"

	"glmquotawatch/internal/env"
)

// DataDir 返回当前构建通道（dev / prod）的运行时数据目录。
func DataDir() string {
	return appDataDir()
}

// DefaultDir 与 DataDir 等价，供 store 等持久层接入。
func DefaultDir() string {
	return appDataDir()
}

// appDataDir 解析 %APPDATA%\language_projects\glmquotawatch\<dev|prod>，
// 取不到时回退 ~/.language_projects/glmquotawatch/<dev|prod>。
func appDataDir() string {
	subDir := env.DataSubDir()

	if appData := os.Getenv("AppData"); appData != "" {
		return filepath.Join(appData, "language_projects", "glmquotawatch", subDir)
	}

	home, err := os.UserHomeDir()
	if err != nil || home == "" {
		return ""
	}
	return filepath.Join(home, ".language_projects", "glmquotawatch", subDir)
}

// webviewDataPath 隔离 WebView2 运行时用户缓存目录。
func webviewDataPath() string {
	base := appDataDir()
	if base == "" {
		return ""
	}
	return filepath.Join(base, "webview2")
}
