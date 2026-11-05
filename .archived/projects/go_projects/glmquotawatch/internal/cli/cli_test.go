package cli

import (
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/spf13/cobra"
)

// ocCLITestToken OpenCode 侧测试 key（mock 上游按此校验鉴权）。
const ocCLITestToken = "oc_sk_cli_test_0123456789abcdef"

// TestMain 隔离数据目录（AppData → 临时目录）并把 GLM / OpenCode 上游分别
// 指到进程内 httptest（service.Open 经环境变量注入），绝不触网、不碰真实配置。
func TestMain(m *testing.M) {
	tmp, err := os.MkdirTemp("", "gqwgui-cli-test-*")
	if err != nil {
		panic(err)
	}
	defer os.RemoveAll(tmp)
	os.Setenv("AppData", tmp)

	var pct atomic.Int64
	pct.Store(2)
	reset := time.Now().Add(4*time.Hour + 43*time.Minute).UnixMilli()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		fmt.Fprintf(w, `{"code":200,"msg":"操作成功","success":true,"data":{"level":"max","limits":[`+
			`{"type":"TOKENS_LIMIT","unit":3,"number":5,"percentage":%d,"nextResetTime":%d}]}}`,
			pct.Load(), reset)
	}))
	defer srv.Close()
	os.Setenv("GLMQUOTAWATCH_GUI_API_BASE", srv.URL)

	// OpenCode Go mock：Bearer 校验；有效 key 返回三窗口，其余 401
	ocNow := time.Now()
	ocSrv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer "+ocCLITestToken {
			w.WriteHeader(http.StatusUnauthorized)
			fmt.Fprint(w, `{"type":"error","error":{"type":"AuthError","message":"invalid key"}}`)
			return
		}
		fmt.Fprintf(w, `{"usage":{
			"rolling": {"status":"ok","percent":12,"resetsAt":"%s"},
			"weekly":  {"status":"ok","percent":34,"resetsAt":"%s"},
			"monthly": {"status":"rate-limited","percent":100,"resetsAt":"%s"}}}`,
			ocNow.Add(3*time.Hour+25*time.Minute).UTC().Format(time.RFC3339),
			ocNow.Add(4*24*time.Hour).UTC().Format(time.RFC3339),
			ocNow.Add(10*24*time.Hour).UTC().Format(time.RFC3339))
	}))
	defer ocSrv.Close()
	os.Setenv("OPENCODE_GO_API_BASE", ocSrv.URL)
	os.Setenv("OPENCODE_API_KEY", "") // 隔离真实环境变量，保证 no_token/env 回退路径确定

	code := m.Run()
	srv.Close()
	ocSrv.Close()
	os.Exit(code)
}

// capture 截获标准流（os.Stdout/os.Stderr 在调用时求值，可直接替换）。
// 读取必须在后台并发进行：输出超过 pipe 缓冲（如 schema 导出）时，
// 先写后读会让写端阻塞在 writeFile 上造成死锁。
func capture(t *testing.T, target **os.File, fn func()) string {
	t.Helper()
	old := *target
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("os.Pipe: %v", err)
	}
	*target = w
	done := make(chan string, 1)
	go func() {
		b, _ := io.ReadAll(r)
		done <- string(b)
	}()
	fn()
	_ = w.Close()
	*target = old
	return <-done
}

func captureStdout(t *testing.T, fn func()) string { return capture(t, &os.Stdout, fn) }

func TestRunExitCodes(t *testing.T) {
	// 参数/flag 错误 → 2，stdout 仍是信封
	var stdOut string
	var code int
	stdOut = captureStdout(t, func() { code = Run([]string{"token", "set"}) })
	if code != 2 {
		t.Fatalf("参数不足应退出码 2: %d", code)
	}
	if !strings.Contains(stdOut, `"ok": false`) || !strings.Contains(stdOut, "bad_args") {
		t.Fatalf("参数错误应输出信封: %q", stdOut)
	}
	stdOut = captureStdout(t, func() { code = Run([]string{"status", "--nope"}) })
	if code != 2 || !strings.Contains(stdOut, `"ok": false`) {
		t.Fatalf("未知 flag 应退出码 2 且信封输出: code=%d out=%q", code, stdOut)
	}

	// 业务错误 → 1，stdout 信封（恒 JSON，无人读分支）
	stdOut = captureStdout(t, func() { code = Run([]string{"token", "set", "short"}) })
	if code != 1 {
		t.Fatalf("短 token 应退出码 1: %d", code)
	}
	if !strings.Contains(stdOut, `"ok": false`) || !strings.Contains(stdOut, "bad_args") {
		t.Fatalf("业务失败应输出错误信封: %q", stdOut)
	}

	// 配置成功 → 0，信封含 data
	stdOut = captureStdout(t, func() { code = Run([]string{"token", "set", strings.Repeat("x", 30)}) })
	if code != 0 || !strings.Contains(stdOut, `"ok": true`) {
		t.Fatalf("token set 应成功信封: code=%d out=%q", code, stdOut)
	}

	// config set 非法值 → 1；合法 → 0
	captureStdout(t, func() { code = Run([]string{"config", "set", "interval", "bogus"}) })
	if code != 1 {
		t.Fatalf("非法 interval 应退出码 1: %d", code)
	}
	captureStdout(t, func() { code = Run([]string{"config", "set", "thresholds", "80,50,50"}) })
	if code != 0 {
		t.Fatalf("thresholds 应成功: %d", code)
	}

	// status → 信封（恒 JSON，无 --json flag）
	stdOut = captureStdout(t, func() { code = Run([]string{"status"}) })
	if code != 0 {
		t.Fatalf("status 应成功: %d", code)
	}
	if !strings.Contains(stdOut, `"ok": true`) || !strings.Contains(stdOut, `"windows"`) || !strings.Contains(stdOut, `"5h 窗口"`) {
		t.Fatalf("status 信封不符: %q", stdOut)
	}

	// token show → 脱敏：有 token 但不含明文
	stdOut = captureStdout(t, func() { code = Run([]string{"token", "show"}) })
	if code != 0 {
		t.Fatalf("token show 应成功: %d", code)
	}
	if !strings.Contains(stdOut, `"has_token": true`) {
		t.Fatalf("配置信封不符: %q", stdOut)
	}
	if strings.Contains(stdOut, strings.Repeat("x", 30)) {
		t.Fatalf("token show 不应输出明文: %q", stdOut)
	}

	// --json flag 已移除：作为未知 flag 报 bad_args 退出码 2
	captureStdout(t, func() { code = Run([]string{"--json", "status"}) })
	if code != 2 {
		t.Fatalf("--json 已移除，应退出码 2: %d", code)
	}
}

// TestOpenCodeCLI 覆盖 AC-1/AC-2/AC-3：token set/show/remove 与 status 信封、
// 脱敏不回明文、无效 key → auth_error 退出码 1。
func TestOpenCodeCLI(t *testing.T) {
	var stdOut string
	var code int

	// 未配置 token → no_token（env 已在 TestMain 清空）
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "status"}) })
	if code != 1 || !strings.Contains(stdOut, `"no_token"`) {
		t.Fatalf("未配置应 no_token 且退出码 1: code=%d out=%q", code, stdOut)
	}

	// 短 key → bad_args 退出码 1
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "set", "short"}) })
	if code != 1 || !strings.Contains(stdOut, `"bad_args"`) {
		t.Fatalf("短 key 应 bad_args: code=%d out=%q", code, stdOut)
	}

	// 设置有效 key → 成功信封
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "set", ocCLITestToken}) })
	if code != 0 || !strings.Contains(stdOut, `"has_token": true`) {
		t.Fatalf("token set 应成功: code=%d out=%q", code, stdOut)
	}

	// AC-2：status 输出三窗口
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "status"}) })
	if code != 0 || !strings.Contains(stdOut, `"ok": true`) {
		t.Fatalf("status 应成功: code=%d out=%q", code, stdOut)
	}
	for _, want := range []string{`"rolling"`, `"weekly"`, `"monthly"`, `"percent": 12`, `"resets_at"`, `"reset_in"`, `"rate-limited"`} {
		if !strings.Contains(stdOut, want) {
			t.Fatalf("status 输出缺 %s: %q", want, stdOut)
		}
	}

	// AC-1：token show 前4后4脱敏且不含明文
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "show"}) })
	if code != 0 || !strings.Contains(stdOut, `"token": "oc_s…cdef"`) {
		t.Fatalf("token show 应脱敏: code=%d out=%q", code, stdOut)
	}
	if strings.Contains(stdOut, ocCLITestToken) {
		t.Fatalf("token show 不应输出明文: %q", stdOut)
	}

	// AC-3：无效 key → auth_error 退出码 1
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "set", "oc_sk_cli_invalid_0000000000"}) })
	if code != 0 {
		t.Fatalf("格式合法的无效 key set 应成功: code=%d out=%q", code, stdOut)
	}
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "status"}) })
	if code != 1 || !strings.Contains(stdOut, `"auth_error"`) || !strings.Contains(stdOut, `"ok": false`) {
		t.Fatalf("无效 key 应 auth_error 且退出码 1: code=%d out=%q", code, stdOut)
	}

	// remove（幂等）→ 回到 no_token
	captureStdout(t, func() { code = Run([]string{"opencode", "token", "remove"}) })
	if code != 0 {
		t.Fatalf("token remove 应成功: %d", code)
	}
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "remove"}) })
	if code != 0 || !strings.Contains(stdOut, `"has_token": false`) {
		t.Fatalf("重复 remove 应幂等: code=%d out=%q", code, stdOut)
	}
}

// TestOpenCodeEnvFallbackCLI 环境变量回退：无本地配置时 make status 可用（AC-2 补充）。
func TestOpenCodeEnvFallbackCLI(t *testing.T) {
	os.Setenv("OPENCODE_API_KEY", ocCLITestToken)
	defer os.Setenv("OPENCODE_API_KEY", "")

	var code int
	var stdOut string
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "status"}) })
	if code != 0 || !strings.Contains(stdOut, `"ok": true`) {
		t.Fatalf("env 回退采样应成功: code=%d out=%q", code, stdOut)
	}
	stdOut = captureStdout(t, func() { code = Run([]string{"opencode", "token", "show"}) })
	if code != 0 || !strings.Contains(stdOut, `"has_token": true`) || strings.Contains(stdOut, ocCLITestToken) {
		t.Fatalf("env 回退 show 应为 has_token 且脱敏: code=%d out=%q", code, stdOut)
	}
}

func TestSchemaExport(t *testing.T) {
	var code int
	stdOut := captureStdout(t, func() { code = Run([]string{"schema"}) })
	if code != 0 {
		t.Fatalf("schema 应成功: %d", code)
	}
	if !strings.Contains(stdOut, `"interface": "cli"`) {
		t.Fatalf("schema 应声明 interface: cli: %q", stdOut)
	}
	for _, want := range []string{
		"token set", "token show", "token remove", "status", "config show", "config set",
		"opencode token set", "opencode token show", "opencode token remove", "opencode status",
		"schema", "version",
	} {
		if !strings.Contains(stdOut, `"`+want+`"`) {
			t.Fatalf("schema 导出缺命令 %s", want)
		}
	}

	// 漂移防线：生成器的命令名集合 == 命令树实际名称集合
	doc, err := BuildSchemaDoc()
	if err != nil {
		t.Fatalf("BuildSchemaDoc: %v", err)
	}
	got := map[string]bool{}
	for _, c := range doc.Commands {
		got[c.Name] = true
	}
	want := map[string]bool{}
	root := newRootCmd()
	var walk func(parent string, c *cobra.Command)
	walk = func(parent string, c *cobra.Command) {
		for _, sub := range c.Commands() {
			if sub.Hidden || builtinCommands[sub.Name()] {
				continue
			}
			path := sub.Name()
			if parent != "" {
				path = parent + " " + sub.Name()
			}
			want[path] = true
			walk(path, sub)
		}
	}
	walk("", root)
	if len(got) != len(want) {
		t.Fatalf("命令集合不一致: got %v want %v", got, want)
	}
	for k := range want {
		if !got[k] {
			t.Fatalf("命令树含 %s 但 schema 缺失", k)
		}
	}
}

func TestVersionEnvelope(t *testing.T) {
	var code int
	stdOut := captureStdout(t, func() { code = Run([]string{"--version"}) })
	if code != 0 || !strings.Contains(stdOut, `"ok": true`) || !strings.Contains(stdOut, `"version"`) {
		t.Fatalf("--version 应输出信封: code=%d out=%q", code, stdOut)
	}
	stdOut = captureStdout(t, func() { code = Run([]string{"version"}) })
	if code != 0 || !strings.Contains(stdOut, `"ok": true`) {
		t.Fatalf("version 子命令应输出信封: code=%d out=%q", code, stdOut)
	}
}
