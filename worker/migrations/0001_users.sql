-- One row per Telegram private chat. Only what the bot needs: no names, no usernames.
CREATE TABLE IF NOT EXISTS users (
  chat_id    INTEGER PRIMARY KEY,
  lang       TEXT CHECK (lang IN ('fr', 'en')),
  level      INTEGER CHECK (level IN (1, 2)),
  active     INTEGER NOT NULL DEFAULT 1,
  last_sent  TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_active ON users (active);
