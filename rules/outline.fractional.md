---
id: outline.fractional
title: Whole-unit coordinates in CFF outlines
summary: Outlines in OTF (CFF) fonts use only whole-unit coordinates.
category: C
level: designer
severity: low
action: fix
applies: OTF fonts with CFF or CFF2 outlines.
related: outline.extrema, widths.near_equal
---

## What it checks

Every point of every outline lies on a whole unit: (312, 540), not (312.4, 539.75).

## Why it matters

Fractional coordinates usually come from scaling, rotating or interpolating outlines. TrueType fonts round them at export, but CFF outlines (OTF) can keep them. Different apps and rasterizers then round them differently, so the same glyph can differ by a unit from one app to another, stems lose their exact width, and joins between components may show hairline gaps.

## How it is checked

All points of each glyph's own contours are read from the CFF outlines. Points with a fractional x or y are counted per glyph; the finding lists the glyphs with their count.

## When it does not apply

- TrueType fonts (TTF and their WOFF copies): coordinates are always rounded there.
- Variable CFF2 fonts are checked in their default master.

## How to fix

Round the coordinates in the source and export again. In Glyphs, keep the grid spacing in Font Info at 1 so that nodes snap to whole units, round the existing ones, and check that scaling or interpolation in the instances does not produce new fractions.

## Example

| Glyph | Point | |
|---|---|---|
| H | (88, 0) | good |
| e | (312.5, 540) | bad |
