# Hebrew Daily Bot

A Telegram bot that teaches Hebrew every morning (Sunday to Friday), in French or English, at two levels.
Each person picks their language and level in Telegram, then receives:

1. **A themed pack**: 10–15 words on a theme (body, house, family, food, emotions…) plus **4 sentences** that reuse them.
2. **A root of the day** with its word family (e.g. כ־ת־ב: write, letter, headline…).

The content is **curated and stored in this repository**. No AI runs when messages are sent.

```
Telegram ──▶ Worker (worker/) ──▶ D1 database: who chose which level and language
                                        ▲
GitHub Actions "Curated daily" ─────────┘ builds today's messages from content/ and sends each person theirs
```

## Parts

| Folder | What it is |
|---|---|
| [`content/`](content/README.md) | The curated library: themes, sentences, root families. 11 themes, 46 roots, levels 1–2, French and English. |
| `hebbot/` | Python: loads and validates the content, renders Telegram messages, picks the day's pack and root, sends to subscribers. |
| [`worker/`](worker/README.md) | Cloudflare Worker: `/start`, level and language buttons, `/stop`, `/status`. |
| `tests/` | Python tests. The Worker has its own in `worker/test/`. |
| `.github/workflows/` | `curated-daily` (the daily send), `deploy-worker` (deploys the Worker), `validate` (CI). |

## Setup

1. Create the bot with `@BotFather` and keep its token.
2. Add the repository secret `TELEGRAM_BOT_TOKEN`.
3. Deploy the Worker so people can register: follow [`worker/README.md`](worker/README.md)
   (a free Cloudflare account, two more secrets, one workflow run).
4. People send `/start` to the bot. Run **Actions → Curated daily → Run workflow** to send right away;
   otherwise it runs by itself Sunday to Friday at 05:30 UTC.

Without the Cloudflare secrets the daily workflow falls back to one chat: set `TELEGRAM_CHAT_ID`
(and optionally the repository variables `HEBBOT_LEVEL` and `HEBBOT_LANG`).

## Try it locally

```bash
pip install -r requirements.txt
python -m hebbot.validate                                   # check the content
python -m unittest discover -s tests -t .                   # tests
python -m hebbot.daily --level 1 --lang fr --allow-draft    # print today's messages
python -m hebbot.daily --level 2 --lang en --date 2026-11-15 --allow-draft
python -m hebbot.preview --kind root --level 2 --lang fr    # one root card
```

`--send` posts to Telegram (needs `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`).

## Content status

Everything is marked `draft` until a Hebrew speaker has reviewed it, and every message says so. See
[`content/README.md`](content/README.md) for the format, the review workflow and the sources
(the root sheets of Serge Frydman, Ort Villiers – hebreu.org, are credited on each of their roots).
