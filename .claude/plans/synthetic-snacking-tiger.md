# 内置测试发信（163 → QQ）

## Context

用户已用 `scripts/send_test_mail.py` 验证过链路。现在希望把「发送测试邮件」内置到 exe：GUI 与 CLI 都能一键用网易 163 邮箱发信到自己的 QQ 邮箱，触发真实的外部来信链路（QQ 收信 → 白名单 → 飞书推送）。

安全底线：授权码不写入源码、exe、仓库或日志，只存用户本机数据目录的 `config.yaml`（0600，已 gitignore）。163 邮箱地址用户尚未提供，由用户在 GUI 配置页填写一次。

## 设计

### 1. 配置（internal/config/config.go）

新增可选段：

```yaml
test_sender:
  host: smtp.163.com
  port: 465
  username: yourname@163.com
  password: "163授权码"
  from_name: "mail2feishu 测试"
```

- `Config` 增加 `TestSender TestSenderConfig yaml:"test_sender"`，保持 `KnownFields(true)` 兼容。
- `ApplyDefaults`：host 默认 `smtp.163.com`，port 默认 465。
- `Validate`：仅当 `username` 非空时校验 password/host/port；整段为空合法。
- `config.yaml.example` 增加带注释的占位示例。

### 2. 运行时（internal/runtime）

新增 `internal/runtime/testmail.go`：

- `BuildTestMail(from, fromName, to string, now time.Time) []byte`：纯函数，构造 RFC 5322 邮件（UTF-8 主题/正文、Date、Message-ID、From 显示名），便于单测。
- `Runtime.SendTestMail(ctx) error`：
  - 收件人 = `cfg.IMAP.Username`；未配置 `test_sender` 时返回可读错误。
  - `tls.Dial`（465 隐式 TLS，MinVersion TLS1.2，30s 超时）→ `smtp.NewClient` → `smtp.PlainAuth` → Mail/Rcpt/Data。
  - 错误分类：未配置 / 连接失败 / 认证失败 / 被拒收。
- `ConfigView` 增加 `TestSenderView`（含 `password_set`，password 留空表示不修改）；同步 `NewConfigView`、`ToConfig`；`UpdateConfig` 对空密码沿用旧值。

### 3. API（internal/api/server.go）

- 新增 `POST /api/test-mail` → `runtime.SendTestMail`，30s context。
- 成功返回 `{sent:true,to:"<QQ 邮箱>"}`；失败 502 `test_mail_failed`；未配置 400 `test_sender_missing`。

### 4. GUI 与 WebUI

- 托盘（`internal/app/gui.go`）：「测试飞书投递」后新增「发送测试邮件」，goroutine + 30s context + 日志。
- 概览页（`internal/web/assets/index.html`）：新增「发送测试邮件」按钮。
- 配置页：新增「测试发信（163）」卡片（host/port/username/password/from_name），password 留空提示沿用。
- `app.js`：`fillConfig` / `collectConfig` 增加 `test_sender`；按钮调用 `POST /api/test-mail` 并 toast。

### 5. CLI（cmd/mail2feishu/cli.go）

- 新增 `-send-test`，在 `AcquireInstance` / `svc.Start` 之前执行并返回（与 `-test-webhook` 同构）。

### 6. 文档与测试

- README 能力表、配置说明、运行示例；`config.yaml.example` 同步。
- 单测：`BuildTestMail` 头字段与中文编码、config 条件校验、ConfigView 脱敏、API 未配置时的错误码；真实发送不做自动测试。

## 关键文件

- `internal/config/config.go`
- `internal/runtime/runtime.go`、`internal/runtime/config_view.go`、`internal/runtime/testmail.go`（新增）
- `internal/api/server.go`
- `internal/app/gui.go`
- `internal/web/assets/index.html`、`internal/web/assets/app.js`
- `cmd/mail2feishu/cli.go`
- `config.yaml.example`、`README.md`

## 验证

1. `go test ./... -race`、`go vet ./...`
2. `uv run scripts/build.py` 产出 GUI / CLI 双通道
3. GUI：配置页填 163 地址与授权码 → 保存 → 点「发送测试邮件」→ QQ 收到邮件 → 审计出现 `whitelisted` 与 `pushed`（白名单需包含 163 地址或对应规则）
4. CLI：`mail2feishu-cli-dev.exe -send-test`
5. 未配置时应提示「请先在配置页填写测试发信账号」，不崩溃、不发送

## 安全与注意

- 授权码只落本地 `config.yaml`（0600、gitignore）；代码、日志、API 响应均不回显。
- 用户已在对话中暴露过 163 授权码，建议测试完成后到网易邮箱删除该授权码并重新生成。
- 163 → QQ 属外部来信，正常进 INBOX；若进垃圾箱需在 QQ 邮箱设置中放行。
- 白名单若不含 163 发件人，审计显示 `dropped`，不会推送（这本身也是一次有效验证）。
