---
id: head.sane
title: The head table has valid values
summary: head.magicNumber is 0x5F0F3CF5, unitsPerEm is between 16 and 16384, indexToLocFormat is 0 or 1.
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files.
related: maxp.counts, sfnt.checksums
sources:
  - OpenType spec, head table | https://learn.microsoft.com/en-us/typography/opentype/spec/head
---

## What it checks

The `head` table holds the font's global values. Three of them are validated by every parser:

| Field | Valid value |
|---|---|
| `magicNumber` | `0x5F0F3CF5` |
| `unitsPerEm` | 16 to 16384 (1000 for CFF and 1000 or 2048 for TrueType are the usual choices) |
| `indexToLocFormat` | 0 (short offsets) or 1 (long offsets) |

## Why it matters

A wrong magic number means the table is not a `head` table; a scale outside the range makes every glyph, metric and position meaningless. Parsers refuse such a file, so the font does not install.

## How it is checked

The three values are read from `head` and compared with the table above; each wrong one is reported separately. Whether `indexToLocFormat` fits the `loca` table is checked in *Glyph counts agree between tables*.

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Export again; set the units per em to 1000 (or 2048) in the source. If a hand edit changed the table, restore it from a compiled font.

## Example

| unitsPerEm | Verdict |
|---|---|
| 1000, 2048 | good |
| 8 | bad: below the minimum of 16 |
