import test from "node:test";
import assert from "node:assert/strict";

import { handleUpdate, parseCommand } from "../src/bot.js";
import { messagesFor, ordinal, todayInIsrael } from "../src/daily.js";
import worker, { safeEqual } from "../src/index.js";

const TODAY = "2026-11-12";

// --- fakes -----------------------------------------------------------------

function fakeDb() {
  const rows = new Map();
  return {
    rows,
    async get(id) {
      return rows.get(id) ? { ...rows.get(id) } : null;
    },
    async upsert(id) {
      const row = rows.get(id) || { chat_id: id, lang: null, level: null, active: 1, last_sent: null };
      rows.set(id, { ...row, active: 1 });
    },
    async setLang(id, lang) {
      rows.get(id).lang = lang;
    },
    async setLevel(id, level) {
      rows.get(id).level = level;
    },
    async setActive(id, active) {
      rows.get(id).active = active ? 1 : 0;
    },
    async setLastSent(id, day) {
      rows.get(id).last_sent = day;
    },
  };
}

/** failHtml: make sendMessage fail for lesson messages (the ones sent with parse_mode HTML). */
function fakeTg({ failHtml = false } = {}) {
  const calls = [];
  const rec = (name) => async (...args) => {
    calls.push({ name, args });
    const extra = name === "sendMessage" ? args[2] : undefined;
    if (failHtml && extra && extra.parse_mode === "HTML") return { ok: false, description: "can't parse entities" };
    return { ok: true };
  };
  return {
    calls,
    sendMessage: rec("sendMessage"),
    editMessageText: rec("editMessageText"),
    answerCallbackQuery: rec("answerCallbackQuery"),
    last: () => calls[calls.length - 1],
  };
}

const sent = (tg) => tg.calls.filter((c) => c.name === "sendMessage");
const edits = (tg) => tg.calls.filter((c) => c.name === "editMessageText");
const lessonMessages = (tg) => sent(tg).filter((c) => c.args[2] && c.args[2].parse_mode === "HTML").map((c) => c.args[1]);

const msg = (text, extra = {}) => ({
  message: { chat: { id: 42, type: "private" }, from: { id: 42, language_code: "fr" }, text, ...extra },
});
const press = (data) => ({
  callback_query: { id: "cb1", data, from: { id: 42 }, message: { message_id: 7, chat: { id: 42, type: "private" } } },
});

async function run(update, db, tg) {
  await handleUpdate(update, {}, { db, tg, today: () => TODAY, sleep: async () => {} });
}

// --- conversation ----------------------------------------------------------

test("parseCommand understands French and English aliases and bot suffixes", () => {
  assert.equal(parseCommand("/niveau"), "level");
  assert.equal(parseCommand("/level"), "level");
  assert.equal(parseCommand("/langue"), "lang");
  assert.equal(parseCommand("/START@my_bot extra"), "start");
  assert.equal(parseCommand("/wat"), "unknown");
  assert.equal(parseCommand("hello"), null);
  assert.equal(parseCommand(undefined), null);
});

test("/start creates the user and asks for the language in both languages", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/start"), db, tg);
  assert.equal(db.rows.get(42).active, 1);
  const [, text, extra] = tg.last().args;
  assert.match(text, /Choisis ta langue/);
  assert.match(text, /Choose your language/);
  assert.equal(extra.reply_markup.inline_keyboard[0].length, 2);
  assert.deepEqual(lessonMessages(tg), []); // nothing to send before the choices are made
});

test("onboarding: language, then level, then ready (editing the same message)", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/start"), db, tg);

  await run(press("lang:en"), db, tg);
  assert.equal(db.rows.get(42).lang, "en");
  assert.match(edits(tg).at(-1).args[2], /What's your level/);
  assert.deepEqual(lessonMessages(tg), []); // still not ready: no lesson yet

  await run(press("lvl:2"), db, tg);
  assert.equal(db.rows.get(42).level, 2);
  assert.match(edits(tg).at(-1).args[2], /All set/);
  assert.match(edits(tg).at(-1).args[2], /Level: 2 · Intermediate/);
});

// --- today's lesson, right away ---------------------------------------------

test("finishing onboarding sends today's lesson immediately, in their language and level", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/start"), db, tg);
  await run(press("lang:fr"), db, tg);
  await run(press("lvl:1"), db, tg);

  const expected = messagesFor("fr", 1, TODAY);
  assert.equal(expected.length, 2);
  assert.deepEqual(lessonMessages(tg), expected);
  assert.match(sent(tg).at(-3).args[1], /leçon du jour/); // short lead-in first
  assert.equal(sent(tg).at(-1).args[2].parse_mode, "HTML");
  assert.equal(db.rows.get(42).last_sent, TODAY);
});

test("the lesson depends on the day: tomorrow's registrant gets tomorrow's pack", async () => {
  const dbA = fakeDb(), tgA = fakeTg(), dbB = fakeDb(), tgB = fakeTg();
  const at = (day) => async (update, db, tg) =>
    handleUpdate(update, {}, { db, tg, today: () => day, sleep: async () => {} });
  for (const [day, db, tg] of [["2026-11-12", dbA, tgA], ["2026-11-13", dbB, tgB]]) {
    await at(day)(msg("/start"), db, tg);
    await at(day)(press("lang:en"), db, tg);
    await at(day)(press("lvl:1"), db, tg);
  }
  assert.deepEqual(lessonMessages(tgA), messagesFor("en", 1, "2026-11-12"));
  assert.deepEqual(lessonMessages(tgB), messagesFor("en", 1, "2026-11-13"));
  assert.notDeepEqual(lessonMessages(tgA), lessonMessages(tgB));
});

test("nobody gets the same day's lesson twice", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: null, active: 1, last_sent: TODAY });
  await run(press("lvl:1"), db, tg);
  assert.match(edits(tg).at(-1).args[2], /C'est réglé/);
  assert.deepEqual(lessonMessages(tg), []);
});

test("changing language or level after onboarding does not resend a lesson", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: 1, active: 1, last_sent: "2026-11-11" });
  await run(press("lang:en"), db, tg);
  await run(press("lvl:2"), db, tg);
  assert.deepEqual([db.rows.get(42).lang, db.rows.get(42).level], ["en", 2]);
  assert.deepEqual(lessonMessages(tg), []);
  assert.equal(db.rows.get(42).last_sent, "2026-11-11");
});

test("if the lesson cannot be delivered, the day is not recorded (it can be retried)", async () => {
  const db = fakeDb(), tg = fakeTg({ failHtml: true });
  db.rows.set(42, { chat_id: 42, lang: "en", level: null, active: 1, last_sent: null });
  await run(press("lvl:1"), db, tg);
  assert.equal(db.rows.get(42).last_sent, null);
});

test("a paused person pressing an old button does not get a lesson", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: null, active: 0, last_sent: null });
  await run(press("lvl:1"), db, tg);
  assert.deepEqual(lessonMessages(tg), []);
});

test("coming back with /start after a pause resumes and sends today's lesson, once", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: 1, active: 1, last_sent: "2026-11-11" });
  await run(msg("/stop"), db, tg);
  assert.equal(db.rows.get(42).active, 0);
  assert.match(tg.last().args[1], /plus rien/);

  await run(msg("/start"), db, tg);
  assert.equal(db.rows.get(42).active, 1);
  assert.deepEqual(lessonMessages(tg), messagesFor("fr", 1, TODAY));
  assert.match(sent(tg).find((c) => /Bon retour/.test(c.args[1])).args[1], /Niveau : 1/);
  assert.equal(db.rows.get(42).last_sent, TODAY);

  // Pausing and resuming again the same day does not resend.
  await run(msg("/stop"), db, tg);
  const before = lessonMessages(tg).length;
  await run(msg("/start"), db, tg);
  assert.equal(lessonMessages(tg).length, before);
});

test("/start for an active person only shows their settings", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "en", level: 2, active: 1, last_sent: "2026-11-11" });
  await run(msg("/start"), db, tg);
  assert.match(tg.last().args[1], /Level: 2/);
  assert.deepEqual(lessonMessages(tg), []);
});

// --- other commands ----------------------------------------------------------

test("/status shows settings, or asks to finish onboarding", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/status"), db, tg);
  assert.match(tg.last().args[1], /Il manque/);
  db.rows.set(42, { chat_id: 42, lang: "en", level: 2, active: 0, last_sent: null });
  await run(msg("/status"), db, tg);
  assert.match(tg.last().args[1], /Level: 2/);
  assert.match(tg.last().args[1], /paused/);
});

test("/level and /langue show keyboards in the user's language", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "en", level: 1, active: 1, last_sent: null });
  await run(msg("/level"), db, tg);
  assert.equal(tg.last().args[2].reply_markup.inline_keyboard.length, 2);
  assert.match(tg.last().args[2].reply_markup.inline_keyboard[0][0].text, /Beginner/);
  await run(msg("/langue"), db, tg);
  assert.match(tg.last().args[1], /Choose your language/);
});

test("group chats get a nudge to write privately and are never stored", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run({ message: { chat: { id: -100, type: "supergroup" }, from: { id: 1 }, text: "/start" } }, db, tg);
  assert.equal(db.rows.size, 0);
  assert.match(tg.last().args[1], /message me privately|Écris-moi en message privé/i);
  const before = tg.calls.length;
  await run({ message: { chat: { id: -100, type: "supergroup" }, from: { id: 1 }, text: "hello" } }, db, tg);
  assert.equal(tg.calls.length, before);
});

test("garbage callback data never throws or changes settings", async () => {
  const db = fakeDb(), tg = fakeTg();
  const row = { chat_id: 42, lang: "fr", level: 1, active: 1, last_sent: "2026-11-11" };
  db.rows.set(42, { ...row });
  for (const data of ["lang:de", "lvl:9", "lvl:abc", "x", "", "lang:"]) {
    await run(press(data), db, tg);
  }
  assert.deepEqual(db.rows.get(42), row);
  assert.deepEqual(lessonMessages(tg), []);
});

test("unknown commands get a help hint", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/wat"), db, tg);
  assert.match(tg.last().args[1], /\/help/);
});

// --- day picking ---------------------------------------------------------------

test("ordinal() matches Python's date.toordinal() (tests/test_bundle.py asserts the same numbers)", () => {
  assert.equal(ordinal("1970-01-01"), 719163);
  assert.equal(ordinal("2026-11-12"), 739932);
  assert.equal(ordinal("2027-03-26"), 740066);
  assert.equal(ordinal("2026-11-13") - ordinal("2026-11-12"), 1);
});

test("todayInIsrael uses the Israeli date, winter and summer", () => {
  assert.equal(todayInIsrael(new Date("2026-11-12T22:30:00Z")), "2026-11-13"); // UTC+2
  assert.equal(todayInIsrael(new Date("2026-07-01T21:30:00Z")), "2026-07-02"); // UTC+3
  assert.equal(todayInIsrael(new Date("2026-11-12T05:30:00Z")), "2026-11-12");
  assert.match(todayInIsrael(), /^\d{4}-\d{2}-\d{2}$/);
});

test("messagesFor rotates by day, wraps around, and is empty for unknown settings", () => {
  const data = { fr: { 1: { packs: ["p0", "p1", "p2"], roots: ["r0", "r1"] } } };
  const n = ordinal("2026-11-12");
  assert.deepEqual(messagesFor("fr", 1, "2026-11-12", data), [`p${n % 3}`, `r${n % 2}`]);
  assert.deepEqual(messagesFor("fr", 1, "2026-11-13", data), [`p${(n + 1) % 3}`, `r${(n + 1) % 2}`]);
  assert.deepEqual(messagesFor("de", 1, "2026-11-12", data), []);
  assert.deepEqual(messagesFor("fr", 9, "2026-11-12", data), []);
  assert.deepEqual(messagesFor("fr", 1, "2026-11-12", { fr: { 1: { packs: [], roots: ["r0"] } } }), ["r0"]);
});

test("the real bundle serves both messages for every language and level, every day of a year", () => {
  for (const lang of ["fr", "en"]) {
    for (const level of [1, 2]) {
      for (let i = 0; i < 365; i++) {
        const day = new Date(Date.UTC(2026, 10, 12 + i)).toISOString().slice(0, 10);
        const messages = messagesFor(lang, level, day);
        assert.equal(messages.length, 2, `${lang} L${level} ${day}`);
        assert.ok(messages.every((m) => m.length > 20 && m.length <= 4096));
      }
    }
  }
});

// --- webhook -----------------------------------------------------------------

test("safeEqual compares secrets strictly", () => {
  assert.equal(safeEqual("abc", "abc"), true);
  assert.equal(safeEqual("abc", "abd"), false);
  assert.equal(safeEqual("abc", "abcd"), false);
  assert.equal(safeEqual(undefined, "abc"), false);
});

test("webhook rejects a missing or wrong secret and answers Telegram immediately otherwise", async () => {
  const env = { WEBHOOK_SECRET: "s3cret", TELEGRAM_BOT_TOKEN: "x", DB: {} };
  const waited = [];
  const ctx = { waitUntil: (p) => waited.push(p) };
  const post = (headers, body = "{}") =>
    new Request("https://w.example/webhook", { method: "POST", headers, body });

  assert.equal((await worker.fetch(post({}), env, ctx)).status, 403);
  assert.equal((await worker.fetch(post({ "X-Telegram-Bot-Api-Secret-Token": "nope" }), env, ctx)).status, 403);
  assert.equal((await worker.fetch(post({ "X-Telegram-Bot-Api-Secret-Token": "s3cret" }, "not json"), env, ctx)).status, 400);
  assert.equal((await worker.fetch(post({ "X-Telegram-Bot-Api-Secret-Token": "s3cret" }), env, ctx)).status, 200);
  await Promise.all(waited);

  assert.equal((await worker.fetch(post({}), { ...env, WEBHOOK_SECRET: "" }, ctx)).status, 403);

  assert.equal((await worker.fetch(new Request("https://w.example/"), env, ctx)).status, 200);
  assert.equal((await worker.fetch(new Request("https://w.example/nope"), env, ctx)).status, 404);
});
