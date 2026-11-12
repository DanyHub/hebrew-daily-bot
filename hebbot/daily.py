"""Daily push: one themed pack and one root of the day.

No database and no AI at send time. The pick is a pure function of the date, so
the same date always gives the same messages and consecutive days rotate through
the library.

Examples:
    python -m hebbot.daily --level 1 --lang fr                  # print today's messages
    python -m hebbot.daily --level 2 --lang en --date 2026-11-15
    python -m hebbot.daily --level 1 --lang fr --send --allow-draft

Defaults come from HEBBOT_LEVEL / HEBBOT_LANG (then 1 / fr).
"""
import argparse
import os
import sys
import time
from datetime import date

from hebbot import content as content_lib
from hebbot import render


def day_number(day):
    """Days since 0001-01-01: a stable counter that advances by 1 each calendar day."""
    return day.toordinal()


def _usable(sets, allow_draft):
    return [s for s in sets if allow_draft or s.get("status") == "reviewed"]


def pick_pack(content, level, day, allow_draft=False):
    """The themed pack of the day, or None when the library has nothing usable."""
    packs = build_usable_packs(content, level, allow_draft)
    return packs[day_number(day) % len(packs)] if packs else None


def build_usable_packs(content, level, allow_draft=False):
    packs = content_lib.build_packs(content, level)
    allowed = {t for t, d in content["themes"].items() if allow_draft or d.get("status") == "reviewed"}
    return [p for p in packs if p["theme"] in allowed]


def pick_root(content, level, day, allow_draft=False):
    """The root of the day, or None when the library has nothing usable."""
    roots = _usable(content_lib.roots_for_level(content, level), allow_draft)
    return roots[day_number(day) % len(roots)] if roots else None


def build_daily(content, level, lang, day, allow_draft=False):
    """The messages to send for a given day: [theme pack, root card] (missing ones are skipped)."""
    messages = []
    pack = pick_pack(content, level, day, allow_draft)
    if pack:
        messages.append(render.render_pack(pack, lang, show_draft=pack_is_draft(content, pack)))
    root = pick_root(content, level, day, allow_draft)
    if root:
        messages.append(render.render_root(root, lang, show_draft=root.get("status") == "draft"))
    return messages


def pack_is_draft(content, pack):
    return content["themes"][pack["theme"]].get("status") == "draft"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, choices=content_lib.LEVELS,
                        default=int(os.environ.get("HEBBOT_LEVEL") or 1))
    parser.add_argument("--lang", choices=content_lib.LANGS, default=os.environ.get("HEBBOT_LANG") or "fr")
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--allow-draft", action="store_true",
                        help="also use content not yet marked 'reviewed' (shows a warning line)")
    parser.add_argument("--send", action="store_true", help="send to Telegram instead of printing")
    args = parser.parse_args(argv)

    day = args.date or date.today()
    content = content_lib.load_content()
    messages = build_daily(content, args.level, args.lang, day, args.allow_draft)
    if not messages:
        sys.exit("Nothing to send: no reviewed content for this level (use --allow-draft to include drafts).")

    if not args.send:
        print(f"--- {day.isoformat()} · level {args.level} · {args.lang} ---")
        print("\n\n=========\n\n".join(messages))
        return

    from hebbot.telegram import send_html
    for i, text in enumerate(messages):
        send_html(text)
        print(f"Sent message {i + 1}/{len(messages)}.")
        if i < len(messages) - 1:
            time.sleep(1)


if __name__ == "__main__":
    main()
