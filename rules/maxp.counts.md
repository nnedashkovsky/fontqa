---
id: maxp.counts
title: Glyph counts agree between tables
summary: maxp.numGlyphs matches hmtx, loca (or the CFF CharStrings) and the post glyph names.
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files.
related: head.sane, sfnt.outline_match
sources:
  - OpenType spec, maxp table | https://learn.microsoft.com/en-us/typography/opentype/spec/maxp
  - OpenType spec, hmtx and loca tables | https://learn.microsoft.com/en-us/typography/opentype/spec/hmtx
---

## What it checks

`maxp.numGlyphs` states how many glyphs the font has. The tables that hold one record per glyph must agree with it: `hmtx` (advance widths), `loca` (outline offsets; it has one more entry than there are glyphs), the CFF `CharStrings` and the glyph names in `post` format 2.

## Why it matters

Tables are read by glyph index. If one holds fewer records than `maxp` promises, the parser reads past its end; if more, glyphs at the end are dropped. The result is a rejected font, missing or shifted glyphs, or wrong widths.

**Tested:** a font whose `maxp` promised 999 glyphs against 220 in the other tables was refused by macOS and Windows.

## How it is checked

- `hhea.numberOfHMetrics` is between 1 and the glyph count, and `hmtx` is long enough: four bytes for each full metric and two for each remaining left side bearing.
- `loca` has glyphs + 1 entries, counted with the entry size `head.indexToLocFormat` gives (a mismatch here is usually a wrong format).
- A CFF or CFF2 font has as many charstrings as glyphs.
- `post` format 2 lists as many names as glyphs (medium).

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Export the font again from the source. Counts are written by the compiler; if they disagree, the file was edited or built by a tool that left a table behind.

## Example

| maxp | hmtx | loca | Verdict |
|---|---|---|---|
| 220 | 220 glyphs | 221 entries | good |
| 999 | 220 glyphs | 221 entries | bad: maxp says 999 glyphs |
