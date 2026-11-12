---
id: layout.legacy_kern
title: Legacy kern table for Word
summary: An installable font with OpenType kerning also has a legacy kern table, so that Microsoft Word kerns it.
category: D
level: engineer
severity: low
action: confirm
applies: Installable fonts (outside a Web folder) with GPOS kerning.
related: layout.kern_shadowed
sources:
  - OpenType spec, kern table | https://learn.microsoft.com/en-us/typography/opentype/spec/kern
---

## What it checks

Kerning is normally stored in GPOS. The old TrueType `kern` table can hold a flat list of pairs as well. The check reports installable fonts that have GPOS kerning but no `kern` table.

## Why it matters

Microsoft Word, in many versions and settings, applies kerning only from the legacy `kern` table. With GPOS alone, text in Word is not kerned at all — even with "Kerning for fonts" switched on. Users notice it in large headings: "AV", "To", "Ye" look loose.

The `kern` table has no class kerning, so it is a flattened copy of the GPOS pairs and can be large; that is why it is often left out, and why the result is **Confirm**.

## How it is checked

For installable fonts, the check looks for GPOS kerning (a `kern` feature) and a legacy `kern` table. GPOS kerning without the table is reported.

## When it does not apply

- Web fonts: browsers use GPOS.
- Fonts without kerning.

## How to fix

Export a legacy `kern` table too, at least for the Desktop build. Some editors can write it at export; otherwise it can be added afterwards with fontTools by flattening the GPOS pairs. Keep it within the size limits of the format (pairs per subtable).

## Example

| Font | GPOS kern | kern table | |
|---|---|---|---|
| Desktop/AcmeSans-Bold.otf | yes | yes | good |
| Desktop/AcmeSans-Bold.otf | yes | — | Confirm: Word will not kern |
| Web/AcmeSans-Bold.woff2 | yes | — | not checked |
