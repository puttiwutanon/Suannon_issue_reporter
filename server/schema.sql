-- Run once to create the table in D1:
--   npx wrangler d1 execute skn-issue-reporter --remote --file=./schema.sql

CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    line_user_id TEXT NOT NULL,
    reporter_name TEXT,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT,
    latitude REAL,
    longitude REAL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    student_year TEXT,
    student_class TEXT,
    student_number TEXT,
    issue_type TEXT DEFAULT 'urgent',
    fix_image_url TEXT,
    resolved_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_issues_line_user_id ON issues (line_user_id);
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues (status);
CREATE INDEX IF NOT EXISTS idx_issues_created_at ON issues (created_at);
