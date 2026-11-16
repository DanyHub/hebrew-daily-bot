// D1 access for the users table. Every query is parameterised.

export function makeDb(d1) {
  return {
    async get(chatId) {
      return d1
        .prepare("SELECT chat_id, lang, level, active, last_sent FROM users WHERE chat_id = ?")
        .bind(chatId)
        .first();
    },
    /** Create the user, or reactivate an existing one (keeps their language and level). */
    async upsert(chatId) {
      await d1
        .prepare(
          "INSERT INTO users (chat_id) VALUES (?) " +
            "ON CONFLICT(chat_id) DO UPDATE SET active = 1, updated_at = datetime('now')",
        )
        .bind(chatId)
        .run();
    },
    async setLang(chatId, lang) {
      await d1
        .prepare("UPDATE users SET lang = ?, updated_at = datetime('now') WHERE chat_id = ?")
        .bind(lang, chatId)
        .run();
    },
    async setLevel(chatId, level) {
      await d1
        .prepare("UPDATE users SET level = ?, updated_at = datetime('now') WHERE chat_id = ?")
        .bind(level, chatId)
        .run();
    },
    /** Remember the day (Israel date) a person last received a lesson, so nobody gets it twice. */
    async setLastSent(chatId, day) {
      await d1
        .prepare("UPDATE users SET last_sent = ?, updated_at = datetime('now') WHERE chat_id = ?")
        .bind(day, chatId)
        .run();
    },
    /** Active, fully set-up people who have not had the lesson of `day` yet (at most `limit`). */
    async dueUsers(day, limit) {
      const { results } = await d1
        .prepare(
          "SELECT chat_id, lang, level, last_sent FROM users " +
            "WHERE active = 1 AND lang IS NOT NULL AND level IS NOT NULL " +
            "AND (last_sent IS NULL OR last_sent <> ?) ORDER BY chat_id LIMIT ?",
        )
        .bind(day, limit)
        .all();
      return results || [];
    },
    async setActive(chatId, active) {
      await d1
        .prepare("UPDATE users SET active = ?, updated_at = datetime('now') WHERE chat_id = ?")
        .bind(active ? 1 : 0, chatId)
        .run();
    },
  };
}
