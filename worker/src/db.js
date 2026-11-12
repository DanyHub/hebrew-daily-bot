// D1 access for the users table. Every query is parameterised.

export function makeDb(d1) {
  return {
    async get(chatId) {
      return d1
        .prepare("SELECT chat_id, lang, level, active FROM users WHERE chat_id = ?")
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
    async setActive(chatId, active) {
      await d1
        .prepare("UPDATE users SET active = ?, updated_at = datetime('now') WHERE chat_id = ?")
        .bind(active ? 1 : 0, chatId)
        .run();
    },
  };
}
