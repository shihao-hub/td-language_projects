# Task List

- [ ] 1. 实现图片 SHA-256 Blob 归档、移除内存 Base64 缓存，并在构造多轮请求时将超过 3 轮的老图片动态降级为纯文本占位符
  - Files: `internal/service/image.go`, `internal/service/chat.go`
  - 实现细节：
    1. 在 `internal/service/image.go` 中定义 `MaxImageContextTurns = 3`，移除 `Image.Base64` 字段；在 `PrepareImage` 中识别已归档的 `<64位hex>.<ext>` blob 路径并将 `FileName` 设为 `"clipboard" + ext`。
    2. 在 `internal/service/image.go` 中实现 `ArchiveImage(blobDir string, image Image) (Image, error)`（计算 SHA-256、映射 `.png`/`.jpg`/`.webp`/`.gif`、同目录临时文件原子写入 `<dataDir>/blobs/<sha256>.<ext>`、已存在同大小文件直接复用、保留原 `FileName`），实现 `CaptureClipboardImageInDir(dataDir string)` 与 `CaptureClipboardImage()`（捕获后归档至 `blobs/` 并 `defer os.Remove` 清理临时文件），实现 `formatDegradedImageMessage(rawContent string, images []session.Image) string`（剥离 `[[image:...]]` 标记后按行追加 `[用户曾在此处发送图片: <file_name>]`）。
    3. 在 `internal/service/chat.go`（依赖本任务步骤 1-2 的函数）中移除 `imageMu`、`imageCache` 及相关缓存方法，新增 `dataDir`/`blobDir` 字段与 `(c *Chat) CaptureClipboardImage()` 方法；在 `SendWithImages` 中将本轮图片先通过 `ArchiveImage` 归档至 `c.blobDir` 再构造请求并写入 `session.json`；在 `buildRequestMessages` 中统计历史 user 轮次，最近 `MaxImageContextTurns` 轮（含当前发送轮）按需调用 `loadImage` 发送 `llm.ImageMessage`（历史消息同步调用 `stripImageMarkers`），更早轮次调用 `formatDegradedImageMessage` 发送 `llm.TextMessage` 且不读取磁盘文件。
  - Verify: 执行 `go build ./...`，预期退出码为 0 且无编译错误（默认仅作备用信息，执行阶段不跑）
  - Ref: AC-1, AC-2, AC-3, AC-4

- [ ] 2. 绑定 TUI 剪贴板捕获目录、修复 `/image` 暂存图片提交透传，并同步更新 `README.md`
  - Files: `internal/tui/model.go`, `README.md`
  - 实现细节：
    1. 在 `internal/tui/model.go`（依赖任务 1 的 `chat.CaptureClipboardImage`）的 `newModel` 中，当 `chat != nil` 时将 `captureClipboard` 设为 `chat.CaptureClipboardImage`；在 `submit()` 中先保存 `staged := m.staged` 再置 `m.staged = nil`，将 `staged` 传入 `startStreamWithImages`。
    2. 在 `README.md` 中将剪贴板保存路径与图片缓存说明更新为统一归档至 `%APPDATA%\language_projects\typeai\blobs\<sha256>.<ext>`、按需读取编码 Base64，以及多轮对话仅保留最近 3 轮真实图片负载、更早轮次降级为 `[用户曾在此处发送图片: <文件名>]`。
  - Verify: 执行 `go build ./...`，预期退出码为 0 且无编译错误（默认仅作备用信息，执行阶段不跑）
  - Ref: AC-1, AC-2, AC-4

- [ ] 3. 更新图片单元测试与多轮图片归档/降级集成测试
  - Files: `internal/service/image_test.go`, `internal/service/image_marker_test.go`
  - 实现细节：
    1. 移除 `internal/service/image_test.go` 与 `internal/service/image_marker_test.go` 中对已删除字段 `Image.Base64` 的直接断言。
    2. 在 `internal/service/image_test.go` 中验证外部图片与标记图片发送后归档至 `<dataDir>/blobs/<sha256>.png`、`session.json` 记录归档路径与原 `file_name`、原外部图片删除后第 2~3 轮仍能按需读取重建 Base64 负载。
    3. 在 `internal/service/image_test.go` 中新增 4 轮对话测试：验证第 1~3 轮请求中第 1 轮消息包含 `image_url` Base64 负载，第 4 轮请求中（即使手动删除第 1 轮的 blob 文件）第 1 轮消息自动降级为纯文本 `"<文本>\n[用户曾在此处发送图片: <file_name>]"` 且不含 `image_url`。
  - Verify: 执行 `go test ./...`，预期所有测试 PASS 且退出码为 0（默认仅作备用信息，执行阶段不跑）
  - Ref: AC-1, AC-2, AC-3, AC-4
  - [test]