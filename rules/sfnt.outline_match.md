---
id: sfnt.outline_match
title: Outline tables match the font's declared type
summary: The version tag, the maxp version and the outline table agree — TrueType with glyf, or CFF with OTTO — and the CFF matrix is 1/unitsPerEm.
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files.
related: sfnt.required_tables, head.sane
sources:
  - OpenType spec, maxp table | https://learn.microsoft.com/en-us/typography/opentype/spec/maxp
  - OpenType spec, CFF table | https://learn.microsoft.com/en-us/typography/opentype/spec/cff
---

## What it checks

A font declares what its outlines are in three places: the file's version tag (`00010000` for TrueType, `OTTO` for CFF), the `maxp` table version (`1.0` for TrueType, `0.5` for CFF) and the outline table itself (`glyf` or `CFF`). The three must tell the same story. A CFF font also states a scale (`FontMatrix`), which must be 1 divided by `unitsPerEm`.

## Why it matters

A text engine picks its rasterizer from these declarations. If they disagree it reads quadratic curves as cubic ones or the reverse, so glyphs are empty or distorted — or the font is rejected at install time. A wrong CFF scale draws every glyph too large or too small.

**Tested:** a TrueType font whose version tag said `OTTO` was refused by macOS and Windows. The `maxp` version and the CFF matrix were not tested.

## How it is checked

- Both `glyf` and `CFF` in one file, `OTTO` with `glyf`, or a TrueType version tag with `CFF` are reported.
- The `maxp` version must be `0.5` for CFF and `1.0` for TrueType.
- For CFF, the first value of `FontMatrix` times `unitsPerEm` must be 1 (medium).

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Export the font again with one outline format. If the file was converted by hand (TTF renamed to OTF, or the reverse), convert it with a font tool (fontTools, `otf2ttf`, Glyphs export) instead.

## Example

| Version tag | Outlines | maxp | Verdict |
|---|---|---|---|
| OTTO | CFF | 0.5 | good |
| 00010000 | glyf | 1.0 | good |
| 00010000 | glyf | 0.5 | bad: maxp describes a CFF font |
