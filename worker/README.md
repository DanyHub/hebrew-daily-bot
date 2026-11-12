# Telegram Worker: levels, languages and subscribers

A small Cloudflare Worker that talks to people on Telegram. It does **only** the conversation;
the daily content is still sent by GitHub Actions (`hebbot.daily --subscribers`).

```
Telegram ──webhook──▶ Worker (worker/) ──▶ D1 database (users)
                                              ▲
GitHub Actions "Curated daily" ───────────────┘ reads subscribers, sends each their
                                                level + language, marks them as served
```

What a person sees:

1. `/start` → "Choisis ta langue · Choose your language" (buttons)
2. Level buttons (1 Beginner, 2 Intermediate)
3. A confirmation, then **today's lesson right away** (a theme with 4 sentences, then a root), whatever the
   time they register. After that, every morning (Sun–Fri), the same.

The first lesson is also sent when someone comes back with `/start` after a pause. Nobody gets the same
day's lesson twice: the day (Israel date) is stored in `last_sent`, and the scheduled send skips people already served.

Commands: `/level` · `/language` (or `/niveau`, `/langue`) · `/status` · `/stop` (pause) · `/start` (resume) · `/help`.
It only works in private chats (groups get a nudge to write privately), and a person who blocks the
bot is paused automatically at the next send.

## Set it up (about 10 minutes, doable from a phone)

You need a free Cloudflare account.

1. **Account ID.** Cloudflare dashboard → *Workers & Pages* → the Account ID is shown on the right.
   The first time, Cloudflare asks you to pick a free `workers.dev` subdomain: do that once.
2. **API token.** *My Profile → API Tokens → Create Token → Custom token*, with two account permissions:
   *Workers Scripts: Edit* and *D1: Edit*. Copy the token (shown once).
3. **GitHub secrets.** Repository → *Settings → Secrets and variables → Actions → New repository secret*:
   - `CLOUDFLARE_API_TOKEN` (step 2)
   - `CLOUDFLARE_ACCOUNT_ID` (step 1)
   - `TELEGRAM_BOT_TOKEN` (already there)
4. **Merge to the default branch.** GitHub only lists and schedules workflows that exist on `main`.
5. **Run it.** *Actions → Deploy Worker → Run workflow.* It tests the Worker, creates the D1
   database the first time, applies migrations, deploys, stores the secrets and points Telegram at
   the Worker. A green run ends with the health check and the webhook status.
6. **Try it.** Open your bot in Telegram and send `/start`.
7. **First daily send.** *Actions → Curated daily → Run workflow* with *dry run* ticked: it prints how
   many subscribers there are per level and language. Untick it to really send.

Once the Cloudflare secrets exist, the daily workflow automatically sends to subscribers. Without them
it keeps sending to the single chat in `TELEGRAM_CHAT_ID`.

Re-running *Deploy Worker* is safe: it reuses the database and keeps everyone's settings.

## Data and privacy

One row per private chat: chat id, language, level, active flag, date of the last send. No names,
no usernames, no message text. To remove someone: Cloudflare dashboard → D1 →
`hebrew-daily-bot` → console → `DELETE FROM users WHERE chat_id = 123456789;`

## Local development

```bash
cd worker
npm install
npm test                      # unit tests (no network, fake database)

# full local run with a real (local) D1:
printf 'TELEGRAM_API=http://127.0.0.1:9099\nTELEGRAM_BOT_TOKEN=test\nWEBHOOK_SECRET=s3cret\n' > .dev.vars
npx wrangler d1 migrations apply hebrew-daily-bot --local
npx wrangler dev --local --port 8799
curl -X POST localhost:8799/webhook -H 'X-Telegram-Bot-Api-Secret-Token: s3cret' \
  -d '{"message":{"chat":{"id":1,"type":"private"},"from":{"id":1},"text":"/start"}}'
```

`TELEGRAM_API` lets you point the Worker at a fake Telegram server; in production it is unset.

## When the content changes

The Worker sends the first lesson from `src/daily-bundle.json`, a pre-rendered copy of the rotation.
After editing anything in `content/`, run `python -m hebbot.export_bundle` and commit the result;
the Python tests fail if it is stale, and committing it redeploys the Worker.

## Files

| File | Role |
|---|---|
| `src/index.js` | Webhook entry point; rejects any request without Telegram's secret header |
| `src/bot.js` | Commands and button handling |
| `src/i18n.js` | All French and English text |
| `src/db.js` | The only SQL (parameterised) |
| `src/daily.js` + `src/daily-bundle.json` | Picks today's lesson. The bundle is generated from `content/` by `python -m hebbot.export_bundle` |
| `migrations/0001_users.sql` | The users table |
| `test/bot.test.js` | Unit tests |

Python side: `hebbot/subscribers.py` (D1 over the Cloudflare REST API) and `hebbot/daily.py` (`--subscribers`).
