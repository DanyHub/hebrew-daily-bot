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
- `pos`: `nm`/`nf` (masc./fem. noun), `nmp`/`nfp` (plural), `v`, `adj`, `adv`.
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

Themes (levels 1 and 2): body, house, family, food, clothes, animals, nature and
weather, city and transport, time, emotions and character, health and physical
state. The level 2 "emotions" and "health and physical state" sets are the cards
from the "Les 1001 mots en hébreu" screenshots (Hebrew and French as shown there).
Roots: 8 at level 1 and 38 at level 2. Six were written for this bot with example
sentences (ktv, lmd, ahv, shlh, ptch, shmr); the others come from the root sheets of
Serge Frydman (Ort Villiers, hebreu.org), shown with a source line. For those, the
word choice follows the sheets while the glosses are re-written and English added.
Get the author's permission before publishing them beyond a private study group.

## Daily push

`python -m hebbot.daily` picks one themed pack (words + a few sentences) and one root
from the date (no
database, no AI). Same date, same messages; each day moves to the next theme and the
next root. Drafts are only used with `--allow-draft`.

## Commands

```bash
python -m hebbot.validate                                  # schema + length checks
python -m unittest discover -s tests -t .                  # tests
python -m hebbot.preview --kind pack --theme body --level 1 --lang fr
python -m hebbot.preview --kind root --level 2 --lang en
python -m hebbot.preview --kind pack --theme house --level 2 --lang fr --send   # to Telegram
python -m hebbot.daily --level 1 --lang fr --allow-draft                          # today's push (print)
python -m hebbot.daily --level 2 --lang en --date 2026-11-15 --allow-draft --send
```
