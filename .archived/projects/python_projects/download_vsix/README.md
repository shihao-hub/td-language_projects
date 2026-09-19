# VSIX Downloader

一个用于从 VS Code 插件市场下载 VSIX 文件的命令行工具。

## 功能特性

- 🔍 **自动解析**：从 VS Code 插件市场 URL 自动提取扩展信息
- 📦 **最新版本**：自动获取扩展的最新版本号
- ⬇️ **智能下载**：支持进度条显示、断点续传、自动重试
- 🛡️ **错误处理**：完善的错误提示和用户友好的反馈
- 🎨 **美观输出**：使用 Rich 库提供彩色终端输出

## 安装

### 使用 uv 安装（推荐）

```bash
# 克隆项目
git clone <repository-url>
cd download_vsix

# 使用 uv 安装依赖
uv sync

# 安装到系统
uv pip install -e .
```

### 使用 pip 安装

```bash
# 安装依赖
pip install -r requirements.txt

# 安装到系统
pip install -e .
```

## 使用方法

### 基本用法

```bash
download-vsix https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno
```

### 指定输出目录

```bash
download-vsix <url> --output-dir ./my-extensions
```

### 强制覆盖已存在文件

```bash
download-vsix <url> --force
```

### 禁用断点续传

```bash
download-vsix <url> --no-resume
```

### 详细模式（显示调试信息）

```bash
download-vsix <url> --verbose
```

### 不显示横幅

```bash
download-vsix <url> --no-banner
```

## 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--output-dir` | `-o` | 指定保存 VSIX 文件的目录（默认：`vsixs`）|
| `--force` | `-f` | 强制覆盖已存在的文件 |
| `--no-resume` | | 禁用断点续传功能 |
| `--verbose` | `-v` | 启用详细输出模式 |
| `--no-banner` | | 不显示应用横幅 |

## 工作原理

1. **URL 解析**：从输入的 URL 中提取 `itemName`（如 `denoland.vscode-deno`）
2. **信息提取**：将 `itemName` 分解为 `publisher`（如 `denoland`）和 `extension_name`（如 `vscode-deno`）
3. **版本获取**：访问扩展详情页，解析 Version History 获取最新版本号
4. **URL 拼接**：根据模板拼接下载 URL：
   ```
   https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{extension_name}/{version}/vspackage
   ```
5. **文件下载**：下载 VSIX 文件到指定目录

## 示例

下载 Deno 扩展：

```bash
download-vsix https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno
```

输出示例：

```
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║         VSIX Downloader for VS Code Marketplace           ║
    ║                     v0.1.0                                ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝

ℹ Validating URL: https://marketplace.visualstudio.com/items?itemName=denoland.vscode-deno
ℹ Parsing extension information...
ℹ Fetching extension details...

Extension: denoland.vscode-deno v3.43.3
  Version: 3.43.3
  Download URL: https://marketplace.visualstudio.com/_apis/public/gallery/publishers/denoland/vsextensions/vscode-deno/3.43.3/vspackage

Starting download...
File size: 12.34 MB

Downloading denoland.vscode-deno-3.43.3.vix ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 12.34 MB/12.34 MB 2.34 MB/s 00:00:05

✓ Download completed successfully!
  File: vsixs/denoland.vscode-deno-3.43.3.vix
  Size: 12.34 MB
  SHA256: abc123...

============================================================
Download completed successfully!
============================================================
  Extension: denoland.vscode-deno v3.43.3
  Saved to: vsixs/denoland.vscode-deno-3.43.3.vix
  Filename: denoland.vscode-deno-3.43.3.vix
```

## 错误处理

工具会处理以下错误情况：

- **无效 URL**：提示正确的 URL 格式
- **网络错误**：自动重试 3 次，使用指数退避策略
- **版本解析失败**：提示可能的原因和解决方案
- **文件已存在**：提示使用 `--force` 参数覆盖
- **下载失败**：提供详细的错误信息

## 开发

### 安装开发依赖

```bash
uv pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
ruff format .
ruff check .
```

### 类型检查

```bash
mypy src/
```

## 项目结构

```
download_vsix/
├── pyproject.toml          # 项目配置
├── README.md               # 项目文档
├── .gitignore              # Git 忽略文件
├── vsixs/                  # 默认下载目录
│
├── src/
│   └── download_vsix/
│       ├── __init__.py
│       ├── cli.py          # 命令行入口
│       ├── parser.py       # URL 和页面解析
│       ├── downloader.py   # 下载模块
│       ├── utils.py        # 工具函数
│       └── exceptions.py   # 自定义异常
│
└── tests/                  # 测试用例
```

## 依赖项

- `httpx` - HTTP 请求库
- `beautifulsoup4` - HTML 解析
- `typer` - CLI 框架
- `rich` - 美观的终端输出
- `loguru` - 日志记录

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

本工具基于 VS Code 插件市场的 API 实现。
