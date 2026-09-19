---
name: aoci-setup
description: AOCI-CODE（AI Agent 仓库认知索引 MCP）的下载、安装与全局配置手册：发行包下载与 SHA256 校验、二进制落位、Agent 的 MCP 全局配置、版本升级与卸载。当用户说"装 AOCI"、"配置 aoci-code"、"新机器接入仓库认知索引"、"升级/卸载 AOCI"、"aoci MCP 没起来要重装"时使用。
---

# GUIDE-AOCI-SETUP

> AOCI-CODE（AI Agent 仓库认知索引 MCP）的下载、安装与三工具全局配置手册。
> 适用范围：本仓库（`language_projects`）及所有子项目；当前采用**全局配置**（非项目级）。

---

## 1. AOCI-CODE 是什么

[AOCI-CODE](https://github.com/aoci-spec/aoci-code) 把代码 + 数据库结构蒸馏成一份持久的、受治理的结构化文本索引（`aoci*.txt`，可进 Git），通过 stdio MCP 向 AI Agent 暴露 9 个工具（`aoci_rules` / `aoci_overview` / `aoci_get_entries` / `aoci_search` / `aoci_maintain` / `aoci_update_entry` / `aoci_remove_entry` / `aoci_header` / `aoci_report`），让 AI 在动手前对系统有版本化、可追溯的理解。

- Go 单二进制，CGO-free，本地运行，无云端依赖
- 许可：FSL-1.1-MIT；当前版本：`v0.1.0-rc14`

---

## 2. 下载与安装（Windows）

### 2.1 下载发行包并校验 SHA256

```powershell
$Tag = "v0.1.0-rc14"   # 升级时改成新版本号即可
$Tmp = "$env:TEMP\aoci-install"
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

gh release download $Tag --repo aoci-spec/aoci-code `
  --pattern "aoci_$($Tag.Substring(1))_windows_amd64.zip" `
  --pattern "SHA256SUMS" --dir $Tmp --clobber

# 校验（校验不过会抛异常中止）
$Archive = "aoci_$($Tag.Substring(1))_windows_amd64.zip"
$Expected = ((Select-String -Path "$Tmp\SHA256SUMS" -Pattern "  $([regex]::Escape($Archive))$").Line -split '\s+')[0]
$Actual = (Get-FileHash -Algorithm SHA256 "$Tmp\$Archive").Hash.ToLowerInvariant()
if ($Actual -ne $Expected) { throw "archive checksum mismatch" }
"checksum OK: $Actual"
```

### 2.2 解压到稳定路径并加入用户 PATH

```powershell
$Dest = "$env:LOCALAPPDATA\Programs\aoci"
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Expand-Archive -Path "$Tmp\$Archive" -DestinationPath $Dest -Force

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$Dest*") {
  [Environment]::SetEnvironmentVariable("Path", "$UserPath;$Dest", "User")
}

# 新开一个终端后验证
aoci --version
# 期望输出：aoci version 0.1.0-rc14 (commit ..., built ...)
```

> `aoci.exe` 位于 `$Dest`，全局 MCP 配置一律写这个绝对路径（避免 PATH 变动后选错二进制）。

---

## 3. 三工具全局配置（根目录级别，非项目级）

统一约定：

| 项 | 值 |
|---|---|
| 二进制绝对路径 | `C:\Users\29580\AppData\Local\Programs\aoci\aoci.exe` |
| 服务仓库（`--repo`） | `D:\Users\language_projects`（父仓库根） |
| 启动命令 | `<exe> --repo D:\Users\language_projects mcp` |

> AOCI 的 MCP server 是 per-repo 的：全局配置里 `--repo` 固定指向父仓库，
> 三个工具在任何目录打开时都连接**同一个**父仓库索引。

### 3.1 OpenCode — `~/.config/opencode/opencode.json`

在全局配置的 `"mcp"` 对象中加入（保留其余字段不动）：

```json
{
  "mcp": {
    "aoci": {
      "type": "local",
      "command": [
        "C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe",
        "--repo",
        "D:/Users/language_projects",
        "mcp"
      ],
      "enabled": true
    }
  }
}
```

保存后**重启 opencode**（配置不热加载）。会话中出现 `aoci_*` 前缀工具即生效。

### 3.2 Claude Code — 用户级（`~/.claude.json`）

推荐用官方 CLI 写入。**PowerShell 5.1 的坑**：`--` 分隔符会被吞、`add-json` 的内层双引号会丢，直接跑会报 `unknown option '--repo'` 或 `Invalid input`。绕过方式（node 直写，先备份）：

```powershell
Copy-Item "$env:USERPROFILE\.claude.json" "$env:TEMP\claude.json.bak" -Force
node -e "const fs=require('fs');const p=process.env.USERPROFILE+'\\.claude.json';const j=JSON.parse(fs.readFileSync(p,'utf8'));j.mcpServers=j.mcpServers||{};j.mcpServers.aoci={type:'stdio',command:'C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe',args:['--repo','D:/Users/language_projects','mcp']};fs.writeFileSync(p,JSON.stringify(j,null,2));"

# 验证（期望 Status: √ Connected）
claude mcp get aoci
```

在 bash / cmd 下则可直接用一行命令：

```bash
claude mcp add-json aoci '{"type":"stdio","command":"C:/Users/29580/AppData/Local/Programs/aoci/aoci.exe","args":["--repo","D:/Users/language_projects","mcp"]}' --scope user
```

### 3.3 Codex — `~/.codex/config.toml`

在全局 `config.toml` 中追加（保留已有 `[mcp_servers.*]`）：

```toml
[mcp_servers.aoci]
command = 'C:\Users\29580\AppData\Local\Programs\aoci\aoci.exe'
args = ["--repo", "D:\Users\language_projects", "mcp"]
```

重启 Codex 后生效（Codex 全局配置不需要项目信任弹窗；项目级 `.codex/config.toml` 才需要）。

---

## 4. 仓库侧资产（已就绪，勿删）

父仓库内以下文件是 AOCI 的**正式索引资产**（MCP server 服务的就是它们）：

| 文件/目录 | 作用 |
|---|---|
| `aoci.txt` | Root：声明 CognitionSet 组成（入口） |
| `aoci.meta.txt` | Meta：标签字典、FRAS 规则、配额 |
| `aoci.code.txt` | Code Volume：代码对象条目（当前为骨架，0 条目） |
| `.aoci/` | 分层：`baseline.json`（漂移基准）、`config.json`（治理配置）、`curation.json` 为治理资产，**建议入库**（`.aoci/.gitignore` 白名单已放开，`git add .aoci` 自动只加白名单文件）；`ledger.jsonl`、`verify_history/`、`hooks/` 为本机运行时流水，默认忽略不入库 |
| `.gitattributes` | 保证各 checkout 行尾一致 |
| `AGENTS.md` 末尾 aoci 块 | AI 会话进入本仓库的运行契约（勿手改） |

首次建立 Baseline 已执行：`aoci --repo D:\Users\language_projects scan`（471 files）。

---

## 5. 日常使用与维护

```powershell
# 仓库文件变动后重建/对齐 Baseline
aoci --repo D:\Users\language_projects scan

# 漂移检查（Missing / Orphan / Stale / Unbaselined）与治理门
aoci --repo D:\Users\language_projects verify --json
aoci --repo D:\Users\language_projects check --json

# 本地只读面板（浏览器查看索引全文、覆盖率、压缩率；仅绑定 loopback）
aoci --repo D:\Users\language_projects ui --detach

# 集成与仓库自检
aoci --repo D:\Users\language_projects doctor
aoci --repo D:\Users\language_projects capabilities
```

日常维护**通过 MCP 工具完成**（AI 会话内调用 `aoci_maintain` 等），不要手工编辑 `aoci*.txt`。
AI 会话首次进入仓库时的标准流程：先 `aoci_rules`，再 `aoci_overview` 建立完整认知。

### 子项目想独立建索引？（项目级，对照参考）

全局配置已固定 `--repo` 指向父仓库。若某个子项目要维护**自己独立**的索引，需改用项目级：
在项目根执行 `aoci init --agent <host>` + `aoci scan`，并把该 host 的 MCP 配置从全局改为项目级（或单独一条不同名的 server，`--repo` 指向子项目）。两套并存时注意 server 命名不要都叫 `aoci`。

---

## 6. 升级与卸载

```powershell
# 升级：重跑第 2 节，换新 $Tag 下载覆盖 $Dest 即可（配置无需改动，路径不变）
# 查看当前版本
aoci --version

# 卸载三工具配置
claude mcp remove aoci -s user                # Claude Code
# OpenCode：删掉 ~/.config/opencode/opencode.json 里 mcp.aoci 段
# Codex：删掉 ~/.codex/config.toml 里 [mcp_servers.aoci] 段

# 卸载二进制与仓库资产
Remove-Item "$env:LOCALAPPDATA\Programs\aoci" -Recurse -Force
# （可选）删除仓库内 aoci*.txt / .aoci/ / .gitattributes 及 AGENTS.md 的 aoci 块
```

---

## 7. 排错速查

| 症状 | 处理 |
|---|---|
| opencode 会话里没有 `aoci_*` 工具 | 配置不热加载，退出并重启 opencode |
| `claude mcp get aoci` 显示连接失败 | 先手动跑 `aoci --repo D:\Users\language_projects mcp` 看 stderr 报错 |
| doctor 报 Baseline missing | 执行 `aoci --repo . scan` |
| AGENTS.md 的 aoci 块丢失 | 仓库资产被误删，重跑 `aoci init`（幂等，不覆盖已有索引） |
| 升级后 host 起了旧版本 | 检查配置里写的是绝对路径而非 PATH 查找；确认 `$Dest\aoci.exe --version` |
