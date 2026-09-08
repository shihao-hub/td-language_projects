# init-submodules.ps1 —— 克隆后初始化子模块并切换到跟踪分支
# 用法：git clone --recurse-submodules <URL> 后，在父仓库根目录执行一次本脚本
# 说明：git 子模块默认以 detached HEAD checkout 父仓库记录的 commit，
#       本脚本在初始化后按 .gitmodules 中各子模块的 branch 字段切到对应本地分支。

$ErrorActionPreference = 'Stop'

# 1. 仅初始化尚未拉取的子模块（status 输出前缀 '-' 表示未初始化）；
#    已存在的 checkout 保持原样，不把领先指针的子模块拽回旧 commit
git submodule status | ForEach-Object {
    if ($_ -match '^-[0-9a-f]+ (\S+)') {
        $smPath = $Matches[1]
        Write-Host "init: $smPath"
        git submodule update --init -- $smPath
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}

# 2. 按各子模块在 .gitmodules 中声明的 branch 切换本地分支；
#    未声明 branch 时回退 master，再回退 main
#    （git switch 在本地无同名分支时会自动创建并跟踪 origin/<branch>）
git submodule foreach --recursive 'branch=$(git config -f $toplevel/.gitmodules submodule.$name.branch); if [ -z "$branch" ]; then branch=master; fi; git switch "$branch" 2>/dev/null || git switch main'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'OK: 子模块已初始化并全部切换到跟踪分支。'
