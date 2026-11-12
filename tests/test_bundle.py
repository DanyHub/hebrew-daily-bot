import json
import unittest
from datetime import date, datetime, timedelta, timezone

from hebbot import content as content_lib
from hebbot import daily, export_bundle
from hebbot import order as order_lib


def pick_like_the_worker(bundle, lang, level, day):
    """The Worker's rule (worker/src/daily.js): packs[index % len] for the level, then roots[index % len]."""
    index = order_lib.send_index(day, date.fromisoformat(bundle["start"]))
    packs = bundle[lang]["packs"][str(level)]
    roots = bundle[lang]["roots"]
    out = []
    if packs:
        out.append(packs[index % len(packs)])
    if roots:
        out.append(roots[index % len(roots)])
    return out


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()
        cls.bundle = json.loads(export_bundle.BUNDLE_PATH.read_text(encoding="utf-8"))

    def test_bundle_file_is_up_to_date(self):
        expected = export_bundle.dump(export_bundle.build_bundle(self.content))
        actual = export_bundle.BUNDLE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            actual, expected,
            "worker/src/daily-bundle.json is stale: run `python -m hebbot.export_bundle` and commit it",
        )

    def test_the_workers_pick_equals_the_scheduled_send_every_day_for_two_years(self):
        start = date(2026, 11, 1)
        order = order_lib.load_order()
        for lang in content_lib.LANGS:
            for level in self.bundle["levels"]:
                for i in range(-30, 730):  # includes the days before the schedule starts, and every Saturday
                    day = start + timedelta(days=i)
                    self.assertEqual(
                        pick_like_the_worker(self.bundle, lang, level, day),
                        daily.build_daily(self.content, level, lang, day, daily.SEND_DRAFTS, order),
                        f"{lang} L{level} {day}",
                    )

    def test_every_bundled_message_fits_telegram(self):
        for lang in content_lib.LANGS:
            messages = self.bundle[lang]["roots"] + [m for packs in self.bundle[lang]["packs"].values() for m in packs]
            self.assertTrue(messages)
            for m in messages:
                self.assertLessEqual(len(m), content_lib.TELEGRAM_MAX_LEN)

    def test_a_level_is_only_offered_once_it_has_enough_packs(self):
        order = order_lib.load_order()
        for level in content_lib.LEVELS:
            enough = len(order_lib.ordered_packs(self.content, level, daily.SEND_DRAFTS, order)) >= export_bundle.MIN_PACKS_TO_OFFER
            self.assertEqual(level in self.bundle["levels"], enough, level)

    def test_ordinals_the_worker_tests_rely_on(self):
        # worker/test/bot.test.js asserts the same numbers for its JavaScript ordinal().
        self.assertEqual(date(1970, 1, 1).toordinal(), 719163)
        self.assertEqual(date(2026, 11, 12).toordinal(), 739932)
        self.assertEqual(date(2027, 3, 26).toordinal(), 740066)


class IsraelTodayTests(unittest.TestCase):
    def test_uses_the_israeli_date_not_the_utc_date(self):
        late_utc = datetime(2026, 11, 12, 22, 30, tzinfo=timezone.utc)  # 00:30 next day in Israel (UTC+2)
        self.assertEqual(daily.israel_today(late_utc), date(2026, 11, 13))
        summer = datetime(2026, 7, 1, 21, 30, tzinfo=timezone.utc)      # UTC+3 in summer
        self.assertEqual(daily.israel_today(summer), date(2026, 7, 2))
        morning = datetime(2026, 11, 12, 5, 30, tzinfo=timezone.utc)     # the scheduled send time
        self.assertEqual(daily.israel_today(morning), date(2026, 11, 12))


if __name__ == "__main__":
    unittest.main()
