// The scheduled daily send, run by a Cloudflare cron trigger (see wrangler.toml).
//
// Cloudflare starts cron triggers on time, unlike GitHub Actions schedules (which can be hours late).
// The cron fires every 5 minutes between 10:00 and 14:59 UTC; each run does nothing until it is 13:00 in
// Israel (10:00 UTC in summer, 11:00 UTC in winter), and never on Saturday. From then on every run sends to
// a small batch of people who have not had today's lesson yet, so a failed or interrupted send is retried
// 5 minutes later and nobody gets it twice (last_sent). The batch is small because a Worker invocation may
// only make a limited number of outgoing requests.

import { messagesFor, todayInIsrael } from "./daily.js";
import { sleep } from "./bot.js";

export const SEND_FROM_HOUR = 13; // Israel time
export const BATCH_SIZE = 8; // people per run: ~3 Telegram calls + 1 database write each, under the 50-request limit

/** Hour (0-23) and weekday short name ("Sat"...) in Israel. */
export function israelClock(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Jerusalem",
    hour: "2-digit",
    hourCycle: "h23",
    weekday: "short",
  }).formatToParts(now);
  const get = (type) => parts.find((p) => p.type === type).value;
  return { hour: Number(get("hour")), weekday: get("weekday") };
}

export function isSendTime(now = new Date()) {
  const { hour, weekday } = israelClock(now);
  return weekday !== "Sat" && hour >= SEND_FROM_HOUR;
}

/** Telegram says the person blocked the bot, deleted the chat or is gone: stop trying. */
export function isUnreachable(result) {
  if (!result) return false;
  if (result.error_code === 403) return true;
  return result.error_code === 400 && /chat not found/i.test(result.description || "");
}

/**
 * Send today's lesson to the next batch of people who have not had it.
 * Returns {sent, paused, failed} counts (for logs and tests).
 */
export async function runDailySend(deps) {
  const { db, tg } = deps;
  const now = deps.now ? deps.now() : new Date();
  const stats = { sent: 0, paused: 0, failed: 0, skipped: false };
  if (!isSendTime(now)) {
    stats.skipped = true;
    return stats;
  }
  const day = todayInIsrael(now);
  const wait = deps.sleep ?? sleep; // Telegram allows about one message per second per chat
  const users = await db.dueUsers(day, BATCH_SIZE);

  for (const user of users) {
    const messages = messagesFor(user.lang, user.level, day);
    if (messages.length === 0) continue;
    let delivered = true;
    for (let i = 0; i < messages.length; i++) {
      if (i > 0) await wait(1100);
      const result = await tg.sendMessage(user.chat_id, messages[i], { parse_mode: "HTML" });
      if (result && result.ok) continue;
      delivered = false;
      if (isUnreachable(result)) {
        await db.setActive(user.chat_id, false);
        stats.paused++;
      } else {
        stats.failed++;
      }
      break;
    }
    if (delivered) {
      await db.setLastSent(user.chat_id, day);
      stats.sent++;
    }
  }
  console.log(`daily send ${day}: sent ${stats.sent}, paused ${stats.paused}, failed ${stats.failed}`);
  return stats;
}
