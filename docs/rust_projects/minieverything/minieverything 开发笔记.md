# minieverything 开发笔记

> 项目位置：`rust_projects/minieverything/`（子仓 monorepo 内独立项目）

## 需求背景

做一个 Everything（voidtools）的简单 CLI 版：全盘文件名索引 + 秒级搜索。澄清后确认的技术路线：

- **语言**：Rust（`windows-rs` 对 NTFS 底层 API 支持完整）
- **索引**：一期目录遍历建索引（非 MFT 直读）+ **USN Journal 增量**
- **功能**：子串 / 通配符 / 正则 / 大小写开关 / 类型过滤
- **更新策略**：查询时自动增量（无权限自动降级）

## 架构

```
src/
├── main.rs    # clap CLI：update / status / 直接搜索
├── volume.rs  # NTFS 卷枚举（GetLogicalDrives + GetVolumeInformationW）
├── scan.rs    # jwalk 并行遍历 + 目录 file_ref 采集（CreateFileW + BY_HANDLE_FILE_INFORMATION）
├── index.rs   # 索引结构 + bincode 持久化（原子替换）+ 路径操作
├── usn.rs     # USN Journal 查询/创建/读取/增量应用
└── search.rs  # 子串/通配符/正则匹配
```

### 数据结构

- `entries: Vec<{path, is_dir}>`——全量条目
- `dirs: HashMap<u64 file_ref, String path>`——**仅目录**的 MFT 引用号映射，USN 增量靠它把 `parent_ref + 文件名` 解析为完整路径
- `volumes: Vec<{root, journal_id, next_usn}>`——各卷 USN 游标

### 为什么只给目录建 ref 映射？

文件数量 ≫ 目录数量（典型 10:1），为每个文件开句柄拿 ref 太慢；而 USN 记录的 `ParentFileReferenceNumber` 一定是目录，只需目录映射即可解析路径。全量扫描后批量 `CreateFileW(FILE_FLAG_BACKUP_SEMANTICS)` + `GetFileInformationByHandle` 采集（约 35 万目录几秒内完成）。注意**卷根本身也要入库**（scan 跳过 depth==0，需额外补 `dir_file_ref(root)`），否则根目录下新建文件解析不了父路径。

## USN 增量的坑（实操记录）

实现过程中踩过的坑，均有对应处理：

1. **`USN_JOURNAL_DATA` 实际是 56 字节（7×u64）**——不是 48。缓冲给小了返回 `ERROR_INVALID_USER_BUFFER (0x800706F8)`，而不是直觉上的 `ERROR_INSUFFICIENT_BUFFER`。解法：直接用 windows-rs 的 `USN_JOURNAL_DATA_V1` 类型化结构体。
2. **`READ_USN_JOURNAL_DATA_V0` 第 6 个字段是 `UsnJournalID`**——不是 BytesToReturn！必须携带 QUERY 得到的 journal_id，驱动用它检测 journal 重建竞态，缺失时读取被拒。
3. **`USN_RECORD_V2` 的文件名偏移要用记录内 `FileNameOffset` 字段**（V2 通常为 60），不能硬编码 58——58 位置上是 FileNameOffset 本身（56 是 FileNameLength）。
4. **目录改名只产生一条目录自身的 RENAME 记录**，子项不会有记录。路径导向的索引必须对整棵子树做前缀重写；且前缀匹配要按**路径段边界**（`C:\a` 改名不得误伤 `C:\ab`）。
5. **改名可能拆成两条记录**（RENAME_OLD 携旧名/旧父、RENAME_NEW 携新名/新父），也可能合并为一条（此时 parent/name 即新位置）。两条式需要 `pending_renames: HashMap<file_ref, old_path>` 衔接；上半程对目录**不能删除条目**，等下半程整体前缀重写。
6. **USN Journal 可能不存在**：`FSCTL_QUERY_USN_JOURNAL` 返回 `ERROR_JOURNAL_NOT_EXIST (1178)` 时用 `FSCTL_CREATE_USN_JOURNAL`（全 0 输入 = 系统默认尺寸）创建。顺序：先建 journal 再扫描，扫描期间的变更留待下次增量幂等补上。
7. **读追平时**可能返回 `ERROR_HANDLE_EOF (38)`，按正常结束处理。

## 降级策略

- 非管理员：打开 `\\.\C:` 被拒 → 游标记 0 → 后续增量自动跳过，搜索退化为纯离线查询；管理员首次接管时采纳当前 NextUsn 为游标（不回放历史避免重复应用），提示 `--rebuild` 可精确同步。
- journal 重建 / 环形覆盖（游标落后于 LowestValidUsn）：`update` 触发该卷全量重扫；搜索前刷新则不重扫（避免意外长阻塞），仅提示。

## 性能实测（2026-09，2 卷 220 万条目）

| 操作 | 耗时 |
|---|---|
| 全量扫描 + 目录 ref 采集（冷缓存） | ~46s |
| 全量扫描（热缓存） | ~17s |
| 子串搜索（220 万条） | 300~400ms |
| USN 增量（追平） | <100ms |

## 二期方向（未做）

- MFT 直读（`FSCTL_ENUM_USN_DATA`）替代目录遍历，建索引从分钟级降到秒级
- 布尔/多关键词搜索（AND/OR）、结果排序
- 常驻守护进程实时 USN 监听
- 非 NTFS 卷的降级遍历索引
