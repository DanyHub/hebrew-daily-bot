-- Allow level 3 (advanced). SQLite cannot change a CHECK constraint in place, so the table is rebuilt
-- and every existing row is copied across unchanged.
CREATE TABLE users_new (
  chat_id    INTEGER PRIMARY KEY,
  lang       TEXT CHECK (lang IN ('fr', 'en')),
  level      INTEGER CHECK (level IN (1, 2, 3)),
  active     INTEGER NOT NULL DEFAULT 1,
  last_sent  TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO users_new (chat_id, lang, level, active, last_sent, created_at, updated_at)
  SELECT chat_id, lang, level, active, last_sent, created_at, updated_at FROM users;

DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

CREATE INDEX IF NOT EXISTS idx_users_active ON users (active);
