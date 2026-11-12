// Conversation logic. Pure functions of (update, services): easy to test with fakes.

import { makeDb } from "./db.js";
import { makeTelegram } from "./telegram.js";
import { messagesFor, offeredLevels, todayInIsrael } from "./daily.js";
import {
  BILINGUAL_WELCOME,
  LANGS,
  TEXT,
  langKeyboard,
  levelKeyboard,
} from "./i18n.js";

// Command aliases (French and English) mapped to one canonical action.
const COMMANDS = {
  start: "start",
  help: "help",
  aide: "help",
  level: "level",
  niveau: "level",
  lang: "lang",
  language: "lang",
  langue: "lang",
  status: "status",
  reglages: "status",
  stop: "stop",
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const isReady = (user) => Boolean(user && user.lang && user.level);
const levelsOf = (deps) => (deps && deps.levels) || offeredLevels(); // levels with enough content to offer

function uiLang(user, from) {
  if (user && user.lang) return user.lang;
  return from && typeof from.language_code === "string" && from.language_code.startsWith("fr") ? "fr" : "en";
}

export function parseCommand(text) {
  if (typeof text !== "string" || !text.startsWith("/")) return null;
  const word = text.trim().split(/\s+/)[0].slice(1).split("@")[0].toLowerCase();
  return COMMANDS[word] || "unknown";
}

/**
 * Send today's lesson right away (the pack, then the root), unless this person already got today's.
 * The day is recorded only when everything was delivered, so a failed send can be retried.
 * Returns true when the lesson was delivered.
 */
export async function deliverToday(user, chatId, tg, db, deps = {}) {
  if (!user || !user.active || !isReady(user)) return false;
  const day = (deps.today ?? todayInIsrael)();
  if (user.last_sent === day) return false;
  const messages = messagesFor(user.lang, user.level, day);
  if (messages.length === 0) return false;

  const wait = deps.sleep ?? sleep; // Telegram allows about one message per second per chat
  await tg.sendMessage(chatId, TEXT[user.lang].firstSend);
  for (let i = 0; i < messages.length; i++) {
    await wait(1100);
    const result = await tg.sendMessage(chatId, messages[i], { parse_mode: "HTML" });
    if (!result || !result.ok) return false;
  }
  await db.setLastSent(chatId, day);
  return true;
}

export async function handleUpdate(update, env, deps = {}) {
  const tg = deps.tg ?? makeTelegram(env);
  const db = deps.db ?? makeDb(env.DB);
  const services = { tg, db, deps };
  if (update && update.callback_query) return handleCallback(update.callback_query, services);
  if (update && update.message) return handleMessage(update.message, services);
}

async function handleMessage(message, { tg, db, deps }) {
  const chat = message.chat;
  if (!chat || chat.type !== "private") {
    if (chat && parseCommand(message.text)) {
      await tg.sendMessage(chat.id, TEXT[uiLang(null, message.from)].privateOnly);
    }
    return;
  }
  const chatId = chat.id;
  const command = parseCommand(message.text);
  const user = await db.get(chatId);
  const lang = uiLang(user, message.from);
  const t = TEXT[lang];

  switch (command) {
    case "start": {
      const wasPaused = user && !user.active;
      await db.upsert(chatId);
      const fresh = await db.get(chatId);
      if (!fresh.lang) {
        await tg.sendMessage(chatId, BILINGUAL_WELCOME, { reply_markup: langKeyboard() });
      } else if (!fresh.level) {
        const levels = levelsOf(deps);
        await tg.sendMessage(chatId, TEXT[fresh.lang].chooseLevel(levels), { reply_markup: levelKeyboard(fresh.lang, levels) });
      } else {
        const tt = TEXT[fresh.lang];
        await tg.sendMessage(chatId, `${wasPaused ? tt.resumed + "\n\n" : ""}${tt.status(fresh)}`);
        // Someone coming back after a pause gets today's lesson without waiting for tomorrow.
        if (wasPaused) await deliverToday(fresh, chatId, tg, db, deps);
      }
      return;
    }
    case "lang":
      await tg.sendMessage(chatId, t.chooseLang, { reply_markup: langKeyboard() });
      return;
    case "level": {
      const levels = levelsOf(deps);
      await tg.sendMessage(chatId, t.chooseLevel(levels), { reply_markup: levelKeyboard(lang, levels) });
      return;
    }
    case "status":
      if (!isReady(user)) await tg.sendMessage(chatId, t.notReady);
      else await tg.sendMessage(chatId, t.status(user));
      return;
    case "stop":
      if (user) await db.setActive(chatId, false);
      await tg.sendMessage(chatId, t.stopped);
      return;
    case "help":
      await tg.sendMessage(chatId, t.help);
      return;
    default:
      await tg.sendMessage(chatId, t.unknown);
  }
}

async function handleCallback(query, { tg, db, deps }) {
  const chatId = query.message && query.message.chat && query.message.chat.id;
  const messageId = query.message && query.message.message_id;
  const data = typeof query.data === "string" ? query.data : "";
  if (!chatId || query.message.chat.type !== "private") {
    await tg.answerCallbackQuery(query.id);
    return;
  }

  const [kind, value] = data.split(":");
  let user = await db.get(chatId);
  if (!user) {
    await db.upsert(chatId);
    user = await db.get(chatId);
  }
  const wasReady = isReady(user);
  const levels = levelsOf(deps);
  const edit = (text, markup) =>
    messageId
      ? tg.editMessageText(chatId, messageId, text, markup ? { reply_markup: markup } : {})
      : tg.sendMessage(chatId, text, markup ? { reply_markup: markup } : {});

  if (kind === "lang" && LANGS.includes(value)) {
    await db.setLang(chatId, value);
    user = await db.get(chatId);
    await tg.answerCallbackQuery(query.id);
    if (!user.level) {
      await edit(TEXT[value].chooseLevel(levels), levelKeyboard(value, levels));
    } else {
      await edit(TEXT[value].ready(value, user.level));
      if (!wasReady) await deliverToday(user, chatId, tg, db, deps); // finished onboarding
    }
    return;
  }
  if (kind === "lvl" && levels.includes(Number(value))) {
    const level = Number(value);
    await db.setLevel(chatId, level);
    user = await db.get(chatId);
    await tg.answerCallbackQuery(query.id);
    const lang = user.lang || uiLang(null, query.from);
    if (!user.lang) {
      // Level chosen before a language (stale button): ask for the language next.
      await edit(BILINGUAL_WELCOME, langKeyboard());
    } else {
      await edit(TEXT[lang].ready(lang, level));
      if (!wasReady) await deliverToday(user, chatId, tg, db, deps); // finished onboarding
    }
    return;
  }
  await tg.answerCallbackQuery(query.id);
}
