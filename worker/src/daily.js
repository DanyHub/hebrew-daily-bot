// Today's lesson for a subscriber, from the bundle pre-rendered by `python -m hebbot.export_bundle`.
// The rule is the same as hebbot/daily.py: packs[n % len] then roots[n % len], n = day ordinal.

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

/** [pack message, root message] (HTML) for a language, level and day; [] if there is nothing for them. */
export function messagesFor(lang, level, isoDate, data = bundle) {
  const entry = data[lang] && data[lang][String(level)];
  if (!entry) return [];
  const n = ordinal(isoDate);
  const out = [];
  if (entry.packs.length) out.push(entry.packs[n % entry.packs.length]);
  if (entry.roots.length) out.push(entry.roots[n % entry.roots.length]);
  return out;
}
