// Package opencode 实现 OpenCode Go（opencode.ai）套餐用量查询客户端。
// 接口已实测：GET https://opencode.ai/zen/go/v1/usage，
// Authorization: Bearer <API_KEY>（格式形如 oc_sk_...）。
// 响应体：{"usage":{"rolling":{"status","percent","resetsAt"},weekly,monthly}}；
// 401/403 返回 {"type":"error","error":{"type","message"}}。
package opencode

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// DefaultBaseURL OpenCode Go 官方端点前缀。
const DefaultBaseURL = "https://opencode.ai/zen/go/v1"

// EnvBaseURL 允许用环境变量覆盖基地址（测试注入 httptest、本地 Mock）。
// 空值时用 DefaultBaseURL。
const EnvBaseURL = "OPENCODE_GO_API_BASE"

// RequestTimeout 探测请求强制超时（NFR-3）。
const RequestTimeout = 10 * time.Second

// 哨兵错误：401 未授权 / 403 未订阅 Go 套餐。errors.Is 可判。
var (
	ErrUnauthorized = errors.New("API key 无效或未授权")
	ErrForbidden    = errors.New("需要 OpenCode Go 订阅")
)

// WindowUsage 单个额度窗口（滚动 / 周 / 月）。
type WindowUsage struct {
	Status   string `json:"status"`   // "ok" | "rate-limited"
	Percent  int    `json:"percent"`  // 0..100
	ResetsAt string `json:"resetsAt"` // ISO 8601 重置时间戳
}

// Usage 三窗口用量快照。
type Usage struct {
	Rolling WindowUsage `json:"rolling"`
	Weekly  WindowUsage `json:"weekly"`
	Monthly WindowUsage `json:"monthly"`
}

// HTTPError 上游返回非 2xx（401/403 已单独分类为哨兵错误）。
type HTTPError struct {
	Status int
	Body   string
}

func (e *HTTPError) Error() string {
	body := e.Body
	if len(body) > 300 {
		body = body[:300] + "..."
	}
	return fmt.Sprintf("上游 HTTP %d: %s", e.Status, body)
}

// Client 探测客户端。
type Client struct {
	BaseURL string
	Token   string
	HTTP    *http.Client // nil 时用 http.DefaultClient
}

// NewClient 构造客户端；baseURL 为空时用 DefaultBaseURL。
func NewClient(baseURL, token string) *Client {
	if strings.TrimSpace(baseURL) == "" {
		baseURL = DefaultBaseURL
	}
	return &Client{BaseURL: strings.TrimRight(baseURL, "/"), Token: token}
}

// envelope 成功响应壳。
type envelope struct {
	Usage *Usage `json:"usage"`
}

// errorEnvelope 错误响应壳（401/403 携带可读 message）。
type errorEnvelope struct {
	Error struct {
		Type    string `json:"type"`
		Message string `json:"message"`
	} `json:"error"`
}

// FetchUsage 查询当前用量；内部强制 RequestTimeout 超时预算。
// 401 → ErrUnauthorized、403 → ErrForbidden（errors.Is 可判），
// 其余非 2xx → *HTTPError；超时经 context.DeadlineExceeded 判定。
func (c *Client) FetchUsage(ctx context.Context) (*Usage, error) {
	ctx, cancel := context.WithTimeout(ctx, RequestTimeout)
	defer cancel()

	if c.HTTP == nil {
		c.HTTP = http.DefaultClient
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.BaseURL+"/usage", nil)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+c.Token)
	req.Header.Set("Accept", "application/json")

	resp, err := c.HTTP.Do(req)
	if err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			return nil, fmt.Errorf("请求超时: %w", err)
		}
		return nil, fmt.Errorf("请求用量接口失败: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %w", err)
	}
	switch {
	case resp.StatusCode == http.StatusUnauthorized:
		return nil, wrapSentinel(ErrUnauthorized, body)
	case resp.StatusCode == http.StatusForbidden:
		return nil, wrapSentinel(ErrForbidden, body)
	case resp.StatusCode < 200 || resp.StatusCode > 299:
		return nil, &HTTPError{Status: resp.StatusCode, Body: string(body)}
	}

	var env envelope
	if err := json.Unmarshal(body, &env); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}
	if env.Usage == nil {
		return nil, errors.New("响应缺少 usage 字段")
	}
	return env.Usage, nil
}

// wrapSentinel 把哨兵错误与上游 message 合并（无 message 时原样返回）。
func wrapSentinel(sentinel error, body []byte) error {
	var ee errorEnvelope
	if err := json.Unmarshal(body, &ee); err == nil && ee.Error.Message != "" {
		return fmt.Errorf("%w: %s", sentinel, ee.Error.Message)
	}
	return sentinel
}
