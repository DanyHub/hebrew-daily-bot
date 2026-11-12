"""Render content as Telegram messages (parse_mode=HTML), in French or English.

HTML mode is used on purpose: every dynamic string goes through html.escape, so a
stray '_' or '*' in the content can never make Telegram reject the message
(which the old Markdown mode allowed).
"""
from html import escape

from hebbot.content import LANGS


def esc(text):
    """Escape for Telegram HTML; quotes need no escaping in text nodes."""
    return escape(str(text), quote=False)


LEVEL_NAMES = {
    "fr": {1: "Débutant", 2: "Intermédiaire"},
    "en": {1: "Beginner", 2: "Intermediate"},
}

UI = {
    "fr": {
        "level": "Niveau",
        "pack": "Pack de mots",
        "part": "partie",
        "root": "Racine",
        "root_meaning": "Sens de la racine :",
        "family": "Famille de mots",
        "draft": "⚠️ Contenu en cours de relecture",
        "source": "Source :",
        "sentences": "En phrases",
    },
    "en": {
        "level": "Level",
        "pack": "Word pack",
        "part": "part",
        "root": "Root",
        "root_meaning": "Root meaning:",
        "family": "Word family",
        "draft": "⚠️ Content pending review",
        "source": "Source:",
        "sentences": "In sentences",
    },
}

# Short label used in packs (gender) and a longer one used for root families.
POS_SHORT = {"nm": "m.", "nf": "f.", "nmp": "m. pl.", "nfp": "f. pl.", "v": "v.", "adj": "adj.", "adv": "adv."}
POS_LONG = {
    "fr": {"nm": "nom masc.", "nf": "nom fém.", "nmp": "nom masc. pl.", "nfp": "nom fém. pl.",
           "v": "verbe", "adj": "adjectif", "adv": "adverbe"},
    "en": {"nm": "masc. noun", "nf": "fem. noun", "nmp": "masc. plural noun", "nfp": "fem. plural noun",
           "v": "verb", "adj": "adjective", "adv": "adverb"},
}

SEPARATOR = "〰️〰️〰️〰️〰️"


def _check_lang(lang):
    if lang not in LANGS:
        raise ValueError(f"unsupported language {lang!r}; expected one of {LANGS}")


def level_label(level, lang):
    return f"{UI[lang]['level']} {level} · {LEVEL_NAMES[lang][level]}"


def format_root_letters(letters):
    """'כתב' -> 'כ־ת־ב' (letters joined with a maqaf, as roots are usually written)."""
    return "־".join(letters)


def render_pack(pack, lang, show_draft=False):
    """One themed pack, in the spirit of the '15 words' cards."""
    _check_lang(lang)
    title = pack["title"][lang]
    suffix = ""
    if pack.get("parts", 1) > 1:
        suffix = f" ({UI[lang]['part']} {pack['part']}/{pack['parts']})"
    lines = [
        f"{pack['emoji']} <b>{esc(title)}</b>{esc(suffix)}",
        f"<i>{esc(level_label(pack['level'], lang))}</i>",
        "",
    ]
    for i, w in enumerate(pack["words"], 1):
        lines.append(
            f"{i}. <b>{esc(w['he'])}</b> — {esc(w['meaning'][lang])} — "
            f"<i>{esc(w['translit'][lang])}</i> ({esc(POS_SHORT[w['pos']])})"
        )
    sentences = pack.get("sentences") or []
    if sentences:
        lines += ["", f"🗣️ <b>{esc(UI[lang]['sentences'])}</b>", ""]
        for x in sentences:
            lines += [
                f"🇮🇱 {esc(x['he'])}",
                f"🔤 <i>{esc(x['translit'][lang])}</i>",
                f"💬 {esc(x['translation'][lang])}",
                "",
            ]
        lines.pop()
    if show_draft:
        lines += ["", esc(UI[lang]["draft"])]
    return "\n".join(lines)


def render_root(root, lang, show_draft=False):
    """A root card: the root, its core meaning and its family of words with examples."""
    _check_lang(lang)
    ui = UI[lang]
    lines = [
        f"🌳 <b>{esc(ui['root'])} {esc(format_root_letters(root['letters']))}</b>",
        f"<i>{esc(level_label(root['level'], lang))}</i>",
        f"{esc(ui['root_meaning'])} <b>{esc(root['meaning'][lang])}</b>",
        "",
        f"<b>{esc(ui['family'])}</b>",
        "",
    ]
    for i, w in enumerate(root["words"], 1):
        lines.append(
            f"{i}. <b>{esc(w['he'])}</b> — {esc(w['meaning'][lang])} — "
            f"<i>{esc(w['translit'][lang])}</i> ({esc(POS_LONG[lang][w['pos']])})"
        )
        ex = w.get("example")
        if ex:
            lines += [
                f"🇮🇱 {esc(ex['he'])}",
                f"🔤 <i>{esc(ex['translit'][lang])}</i>",
                f"💬 {esc(ex['translation'][lang])}",
                "",
            ]
    if lines[-1] != "":
        lines.append("")
    if root.get("source"):
        lines.append(f"📚 {esc(ui['source'])} {esc(root['source'])}")
    if show_draft:
        lines.append(esc(ui["draft"]))
    return "\n".join(lines).rstrip()
