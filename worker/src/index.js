import { handleUpdate } from "./bot.js";

const SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token";

/** Constant-time string comparison (length is not secret here). */
export function safeEqual(a, b) {
  if (typeof a !== "string" || typeof b !== "string" || a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return new Response("hebrew-daily-bot: ok");
    }

    if (request.method === "POST" && url.pathname === "/webhook") {
      // Only Telegram knows the secret it was registered with.
      if (!env.WEBHOOK_SECRET || !safeEqual(request.headers.get(SECRET_HEADER) || "", env.WEBHOOK_SECRET)) {
        return new Response("forbidden", { status: 403 });
      }
      let update;
      try {
        update = await request.json();
      } catch {
        return new Response("bad request", { status: 400 });
      }
      // Answer Telegram right away; do the work after the response.
      ctx.waitUntil(
        handleUpdate(update, env).catch((err) => console.error("update failed:", err && err.message)),
      );
      return new Response("ok");
    }

    return new Response("not found", { status: 404 });
  },
};
