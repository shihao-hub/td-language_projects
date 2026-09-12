-- clictl 表结构存档 000：初始建表（v1.0.0，2026-09-11 追溯快照）
-- 数据库：%AppData%\clictl\clictl.db（SQLite，WAL + busy_timeout=2s + foreign_keys=ON）
-- 说明：本文件为文档存档，运行时建表由 store.go 的 schema 常量执行，clictl 不读取本文件

CREATE TABLE IF NOT EXISTS tools (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- 调用名，统一小写存储
  path        TEXT NOT NULL UNIQUE COLLATE NOCASE,   -- 绝对路径，Clean 后
  description TEXT NOT NULL DEFAULT '',
  status      TEXT NOT NULL DEFAULT 'active'
              CHECK (status IN ('active','invalid')),  -- 上次校验时的文件状态
  meta        TEXT,                                    -- 扩展 JSON；应用层白名单 + 4KB 硬限
  added_at    TEXT NOT NULL                            -- UTC RFC3339（9 位纳秒）
);

CREATE TABLE IF NOT EXISTS launches (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tool_id     INTEGER NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
  started_at  TEXT NOT NULL,                           -- UTC RFC3339（9 位纳秒）
  duration_ms INTEGER,                                 -- NULL = 未正常结束
  exit_code   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_launches_tool
  ON launches(tool_id, started_at DESC);
