# 个人项目价值盘点

> 按语言子仓划分，覆盖活跃与归档项目。
> 列含义：状态 = 当前可用性；源码阅读情况 = 核心链路阅读进度；价值 = 对个人成长/简历的意义；下一步 = 最近的动作计划。
> 归档项目可能只是暂时归档，同样保留全部列，便于重启时评估。

## typescript_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| taskmon | 更好用的任务管理器 | 稳定，长期使用 | 未阅读，核心链路未知 |  |  |
| text-extractor | chrome 插件开发初体验 | 可用 | 已阅读，较简单，但是又属于跨领域知识了，好处是公司也有达人插件开发，可以用来优化简历 |  |  |
| django-lab-react | 图书馆业务系统的 React SPA 前端，消费 django-lab 后端 /api/ 接口，前后端分离形态 |  |  |  |  |

## python_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| archery-mcp | 同事封装内部平台的 http 接口为 mcp tool | 对方已实现且可用 | 未阅读，亟待阅读 | agent mcp 与前端知识 |  |
| django-lab | django 回忆项目，为了汲取 django 的思想 |  | 未阅读，亟待阅读 | 高价值，但无法投入过多，要从架构师层面思考 |  |
| file-sync-py | python 复刻 file-sync-go |  | 还未开始，待办 | 高价值，锻炼 python 的手写能力 | 期待 9.15 左右能开始 |
| script-lab | 学习类项目，结构正在思考 | pass |  |  |  |
| tech_learning_room | 计划采用 apps 结构，一个 app 地去学习 cv 涉及到的技术 | pass |  |  |  |
| zed-opencode-sessions | MCP server + CLI，查询、导出、跨机迁移 Zed 与 OpenCode 的 AI 会话数据 |  |  |  |  |
| zedhub | zed 表数据 read 和 write，CLI 与 GUI 分离架构 | 待测试 | 核心链路阅读完毕，未阅读具体实现，其实不需要阅读，去了解 zed sqlite 表结构字段即可，具体实现不是关键 | 超高价值 |  |

## go_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| exestarter | exe 收藏架 CLI：扫描收集、集中注册、透传启动/定位/开终端（exe-launcher 的 CLI 版） |  |  |  |  |
| filesync | 带忽略规则的本地目录同步 CLI，三级判定加速，与 GUI 版共享任务配置（file-sync-native 的 CLI 版） |  |  |  |  |
| instancelock | 基于锁文件的进程单实例锁库，支持 try/hold 模式、超时与父进程存活检测 |  |  |  |  |
| ocstat | 统计 opencode 各会话启动所用模型与思考档位的 CLI |  |  |  |  |
| projstat | 总仓项目状态标注 CLI，合并 PROJECT.toml 手工标注与 git 元数据 |  |  |  |  |
| pythonlauncher | go 编写的 python 本地项目启动器，本质就是找到 python project path 和 uv，用 uv 的命令配合 pro（原 python-launcher-go） | 稳定 | 已阅读，但意义不大，毕竟也不用 go 干活，哪怕干活用的 python 也不咋看代码了，需要思考一下 |  |  |
| quickask | 命令行快速问 AI：预设指令 + 流式输出 + REPL，C/S 架构后端 quickaskd（aiquick 的 CLI 版） |  |  |  |  |
| taskmon | 空壳项目，刚初始化（taskmon 的 Go 版起点，原 taskmon-go） |  |  |  |  |
| zreadmanager | zread browse 生命周期管理 CLI：启动/树杀/探活，pidfile 跨进程定位（zread-tray 的 CLI 版） |  |  |  |  |

## rust_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| mini-everything | Everything CLI 简化版，NTFS 全盘文件名索引 + 秒级搜索 |  |  |  |  |
| mini-http-server | 纯 Rust 标准库多线程 HTTP 服务器，零依赖语言练手 |  |  |  |  |
| whoholds | Windows 文件句柄占用检测（类似 handle.exe），查占用指定文件的进程 |  |  |  |  |

## 归档项目（.archived）

### .archived/go_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| agent-reaper | 按 CPU/IO 增量判定闲置，整树清理 AI 编码代理进程 |  |  |  |  |
| aiquick | 常驻托盘 AI 快速助手，Alt+S 秒开，划词预填、预设指令、流式输出（CLI 版 quickask 已替代） | 归档 |  |  |  |
| console-calculator | Go 控制台四则运算计算器，手写词法分析与表达式求值 |  |  |  |  |
| exe-launcher | Windows 常用 exe 集中启动器，纯 Win32 API 单文件零依赖（CLI 版 exestarter 已替代） | 归档 |  |  |  |
| file-sync | 带 gitignore 式忽略规则、Web UI 与托盘的本地目录同步工具 |  |  |  |  |
| file-sync-native | 带忽略规则的本地目录同步工具，Wails v2 GUI（CLI 版 filesync 已替代） | 归档 |  |  |  |
| mcp-cleanup | 查找并击杀 AI 工具异常退出后泄漏的 MCP server 进程树 |  |  |  |  |
| mini-http-server-go | 用 Go 复刻 Rust 版迷你 HTTP 服务器，学习练手 |  |  |  |  |
| sublime-folders | 托盘常驻，定时将 Sublime 打开的目录记入 SQLite |  |  |  |  |
| zread-tray | 系统托盘常驻，为工作区一键启动/重启 zread 服务并拉起浏览器（CLI 版 zreadmanager 已替代） | 归档 |  |  |  |

### .archived/python_projects

| 项目 | 摘要 | 状态 | 源码阅读情况 | 价值 | 下一步 |
|-|-|-|-|-|-|
| demo-api | FastAPI 入门示例，异步 SQLAlchemy + PostgreSQL + Alembic |  |  |  |  |
| download_vsix | 从 VS Code 插件市场下载 VSIX 的 CLI，支持断点续传与重试 |  |  |  |  |
| flet-android-lab | Flet 纯 Python 开发 Android 应用实验（数日子 App） |  |  |  |  |
| lele | 高一化学教学资料合集（小测试卷与复习笔记），非代码项目 |  |  |  |  |
| pystand-lab | PyStand 打包 Python 桌面应用的踩坑实验 |  |  |  |  |
| sublime-rider-dark | Sublime Text 4 的 Rider Dark 主题配色包 |  |  |  |  |
