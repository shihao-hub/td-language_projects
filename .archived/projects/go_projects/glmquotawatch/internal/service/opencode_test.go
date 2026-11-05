package service

import (
	"context"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"glmquotawatch/internal/store"
)

const ocTestToken = "oc_sk_test_0123456789abcdef"

// ocUsageBody 上游成功响应（实测形状；重置时间动态生成，避免依赖挂钟）。
func ocUsageBody(now time.Time) string {
	return fmt.Sprintf(`{"usage":{
  "rolling": {"status":"ok","percent":0,"resetsAt":"%s"},
  "weekly":  {"status":"ok","percent":3,"resetsAt":"%s"},
  "monthly": {"status":"rate-limited","percent":83,"resetsAt":"%s"}}}`,
		now.Add(3*time.Hour+25*time.Minute).UTC().Format(time.RFC3339),
		now.Add(4*24*time.Hour).UTC().Format(time.RFC3339),
		now.Add(10*24*time.Hour).UTC().Format(time.RFC3339))
}

// newOpenCodeSvc 构造 httptest 上游 + 隔离数据目录的 Service（环境变量回退默认清空）。
func newOpenCodeSvc(t *testing.T, handler http.HandlerFunc) *Service {
	t.Helper()
	t.Setenv(EnvOpenCodeAPIKey, "")
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	st, err := store.Open(t.TempDir())
	if err != nil {
		t.Fatalf("store.Open: %v", err)
	}
	return New(st, WithOpenCodeBaseURL(srv.URL))
}

func ocOKHandler(t *testing.T, wantToken string) http.HandlerFunc {
	t.Helper()
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer "+wantToken {
			w.WriteHeader(http.StatusUnauthorized)
			_, _ = w.Write([]byte(`{"type":"error","error":{"type":"AuthError","message":"bad key"}}`))
			return
		}
		_, _ = w.Write([]byte(ocUsageBody(time.Now())))
	}
}

func TestMaskOpenCodeToken(t *testing.T) {
	// FR-2 / AC-1：前 4 后 4
	if got := MaskOpenCodeToken("oc_sk_0123456789abcdef"); got != "oc_s…cdef" {
		t.Fatalf("前4后4脱敏不符: %s", got)
	}
	if got := MaskOpenCodeToken("short"); got != "*****" {
		t.Fatalf("短 token 应全星: %s", got)
	}
	if MaskOpenCodeToken("") != "" {
		t.Fatalf("空 token 应为空")
	}
}

func TestOpenCodeTokenLifecycle(t *testing.T) {
	svc := newOpenCodeSvc(t, ocOKHandler(t, ocTestToken))

	if _, err := svc.SetOpenCodeToken("short"); svcErrCode(t, err) != "bad_args" {
		t.Fatalf("短 token 应 bad_args: %v", err)
	}
	view, err := svc.SetOpenCodeToken("  " + ocTestToken + "  ") // trim 生效
	if err != nil {
		t.Fatalf("SetOpenCodeToken: %v", err)
	}
	if !view.HasToken || view.Token != MaskOpenCodeToken(ocTestToken) {
		t.Fatalf("视图应脱敏: %+v", view)
	}
	if strings.Contains(view.Token, ocTestToken) || view.Dir == "" {
		t.Fatalf("视图不应含明文 token 且须带数据目录: %+v", view)
	}

	// 本地配置已存在时，采样不再依赖环境变量
	token, err := svc.openCodeToken()
	if err != nil || token != ocTestToken {
		t.Fatalf("token 解析应取本地配置: %q err=%v", token, err)
	}

	// 幂等清除
	if view, err = svc.RemoveOpenCodeToken(); err != nil || view.HasToken {
		t.Fatalf("remove 后应无 token: %+v err=%v", view, err)
	}
	if view, err = svc.RemoveOpenCodeToken(); err != nil || view.HasToken {
		t.Fatalf("重复 remove 应幂等: %+v err=%v", view, err)
	}

	// 既有 GLM 配置不受影响
	cfg, err := svc.st.LoadConfig()
	if err != nil || cfg.OpenCodeToken != "" {
		t.Fatalf("配置回读不符: %+v err=%v", cfg, err)
	}
}

func TestSampleOpenCodeOnceMock(t *testing.T) {
	svc := newOpenCodeSvc(t, ocOKHandler(t, ocTestToken))
	if _, err := svc.SetOpenCodeToken(ocTestToken); err != nil {
		t.Fatal(err)
	}
	view, err := svc.SampleOpenCodeOnce(context.Background())
	if err != nil {
		t.Fatalf("SampleOpenCodeOnce: %v", err)
	}
	if view.SampledAt == "" || len(view.Windows) != 3 {
		t.Fatalf("视图不符: %+v", view)
	}
	names := []string{"rolling", "weekly", "monthly"}
	labels := []string{"滑动短期窗口", "本周窗口", "本月窗口"}
	for i, w := range view.Windows {
		if w.Name != names[i] || w.Label != labels[i] {
			t.Fatalf("窗口顺序/标签不符: %+v", view.Windows)
		}
		if w.ResetsAt == "" || w.ResetIn == "" {
			t.Fatalf("窗口应含重置时间与倒计时: %+v", w)
		}
	}
	if view.Windows[0].Percent != 0 || view.Windows[1].Percent != 3 || view.Windows[2].Percent != 83 {
		t.Fatalf("百分比解析不符: %+v", view.Windows)
	}
	if view.Windows[2].Status != "rate-limited" {
		t.Fatalf("限流状态解析不符: %+v", view.Windows[2])
	}
	// 倒计时人读短文本（动态未来时间；小时级窗口精确到分钟）
	if view.Windows[0].ResetIn != "3h25m" {
		t.Fatalf("倒计时格式不符: %+v", view.Windows)
	}
	for _, w := range view.Windows[1:] {
		if !strings.HasSuffix(w.ResetIn, "h") && !strings.HasSuffix(w.ResetIn, "d") {
			t.Fatalf("倒计时格式不符: %+v", w)
		}
	}
}

func TestSampleOpenCodeNoToken(t *testing.T) {
	svc := newOpenCodeSvc(t, ocOKHandler(t, ocTestToken))
	if _, err := svc.SampleOpenCodeOnce(context.Background()); svcErrCode(t, err) != "no_token" {
		t.Fatalf("未配 token 应 no_token: %v", err)
	}
	// 环境变量回退可见性：仅 env 有值时 has_token 为 true 且脱敏字段为空
	t.Setenv(EnvOpenCodeAPIKey, ocTestToken)
	view := svc.GetOpenCodeConfig()
	if !view.HasToken || view.Token != "" {
		t.Fatalf("env 回退视图不符: %+v", view)
	}
}

func TestSampleOpenCodeEnvFallback(t *testing.T) {
	svc := newOpenCodeSvc(t, ocOKHandler(t, ocTestToken))
	t.Setenv(EnvOpenCodeAPIKey, ocTestToken)
	view, err := svc.SampleOpenCodeOnce(context.Background())
	if err != nil {
		t.Fatalf("env 回退采样应成功: %v", err)
	}
	if len(view.Windows) != 3 {
		t.Fatalf("视图不符: %+v", view)
	}
}

func TestSampleOpenCodeErrorMapping(t *testing.T) {
	// 401 → auth_error
	unauth := newOpenCodeSvc(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"type":"error","error":{"type":"AuthError","message":"invalid"}}`))
	})
	_, _ = unauth.SetOpenCodeToken(ocTestToken)
	if _, err := unauth.SampleOpenCodeOnce(context.Background()); svcErrCode(t, err) != "auth_error" {
		t.Fatalf("401 应 auth_error: %v", err)
	}

	// 403 → entitlement_error
	forbidden := newOpenCodeSvc(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		_, _ = w.Write([]byte(`{"type":"error","error":{"type":"EntitlementError","message":"no subscription"}}`))
	})
	_, _ = forbidden.SetOpenCodeToken(ocTestToken)
	if _, err := forbidden.SampleOpenCodeOnce(context.Background()); svcErrCode(t, err) != "entitlement_error" {
		t.Fatalf("403 应 entitlement_error: %v", err)
	}

	// 5xx → api_error
	broken := newOpenCodeSvc(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	})
	_, _ = broken.SetOpenCodeToken(ocTestToken)
	if _, err := broken.SampleOpenCodeOnce(context.Background()); svcErrCode(t, err) != "api_error" {
		t.Fatalf("5xx 应 api_error: %v", err)
	}

	// 超时 → timeout
	slow := newOpenCodeSvc(t, func(w http.ResponseWriter, _ *http.Request) {
		time.Sleep(300 * time.Millisecond)
		_, _ = fmt.Fprint(w, ocUsageBody(time.Now()))
	})
	_, _ = slow.SetOpenCodeToken(ocTestToken)
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	if _, err := slow.SampleOpenCodeOnce(ctx); svcErrCode(t, err) != "timeout" {
		t.Fatalf("超时应 timeout: %v", err)
	}

	// 连接失败 → network_error
	closed := httptest.NewServer(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {}))
	closedURL := closed.URL
	closed.Close()
	st, _ := store.Open(t.TempDir())
	svc := New(st, WithOpenCodeBaseURL(closedURL))
	_, _ = svc.SetOpenCodeToken(ocTestToken)
	if _, err := svc.SampleOpenCodeOnce(context.Background()); svcErrCode(t, err) != "network_error" {
		t.Fatalf("网络失败应 network_error: %v", err)
	}
}

// TestOpenCodeErrorsAreServiceErrors 映射后的错误必须可经 errors.As 取回业务码。
func TestOpenCodeErrorsAreServiceErrors(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()
	st, _ := store.Open(t.TempDir())
	svc := New(st, WithOpenCodeBaseURL(srv.URL))
	_, _ = svc.SetOpenCodeToken(ocTestToken)
	_, err := svc.SampleOpenCodeOnce(context.Background())
	var se *Error
	if !errors.As(err, &se) || se.Code != "auth_error" || se.Message == "" {
		t.Fatalf("错误应为 *service.Error: %v", err)
	}
}

func TestSampleOpenCodeHistoryPersistenceAndRead(t *testing.T) {
	svc := newOpenCodeSvc(t, ocOKHandler(t, ocTestToken))
	_, err := svc.SetOpenCodeToken(ocTestToken)
	if err != nil {
		t.Fatalf("SetOpenCodeToken: %v", err)
	}

	windows := OpenCodeHistoryWindows()
	if len(windows) != 3 {
		t.Fatalf("OpenCodeHistoryWindows 数量应为 3: %d", len(windows))
	}

	before := time.Now().Add(-time.Second)
	view, err := svc.SampleOpenCodeOnce(context.Background())
	if err != nil {
		t.Fatalf("SampleOpenCodeOnce: %v", err)
	}
	if len(view.Windows) != 3 {
		t.Fatalf("Windows 数量应为 3: %d", len(view.Windows))
	}

	// 验证三个窗口的持久化历史点
	for _, tc := range []struct {
		win     string
		wantPct int64
	}{
		{"rolling", 0},
		{"weekly", 3},
		{"monthly", 83},
	} {
		pts, rerr := svc.ReadOpenCodeHistory(tc.win, before)
		if rerr != nil {
			t.Fatalf("ReadOpenCodeHistory(%s) failed: %v", tc.win, rerr)
		}
		if len(pts) != 1 {
			t.Fatalf("ReadOpenCodeHistory(%s) 应返回 1 个数据点，实际 %d", tc.win, len(pts))
		}
		if pts[0].Pct != tc.wantPct {
			t.Fatalf("ReadOpenCodeHistory(%s) Pct 期望 %d，实际 %d", tc.win, tc.wantPct, pts[0].Pct)
		}
	}
}

