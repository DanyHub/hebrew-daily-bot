import test from "node:test";
import assert from "node:assert/strict";

import { handleUpdate, parseCommand } from "../src/bot.js";
import worker, { safeEqual } from "../src/index.js";

// --- fakes -----------------------------------------------------------------

function fakeDb() {
  const rows = new Map();
  return {
    rows,
    async get(id) {
      return rows.get(id) ? { ...rows.get(id) } : null;
    },
    async upsert(id) {
      const row = rows.get(id) || { chat_id: id, lang: null, level: null, active: 1 };
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
  };
}

function fakeTg() {
  const calls = [];
  const rec = (name) => async (...args) => {
    calls.push({ name, args });
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

const msg = (text, extra = {}) => ({
  message: { chat: { id: 42, type: "private" }, from: { id: 42, language_code: "fr" }, text, ...extra },
});
const press = (data) => ({
  callback_query: { id: "cb1", data, from: { id: 42 }, message: { message_id: 7, chat: { id: 42, type: "private" } } },
});

async function run(update, db, tg) {
  await handleUpdate(update, {}, { db, tg });
}

// --- tests -----------------------------------------------------------------

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
});

test("onboarding: language then level then ready, editing the same message", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/start"), db, tg);

  await run(press("lang:en"), db, tg);
  assert.equal(db.rows.get(42).lang, "en");
  assert.equal(tg.last().name, "editMessageText");
  assert.match(tg.last().args[2], /What's your level/);

  await run(press("lvl:2"), db, tg);
  assert.equal(db.rows.get(42).level, 2);
  assert.match(tg.last().args[2], /All set/);
  assert.match(tg.last().args[2], /Level: 2 · Intermediate/);
});

test("changing the language later keeps the level and confirms", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: 1, active: 1 });
  await run(press("lang:en"), db, tg);
  assert.deepEqual([db.rows.get(42).lang, db.rows.get(42).level], ["en", 1]);
  assert.match(tg.last().args[2], /All set/);
});

test("/stop pauses, /start resumes and says so, keeping settings", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: 1, active: 1 });
  await run(msg("/stop"), db, tg);
  assert.equal(db.rows.get(42).active, 0);
  assert.match(tg.last().args[1], /plus rien/);

  await run(msg("/start"), db, tg);
  assert.equal(db.rows.get(42).active, 1);
  assert.match(tg.last().args[1], /Bon retour/);
  assert.match(tg.last().args[1], /Niveau : 1/);
});

test("/status shows settings, or asks to finish onboarding", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/status"), db, tg);
  assert.match(tg.last().args[1], /Il manque/);
  db.rows.set(42, { chat_id: 42, lang: "en", level: 2, active: 0 });
  await run(msg("/status"), db, tg);
  assert.match(tg.last().args[1], /Level: 2/);
  assert.match(tg.last().args[1], /paused/);
});

test("/level and /langue show keyboards in the user's language", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "en", level: 1, active: 1 });
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
  // Plain chatter in a group is ignored entirely.
  const before = tg.calls.length;
  await run({ message: { chat: { id: -100, type: "supergroup" }, from: { id: 1 }, text: "hello" } }, db, tg);
  assert.equal(tg.calls.length, before);
});

test("garbage callback data never throws or changes settings", async () => {
  const db = fakeDb(), tg = fakeTg();
  db.rows.set(42, { chat_id: 42, lang: "fr", level: 1, active: 1 });
  for (const data of ["lang:de", "lvl:9", "lvl:abc", "x", "", "lang:"]) {
    await run(press(data), db, tg);
  }
  assert.deepEqual(db.rows.get(42), { chat_id: 42, lang: "fr", level: 1, active: 1 });
});

test("unknown commands get a help hint", async () => {
  const db = fakeDb(), tg = fakeTg();
  await run(msg("/wat"), db, tg);
  assert.match(tg.last().args[1], /\/help/);
});

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

  // No secret configured at all: refuse everything rather than accept anonymous calls.
  assert.equal((await worker.fetch(post({}), { ...env, WEBHOOK_SECRET: "" }, ctx)).status, 403);

  assert.equal((await worker.fetch(new Request("https://w.example/"), env, ctx)).status, 200);
  assert.equal((await worker.fetch(new Request("https://w.example/nope"), env, ctx)).status, 404);
});
