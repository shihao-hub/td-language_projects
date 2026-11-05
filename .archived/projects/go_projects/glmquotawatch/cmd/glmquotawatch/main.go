//go:build !cli

// GUI 通道入口（glmquotawatch-gui）：只负责把桌面工作台拉起来。
//
// 它不承担任何 CLI 语义：不管从哪里启动（双击、终端、快捷方式、带任意参数），
// 行为都是显示 GUI。唯一有意义的参数是 --hidden（开机自启注册的静默托盘模式，
// --tray 为同义别名），其余参数一律忽略。
// 需要命令行能力请改用 console 通道产物 glmquotawatch-cli.exe。
package main

import (
	"os"

	"glmquotawatch/internal/app"
)

func main() {
	defer app.Recover(true)

	hidden := false
	demo := false
	for _, arg := range os.Args[1:] {
		switch arg {
		case "--hidden", "--tray":
			hidden = true
		case "--demo":
			demo = true
		}
	}

	if err := app.LaunchGUI(hidden, demo); err != nil {
		app.Logf("LaunchGUI error: %v", err)
	}
}
