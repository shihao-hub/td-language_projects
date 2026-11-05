// opencode.go：OpenCode Go 套餐用量探测用例（与 GLM 链路完全解耦）。
// 配置落盘复用 store.Config.OpenCodeToken；探测走 internal/opencode 客户端；
// 视图组装（标签 / 倒计时 / 脱敏）只在本文件，CLI 与 GUI 绑定共用。
package service

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"strings"
	"time"

	"glmquotawatch/internal/opencode"
	"glmquotawatch/internal/quota"
	"glmquotawatch/internal/store"
)

// EnvOpenCodeAPIKey 本地配置为空时的临时回退环境变量（FR-2）。
const EnvOpenCodeAPIKey = "OPENCODE_API_KEY"

// openCodeTokenMinLen OpenCode token 最小长度（防呆；真实 key 形如 oc_sk_...）。
const openCodeTokenMinLen = 10

// OpenCodeConfigView OpenCode Go 配置视图（token 恒脱敏）。
type OpenCodeConfigView struct {
	Token    string `json:"token"`     // 脱敏后的展示形态（来源为本地配置；环境变量回退时为空）
	HasToken bool   `json:"has_token"` // 本地配置或环境变量任一有值即为 true
	Dir      string `json:"dir"`
}

// OpenCodeWindowView 单个额度窗口（rolling / weekly / monthly）。
type OpenCodeWindowView struct {
	Name     string `json:"name"`      // "rolling" | "weekly" | "monthly"
	Label    string `json:"label"`     // "滑动短期窗口" | "本周窗口" | "本月窗口"
	Status   string `json:"status"`    // "ok" | "rate-limited"
	Percent  int    `json:"percent"`   // 0..100
	ResetsAt string `json:"resets_at"` // ISO 8601
	ResetIn  string `json:"reset_in"`  // 人读倒计时，如 "3h25m"
}

// OpenCodeStatusView 一次探测的完整视图。
type OpenCodeStatusView struct {
	SampledAt string               `json:"sampled_at"`
	Windows   []OpenCodeWindowView `json:"windows"`
}

// openCodeWindowSpec 窗口固定展示顺序与中文标签。
type openCodeWindowSpec struct {
	name  string
	label string
}

var openCodeWindowSpecs = []openCodeWindowSpec{
	{name: "rolling", label: "滑动短期窗口"},
	{name: "weekly", label: "本周窗口"},
	{name: "monthly", label: "本月窗口"},
}

// GetOpenCodeConfig 返回 OpenCode Go 配置视图（脱敏）。
func (s *Service) GetOpenCodeConfig() OpenCodeConfigView {
	cfg, err := s.st.LoadConfig()
	if err != nil {
		// 配置损坏时按空配置降级展示（仍反映环境变量回退可用性）
		return OpenCodeConfigView{
			HasToken: strings.TrimSpace(os.Getenv(EnvOpenCodeAPIKey)) != "",
			Dir:      s.st.Dir(),
		}
	}
	return s.openCodeView(cfg)
}

// SetOpenCodeToken 设置 OpenCode Go API key（trim 后长度须 ≥ openCodeTokenMinLen）。
func (s *Service) SetOpenCodeToken(token string) (OpenCodeConfigView, error) {
	token = strings.TrimSpace(token)
	if len(token) < openCodeTokenMinLen {
		return OpenCodeConfigView{}, errf("bad_args", "opencode token 长度须 ≥ %d，当前 %d", openCodeTokenMinLen, len(token))
	}
	cfg, err := s.st.LoadConfig()
	if err != nil {
		return OpenCodeConfigView{}, errf("internal", "读取配置失败: %v", err)
	}
	cfg.OpenCodeToken = token
	if err := s.st.SaveConfig(cfg); err != nil {
		return OpenCodeConfigView{}, errf("internal", "保存配置失败: %v", err)
	}
	return s.openCodeView(cfg), nil
}

// RemoveOpenCodeToken 清除 OpenCode Go API key；幂等（未配置时也返回成功）。
func (s *Service) RemoveOpenCodeToken() (OpenCodeConfigView, error) {
	cfg, err := s.st.LoadConfig()
	if err != nil {
		return OpenCodeConfigView{}, errf("internal", "读取配置失败: %v", err)
	}
	cfg.OpenCodeToken = ""
	if err := s.st.SaveConfig(cfg); err != nil {
		return OpenCodeConfigView{}, errf("internal", "保存配置失败: %v", err)
	}
	return s.openCodeView(cfg), nil
}

// SampleOpenCodeOnce 立即探测一次 OpenCode Go 用量（落历史、不发通知）。
// Token 解析：本地配置优先，为空时回退环境变量 OPENCODE_API_KEY。
func (s *Service) SampleOpenCodeOnce(ctx context.Context) (OpenCodeStatusView, error) {
	token, err := s.openCodeToken()
	if err != nil {
		return OpenCodeStatusView{}, err
	}
	if token == "" {
		return OpenCodeStatusView{}, errf("no_token", "尚未配置 OpenCode Go API key，请先运行 opencode token set 或在设置页录入")
	}
	client := opencode.NewClient(s.openCodeBaseURL, token)
	usage, err := client.FetchUsage(ctx)
	if err != nil {
		return OpenCodeStatusView{}, mapOpenCodeError(err)
	}
	now := time.Now()
	if raw, jerr := json.Marshal(usage); jerr == nil {
		_, _ = s.st.AppendOpenCodeSample(now, raw)
	}
	return buildOpenCodeStatusView(usage, now), nil
}

// HasOpenCodeToken 是否存在可用 token（本地配置或环境变量）。
func (s *Service) HasOpenCodeToken() bool {
	t, _ := s.openCodeToken()
	return t != ""
}

func (s *Service) openCodeView(cfg store.Config) OpenCodeConfigView {
	hasEnv := strings.TrimSpace(os.Getenv(EnvOpenCodeAPIKey)) != ""
	return OpenCodeConfigView{
		Token:    MaskOpenCodeToken(cfg.OpenCodeToken),
		HasToken: cfg.OpenCodeToken != "" || hasEnv,
		Dir:      s.st.Dir(),
	}
}

// openCodeToken 返回生效 token：本地配置优先，为空时取环境变量（均 trim）。
func (s *Service) openCodeToken() (string, error) {
	cfg, err := s.st.LoadConfig()
	if err != nil {
		return "", errf("internal", "读取配置失败: %v", err)
	}
	if t := strings.TrimSpace(cfg.OpenCodeToken); t != "" {
		return t, nil
	}
	return strings.TrimSpace(os.Getenv(EnvOpenCodeAPIKey)), nil
}

// MaskOpenCodeToken 脱敏：前 4 后 4 中间省略（FR-2）；过短全部打星。
func MaskOpenCodeToken(t string) string {
	if t == "" {
		return ""
	}
	if len(t) <= 12 {
		return strings.Repeat("*", len(t))
	}
	return t[:4] + "…" + t[len(t)-4:]
}

// buildOpenCodeStatusView 组装三窗口视图（固定 rolling → weekly → monthly）。
func buildOpenCodeStatusView(u *opencode.Usage, now time.Time) OpenCodeStatusView {
	windows := map[string]opencode.WindowUsage{
		"rolling": u.Rolling,
		"weekly":  u.Weekly,
		"monthly": u.Monthly,
	}
	v := OpenCodeStatusView{
		SampledAt: now.Format(time.RFC3339),
		Windows:   []OpenCodeWindowView{},
	}
	for _, spec := range openCodeWindowSpecs {
		w := windows[spec.name]
		win := OpenCodeWindowView{
			Name:     spec.name,
			Label:    spec.label,
			Status:   w.Status,
			Percent:  w.Percent,
			ResetsAt: w.ResetsAt,
		}
		if t, perr := time.Parse(time.RFC3339, w.ResetsAt); perr == nil {
			win.ResetIn = quota.FormatResetIn(t.Sub(now))
		}
		v.Windows = append(v.Windows, win)
	}
	return v
}

// mapOpenCodeError 把客户端错误映射为业务错误码（FR-2/NFR-3 分类）。
func mapOpenCodeError(err error) error {
	switch {
	case errors.Is(err, opencode.ErrUnauthorized):
		return errf("auth_error", "%v", err)
	case errors.Is(err, opencode.ErrForbidden):
		return errf("entitlement_error", "%v", err)
	case errors.Is(err, context.DeadlineExceeded):
		return errf("timeout", "探测 OpenCode Go 超时，请稍后重试")
	}
	var he *opencode.HTTPError
	if errors.As(err, &he) {
		return errf("api_error", "%v", he)
	}
	return errf("network_error", "探测 OpenCode Go 失败: %v", err)
}
