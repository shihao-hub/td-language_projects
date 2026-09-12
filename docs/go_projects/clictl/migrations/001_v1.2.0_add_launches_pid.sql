-- clictl 表结构存档 001：launches 加 pid 列（v1.2.0，2026-09-12）
-- 变更原因：start 后台分离启动需要记录子进程 PID，供 list --running / info / stop 探活
-- 涉及表：launches
-- 语义：pid 仅 start 命令写入；run（前台透传）记录恒 NULL；
--       未闭环后台启动 = pid IS NOT NULL AND duration_ms IS NULL
-- 执行方式：新库由 store.go schema 常量直接建含 pid 的表；存量库由 Open() 内
--           migrate() 检测 PRAGMA table_info(launches) 无 pid 列后自动执行本语句。
--           本文件为文档存档（人工审阅 / 手工复现用），clictl 不读取本文件

ALTER TABLE launches ADD COLUMN pid INTEGER;
