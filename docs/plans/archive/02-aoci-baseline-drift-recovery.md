# language_projects 父仓 AOCI 基线指纹漂移修复计划

## 项目概述

父仓 AOCI（v0.1.0-rc14，Volumes v1 布局）的正式索引仅有 7 行 Volume 骨架 Header（`entry_count=0`），Baseline 指纹停留在多轮目录迁移前的布局，形成复合漂移：

- 438 actionable missing（管理面要求有 Entry 的文件全部缺失）
- 427 unbaselined（当前树未入基线）+ 5 stale
- 70 条 observe 待审 = 35 新增 + 35 移除（实为同一批测试文件从 `.archived/<lang>/` 搬到 `.archived/projects/<lang>/`）
- 治理阻塞合计 871；`scope preview` stage=`observed_evidence_review_required`
- 16 项 requires_human_review 均为良性安全排除（`.aoci` 运行时×4、wails build 产物×9、4 个子模块边界）

核心需求（用户已拍板）：

1. `.archived/**` 整体 exclude（归档停更项目不再产生指纹漂移）
2. `docs/projects/**` 进 Entry 语义管理（一次到位，约 75 个）
3. `scope acknowledge` 由 AI 受托执行（reviewed-by 记用户名义）

## 目标状态（核心数据结构）

**新增 project-owned Scope 规则（2 条）：**

```json
[
  {
    "rule_id": "proj-archived-excluded",
    "action": "exclude",
    "pattern": ".archived/**",
    "pattern_kind": "glob",
    "reason": "归档停更项目不维护语义；防止归档目录迁移反复制造基线指纹漂移",
    "created_by": "user:shihao-hub"
  },
  {
    "rule_id": "proj-assets-excluded",
    "action": "exclude",
    "pattern": "docs/assets/**",
    "pattern_kind": "glob",
    "reason": "跨项目二进制资源（图标等）无文本语义可写 Entry",
    "created_by": "user:shihao-hub"
  }
]
```

**量化验收指标：**

| 指标 | 现值 | 目标 |
|---|---|---|
| observed_pending_review | 70 | 0 |
| drift.unbaselined / stale | 427 / 5 | 0 / 0 |
| drift.missing（authoring targets） | 438 | 0（排除后约 99 个逐一补齐） |
| entry_count | 0 | ≈100 + Header/Meta |
| governance_blocker_count | 871 | 0 |
| `aoci verify` / `aoci check` | 未通过 | 通过 |

精确数字以机器 `scope preview --json` 返回为准。

## 对外接口设计（治理命令面）

| 阶段 | 命令 | 作用 | 产物 |
|---|---|---|---|
| 范围 | `scope rule add <id> --action exclude --pattern ... --reason ... --created-by user:shihao-hub` | 收窄管理面 | config 内规则 |
| 证据 | `scope acknowledge --reviewed-by "user:shihao-hub(opencode)"` | 推进 observe 待审指纹 | ledger 记录 |
| 事务 | `scope plan` → `scope authorize --preview-file <f>` → `scope apply --preview-file <f> --authorization-file <f>` | Managed Scope + Entry + Baseline + observe 一个原子事务 | preview/authorization JSON artifact |
| 基线备选 | `baseline scope plan/preview/apply` | 单独的 Safe Inventory 基线刷新（若 scope apply 未覆盖时使用） | baseline-scope artifact |
| 建索引 | `index agent`（Guide 入口）→ `cognition plan bootstrap` → `cognition bootstrap` | Volume Bootstrap 编排，Guide 权威驱动 | aoci.meta.txt / aoci.code.txt |
| 写 Entry | MCP `aoci_maintain` → `aoci_update_entry`（code_batch_id + candidate_id + source_sha256 原样保留） | 模型逐批 authoring | 正式 Entries |
| 验证 | `aoci verify`、`aoci check`、`scope preview --json`、可选 `index score` | 治理对齐证明 | verify_history |

artifact 一律放 `C:\Users\29580\AppData\Local\Temp\opencode\`（已批准的临时目录），不入仓。

## 核心模块设计

### 顺序约束（不可颠倒）

**先 exclude、再 acknowledge、最后 apply**：若先把搬家后的 `.archived/projects/<lang>` 测试文件指纹收进新基线、再排除 `.archived`，基线立刻二次漂移。排除规则生效后，35/35 的 observe 位移大概率自动离开管理面，acknowledge 兜底处理剩余项。

### 事务失败路径

- `repair_required`：只修 findings 明示的候选（retry_scope），同批完整重提
- `stopped`：查 `failed_step` → `scope resume`（有可证 postimage 的完整 Intent）或 `scope rollback`（exact preimage）后重规划；**绝不手改 `.aoci/baseline.json`**
- 审批 artifact 缺失被拒：按 `scope authorize`/`--approval-file` 的返回补齐重试

### Entry authoring 纪律

- 写前必读源文件全文，禁止按文件名/路径猜语义（AOCI 模型生成-模型读循环）
- 每批 ≤20 个（机器 code_cognition_batch_entries 默认值），`remaining>0` 就对新 preimage 再次 Maintain，**不切片机器批次**
- Header/Meta 先行：tag 字典与校准示例决定后续所有 Entry 质量

## 实现步骤（分阶段）

### Phase 1 范围收窄与治理事务（~0.5h）

- [x] 1.1 `scope rule add proj-archived-excluded ...` + `scope rule add proj-assets-excluded ...`（参数见上）
- [x] 1.2 `scope preview --json` 复核：missing/unbaselined 不再含 `.archived/**` 与 `docs/assets/**`；authoring_targets = 92（机器实测，略低于预估 99）
- [x] 1.3 observe 待审推进：`scope acknowledge --reviewed-by "user:shihao-hub(opencode-glm-5.3-flash)"`——实测必须在规则添加**之前**执行（预期策略下 pending=0 会拒绝、活动策略下 70 条未推进会卡 preview 闸门），已按"临时移除规则 → acknowledge → 恢复规则"顺序完成（事务 13493988…，policy_bound_auto）
- [x] 1.4 治理事务：`.aoci/scope-change/candidates.json`（空候选集）→ `scope preview --candidate-file … > preview.json` → `scope apply --preview-file …`（事务 37631a66…，policy_bound_auto，无需 TTY 审批）；注意 PowerShell 5.1 `>` 会写 UTF-16 必须 WriteAllText 落盘
- [x] 1.5 验收通过：stage=`authoring_required`，policy/budget 双对齐，pending_review=0，drift.unbaselined/observed_new/observed_removed/orphan 全 0，index-role 95 / authoring targets 92

### Phase 2 Header 与 Meta Volume authoring（~0.5h）

- [x] 2.1 `aoci index agent --json` 获取当前 Guide，按 Guide 进入 bootstrap 流程（实测 Guide 指向 MCP `aoci_maintain` 路径，Header/Meta 字典已完备，无需独立 bootstrap）
- [x] 2.2 按 Guide 要求补全 Header / aoci.meta.txt（项目规则、tag 字典、校准示例）——Meta 字典已就位，authoring 契约由 Guide 下发
- [x] 2.3 验收：Guide 阶段推进至 authoring 批次下发

### Phase 3 Code Entry：根目录 + 基础设施文档（实际 2 批 40 个）

- [x] 3.1 批 1（20 个）：根目录 8 文件 + `.scripts/` 4 脚本 + docs/guides 6 GUIDE + `.gitattributes/.gitignore/.gitmodules`
- [x] 3.2 批 2（20 个）：docs/guides/README、docs/plans 01+02、docs/projects/go_projects 文档树（CLI 标准、clictl、exestarter、glmquotawatch、liteconf/brunos）
- [x] 3.3 验收：各批 remaining 递减正常，`aoci_update_entry` 全部 applied

### Phase 4 Code Entry：docs/projects/**（实际 3 批 52 个）

- [x] 4.1 批 3（20）：liteconf brunos 收尾 + liteconf plans/specs + projstat specs + 统一核心指南 + django-lab + llm-lab 01
- [x] 4.2 批 4（20）：llm-finetune-lab 全套 + rag_lab + tech_learning_room 11 篇
- [x] 4.3 批 5（10）：zedhub 协议 + minieverything 笔记 + taskmon 5 篇 + tooldeck PLAN + docs/repo 2 篇
- [x] 4.4 尾项：SPEC-AGENT/SPEC-HUMAN 为 0 字节空占位（pending_curation），经兼容单对象模式诚实落"空占位"Entry（Curation 排除通道在 Volumes v1 被闸口关闭）
- [x] 4.5 验收：`aoci_update_entry` aligned=true、remaining=0、findings=[]；修复过一次 tag 字典违规（B=K 不存在，改 B=A）与 7 处 E 档位 warning

### Phase 5 终验与收尾（~0.5h）

- [x] 5.1 `aoci verify`（governance_aligned=true, result=aligned, findings=[]）+ `aoci check`（ok=true, next_action=none）
- [x] 5.2 `index agent guide`：mode=complete, stage=aligned, complete=True, next=none；92/92 Entry，whole_index 9906 tokens（预算 200000），零漂移
- [x] 5.3 整体汇报 + git commit 命令（父仓范围：aoci.code.txt、.aoci/baseline.json、.aoci/config.json、docs/plans/02-*.md）

## 技术依赖

- `C:\Users\29580\AppData\Local\Programs\aoci\aoci.exe`（rc14）——唯一治理工具
- MCP `aoci`（opencode.json 全局配置）——maintain/update_entry/overview 通道
- `ai.enabled=false` 保持不变：不配置 AI 端点，Entry 全部由会话模型直接写

## 关键技术点

1. **排除先行**：避免把即将出管理面的路径写进新基线造成二次漂移（见"顺序约束"）
2. **原子事务 + 可恢复**：scope apply 走 lock/CAS/Recovery，ledger.jsonl 全程审计；rollback 有 exact preimage
3. **authoring 证据绑定**：每个 Entry 的 F/R/A/S 来自读到的文件内容，source_sha256/candidate_id 原样透传，机器校验
4. **子模块边界**：go/python/rust/typescript_projects 目录由安全边界自动排除（unsafe_filesystem_object），**不建规则**、不碰子模块内容
5. **24 个 untracked 文件**（SPEC-×2、docs/assets、glmquotawatch/liteconf/rag_lab）照常按磁盘事实建 Entry；是否 git 入库由用户另行决定，不属于本任务

## 预计时间

| Phase | 估时 |
|---|---|
| 1 范围收窄与治理事务 | 0.5h |
| 2 Header/Meta | 0.5h |
| 3 根目录+基础设施 Entry | 1h |
| 4 docs/projects Entry | 2.5-3h |
| 5 终验收尾 | 0.5h |
| **总计** | **≈5-5.5h** |

## 后续扩展（二期）

- 五个语言子仓各自建立独立 AOCI 认知（各自会话处理，父仓不越界）
- 细化 observe 规则（如对 docs/scripts 的 ps1/py 变更做观察）
- 启用 `aoci ui` 本地只读状态页

## 注意事项

- 16 项 requires_human_review 为良性安全排除，在 apply 事务中一并确认
- 执行期间用户不再改动根文件与 docs/**，否则 source_sha256 失配需重走 candidate（外部改动以机器返回为准，不手工对账）
- 全程不修改任何业务文件内容；只写 AOCI 管理资产（aoci.txt、aoci.meta.txt、aoci.code.txt、.aoci/）与本计划文件
- PowerShell 下所有含中文/空格的路径参数加引号

---
**最后更新：** 2026-09-19
**作者：** AI & User
**版本：** v1.1（执行完毕，全部 Phase 验收通过；实测与计划的偏差已就地批注）
