package app

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

var (
	logOnce sync.Once
	logFile *os.File
)

// Logf 同时向 os.Stderr 与数据目录下的日志文件写入格式化日志。
func Logf(format string, args ...any) {
	logf(format, args...)
}

func logf(format string, args ...any) {
	line := fmt.Sprintf("%s %s\n", time.Now().Format("2006-01-02 15:04:05"), fmt.Sprintf(format, args...))
	_, _ = fmt.Fprint(os.Stderr, line)

	logOnce.Do(func() {
		base := appDataDir()
		if base == "" {
			return
		}
		if err := os.MkdirAll(base, 0o755); err != nil {
			return
		}
		f, err := os.OpenFile(filepath.Join(base, "glmquotawatch.log"), os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o644)
		if err == nil {
			logFile = f
		}
	})
	if logFile != nil {
		_, _ = logFile.WriteString(line)
	}
}
