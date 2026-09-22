<#
.SYNOPSIS
    检测 Google Antigravity ACP 上游 Registry 版本与 GitHub 社区仓库动态
.PARAMETER OnlyRegistry
    仅检测官方 ACP Registry 版本，不调用 GitHub 搜索 API
.PARAMETER Query
    自定义 GitHub 搜索关键词（默认为 "antigravity-acp OR agy-acp"）
#>
param(
    [switch]$OnlyRegistry,
    [string]$Query = "antigravity acp"
)

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       Google Antigravity ACP 上游监控检测        " -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# ----------------------------------------------------
# 1. 检查官方 ACP Registry 与本地已安装版本
# ----------------------------------------------------
Write-Host "[1/2] 正在检查 ACP 官方注册表与本地版本..." -ForegroundColor Yellow

$localInstalledVersion = "未知(未安装)"
$localInstalledDir = "$env:LOCALAPPDATA\Zed\external_agents\registry\antigravity-acp"
if (Test-Path $localInstalledDir) {
    $dirs = Get-ChildItem -Path $localInstalledDir -Directory -Filter "v_*"
    if ($dirs.Count -gt 0) {
        $firstDir = $dirs[0].Name
        if ($firstDir -match '^v_([^_]+)_') {
            $localInstalledVersion = $matches[1]
        } else {
            $localInstalledVersion = $firstDir
        }
    }
}

$registryUrl = "https://cdn.agentclientprotocol.com/registry/v1/latest/registry.json"
$remoteVersion = $null
$remoteDist = $null

try {
    $resp = Invoke-RestMethod -Uri $registryUrl -Method Get -TimeoutSec 10 -Headers @{ "User-Agent" = "PowerShell-AGY-Checker" }
    $agent = $resp.agents | Where-Object { $_.id -eq "antigravity-acp" }
    if ($agent) {
        $remoteVersion = $agent.version
        $remoteDist = $agent.distribution.binary."windows-x86_64".archive
    }
} catch {
    Write-Warning "连接官方 ACP Registry 失败: $($_.Exception.Message)"
}

Write-Host "  * 本地已安装版本 : $localInstalledVersion" -ForegroundColor White
if ($remoteVersion) {
    Write-Host "  * 上游 Registry 版本: $remoteVersion" -ForegroundColor White
    if ($remoteDist) {
        Write-Host "  * 上游分发包 URL  : $remoteDist" -ForegroundColor Gray
    }
    if ($localInstalledVersion -eq $remoteVersion) {
        Write-Host "  ✔ 当前本地版本与上游 Registry 一致 (最新版)。" -ForegroundColor Green
    } else {
        Write-Host "  ▲ 检测到版本差异！本地: $localInstalledVersion -> 上游: $remoteVersion" -ForegroundColor Magenta
        Write-Host "    可在 Zed 命令面板运行 'agent: update' 或重启 Zed 触发自动升级。" -ForegroundColor Yellow
    }
} else {
    Write-Host "  * 未能获取到远端版本。" -ForegroundColor Red
}

Write-Host ""

if ($OnlyRegistry) {
    exit 0
}

# ----------------------------------------------------
# 2. 检索 GitHub 社区活跃仓库
# ----------------------------------------------------
Write-Host "[2/2] 正在搜索 GitHub 社区仓库 (关键词: '$Query')..." -ForegroundColor Yellow

$searchUrl = "https://api.github.com/search/repositories?q=$([Uri]::EscapeDataString($Query))&sort=updated&order=desc&per_page=6"
try {
    $headers = @{
        "User-Agent" = "PowerShell-AGY-Checker"
        "Accept"     = "application/vnd.github.v3+json"
    }
    $ghResp = Invoke-RestMethod -Uri $searchUrl -Method Get -Headers $headers -TimeoutSec 10
    $items = $ghResp.items
    if ($items -and $items.Count -gt 0) {
        Write-Host "  找到 $($items.Count) 个相关仓库：" -ForegroundColor White
        Write-Host ""
        foreach ($repo in $items) {
            $updated = ([DateTime]$repo.updated_at).ToString("yyyy-MM-dd")
            Write-Host "  - $($repo.full_name)" -ForegroundColor Cyan -NoNewline
            Write-Host " (⭐ $($repo.stargazers_count) | 更新于 $updated)" -ForegroundColor Gray
            if ($repo.description) {
                Write-Host "    $($repo.description)" -ForegroundColor DarkGray
            }
            Write-Host "    $($repo.html_url)" -ForegroundColor DarkCyan
        }
    } else {
        Write-Host "  未找到匹配的相关仓库。" -ForegroundColor Gray
    }
} catch {
    Write-Warning "调用 GitHub Search API 失败（可能触发未登录速率限制）: $($_.Exception.Message)"
}

Write-Host ""
Write-Host "检测完成。" -ForegroundColor Green