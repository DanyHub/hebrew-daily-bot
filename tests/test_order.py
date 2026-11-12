import copy
import json
import unittest
from datetime import date, timedelta

from hebbot import content as content_lib
from hebbot import order as order_lib

START = date(2026, 11, 15)  # a Sunday


class SendIndexTests(unittest.TestCase):
    def test_sunday_to_friday_count_and_saturday_shares_fridays_index(self):
        idx = lambda d: order_lib.send_index(date.fromisoformat(d), START)
        self.assertEqual([idx(f"2026-11-{d}") for d in (15, 16, 17, 18, 19, 20)], [0, 1, 2, 3, 4, 5])
        self.assertEqual(idx("2026-11-21"), 5)   # Saturday = Friday's lesson
        self.assertEqual(idx("2026-11-22"), 6)   # next Sunday continues without a gap

    def test_known_values_the_worker_tests_rely_on(self):
        # worker/test/bot.test.js asserts the same numbers for its JavaScript sendIndex().
        expected = {
            "2026-11-15": 0, "2026-11-20": 5, "2026-11-21": 5, "2026-11-22": 6,
            "2026-11-13": -1, "2026-11-14": -1, "2026-11-09": -5, "2026-11-12": -2, "2027-03-26": 113,
        }
        for day, value in expected.items():
            self.assertEqual(order_lib.send_index(date.fromisoformat(day), START), value, day)

    def test_every_send_day_advances_by_exactly_one(self):
        previous = None
        for i in range(400):
            d = START - timedelta(days=100) + timedelta(days=i)
            if d.weekday() == 5:  # Saturday: no send, same index as Friday
                continue
            idx = order_lib.send_index(d, START)
            if previous is not None:
                self.assertEqual(idx, previous + 1, d)
            previous = idx


class OrderFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()
        cls.order = order_lib.load_order()

    def test_order_file_is_valid_and_complete(self):
        self.assertEqual(order_lib.check(self.content, self.order), [])
        self.assertEqual(order_lib.start_date(self.order).weekday(), 6)

    def test_sync_is_idempotent_and_never_reorders(self):
        again, added = order_lib.sync(self.content, self.order)
        self.assertEqual(added, [])
        self.assertEqual(again, self.order)

    def test_sync_appends_new_items_at_the_end(self):
        content = copy.deepcopy(self.content)
        root = copy.deepcopy(content["roots"][0])
        root["id"] = "zzz"
        content["roots"].append(root)
        new, added = order_lib.sync(content, self.order)
        self.assertEqual(added, ["root zzz"])
        self.assertEqual(new["roots"][:-1], self.order["roots"])
        self.assertEqual(new["roots"][-1], "zzz")

    def test_check_reports_missing_unknown_and_duplicate_entries(self):
        broken = copy.deepcopy(self.order)
        broken["roots"].pop()
        broken["roots"].append("ghost")
        broken["packs"]["1"].append(broken["packs"]["1"][0])
        errors = "\n".join(order_lib.check(self.content, broken))
        self.assertIn("missing", errors)
        self.assertIn("unknown root 'ghost'", errors)
        self.assertIn("duplicate pack keys", errors)

    def test_start_must_be_a_sunday(self):
        broken = copy.deepcopy(self.order)
        broken["start"] = "2026-11-16"
        self.assertTrue(any("Sunday" in e for e in order_lib.check(self.content, broken)))

    def test_append_only_check_accepts_growth_and_rejects_reordering_or_changes(self):
        grown = copy.deepcopy(self.order)
        grown["roots"].append("brand-new")
        self.assertEqual(order_lib.check_append_only(self.order, grown), [])

        reordered = copy.deepcopy(self.order)
        reordered["roots"][0], reordered["roots"][1] = reordered["roots"][1], reordered["roots"][0]
        self.assertTrue(order_lib.check_append_only(self.order, reordered))

        shortened = copy.deepcopy(self.order)
        shortened["packs"]["1"].pop(0)
        self.assertTrue(order_lib.check_append_only(self.order, shortened))

        moved_start = copy.deepcopy(self.order)
        moved_start["start"] = "2026-11-22"
        self.assertTrue(order_lib.check_append_only(self.order, moved_start))

    def test_runway_counts_down_and_stops_at_zero(self):
        info = order_lib.runway(self.content, self.order, START, True)
        n_roots, left_roots = info["roots"]
        self.assertEqual(left_roots, n_roots)               # day 0: everything is still unseen
        later = order_lib.runway(self.content, self.order, START + timedelta(days=7 * 3), True)
        self.assertEqual(later["roots"][1], n_roots - 18)   # three weeks = 18 send days
        way_later = order_lib.runway(self.content, self.order, START + timedelta(days=7 * 400), True)
        self.assertEqual(way_later["roots"][1], 0)


if __name__ == "__main__":
    unittest.main()
