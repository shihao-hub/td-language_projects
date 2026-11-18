# TaskbarGuard 快捷方式精准过滤与只读基线备份恢复实施计划

## 一、需求背景与问题定义
在执行 `taskbarguard run wt --style titanium` 时暴露出三处重大安全与体验隐患：
1. **别名粗暴映射**：`main.go` 将 `wt` / `terminal` 硬映射到 `powershell`，终端宿主与 Shell 解释器概念混淆。
2. **快捷方式模糊误伤**：补丁脚本以包含 `terminal` / `powershell` 为关键词遍历开始菜单和桌面，误伤第三方独立工具（`XTerminal`）、系统内置 PowerShell 5.1 以及已卸载软件的残留死链（Anaconda）。
3. **零备份与重复执行污染**：无初始图标与二进制备份，重复执行时极易将已修改状态误当成原始状态覆写备份。

## 二、架构设计与实施步骤

### 1. 快捷方式精准目标匹配与死链防御 (`scripts/powershell/patch_powershell_icon.py`)
- **废弃文件名模糊搜索**：彻底移除 `keywords = ["terminal", "powershell", ...]` 文件名匹配逻辑。
- **改走 TargetPath 严格目标校验**：
  - 仅处理 `TargetPath` 规范化结尾命中目标的快捷方式：
    - Windows Terminal：`\wt.exe` 或 `\windowsterminal.exe`
    - PowerShell 7：`\pwsh.exe`
  - 严禁触碰 `XTerminal.exe`、系统自带 `powershell.exe`（v5.1）等无关应用。
- **死链自动识别与跳过**：检测到 `TargetPath` 不存在或指向已卸载程序时，直接跳过并记录告警，严禁修改。

### 2. 只读基线备份与防重入机制 (`%APPDATA%\language_projects\taskbarguard\state.json`)
- **遵循数据存放强约束**：状态与备份目录统一落盘于 `%APPDATA%\language_projects\taskbarguard\`。
- **快捷方式初态锁定（Pristine Lock）**：
  - 首次纳管快捷方式时，记录其真实原生 `pristine_icon` 与 `created_by_guard` 标识。
  - **重复执行防污染铁律**：若记录已存在，仅更新 `current_icon`，**绝对禁止覆写 `pristine_icon`**。
- **PE EXE 纯净备份**：
  - 首次注入前将原版复制至 `backups/<app>.pristine.exe`；
  - 重复执行检测当前 EXE 签名或状态，已有备份时绝不二次覆写备份文件。

### 3. 一键回退命令 (`taskbarguard revert [APP]`)
- **Python 补丁层**：新增 `--revert` 参数，一键读取 `state.json` 中的 `pristine_icon` 还原快捷方式，若由守卫自动新建则执行安全移除；通过备份还原 EXE。
- **Go CLI 调度层**：`main.go` 增加 `revert` 子命令与契约导出，支持一键撤销并广播刷新外壳。

### 4. 测试与验证
- 补充单元测试：测试 `revert` 命令、参数解析、只读初态不变式。
- 实机演练：验证精准匹配、防重入备份、修改、一键回退全流程。

### 未决问题与阻塞确认清单
- [x] 是否将 `wt`（Windows Terminal）与 `powershell`（PowerShell 7）物理拆分：用户确认仅使用 wt，彻底独立出 `scripts/wt/` 专属应用模块，`main.go` 别名 `wt`/`terminal` 专属于 `wt`，只识别 `wt.exe`/`WindowsTerminal.exe`，不再与 powershell 产生任何关联。
- [x] 任务栏自动创建的 `Windows Terminal.lnk` 在 `revert` 时是否默认直接清理删除：是，用户确认自动删除守卫新建的快捷方式，彻底恢复系统原生任务栏状态。

## 三、实施成果与勾选清单
- [x] **创建 Windows Terminal 专属模块**：`scripts/wt/` 独立承载专属图标与补丁脚本，彻底解除与 powershell 的混淆。
- [x] **废除文件名模糊匹配**：改为单次 PowerShell 批量检索 TargetPath（仅匹配 `wt.exe`/`windowsterminal.exe`），彻底根除对 XTerminal、PowerShell 5.1 与死链快捷方式的误伤。
- [x] **只读基线备份与防重入机制**：`state.json` 首次纳管时锁定 `pristine_icon` 与 `created_by_guard`，重复执行换肤时绝对禁止覆写初态备份。
- [x] **一键撤销恢复命令**：Go CLI 调度层新增 `taskbarguard revert [APP]`，支持自动移除新建项并恢复原生图标。
- [x] **自动化测试与构建通过**：新增并更新 12 个单元测试全部通过，`build.py --dev` 编译顺利。

