"""Loading, indexing and validating the curated content library.

Layout (see content/README.md):
    content/words/<theme>.json   themed vocabulary, each word tagged with a level
    content/roots.json           root families (shorashim) with example sentences
"""
import json
import re
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

LANGS = ("fr", "en")
LEVELS = (1, 2)
POS = ("nm", "nf", "nmp", "nfp", "v", "adj", "adv")
STATUSES = ("draft", "reviewed")
MAX_PACK_SIZE = 15
TELEGRAM_MAX_LEN = 4096

_NIKUD = re.compile(r"[֑-ׇ]")
_HEBREW_OK = re.compile(r"^[א-ת֑-ׇ \-'\"׳״]+$")
_HEBREW_LETTER = re.compile(r"[א-ת]")


def strip_nikud(text):
    """Return the Hebrew text without vowel points / cantillation marks."""
    return _NIKUD.sub("", text)


def load_content(content_dir=CONTENT_DIR):
    content_dir = Path(content_dir)
    themes = {}
    for path in sorted((content_dir / "words").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_file"] = path.name
        themes[data["theme"]] = data
    roots_data = json.loads((content_dir / "roots.json").read_text(encoding="utf-8"))
    return {"themes": themes, "roots": roots_data["roots"]}


def build_packs(content, level):
    """Themed packs for a level: one per theme, split in chunks of MAX_PACK_SIZE."""
    packs = []
    for theme_id, theme in content["themes"].items():
        words = [w for w in theme["words"] if w["level"] == level]
        chunks = [words[i:i + MAX_PACK_SIZE] for i in range(0, len(words), MAX_PACK_SIZE)]
        for n, chunk in enumerate(chunks, 1):
            packs.append({
                "theme": theme_id,
                "emoji": theme.get("emoji", "📚"),
                "title": theme["title"],
                "level": level,
                "part": n,
                "parts": len(chunks),
                "words": chunk,
            })
    return packs


def roots_for_level(content, level):
    return [r for r in content["roots"] if r["level"] == level]


def find_root(content, root_id):
    for root in content["roots"]:
        if root["id"] == root_id:
            return root
    return None


def family_of(content, root_id):
    """All words of a root family (the data behind a future 'Family' button)."""
    root = find_root(content, root_id)
    return root["words"] if root else []


def _check_i18n(errors, where, obj, key):
    value = obj.get(key)
    if not isinstance(value, dict):
        errors.append(f"{where}: '{key}' must be an object with {LANGS}")
        return
    for lang in LANGS:
        if not isinstance(value.get(lang), str) or not value[lang].strip():
            errors.append(f"{where}: '{key}.{lang}' missing or empty")


def _check_hebrew(errors, where, text, require_nikud=True):
    if not isinstance(text, str) or not text.strip():
        errors.append(f"{where}: Hebrew text missing")
        return
    if not _HEBREW_LETTER.search(text):
        errors.append(f"{where}: no Hebrew letters in {text!r}")
    if require_nikud and not _NIKUD.search(text):
        errors.append(f"{where}: no nikud in {text!r}")


def _check_word(errors, where, word, seen_ids, root_ids):
    wid = word.get("id")
    if not wid:
        errors.append(f"{where}: missing id")
    elif wid in seen_ids:
        errors.append(f"{where}: duplicate id {wid!r}")
    else:
        seen_ids.add(wid)
    where = f"{where} [{wid}]"
    _check_hebrew(errors, where, word.get("he"))
    if isinstance(word.get("he"), str) and not _HEBREW_OK.match(word["he"]):
        errors.append(f"{where}: unexpected characters in {word['he']!r}")
    if word.get("pos") not in POS:
        errors.append(f"{where}: pos must be one of {POS}")
    _check_i18n(errors, where, word, "translit")
    _check_i18n(errors, where, word, "meaning")
    if word.get("root") and word["root"] not in root_ids:
        errors.append(f"{where}: unknown root {word['root']!r}")
    example = word.get("example")
    if example is not None:
        _check_hebrew(errors, f"{where} example", example.get("he"))
        _check_i18n(errors, f"{where} example", example, "translit")
        _check_i18n(errors, f"{where} example", example, "translation")


def validate(content):
    """Return a list of human-readable problems (empty list = valid)."""
    # Imported here to avoid a circular import (render uses this module).
    from hebbot import render

    errors = []
    seen_ids = set()
    root_ids = {r["id"] for r in content["roots"]}

    for theme_id, theme in content["themes"].items():
        where = f"theme {theme_id}"
        if theme.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        _check_i18n(errors, where, theme, "title")
        for word in theme["words"]:
            _check_word(errors, where, word, seen_ids, root_ids)
            if word.get("level") not in LEVELS:
                errors.append(f"{where} [{word.get('id')}]: level must be one of {LEVELS}")

    if len(root_ids) != len(content["roots"]):
        errors.append("roots: duplicate root ids")
    for root in content["roots"]:
        where = f"root {root.get('id')}"
        if root.get("level") not in LEVELS:
            errors.append(f"{where}: level must be one of {LEVELS}")
        if root.get("status") not in STATUSES:
            errors.append(f"{where}: status must be one of {STATUSES}")
        letters = root.get("letters", "")
        if not (2 <= len(letters) <= 4) or not all(_HEBREW_LETTER.match(c) for c in letters):
            errors.append(f"{where}: 'letters' must be 2-4 plain Hebrew letters")
        _check_i18n(errors, where, root, "meaning")
        if not root.get("words"):
            errors.append(f"{where}: no words")
        for word in root.get("words", []):
            _check_word(errors, where, word, seen_ids, root_ids)
            if "example" not in word:
                errors.append(f"{where} [{word.get('id')}]: root words need an example")

    if errors:
        # Rendering malformed entries would crash; report the structural problems first.
        return errors

    # Everything we would send must fit in one Telegram message, in both languages.
    for level in LEVELS:
        for lang in LANGS:
            for pack in build_packs(content, level):
                if len(render.render_pack(pack, lang)) > TELEGRAM_MAX_LEN:
                    errors.append(f"pack {pack['theme']} L{level} {lang}: exceeds {TELEGRAM_MAX_LEN} chars")
            for root in roots_for_level(content, level):
                if len(render.render_root(root, lang)) > TELEGRAM_MAX_LEN:
                    errors.append(f"root {root['id']} {lang}: exceeds {TELEGRAM_MAX_LEN} chars")
    return errors
