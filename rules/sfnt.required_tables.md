---
id: sfnt.required_tables
title: The tables every font needs are present
summary: cmap, head, hhea, hmtx, maxp, name, OS/2 and post exist, together with outlines (glyf and loca, or CFF).
category: A
level: engineer
severity: high
action: fix
applies: TTF and OTF files, including files the font library cannot open.
related: sfnt.header, sfnt.outline_match
sources:
  - OpenType spec, required tables | https://learn.microsoft.com/en-us/typography/opentype/spec/otff#required-tables
---

## What it checks

An OpenType font must carry eight tables — `cmap` (characters to glyphs), `head` (global values), `hhea` and `hmtx` (horizontal metrics), `maxp` (glyph count), `name` (names), `OS/2` (style and metrics) and `post` (PostScript data) — and its outlines: `glyf` together with `loca` for TrueType, or `CFF` (`CFF2` in variable OpenType).

## Why it matters

The installer and the text engines read these tables directly. Without `name` or `cmap` the font does not install or shows no text; without `OS/2` or `post`, Windows and Adobe applications can refuse it or list it wrongly.

## How it is checked

The table tags are read from the directory. Each missing required table is listed. For outlines, `glyf` without `loca` (or the reverse) and a font with neither `glyf` nor `CFF` are reported. Fonts with bitmap or SVG glyph tables (`CBDT`, `EBDT`, `sbix`, `SVG `) may have no outline table.

## When it does not apply

- Web fonts (WOFF, WOFF2).

## How to fix

Add the missing table at the source and export again; every font editor writes these tables by default, so a gap usually means a post-processing tool dropped one.

## Example

| Tables | Verdict |
|---|---|
| cmap, head, hhea, hmtx, maxp, name, OS/2, post, glyf, loca | complete |
| the same without OS/2 | bad: Windows may refuse or misname the font |
