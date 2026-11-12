import copy
import unittest
from datetime import date, timedelta

from hebbot import content as content_lib
from hebbot import daily
from hebbot import order as order_lib


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
        order = order_lib.load_order()
        for level in content_lib.LEVELS:
            if not order_lib.ordered_packs(self.content, level, True, order):
                continue
            msgs = daily.build_daily(self.content, level, "en", date(2026, 11, 15), allow_draft=True)
            self.assertEqual(len(msgs), 2)
            self.assertIn("🌳", msgs[1])

    def test_a_full_cycle_shows_every_item_once_with_no_repeat(self):
        order = order_lib.load_order()
        start = order_lib.start_date(order)
        for level in content_lib.LEVELS:
            packs = order_lib.ordered_packs(self.content, level, True, order)
            roots = order_lib.ordered_roots(self.content, True, order)
            if not packs:
                continue
            seen_packs = [daily.pick_pack(self.content, level, start + timedelta(days=i + i // 6), True, order)["theme"]
                          for i in range(len(packs))]  # i + i // 6 skips the Saturdays
            self.assertEqual(sorted(seen_packs), sorted(p["theme"] for p in packs))
            seen_roots = [daily.pick_root(self.content, start + timedelta(days=i + i // 6), True, order)["id"]
                          for i in range(len(roots))]
            self.assertEqual(sorted(seen_roots), sorted(r["id"] for r in roots))

    def test_no_repeat_on_consecutive_send_days(self):
        order = order_lib.load_order()
        d = date(2026, 11, 16)  # a Monday
        for level in content_lib.LEVELS:
            if not order_lib.ordered_packs(self.content, level, True, order):
                continue
            a = daily.pick_pack(self.content, level, d, True, order)["theme"]
            b = daily.pick_pack(self.content, level, d + timedelta(days=1), True, order)["theme"]
            self.assertNotEqual(a, b)
        self.assertNotEqual(daily.pick_root(self.content, d, True, order)["id"],
                            daily.pick_root(self.content, d + timedelta(days=1), True, order)["id"])

    def test_saturday_gets_fridays_lesson_so_no_item_is_wasted(self):
        order = order_lib.load_order()
        friday, saturday, sunday = date(2026, 11, 20), date(2026, 11, 21), date(2026, 11, 22)
        self.assertEqual(daily.build_daily(self.content, 1, "fr", friday, True, order),
                         daily.build_daily(self.content, 1, "fr", saturday, True, order))
        self.assertNotEqual(daily.build_daily(self.content, 1, "fr", friday, True, order),
                            daily.build_daily(self.content, 1, "fr", sunday, True, order))

    def test_everyone_gets_the_same_root_whatever_their_level(self):
        order = order_lib.load_order()
        for i in range(30):
            d = date(2026, 11, 15) + timedelta(days=i)
            roots = {daily.build_daily(self.content, level, "en", d, True, order)[-1] for level in content_lib.LEVELS
                     if order_lib.ordered_packs(self.content, level, True, order)}
            self.assertEqual(len(roots), 1, d)

    def test_adding_content_never_changes_what_the_days_before_the_end_get(self):
        """The point of the locked order: new items go to the end, so nothing already scheduled moves."""
        order = order_lib.load_order()
        content2 = copy.deepcopy(self.content)
        new_root = copy.deepcopy(content2["roots"][0])
        new_root["id"] = "new-root"
        content2["roots"].append(new_root)
        theme = copy.deepcopy(content2["themes"]["body"])
        theme["theme"] = "newtheme"
        for w in theme["words"]:
            w["id"] = "new-" + w["id"]
            w["he"] = w["he"] + "ם"
        content2["themes"]["newtheme"] = theme
        order2, added = order_lib.sync(content2, order)
        self.assertTrue(any("new-root" in a for a in added) and any("newtheme" in a for a in added))
        self.assertEqual(order_lib.check_append_only(order, order2), [])
        start = order_lib.start_date(order)
        day = lambda i: start + timedelta(days=i + i // 6)   # i-th send day, skipping Saturdays
        n_roots = len(order_lib.ordered_roots(self.content, True, order))
        for i in range(n_roots):  # until the root list runs out, the root of every day is unchanged
            self.assertEqual(daily.pick_root(self.content, day(i), True, order)["id"],
                             daily.pick_root(content2, day(i), True, order2)["id"], day(i))
        for level in content_lib.LEVELS:
            n_packs = len(order_lib.ordered_packs(self.content, level, True, order))
            for i in range(n_packs):  # likewise for the packs of each level
                self.assertEqual(daily.pick_pack(self.content, level, day(i), True, order)["theme"],
                                 daily.pick_pack(content2, level, day(i), True, order2)["theme"], (level, day(i)))

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
