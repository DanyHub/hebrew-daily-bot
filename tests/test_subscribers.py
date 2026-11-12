import unittest
from datetime import date

from hebbot import content as content_lib
from hebbot import daily
from hebbot.subscribers import CHUNK, D1Error, D1Subscribers

DAY = date(2026, 11, 15)
OK = {"ok": True, "error_code": None, "description": "", "retry_after": None}


def err(code, description="", retry_after=None):
    return {"ok": False, "error_code": code, "description": description, "retry_after": retry_after}


class Recorder:
    """A fake `send` that records (chat_id, text) and answers from a script (default: ok)."""

    def __init__(self, script=None):
        self.calls = []
        self.script = script or {}

    def __call__(self, chat_id, text):
        self.calls.append((chat_id, text))
        queue = self.script.get(chat_id)
        return queue.pop(0) if queue else OK

    def texts(self, chat_id):
        return [t for c, t in self.calls if c == chat_id]


def user(chat_id, lang="fr", level=1, last_sent=None):
    return {"chat_id": chat_id, "lang": lang, "level": level, "last_sent": last_sent}


class FanOutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()

    def run_fan_out(self, users, send):
        return daily.send_to_subscribers(self.content, DAY, users, send, allow_draft=True,
                                         sleep=lambda s: None, round_gap=0)

    def test_everyone_gets_their_own_level_and_language_in_order(self):
        send = Recorder()
        out = self.run_fan_out([user(1, "fr", 1), user(2, "en", 2)], send)
        self.assertEqual(sorted(out["sent"]), [1, 2])
        for chat_id, lang, level in [(1, "fr", 1), (2, "en", 2)]:
            texts = send.texts(chat_id)
            self.assertEqual(texts, daily.build_daily(self.content, level, lang, DAY, allow_draft=True))
            self.assertIn("🌳", texts[1])  # pack first, root second
        self.assertNotEqual(send.texts(1), send.texts(2))

    def test_same_choice_shares_the_same_messages(self):
        send = Recorder()
        self.run_fan_out([user(1, "en", 1), user(2, "en", 1)], send)
        self.assertEqual(send.texts(1), send.texts(2))

    def test_users_already_served_today_are_skipped(self):
        send = Recorder()
        out = self.run_fan_out([user(1, last_sent=DAY.isoformat()), user(2, last_sent="2026-11-14")], send)
        self.assertEqual(out["skipped"], [1])
        self.assertEqual(out["sent"], [2])
        self.assertEqual(send.texts(1), [])

    def test_blocked_users_are_reported_unreachable_and_not_marked_sent(self):
        send = Recorder({1: [err(403, "Forbidden: bot was blocked by the user")],
                         2: [err(400, "Bad Request: chat not found")]})
        out = self.run_fan_out([user(1), user(2), user(3)], send)
        self.assertEqual(out["unreachable"], [1, 2])
        self.assertEqual(out["sent"], [3])
        self.assertEqual(out["failed"], [])
        self.assertEqual(len(send.texts(1)), 1)  # no pointless second attempt at a blocked chat

    def test_other_errors_are_failures_not_deactivations(self):
        send = Recorder({1: [err(500, "Internal error")], 2: [err(400, "Bad Request: message is too long")]})
        out = self.run_fan_out([user(1), user(2), user(3)], send)
        self.assertEqual(out["failed"], [1, 2])
        self.assertEqual(out["unreachable"], [])
        self.assertEqual(out["sent"], [3])

    def test_rate_limit_waits_then_retries_once(self):
        slept = []
        send = Recorder({1: [err(429, "Too Many Requests", retry_after=7)]})
        out = daily.send_to_subscribers(self.content, DAY, [user(1)], send, allow_draft=True,
                                        sleep=slept.append, round_gap=0)
        self.assertEqual(out["sent"], [1])
        self.assertIn(7, slept)
        self.assertEqual(len(send.texts(1)), 3)  # message 1 twice, then message 2

    def test_rounds_never_put_two_messages_to_one_chat_in_one_second(self):
        slept = []
        send = Recorder()
        daily.send_to_subscribers(self.content, DAY, [user(1)], send, allow_draft=True,
                                  sleep=slept.append, round_gap=1.1)
        self.assertTrue(any(s >= 1.0 for s in slept))

    def test_drafts_are_not_sent_without_allow_draft(self):
        send = Recorder()
        out = daily.send_to_subscribers(self.content, DAY, [user(1)], send, allow_draft=False,
                                        sleep=lambda s: None, round_gap=0)
        self.assertEqual(out["sent"], [])
        self.assertEqual(send.calls, [])


class FakeD1:
    def __init__(self, users):
        self.users, self.marked, self.deactivated = users, [], []

    def active_users(self):
        return self.users

    def mark_sent(self, ids, day):
        self.marked.append((sorted(ids), day))

    def deactivate(self, ids):
        self.deactivated.append(sorted(ids))


class RunSubscribersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = content_lib.load_content()

    def test_dry_run_reads_but_sends_and_writes_nothing(self):
        d1, send = FakeD1([user(1), user(2, "en", 2)]), Recorder()
        code = daily.run_subscribers(self.content, DAY, True, send_enabled=False, d1=d1, send=send)
        self.assertEqual(code, 0)
        self.assertEqual((send.calls, d1.marked, d1.deactivated), ([], [], []))

    def test_send_marks_sent_and_pauses_blocked_users(self):
        d1 = FakeD1([user(1), user(2), user(3)])
        send = Recorder({2: [err(403, "blocked")]})
        original = daily.send_to_subscribers
        daily.send_to_subscribers = lambda *a, **k: original(*a, sleep=lambda s: None, round_gap=0, **k)
        try:
            code = daily.run_subscribers(self.content, DAY, True, send_enabled=True, d1=d1, send=send)
        finally:
            daily.send_to_subscribers = original
        self.assertEqual(code, 0)
        self.assertEqual(d1.marked, [([1, 3], DAY.isoformat())])
        self.assertEqual(d1.deactivated, [[2]])

    def test_exit_code_is_nonzero_when_a_send_failed(self):
        d1, send = FakeD1([user(1)]), Recorder({1: [err(500, "boom")]})
        original = daily.send_to_subscribers
        daily.send_to_subscribers = lambda *a, **k: original(*a, sleep=lambda s: None, round_gap=0, **k)
        try:
            code = daily.run_subscribers(self.content, DAY, True, send_enabled=True, d1=d1, send=send)
        finally:
            daily.send_to_subscribers = original
        self.assertEqual(code, 1)
        self.assertEqual(d1.marked, [])


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        if self.payload is None:
            raise ValueError("no json")
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.headers, self.requests, self.responses = {}, [], list(responses)

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self.responses.pop(0)


def ok(result):
    return FakeResponse({"success": True, "result": result})


class D1ClientTests(unittest.TestCase):
    def client(self, *responses):
        session = FakeSession(responses)
        return D1Subscribers("acct", "tok", "mydb", session=session), session

    def test_finds_the_database_by_name_once_and_queries_it(self):
        d1, session = self.client(
            ok([{"uuid": "other", "name": "mydb-staging"}, {"uuid": "abc-123", "name": "mydb"}]),
            ok([{"results": [{"chat_id": 5, "lang": "fr", "level": 1, "last_sent": None}]}]),
            ok([{"results": []}]),
        )
        users = d1.active_users()
        d1.query("SELECT 1")
        self.assertEqual(users[0]["chat_id"], 5)
        self.assertEqual(session.headers["Authorization"], "Bearer tok")
        self.assertEqual(sum(1 for m, u, k in session.requests if m == "GET"), 1)
        self.assertTrue(session.requests[1][1].endswith("/accounts/acct/d1/database/abc-123/query"))
        self.assertIn("active = 1", session.requests[1][2]["json"]["sql"])

    def test_missing_database_explains_what_to_do(self):
        d1, _ = self.client(ok([]))
        with self.assertRaisesRegex(D1Error, "deploy the Worker first"):
            d1.active_users()

    def test_api_errors_become_d1_errors(self):
        d1, _ = self.client(FakeResponse({"success": False, "errors": [{"message": "Authentication error"}]}, 403))
        with self.assertRaisesRegex(D1Error, "Authentication error"):
            d1.active_users()
        d1, _ = self.client(FakeResponse(None, 502))
        with self.assertRaisesRegex(D1Error, "non-JSON"):
            d1.active_users()

    def test_updates_are_parameterised_and_chunked(self):
        ids = list(range(1, CHUNK * 2 + 6))  # 3 chunks
        d1, session = self.client(ok([{"uuid": "u", "name": "mydb"}]), *[ok([{"results": []}])] * 3)
        d1.mark_sent(ids, "2026-11-15")
        queries = [k["json"] for m, u, k in session.requests if m == "POST"]
        self.assertEqual(len(queries), 3)
        for q in queries:
            self.assertLessEqual(len(q["params"]), 100)
            self.assertNotIn("2026-11-15", q["sql"])  # value is bound, never concatenated
            self.assertEqual(q["params"][0], "2026-11-15")
        self.assertEqual(sum(len(q["params"]) - 1 for q in queries), len(ids))

    def test_ids_are_forced_to_integers(self):
        d1, session = self.client(ok([{"uuid": "u", "name": "mydb"}]), ok([{"results": []}]))
        d1.deactivate(["12", 13])
        self.assertEqual(session.requests[-1][2]["json"]["params"], [12, 13])


if __name__ == "__main__":
    unittest.main()
