// Thin Telegram Bot API client. Never throws on an API error: logs it (without the token) and returns the response.

export function makeTelegram(env, fetchImpl = fetch) {
  const base = `${env.TELEGRAM_API || "https://api.telegram.org"}/bot${env.TELEGRAM_BOT_TOKEN}`;

  async function call(method, payload) {
    try {
      const res = await fetchImpl(`${base}/${method}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({ ok: false, description: `HTTP ${res.status}` }));
      if (!data.ok) console.error(`telegram ${method} failed:`, data.error_code, data.description);
      return data;
    } catch (err) {
      console.error(`telegram ${method} error:`, err && err.message);
      return { ok: false, description: String(err && err.message) };
    }
  }

  return {
    sendMessage: (chat_id, text, extra = {}) => call("sendMessage", { chat_id, text, ...extra }),
    editMessageText: (chat_id, message_id, text, extra = {}) =>
      call("editMessageText", { chat_id, message_id, text, ...extra }),
    answerCallbackQuery: (callback_query_id, extra = {}) =>
      call("answerCallbackQuery", { callback_query_id, ...extra }),
  };
}
