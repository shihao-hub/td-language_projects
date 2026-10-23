# AutoHotkey 极速应用切换与 Toggle 自动化配置指南

## 1. 背景与核心痛点

随着日常工作流中常驻的开发工具越来越多（代码编辑器、数据库客户端、Git GUI、终端、飞书沟通等），在任务栏中频繁切换窗口通常会面临两个体验矛盾：

1. **鼠标大幅位移疲劳**：任务栏排列过长时，鼠标需要从屏幕左侧主力区频繁横跨大半个屏幕甩到右侧点击，手腕负荷大；如果全部排在左侧，又会导致图标挤压严重，辨识与瞄准成本升高。
2. **传统工具的局限**：
   - **Windows 原生 Alt+Tab**：基于最近使用时间（MRU）线性轮转，较少使用的工具会被挤到很靠后的位置，每次需要按很多次 Tab 才能切到。
   - **PowerToys Keyboard Manager（运行程序）**：虽然可以绑定快捷键，但其底层属于启动器逻辑——如果目标软件当前未开启，会强行启动软件；且对于 Windows Terminal 这类应用，每次调用都会重复弹出新窗口。

> **终极解法：“主力鼠标点选 + 次频键盘盲切”**  
> 利用 **AutoHotkey (v2)** 编写极简的后台守护脚本，实现纯左手单手快捷键（如 Alt + 1~3、Alt + W 等），做到**呼之即来、挥之即去（Toggle 机制）**。

---

## 2. 状态机与多窗口设计

脚本核心在于 ToggleApp 函数的状态流转：

- **软件未运行**：彻底无反应（保持静默，绝不自动启动程序）。
- **软件在后台**：第一次按快捷键瞬间置顶激活。
- **软件已在前台**：再次按相同快捷键自动最小化收起。
- **多窗口轮换**：若同一软件打开了多个窗口，依次轮换各个窗口，切完一轮后最小化收起。

### 多进程与多窗口处理说明：
- **浏览器/Electron应用的多子进程**：例如 Chrome、VS Code 会启动多个后台辅助进程。脚本使用 ahk_exe 配合窗口句柄操作，仅针对**具有可见界面（Top-Level Window）的主窗口**生效，不会受到底层多进程的影响。
- **同一软件多窗口（如多个终端或编辑器）**：首次按下激活最近使用的窗口；再次按下依次轮询切换其余子窗口；当所有窗口都查看完毕后，最后一次按下执行最小化隐藏。

---

## 3. 手动复现与安装步骤

### 第一步：安装 AutoHotkey v2

AutoHotkey 是 Windows 上最轻量级的键盘鼠标钩子与自动化工具（后台常驻内存仅 2~3MB）。

- **方式一（命令行一键安装）**：打开 PowerShell 执行 `winget install AutoHotkey.AutoHotkey`
- **方式二（官网下载）**：访问 [AutoHotkey 官网](https://www.autohotkey.com/)，下载并安装 **v2 版本**。

### 第二步：编写脚本并配置快捷键

在任意位置新建文件 app_switcher.ahk，粘贴以下完整代码：

```autohotkey
#Requires AutoHotkey v2.0
#SingleInstance Force

; ========================================================
; 核心架构设置：全局修饰键掩码安全声明（彻底根治 Sticky 粘滞升格）
; --------------------------------------------------------
; AHK 默认掩码键为 vk11sc01D (Left Control)！
; 极速按 Alt+Tab 时，AHK 自动注入的 Left Ctrl 会与用户的 Alt+Tab 发生物理碰撞，
; 导致 Windows 将其判定为 Ctrl+Alt+Tab，瞬间升格为原生“粘滞任务切换器”，表现为松手不关！
; 显式重定向为微软保留的未分配键码 vkE8，彻底杜绝 Ctrl 污染。
; ========================================================
A_MenuMaskKey := "vkE8"

; ========================================================
; 全局启动守卫初始化 (Auto-Execute)
; ========================================================
; Antigravity 启动自动最大化外挂 (250ms 极轻开销轮询)
SetTimer(AutoMaximizeAntigravity, 250)

; conhost 控制台黑框后台无感最小化守卫 (100ms 快速响应，零打扰零抢焦点)
SetTimer(AutoMinimizeConhost, 100)

; ========================================================
; 启动守卫：Antigravity 自动最大化核心函数
; 1. 软件未运行 -> 自动清空已处理列表
; 2. 软件运行且新窗口露面 -> 立即最大化该窗口，并记录 Hwnd
; 3. 用户手动还原窗口 -> 绝不重复强行拉大
; ========================================================
AutoMaximizeAntigravity() {
    static seenHwnds := Map()
    target := "ahk_exe Antigravity.exe"
    
    if !WinExist(target) {
        if (seenHwnds.Count > 0) {
            seenHwnds.Clear()
        }
        return
    }

    try {
        for hwnd in WinGetList(target) {
            if !seenHwnds.Has(hwnd) {
                style := WinGetStyle("ahk_id " hwnd)
                ; WS_VISIBLE (0x10000000)
                if (style & 0x10000000) {
                    title := WinGetTitle("ahk_id " hwnd)
                    ; 匹配主界面窗口（标题含 Antigravity 且可见）
                    if (title != "" && InStr(title, "Antigravity")) {
                        WinMaximize("ahk_id " hwnd)
                        seenHwnds[hwnd] := true
                    }
                }
            }
        }
    }
}

; ========================================================
; 启动守卫：conhost 控制台黑框后台无感最小化核心函数
; 1. 监测到新生成的 ConsoleWindowClass 窗口露面 (如 agy.exe, node 等拉起的黑框)
; 2. 露面瞬间自动执行 WinMinimize 最小化到任务栏，绝不遮挡当前界面
; 3. 记录已处理句柄指纹，用户后续自己从任务栏点开查看时不重复强行压制
; 4. 若抢走了输入焦点，瞬间将焦点归还给原前台窗口
; ========================================================
AutoMinimizeConhost() {
    static handledHwnds := Map()
    static lastUserWindow := 0
    target := "ahk_class ConsoleWindowClass"

    ; 实时捕获用户正常操作的前台窗口 (排除自身是控制台的情况)
    try {
        if (activeHwnd := WinActive("A")) {
            if (WinGetClass("ahk_id " activeHwnd) != "ConsoleWindowClass") {
                lastUserWindow := activeHwnd
            }
        }
    }

    if !WinExist(target) {
        if (handledHwnds.Count > 0) {
            handledHwnds.Clear()
        }
        return
    }

    try {
        for hwnd in WinGetList(target) {
            ; 只要遍历过，立刻登记指纹，杜绝重复检查
            if !handledHwnds.Has(hwnd) {
                handledHwnds[hwnd] := true
                
                ; WinGetMinMax: 0 = 正常, 1 = 最大化, -1 = 最小化
                minState := WinGetMinMax("ahk_id " hwnd)
                if (minState != -1) {
                    wasActive := (WinActive("A") = hwnd)
                    
                    ; 瞬间最小化到任务栏 (绝不挡住主屏幕)
                    WinMinimize("ahk_id " hwnd)

                    ; 若瞬时抢走了焦点，立即归还给用户原工作窗口，打字 100% 连贯
                    if (wasActive && lastUserWindow && WinExist("ahk_id " lastUserWindow)) {
                        WinActivate("ahk_id " lastUserWindow)
                    }
                }
            }
        }
    }
}

; ========================================================
; 窗口切换与最小化 Toggle 核心函数
; 1. 软件未运行 -> 彻底无反应（绝不自动启动）
; 2. 软件在后台 -> 激活并置顶到最前
; 3. 软件当前已在最前 -> 再次按下则最小化收起
; 4. 多窗口处理：若有多个窗口，依次轮换，最后一个最小化收起
; ========================================================
ToggleApp(exeName) {
    target := 'ahk_exe ' . exeName
    
    ; 1. 软件未运行：彻底无反应
    if !WinExist(target) {
        return
    }

    ; 2. 如果当前激活窗口正是该程序
    if WinActive(target) {
        winList := WinGetList(target)
        ; 单窗口：直接最小化收起
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
        ; 多窗口：依次轮换各个窗口，轮换完最后一个后最小化收起
        currentId := WinGetID('A')
        nextId := 0
        loop winList.Length {
            if (winList[A_Index] = currentId) {
                if (A_Index < winList.Length) {
                    nextId := winList[A_Index + 1]
                }
                break
            }
        }
        
        if (nextId) {
            WinActivate('ahk_id ' . nextId)
        } else {
            WinMinimize('ahk_id ' . currentId)
        }
    } else {
        ; 3. 软件在后台：立即置顶激活
        WinActivate(target)
    }
}

; ========================================================
; 文件资源管理器专用 Toggle 函数 (Explorer)
; 1. 窗口未运行 -> 启动打开资源管理器 (Run "explorer.exe")
; 2. 窗口在后台 -> 激活并置顶到最前
; 3. 窗口已在最前 -> 再次按下则最小化收起 (抽屉式 Toggle)
; 4. 多窗口处理 -> 依次轮换各个文件夹窗口，最后一个最小化收起
; 注意：不能使用 ahk_exe explorer.exe（会误匹配桌面与任务栏）
; 必须使用 ahk_class CabinetWClass 精准匹配文件夹窗口
; ========================================================
ToggleExplorer() {
    target := 'ahk_class CabinetWClass ahk_exe explorer.exe'
    
    ; 1. 未打开任何资源管理器窗口：直接启动打开
    if !WinExist(target) {
        Run('explorer.exe')
        return
    }

    ; 2. 如果当前激活窗口正是资源管理器
    if WinActive(target) {
        winList := WinGetList(target)
        ; 单窗口：直接最小化收起
        if (winList.Length <= 1) {
            WinMinimize('A')
            return
        }
        
        ; 多窗口：依次轮换各个窗口，轮换完最后一个后最小化收起
        currentId := WinGetID('A')
        nextId := 0
        loop winList.Length {
            if (winList[A_Index] = currentId) {
                if (A_Index < winList.Length) {
                    nextId := winList[A_Index + 1]
                }
                break
            }
        }
        
        if (nextId) {
            WinActivate('ahk_id ' . nextId)
        } else {
            WinMinimize('ahk_id ' . currentId)
        }
    } else {
        ; 3. 资源管理器在后台：立即置顶激活
        WinActivate(target)
    }
}

; ========================================================
; 从 PowerToys 读取并迁移的全部快捷键
; ========================================================

; Alt + 1 -> Zed
!1::ToggleApp('Zed.exe')

; Alt + 2 -> Sublime Merge
!2::ToggleApp('sublime_merge.exe')

; Alt + 3 -> Sublime Text
!3::ToggleApp('sublime_text.exe')

; Alt + A -> Antigravity
!a::ToggleApp('Antigravity.exe')

; ; Alt + C -> Cursor
; !c::ToggleApp('Cursor.exe')

; Alt + D -> DeepSeek Harness
!d::ToggleApp('DeepSeek Harness.exe')

; ; Alt + E -> IntelliJ IDEA
; !e::ToggleApp('idea64.exe')

; Alt + F -> 飞书
!f::ToggleApp('Feishu.exe')

; Alt + R -> Google Chrome
!r::ToggleApp('chrome.exe')

; ; Alt + V -> VS Code
; !v::ToggleApp('Code.exe')

; Alt + W -> Windows Terminal
!w::ToggleApp('WindowsTerminal.exe')

; Alt + X -> 资源管理器 (未开启则启动，已开启则盲切/Toggle)
!x::ToggleExplorer()

; ========================================================
; 全局应急解卡键安全网 (Emergency Reset)
; 遇到任何外部全屏游戏、XAML 死锁或第三方钩子导致修饰键卡死时，
; 按 Ctrl + Alt + F12 一键强行复位所有系统修饰键物理逻辑状态
; ========================================================
^!F12:: {
    Send("{Ctrl Up}{Alt Up}{Shift Up}{Win Up}")
    ToolTip("已强制复位所有修饰键状态 (Modifiers Cleared)")
    SetTimer(() => ToolTip(), -1500)
}

; ========================================================
; Chrome 专区：消除三点菜单抢焦点 & 豆包输入法右 Alt 语音透传
; --------------------------------------------------------
; 1. 豆包输入法仅使用【右侧 Alt (RAlt)】，必须维持 ~RAlt 透传；
; 2. 严禁在 ~LAlt Down 时盲发 SendInput！改用 ~LAlt Up + A_PriorKey 守卫；
; 3. 只有当用户确实【单按并松开 LAlt】且中途未触发任何组合键时才发 vkE8；
; 4. 当用户按 Alt+Tab 时，A_PriorKey 必定为 "Tab"，LAlt Up 分支直接短路，
;    输入流 100% 保持纯净物理信号，彻底消灭 Alt+Tab 界面卡滞死锁！
; ========================================================
#HotIf WinActive("ahk_exe chrome.exe")
; 豆包输入法语音录入透传与三点菜单消除
~RAlt::Send "{Blind}{vkE8}"

; 左 Alt 防菜单安全守卫 (单按释放才掩码，Alt+Tab 零干扰)
~LAlt Up:: {
    if (A_PriorKey = "LAlt") {
        Send("{Blind}{vkE8}")
    }
}
#HotIf


```

#### 快捷键映射表（已同步自系统配置）：

- **Alt + 1** -> Zed
- **Alt + 2** -> Sublime Merge
- **Alt + 3** -> Sublime Text
- **Alt + A** -> Antigravity (已配置)
- **Alt + D** -> DeepSeek Harness
- **Alt + F** -> 飞书
- **Alt + R** -> Google Chrome
- **Alt + W** -> Windows Terminal
- **Alt + X** -> 资源管理器 (未开启直接启动，已开启抽屉式 Toggle)
- **【启动守卫】** -> Antigravity 新窗口启动露面瞬间自动最大化（指纹记录防重复拉大）
- **【工程全景】** -> 详细架构与更多自动化能力参见全机知识库 [`095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md`](file:///C:/Users/29580/.gemini/config/skills/kb-engineering-notes/095_win_ahk_flow_Win非侵入式AHK启动外挂与极客桌面自动化全景.md)

> *提示：若需新增其他工具，只需在任务管理器“详细信息”页查看该软件的进程名（如 xxx.exe），仿照上方格式增加一行即可。*

### 第三步：配置开机静默自启

为了让脚本每次开机后自动生效，无需每次手动打开：

1. 按下快捷键 Win + R 呼出“运行”对话框；
2. 输入 shell:startup 并回车，系统将直接打开 Windows 的**启动文件夹**：  
   C:\Users\29580\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
3. 将写好的 app_switcher.ahk 文件复制或移动到此文件夹中；
4. 双击运行一次即可（右下角系统托盘会显示一个绿色的“H”图标，表示脚本正在后台静默守护）。

---

## 4. 常见问题与避坑指南

1. **与 PowerToys 键盘管理器的冲突**：  
   如果之前在 PowerToys 中配置过同名的快捷键（如 Alt + 1），PowerToys 会更早拦截全局热键，导致 AHK 脚本接收不到按键。  
   **处理方法**：打开 PowerToys -> 键盘管理器 -> 关闭该模块，或删除里面对应的重复映射项。
2. **Windows Terminal (wt.exe) 映射问题**：  
   命令行启动别名为 wt.exe，但实际运行在后台的主进程为 WindowsTerminal.exe。  
   在 AHK 的 ToggleApp 中必须传入实际进程名 WindowsTerminal.exe，方可精准捕获窗口并避免重复开新窗口。
3. **权限问题（以管理员身份运行的窗口）**：  
   如果某个软件（如以管理员权限开启的 PowerShell）处于最前台，标准权限运行的 AHK 可能无法在该窗口上拦截热键。  
   **处理方法**：若有此需求，可将 app_switcher.ahk 的快捷方式属性设置为“以管理员身份运行”。
