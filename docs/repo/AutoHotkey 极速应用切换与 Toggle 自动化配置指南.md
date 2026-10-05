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
; 从 PowerToys 读取并迁移的全部快捷键
; ========================================================

; Alt + 1 -> Zed
!1::ToggleApp('Zed.exe')

; Alt + 2 -> Sublime Merge
!2::ToggleApp('sublime_merge.exe')

; Alt + 3 -> Sublime Text
!3::ToggleApp('sublime_text.exe')

; Alt + C -> Cursor
!c::ToggleApp('Cursor.exe')

; Alt + D -> DeepSeek Harness
!d::ToggleApp('DeepSeek Harness.exe')

; Alt + F -> 飞书
!f::ToggleApp('Feishu.exe')

; Alt + V -> VS Code
!v::ToggleApp('Code.exe')

; Alt + W -> Windows Terminal
!w::ToggleApp('WindowsTerminal.exe')
```

#### 快捷键映射表（已同步自系统配置）：

- Alt + 1 -> Zed
- Alt + 2 -> Sublime Merge
- Alt + 3 -> Sublime Text
- Alt + C -> Cursor
- Alt + D -> DeepSeek Harness
- Alt + F -> 飞书
- Alt + V -> VS Code
- Alt + W -> Windows Terminal

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
