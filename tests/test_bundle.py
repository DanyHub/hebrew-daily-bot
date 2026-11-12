import json
import unittest
from datetime import date, datetime, timedelta, timezone

from hebbot import content as content_lib
from hebbot import daily, export_bundle


def pick_like_the_worker(bundle, lang, level, day):
    """The Worker's rule (worker/src/daily.js): packs[n % len] then roots[n % len], n = day ordinal."""
    entry = bundle[lang][str(level)]
    n = day.toordinal()
    out = []
    if entry["packs"]:
        out.append(entry["packs"][n % len(entry["packs"])])
    if entry["roots"]:
        out.append(entry["roots"][n % len(entry["roots"])])
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
        for lang in content_lib.LANGS:
            for level in content_lib.LEVELS:
                for i in range(0, 730):
                    day = start + timedelta(days=i)
                    self.assertEqual(
                        pick_like_the_worker(self.bundle, lang, level, day),
                        daily.build_daily(self.content, level, lang, day, daily.SEND_DRAFTS),
                        f"{lang} L{level} {day}",
                    )

    def test_every_bundled_message_fits_telegram(self):
        for lang in self.bundle.values():
            for entry in lang.values():
                for m in entry["packs"] + entry["roots"]:
                    self.assertLessEqual(len(m), content_lib.TELEGRAM_MAX_LEN)

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
