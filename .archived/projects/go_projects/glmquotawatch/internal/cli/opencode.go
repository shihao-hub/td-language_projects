// opencode.go：OpenCode Go 独立命令组（与 GLM 命令完全解耦、互不影响）。
// 恒 JSON 信封输出，语义与 GLM 命令组一致：解析 → service → 信封 → 退出码。
package cli

import (
	"context"
	"time"

	"github.com/spf13/cobra"
)

// openCodeStatusTimeout CLI 侧探测预算（客户端内部另有 10s 强制超时）。
const openCodeStatusTimeout = 15 * time.Second

// opencodeCmd 顶级子命令组：token（set/show/remove）与 status。
func opencodeCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "opencode",
		Short: "OpenCode Go 套餐用量探测（与 GLM 命令完全独立）",
	}
	cmd.AddCommand(openCodeTokenCmd(), openCodeStatusCmd())
	return cmd
}

func openCodeTokenCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "token",
		Short: "配置 OpenCode Go API key",
	}
	set := &cobra.Command{
		Use:   "set <key>",
		Short: "设置 OpenCode Go API key（形如 oc_sk_...，长度 ≥ 10）",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			svc, err := mustService()
			if err != nil {
				return outErr(cmd, err)
			}
			view, err := svc.SetOpenCodeToken(args[0])
			if err != nil {
				return outErr(cmd, err)
			}
			return outOK(cmd, view)
		},
	}
	show := &cobra.Command{
		Use:   "show",
		Short: "查看 OpenCode Go API key（脱敏）及配置状态",
		RunE: func(cmd *cobra.Command, args []string) error {
			svc, err := mustService()
			if err != nil {
				return outErr(cmd, err)
			}
			return outOK(cmd, svc.GetOpenCodeConfig())
		},
	}
	remove := &cobra.Command{
		Use:   "remove",
		Short: "清除 OpenCode Go API key（幂等）",
		RunE: func(cmd *cobra.Command, args []string) error {
			svc, err := mustService()
			if err != nil {
				return outErr(cmd, err)
			}
			view, err := svc.RemoveOpenCodeToken()
			if err != nil {
				return outErr(cmd, err)
			}
			return outOK(cmd, view)
		},
	}
	cmd.AddCommand(set, show, remove)
	return cmd
}

func openCodeStatusCmd() *cobra.Command {
	return &cobra.Command{
		Use:   "status",
		Short: "立即探测一次 OpenCode Go 用量（滑动 / 周 / 月三窗口）",
		RunE: func(cmd *cobra.Command, args []string) error {
			svc, err := mustService()
			if err != nil {
				return outErr(cmd, err)
			}
			ctx, cancel := context.WithTimeout(cmd.Context(), openCodeStatusTimeout)
			defer cancel()
			view, err := svc.SampleOpenCodeOnce(ctx)
			if err != nil {
				return outErr(cmd, err)
			}
			return outOK(cmd, view)
		},
	}
}
