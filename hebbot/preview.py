"""Preview or send a pack / root card.

Examples:
    python -m hebbot.preview --kind pack --theme body --level 1 --lang fr
    python -m hebbot.preview --kind root --level 2 --lang en
    python -m hebbot.preview --kind pack --theme house --level 2 --lang fr --send

--send needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment.
"""
import argparse
import sys

from hebbot import content as content_lib
from hebbot import render
from hebbot.telegram import send_html


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kind", choices=["pack", "root"], required=True)
    parser.add_argument("--level", type=int, choices=content_lib.LEVELS, default=1)
    parser.add_argument("--lang", choices=content_lib.LANGS, default="fr")
    parser.add_argument("--theme", help="theme id for packs (e.g. body, house)")
    parser.add_argument("--root", help="root id for roots (e.g. ktv, shlh)")
    parser.add_argument("--send", action="store_true", help="send to Telegram instead of printing")
    args = parser.parse_args(argv)

    content = content_lib.load_content()
    if args.kind == "pack":
        packs = [p for p in content_lib.build_packs(content, args.level)
                 if args.theme in (None, p["theme"])]
        if not packs:
            sys.exit("No matching pack.")
        text = render.render_pack(packs[0], args.lang, show_draft=True)
    else:
        roots = [r for r in content_lib.roots_for_level(content, args.level)
                 if args.root in (None, r["id"])]
        if not roots:
            sys.exit("No matching root.")
        text = render.render_root(roots[0], args.lang, show_draft=True)

    if args.send:
        send_html(text)
        print("Sent.")
    else:
        print(text)


if __name__ == "__main__":
    main()
