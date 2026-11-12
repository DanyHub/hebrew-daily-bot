import copy
import unittest
from datetime import date, timedelta

from hebbot import content as content_lib
from hebbot import daily


class DailyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()

    def test_same_date_gives_same_messages(self):
        d = date(2026, 11, 15)
        a = daily.build_daily(self.content, 1, "fr", d, allow_draft=True)
        b = daily.build_daily(self.content, 1, "fr", d, allow_draft=True)
        self.assertEqual(a, b)

    def test_one_pack_and_one_root_per_day(self):
        for level in content_lib.LEVELS:
            msgs = daily.build_daily(self.content, level, "en", date(2026, 11, 15), allow_draft=True)
            self.assertEqual(len(msgs), 2)
            self.assertIn("🌳", msgs[1])

    def test_consecutive_days_rotate_through_every_pack_and_root(self):
        for level in content_lib.LEVELS:
            packs = daily.build_usable_packs(self.content, level, allow_draft=True)
            roots = content_lib.roots_for_level(self.content, level)
            start = date(2026, 11, 1)
            seen_packs = {daily.pick_pack(self.content, level, start + timedelta(days=i), True)["theme"]
                          for i in range(len(packs))}
            seen_roots = {daily.pick_root(self.content, level, start + timedelta(days=i), True)["id"]
                          for i in range(len(roots))}
            self.assertEqual(len(seen_packs), len(packs))
            self.assertEqual(len(seen_roots), len(roots))

    def test_no_repeat_on_consecutive_days(self):
        d = date(2026, 11, 15)
        today = daily.pick_pack(self.content, 1, d, True)["theme"]
        tomorrow = daily.pick_pack(self.content, 1, d + timedelta(days=1), True)["theme"]
        self.assertNotEqual(today, tomorrow)

    def test_drafts_are_excluded_unless_allowed(self):
        self.assertEqual(daily.build_daily(self.content, 1, "fr", date(2026, 11, 15)), [])
        content = copy.deepcopy(self.content)
        for theme in content["themes"].values():
            theme["status"] = "reviewed"
        for root in content["roots"]:
            root["status"] = "reviewed"
        msgs = daily.build_daily(content, 1, "fr", date(2026, 11, 15))
        self.assertEqual(len(msgs), 2)
        self.assertNotIn("relecture", "".join(msgs))

    def test_messages_have_no_review_warning_and_no_source_line(self):
        for lang, banner, source in [("fr", "relecture", "Source"), ("en", "pending review", "Source")]:
            for level in content_lib.LEVELS:
                for i in range(30):
                    for m in daily.build_daily(self.content, level, lang, date(2026, 11, 1) + timedelta(days=i), True):
                        self.assertNotIn(banner, m)
                        self.assertNotIn(source, m)
                        self.assertNotIn("hebreu.org", m)

    def test_every_message_fits_telegram_in_every_language_and_level(self):
        start = date(2026, 11, 1)
        for lang in content_lib.LANGS:
            for level in content_lib.LEVELS:
                for i in range(40):
                    for m in daily.build_daily(self.content, level, lang, start + timedelta(days=i), True):
                        self.assertLessEqual(len(m), content_lib.TELEGRAM_MAX_LEN)


if __name__ == "__main__":
    unittest.main()
