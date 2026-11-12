"""Daily push: one themed pack and one root of the day.

No database and no AI at send time. The pick is a pure function of the date, so
the same date always gives the same messages and consecutive days rotate through
the library.

Examples:
    python -m hebbot.daily --level 1 --lang fr                  # print today's messages
    python -m hebbot.daily --level 2 --lang en --date 2026-11-15
    python -m hebbot.daily --level 1 --lang fr --send --allow-draft

    python -m hebbot.daily --subscribers --send --allow-draft   # everyone registered through the Worker

Defaults come from HEBBOT_LEVEL / HEBBOT_LANG (then 1 / fr). With --subscribers, each person
gets the level and language they chose (needs CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN).
"""
import argparse
import os
import sys
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from hebbot import content as content_lib
from hebbot import order as order_lib
from hebbot import render

# One switch for "may unreviewed (draft) content be sent?". The scheduled send, the Worker's
# instant first lesson (worker/src/daily-bundle.json) and the tests all follow it.
# Flip it to False once the content has been reviewed, then re-run `python -m hebbot.export_bundle`.
SEND_DRAFTS = True

# "Today" is the date in Israel, so the scheduled send and the Worker agree on the day.
ISRAEL = ZoneInfo("Asia/Jerusalem")


def israel_today(now=None):
    now = now or datetime.now(ISRAEL)
    return now.astimezone(ISRAEL).date()


def _order(order):
    return order if order is not None else order_lib.load_order()


def pick_pack(content, level, day, allow_draft=False, order=None):
    """The pack of the day for a level (locked order, then other levels' fresh packs when the level runs out)."""
    order = _order(order)
    packs, _own = order_lib.pool_packs(content, level, allow_draft, order)
    return order_lib.pick(packs, order_lib.send_index(day, order_lib.start_date(order)))


def pick_root(content, day, allow_draft=False, order=None):
    """The root of the day. Roots are shared by everyone, whatever their level."""
    order = _order(order)
    roots = order_lib.ordered_roots(content, allow_draft, order)
    return order_lib.pick(roots, order_lib.send_index(day, order_lib.start_date(order)))


def build_daily(content, level, lang, day, allow_draft=False, order=None):
    """The messages to send for a given day: [theme pack, root card] (missing ones are skipped)."""
    order = _order(order)
    messages = []
    pack = pick_pack(content, level, day, allow_draft, order)
    if pack:
        messages.append(render.render_pack(pack, lang))
    root = pick_root(content, day, allow_draft, order)
    if root:
        messages.append(render.render_root(root, lang, show_source=False))
    return messages


# Telegram answers these when the person blocked the bot, deleted the chat or the account is gone.
UNREACHABLE = {403}


def _is_unreachable(result):
    if result["error_code"] in UNREACHABLE:
        return True
    return result["error_code"] == 400 and "chat not found" in result["description"].lower()


def send_to_subscribers(content, day, users, send, allow_draft=False, sleep=time.sleep, round_gap=1.1):
    """Send each subscriber the messages for their own level and language.

    send(chat_id, text) -> {"ok", "error_code", "description", "retry_after"} (never raises).
    Messages go out in rounds (all first messages, then all second messages) so one chat never
    gets two messages in the same second. Returns {"sent": [ids], "unreachable": [ids],
    "failed": [ids], "skipped": [ids]}; the caller records them.
    """
    day_iso = day.isoformat()
    cache = {}
    plan = {}
    skipped = []
    for u in users:
        if u.get("last_sent") == day_iso:
            skipped.append(u["chat_id"])  # already got today's messages (workflow re-run)
            continue
        key = (u["lang"], int(u["level"]))
        if key not in cache:
            cache[key] = build_daily(content, key[1], key[0], day, allow_draft)
        if cache[key]:
            plan[u["chat_id"]] = cache[key]

    sent_all, unreachable, failed = [], set(), set()
    rounds = max((len(m) for m in plan.values()), default=0)
    for i in range(rounds):
        started = time.monotonic()
        for chat_id, messages in plan.items():
            if i >= len(messages) or chat_id in unreachable or chat_id in failed:
                continue
            result = send(chat_id, messages[i])
            if not result["ok"] and result["error_code"] == 429:
                sleep(min(int(result["retry_after"] or 5), 30))
                result = send(chat_id, messages[i])
            if result["ok"]:
                if i == len(messages) - 1:
                    sent_all.append(chat_id)
            elif _is_unreachable(result):
                unreachable.add(chat_id)
            else:
                failed.add(chat_id)
                print(f"Failed for {chat_id}: {result['error_code']} {result['description']}")
            sleep(0.05)
        if i < rounds - 1:
            sleep(max(0.0, round_gap - (time.monotonic() - started)))
    return {"sent": sent_all, "unreachable": sorted(unreachable), "failed": sorted(failed), "skipped": skipped}


def run_subscribers(content, day, allow_draft, send_enabled, d1=None, send=None):
    from hebbot import subscribers
    from hebbot.telegram import post_message

    d1 = d1 or subscribers.D1Subscribers.from_env()
    users = d1.active_users()
    groups = {}
    for u in users:
        groups.setdefault((u["lang"], int(u["level"])), 0)
        groups[(u["lang"], int(u["level"]))] += 1
    print(f"{len(users)} active subscribers: " + (", ".join(f"{n} × {l}/level {v}" for (l, v), n in sorted(groups.items())) or "none"))
    if not send_enabled:
        print("Dry run: nothing sent.")
        return 0

    if send is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            sys.exit("TELEGRAM_BOT_TOKEN is required to send")
        send = lambda chat_id, text: post_message(text, chat_id, token)  # noqa: E731

    outcome = send_to_subscribers(content, day, users, send, allow_draft)
    if outcome["sent"]:
        d1.mark_sent(outcome["sent"], day.isoformat())
    if outcome["unreachable"]:
        d1.deactivate(outcome["unreachable"])
    print(f"Sent: {len(outcome['sent'])} · already sent today: {len(outcome['skipped'])} · "
          f"blocked/removed (now paused): {len(outcome['unreachable'])} · failed: {len(outcome['failed'])}")
    return 1 if outcome["failed"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, choices=content_lib.LEVELS,
                        default=int(os.environ.get("HEBBOT_LEVEL") or 1))
    parser.add_argument("--lang", choices=content_lib.LANGS, default=os.environ.get("HEBBOT_LANG") or "fr")
    parser.add_argument("--date", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today in Israel)")
    parser.add_argument("--allow-draft", action="store_true",
                        help="also use content not yet marked 'reviewed' (already the default while SEND_DRAFTS is True)")
    parser.add_argument("--send", action="store_true", help="send to Telegram instead of printing")
    parser.add_argument("--subscribers", action="store_true",
                        help="send to everyone registered through the Worker (their own level and language)")
    args = parser.parse_args(argv)

    day = args.date or israel_today()
    allow_draft = args.allow_draft or SEND_DRAFTS
    content = content_lib.load_content()
    if args.subscribers:
        sys.exit(run_subscribers(content, day, allow_draft, args.send))
    messages = build_daily(content, args.level, args.lang, day, allow_draft)
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
