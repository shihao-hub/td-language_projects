package store

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"glmquotawatch/internal/env"
)

func TestDefaultDirUsesAppData(t *testing.T) {
	tmp := t.TempDir()
	t.Setenv("AppData", tmp)
	dir, err := DefaultDir()
	if err != nil {
		t.Fatalf("DefaultDir: %v", err)
	}
	want := filepath.Join(tmp, "language_projects", "glmquotawatch", env.DataSubDir())
	if dir != want {
		t.Fatalf("数据目录不符: got %s want %s", dir, want)
	}
}

func TestDefaultDirFallsBackHome(t *testing.T) {
	t.Setenv("AppData", "")
	dir, err := DefaultDir()
	if err != nil {
		t.Fatalf("DefaultDir: %v", err)
	}
	home, _ := os.UserHomeDir()
	want := filepath.Join(home, ".language_projects", "glmquotawatch", env.DataSubDir())
	if dir != want {
		t.Fatalf("回退目录不符: got %s want %s", dir, want)
	}
}

func TestConfigRoundTrip(t *testing.T) {
	st, err := Open(t.TempDir())
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	cfg, err := st.LoadConfig()
	if err != nil {
		t.Fatalf("LoadConfig: %v", err)
	}
	def := DefaultConfig()
	if cfg.Interval != def.Interval || cfg.Hysteresis != def.Hysteresis || len(cfg.Thresholds) != 4 {
		t.Fatalf("缺失时应返回默认值: %+v", cfg)
	}

	cfg.Token = "token-abcdefgh-1234"
	cfg.Interval = "90s"
	if err := st.SaveConfig(cfg); err != nil {
		t.Fatalf("SaveConfig: %v", err)
	}
	got, err := st.LoadConfig()
	if err != nil {
		t.Fatalf("回读: %v", err)
	}
	if got.Token != cfg.Token || got.Interval != "90s" {
		t.Fatalf("回读不符: %+v", got)
	}

	// 无 .tmp 残留
	entries, _ := os.ReadDir(st.Dir())
	for _, e := range entries {
		if strings.HasSuffix(e.Name(), ".tmp") {
			t.Fatalf("残留临时文件: %s", e.Name())
		}
	}
}

// TestOpenCodeTokenCompat 双向兼容：旧配置文件（无 opencode_token）解析为空，
// 新字段存取往返一致，且不影响既有 GLM 字段。
func TestOpenCodeTokenCompat(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "config.json"),
		[]byte(`{"token":"glm-legacy-token-1234567890","interval":"5m","thresholds":[50,60],"hysteresis":5,"silent":false}`), 0o600); err != nil {
		t.Fatal(err)
	}
	st, err := Open(dir)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	cfg, err := st.LoadConfig()
	if err != nil {
		t.Fatalf("旧配置应可解析: %v", err)
	}
	if cfg.OpenCodeToken != "" {
		t.Fatalf("缺失字段应为空: %q", cfg.OpenCodeToken)
	}
	if cfg.Token != "glm-legacy-token-1234567890" || cfg.Interval != "5m" {
		t.Fatalf("既有字段不应受影响: %+v", cfg)
	}

	cfg.OpenCodeToken = "oc_sk_roundtrip_0123456789"
	if err := st.SaveConfig(cfg); err != nil {
		t.Fatalf("SaveConfig: %v", err)
	}
	got, err := st.LoadConfig()
	if err != nil {
		t.Fatalf("回读: %v", err)
	}
	if got.OpenCodeToken != cfg.OpenCodeToken || got.Token != cfg.Token {
		t.Fatalf("回读不符: %+v", got)
	}

	// opencode_token 为空时序列化省略（omitempty），旧读取器无感
	cfg.OpenCodeToken = ""
	if err := st.SaveConfig(cfg); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(filepath.Join(dir, "config.json"))
	if strings.Contains(string(raw), "opencode_token") {
		t.Fatalf("空值不应落盘 opencode_token: %s", raw)
	}
}

func TestConfigCorrupt(t *testing.T) {
	st, _ := Open(t.TempDir())
	if err := os.WriteFile(filepath.Join(st.Dir(), "config.json"), []byte("{bad json"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := st.LoadConfig(); err == nil {
		t.Fatalf("损坏的 config.json 应报错")
	}
}

func TestStateRoundTripAndCorrupt(t *testing.T) {
	st, _ := Open(t.TempDir())

	s0, err := st.LoadState()
	if err != nil || s0.Version != 0 || s0.Notified != nil {
		t.Fatalf("缺失状态应为零值: %+v err=%v", s0, err)
	}

	want := State{Version: 1, Thresholds: []int{50}, Notified: map[string][]int{"TOKENS_LIMIT:3:5": {50, 60}}}
	if err := st.SaveState(want); err != nil {
		t.Fatalf("SaveState: %v", err)
	}
	got, err := st.LoadState()
	if err != nil || got.Version != 1 || len(got.Notified["TOKENS_LIMIT:3:5"]) != 2 {
		t.Fatalf("状态回读不符: %+v err=%v", got, err)
	}

	if err := os.WriteFile(filepath.Join(st.Dir(), "state.json"), []byte("{bad"), 0o644); err != nil {
		t.Fatal(err)
	}
	_, err = st.LoadState()
	if err == nil {
		t.Fatalf("损坏的 state.json 应报错")
	}
}

func TestAppendSampleMonthlyFile(t *testing.T) {
	st, _ := Open(t.TempDir())
	now := time.Date(2026, 9, 15, 10, 0, 0, 0, time.Local)

	p1, err := st.AppendSample(now, json.RawMessage(`{"level":"max"}`))
	if err != nil {
		t.Fatalf("AppendSample: %v", err)
	}
	if base := filepath.Base(p1); base != "samples-2026-09.jsonl" {
		t.Fatalf("文件名不符: %s", base)
	}
	if _, err := st.AppendSample(now.Add(time.Minute), json.RawMessage(`{"level":"max"}`)); err != nil {
		t.Fatalf("第二次追加: %v", err)
	}

	data, err := os.ReadFile(p1)
	if err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimRight(string(data), "\n"), "\n")
	if len(lines) != 2 {
		t.Fatalf("应两行，实际 %d", len(lines))
	}
	var line struct {
		Ts   string          `json:"ts"`
		Data json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal([]byte(lines[0]), &line); err != nil {
		t.Fatalf("行非合法 JSON: %v", err)
	}
	if string(line.Data) != `{"level":"max"}` {
		t.Fatalf("data 应为原文: %s", line.Data)
	}
}

func TestResetDirGuard(t *testing.T) {
	base := t.TempDir()
	st, _ := Open(base)

	demoDir := filepath.Join(base, "demo")
	if err := os.MkdirAll(demoDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(demoDir, "state.json"), []byte("{}"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := st.ResetDir(demoDir); err != nil {
		t.Fatalf("demo 目录应允许重置: %v", err)
	}
	if _, err := os.Stat(filepath.Join(demoDir, "state.json")); !os.IsNotExist(err) {
		t.Fatalf("重置后旧文件应被清除")
	}

	for _, bad := range []string{base, filepath.Join(base, "demo2"), filepath.Join(base, "demo", "sub"), "", "."} {
		if err := st.ResetDir(bad); err == nil {
			t.Fatalf("非法目标 %q 应被拒绝", bad)
		}
	}
}

func TestAppendOpenCodeSampleAndList(t *testing.T) {
	st, _ := Open(t.TempDir())

	t0 := time.Date(2026, 10, 15, 12, 0, 0, 0, time.Local)
	path, err := st.AppendOpenCodeSample(t0, json.RawMessage(`{"usage":{"rolling":{"percent":5}}}`))
	if err != nil {
		t.Fatalf("AppendOpenCodeSample: %v", err)
	}
	if !strings.HasSuffix(path, "opencode-samples-2026-10.jsonl") {
		t.Fatalf("文件名不符: %s", path)
	}

	files, err := st.ListOpenCodeSampleFiles(t0.AddDate(0, 0, -1))
	if err != nil {
		t.Fatalf("ListOpenCodeSampleFiles: %v", err)
	}
	if len(files) != 1 || files[0] != path {
		t.Fatalf("列出结果不符: %+v", files)
	}
}
