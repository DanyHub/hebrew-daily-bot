// Today's lesson for a subscriber, from the bundle pre-rendered by `python -m hebbot.export_bundle`.
// The rule is the same as hebbot/daily.py: the item at the day's send index in the locked order
// (packs for the person's level, roots for everyone). Tests prove both sides agree.

import bundle from "./daily-bundle.json" with { type: "json" };

/** Days since 0001-01-01 for a "YYYY-MM-DD" date: identical to Python's date.toordinal(). */
export function ordinal(isoDate) {
  const [y, m, d] = isoDate.split("-").map(Number);
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000) + 719163; // 719163 = ordinal of 1970-01-01
}

/** Today's date in Israel as "YYYY-MM-DD", so the Worker and the scheduled send agree on the day. */
export function todayInIsrael(now = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jerusalem",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(now);
}

export const floorMod = (a, n) => ((a % n) + n) % n;

/**
 * Index of a day in the send calendar (same as hebbot.order.send_index): Sunday to Friday count,
 * Saturday shares Friday's index. `startIso` is a Sunday. Negative before the start.
 */
export function sendIndex(isoDate, startIso) {
  const day = ordinal(isoDate);
  const weekday = day % 7; // Python's ordinal 1 is a Monday, so ordinal % 7 gives Sunday = 0 ... Saturday = 6
  const sunday = day - weekday;
  const weeks = Math.floor((sunday - ordinal(startIso)) / 7);
  return weeks * 6 + Math.min(weekday, 5);
}

/** Levels that have enough content to be offered to new subscribers. */
export function offeredLevels(data = bundle) {
  return data.levels.slice();
}

/** [pack message, root message] (HTML) for a language, level and day; [] if there is nothing for them. */
export function messagesFor(lang, level, isoDate, data = bundle) {
  const entry = data[lang];
  if (!entry) return [];
  const packs = (entry.packs && entry.packs[String(level)]) || [];
  const roots = entry.roots || [];
  const index = sendIndex(isoDate, data.start);
  const out = [];
  if (packs.length) out.push(packs[floorMod(index, packs.length)]);
  if (roots.length) out.push(roots[floorMod(index, roots.length)]);
  return out;
}
