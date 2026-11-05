package frontend

import "embed"

// Dist 嵌入前端构建产物（HTML/CSS/JS）。
//
//go:embed all:dist
var Dist embed.FS
