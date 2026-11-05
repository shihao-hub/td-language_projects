package opencode

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

const testToken = "oc_sk_test_0123456789abcdef"

// successBody 官方文档实测响应形状。
const successBody = `{
  "usage": {
    "rolling": {"status": "ok", "percent": 0, "resetsAt": "2026-10-14T05:21:41.000Z"},
    "weekly":  {"status": "ok", "percent": 3, "resetsAt": "2026-10-19T00:00:00.000Z"},
    "monthly": {"status": "rate-limited", "percent": 100, "resetsAt": "2026-10-20T17:59:00.000Z"}
  }
}`

func newServer(t *testing.T, handler http.HandlerFunc) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	return srv
}

func TestNewClientDefaults(t *testing.T) {
	c := NewClient("", testToken)
	if c.BaseURL != DefaultBaseURL {
		t.Fatalf("空 baseURL 应回退默认: %s", c.BaseURL)
	}
	c = NewClient("https://example.com/base/", testToken)
	if c.BaseURL != "https://example.com/base" {
		t.Fatalf("baseURL 应去尾斜杠: %s", c.BaseURL)
	}
}

func TestEnvBaseURLName(t *testing.T) {
	// FR-1 钉死环境变量名契约（服务层按此读取）。
	if EnvBaseURL != "OPENCODE_GO_API_BASE" {
		t.Fatalf("环境变量名漂移: %s", EnvBaseURL)
	}
}

func TestFetchUsageSuccess(t *testing.T) {
	var gotPath, gotAuth string
	srv := newServer(t, func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotAuth = r.Header.Get("Authorization")
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(successBody))
	})

	c := NewClient(srv.URL, testToken)
	usage, err := c.FetchUsage(context.Background())
	if err != nil {
		t.Fatalf("FetchUsage: %v", err)
	}
	if gotPath != "/usage" {
		t.Fatalf("请求路径不符: %s", gotPath)
	}
	if gotAuth != "Bearer "+testToken {
		t.Fatalf("Authorization 头不符: %s", gotAuth)
	}
	if usage.Rolling.Percent != 0 || usage.Rolling.Status != "ok" {
		t.Fatalf("rolling 解析不符: %+v", usage.Rolling)
	}
	if usage.Weekly.Percent != 3 || usage.Weekly.ResetsAt != "2026-10-19T00:00:00.000Z" {
		t.Fatalf("weekly 解析不符: %+v", usage.Weekly)
	}
	if usage.Monthly.Status != "rate-limited" || usage.Monthly.Percent != 100 {
		t.Fatalf("monthly 解析不符: %+v", usage.Monthly)
	}
}

func TestFetchUsageUnauthorized(t *testing.T) {
	srv := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
		_, _ = w.Write([]byte(`{"type":"error","error":{"type":"AuthError","message":"invalid api key"}}`))
	})
	_, err := NewClient(srv.URL, "bad").FetchUsage(context.Background())
	if !errors.Is(err, ErrUnauthorized) {
		t.Fatalf("401 应映射 ErrUnauthorized: %v", err)
	}
	if !strings.Contains(err.Error(), "invalid api key") {
		t.Fatalf("错误应携带上游 message: %v", err)
	}
}

func TestFetchUsageForbidden(t *testing.T) {
	srv := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusForbidden)
		_, _ = w.Write([]byte(`{"type":"error","error":{"type":"EntitlementError","message":"go plan required"}}`))
	})
	_, err := NewClient(srv.URL, testToken).FetchUsage(context.Background())
	if !errors.Is(err, ErrForbidden) {
		t.Fatalf("403 应映射 ErrForbidden: %v", err)
	}
}

func TestFetchUsageServerError(t *testing.T) {
	srv := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusBadGateway)
		_, _ = w.Write([]byte("bad gateway"))
	})
	_, err := NewClient(srv.URL, testToken).FetchUsage(context.Background())
	var he *HTTPError
	if !errors.As(err, &he) || he.Status != http.StatusBadGateway {
		t.Fatalf("5xx 应映射 *HTTPError: %v", err)
	}
}

func TestFetchUsageBadResponse(t *testing.T) {
	srv := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte("not json"))
	})
	_, err := NewClient(srv.URL, testToken).FetchUsage(context.Background())
	if err == nil || errors.Is(err, ErrUnauthorized) || errors.Is(err, ErrForbidden) {
		t.Fatalf("非法 JSON 应报解析错误: %v", err)
	}

	empty := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		_, _ = w.Write([]byte(`{}`))
	})
	_, err = NewClient(empty.URL, testToken).FetchUsage(context.Background())
	if err == nil || !strings.Contains(err.Error(), "usage") {
		t.Fatalf("缺 usage 字段应报错: %v", err)
	}
}

func TestFetchUsageTimeout(t *testing.T) {
	srv := newServer(t, func(w http.ResponseWriter, _ *http.Request) {
		time.Sleep(300 * time.Millisecond)
		_, _ = w.Write([]byte(successBody))
	})
	ctx, cancel := context.WithTimeout(context.Background(), 50*time.Millisecond)
	defer cancel()
	_, err := NewClient(srv.URL, testToken).FetchUsage(ctx)
	if !errors.Is(err, context.DeadlineExceeded) {
		t.Fatalf("超时应可判定 DeadlineExceeded: %v", err)
	}
}

func TestFetchUsageNetworkError(t *testing.T) {
	srv := newServer(t, func(http.ResponseWriter, *http.Request) {})
	url := srv.URL
	srv.Close() // 立即关闭制造连接失败

	_, err := NewClient(url, testToken).FetchUsage(context.Background())
	if err == nil {
		t.Fatalf("连接失败应报错")
	}
	if errors.Is(err, ErrUnauthorized) || errors.Is(err, ErrForbidden) {
		t.Fatalf("网络错误不应误判为鉴权错误: %v", err)
	}
}
