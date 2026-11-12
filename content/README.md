# Content library

Curated vocabulary served by the bot. Nothing here is generated at send time.

```
content/
  words/<theme>.json   one file per theme (body, house, ...), words tagged by level
  roots.json           root families (shorashim) with an example per word
```

## Word

```json
{
  "id": "body-rosh",
  "level": 1,
  "he": "רֹאשׁ",
  "pos": "nm",
  "translit": {"fr": "rosh", "en": "rosh"},
  "meaning":  {"fr": "Tête", "en": "Head"},
  "root": "ktv"
}
```

- `id`: unique and stable (progress and spaced repetition will key on it).
- `he`: plain Hebrew letters, no nikud (nikud is accepted but not required).
- `level`: 1 beginner, 2 intermediate, 3 advanced.
- `pos`: `nm`/`nf` (masc./fem. noun), `nmp`/`nfp` (plural), `v`, `adj`, `adv`, `expr` (an idiom or expression).
- `literal` (optional, mostly for idioms): the word-for-word meaning in `fr`/`en`, shown as a "litt." line.
- `translit` is per language on purpose: French uses `ou`, `h'`, `ch`; English uses `u`, `ch`, `sh`.
- `root` (optional): id of an entry in `roots.json`; powers the future "Family" button.
- Root words may carry an `example` (`he`, `translit.{fr,en}`, `translation.{fr,en}`); it is optional.
- A root may carry a `source` string; it is shown at the bottom of the root card.

## Theme file

`theme`, `status`, `emoji`, `title.{fr,en}`, `words[]`, `sentences[]`. A pack is every word
of a theme at a given level (split in chunks of 15). `sentences` are exactly 4 short sentences
per level (`level`, `he`, `translit.{fr,en}`, `translation.{fr,en}`) that reuse the pack's
words; they are shown under the word list. Each sentence must contain at least one word
of its pack (checked by the tests).

## Review workflow

Every theme and root has a `status`:

- `draft`: drafted, not yet checked by a Hebrew speaker. Previews show a warning.
- `reviewed`: checked. Only this status should be scheduled for real users.

Flip a set to `reviewed` only after a native/fluent check of nikud, meaning and
both transliterations.

## Current library

- **Level 1 and 2:** 11 themes each (body, house, family, food, clothes, animals, nature and weather, city and
  transport, time, emotions and character, health and physical state). The level 2 emotions and physical-state
  sets are the cards from the "Les 1001 mots en hébreu" screenshots.
- **Level 3 (advanced):** idiomatic expressions and slang, the format of the "Expressions typiquement israéliennes"
  card: 10 packs of 8 expressions (feelings, body, animals, food, nature, time and money, work, speech, slang,
  daily life), each with a literal meaning where it helps and 4 sentences.
- **Roots are shared by everyone**, whatever their level: 46 roots. Six were written for this bot with example
  sentences; the others come from the root sheets of Serge Frydman (Ort Villiers, hebreu.org), credited in their
  `source` field. For those, the word choice follows the sheets while the glosses are re-written and English
  added. Get the author's permission before publishing them beyond a private study group.

## The locked order (no repeats)

`content/order.json` is the order in which packs (one list per level) and roots (one shared list) are sent.
It is **append-only**: new items go at the end, nothing is reordered or removed. The item for a day is the one
at that day's index (Sunday to Friday count, Saturday reuses Friday's), so adding content never changes what a
day gets and nothing repeats until a list is used up.

```bash
python -m hebbot.order sync      # after adding a pack or a root: append it to order.json
python -m hebbot.order check     # validate (also runs in the tests); add --base origin/main to check it only grew
python -m hebbot.order runway    # send days of unseen content left, per list (warns under 14)
```

A level is only offered to new subscribers once it has at least 10 packs.

## Spelling

`python -m hebbot.spell` checks every Hebrew string with Hspell (`apt-get install hspell`). Words that are fine
but unknown to the dictionary go in `content/spell-allow.txt` with a note. It catches missing letters, not wrong
meanings: a fluent reader is still needed.

## Daily push

`python -m hebbot.daily` picks one themed pack (words + a few sentences) and one root
from the date (no
database, no AI). Same date, same messages; each day moves to the next theme and the
next root. Drafts are only used with `--allow-draft`.

## Sending unreviewed content

`SEND_DRAFTS` in `hebbot/daily.py` decides whether content still marked `draft` may be sent (the scheduled send
and the Worker's instant first lesson both follow it). When the content is reviewed, set it to `False`, mark the
reviewed sets `reviewed`, run `python -m hebbot.export_bundle` and commit.

## Commands

```bash
python -m hebbot.validate                                  # schema + length checks
python -m hebbot.order sync                                # append new packs/roots to the locked order
python -m hebbot.export_bundle                             # refresh worker/src/daily-bundle.json after content edits
python -m hebbot.spell                                     # Hebrew spell-check
python -m unittest discover -s tests -t .                  # tests
python -m hebbot.preview --kind pack --theme body --level 1 --lang fr
python -m hebbot.preview --kind root --lang en --root shlh
python -m hebbot.preview --kind pack --theme house --level 2 --lang fr --send   # to Telegram
python -m hebbot.daily --level 1 --lang fr --allow-draft                          # today's push (print)
python -m hebbot.daily --level 2 --lang en --date 2026-11-15 --allow-draft --send
```
