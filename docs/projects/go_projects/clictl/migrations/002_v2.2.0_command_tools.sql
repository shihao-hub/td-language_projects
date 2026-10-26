-- clictl 表结构存档 002：v2.2.0 双目标（exe + 源码命令）与启动记录 target/mode
-- 数据库：%APPDATA%\language_projects\clictl\{dev,prod}\clictl.db（WAL + foreign_keys=ON）
-- 说明：本文件为文档存档，运行时迁移由 internal/store/store.go 的
--       schemaTables + migrateToolsV3 + migrateLaunches 执行；clictl 不读取本文件。
--
-- 运行时顺序（单连接；PRAGMA foreign_keys 必须在事务外切换）：
--   1. PRAGMA foreign_keys=OFF
--   2. CREATE TABLE tools_new (...)                      -- 下方 tools v3 定义
--   3. INSERT INTO tools_new (...) SELECT id,name,description,status,meta,added_at,
--        'exe', path, '', '', '[]', 'gui' FROM tools;    -- 旧 path → exe_path
--   4. DROP TABLE tools
--   5. ALTER TABLE tools_new RENAME TO tools
--   6. UPDATE sqlite_sequence SET name='tools' WHERE name='tools_new'
--   7. ALTER TABLE launches ADD COLUMN pid INTEGER       -- 若缺
--   8. ALTER TABLE launches ADD COLUMN target TEXT       -- 若缺
--   9. ALTER TABLE launches ADD COLUMN mode TEXT         -- 若缺
--  10. 创建下方 partial unique indexes
--  11. PRAGMA foreign_keys=ON
--
-- tools v3：
--   id              INTEGER PRIMARY KEY AUTOINCREMENT
--   name            TEXT NOT NULL UNIQUE COLLATE NOCASE
--   description     TEXT NOT NULL DEFAULT ''
--   status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','invalid'))
--   meta            TEXT
--   added_at        TEXT NOT NULL
--   default_target  TEXT NOT NULL DEFAULT 'exe' CHECK (default_target IN ('exe','source'))
--   exe_path        TEXT NOT NULL DEFAULT '' COLLATE NOCASE
--   source_program  TEXT NOT NULL DEFAULT '' COLLATE NOCASE
--   source_workdir  TEXT NOT NULL DEFAULT '' COLLATE NOCASE
--   source_args     TEXT NOT NULL DEFAULT '[]'                 -- JSON 数组，如 ["run","zedhub-gui"]
--   source_type     TEXT NOT NULL DEFAULT 'gui' CHECK (source_type IN ('gui','console'))
--
-- 语义：
--   - exe_path 与 source_program 至少一个非空（应用层校验）
--   - default_target 必须指向实际存在的目标（服务层归一化，删除目标时自动切换）
--   - status 为总体状态：任一目标有效 = active；per-target 状态在服务层实时计算
--
-- partial unique indexes：
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_exe_path
  ON tools(exe_path) WHERE exe_path <> '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_tools_source
  ON tools(source_program, source_workdir, source_args)
  WHERE source_program <> '';
CREATE INDEX IF NOT EXISTS idx_launches_tool
  ON launches(tool_id, started_at DESC);
