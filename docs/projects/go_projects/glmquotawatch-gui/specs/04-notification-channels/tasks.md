# Task List

- [ ] 1. store 层扩展：`Config.Notify` 渠道列表 + `State.Channels` 逐渠道记账 + 旧状态迁移
  - Files: `internal/store/store.go`
  - 实现细节：按 design §3 增加 `ChannelConfig`/`ChannelState` 类型与字段；`LoadState` 加入迁移不变量（`Channels == nil && len(Notified) > 0` → 映射为 `toast` 渠道）；`LoadConfig` 对缺失 `notify` 字段返回空切片而非报错。不改动既有字段语义与原子写实现。
  - Verify: `go build ./...`（退出码 0）；`go test ./internal/store/...`（既有 store 用例仍通过）
  - Ref: AC-4

- [ ] 2. 新建 `internal/notify` 包骨架：Message/Alert/Channel/Delivery/Dispatcher
  - Files: `internal/notify/message.go`、`internal/notify/channel.go`
  - 实现细节：按 design §1 定义类型；Dispatcher 用 `sync.WaitGroup` 并发、`context.WithTimeout(10s)` 单渠道超时、`budget=20s` 整批预算，结果按配置顺序返回；`Message.PlainBody()` 提供渠道通用正文渲染。
  - Verify: `go build ./...`；`go test ./internal/notify/... -run Dispatcher`（并发顺序、部分失败、超时三条用例通过）
  - Ref: AC-3

- [ ] 3. toast 渠道化 + GUI 侧组装（行为与现状一致）
  - Files: `internal/notify/toast.go`、`internal/guiapp/runtime.go`
  - 实现细节：`NewToast(name, send func(title, body string, silent bool) error)`；`runtime.go` 把 `r.ns.SendNotification` 包成回调注入，组装 `Dispatcher`，替换 `runtime.go:240` 处的 `toastNotifier{...}`；删除原 `toastNotifier` 类型。
  - Verify: `uv run scripts/build-dev.py` 成功产出 `bin\glmquotawatch-gui-dev.exe`；`Taskfile.yml` 的 dev 任务可启动 GUI，托盘/主窗无回归
  - Ref: AC-4

- [ ] 4. smtp 渠道实现（QQ 邮箱 465/587 双路径）
  - Files: `internal/notify/smtp.go`
  - 实现细节：按 design §1 的 smtp.go 卡片；`security=ssl` 走 `tls.Dial` + `smtp.NewClient`，`starttls` 走 `smtp.Dial` + `StartTLS`；主题 `{subject_prefix}{title}`，正文 `PlainBody()`；`to` 支持逗号分隔多收件人；错误分类为 `notify_auth_failed` / `notify_unreachable` / `notify_rejected`。
  - Verify: `go test ./internal/notify/... -run SMTP`（注入假 dialer 的用例通过）；真机验证放在任务 13
  - Ref: AC-1

- [ ] 5. http 渠道实现（通用 Webhook/机器人/短信网关）
  - Files: `internal/notify/http.go`
  - 实现细节：按 design §1 的 http.go 卡片；`strings.NewReplacer` 渲染 `{{title}}/{{body}}/{{time}}/{{windows}}`；`headers.<Name>` 机制；`expect_status` 默认 2xx；`headers.*` 值含 CR/LF 时报 `bad_value`（头注入防护）。
  - Verify: `go test ./internal/notify/... -run HTTP`（`httptest` 断言 method/header/body 渲染结果、2xx 与 5xx 分支）
  - Ref: AC-2

- [ ] 6. preset 表与配置构造/校验
  - Files: `internal/notify/presets.go`、`internal/notify/factory.go`
  - 实现细节：按 design §1 的 preset 表实现 9 条 preset（feishu/wecom/serverchan/pushplus/bark/ntfy/onebot/sms-generic/custom），`feishu` 的 `secret` 签名（`base64(HMAC-SHA256(key=timestamp, data=timestamp+"\n"+secret))`）随 body 一起发送；`Validate` 覆盖 name/kind/端口/security/url/参数白名单六类规则；`Build` 由 `ChannelConfig` 构造 `Channel`。
  - Verify: `go test ./internal/notify/... -run 'Preset|Validate'`（每条 preset 的必填校验与渲染快照用例通过）
  - Ref: AC-2, AC-5

- [ ] 7. service 层：Notifier 契约升级 + 渠道用例 + 脱敏视图 + 配置指纹
  - Files: `internal/service/service.go`
  - 实现细节：按 design §2 替换 `Notifier` 接口；新增 `ChannelView`/`ChannelInput` 与 `ListChannels/AddChannel/UpdateChannel/RemoveChannel/SetChannelEnabled/TestChannel`；`ConfigView` 增加 `Notify`；脱敏函数对 `SecretKeys` 命中的值输出 `前4…后4`；新增渠道指纹函数（name+kind+preset+params 的稳定哈希）供 daemon 判断是否需要重建 Dispatcher；错误码沿用 `bad_value`/`conflict`/`not_found`。
  - Verify: `go test ./internal/service/...`（用例覆盖：重名 conflict、非法端口 bad_value、TestChannel 不写 state、脱敏输出无明文）
  - Ref: AC-3, AC-5

- [ ] 8. daemon 改造：分发 + 逐渠道独立记账 + 回落清理
  - Files: `internal/service/daemon.go`
  - 实现细节：按 design §2 的 daemon 卡片；构造 `notify.Message`（Alerts 来自 pending）；仅对成功渠道 merge `Newly` 到 `state.Channels[名].Notified`，失败渠道写 `LastErr/LastAt/LastOK=false` 并保留 pending；全部失败不 merge；`Cleared` 时从所有渠道删除该 key；每轮 tick 检查渠道指纹，变化则重建 Dispatcher（热加载）。
  - Verify: `go test ./internal/service/... -run Daemon`（首轮跨档投递、单渠道失败仅该渠道重试、全失败不记账、指纹变化后新渠道生效四条用例通过）
  - Ref: AC-1, AC-3, AC-6

- [ ] 9. CLI：`notify` 命令组 + schema 契约同步
  - Files: `internal/cli/root.go`、`internal/cli/schema.go`
  - 实现细节：按 design §4 实现 7 个子命令与 `--set`/`--params -` 合并规则；全部走 `outOK/outErr` 信封；`schema.go` 追加命令与输出视图描述，并保证 `schema` 分支零网络 I/O。
  - Verify: `bin\glmquotawatch-gui-dev.exe schema`（新命令出现在契约 JSON 中，且耗时 <100ms）；`bin\glmquotawatch-gui-dev.exe notify list`（返回 `{"ok":true,...}`）
  - Ref: AC-5

- [ ] 10. GUI：渠道管理绑定与偏好配置页
  - Files: `internal/guiapp/bindings.go`、`frontend/src/**`
  - 实现细节：新增 6 个绑定方法（返回脱敏视图与业务错误码）；偏好配置页新增"通知渠道"区（列表含启用开关、kind/preset、最近投递状态与错误摘要；新增/编辑对话框按 kind/preset 动态渲染字段，密钥字段 `type=password` 且展示脱敏占位；提供"发送测试"按钮）。
  - Verify: `uv run scripts/build-dev.py` 成功；启动 dev GUI 手工核对：新增一条 `http`+`feishu` 渠道后能看到脱敏回显，点"发送测试"能看到成功/失败提示
  - Ref: AC-2, AC-5

- [ ] 11. 适配既有测试（fake notifier → dispatcher 版本）
  - Files: `internal/service/daemon_test.go`、`internal/cli/cli_test.go`、`internal/store/store_test.go`
  - 实现细节：把 `fakeNotifier` 改为返回 `[]notify.Delivery` 的 fake；补充旧 state 迁移用例（`channels` 缺失 + `notified` 存在 → 不重复告警）。执行阶段默认跳过本任务，仅保留为验收信息。
  - Verify: `go test ./...`（全绿）
  - Ref: AC-4
  - [test]

- [ ] 12. 文档：README「通知渠道」章节 + 免费额度与风险说明
  - Files: `README.md`
  - 实现细节：列出三种 kind 与 9 条 preset 的必填字段示例；写明 QQ 邮箱用授权码而非登录密码；写明免费边界——飞书/企业微信机器人、Bark、ntfy 免费；Server酱/PushPlus 有免费额度但限频；**短信没有长期免费渠道**，只有云厂商新用户赠送（需实名 + 模板报备），并提示个人微信/QQ 协议级机器人的封号风险不在支持范围。
  - Verify: 人工通读 README 新增章节，字段示例与 `notify add --set` 用法逐条对得上
  - Ref: FR-11

- [ ] 13. 端到端冒烟：dev 构建 + 真机渠道投递
  - Files: 无代码改动（仅验证）
  - 实现细节：用 dev 数据目录（`%APPDATA%\language_projects\glmquotawatch-gui\dev`）配置两条真实渠道：QQ 邮箱 smtp 与飞书自定义机器人；跑 `notify test` 各发一条；再手工把阈值临时调低触发一次真实告警，确认两条渠道都收到且 `state.json` 的 `channels` 里记录正确。
  - Verify: `bin\glmquotawatch-gui-dev.exe notify test --name qqmail`（QQ 邮箱收到邮件）；`... notify test --name feishu`（飞书群收到消息）；`state.json` 中 `channels.<名>.last_ok == true`
  - Ref: AC-1, AC-2
