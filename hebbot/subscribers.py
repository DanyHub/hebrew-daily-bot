"""Subscribers stored by the Cloudflare Worker, read and updated through the D1 REST API.

Needs a Cloudflare API token that can edit D1, and the account id. The database is found by name,
so no database id has to be copied around.
"""
import os

import requests

API = "https://api.cloudflare.com/client/v4"
CHUNK = 90  # D1 allows at most 100 bound parameters per query


class D1Error(RuntimeError):
    pass


class D1Subscribers:
    def __init__(self, account_id, token, database_name="hebrew-daily-bot", session=None):
        self.account_id = account_id
        self.database_name = database_name
        self._session = session or requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {token}"})
        self._db_id = None

    @classmethod
    def from_env(cls):
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        token = os.environ.get("CLOUDFLARE_API_TOKEN")
        if not (account_id and token):
            raise D1Error("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required")
        return cls(account_id, token, os.environ.get("D1_DATABASE_NAME") or "hebrew-daily-bot")

    def _request(self, method, path, **kwargs):
        resp = self._session.request(method, f"{API}/accounts/{self.account_id}{path}", timeout=30, **kwargs)
        try:
            data = resp.json()
        except ValueError:
            raise D1Error(f"Cloudflare returned non-JSON (HTTP {resp.status_code})") from None
        if not data.get("success"):
            errors = "; ".join(e.get("message", "?") for e in data.get("errors", [])) or f"HTTP {resp.status_code}"
            raise D1Error(f"Cloudflare D1 error: {errors}")
        return data["result"]

    @property
    def database_id(self):
        if self._db_id is None:
            found = [d for d in self._request("GET", "/d1/database", params={"name": self.database_name})
                     if d.get("name") == self.database_name]
            if not found:
                raise D1Error(f"D1 database {self.database_name!r} not found: deploy the Worker first")
            self._db_id = found[0]["uuid"]
        return self._db_id

    def query(self, sql, params=None):
        result = self._request("POST", f"/d1/database/{self.database_id}/query",
                               json={"sql": sql, "params": params or []})
        return result[0].get("results", []) if result else []

    def active_users(self):
        """Users who finished onboarding and have not paused: [{chat_id, lang, level, last_sent}]."""
        return self.query(
            "SELECT chat_id, lang, level, last_sent FROM users "
            "WHERE active = 1 AND lang IS NOT NULL AND level IS NOT NULL"
        )

    def mark_sent(self, chat_ids, day_iso):
        for i in range(0, len(chat_ids), CHUNK):
            chunk = [int(c) for c in chat_ids[i:i + CHUNK]]
            marks = ",".join("?" * len(chunk))
            self.query(f"UPDATE users SET last_sent = ? WHERE chat_id IN ({marks})", [day_iso, *chunk])

    def deactivate(self, chat_ids):
        for i in range(0, len(chat_ids), CHUNK):
            chunk = [int(c) for c in chat_ids[i:i + CHUNK]]
            marks = ",".join("?" * len(chunk))
            self.query(f"UPDATE users SET active = 0, updated_at = datetime('now') WHERE chat_id IN ({marks})", chunk)
