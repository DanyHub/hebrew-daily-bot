"""Pre-render the daily rotation for the Worker, so it can send a new subscriber today's lesson at once.

The Worker has no copy of the content logic. It picks `packs[n % len(packs)]` and
`roots[n % len(roots)]` from this file, where n is the day's ordinal (same rule as hebbot.daily).

    python -m hebbot.export_bundle           # (re)write worker/src/daily-bundle.json
    python -m hebbot.export_bundle --check   # exit 1 if the file is out of date (used by the tests)
"""
import argparse
import json
import sys
from pathlib import Path

from hebbot import content as content_lib
from hebbot import daily, render

BUNDLE_PATH = Path(__file__).resolve().parent.parent / "worker" / "src" / "daily-bundle.json"


def build_bundle(content, allow_draft=daily.SEND_DRAFTS):
    bundle = {}
    for lang in content_lib.LANGS:
        bundle[lang] = {}
        for level in content_lib.LEVELS:
            packs = [render.render_pack(p, lang) for p in daily.build_usable_packs(content, level, allow_draft)]
            roots = [render.render_root(r, lang, show_source=False)
                     for r in daily.usable_roots(content, level, allow_draft)]
            bundle[lang][str(level)] = {"packs": packs, "roots": roots}
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
