---
id: os2.codepage_ranges
title: Code page bits match the character set
summary: The code page bits in OS/2 (ulCodePageRange) say which legacy code pages the font supports, and they match its characters.
category: F
level: engineer
severity: low
action: confirm
applies: All fonts.
related: os2.unicode_ranges, charset.store_minimum
sources:
  - OpenType spec, OS/2.ulCodePageRange | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#ulcodepagerange1-bits-031ulcodepagerange2-bits-3263
---

## What it checks

`OS/2.ulCodePageRange` has a bit for each legacy Windows and Mac code page: Latin 1 (1252), Central European (1250), Cyrillic (1251), Greek, Turkish and others. A bit says "this font covers that code page". The check compares the bits with the code pages the font's characters really cover.

## Why it matters

Windows uses these bits to list the scripts a font supports — the "Script" menu in older font dialogs, and the font lists of some apps filtered by language. A missing bit hides the font from users of that script; an extra bit offers it for text it cannot show.

The result is **Confirm**, as with the Unicode range bits.

## How it is checked

fontTools computes the code page bits from the font's characters. The font's bits are compared with them, and the finding lists bits that are **off but supported** and **on but not supported**.

## When it does not apply

Always applies (unless the installed fontTools cannot compute the bits).

## How to fix

Let the export compute the bits — editors do this by default. Remove a custom parameter that sets them by hand, unless a client asked for it.

## Example

| Bit | Code page | | |
|---|---|---|---|
| 0 | 1252 Latin 1 | on, all characters present | good |
| 1 | 1250 Central European | off, but Ł ő ű are there | Confirm: Windows does not list the font for Polish |
