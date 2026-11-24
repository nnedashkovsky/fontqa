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

A compiler never writes a wrong magic number, so a wrong one is a **trace of a hand edit**: someone patched the file's bytes instead of re-exporting, and other tables may be affected too. A scale outside the range makes every glyph, metric and position meaningless.

Systems differ in how they react. Strict parsers — the OpenType Sanitizer in Chrome and Firefox — refuse the file, so a web font does not load. macOS (CoreText) registered a font with a zeroed magic number without complaint when tested, so "the system accepts it" does not mean the file is sound.

## How it is checked

The three values are read from `head` and compared with the table above; each wrong one is reported separately. Whether `indexToLocFormat` fits the `loca` table is checked in *Glyph counts agree between tables*.

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Export again; set the units per em to 1000 (or 2048) in the source. If a hand edit changed the table, restore it from a compiled font.

The `head` table starts with its version (bytes 0–3), `fontRevision` (4–7), `checkSumAdjustment` (8–11) and `magicNumber` (12–15). A script that recomputes the file checksum and writes it **4 bytes too far** overwrites the magic number; the same script written correctly leaves it alone.

## Example

| Case | Verdict |
|---|---|
| unitsPerEm 1000 or 2048 | good |
| unitsPerEm 8 | bad: below the minimum of 16 |
| magicNumber `0x5F0F3CF5` | good |
| magicNumber `0x00000000`, after a script wrote the checksum at byte 12 instead of byte 8 | bad: the table was edited outside the compiler; check the other tables too |
