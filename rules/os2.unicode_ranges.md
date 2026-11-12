---
id: os2.unicode_ranges
title: Unicode range bits match the character set
summary: The Unicode range bits in OS/2 (ulUnicodeRange) say which blocks the font covers, and they match its characters.
category: F
level: engineer
severity: low
action: confirm
applies: All fonts.
related: os2.codepage_ranges
sources:
  - OpenType spec, OS/2.ulUnicodeRange | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#ulunicoderange1-bits-031ulunicoderange2-bits-3263ulunicoderange3-bits-6495ulunicoderange4-bits-96127
---

## What it checks

`OS/2.ulUnicodeRange` is a set of 128 bits, one per group of Unicode blocks (Basic Latin, Cyrillic, Greek, General Punctuation…). A bit says "this font supports that block". The check compares the bits in the font with the bits its characters actually call for.

## Why it matters

Windows and Office use these bits to decide whether a font can show a piece of text, and to choose fallback fonts. A bit that is off for a block the font covers can make Office pick another font for that text; a bit that is on for a block the font does not cover can make the system choose this font and then show missing characters.

The result is **Confirm**: some clients ask for certain bits to be off on purpose.

## How it is checked

fontTools computes the bits from the font's characters. The font's own bits are compared with them, and the finding lists bits that are **off but used** and **on but unused**.

## When it does not apply

Always applies.

## How to fix

Let the export compute the bits from the character set — editors do this by default. If they were set by hand (a custom parameter), remove the override or record why it differs.

## Example

| Bit | Block | In the font | |
|---|---|---|---|
| 9 | Cyrillic | on, 66 Cyrillic characters | good |
| 62 | Alphabetic Presentation Forms | off, but ﬁ ﬂ are there | Confirm |
| 60 | Private Use Area | on, no PUA characters | Confirm |
