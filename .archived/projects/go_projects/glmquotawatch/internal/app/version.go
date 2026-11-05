package app

import "glmquotawatch/internal/env"

var (
	// Version 编译期通过 -ldflags "-X glmquotawatch/internal/app.Version=..." 注入
	Version = "dev"
	// BuildMode 编译期通过 -ldflags "-X glmquotawatch/internal/app.BuildMode=release" 注入
	BuildMode = "dev"
)

// IsRelease 返回当前二进制是否为正式发行版。
// 单一真源：优先认编译期注入的 BuildMode == "release"，兼顾 !env.IsDev()。
func IsRelease() bool {
	return BuildMode == "release" || (!env.IsDev() && BuildMode != "dev")
}
