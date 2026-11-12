// Conversation logic. Pure functions of (update, services): easy to test with fakes.

import { makeDb } from "./db.js";
import { makeTelegram } from "./telegram.js";
import {
  BILINGUAL_WELCOME,
  LANGS,
  LEVELS,
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

function uiLang(user, from) {
  if (user && user.lang) return user.lang;
  return from && typeof from.language_code === "string" && from.language_code.startsWith("fr") ? "fr" : "en";
}

export function parseCommand(text) {
  if (typeof text !== "string" || !text.startsWith("/")) return null;
  const word = text.trim().split(/\s+/)[0].slice(1).split("@")[0].toLowerCase();
  return COMMANDS[word] || "unknown";
}

export async function handleUpdate(update, env, deps = {}) {
  const tg = deps.tg ?? makeTelegram(env);
  const db = deps.db ?? makeDb(env.DB);
  if (update && update.callback_query) return handleCallback(update.callback_query, tg, db);
  if (update && update.message) return handleMessage(update.message, tg, db);
}

async function handleMessage(message, tg, db) {
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
        await tg.sendMessage(chatId, TEXT[fresh.lang].chooseLevel, { reply_markup: levelKeyboard(fresh.lang) });
      } else {
        const tt = TEXT[fresh.lang];
        await tg.sendMessage(chatId, `${wasPaused ? tt.resumed + "\n\n" : ""}${tt.status(fresh)}`);
      }
      return;
    }
    case "lang":
      await tg.sendMessage(chatId, t.chooseLang, { reply_markup: langKeyboard() });
      return;
    case "level":
      await tg.sendMessage(chatId, t.chooseLevel, { reply_markup: levelKeyboard(lang) });
      return;
    case "status":
      if (!user || !user.lang || !user.level) await tg.sendMessage(chatId, t.notReady);
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

async function handleCallback(query, tg, db) {
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
  const edit = (text, markup) =>
    messageId
      ? tg.editMessageText(chatId, messageId, text, markup ? { reply_markup: markup } : {})
      : tg.sendMessage(chatId, text, markup ? { reply_markup: markup } : {});

  if (kind === "lang" && LANGS.includes(value)) {
    await db.setLang(chatId, value);
    user = await db.get(chatId);
    await tg.answerCallbackQuery(query.id);
    if (!user.level) await edit(TEXT[value].chooseLevel, levelKeyboard(value));
    else await edit(TEXT[value].ready(value, user.level));
    return;
  }
  if (kind === "lvl" && LEVELS.includes(Number(value))) {
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
    }
    return;
  }
  await tg.answerCallbackQuery(query.id);
}
