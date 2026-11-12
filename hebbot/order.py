"""The locked, append-only order in which packs and roots are sent.

Why: picking `n mod (number of items)` reshuffles everything whenever content is added, so people could
see something again days after they saw it. Here the order lives in content/order.json and is only ever
*appended to*. The item for a day is `list[send_index(day)]`: while the list is longer than the days
elapsed nothing repeats, and adding items at the end never changes what any day gets.

    python -m hebbot.order sync                    # append packs/roots that are not in the order yet
    python -m hebbot.order check [--base REF]      # validate; with --base, also check it only grew
    python -m hebbot.order runway                  # how many send days of fresh content remain

Roots are shared by everyone (one list). Packs have one list per level.
"""
import argparse
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from hebbot import content as content_lib

ORDER_PATH = content_lib.CONTENT_DIR / "order.json"
SEND_DAYS_PER_WEEK = 6  # Sunday to Friday


def pack_key(pack):
    return pack["theme"] if pack["parts"] == 1 else f"{pack['theme']}:{pack['part']}"


def load_order(path=ORDER_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_order(order):
    return json.dumps(order, ensure_ascii=False, indent=2) + "\n"


def start_date(order):
    start = date.fromisoformat(order["start"])
    if start.weekday() != 6:
        raise ValueError(f"order.json 'start' must be a Sunday, got {order['start']}")
    return start


def send_index(day, start):
    """0-based index of a day in the send calendar: Sunday..Friday count, Saturday shares Friday's index.

    Negative for days before `start` (Python's floor division and modulo make that work).
    """
    weekday = (day.weekday() + 1) % 7  # Sunday = 0 ... Saturday = 6
    sunday = day - timedelta(days=weekday)
    weeks = (sunday - start).days // 7
    return weeks * SEND_DAYS_PER_WEEK + min(weekday, 5)


def _usable(item, allow_draft):
    return allow_draft or item.get("status") == "reviewed"


def ordered_packs(content, level, allow_draft, order):
    """Usable packs of a level, in the locked order."""
    by_key = {pack_key(p): p for p in content_lib.build_packs(content, level)}
    themes = content["themes"]
    keys = order["packs"].get(str(level), [])
    return [by_key[k] for k in keys if k in by_key and _usable(themes[by_key[k]["theme"]], allow_draft)]


def ordered_roots(content, allow_draft, order):
    """Usable roots, in the locked order (shared by all levels)."""
    by_id = {r["id"]: r for r in content_lib.all_roots(content)}
    return [by_id[i] for i in order["roots"] if i in by_id and _usable(by_id[i], allow_draft)]


def pick(items, index):
    return items[index % len(items)] if items else None


def all_pack_keys(content):
    return {level: [pack_key(p) for p in content_lib.build_packs(content, level)] for level in content_lib.LEVELS}


def sync(content, order=None):
    """Return (order, added): the order with any new packs/roots appended at the end (never reordered)."""
    order = json.loads(json.dumps(order)) if order else {"start": None, "roots": [], "packs": {}}
    added = []
    known = set(order["roots"])
    for root in content_lib.all_roots(content):
        if root["id"] not in known:
            order["roots"].append(root["id"])
            added.append(f"root {root['id']}")
    for level, keys in all_pack_keys(content).items():
        lst = order["packs"].setdefault(str(level), [])
        known = set(lst)
        for key in keys:
            if key not in known:
                lst.append(key)
                added.append(f"pack {key} (level {level})")
    return order, added


def check(content, order):
    """Problems with the order itself (empty list = fine)."""
    errors = []
    try:
        start_date(order)
    except (KeyError, ValueError) as exc:
        errors.append(str(exc))
    root_ids = [r["id"] for r in content_lib.all_roots(content)]
    if len(set(order["roots"])) != len(order["roots"]):
        errors.append("order.json: duplicate root ids")
    for rid in order["roots"]:
        if rid not in root_ids:
            errors.append(f"order.json: unknown root {rid!r} (an item must not be deleted once scheduled)")
    for rid in root_ids:
        if rid not in order["roots"]:
            errors.append(f"order.json: root {rid!r} is missing: run `python -m hebbot.order sync`")
    keys_by_level = all_pack_keys(content)
    for level in content_lib.LEVELS:
        lst = order["packs"].get(str(level), [])
        if len(set(lst)) != len(lst):
            errors.append(f"order.json: duplicate pack keys at level {level}")
        for key in lst:
            if key not in keys_by_level[level]:
                errors.append(f"order.json: unknown pack {key!r} at level {level}")
        for key in keys_by_level[level]:
            if key not in lst:
                errors.append(f"order.json: pack {key!r} (level {level}) is missing: run `python -m hebbot.order sync`")
    return errors


def check_append_only(base_order, new_order):
    """The new order must start with every list of the base order (only appends allowed)."""
    errors = []
    if base_order.get("start") != new_order.get("start"):
        errors.append(f"order.json: 'start' changed from {base_order.get('start')} to {new_order.get('start')}")
    if new_order["roots"][: len(base_order["roots"])] != base_order["roots"]:
        errors.append("order.json: the root order changed (only appending is allowed)")
    for level, base_list in base_order["packs"].items():
        if new_order["packs"].get(level, [])[: len(base_list)] != base_list:
            errors.append(f"order.json: the level {level} pack order changed (only appending is allowed)")
    return errors


def runway(content, order, day, allow_draft):
    """Send days of unseen content left, per list. 0 means the list has started to repeat."""
    index = send_index(day, start_date(order))
    out = {"index": index, "roots": None, "packs": {}}

    def left(n):
        return 0 if n == 0 else max(0, n - max(index, 0)) if index < n else 0

    out["roots"] = (len(ordered_roots(content, allow_draft, order)), left(len(ordered_roots(content, allow_draft, order))))
    for level in content_lib.LEVELS:
        n = len(ordered_packs(content, level, allow_draft, order))
        out["packs"][level] = (n, left(n))
    return out


def _git_show(ref, path="content/order.json"):
    result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    return json.loads(result.stdout) if result.returncode == 0 else None


def main(argv=None):
    from hebbot import daily

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["sync", "check", "runway"])
    parser.add_argument("--base", help="git ref to compare with (check): the order may only have grown")
    args = parser.parse_args(argv)
    content = content_lib.load_content()

    if args.command == "sync":
        order = load_order() if ORDER_PATH.exists() else None
        new, added = sync(content, order)
        if not new.get("start"):
            sys.exit("order.json does not exist yet: create it with a 'start' Sunday first")
        ORDER_PATH.write_text(dump_order(new), encoding="utf-8")
        print("Appended:" if added else "Nothing to append.", *added, sep="\n  ")
        return

    order = load_order()
    if args.command == "check":
        errors = check(content, order)
        if args.base:
            base = _git_show(args.base)
            if base is None:
                print(f"No order.json in {args.base}: nothing to compare with.")
            else:
                errors += check_append_only(base, order)
        if errors:
            sys.exit("\n".join(errors))
        print("order.json is valid" + (f" and only grew since {args.base}." if args.base else "."))
        return

    info = runway(content, order, daily.israel_today(), daily.SEND_DRAFTS)
    n, left_ = info["roots"]
    lines = [f"roots (shared): {n} items, {left_} send days of unseen content left"]
    lines += [f"level {lv} packs: {n} items, {left_} send days left" for lv, (n, left_) in info["packs"].items()]
    print("\n".join(lines))
    for line, (_n, left_) in zip(lines, [info["roots"], *info["packs"].values()]):
        if left_ < 14:
            print(f"::warning::{line}: add content soon, items will start to repeat")


if __name__ == "__main__":
    main()
