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
- Root words additionally require an `example` (`he`, `translit.{fr,en}`, `translation.{fr,en}`).

## Theme file

`theme`, `status`, `emoji`, `title.{fr,en}`, `words[]`. A pack is every word of a
theme at a given level (split in chunks of 15).

## Review workflow

Every theme and root has a `status`:

- `draft`: drafted, not yet checked by a Hebrew speaker. Previews show a warning.
- `reviewed`: checked. Only this status should be scheduled for real users.

Flip a set to `reviewed` only after a native/fluent check of nikud, meaning and
both transliterations.

## Commands

```bash
python -m hebbot.validate                                  # schema + length checks
python -m unittest discover -s tests -t .                  # tests
python -m hebbot.preview --kind pack --theme body --level 1 --lang fr
python -m hebbot.preview --kind root --level 2 --lang en
python -m hebbot.preview --kind pack --theme house --level 2 --lang fr --send   # to Telegram
```
