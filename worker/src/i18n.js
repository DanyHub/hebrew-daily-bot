// All user-facing text, in French and English. Plain text (no parse_mode) on purpose.

export const LANGS = ["fr", "en"];

export const LEVEL_NAMES = {
  fr: { 1: "Débutant", 2: "Intermédiaire", 3: "Avancé" },
  en: { 1: "Beginner", 2: "Intermediate", 3: "Advanced" },
};

// One line per level, shown when asking which level to pick.
export const LEVEL_BLURBS = {
  fr: {
    1: "les mots du quotidien (famille, nourriture, maison, corps…)",
    2: "un vocabulaire plus riche",
    3: "les expressions idiomatiques et l'argot israéliens",
  },
  en: {
    1: "everyday words (family, food, house, body…)",
    2: "richer vocabulary",
    3: "Israeli idioms and slang",
  },
};

const chooseLevel = (lang, intro, outro) => (levels) =>
  `${intro}\n\n` + levels.map((l) => `${l} · ${LEVEL_NAMES[lang][l]} : ${LEVEL_BLURBS[lang][l]}`).join("\n") + `\n\n${outro}`;

export const LANG_NAMES = { fr: "Français", en: "English" };

export const TEXT = {
  fr: {
    chooseLevel: chooseLevel("fr", "Quel est ton niveau ?", "Tu pourras changer quand tu veux."),
    ready: (lang, level) =>
      `✅ C'est réglé !\nLangue : ${LANG_NAMES[lang]} · Niveau : ${level} · ${LEVEL_NAMES[lang][level]}\n\n` +
      "Du dimanche au vendredi, chaque jour à 13h (heure d'Israël) :\n" +
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
      "Je t'envoie chaque jour à 13h, heure d'Israël (dim–ven), un thème de vocabulaire hébreu avec 4 phrases, et une racine.\n\n" +
      "/niveau : changer de niveau\n/langue : changer de langue\n/status : voir tes réglages\n/stop : pause · /start : reprendre",
    privateOnly: "Écris-moi en message privé pour régler ton niveau et ta langue. 🙂",
    unknown: "Je n'ai pas compris. Tape /help pour voir les commandes.",
    chooseLang: "Choisis ta langue :",
    firstSend: "📬 Voici ta leçon du jour :",
  },
  en: {
    chooseLevel: chooseLevel("en", "What's your level?", "You can change it any time."),
    ready: (lang, level) =>
      `✅ All set!\nLanguage: ${LANG_NAMES[lang]} · Level: ${level} · ${LEVEL_NAMES[lang][level]}\n\n` +
      "Sunday to Friday, every day at 1pm (Israel time):\n" +
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
      "Every day at 1pm Israel time (Sun–Fri) I send a Hebrew vocabulary theme with 4 sentences, and a root.\n\n" +
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

export function levelKeyboard(lang, levels) {
  return {
    inline_keyboard: levels.map((l) => [{ text: `${l} · ${LEVEL_NAMES[lang][l]}`, callback_data: `lvl:${l}` }]),
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
