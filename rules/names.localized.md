---
id: names.localized
title: Localized name records are complete
summary: Every Windows language that has its own IDs 1/2 also has IDs 16/17, when English has them.
category: A
severity: high
action: fix
applies: Installable fonts (OTF, TTF outside a Web folder).
related: names.ribbi
sources:
  - OpenType spec, name table, language IDs | https://learn.microsoft.com/en-us/typography/opentype/spec/name#windows-language-ids
---

## What it checks

A font can carry its names in several languages: English, plus Japanese, Chinese, Russian… Each language has its own set of records. If a language has its own family and style (IDs 1 and 2), it must also have its own typographic family and style (IDs 16 and 17) — as long as the English set has them.

## Why it matters

Apps choose the record set that matches the user's interface language, **as a whole**. They do not mix languages record by record.

So on a Japanese system the app reads the Japanese IDs 1 and 2. If the Japanese set has no IDs 16/17, the app concludes that this font has only the four RIBBI styles. The whole family then appears under several family names, each with only Regular / Bold — exactly what the English names were built to avoid. On an English system everything looks fine, so the problem is easy to miss.

## How it is checked

1. Takes the Windows English (0x409) records: which of IDs 16 and 17 exist.
2. Every other Windows language that has ID 1 or ID 2 must also have each of IDs 16 / 17 that English has.
3. Each language with missing records is one line in the finding: which IDs it has and which are missing.

## When it does not apply

- Languages that have no IDs 1/2 of their own: the app falls back to English for all names, which is consistent.
- English without IDs 16/17 (a pure RIBBI family): nothing to copy.
- Web fonts.

## How to fix

Copy IDs 16 and 17 into every language that has IDs 1 and 2. If the style name is not translated, use the English value; what matters is that the record exists.

In Glyphs, localized names come from the Localized Family Names / Localized Style Names properties; add the typographic family and style for the same languages.

## Example

| Language | IDs present | |
|---|---|---|
| English 0x409 | 1, 2, 3, 4, 5, 6, 16, 17 | reference |
| Japanese 0x411 | 1, 2, 4, 16, 17 | good |
| Chinese 0x804 | 1, 2, 4 | bad: lacks 16, 17 |
