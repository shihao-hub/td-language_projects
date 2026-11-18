# 46 · 全机 Python 统一到 uv（3.12.5），全局 python/pip 走 shim，卸载 anaconda3 与 python312

## 状态：已完成（2026-10-07）

| 项 | 结果 |
| --- | --- |
| 全局 `python` / `pip` | `D:\Users\uv_shim` 转发 → 专用全局环境 `.uv-global`（uv 3.12.5） |
| uv 默认版本 | `UV_PYTHON=3.12.5` 持久化；`uv venv` / `uv run` 默认 3.12.5 |
| `D:\Users\python312`（4.95GB） | ⛔ **已卸载**（官方 MSI + 注册表清理 + 残留目录删除） |
| `D:\Users\29580\anaconda3`（4.67GB） | ⛔ **已卸载**（官方 `Uninstall-Anaconda3.exe` /S + 注册表清理） |
| 释放磁盘 | 共约 9.6GB；USER PATH 已无 python312/anaconda3 条目 |
| torch（`llm-finetune-lab`） | ⏸ 未安装（`download.pytorch.org` 网络拉不动），见「torch」节 |

## 背景

用户此前环境混乱，存在多个 Python 来源并存：

| 来源 | 路径 | 版本 | 包规模 | 处置 |
| --- | --- | --- | --- | --- |
| anaconda3 base | `D:\Users\29580\anaconda3` | 3.12.7 | 379 个科学计算包（numpy/pandas/scipy…，无 torch） | ⛔ 已卸载 |
| python312（手动 pip） | `D:\Users\python312` | 3.12.5 | 独立 site-packages | ⛔ 已卸载 |
| msys64/mingw64 | `D:\msys64\mingw64\bin` | 3.12（mingw） | 干扰 uv 探测定版 | 保留但由 shim 优先级压住 |
| uv 托管 | `C:\Users\29580\AppData\Roaming\uv\python\...` | 多版本 | uv 管理 | ✅ 唯一来源 |
| WindowsApps stub | `...\WindowsApps\python.exe` | —— | 商店 stub | 无关 |

需求场景：`python xxx` 与 `uv run xxx`。结论：**统一到 uv**，同时让只认 `python`/`pip` 的 AI 也能用。

## 最终架构（已落地）

```text
全局 python / pip（不认识 uv 的 AI 用）
   └─> D:\Users\uv_shim\{python.bat, pip.bat, python3.bat, pip3.bat}
          └─> D:\Users\uv_shim\.uv-global\Scripts\python.exe   （uv venv --python 3.12.5）
                ├─ python xxx      ->  .uv-global 解释器（3.12.5）
                └─ pip install X   ->  .uv-global 的 pip（装进同一环境，python 立即可 import）

uv run / uv add（懂 uv 的工具和你自己）
   └─> 各项目独立 .venv（隔离，互不干扰，默认 3.12.5）

uv 托管解释器本体（cpython-3.12.5）-> 只读、PEP 668 保护，纯净不污染
```

- `python`/`pip` 指向**同一个** `.uv-global` → pip 装的包 python 直接能 use（复刻传统全局 pip）。
- uv 托管解释器本体保持纯净；真正的 uv 工作流走项目 `.venv`，两套互不干扰。

## 关键事实（侦查确认）

1. `uv python list` 曾把 `D:\Users\python312\python.exe` **借用**为 3.12.5 来源；卸载后由 uv 托管版
   `C:\Users\29580\AppData\Roaming\uv\python\cpython-3.12.5-windows-x86_64-none\python.exe` 承担。
2. uv 托管解释器被 **PEP 668** 保护（`externally-managed`），裸 `pip install` 会被拒；故全局装包
   需一个**可自由 pip 的 venv**（`.uv-global`，uv 创建，无 PEP 668）。
3. `uv venv` 默认**不带 pip** → 必须先 `uv pip install --python X pip` seed，`python -m pip` 才可用。
4. `uv python find`（无参数）返回最高版本（如 3.13）是"探测解释器"，**不代表默认**；
   真正默认由 `UV_PYTHON=3.12.5` 控制（venv/run 均 3.12.5）。
5. `pip.bat` 走 `python -m pip` 而非 `uv pip`：`uv pip install` 会把 `install` 当包名、受 registry 干扰。
6. anaconda3 base **没有** torch/tensorflow（`pip show torch` 无）；"复用 anaconda 大依赖"对深度学习不成立。

## 实施步骤（本机已完成 + 新电脑复现）

### 1. uv 托管版 3.12.5
```powershell
uv python install 3.12.5
```

### 2. 锁定 uv 默认版本
```powershell
[System.Environment]::SetEnvironmentVariable('UV_PYTHON','3.12.5','User')
```

### 3. 建专用全局环境 + seed pip
```powershell
$shim = "$HOME\uv_shim"
New-Item -ItemType Directory -Force -Path $shim | Out-Null
uv venv --python 3.12.5 "$shim\.uv-global"
uv pip install --python "$shim\.uv-global\Scripts\python.exe" pip
```

### 4. 写转发脚本（4 个 .bat，内容见「新电脑一键引导」）
`python.bat` / `python3.bat` / `pip.bat` / `pip3.bat` 均指向 `.uv-global`。

### 5. 改 USER PATH
- **移除**：`D:\Users\python312`、`D:\Users\python312\Scripts`
- **前置**：`D:\Users\uv_shim`（最前，压过 mingw64 的 python，接管 `python`/`pip`）

### 6. 验证（须新开终端）
`python --version` → 3.12.5；`pip install six` → `python -c "import six"` → ok。

### 7. 卸载 python312 + anaconda3
- python312：官方 MSI 卸载器 `python-3.12.5-amd64.exe /uninstall /quiet`，注册表清理，删残留目录。
- anaconda3：`Uninstall-Anaconda3.exe /S`，注册表清理。

## torch / CUDA 深度学习方案（uv 项目隔离环境）

`llm-finetune-lab` 是完整 uv 项目，`pyproject.toml` 预配 cu128 索引（RTX 50 系 / Blackwell / sm_120
只有 cu128+ wheel 支持）：

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true
[tool.uv.sources]
torch = { index = "pytorch-cu128" }
```

- **已验证**：该 `.venv` 曾成功装出 `torch 2.11.0+cu128`，`torch.cuda.is_available()==True`，
  识别 `NVIDIA GeForce RTX 5050 Laptop GPU`。
- **副作用**：全局 `UV_PYTHON=3.12.5` 使 `uv run`/`sync` 重建 `.venv`（原 3.12.11 被删），
  触发 torch 2.6GB cu128 wheel 重新下载。
- **现状（待办）**：`download.pytorch.org` 大文件下载在本机网络**不可靠**（索引页 HTTP 200、wheel
  HTTP=000 中断），两次重试均中止。用户选择**暂不安装**，保留骨架（`.venv`=3.12.5）。
- **出路（使用 torch 时）**：换国内可访问的 cu128 wheel 源（如 `https://mirrors.aliyun.com/pytorch-wheels/cu128`，
  需同步改 `pyproject.toml` 的 index）；或从 ComfyUI 已装好的 `torch 2.11.0+cu128` 借实体 wheel 离线安装。
- ComfyUI 环境自带 `torch 2.11.0+cu128` 且 CUDA 可用，本机深度学习能力仍在。

## uv / python 下载物落位

| 内容 | 位置 | 说明 |
| --- | --- | --- |
| python 解释器（uv 托管） | `C:\Users\29580\AppData\Roaming\uv\python\cpython-<ver>-...\` | 每版一目录，只读 |
| 第三方依赖 wheel 缓存 | `D:\Users\29580\.cache\uv\`（`wheels-v5/`、`sdists-v9/`、`archive-v0/`） | 全局缓存跨项目复用；受 `UV_CACHE_DIR` 控制 |
| 全局 shim 装的包 | `D:\Users\uv_shim\.uv-global\Lib\site-packages\` | `python`/`pip` 落此 |
| 每个项目实际安装 | `<项目>\.venv\Lib\site-packages\` | 项目隔离 |

> `UV_CACHE_DIR` 已设 `D:\Users\29580\.cache\uv`（默认 `%LOCALAPPDATA%\uv\cache`，本机重定向到 D 盘）。

## 新电脑一键引导（仅安装 uv，复现同一配置）

> 目标：一台只装 uv 的新电脑 → uv 默认锁定 3.12.5，全局任何地方 `python`/`pip` 都用 uv 解释器。
> 假定 Windows + PowerShell；uv 已装（`winget install astral-sh.uv` 或官方脚本）。

```powershell
# 0. 新开终端使 uv 进入 PATH
# 1. 下载并锁定 3.12.5
uv python install 3.12.5
[System.Environment]::SetEnvironmentVariable('UV_PYTHON','3.12.5','User')

# 2. 建专用全局环境 + seed pip
$shim = "$HOME\uv_shim"
New-Item -ItemType Directory -Force -Path $shim | Out-Null
uv venv --python 3.12.5 "$shim\.uv-global"
uv pip install --python "$shim\.uv-global\Scripts\python.exe" pip

# 3. 在 $shim 写 4 个 .bat：
python.bat / python3.bat:
    @echo off
    "%~dp0.uv-global\Scripts\python.exe" %*
pip.bat / pip3.bat:
    @echo off
    "%~dp0.uv-global\Scripts\python.exe" -m pip %*

# 4. uv_shim 放到 USER PATH 最前
$old = [System.Environment]::GetEnvironmentVariable('Path','User')
[System.Environment]::SetEnvironmentVariable('Path', ($shim + ';' + $old), 'User')

# 5.（本机已完成此步，新电脑若同样要卸载旧 python 则执行）卸载 anaconda/python312：
#    python312: "C:\...\python-3.12.5-amd64.exe" /uninstall /quiet
#    anaconda3: Uninstall-Anaconda3.exe /S

# 6. 新开终端验证
python --version; pip --version
pip install six; python -c "import six; print('ok')"
```

### 易踩坑
1. `uv venv` 默认不带 pip → 须 `uv pip install ... pip` seed，否则 `No module named pip`。
2. `pip.bat` 用 `python -m pip`（非 `uv pip install`，其会把 `install` 当包名/受 registry 干扰）。
3. PATH 改动须新开终端生效。
4. `uv python find`（无参数）返回最高版本≠默认；默认由 `UV_PYTHON=3.12.5` 控制。
5. 解释器本体 PEP 668 只读；所有 `pip install` 落 `.uv-global`，不触碰本体 → uv 纯净。

## 回滚

```powershell
[System.Environment]::SetEnvironmentVariable('UV_PYTHON', $null, 'User')
# 恢复 USER PATH 原值（去掉 D:\Users\uv_shim 前缀）
# uv 托管版/ .uv-global 保留无害；如需删：uv python uninstall 3.12.5
```

## 后续可选（未做）

1. ~~`C:\Users\29580\.local\bin\python3.12.exe`（非 uv 管理，指向 3.12.11）与 uv 想放的 launcher 冲突~~  
   **已完成（2026-10-07）**：`uv python install 3.12.5 --force` 将该启动器重建为指向 **uv 托管 3.12.5**。
   现状：`python`/`python3`/`python3.12`/`pip` 全部为 3.12.5。该 launcher 本质是 uv 的薄启动器
   （41KB，运行时转调 `sys.prefix` 指向的托管解释器），对 shim 工作流零影响，故改为 3.12.5 更一致。
2. msys64/mingw64 的 python 会干扰 uv 探测定版（warning）：不影响运行暂不处理；
   `D:\Users\uv_shim` 在 PATH 最前已接管 `python`/`pip`。
3. torch 实装（见「torch」节出路）：换国内源或借 ComfyUI wheel。