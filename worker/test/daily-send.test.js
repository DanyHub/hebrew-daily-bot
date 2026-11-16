import test from "node:test";
import assert from "node:assert/strict";

import { runDailySend, isSendTime, israelClock, isUnreachable, BATCH_SIZE } from "../src/daily-send.js";
import { messagesFor } from "../src/daily.js";
import worker from "../src/index.js";

// Wed 2026-11-18 in winter (Israel = UTC+2): 13:00 Israel is 11:00 UTC. Summer (UTC+3): 13:00 is 10:00 UTC.
const WINTER_1PM = new Date("2026-11-18T11:00:00Z");
const DAY = "2026-11-18";

function fakeDb(users) {
  const rows = new Map(users.map((u) => [u.chat_id, { active: 1, last_sent: null, ...u }]));
  return {
    rows,
    async dueUsers(day, limit) {
      return [...rows.values()]
        .filter((u) => u.active === 1 && u.lang && u.level && u.last_sent !== day)
        .slice(0, limit)
        .map((u) => ({ ...u }));
    },
    async setLastSent(id, day) { rows.get(id).last_sent = day; },
    async setActive(id, active) { rows.get(id).active = active ? 1 : 0; },
  };
}

function fakeTg(results = {}) {
  const calls = [];
  return {
    calls,
    async sendMessage(chat, text, extra) {
      calls.push({ chat, text, extra });
      return results[chat] || { ok: true };
    },
  };
}

const deps = (db, tg, now = WINTER_1PM) => ({ db, tg, now: () => now, sleep: async () => {} });

test("israelClock and isSendTime follow Israel winter and summer time", () => {
  assert.deepEqual(israelClock(new Date("2026-11-18T10:59:00Z")), { hour: 12, weekday: "Wed" });
  assert.equal(isSendTime(new Date("2026-11-18T10:59:00Z")), false); // 12:59 in winter
  assert.equal(isSendTime(new Date("2026-11-18T11:00:00Z")), true); // 13:00 in winter
  assert.equal(isSendTime(new Date("2026-07-15T09:59:00Z")), false); // 12:59 in summer
  assert.equal(isSendTime(new Date("2026-07-15T10:00:00Z")), true); // 13:00 in summer
  assert.equal(isSendTime(new Date("2026-11-21T11:00:00Z")), false); // Saturday
  assert.equal(isSendTime(new Date("2026-11-18T13:30:00Z")), true); // later runs still send (retries)
});

test("nothing is sent before 13:00 Israel time", async () => {
  const db = fakeDb([{ chat_id: 1, lang: "fr", level: 1 }]), tg = fakeTg();
  const stats = await runDailySend(deps(db, tg, new Date("2026-11-18T10:55:00Z")));
  assert.equal(stats.skipped, true);
  assert.equal(tg.calls.length, 0);
});

test("at 13:00 each due person gets their own level and language, once", async () => {
  const db = fakeDb([
    { chat_id: 1, lang: "fr", level: 1 },
    { chat_id: 2, lang: "en", level: 3 },
    { chat_id: 3, lang: "en", level: 2, last_sent: DAY }, // already got it
    { chat_id: 4, lang: null, level: null }, // onboarding not finished
    { chat_id: 5, lang: "fr", level: 1, active: 0 }, // paused
  ]);
  const tg = fakeTg();
  const stats = await runDailySend(deps(db, tg));
  assert.deepEqual([stats.sent, stats.paused, stats.failed], [2, 0, 0]);
  assert.deepEqual(tg.calls.filter((c) => c.chat === 1).map((c) => c.text), messagesFor("fr", 1, DAY));
  assert.deepEqual(tg.calls.filter((c) => c.chat === 2).map((c) => c.text), messagesFor("en", 3, DAY));
  assert.ok(tg.calls.every((c) => c.extra.parse_mode === "HTML" && ![3, 4, 5].includes(c.chat)));
  assert.equal(db.rows.get(1).last_sent, DAY);

  const again = await runDailySend(deps(db, tg)); // the next 5-minute run
  assert.equal(again.sent, 0);
  assert.equal(tg.calls.length, 4); // nothing was sent twice
});

test("someone who blocked the bot is paused, others are still served", async () => {
  const db = fakeDb([{ chat_id: 1, lang: "fr", level: 1 }, { chat_id: 2, lang: "fr", level: 1 }]);
  const tg = fakeTg({ 1: { ok: false, error_code: 403, description: "Forbidden: bot was blocked by the user" } });
  const stats = await runDailySend(deps(db, tg));
  assert.deepEqual([stats.sent, stats.paused], [1, 1]);
  assert.equal(db.rows.get(1).active, 0);
  assert.equal(db.rows.get(1).last_sent, null);
  assert.equal(db.rows.get(2).last_sent, DAY);
});

test("a temporary failure is not recorded, so the next run retries it", async () => {
  const db = fakeDb([{ chat_id: 1, lang: "en", level: 1 }]);
  const stats = await runDailySend(deps(db, fakeTg({ 1: { ok: false, error_code: 500, description: "boom" } })));
  assert.deepEqual([stats.sent, stats.failed], [0, 1]);
  assert.equal(db.rows.get(1).active, 1);
  assert.equal(db.rows.get(1).last_sent, null);
  const retry = await runDailySend(deps(db, fakeTg()));
  assert.equal(retry.sent, 1);
});

test("a run serves at most one batch; the next run takes the rest", async () => {
  const db = fakeDb(Array.from({ length: BATCH_SIZE + 3 }, (_, i) => ({ chat_id: i + 1, lang: "fr", level: 1 })));
  const first = await runDailySend(deps(db, fakeTg()));
  assert.equal(first.sent, BATCH_SIZE);
  const second = await runDailySend(deps(db, fakeTg()));
  assert.equal(second.sent, 3);
});

test("isUnreachable recognises blocked and deleted chats only", () => {
  assert.equal(isUnreachable({ error_code: 403 }), true);
  assert.equal(isUnreachable({ error_code: 400, description: "Bad Request: chat not found" }), true);
  assert.equal(isUnreachable({ error_code: 400, description: "can't parse entities" }), false);
  assert.equal(isUnreachable({ error_code: 429 }), false);
});

test("the worker exposes a scheduled handler", () => {
  assert.equal(typeof worker.scheduled, "function");
});
