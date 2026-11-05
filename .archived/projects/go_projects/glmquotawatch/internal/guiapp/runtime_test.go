package guiapp

import (
	"errors"
	"os"
	"path/filepath"
	"testing"

	"glmquotawatch/internal/service"
)

// SetActiveProvider 未识别值应 bad_args（校验先于任何 app 交互，无 GUI 环境可测）。
func TestSetActiveProviderRejectsUnknown(t *testing.T) {
	rt := &MonitorRuntime{activeProvider: ProviderGLM}
	err := rt.SetActiveProvider("foo")
	var se *service.Error
	if !errors.As(err, &se) || se.Code != "bad_args" {
		t.Fatalf("未知 Provider 应 bad_args: %v", err)
	}
	if rt.activeProvider != ProviderGLM {
		t.Fatalf("非法切换不应改变状态: %s", rt.activeProvider)
	}
}

// SampleOpenCodeNow 在服务未启动时应报错而非 panic。
func TestSampleOpenCodeNowRequiresService(t *testing.T) {
	rt := &MonitorRuntime{}
	if _, err := rt.SampleOpenCodeNow(); err == nil {
		t.Fatalf("未启动时采样应报错")
	}
}

func TestBindingsHistoryWindowsOpenCode(t *testing.T) {
	rt := &MonitorRuntime{activeProvider: ProviderOpenCode}
	b := &BindingsService{rt: rt}
	windows, err := b.HistoryWindows()
	if err != nil {
		t.Fatalf("OpenCode HistoryWindows 报错: %v", err)
	}
	if len(windows) != 3 {
		t.Fatalf("OpenCode 窗口应为 3 个: %d", len(windows))
	}
	if windows[0].Key != "rolling" {
		t.Fatalf("第一个窗口应为 rolling: %s", windows[0].Key)
	}
}

func TestBindingsReadHistoryArgs(t *testing.T) {
	rt := &MonitorRuntime{activeProvider: ProviderOpenCode}
	b := &BindingsService{rt: rt}

	// hours 非法
	_, err := b.ReadHistory("rolling", 10)
	var se *service.Error
	if !errors.As(err, &se) || se.Code != "bad_args" {
		t.Fatalf("hours 非法应 bad_args: %v", err)
	}

	// 未识别 windowKey
	_, err = b.ReadHistory("unknown_window", 24)
	if !errors.As(err, &se) || se.Code != "bad_args" {
		t.Fatalf("windowKey 非法应 bad_args: %v", err)
	}
}

// TestSetActiveProviderPersists 切换 Provider 须落盘到 config.json（重启记忆），
// 且 app 未就绪（测试环境）时不得 panic。
func TestSetActiveProviderPersists(t *testing.T) {
	dir := t.TempDir()
	svc, err := service.Open(dir)
	if err != nil {
		t.Fatalf("service.Open: %v", err)
	}
	rt := &MonitorRuntime{svc: svc, activeProvider: ProviderGLM}

	if err := rt.SetActiveProvider(ProviderOpenCode); err != nil {
		t.Fatalf("SetActiveProvider: %v", err)
	}
	if rt.ActiveProvider() != ProviderOpenCode {
		t.Fatalf("内存态应为 opencode: %s", rt.ActiveProvider())
	}
	if got := svc.GetActiveProvider(); got != ProviderOpenCode {
		t.Fatalf("应已落盘为 opencode: %s", got)
	}
}

// TestSnapshotConfigNeverNil 配置不可读时快照仍下发降级 ConfigView（非 nil），
// 避免前端把 null 误判成「未初始化」而永久停在加载态。
func TestSnapshotConfigNeverNil(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "config.json"), []byte("{oops"), 0o600); err != nil {
		t.Fatalf("写坏配置失败: %v", err)
	}
	svc, err := service.Open(dir)
	if err != nil {
		t.Fatalf("service.Open: %v", err)
	}
	rt := &MonitorRuntime{svc: svc, mode: ModeNormal, activeProvider: ProviderGLM}

	st := rt.Snapshot()
	if st.Config == nil {
		t.Fatalf("Config 不应为 nil")
	}
	if st.Config.HasToken {
		t.Fatalf("降级视图不应声称有 token")
	}
	if st.Config.Dir != dir {
		t.Fatalf("降级视图应带数据目录: %s", st.Config.Dir)
	}
	if st.LastError == nil || st.LastError.Code != "config_read_failed" {
		t.Fatalf("应记录配置读取失败: %+v", st.LastError)
	}
}
