"""Pre-render the daily lessons for the Worker, so it can send a new subscriber today's lesson at once.

The Worker has no copy of the content logic. It reads this file and applies the same rule as hebbot.daily:
`packs[send_index(day) mod len]` for the person's level and `roots[send_index(day) mod len]` for everyone,
both in the locked order of content/order.json.

    python -m hebbot.export_bundle           # (re)write worker/src/daily-bundle.json
    python -m hebbot.export_bundle --check   # exit 1 if the file is out of date (used by the tests)
"""
import argparse
import json
import sys
from pathlib import Path

from hebbot import content as content_lib
from hebbot import daily, order as order_lib, render

BUNDLE_PATH = Path(__file__).resolve().parent.parent / "worker" / "src" / "daily-bundle.json"

# A level is only offered to new subscribers once it has enough packs to avoid immediate repeats.
MIN_PACKS_TO_OFFER = 10


def build_bundle(content, allow_draft=daily.SEND_DRAFTS, order=None):
    order = order if order is not None else order_lib.load_order()
    bundle = {"start": order["start"], "levels": [], "fr": {}, "en": {}}
    for level in content_lib.LEVELS:
        if len(order_lib.ordered_packs(content, level, allow_draft, order)) >= MIN_PACKS_TO_OFFER:
            bundle["levels"].append(level)
    for lang in content_lib.LANGS:
        bundle[lang] = {
            "roots": [render.render_root(r, lang, show_source=False)
                      for r in order_lib.ordered_roots(content, allow_draft, order)],
            "packs": {
                str(level): [render.render_pack(p, lang) for p in order_lib.pool_packs(content, level, allow_draft, order)[0]]
                for level in content_lib.LEVELS
            },
        }
    return bundle


def dump(bundle):
    return json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="only verify the file is up to date")
    args = parser.parse_args(argv)

    text = dump(build_bundle(content_lib.load_content()))
    if args.check:
        current = BUNDLE_PATH.read_text(encoding="utf-8") if BUNDLE_PATH.exists() else ""
        if current != text:
            sys.exit(f"{BUNDLE_PATH.name} is out of date: run `python -m hebbot.export_bundle` and commit it.")
        print(f"{BUNDLE_PATH.name} is up to date.")
        return
    BUNDLE_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {BUNDLE_PATH} ({len(text) // 1024} KiB).")


if __name__ == "__main__":
    main()
