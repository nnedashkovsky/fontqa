---
id: tables.meta
title: Design and supported languages (meta table)
summary: A font whose main script is not Latin has a meta table that lists its design and supported languages (dlng, slng).
category: A
level: engineer
severity: low
action: fix
applies: Installable fonts whose main script is Chinese, Japanese, Korean, Arabic, Cyrillic, Greek, Hebrew, Thai or Devanagari.
related: names.localized
sources:
  - OpenType spec, meta table | https://learn.microsoft.com/en-us/typography/opentype/spec/meta
---

## What it checks

The `meta` table tells the system which languages the font was designed for (`dlng`) and which it supports (`slng`). For a font made mainly for a script other than Latin, the table should be there.

## Why it matters

Windows Settings → Fonts, macOS and font pickers use `meta` to choose the preview text and to match fonts to the language of a document. Without it, a Japanese or Cyrillic font is previewed with English text, so it looks empty or generic in the list, and language-aware apps may not offer it first for text in that language.

## How it is checked

1. Characters of the font are counted by script, ignoring common characters (punctuation, digits) and combining marks.
2. The script with the most characters is the main script.
3. If it is one of Hani, Hira/Kana, Hang, Arab, Cyrl, Grek, Hebr, Thai or Deva and there is no `meta` table, the check reports it, with the expected language tag (`zh-Hans`, `ja`, `ko`, `ar`, `ru`, `el`, `he`, `th`, `hi`).
4. If Latin is still 25% or more of the characters, the font is treated as multi-script and the result is **Confirm** rather than Fix: the preview language is then a choice, not a defect.

## When it does not apply

- Latin-only fonts, or fonts whose main script is Latin.
- Scripts not in the list above.
- Web fonts.

## How to fix

Add a `meta` table with `dlng` and `slng` for the scripts the font is designed for, for example `dlng = Jpan`, `slng = Jpan, Latn`. In Glyphs, use the meta Table custom parameter.

## Example

| Font | Main script | Latin share | meta | |
|---|---|---|---|---|
| Acme Mincho | Hani, 7,000 characters | 3% | — | bad: Fix |
| Acme Sans Pro | Cyrl, 260 characters | 45% | — | Confirm |
| Acme Sans Pro | Cyrl | 45% | dlng Latn, Cyrl | good |
