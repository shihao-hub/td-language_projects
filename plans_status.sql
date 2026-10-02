
-- plan mutation at 2026-09-29 21:52:04
INSERT INTO plan_spec_status (type, path, status, created_at, updated_at)
VALUES ('plan', 'docs/plans/28-plansql-tracker.md', '{"state":"completed"}', '2026-09-29 21:52:04', '2026-09-29 21:52:04')
ON CONFLICT(path) DO UPDATE SET
    type = excluded.type,
    status = excluded.status,
    updated_at = excluded.updated_at;

-- plan mutation at 2026-09-29 21:52:45
INSERT INTO plan_spec_status (type, path, status, created_at, updated_at)
VALUES ('plan', 'docs/plans/28-plansql-tracker.md', '{"state":"completed"}', '2026-09-29 21:52:45', '2026-09-29 21:52:45')
ON CONFLICT(path) DO UPDATE SET
    type = excluded.type,
    status = excluded.status,
    updated_at = excluded.updated_at;
