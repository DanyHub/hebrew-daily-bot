// All user-facing text, in French and English. Plain text (no parse_mode) on purpose.

export const LANGS = ["fr", "en"];
export const LEVELS = [1, 2];

export const LEVEL_NAMES = {
  fr: { 1: "Débutant", 2: "Intermédiaire" },
  en: { 1: "Beginner", 2: "Intermediate" },
};

export const LANG_NAMES = { fr: "Français", en: "English" };

export const TEXT = {
  fr: {
    chooseLevel:
      "Quel est ton niveau ?\n\n" +
      "1 · Débutant : les mots du quotidien (famille, nourriture, maison, corps…)\n" +
      "2 · Intermédiaire : un vocabulaire plus riche, des racines plus abstraites\n\n" +
      "Tu pourras changer quand tu veux.",
    ready: (lang, level) =>
      `✅ C'est réglé !\nLangue : ${LANG_NAMES[lang]} · Niveau : ${level} · ${LEVEL_NAMES[lang][level]}\n\n` +
      "Du dimanche au vendredi, chaque matin :\n" +
      "🏷️ un thème avec 4 phrases\n" +
      "🌳 une racine et sa famille de mots\n\n" +
      "Changer : /niveau · /langue\nPause : /stop · Réglages : /status",
    status: (u) =>
      `Langue : ${LANG_NAMES[u.lang]} · Niveau : ${u.level} · ${LEVEL_NAMES.fr[u.level]}\n` +
      (u.active ? "Envois : actifs ✅" : "Envois : en pause ⏸️ (/start pour reprendre)"),
    notReady: "Il manque encore un réglage. Tape /start pour le terminer.",
    stopped: "⏸️ C'est noté, tu ne recevras plus rien. Tape /start pour reprendre quand tu veux.",
    resumed: "▶️ Bon retour ! Les envois reprennent.",
    help:
      "Je t'envoie chaque matin (dim–ven) un thème de vocabulaire hébreu avec 4 phrases, et une racine.\n\n" +
      "/niveau : changer de niveau\n/langue : changer de langue\n/status : voir tes réglages\n/stop : pause · /start : reprendre",
    privateOnly: "Écris-moi en message privé pour régler ton niveau et ta langue. 🙂",
    unknown: "Je n'ai pas compris. Tape /help pour voir les commandes.",
    chooseLang: "Choisis ta langue :",
    firstSend: "📬 Voici ta leçon du jour :",
  },
  en: {
    chooseLevel:
      "What's your level?\n\n" +
      "1 · Beginner: everyday words (family, food, house, body…)\n" +
      "2 · Intermediate: richer vocabulary, more abstract roots\n\n" +
      "You can change it any time.",
    ready: (lang, level) =>
      `✅ All set!\nLanguage: ${LANG_NAMES[lang]} · Level: ${level} · ${LEVEL_NAMES[lang][level]}\n\n` +
      "Sunday to Friday, every morning:\n" +
      "🏷️ a theme with 4 sentences\n" +
      "🌳 a root and its word family\n\n" +
      "Change: /level · /language\nPause: /stop · Settings: /status",
    status: (u) =>
      `Language: ${LANG_NAMES[u.lang]} · Level: ${u.level} · ${LEVEL_NAMES.en[u.level]}\n` +
      (u.active ? "Messages: on ✅" : "Messages: paused ⏸️ (/start to resume)"),
    notReady: "One setting is still missing. Type /start to finish.",
    stopped: "⏸️ Got it, you won't receive anything. Type /start to resume any time.",
    resumed: "▶️ Welcome back! Messages are on again.",
    help:
      "Every morning (Sun–Fri) I send a Hebrew vocabulary theme with 4 sentences, and a root.\n\n" +
      "/level: change level\n/language: change language\n/status: see your settings\n/stop: pause · /start: resume",
    privateOnly: "Message me privately to set your level and language. 🙂",
    unknown: "I didn't understand. Type /help to see the commands.",
    chooseLang: "Choose your language:",
    firstSend: "📬 Here's today's lesson:",
  },
};

// Shown first, before the language is known.
export const BILINGUAL_WELCOME =
  "Shalom ! 🇮🇱\n\nChoisis ta langue · Choose your language";

export function langKeyboard() {
  return {
    inline_keyboard: [
      [
        { text: "🇫🇷 Français", callback_data: "lang:fr" },
        { text: "🇬🇧 English", callback_data: "lang:en" },
      ],
    ],
  };
}

export function levelKeyboard(lang) {
  return {
    inline_keyboard: [
      [{ text: `1 · ${LEVEL_NAMES[lang][1]}`, callback_data: "lvl:1" }],
      [{ text: `2 · ${LEVEL_NAMES[lang][2]}`, callback_data: "lvl:2" }],
    ],
  };
}

export const COMMANDS = {
  fr: [
    { command: "niveau", description: "Changer de niveau" },
    { command: "langue", description: "Changer de langue" },
    { command: "status", description: "Voir mes réglages" },
    { command: "stop", description: "Mettre en pause" },
    { command: "start", description: "Commencer / reprendre" },
  ],
  en: [
    { command: "level", description: "Change level" },
    { command: "language", description: "Change language" },
    { command: "status", description: "See my settings" },
    { command: "stop", description: "Pause" },
    { command: "start", description: "Start / resume" },
  ],
};
