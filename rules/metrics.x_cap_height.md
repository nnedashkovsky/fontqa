---
id: metrics.x_cap_height
title: Stated x-height and cap height match the drawing
summary: The x-height and cap height stored in the font (OS/2) equal the tops of x and H as drawn, within 0.5% of the em.
category: F
level: designer
severity: low
action: confirm
applies: All fonts that have x and H.
related: metrics.win_clipping, metrics.family_vertical
sources:
  - OpenType spec, OS/2 sxHeight and sCapHeight | https://learn.microsoft.com/en-us/typography/opentype/spec/os2#sxheight
---

## What it checks

The font stores its x-height and cap height as numbers (OS/2 `sxHeight`, `sCapHeight`). The check compares them with the real tops of the letters **x** and **H**.

## Why it matters

Apps use these numbers without looking at the glyphs:

- to size **synthetic small caps, superscripts and subscripts** when the font has none;
- to match the size of a **fallback font** to this one (CSS `font-size-adjust`, some layout engines);
- to align inline images and math with the x-height.

If the numbers are wrong, these things come out too big or too small, even though the font itself looks right.

## How it is checked

1. The top of the outline of **x** is compared with `sxHeight`, the top of **H** with `sCapHeight`.
2. A difference larger than **0.5% of the em** (5 units at 1000 UPM) is reported, with both values.

The result is **Confirm**: overshoots or a design with a slanted top can make a different value reasonable.

## When it does not apply

Fonts without x or H, or without these fields (OS/2 version 1 and older).

## How to fix

In the source, set the x-height and cap height of each master to the drawn heights. In Glyphs, Font Info → Masters → x-Height and Cap Height; Glyphs writes them to OS/2 at export.

## Example

| | Stated | Drawn | |
|---|---|---|---|
| x-height | 500 | 500 | good |
| cap height | 700 | 714 | bad at 1000 UPM: 14 units off |
