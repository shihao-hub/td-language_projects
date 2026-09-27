# Requirements Document

## Summary
重构 `typeai` 的图片持久化与多轮对话图片上下文管理机制：放弃 `%TEMP%` 临时目录与进程内存中的 Base64 缓存，将剪贴板图片（`Alt+V`）与外部本地图片（`/image`、`[[image:...]]`）统一以 SHA-256 内容寻址方式归档至 `%APPDATA%\language_projects\typeai\blobs\<sha256>.<ext>`；在多轮对话构造 LLM 请求时，按需从 `blobs/` 读取图片编码并在请求后释放，同时仅保留最近 3 个对话轮次（含当前发送轮）的真实图片负载，将更早轮次的历史图片动态降级为纯文本占位符 `[用户曾在此处发送图片: <file_name>]`。

## Functional Requirements
- **FR-1（内容寻址 Blob 归档）**：系统在归档图片时，须校验图片非空、不超过 `10 MiB` 上限、且媒体类型为 `image/png`、`image/jpeg`、`image/webp` 或 `image/gif`，计算原始二进制内容的 SHA-256 哈希，按媒体类型映射扩展名（`.png` / `.jpg` / `.webp` / `.gif`），将原始图片字节原子写入 `<dataDir>/blobs/<sha256>.<ext>`。相同内容的图片复用同一归档文件。
- **FR-2（剪贴板图片直接入库）**：用户通过 `Alt+V` 捕获剪贴板图片时，系统不再将最终文件保留在 `%TEMP%\language_projects\typeai\clipboard\`，而是直接归档至 `<dataDir>/blobs/<sha256>.png` 并清理临时捕获文件；归档后的图片 `Path` 为该 blob 绝对路径，`FileName` 固定为 `clipboard.png`。
- **FR-3（外部图片发送归档与 Session 记录）**：用户通过 `/image <路径>` 或 `[[image:<路径>]]` 发送外部图片时，系统将图片归档至 `<dataDir>/blobs/<sha256>.<ext>`；`session.json`（保持 `schema_version: 2`）的 `images` 列表中，`path` 记录归档后的 blob 绝对路径，`file_name` 保留原始文件名（剪贴板图片为 `clipboard.png`），`media_type` 与 `size` 记录真实媒体类型与字节大小，`session.json` 不保存 Base64。
- **FR-4（移除内存 Base64 缓存，按需加载）**：移除 `service.Chat` 中的 `imageCache` 内存缓存及 `service.Image` 上的 `Base64` 常驻字段；在需要向模型发送真实图片负载时，直接从归档路径按需读取字节、校验文件大小与媒体类型并编码为 Base64 构造请求，发送完毕后随请求对象释放。
- **FR-5（多轮上下文老图片动态降级）**：定义内置常量 `MaxImageContextTurns = 3`（按“一问一答为 1 轮”计算，包含当前正在发送的轮次）。构造发往 LLM 的请求消息列表时：
  - 最近 `MaxImageContextTurns` 轮内（即当前发送轮 + `session.Messages` 中最近 2 个已完成对话轮次）的含图 User 消息，剥离文本中的 `[[image:...]]` 标记后，按需从 `blobs/` 读取图片并以 `image_url`（`data:<media_type>;base64,...`）多模态格式发送；
  - 超过 `MaxImageContextTurns` 轮的更早含图 User 消息，不再读取图片文件、不发送 `image_url` part，而是将每张图片按顺序转化为 `[用户曾在此处发送图片: <file_name>]` 追加在剥离 `[[image:...]]` 标记后的文本末尾（以换行分隔；若原文本剥离标记后为空，则仅包含占位符文本），作为普通纯文本消息（`llm.TextMessage`）发送；
  - 本地 `session.json` 始终保留用户原始输入文本与完整的 `images` 元数据，不受请求级降级影响。

## Non-Functional Requirements
- **NFR-1（写入原子性）**：向 `blobs/` 写入归档文件时采用同目录临时文件 + 原子重命名（若目标 `<sha256>.<ext>` 已存在且字节数匹配则直接跳过重写），避免异常中断产生损坏的 blob 文件。
- **NFR-2（临时文件零残留）**：平台剪贴板捕获产生的临时文件在归档或失败后立即删除，不在 `%TEMP%` 留存历史截图。

## Acceptance Criteria
### AC-1：剪贴板图片归档与文件名保留
WHEN 用户触发剪贴板图片捕获（`CaptureClipboardImage`），系统将图片归档至 `<dataDir>/blobs/<sha256>.png` 并删除临时捕获文件，返回的 `service.Image` 的 `Path` 指向 `<dataDir>/blobs/<sha256>.png`、`FileName` 为 `"clipboard.png"`；当该路径通过 `[[image:<blob_path>]]` 标记被解析与发送时，`session.json` 中记录的 `file_name` 仍为 `"clipboard.png"`。

### AC-2：外部图片归档与原文件删除后多轮可用
WHEN 用户通过 `/image <路径>` 或 `[[image:<路径>]]` 发送外部图片（如 `D:\temp\chart.png`）成功后删除原文件 `D:\temp\chart.png`，`session.json` 中记录的 `path` 为 `<dataDir>/blobs/<sha256>.png`、`file_name` 为 `"chart.png"` 且不含 Base64；紧接着在第 2、3 轮发送后续消息时，系统仍能从 `blobs/` 成功读取图片并构造 `data:image/png;base64,...` 请求，且 `service.Chat` 与 `service.Image` 结构中不常驻 Base64 字段或缓存表。

### AC-3：最近 3 轮内保留真实图片负载
WHEN 第 1 轮发送包含图片的消息，在第 1、2、3 轮发往 LLM 的请求中，第 1 轮 User 消息均为多模态数组格式（包含剥离 `[[image:...]]` 后的文本 part 与 `image_url` Base64 part）。

### AC-4：超过 3 轮后老图片动态降级为纯文本占位符
WHEN 第 1 轮发送包含图片（如 `screenshot.png`）的消息，对话进行到第 4 轮及以后时，发往 LLM 的请求中第 1 轮 User 消息降级为纯文本 `content` 字符串（格式为 `<剥离标记后的文本>\n[用户曾在此处发送图片: screenshot.png]`，无前导文本时为 `[用户曾在此处发送图片: screenshot.png]`），不再包含 `image_url` 且不读取第 1 轮的磁盘图片文件；若第 2、3 轮也含图片，它们在第 4 轮请求中仍保持真实 `image_url` 负载；同时 `session.json` 中第 1 轮的 `content` 和 `images` 元数据保持原样不变。

## Out of Scope
- `config.json` 或环境变量对图片保留轮数 `MaxImageContextTurns` 的动态配置（当前固定为内置常量 `3`）。
- 历史 `blobs/` 文件的自动垃圾回收或 CLI 清理子命令。
- 文本消息的上下文裁剪或摘要压缩。