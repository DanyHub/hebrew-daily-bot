"""Spell-check every Hebrew string in the library with Hspell (an open-source Hebrew dictionary).

    python -m hebbot.spell            # list suspicious words (exit 1 if there are any not in the allow-list)

It is a safety net, not a judge: it catches missing letters such as צואר (צוואר) or קרסל (קרסול), but it
accepts valid words in the wrong sense and some old spellings. A fluent reader is still needed.
Words that are fine but unknown to the dictionary (slang, loanwords, names) go in content/spell-allow.txt.

Needs the `hspell` command (Debian/Ubuntu: `apt-get install hspell`). Without it the check is skipped.
"""
import re
import shutil
import subprocess
import sys

from hebbot import content as content_lib

ALLOW_PATH = content_lib.CONTENT_DIR / "spell-allow.txt"
_TOKEN = re.compile(r"[א-ת]+")
CHUNK = 500


def available():
    return shutil.which("hspell") is not None


def hebrew_strings(content):
    """Every Hebrew string with a label saying where it is."""
    for theme_id, theme in content["themes"].items():
        for w in theme["words"]:
            yield f"{theme_id}:{w['id']}", w["he"]
        for i, sentence in enumerate(theme.get("sentences", []), 1):
            yield f"{theme_id}:sentence{i}", sentence["he"]
    for root in content["roots"]:
        for w in root["words"]:
            yield f"root {root['id']}:{w['id']}", w["he"]
            if w.get("example"):
                yield f"root {root['id']}:{w['id']}:example", w["example"]["he"]


def tokens(content):
    """{token: [where it appears]} for every Hebrew word in the library."""
    seen = {}
    for where, text in hebrew_strings(content):
        for tok in _TOKEN.findall(content_lib.strip_nikud(text)):
            if len(tok) > 1:
                seen.setdefault(tok, []).append(where)
    return seen


def load_allow(path=ALLOW_PATH):
    if not path.exists():
        return set()
    return {line.split("#")[0].strip() for line in path.read_text(encoding="utf-8").splitlines() if line.split("#")[0].strip()}


def misspelled(words):
    """Words Hspell does not know, with its suggestions: {word: [suggestions]}."""
    words = sorted(words)
    bad = {}
    for i in range(0, len(words), CHUNK):
        chunk = words[i:i + CHUNK]
        data = ("\n".join(chunk) + "\n").encode("iso-8859-8")
        out = subprocess.run(["hspell", "-a"], input=data, capture_output=True, check=True).stdout.decode("iso-8859-8")
        results = [line for line in out.splitlines() if line and not line.startswith("@")]
        for word, line in zip(chunk, results):
            if line.startswith("&"):    # "& word count offset: suggestion, suggestion"
                bad[word] = [s.strip() for s in line.split(":", 1)[1].split(",")] if ":" in line else []
            elif line.startswith("#"):  # unknown, no suggestion
                bad[word] = []
    return bad


def check(content, allow=None):
    """[(word, suggestions, where)] for suspicious words that are not in the allow-list."""
    allow = load_allow() if allow is None else allow
    found = tokens(content)
    bad = misspelled(w for w in found if w not in allow)
    return [(w, bad[w], found[w][0]) for w in sorted(bad)]


def main():
    if not available():
        print("hspell is not installed: skipping the spell-check.")
        return
    problems = check(content_lib.load_content())
    for word, suggestions, where in problems:
        print(f"{word}  ({where})  suggestions: {', '.join(suggestions) or '-'}")
    print(f"{len(problems)} suspicious word(s).")
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
