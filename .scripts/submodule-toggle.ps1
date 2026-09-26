<#
.SYNOPSIS
    语言子模块临时注销（deinit）/ 恢复（restore）一键脚本，带前置检查与只读体检

.DESCRIPTION
    适用场景：本仓库暂时"停更"的子模块（如 native_projects / rust_projects），
    背景与原理见 docs/repo/Git 子模块临时注销（native、rust）.md。

    三个动作（-Action）：
      status   只读体检：输出各子模块注销状态、gitlink、工作区与未推送情况，不做任何修改
      deinit   本地注销：git submodule deinit -f，不改 .gitmodules、不删
               .git/modules/<name>、不动远端，父仓库无需提交；任一目标存在未提交
               改动或未推送提交时整批拒绝，一个都不动
      restore  本地恢复：git submodule update --init 并切到 .gitmodules 声明的跟踪分支；
               若 index 中 gitlink 已被静默移除（native_projects 的历史遗留），
               自动回溯最近一个包含 gitlink 的历史提交重建之，并在结束时提示
               需要提交父仓库指针

    注销（deinit）前置检查规则：
      1. 已注销 -> 跳过（幂等），不计失败；
      2. 子模块工作区不干净（含未跟踪文件）-> 拒绝；
      3. 子模块存在任何远端都不可达的提交（未推送）-> 拒绝；
      4. 存在 stash 仅提示不阻断（stash 保存在 .git/modules/<name>，deinit 不丢失）。

    安全边界：不触碰远端；不改 .gitmodules；绝不自动 commit / push，
    restore 结束后只打印建议命令。
    退出码：0=成功（含幂等跳过）；1=参数/校验错误；2=前置检查不通过；3=执行失败。

.EXAMPLE
    .\.scripts\submodule-toggle.ps1 -Action status -Name native_projects,rust_projects
    只读体检两个子模块的当前状态

.EXAMPLE
    .\.scripts\submodule-toggle.ps1 -Action deinit -Name native_projects,rust_projects
    通过前置检查后本地注销；已注销的输出跳过提示

.EXAMPLE
    .\.scripts\submodule-toggle.ps1 -Action restore -Name rust_projects
    恢复子模块并切换到跟踪分支

.NOTES
    必须在本父仓库根目录结构下运行（脚本按自身位置定位仓库根）；
    依赖 git >= 2.22（branch --show-current）；兼容 Windows PowerShell 5.1+。
#>
# ============================ AI agent 速读 ============================
# 用途：语言子模块临时注销/恢复（本地 deinit / restore），不改 .gitmodules、不动远端
# 三动作：status=只读体检；deinit=本地注销（有未提交/未推送即整批拒绝）；restore=恢复+切跟踪分支
# 示例：.\.scripts\submodule-toggle.ps1 -Action status -Name native_projects,rust_projects
# 边界：不自动 commit/push；native 的 gitlink 重建完成后需按提示提交父仓指针
# =======================================================================

param(
    [string]$Action,
    [string[]]$Name
)

$ErrorActionPreference = 'Stop'

# ---------------- 通用工具 ----------------

function Show-Usage {
    Write-Host ""
    Write-Host "用法示例：" -ForegroundColor Cyan
    Write-Host "  .\.scripts\submodule-toggle.ps1 -Action status  -Name native_projects,rust_projects"
    Write-Host "  .\.scripts\submodule-toggle.ps1 -Action deinit  -Name native_projects,rust_projects"
    Write-Host "  .\.scripts\submodule-toggle.ps1 -Action restore -Name rust_projects"
    Write-Host ""
    Write-Host "详细说明：Get-Help .\.scripts\submodule-toggle.ps1 -Full"
    Write-Host ""
}

function Get-KnownSubmodules {
    param([string]$GitmodulesPath)
    $names = @()
    foreach ($line in (Get-Content -LiteralPath $GitmodulesPath)) {
        if ($line -match '^\s*\[submodule\s+"([^"]+)"\]') {
            $names += $Matches[1]
        }
    }
    return $names
}

function Invoke-GitChecked {
    param([string]$Path, [string[]]$GitArgs)
    $out = & git -C $Path @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') 失败，退出码 $LASTEXITCODE"
    }
    return $out
}

# 读取单个子模块的完整状态（只读，不产生任何修改）
function Get-SmState {
    param([string]$RepoRoot, [string]$Name)

    $state = @{
        Name = $Name
        ModulesDir = (Test-Path (Join-Path $RepoRoot ".git\modules\$Name"))
        GitlinkSha = $null
        Initialized = $false
        Branch = ''
        Dirty = $false
        DirtyCount = 0
        UnpushedCount = 0
        StashCount = 0
    }

    # index 中是否有 160000 gitlink
    $ls = Invoke-GitChecked -Path $RepoRoot -GitArgs @('ls-files','-s','--',$Name)
    $lsLine = @($ls | Select-Object -First 1)
    if ($lsLine.Count -gt 0 -and ("$($lsLine[0])") -match '^160000\s+([0-9a-f]{40})') {
        $state.GitlinkSha = $Matches[1]
    }

    $smPath = Join-Path $RepoRoot $Name
    if (Test-Path (Join-Path $smPath '.git')) {
        $state.Initialized = $true
        $branchOut = Invoke-GitChecked -Path $smPath -GitArgs @('branch','--show-current')
        if (@($branchOut).Count -gt 0) { $state.Branch = ("$($branchOut[0])").Trim() }
        $porcelain = Invoke-GitChecked -Path $smPath -GitArgs @('status','--porcelain')
        $dirtyLines = @($porcelain | Where-Object { $_ -and ("$_").Trim() })
        $state.DirtyCount = $dirtyLines.Count
        $state.Dirty = ($dirtyLines.Count -gt 0)
        $unpushed = Invoke-GitChecked -Path $smPath -GitArgs @('log','--all','--not','--remotes','--oneline')
        $state.UnpushedCount = @($unpushed | Where-Object { $_ }).Count
        $stash = Invoke-GitChecked -Path $smPath -GitArgs @('stash','list')
        $state.StashCount = @($stash | Where-Object { $_ }).Count
    }
    return $state
}

# ---------------- status：只读体检 ----------------

function Invoke-StatusAction {
    param([string]$RepoRoot, [string[]]$Names)

    Write-Host "======== submodule-toggle 状态体检（共 $($Names.Count) 个目标）========" -ForegroundColor Cyan
    foreach ($n in $Names) {
        $s = Get-SmState -RepoRoot $RepoRoot -Name $n
        Write-Host ""
        Write-Host "[$n]" -ForegroundColor White
        Write-Host "  登记(.gitmodules) : 已登记"
        if ($s.ModulesDir) {
            Write-Host "  本地 git 库       : .git/modules/$n 存在（本地即可恢复）"
        } else {
            Write-Host "  本地 git 库       : 缺失（恢复时需从远端重新拉取）" -ForegroundColor Yellow
        }
        if ($s.GitlinkSha) {
            Write-Host ("  index gitlink     : " + $s.GitlinkSha.Substring(0,7) + "（index 中存在）")
        } else {
            Write-Host "  index gitlink     : 缺失（不能直接 update --init，restore 时脚本会自动重建）" -ForegroundColor Yellow
        }
        if (-not $s.Initialized) {
            Write-Host "  工作区            : 未初始化（已注销）" -ForegroundColor Yellow
            Write-Host "  判定              : 已注销（无数据丢失，随时可 restore）"
            Write-Host ("  建议              : 需要恢复时运行 -Action restore -Name " + $n)
        } else {
            if ($s.Branch) {
                Write-Host ("  工作区            : 已初始化；分支 " + $s.Branch)
            } else {
                Write-Host "  工作区            : 已初始化；detached HEAD（无本地分支）"
            }
            if ($s.Dirty) {
                $dirtyDesc = "有未提交改动（$($s.DirtyCount) 处，含未跟踪）"
            } else {
                $dirtyDesc = "工作区干净"
            }
            Write-Host ("  变更状态          : " + $dirtyDesc + "；未推送提交 " + $s.UnpushedCount + "；stash " + $s.StashCount)
            if ($s.Dirty -or $s.UnpushedCount -gt 0) {
                Write-Host "  判定              : 暂不能 deinit（请先在子模块内处理 commit / push）" -ForegroundColor Yellow
            } else {
                Write-Host "  判定              : 可安全 deinit"
            }
            Write-Host ("  建议              : 注销运行 -Action deinit -Name " + $n)
        }
    }
    Write-Host ""
    Write-Host "体检完成（status 为只读操作，未做任何修改）。" -ForegroundColor Green
}

# ---------------- deinit：本地注销（带前置检查） ----------------

function Invoke-DeinitAction {
    param([string]$RepoRoot, [string[]]$Names)

    # 第一轮：全量前置检查，任一不通过则整批拒绝、一个都不动
    $toDeinit = @()
    $skipped = @()
    $rejected = @()
    foreach ($n in $Names) {
        $s = Get-SmState -RepoRoot $RepoRoot -Name $n
        if (-not $s.Initialized) {
            $skipped += $n
            continue
        }
        $problems = @()
        if ($s.Dirty) {
            $problems += ("    存在未提交改动（" + $s.DirtyCount + " 处，含未跟踪文件），请先在子模块内 commit")
        }
        if ($s.UnpushedCount -gt 0) {
            $problems += ("    存在 " + $s.UnpushedCount + " 个未推送到任何远端的提交，请先在子模块内 push")
        }
        if ($problems.Count -gt 0) {
            $rejected += [pscustomobject]@{ Name = $n; Problems = $problems }
        } else {
            if ($s.StashCount -gt 0) {
                Write-Host "提示：$n 存在 $($s.StashCount) 条 stash（保存在 .git/modules/$n，deinit 不会丢失）。" -ForegroundColor DarkYellow
            }
            $toDeinit += $n
        }
    }

    if ($rejected.Count -gt 0) {
        Write-Host "前置检查未通过，整批拒绝（未修改任何子模块）：" -ForegroundColor Red
        foreach ($r in $rejected) {
            Write-Host ("  [" + $r.Name + "]") -ForegroundColor Red
            foreach ($p in $r.Problems) { Write-Host $p -ForegroundColor Red }
        }
        Write-Host "请先在上述子模块内处理 commit / push，然后重新运行本脚本。" -ForegroundColor Yellow
        exit 2
    }

    foreach ($n in $skipped) {
        Write-Host "[$n] 已处于注销状态，跳过（幂等）。" -ForegroundColor DarkGray
    }

    # 第二轮：执行 deinit + 清理残留 + 验证
    $failed = @()
    foreach ($n in $toDeinit) {
        Write-Host "[$n] 正在本地注销 ..." -ForegroundColor Cyan
        try {
            Invoke-GitChecked -Path $RepoRoot -GitArgs @('submodule','deinit','-f','--',$n) | Out-Null
        } catch {
            Write-Host ("  出错：" + $_.Exception.Message) -ForegroundColor Red
            $failed += $n
            continue
        }

        # 清理残留空目录（deinit 只清空内容、保留目录本身）
        $smPath = Join-Path $RepoRoot $n
        if (Test-Path $smPath) {
            $leftovers = @(Get-ChildItem -Force -LiteralPath $smPath)
            if ($leftovers.Count -eq 0) {
                Remove-Item -LiteralPath $smPath -Force
            } else {
                Write-Host ("  警告：deinit 后目录仍残留 " + $leftovers.Count + " 项，未自动删除，请人工确认。") -ForegroundColor Yellow
            }
        }

        # 验证三项：status 前缀 '-'、本地 git 库保留、config 注册已移除
        $ok = $true
        $statusLine = @(git -C $RepoRoot submodule status -- $n | Select-Object -First 1)
        if (-not ($statusLine.Count -gt 0 -and ("$($statusLine[0])") -match '^-')) {
            $ok = $false
            Write-Host "  验证失败：git submodule status 未显示 '-' 前缀。" -ForegroundColor Red
        }
        if (-not (Test-Path (Join-Path $RepoRoot ".git\modules\$n"))) {
            $ok = $false
            Write-Host "  验证失败：本地 git 库 .git/modules/$n 不在了（不应删除）。" -ForegroundColor Red
        }
        $cfg = @(git -C $RepoRoot config --local --get-regexp ("^submodule\." + [regex]::Escape($n) + "\."))
        if (@($cfg | Where-Object { $_ }).Count -gt 0) {
            $ok = $false
            Write-Host "  验证失败：.git/config 中注册条目未移除。" -ForegroundColor Red
        }

        if ($ok) {
            Write-Host "  完成：已注销；本地 git 库与 .gitmodules 完好；父仓库无需提交。" -ForegroundColor Green
        } else {
            $failed += $n
        }
    }

    if ($failed.Count -gt 0) {
        Write-Host ("以下子模块注销过程出错：" + ($failed -join ', ')) -ForegroundColor Red
        exit 3
    }
    Write-Host ""
    Write-Host "deinit 完成。未触碰：.gitmodules、远端、父仓库 index；恢复请运行 -Action restore。" -ForegroundColor Green
}

# ---------------- restore：本地恢复（普通 + gitlink 重建） ----------------

function Invoke-RestoreAction {
    param([string]$RepoRoot, [string[]]$Names)

    $failed = @()
    foreach ($n in $Names) {
        Write-Host "[$n] 正在恢复 ..." -ForegroundColor Cyan
        $s = Get-SmState -RepoRoot $RepoRoot -Name $n
        $smPath = Join-Path $RepoRoot $n
        if ($s.Initialized) {
            Write-Host "  已处于初始化状态，跳过（幂等）。" -ForegroundColor DarkGray
            continue
        }

        $rebuildGitlink = $false
        $branch = 'main'
        try {
            if ($s.GitlinkSha) {
                Write-Host ("  index gitlink 存在（" + $s.GitlinkSha.Substring(0,7) + "），执行 update --init ...")
                Invoke-GitChecked -Path $RepoRoot -GitArgs @('submodule','update','--init','--',$n) | Out-Null
            } else {
                Write-Host "  index gitlink 缺失（历史遗留），自动回溯历史提交重建 ..." -ForegroundColor Yellow
                $found = $null
                $commits = @(Invoke-GitChecked -Path $RepoRoot -GitArgs @('rev-list','HEAD','--',$n))
                foreach ($c in $commits) {
                    $treeLine = @(Invoke-GitChecked -Path $RepoRoot -GitArgs @('ls-tree',$c,'--',$n) | Select-Object -First 1)
                    if ($treeLine.Count -gt 0 -and ("$($treeLine[0])") -match '^160000\s+([0-9a-f]{40})') {
                        $found = $c
                        break
                    }
                }
                if (-not $found) {
                    throw "在 HEAD 历史中未找到任何包含 $n gitlink 的提交，无法自动重建"
                }
                Write-Host ("  找到包含 gitlink 的历史提交 " + $found.Substring(0,7) + "，取回 index 条目 ...")
                Invoke-GitChecked -Path $RepoRoot -GitArgs @('checkout',$found,'--',$n) | Out-Null
                Invoke-GitChecked -Path $RepoRoot -GitArgs @('submodule','update','--init','--',$n) | Out-Null
                $rebuildGitlink = $true
            }

            # 切换到 .gitmodules 声明的跟踪分支（缺省回退 main）
            $branchCfg = @(Invoke-GitChecked -Path $RepoRoot -GitArgs @('config','-f',(Join-Path $RepoRoot '.gitmodules'),"submodule.$n.branch"))
            if ($branchCfg.Count -gt 0 -and ("$($branchCfg[0])").Trim()) {
                $branch = ("$($branchCfg[0])").Trim()
            }
            Invoke-GitChecked -Path $smPath -GitArgs @('switch',$branch) | Out-Null

            if ($rebuildGitlink) {
                # ignore=all 拦截普通 add，必须 --force；把 index 指针更新为分支最新
                Invoke-GitChecked -Path $RepoRoot -GitArgs @('add','--force','--',$n) | Out-Null
            }
        } catch {
            Write-Host ("  出错：" + $_.Exception.Message) -ForegroundColor Red
            Write-Host "  提示：恢复中断不会丢失数据；可修复问题后重新运行 restore。" -ForegroundColor Yellow
            $failed += $n
            continue
        }

        # 验证：已初始化 + 分支正确
        $newState = Get-SmState -RepoRoot $RepoRoot -Name $n
        $ok = $true
        if (-not $newState.Initialized) {
            $ok = $false
            Write-Host "  验证失败：工作区仍未初始化。" -ForegroundColor Red
        }
        if ($newState.Branch -ne $branch) {
            $ok = $false
            Write-Host ("  验证失败：当前分支 '" + $newState.Branch + "' 与目标分支 '" + $branch + "' 不一致。") -ForegroundColor Red
        }

        if ($ok) {
            if ($rebuildGitlink) {
                Write-Host ("  完成：gitlink 已重建，工作区已切到 " + $branch + " 分支最新。") -ForegroundColor Green
                Write-Host "  注意：父仓库 index 已更新（gitlink 指向分支最新），需要提交父仓库指针，建议命令：" -ForegroundColor Yellow
                Write-Host ("    git add --force " + $n)
                Write-Host ("    git commit -m ""fix: 重建 " + $n + " 子模块 gitlink""")
            } else {
                Write-Host ("  完成：已恢复并切到 " + $branch + " 分支；父仓库指针未变化，无需提交。") -ForegroundColor Green
            }
        } else {
            $failed += $n
        }
    }

    if ($failed.Count -gt 0) {
        Write-Host ("以下子模块恢复过程出错：" + ($failed -join ', ')) -ForegroundColor Red
        exit 3
    }
    Write-Host ""
    Write-Host "restore 完成。全程未触碰远端，未自动提交任何父仓库变更。" -ForegroundColor Green
}

# ---------------- 入口 ----------------

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path (Join-Path $repoRoot '.gitmodules'))) {
    Write-Host "错误：$repoRoot 不是父仓库根（未找到 .gitmodules），请在父仓库内运行。" -ForegroundColor Red
    exit 1
}

if (-not $Action) {
    Write-Host "错误：缺少 -Action（status | deinit | restore）。" -ForegroundColor Red
    Show-Usage
    exit 1
}
if ($Action -notin @('status','deinit','restore')) {
    Write-Host "错误：未知 -Action '$Action'（可选：status | deinit | restore）。" -ForegroundColor Red
    Show-Usage
    exit 1
}
if (-not $Name -or @($Name | Where-Object { $_ -and ("$_").Trim() }).Count -eq 0) {
    Write-Host "错误：缺少 -Name 子模块名称（防止误伤主力子模块，必须显式给出）。" -ForegroundColor Red
    Show-Usage
    exit 1
}
$Name = @($Name | Where-Object { $_ -and ("$_").Trim() } | ForEach-Object { ("$_").Trim() })

$known = Get-KnownSubmodules (Join-Path $repoRoot '.gitmodules')
$invalid = @($Name | Where-Object { $known -notcontains $_ })
if ($invalid.Count -gt 0) {
    Write-Host ("错误：以下名称未在 .gitmodules 登记：" + ($invalid -join ', ')) -ForegroundColor Red
    Write-Host ("已登记的子模块：" + ($known -join ', '))
    Show-Usage
    exit 1
}

try {
    switch ($Action) {
        'status' { Invoke-StatusAction -RepoRoot $repoRoot -Names $Name }
        'deinit' { Invoke-DeinitAction -RepoRoot $repoRoot -Names $Name }
        'restore' { Invoke-RestoreAction -RepoRoot $repoRoot -Names $Name }
        default {
            Write-Host "错误：动作 '$Action' 尚未实现。" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    Write-Host ("执行失败：" + $_.Exception.Message) -ForegroundColor Red
    exit 3
}

exit 0
